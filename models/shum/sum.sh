#!/bin/sh

echo "Hi! I'm Ed Winchester." > foo.log
echo "A word of warning" >& 2
# sleep 3600
expr "$1" + "$2"
