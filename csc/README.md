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
  (although `oc run-app` can).  This breaks Helm.  To fix, run
  `oc-token.sh` (after logging in with `oc login`).
  Unfortunately the token changes periodically, forcing you to
  run the script again.  It should be possible to fix this with
  RBAC instead of using a secret but I cannot get that to work.
- OpenShift [does not run containers as root][img-guide].  It uses a
  generated non-zero UID, which cannot be referenced from Dockerfile.
  File permissions can be arranged via GID, which is always zero
  (root group).
- The Helm charts `stable/nginx-ingress` and `stable/cert-manager`
  don't seem to work.  However, Openshift has some of their
  functionality built in, albeit with a different API (route instead
  of ingress).  Notably absent are [path][rewrite1]
  [rewriting][rewrite2] and [HTTP authentication][auth].

[img-guide]: https://docs.openshift.com/container-platform/3.11/creating_images/guidelines.html
[rewrite1]: https://github.com/openshift/origin/issues/19501
[rewrite2]: https://github.com/openshift/origin/issues/20474
[auth]: https://github.com/openshift/origin/issues/20324
