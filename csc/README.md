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
- The orchestration system is OpenShift, Red Hat's extension of
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

## Tweaking the cluster

- Unless the Docker registry is public, Kubernetes cannot pull
  (although `oc run-app` can).  This breaks Helm.  To fix:
    ```
    kubectl create secret docker-registry intens-reg \
        --docker-server=docker-registry.rahti.csc.fi --docker-username=unused \
        --docker-password=<token from registry console>
    kubectl patch sa default -p '{"imagePullSecrets": [{"name": "intens-reg"}]}'
    ```
- The Helm charts `stable/nginx-ingress` and `stable/cert-manager`
  don't seem to work.  On the other hand Openshift should have their
  functionality built in, albeit with a different API (route
  instead of ingress).
