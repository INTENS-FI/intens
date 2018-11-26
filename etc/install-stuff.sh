#!/bin/sh
# On Minikube use "minikube addons enable ingress" instead.

set -e

helm install --name ingress stable/nginx-ingress
helm install --name cert-man stable/cert-manager
