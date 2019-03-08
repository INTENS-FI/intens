# Needed to get K8s dashboard working on AKS.

kubectl create clusterrolebinding kubernetes-dashboard -n kube-system \
        --clusterrole=cluster-admin \
        --serviceaccount=kube-system:kubernetes-dashboard
