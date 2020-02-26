Title: Running Simsvc at CSC
Author: Timo Korvola
Comment: This is a Multimarkdown document.

# Running Simsvc at CSC

## Getting started at Rahti

- Install Docker locally.
- The CSC container service is called Rahti.  Instructions for getting
  started and links to its web portals are
  [here](https://rahti.csc.fi).  The user experience is a bit
  disjointed because CSC have quite a few web portals; even Rahti has
  two.  The instructions have links to the right web portals for each step.
- The orchestration system is OpenShift, Red Hat's variant of
  Kubernetes.  Install [its
  client](https://github.com/openshift/origin/releases).  Note that
  the two binaries are identical; on Linux, copy `oc` to
  `/usr/local/bin`, symlink it to `kubectl` and remove any non-oc
  version of `kubectl`.  On Windows `kubectl` comes with Docker.
  Maybe just copy `oc.exe` somewhere on `PATH` and hope that the Docker
  version of `kubectl` works.
- Log in to the [registry console][].  Run `csc/rahti-login.sh`
  with the access token.  It logs you in with `oc` and `docker`,
  essentially equivalent to the login commands shown on the page.
  The token changes periodically: repeat as necessary.
- Install Helm.  It is [a bit
  complicated](https://blog.openshift.com/getting-started-helm-openshift/)
  for Helm 2 on OpenShift.  Helm 3 is simpler because it does not
  require anything on the cluster (no Tiller).
- For interactive bliss, add this to `.zshrc` or `.bashrc` (replacing
  `zsh` with `bash`, obviously):
    ```
    . <(kubectl completion zsh)
    . <(helm completion zsh)
    . <(oc completion zsh)
    ```
- Create an OpenShift project or several for your work.  These are
  similar to Kubernetes namespaces but are generally used more for
  organizing cluster objects: e.g., you can easily delete a project
  and everything in it.

## Docker images

- OpenShift clusters have an integrated Docker registry.  For Rahti
  it is `docker-registry.rahti.csc.fi`.
- Build the Simsvc base image with `make SIMSVC_USER=nobody:0
  PERM=ug+rwx` in the `server` directory.  OpenShift [does not run
  containers as root][img-guide].  It uses a generated non-zero UID,
  which cannot be referenced from Dockerfile.  File permissions can be
  arranged via GID, which is always zero (root group).
- Build model images from that base, e.g., by running `docker build
  --build-arg model=mpt.py -t simsvc-mpt models`.  [Tag appropriately
  and push to Rahti][registry console].
- Unless the Docker registry is public, Kubernetes and thus Helm
  cannot pull from it directly.  However, they can pull image
  streams, which OpenShift creates automatically when you push to the
  integrated registry.  It appears necessary to run `oc set
  image-lookup`, probably whenever a new image stream has been
  created.  After that `image: <stream name>:<tag>` appears to
  work in container specs.  You can use `is` short for `imagestream`
  in commands, e.g., `oc get is`.
  
## OpenShift peculiarities

- The Helm charts `stable/nginx-ingress` and `stable/cert-manager`
  don't seem to work.  However, OpenShift has some of their
  functionality built in, albeit with a different API (route instead
  of ingress).  Notably absent are [path][rewrite1]
  [rewriting][rewrite2] and [HTTP authentication][auth].  Simsvc
  has been modified to work without path rewriting.
- If you use service DNS names under `rahtiapp.fi` and TLS edge
  termination, [you don't need to worry about certificate
  management][sec-routes].
- You can optionally [whitelist][] IP addresses.
- Simsvc has also been modified to support HTTP basic authentication.
  It uses the same secret as the old `nginx-ingress` setup.  Set it up
  with `etc/make-htpasswd.sh`.  Copy the generated password from
  `etc/intens-pw.txt` to wherever necessary, typically `.netrc` and
  model YAML files.  Note that if the password file exists when you
  run the script, the password is reused instead of generating a new one.
  The username is `intens`.
- With edge TLS termination, the password is transmitted in cleartext
  over the internal cluster network.  At least use https to encrypt it
  on the Internet.
- Dynamic provisioning of persistent volumes seems to work without any
  particular configuration.  Just use the default storage class. 
- You should now be able to deploy Simsvc instances with `helm install
  -n name charts/simsvc`.  Leave out `-n` if using Helm 3.  See
  `charts/simsvc/values.xml` for parameters.  The release name is also
  the leading path component of service URLs.  Remember to use image
  stream names for pulling from the integrated registry.
- With Helm 2, use `helm delete --purge` to take down instances if you
  want to reuse the release names.  Helm 3 does not have or need the
  `--purge` option.

[registry console]: https://registry-console.rahti.csc.fi/registry
[img-guide]: https://docs.openshift.com/container-platform/3.11/creating_images/guidelines.html
[rewrite1]: https://github.com/openshift/origin/issues/19501
[rewrite2]: https://github.com/openshift/origin/issues/20474
[auth]: https://github.com/openshift/origin/issues/20324
[sec-routes]: https://docs.csc.fi/cloud/rahti/usage/security-guide/#securing-routes
[whitelist]: https://docs.csc.fi/cloud/rahti/tutorials/elemental_tutorial/#route
