#!/bin/sh -e
# Set up an image pull secret using the OpenShift access token.  This
# lets Kubernetes pull from the registry directly.  The token changes
# frequently, forcing you to run this again.
#
# On OpenShift it seems you don't need this for pulling image streams
# created by pushing to the integrated registry.  However, if you want
# to access that registry from an external Kubernetes cluster, e.g.,
# Minikube, this should help.

sname=rahti-reg
reg=docker-registry.rahti.csc.fi
sa=default
occontext=/rahti-csc-fi:8443/korvolat

kubectl delete secret $sname || echo "Never mind that."
kubectl create secret docker-registry $sname --docker-server=$reg \
        --docker-username=unused \
        --docker-password="`oc whoami -t --context=$occontext`"
kubectl patch sa $sa -p '{"imagePullSecrets": [{"name": "'$sname'"}]}'
