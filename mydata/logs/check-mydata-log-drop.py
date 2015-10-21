#!/usr/bin/python
"""
Installed in /root/cron/check-mydata-log-drop.py on Store.Monash-Test

Checks for evidence that MyData's debug log submission system is broken,
and emails an alert if necessary.

To avoid raising multiple helpdesk tickets for the same issue, the status
('OK' or 'WARN') is saved in '/root/cron/mydata-log-drop-status' and a
helpdesk ticket is only created (via email) if the status changes from
'OK' to 'WARN'.

This script is scheduled in root's crontab to run every 5 minutes:
*/5 * * * * /root/cron/check-mydata-log-drop.py

If the status ('OK' or 'WARN') does not change, then this script
generates no output.  If it does change, then the script writes
to stdout, which (if cron is configured correctly) will generate
an email to the server admin.
"""

# pylint: disable=invalid-name

import requests
import sys

r = requests.get('https://cvl.massive.org.au/cgi-bin/mydata_log_drop.py')
status_code = r.status_code
r.close()
# Success: status_code == 200
# Failure: status_code == 404 (or anything else)

if status_code == 200:
    status = 'OK'
else:
    status = 'WARN'

with open('/root/cron/mydata-log-drop-status', 'r') as mydata_log_drop_status:
    status_on_disk = mydata_log_drop_status.read().strip('\n')

if status == status_on_disk:
    sys.exit(0)

print "Changing mydata log drop status on disk from %s to %s" \
    % (status_on_disk, status)
with open('/root/cron/mydata-log-drop-status', 'w') as mydata_log_drop_status:
    mydata_log_drop_status.write(status)

import smtplib
from email.mime.text import MIMEText

fromaddr = 'server.admin@example.com'
toaddrs = 'helpdesk@example.com'

msg = "Received HTTP %d while trying to reach " \
    "https://cvl.massive.org.au/cgi-bin/mydata_log_drop.py" % status_code
msg += "\n\n"

msg = MIMEText(msg)
if status == 'WARN':
    msg['Subject'] = '[Store.Monash-Test] MyData log drop unavailable?'
else:
    msg['Subject'] = '[Store.Monash-Test] MyData log drop available again'
    print "Not raising ticket for MyData log drop recovery."
    sys.exit(0)
msg['From'] = fromaddr
msg['To'] = toaddrs

username = 'email.account@example.com'
password = '................'

server = smtplib.SMTP('smtp.gmail.com:587')
server.starttls()
server.login(username, password)
print "Sending email."
server.sendmail(fromaddr, toaddrs, msg.as_string())
server.quit()
