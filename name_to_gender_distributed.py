import sys
import os
import subprocess
import json
import shutil
import re
from settings import user, password, servers, root_dir, male_dir, female_dir, undetermined_dir

def remote_ssh_cmd(user, password, server, command):
    ssh_cmd = 'sshpass -p %s ssh -o StrictHostKeyChecking=no %s@%s %s' % (password, user, server, command)
    print ssh_cmd
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
    try:
        with open('genderize.log', 'r') as f:
            for line in f.readlines():
                gender.extend(json.loads(line))
            firstnames = [x for x in firstnames if x not in [y['name'] for y in gender]]
    except:
        pass

    for server in servers:
        print 'using server: %s\n' % server
        quota = 1 # probe the real quota
        while len(firstnames) > 1:
            #get the batch of names to process
            names_batch = firstnames[0: min(quota, max_num_names, len(firstnames))]

            # prepare the command
            param = r'\&'.join([r'name[]=%s' % x for x in names_batch])
            print 'fetching %d names...' % len(names_batch)
            ssh_cmd = r"curl -gv \'https://api.genderize.io?%s\'" % param

            # execute remote command
            stdout, stderr = remote_ssh_cmd(user, password, server, ssh_cmd)
            #print 'stdout: %s' % stdout
            #print 'stderr: %s' % stderr

            try:
                # parse the result
                result = json.loads(stdout[0])
                if type(result) is not list:
                    result = [result, ]
            except:
                raise Exception('remote execution error:\nstdout: %s\nstderr: %s' % (stdout,stderr))

            #check if exceed quota
            if 'error' in result[0]:
                print 'exceeds quota!'
                break # exceeds quota

            # store result
            gender.extend(result)
            with open('genderize.log', 'a') as f:
                f.write('%s\n' % json.dumps(result))
            print 'fetched %d results! ' % len(result)

            # update firstnames
            firstnames = [x for x in firstnames if x not in [y['name'] for y in result]]
            print '%d firstnames to go...' % len(firstnames)

            # update quota
            pattern = r".*X-Rate-Limit-Remaining:\s(\d*).*"
            r = re.compile(pattern)
            quota_str = filter(r.match, stderr)[0]
            m = r.search(quota_str)
            quota = int(m.group(1))
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
        with open('firstnames.json', 'r') as f:
            firstnames = json.loads(f.read())
    except:
        firstnames = get_firstnames(root_dir)
        with open('firstnames.json', 'w') as f:
            f.write(json.dumps(firstnames))

    print 'fetching gender...\n'
    try:
        f = open('gender.json', 'r')
        gender = json.loads(f.read())
        firstnames = [x for x in firstnames if x not in [y['name'] for y in gender]]
        gender.extend(genderize(firstnames, user, password, servers))
    except:
        gender = genderize(firstnames, user, password, servers)

    with open('gender.json', 'w') as f:
        f.write(json.dumps(gender))

    move_images(root_dir, male_dir, female_dir, undetermined_dir, gender)


if __name__ == '__main__':
    main(user, password, servers, root_dir, male_dir, female_dir, undetermined_dir)
