#!/bin/sh
set -e

helm install --name ingress stable/nginx-ingress
helm install --name cert-man stable/cert-manager
