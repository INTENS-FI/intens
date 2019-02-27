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
- Create a Kubernetes service (AKS).  This creates a new resource
  group for VMs etc. that the AKS manages: they won't be in the same
  resource group as the AKS itself.  If you want to set up Virtual
  Kubelet to run pods on Azure Container Instances, it is easiest to
  use the "virtual node" feature of AKS, currently in preview.  Create
  your AKS in a region where the feature is available (currently West
  Europe, among others) and enable it.  That will force "advanced
  networking" to be enabled as well, and will create a virtual net or
  use an existing one, as you choose.  Ordinary nodes will be on one
  subnet of the vnet and ACI pods in another.
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
  `intens.westeurope.cloudapp.azure.com`.[^go west]
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
  `aks/storage-rbac.yaml` and the link therein.  The storage
  class definition is in `aks/azure-sc.yaml`.  Storage accounts
  are created automatically.[^sa-spam]  Volumes should be available at
  `//<account>.file.core.windows.net/<volume>`, but I haven't actually
  managed to mount them.  They can be browsed via the portal though.
- You should now be able to deploy Simsvc instances with `helm install
  -n name charts/simsvc`.  See `charts/simsvc/values.xml` for
  parameters.  The release name is also the leading path component of
  URLs to the service (the host is the ingress service set up above).
- Use `helm delete --purge` to take down instances if you want to reuse
  the release names.

[Arrange access]: https://docs.microsoft.com/en-us/azure/container-registry/container-registry-auth-aks
[pubip]: https://docs.microsoft.com/en-us/azure/aks/ingress-tls
[^go west]: Currently West Europe is a bit ahead of North Europe in
    terms of Azure features: Virtual Nodes are in preview for AKS and
    ACI has larger resource limits for Windows.
[^sa-spam]: Currently it seems to create more than one, likely a bug.

## Virtual Kubelet

- The easiest way to get VK working is to enable "virtual node" when
  creating the AKS.  That is a preview feature, not available in all regions.
- If you want to roll your own, it will be something along the lines
  in vk-deploy.sh.  See also the [VK ACI README][].
- The more widely available connector that is installed with `az aks
  install-connector` does not get the job done because we need the
  advanced networking (vnet).
- The "virtual node" feature only deploys a Linux connector.
  According to Microsoft [Windows support is planned][win-vnet].  When
  I tried to install VK manually with vnet support, it likewise only
  worked for Linux.
- DNS is currently broken on the ACI pods.  See `az-vk-values.yaml`
  for a fix.  The file contains values for our chart, e.g., `helm
  install -n mpt -f aks/az-vk-values.yaml charts/simsvc`.  That
  deploys the workers and the scheduler to ACI via VK.
- Unfortunately persistent volumes appear completely unsupported by
  VK.  `kubectl logs` also works funny.  Therefore we keep the web
  app on a regular node for now.
- Deletion of vnets created by "virtual node" is currently buggy.
  You need to [delete the service association link with az][del-vnet]
  until they fix that.  The rest can be deleted from the portal.

[VK ACI README]: https://github.com/virtual-kubelet/virtual-kubelet/blob/master/providers/azure/README.md
[win-vnet]: https://docs.microsoft.com/en-us/azure/container-instances/container-instances-vnet#preview-limitations
[del-vnet]: https://docs.microsoft.com/en-us/azure/container-instances/container-instances-vnet#delete-network-resources
