#!/bin/sh -e
# Log in to Rahti with oc and docker.

usage() {
    echo "Usage: `basename $0` token."
    exit 1
}
[ $# -eq 1 ] || usage

oc login --token "$1" rahti.csc.fi:8443
docker login -p "$1" -u unused docker-registry.rahti.csc.fi
