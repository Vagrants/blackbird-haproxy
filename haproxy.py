#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import os
import socket

from blackbird.plugins import base


class ConcreteJob(base.JobBase):
    """
    This Class is required for blackbird plugin module.
    """

    def __init__(self, options, queue=None, logger=None):
        super(ConcreteJob, self).__init__(options, queue, logger)

    def looped_method(self):
        """
        Get stats data of haproxy.
        Method name must be "looped_method".
        """

        if not 'stats_socket' in self.options:
            raise ValueError('Pleases specify location of stats socket...')
        else:
            stats_socket = self.options['stats_socket']

        if os.path.exists(stats_socket):

            if os.access(stats_socket, os.W_OK):

                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(stats_socket)
                editor = sock.makefile('r+')
                editor.write('show stat\n')
                editor.flush()

                result_raw = editor.read()
                result_keys = result_raw.splitlines()[0][2:-1]
                result_keys = result_keys.split(',')
                result_values = result_raw.splitlines()[1:-1]
                svnames = [line.split(',')[1] for line in result_values]
                
                item = HAProxyDiscoveryItem(
                    key='haproxy.stat.LLD',
                    value=svnames,
                    host=self.options['hostname']
                )
                self.queue.put(item, block=False)

                editor.close()
                sock.close()

                for line in result_values:
                    line = line.split(',')
                    svname = line[1]
                    for (key, value) in zip(result_keys, line):

                        item = HAProxyItem(
                            key=key,
                            value=value,
                            host=self.options['hostname'],
                            svname=svname
                        )
                        self.queue.put(item, block=False)

                        self.logger.debug(
                            ('Inserted to queue {0}'.format(item.data))
                        )

                self.logger.info('Enqueued HAProxyName')

            else:
                self.logger.warn('{0}: Permission denied.'.format(stats_socket))

        else:
            self.logger.warn('{0}: No such file or directory.'.format(stats_socket))


class HAProxyItem(base.ItemBase):
    """
    Enqueued item. This Class has required attribute "data".
    """

    def __init__(self, key, value, host, svname):
        super(HAProxyItem, self).__init__(key, value, host)
    
        self.__data = dict()
        self.svname = svname
        self._generate()

    @property
    def data(self):

        return self.__data

    def _generate(self):
        self.__data['host'] = self.host
        self.__data['key'] = (
            'haproxy.stat[{svname},{key}]'
            ''.format(svname=self.svname, key=self.key)
        )
        self.__data['value'] = self.value


class HAProxyDiscoveryItem(base.ItemBase):
    """
    Item for "zabbix discovery".
    """

    def __init__(self, key, value, host):
        super(HAProxyDiscoveryItem, self).__init__(key, value, host)

        self.__data = dict()
        self._generate()

    @property
    def data(self):
        return self.__data

    def _generate(self):
        self.__data['host'] = self.host
        self.__data['clock'] = self.clock
        self.__data['key'] = self.key

        if (type(self.value) is list) or (type(self.value) is tuple):
            value = {
                'data': [{'{#SVNAME}': svname} for svname in self.value],
            }

        else:
            value = {'data': [
                {'{#SVNAME}': self.value}
            ]}

        self.__data['value'] = json.dumps(value)


class Validator(base.ValidatorBase):
    """
    Check whether the your config file value is invalid.
    """

    def __init__(self):
        self.__spec = None

    @property
    def spec(self):
        self.__spec = (
            "[{0}]".format(__name__),
            "stats_socket = string(default='/var/lib/haproxy/stats')",
            "hostname = string(default={0})".format(self.gethostname()),
        )
        return self.__spec


if __name__ == '__main__':
    OPTIONS = {
            'stats_socket': '/var/lib/haproxy/stats',
            'hostname': 'hogehoge.com'
    }
    BBL_HAPROXY = ConcreteJob(options=OPTIONS)
    BBL_HAPROXY.looped_method()

