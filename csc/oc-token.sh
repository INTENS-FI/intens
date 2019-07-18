#!/bin/sh -e
# Set up an image pull secret using the OpenShift access token.
# This appears necessary for using Helm on rahti.csc.fi.
# The token changes frequently, forcing you to run this again.

sname=rahti-reg
reg=docker-registry.rahti.csc.fi
sa=default

oc delete secret $sname || echo "Never mind that."
oc create secret docker-registry $sname --docker-server=$reg \
    --docker-username=unused --docker-password="`oc whoami -t`"
oc secrets link --for=pull $sa $sname
