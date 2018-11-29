#!/bin/sh
# Create a service principal with read access to an Azure container registry
# and a Kubernetes secret for it.  Patch the default service account to use
# the secret.  Also creates a JSON file with sp data, including
# password (which is why we set umask 77).
#
# If the JSON file already exists, it is assumed that so does the sp on Azure.
# Then we do not create a sp, just configure Kubernetes with data from
# the file.
#
# This allows ACR access for non-AKS clusters, e.g., Minikube.  With AKS
# it suffices to assign a role to the cluster sp; no password needed.
# https://docs.microsoft.com/en-us/azure/container-registry/container-registry-auth-aks
# However, currently that does not work with Virtual Kubelet.  Until that
# is resolved, this script should serve as a workaround.
# https://github.com/virtual-kubelet/virtual-kubelet/issues/192

# Registry name without .azurecr.io.
crname=intens
spname=${crname}-acr-sp

set -e
umask 77

if [ -f ${spname}.json ]
then echo Reading service principal data from ${spname}.json.
else echo Creating new service principal, saving into ${spname}.json.
     acr_id=`az acr show -n $crname --query id -o tsv`
     az ad sp create-for-rbac --name $spname --role Reader \
        --scopes "$acr_id" > ${spname}.json
fi
spid=`jq -er .appId ${spname}.json`
pw=`jq -er .password ${spname}.json`

kubectl create secret docker-registry $spname \
    --docker-server ${crname}.azurecr.io --docker-email Timo.Korvola@vtt.fi \
    --docker-username "$spid" --docker-password "$pw"
kubectl patch serviceaccount default -p \
    '{"imagePullSecrets": [{"name": "'$spname'"}]}'
