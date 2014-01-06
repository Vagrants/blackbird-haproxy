#!/usr/bin/env python
# -*- encoding: utf-8 -*-

import json
import os
import socket

from blackbird.plugins import base
from blackbird.plugins.base import BlackbirdPluginError


class ConcreteJob(base.JobBase):
    """
    This Class is required for blackbird plugin module.
    """

    def __init__(self, options, queue=None, logger=None):
        super(ConcreteJob, self).__init__(options, queue, logger)
        print options

    def build_items(self):
        """
        Get stats data of haproxy.
        """
        if not 'stats_socket' in self.options:
            err_message = 'Pleases specify location of stats socket...'
            raise BlackbirdPluginError(err_message)
        else:
            stats_socket = self.options['stats_socket']

        raw_result = self._get_stat(stats_socket)
        result_keys = raw_result.splitlines()[0][2:-1]
        result_keys = result_keys.split(',')
        result_values = raw_result.splitlines()[1:-1]

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

    def build_discovery_items(self):
        """
        Enqueued build_discovery_item
        """
        if not 'stats_socket' in self.options:
            raise ValueError('Pleases specify location of stats socket...')
        else:
            stats_socket = self.options['stats_socket']

        raw_result = self._get_stat(stats_socket)
        result_values = raw_result.splitlines()[1:-1]
        svnames = [line.split(',')[1] for line in result_values]
        item = base.DiscoveryItem(
            key='haproxy.stat.LLD',
            value=[{'{#SVNAME}': svname} for svname in svnames],
            host=self.options['hostname']
        )
        self.queue.put(item, block=False)

    def _get_stat(self, stats_socket):
        """
        Get haproxy's statistics.
        Execute 'show stat' to haproxy's "stats socket".
        """
        if os.path.exists(stats_socket):

            if os.access(stats_socket, os.W_OK):
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(stats_socket)
                editor = sock.makefile('r+')
                editor.write('show stat\n')
                editor.flush()
                raw_result = editor.read()
                editor.close()
                sock.close()
                return raw_result

            else:
                err_message = '{0}: Permission denied.'.format(stats_socket)
                raise BlackbirdPluginError(err_message)

        else:
            err_message = (
                '{0}: No such file or directory.'
                ''.format(stats_socket)
            )
            raise BlackbirdPluginError(err_message)


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
            "hostname = string(default={0})".format(self.detect_hostname()),
        )
        return self.__spec


if __name__ == '__main__':
    OPTIONS = {
        'stats_socket': '/var/lib/haproxy/stats',
        'hostname': 'hogehoge.com'
    }
    BBL_HAPROXY = ConcreteJob(options=OPTIONS)
    BBL_HAPROXY.build_items()
