#!/bin/sh -e
# Set up an image pull secret using the OpenShift access token.
# This lets Kubernetes pull from the registry directly.
# The token changes frequently, forcing you to run this again.
# It seems you don't need this for pulling image streams, thus it
# is likely best to use those instead.

sname=rahti-reg
reg=docker-registry.rahti.csc.fi
sa=default

oc delete secret $sname || echo "Never mind that."
oc create secret docker-registry $sname --docker-server=$reg \
    --docker-username=unused --docker-password="`oc whoami -t`"
oc secrets link --for=pull $sa $sname
