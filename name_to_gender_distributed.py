import sys
import os
import subprocess
import json
from settings import user, password, servers, root_dir, male_dir, female_dir

def remote_ssh_cmd(user, password, server, command):
    ssh_cmd = 'sshpass -p %s ssh -o StrictHostKeyChecking=no %s@%s %s' % (password, user, server, command)
    ssh = subprocess.Popen(ssh_cmd, shell=True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
    stdout = ssh.stdout.readlines()
    stderr = ssh.stderr.readlines()
    return (stdout, stderr)

def get_firstnames(root_dir):
	# get the names
	names = os.listdir(root_dir)
	if type(names) is not list:
		names = [names, ]
	# get firstnames
	firstnames = [x.split('_')[0] for x in names]
	# remove duplicates
	firstnames = sorted(list(set(firstnames)))
	return firstnames

def genderize(firstnames, user, password, servers):
	max_num_names = 10 # number of maximum names in one query
	gender = []
	for server in servers:
		quota = 1 # probe the real quota
		while len(firstnames) > 1:
			names_batch = firstnames[0: min(quota, max_num_names, len(firstnames))]
			param = '&'.join(['name[]=%s' % x for x in names_batch])
			ssh_cmd = 'curl -gv https://api.genderize.io?%s 2> >(grep X-Rate-Limit-Remaining 1>&2)'
			stdout, stderr = remote_ssh_cmd(user, password, server, command)
			result = json.loads(stdout)
			if type(result) is not list:
				result = [result, ]
			result = [x for x in result if 'name' in x] # remove invalid result
			if len(result) != 0: # if there are valid result
				gender.extends(result)
				# update firstnames
				firstnames = [x for x in firstnames if x not in [y['name'] for y in result]]
				# update quota
				quota = int(stderr.split(': ')[-1])
			else:
				# quota has been run out. break out and increment server
				break

def main(user, password, servers, root_dir, male_dir, female_dir):
	try:
		f = open('firstnames.json', r)
		firstnames = json.loads(f.read())
	except:
		firstnames = get_firstnames(root_dir)
		f = open('firstnames.json', w)
		f.write(json.dump(firstnames))
	
	try:
		f = open('gender.json', r)
		gender = json.loads(f.read())
		firstnames = [x for x in firstnames if x not in [y['name'] for y in gender]]
		gender.extends(genderize(firstnames, user, password, servers))
	except:
		gender = genderize(firstnames, user, password, servers)
	finally:
		f = open('gender.json', w)
		f.write(json.dump(gender))
		

if __name__ == '__main__':
	main(user, password, servers, root_dir, male_dir, female_dir)
