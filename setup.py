#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

setup(
	name = 'arrow-judge',
	version = '1.0.0',
	description = 'Arrow Judge is open source online judge system',
	author = 'Hiromu Yakura',
	author_email = 'hiromu1996@gmail.com',
	url = 'https://github.com/hiromu/arrow-judge',
	license = 'MIT',
	package_dir = {'arrow_judge': 'src'},
	packages = ['arrow_judge'],
	install_requires = ['python-daemon']
)
