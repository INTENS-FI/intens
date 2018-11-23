#!/bin/sh
# Create a self-signed certificate and install as Kubernetes secret intens-tls.
# Args are common name (CN) and organisation (O) for the cert.  The private key
# and cert are stored in local files intens-tls.{key,pem}.  There is no
# passphrase on the private key.

name=intens-tls

set -e
umask 77

openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout ${name}.key -out ${name}.pem \
    -reqexts v3_req -extensions v3_ca -subj "/CN=$1/O=$2"

kubectl create secret tls $name --key ${name}.key --cert ${name}.pem
