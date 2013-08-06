# -*- coding: UTF-8 -*-
import os
import re
import pwd
import json
import stat
import time
import shutil
import signal
import subprocess

from arrow_judge import *

class SandBox():
	def __init__(self, directory, user, params):
		self.base_dir = directory
		self.sandbox_user = user

		self.compile_command = params['compile']
		self.execute_command = params['execute']
		self.compile_limit = params['compile_time']
		self.execute_limit = params['cpu']
		self.output_limit = params['output_limit']
		self.execute_memory = params['memory']

		self.id = params['id']
		self.problem = params['problem']
		self.inputs = params['input']
		self.outputs = []
		self.cpu = []
		self.memory = []

		if self.problem == '0':
			self.answers = params['answer']

		f = open(os.path.join(self.base_dir, 'Main.' + params['extension']), 'w')
		f.write(params['source'].encode('UTF-8'))
		f.close()

	def execCommand(self, command):
		null = open('/dev/null')
		return subprocess.call(command, shell=True, stdout=null, stderr=null)

	def mount(self):
		# Change permission
		uid = pwd.getpwnam(self.sandbox_user)
		os.chown(self.base_dir, uid.pw_uid, uid.pw_gid)

		# Mount /dev filesystem
		if not os.path.exists(self.base_dir + '/dev'):
			os.mkdir(self.base_dir + '/dev')
		for i in AVAILABLE_DEVICES:
			path = self.base_dir + '/dev/' + i

			if not os.path.exists(path):
				open(path, 'a').close()
			if os.path.isdir(path):
				os.removedirs(path)
				open(path, 'a').close()

			self.execCommand('mount -n --bind /dev/%s %s' % (i, path))

		# Mount cgroup filesystem
		self.cgroup_dir = {}
		if not os.path.exists(self.base_dir + '/cgroup'):
			os.mkdir(self.base_dir + '/cgroup')
		for i in CGROUP_SUBSETS:
			path = self.base_dir + '/cgroup/' + i

			if not os.path.exists(path):
				os.makedirs(path)
			if not os.path.isdir(path):
				os.remove(path)
				os.makedirs(path)

			self.execCommand('mount -t cgroup -o %s none %s' % (i, path))

		# Mount allowed directory
		for i in AVAILABLE_PATHS:
			path = self.base_dir + i

			if not os.path.exists(path):
				os.makedirs(path)
			if not os.path.isdir(path):
				os.remove(path)
				os.makedirs(path)

			self.execCommand('mount -n --bind -o ro %s %s' % (i, path))

		# Mount tmp directory
		path = self.base_dir + '/tmp'
		if not os.path.exists(path):
			os.makedirs(path)
		if not os.path.isdir(path):
			os.remove(path)
			os.makedirs(path)
		os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

	def umount(self):
		# Unmount tmp directory
		path = self.base_dir + '/tmp'
		if os.path.exists(path):
			shutil.rmtree(path)

		# Unmount allowed directory
		for i in AVAILABLE_PATHS:
			path = self.base_dir + i

			while True:
				while self.execCommand('umount %s' % (path)):
					pass
				try:
					delete_path = i
					while delete_path != '/':
						if os.listdir(self.base_dir + delete_path):
							break
						os.rmdir(self.base_dir + delete_path)
						delete_path = os.path.dirname(delete_path)
				except OSError, e:
					if re.match(r'\[Errno 16\] Device or resource busy', str(e)):
						continue
				break

		# Unmount cgroup filesystem
		for i in CGROUP_SUBSETS:
			path = self.base_dir + '/cgroup/' + i

			while True:
				while self.execCommand('umount %s' % (path)):
					pass
				try:
					os.rmdir(path)
				except OSError, e:
					if re.match(r'\[Errno 16\] Device or resource busy', str(e)):
						continue
				break
		os.rmdir(self.base_dir + '/cgroup')

		# Unmount /dev filesystem
		for i in AVAILABLE_DEVICES:
			path = self.base_dir + '/dev/' + i

			while True:
				while self.execCommand('umount %s' % (path)):
					pass
				try:
					os.remove(path)
				except OSError, e:
					if re.match(r'\[Errno 16\] Device or resource busy', str(e)):
						continue
				break
				
		os.rmdir(self.base_dir + '/dev')

	def compile(self):
		# Compile
		self.process.stdin.write('sudo -u %s %s 1>/dev/null 2>error\n' % (self.sandbox_user, self.compile_command))
		self.process.stdin.flush()

		# Wait for end of compilation
		start_time = time.time()
		while True:
			if not os.path.exists(self.base_dir + '/error'):
				continue
			lsof = subprocess.check_output('lsof %s | tail -n1' % (self.base_dir + '/error'), shell=True)
			if not lsof:
				break
			if time.time() - start_time > int(self.compile_limit):
				match = re.match(r'[^ ]*[ ]*([0-9]*)', lsof)
				if match:
					pid = int(match.group(1))
					os.kill(pid, signal.SIGKILL)
					break
			time.sleep(0.1)

		# Checking error
		f = open(self.base_dir + '/error')
		error = f.read()
		f.close()

		# Compile Error
		os.remove(self.base_dir + '/error')
		if error != '':
			return self.build_response(2, error)

	def execute(self):
		null = open('/dev/null', 'w')
		self.process = subprocess.Popen('unshare -u -i -n chroot %s' % (self.base_dir), shell=True, stdin=subprocess.PIPE, stdout=null, stderr=null)

		# Limit of IPC
		for i in SYSCTL_PARAMS:
			self.process.stdin.write('sysctl -w "%s" > /dev/null 2>&1\n' % (i))
			self.process.stdin.flush()

		# Compile
		if self.compile_command:
			response = self.compile()
			if response:
				return response

		# Execute
		for i in range(len(self.inputs)):
			if len(self.inputs[i]) == 0:
				break
			input_len = len(self.inputs[i])
			if self.problem == '0':
				answer_len = len(self.answers[i])
			else:
				answer_len = 0

			# Setup input file
			f = open(self.base_dir + '/input', 'w')
			f.write(self.inputs[i].replace('\r', ''))
			f.close()

			# Setup execution script
			f = open(self.base_dir + '/judge.sh', 'w')
			f.write('ulimit -t %d\n' % (int(self.execute_limit) * 2))
			f.write('ulimit -m %d\n' % (int(self.execute_memory) * 2 + input_len + answer_len))
			for j in CGROUP_SUBSETS:
				f.write('echo $$ > /cgroup/%s/testcase/tasks\n' % (j))
			f.write('%s <input 1>output 2>error\n' % (self.execute_command))
			f.close()

			# Setup cgroup
			for j in CGROUP_SUBSETS:
				path = self.base_dir + '/cgroup/' + j + '/testcase'

				if not os.path.exists(path):
					os.makedirs(path)
				if not os.path.isdir(path):
					os.remove(path)
					os.makedirs(path)
					os.mkdir(path)

				uid = pwd.getpwnam(self.sandbox_user)
				os.chown(path + '/tasks',  uid.pw_uid, uid.pw_gid)

			# Execution
			start_time = time.time()
			self.process.stdin.write('sudo -u %s bash judge.sh\n' % (self.sandbox_user))
			self.process.stdin.flush()

			# Wait for end of execution
			execute_time = None
			while True:
				if not os.path.exists(self.base_dir + '/output'):
					continue
				lsof = subprocess.check_output('lsof %s | tail -n1' % (self.base_dir + '/output'), shell=True, stderr=null)
				if not lsof:
					break
				if time.time() - start_time > int(self.execute_limit) + 1:
					match = re.match(r'[^ ]*[ ]*([0-9]*)', lsof)
					if match:
						pid = int(match.group(1))
						os.kill(pid, signal.SIGKILL)
						execute_time = time.time() - start_time
						break
				time.sleep(0.1)

			# Check return value
			if os.path.exists(self.base_dir + '/execute'):
				os.remove(self.base_dir + '/execute')
			self.process.stdin.write('echo $? > execute\n');
			self.process.stdin.flush()

			while True:
				if os.path.exists(self.base_dir + '/execute'):
					break

			f = open(self.base_dir + '/execute')
			result = f.read()
			f.close()

			# Check output/resource data
			f = open(self.base_dir + '/output')
			output = f.read()
			output_len = len(output)
			if len(output) > self.output_limit:
				output = output[:self.output_limit] + ' ...'
			self.outputs.append(output)
			f.close()

			if execute_time:
				self.cpu.append(execute_time)
			else:
				f = open(self.base_dir + '/cgroup/cpuacct/testcase/cpuacct.usage')
				self.cpu.append(int(f.read().strip()) / 1e9)
				f.close()

			f = open(self.base_dir + '/cgroup/memory/testcase/memory.max_usage_in_bytes')
			self.memory.append((int(f.read().strip())) / 1024.0)
			f.close()

			for j in CGROUP_SUBSETS:
				os.rmdir(self.base_dir + '/cgroup/' + j + '/testcase')

			# Resource Limit Exceed
			if float(self.cpu[-1]) > float(self.execute_limit) or float(self.memory[-1]) > float(self.execute_memory):
				return self.build_response(4)

			# Accept
			if self.problem == '0':
				if self.outputs[i] == self.answers[i]:
					continue

			# Abnormal termination
			if result != '0\n':
				# Runtime Error
				f = open(self.base_dir + '/error')
				error = f.read()
				f.close()
				return self.build_response(3, error)

			# Wrong Answer
			if self.problem == '0':
				return self.build_response(5)


		return self.build_response(6)

	def build_response(self, status, *args):
		# Finish
		for i in ['input', 'output', 'error', 'execute', 'judge.sh']:
			if os.path.exists(self.base_dir + '/' + i):
				os.remove(self.base_dir + '/' + i)
		self.process.stdin.write('exit\n')
		self.process.stdin.flush()
		if not self.process.poll():
			try:
				self.process.terminate()
				self.process.wait()
			except OSError:
				pass

		# Build response
		result = {}
		result['problem'] = self.problem
		result['id'] = self.id
		result['status'] = status

		if status in (2, 3):
			result['error'] = args[0]
		if status in (3, 4, 5, 6):
			result['cpu'] = json.dumps(self.cpu)
			result['memory'] = json.dumps(self.memory)
			result['output'] = json.dumps(self.outputs)
				
		return result
