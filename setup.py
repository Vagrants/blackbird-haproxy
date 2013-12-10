#!/usr/bin/env python
# -*- encodig: utf-8 -*-

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

setup(
    name='blackbird-haproxy',
    version='0.1.0',
    description=(
        'Get stats of HAProxy for blackbird'
        'by using "show stats command".'
    ),
    author='ARASHI, Jumpei',
    author_email='jumpei.arashi@arashike.com',
    url='http://ghe.amb.ca.local/Unified/blackbird-haproxy',
    data_files=[
        ('/opt/blackbird/plugins', ['haproxy.py'])
    ]
)
