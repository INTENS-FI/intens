Title: Running Simsvc on Azure
Author: Timo Korvola
Comment: This is a Multimarkdown document.

# Running Simsvc on Azure

## Getting started with Azure

- Get yourself an Azure account and a subscription.
- If using a company MS cloud account, get a Kerberos TGT so
  you don't have to type your password (`kinit` on Linux, should be
  automatic on Windows).
- Install the Azure CLI locally and log in (`az login`).  It starts
  your default web browser for logging in.  Hopefully it knows how to
  use Kerberos.
- You can manage Azure with the client (`az`) or with the [web
  portal](https://portal.azure.com/).
- To avoid Cobol fingers, note that `--name` can be abbreviated `-n`
  and `--resource-group` `-g` in `az`.

## Docker images

- Install Docker locally.
- Create a container registry (ACR).  It gets a public IP and DNS
  name, thus needs to be globally unique (most names in Azure only
  need to be unique within their resource group).  Our charts
  etc. assume it is `intens.azurecr.io`.
- Log in to ACR: `az acr login -n intens`.  Just the short name without
  `azurecr.io`.
- Build the simsvc base image by running `make` in the `server`
  directory.  Sorry, only Linux supported for now.
- Push to ACR (`docker push intens.azurecr.io/simsvc`).  This allows
  others to pull the image with `docker pull
  intens.azurecr.io/simsvc`, so they can build model images on it
  without having to build the base.
- Build a model image, e.g., by running `docker build --build-arg
  model=mpt.py -t intens.azurecr.io/simsvc-mpt models`.  Push to ACR.

## Cluster setup

- Install `kubectl` and Helm locally.
- Create a Kubernetes service (AKS).  This creates a new
  resource group for VMs etc. that the AKS manages: they won't be
  in the same resource group as the AKS itself.
- Point `kubectl` to the AKS with `az aks get-credentials -g group -n name`.
- Create a service account for Tiller (Helm back end).  See
  `helm-rbac.yaml` and the link therein.  Then install Tiller.
- [Arrange access][] from AKS to ACR.  If the simple role assignment
  does not work, use `etc/create-acr-sp.sh` to set up an
  authentication secret.  The secret also works from non-AKS
  Kubernetes clusters.
- Install nginx-ingress and cert-manager with `etc/install-stuff.sh`.
  [Get a domain dame][pubip] for the ingress server.  I find it easier
  to do that with the portal instead of the CLI: just find the public
  IP address in the cluster resource group (the one created by AKS)
  and choose Settings/Configuration.  The short domain name must be
  unique for the Azure region.  Here we assume that the FQDN is
  `intens.northeurope.cloudapp.azure.com`.  This and the ACR are the
  only public addresses in this whole setup.
- For now we have been playing certificate authority for ourselves.
  Set it up with `etc/make-sscert.sh` or set up a better (ACME)
  cert-manager cluster issuer.  Either name it `intens-issuer` os set
  `server.clusterIssuer` when installing the chart (ahead).
- Clients use basic HTTP authentication.  Set it up with
  `etc/make-htpasswd.sh`.  This creates a file with the password in
  plaintext (the htpasswd file only has a hash).  Copy the password
  to your `.netrc` (for the Python utilities) and model YAML files (for
  o4j_client).  The username is "intens".  Remember to use https to
  prevent password eavesdropping.
- Set up dynamic provisioning of work volumes.  See
  `aks/storage-rbac.yaml` and the link therein.  Note that storage account
  names must be globally unique.  Edit the storage account name in
  `aks/azure-sc.yaml` and apply with `kubectl`.
- You should now be able to deploy Simsvc instances with `helm install
  -n name charts/simsvc`.  See `charts/simsvc/values.xml` for
  parameters.  The release name is also the leading path component of
  URLs to the service (the host is the ingress service set up above).
- Use `helm delete --purge` to take down instances if you want to reuse
  the release names.

[Arrange access]: https://docs.microsoft.com/en-us/azure/container-registry/container-registry-auth-aks
[pubip]: https://docs.microsoft.com/en-us/azure/aks/ingress-tls
