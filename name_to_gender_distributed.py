import sys
import os
import subprocess
from settings import user, password, servers

def ssh_connect():
    command = 'ls'
    ssh_cmd = 'sshpass -p %s ssh -o StrictHostKeyChecking=no %s@%s %s' % (password, user, server, command)
    print ssh_cmd
    ssh = subprocess.Popen(ssh_cmd, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stdout = ssh.stdout.readlines()
    stderr = ssh.stderr.readlines()

def main():
	ssh_login()

if __name__ == '__main__':
	main()
