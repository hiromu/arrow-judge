# -*- coding: UTF-8 -*-
import os
import sys
import json
import time
import uuid
import urllib
import logging
import urllib2
import traceback

from arrow_judge import *
from arrow_judge.sandbox import SandBox

class Daemon():
	def __init__(self, config, client_id, log_handler, error_handler):
		self.stdin_path = '/dev/null'
		self.stdout_path = config.get('log', 'log').strip("'")
		self.stderr_path = config.get('log', 'log').strip("'")
		self.pidfile_path = config.get('main', 'pid_file')
		self.pidfile_timeout = 5

		self.base_url = config.get('main', 'url')
		self.client_id = client_id
		self.interval = int(config.get('main', 'interval'))
		self.judge_dir = config.get('main', 'judge_dir')
		self.judge_user = config.get('main', 'judge_user')

		self.compile_timeout = int(config.get('judge', 'compile_timeout'))
		self.output_limit = int(config.get('judge', 'output_limit')) * 1024

		self.judge_log = logging.getLogger('arrow-judge')
		self.judge_log.setLevel(logging.INFO)
		formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
		log_handler.setFormatter(formatter)
		self.judge_log.addHandler(log_handler)

		self.error_log = logging.getLogger('arrow-judge')
		self.error_log.setLevel(logging.WARN)
		formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
		error_handler.setFormatter(formatter)
		self.error_log.addHandler(error_handler)

	def trace(self):
		trace = traceback.format_exc()
		for line in trace.split('\n'):
			self.error_log.error(line)

	def get(self):
		try:
			html = urllib2.urlopen(self.base_url + '/judges/index/' + self.client_id).read()
			params = json.loads(html)
		except urllib2.HTTPError, e:
			if e.code != 404:
				self.error_log.error('HTTP Error %d: %s' % (e.code, e.msg))
				line = e.fp.readline()
				while line:
					self.error_log.error(line.rstrip())
					line = e.fp.readline()
		except ValueError, e:
			if e.message == 'No JSON object could be decoded':
				if html:
					self.error_log.error('Failed to decode json: %s' % (html))
			else:
				self.trace()
		except:
			self.trace()
		else:
			return params

	def judge(self, params):
		params['compile_time'] = self.compile_timeout
		params['output_limit'] = self.output_limit
		directory = self.judge_dir + '/' + str(uuid.uuid4())
		os.makedirs(directory)

		self.judge_log.info('Judging: id = %s, directory = %s' % (params['id'], directory))

		try:
			sandbox = SandBox(directory, self.judge_user, params)
			sandbox.mount()
			result = sandbox.execute()
			sandbox.umount()
		except:
			trace = traceback.format_exc()
			for line in trace.split('\n'):
				self.error_log.error(line)
		else:
			return result

	def post(self, result):
		try:
			urllib2.urlopen(self.base_url + '/judges/post/' + self.client_id, urllib.urlencode(result))
		except urllib2.HTTPError, e:
			if e.code != 404:
				self.error_log.error('HTTP Error %d: %s' % (e.code, e.msg))
				line = e.fp.readline()
				while line:
					self.error_log.error(line)
					line = e.fp.readline()
		except:
			self.trace()

	def run(self):
		while True:
			params = self.get()
			if params:
				result = self.judge(params)
				if result:
					self.post(result)
				continue
			time.sleep(self.interval)
