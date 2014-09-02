import subprocess
import sys

proc = subprocess.Popen('git log -1 --name-status', stdout=subprocess.PIPE,
                        stdin=subprocess.PIPE, stderr=subprocess.STDOUT,
                        shell=True, universal_newlines=True)
stdout, stderr = proc.communicate()

stdout = stdout.split('\n')[0].split()

assert stdout[0] == 'commit'
commit = stdout[1]

f = open('CommitDef.py', 'w')
f.write('LATEST_COMMIT = "' + commit + '"\n')
f.close()
