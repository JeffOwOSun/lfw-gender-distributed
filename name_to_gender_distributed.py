import sys
import os
import subprocess
import json
import shutil
from settings import user, password, servers, root_dir, male_dir, female_dir, undetermined_dir

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
		print 'using server: %s\n' % server
		quota = 1 # probe the real quota
		while len(firstnames) > 1:
			names_batch = firstnames[0: min(quota, max_num_names, len(firstnames))]
			param = '&'.join(['name[]=%s' % x for x in names_batch])
			ssh_cmd = "curl -gv \\'https://api.genderize.io?%s\\' 2> >(grep X-Rate-Limit-Remaining 1>&2)'
			stdout, stderr = remote_ssh_cmd(user, password, server, ssh_cmd)
			try:
				result = json.loads(stdout)
			except:
				raise Exception('remote execution error: %s' % stderr)
			if type(result) is not list:
				result = [result, ]
			result = [x for x in result if 'name' in x] # remove invalid result
			if len(result) > 0: # if there are valid result
				gender.extends(result)
				print 'fetched %d results! ' % len(result)
				# update firstnames
				firstnames = [x for x in firstnames if x not in [y['name'] for y in result]]
				print '%d firstnames to go...\n' % len(firstnames)
				# update quota
				quota = int(stderr.split(': ')[-1])
			else:
				# quota has been run out. break out and increment server
				break
		if len(firstnames) <= 0:
			break
	return gender

def move_images(root_dir, male_dir, female_dir, undetermined_dir, gender):
	for dirpath, dirnames, filenames in os.walk(root_dir):
		# get the firstname for this dir
		firstname = os.path.basename(dirpath).split('_')[0]
		# look firstname up in gender
		query_result = [x for x in gender if x['name'] == firstname]
		# default to undetermined_dir
		target_dir = undetermined_dir
		# try to determine gender
		try:
			result = query_result[0]
			if float(result['probability']) > 0.9 and int(result['count']) >= 100:
				if result['gender'] == 'male':
					target_dir = male_dir
				elif result['gender'] == 'female':
					target_dir = female_dir
		except:
			pass
		# copy the files
		for source_file in filenames:
			shutil.copyfile(os.path.join(dirpath, source_file), os.path.join(target_dir, source_file))

def main(user, password, servers, root_dir, male_dir, female_dir, undetermined_dir):
	print 'loading firstnames...\n'
	try:
		f = open('firstnames.json', 'r')
		firstnames = json.loads(f.read())
	except:
		firstnames = get_firstnames(root_dir)
		f = open('firstnames.json', 'w')
		f.write(json.dumps(firstnames))
	
	print 'fetching gender...\n'
	try:
		f = open('gender.json', 'r')
		gender = json.loads(f.read())
		firstnames = [x for x in firstnames if x not in [y['name'] for y in gender]]
		gender.extends(genderize(firstnames, user, password, servers))
	except:
		gender = genderize(firstnames, user, password, servers)
		
	f = open('gender.json', 'w')
	f.write(json.dumps(gender))
		
	move_images(root_dir, male_dir, female_dir, undetermined_dir, gender)
		

if __name__ == '__main__':
	main(user, password, servers, root_dir, male_dir, female_dir, undetermined_dir)
