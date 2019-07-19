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
  for Helm 2 on OpenShift.  Helm 3 is simpler because it does not
  require anything on the cluster (tiller is gone).

## Tweaking the cluster & apps

- Unless the Docker registry is public, Kubernetes and thus Helm
  cannot pull from it directly.  However, it can pull from image
  streams, which OpenShift automatically creates when you push to the
  integrated registry.  It appears necessary to run `oc set
  image-lookup`.  After that `image: <stream name>:<tag>` appears to
  work in container specs.  You can use `is` short for `imagestream`
  in commands, e.g., `oc get is`.
- OpenShift [does not run containers as root][img-guide].  It uses a
  generated non-zero UID, which cannot be referenced from Dockerfile.
  File permissions can be arranged via GID, which is always zero
  (root group).  To do this, build the Simsvc base image with
  `make SIMSVC_USER=nobody:0 PERM=ug+rwx` in the `server` directory.
- The Helm charts `stable/nginx-ingress` and `stable/cert-manager`
  don't seem to work.  However, OpenShift has some of their
  functionality built in, albeit with a different API (route instead
  of ingress).  Notably absent are [path][rewrite1]
  [rewriting][rewrite2] and [HTTP authentication][auth].  Simsvc
  has been modified to work without path rewriting but still does not
  do authentication.  There is only IP address whitelisting for now
  (`server.whitelist` in the values file).

[img-guide]: https://docs.openshift.com/container-platform/3.11/creating_images/guidelines.html
[rewrite1]: https://github.com/openshift/origin/issues/19501
[rewrite2]: https://github.com/openshift/origin/issues/20474
[auth]: https://github.com/openshift/origin/issues/20324
