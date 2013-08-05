# -*- coding: UTF-8 -*-

AVAILABLE_DEVICES = ['full', 'null', 'random', 'stderr', 'stdin', 'stdout', 'urandom', 'zero']
CGROUP_SUBSETS = ['cpuacct', 'memory']
AVAILABLE_PATHS = ['/bin', '/etc', '/lib', '/lib64', '/proc', '/sbin', '/usr/bin', '/usr/include', '/usr/lib', '/var/lib']
SYSCTL_PARAMS = ['kernel.sem=0 0 0 0', 'kernel.shmall=0', 'kernel.shmmax=0', 'kernel.shmmni=0', 'kernel.msgmax=0', 'kernel.msgmnb=0', 'kernel.msgmni=0', 'fs.mqueue.queues_max=0']
