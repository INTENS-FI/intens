#!/bin/sh
# Generate a random password, a htpasswd file and a Kubernetes secret.

user=intens
secret=intens-pw
pwfile=${secret}.txt
sfile=${secret}.htpasswd

set -e
umask 77

if [ -f $pwfile ]
then echo "Using old password from $pwfile"
else echo "Generating new password into $pwfile"
     pwgen -s 64 1 > $pwfile
fi

htpasswd -ci $sfile $user < $pwfile
kubectl create secret generic $secret --from-file=auth=$sfile
