#!/bin/sh
# Create a self-signed CA certificate and install as Kubernetes secret.
# Create a cert-manager cluster issuer that uses the new certificate.
# The private key and certificate are also stored in local files.
# There is no passphrase on the private key.
# If the private key or the certificate file already exist, they are
# not recreated.

# Certificate subject
subj="/CN=Intens/O=VTT"
# Name of the secret, also base name of generated files
sname=intens-cacert
# Name of the cluster issuer
ciname=intens-issuer

set -e
umask 77

if [ -f ${sname}.key ]
then echo Using existing private key.
else openssl genrsa -out ${sname}.key 2048
fi

if [ ${sname}.pem -nt ${sname}.key ]
then echo Using existing certificate.
else openssl req -x509 -nodes -key ${sname}.key \
             -out ${sname}.pem -reqexts v3_req -extensions v3_ca -subj "$subj"
fi

kubectl create secret tls $sname --key ${sname}.key --cert ${sname}.pem

kubectl apply -f - <<@end
apiVersion: certmanager.k8s.io/v1alpha1
kind: ClusterIssuer
metadata:
  name: $ciname
spec:
  ca:
    secretName: $sname
@end
