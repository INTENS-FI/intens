Title: Running Simsvc at CSC
Author: Timo Korvola
Comment: This is a Multimarkdown document.

# Running Simsvc at CSC

## Getting started at Rahti

- The CSC container service is called Rahti.  Instructions for getting
  started and links to its web portals are
  [here](https://rahti.csc.fi).  The user experience is a bit
  disjointed because CSC have quite a few web portals; even Rahti has
  two.  The instructions have links to the right web portals for each step.
- The orchestration system is OpenShift, Red Hat's variant of
  Kubernetes.  Install [its
  client](https://github.com/openshift/origin/releases).  Note that
  the two binaries are identical; copy `oc` to `/usr/local/bin` and
  symlink it to `kubectl`.  Remove any non-oc version of `kubectl`.
- Log in to the [registry
  console](https://registry-console.rahti.csc.fi/registry).  Run the
  docker and oc login commands with the access tokens.
- Install Helm.  It is [a bit
  complicated](https://blog.openshift.com/getting-started-helm-openshift/)
  on OpenShift.

## Tweaking the cluster & apps

- Unless the Docker registry is public, Kubernetes cannot pull
  (although `oc run-app` can).  This breaks Helm.  To fix:
    ```
    kubectl create secret docker-registry intens-reg \
        --docker-server=docker-registry.rahti.csc.fi --docker-username=unused \
        --docker-password=<token from registry console>
    kubectl patch sa default -p '{"imagePullSecrets": [{"name": "intens-reg"}]}'
    ```
- OpenShift [does not run containers as root or the user specified by
  the image][os-images].  It uses a generated non-zero UID, which
  cannot be referenced from Dockerfile.  File permissions must be
  arranged via GID, which is always zero (root group).
- The Helm charts `stable/nginx-ingress` and `stable/cert-manager`
  don't seem to work.  However, Openshift should have their
  functionality built in, albeit with a different API (route instead
  of ingress).

[os-images]: https://docs.openshift.com/container-platform/4.1/creating_images/guidelines.html
