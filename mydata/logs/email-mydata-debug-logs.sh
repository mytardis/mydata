#!/bin/bash

# This file, used by MyData, lives in
# /root/cron/email-mydata-debug-logs.sh
# on cvl.massive.org.au
# Running crontab -l as root gives:
# */5 * * * * /root/cron/email-mydata-debug-logs.sh

find /opt/mydata_debug_logs/ -type f -mmin -5 | while read filename
do
    # recipients="store.star.help@monash.edu"
    recipients="james.wettenhall@monash.edu"
    sender=$( grep Email: $filename | sed 's/Email://' )
    export REPLYTO="$sender"
    export EMAIL="$sender"
    mutt -s "[MyData Debug Log] $filename" $recipients < $filename
    echo "$(date): Sent MyData debug log $sender $recipients $filename" >> mydata_email.log
done
