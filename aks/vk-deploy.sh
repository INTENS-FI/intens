az network vnet create -g Intens2 -n intens2-vnet \
   --address-prefixes 10.0.0.0/8 --subnet-name intens2-vnet-aks \
   --subnet-prefix 10.240.0.0/16
az network vnet subnet create -g Intens2 --vnet-name intens2-vnet \
   -n intens2-vnet-aci --address-prefix 10.241.0.0/16

aks_subnet=`az network vnet subnet show -g Intens2 \
               --vnet-name intens2-vnet -n intens2-vnet-aks --query id -o tsv`

az aks create -g Intens2 -n vk-test --node-count 1 \
   --network-plugin azure --service-cidr 10.0.0.0/16 \
   --dns-service-ip 10.0.0.10 --docker-bridge-address 172.17.0.1/16 \
   --vnet-subnet-id "$aks_subnet"

az aks get-credentials -g Intens2 -n vk-test

...

sp=`az aks show -g Intens2 -n vk-test -o tsv \
       --query servicePrincipalProfile.clientId`
vnet=`az network vnet show -g Intens2 -n intens2-vnet --query id -o tsv`

az role assignment create --assignee "$sp" --scope "$vnet" \
   --role 'Network Contributor'

url=`kubectl config view -o json \
     | jq -er '.clusters[] | select(.name == "vk-test").cluster.server'`

helm install -n virtual-kubelet --set provider=azure \
     --set providers.azure.targetAKS=true \
     --set providers.azure.masterUri="$url" \
     --set providers.azure.vnet.enabled=true \
     --set providers.azure.vnet.subnetName=intens2-vnet-aci \
     --set providers.azure.vent.subnetCidr=10.241.0.0/16 \
     --set providers.azure.vnet.clusterCidr=10.240.0.0/16 \
     --set providers.azure.vnet.kubeDnsIp=10.0.0.10 \
     virtual-kubelet-latest.tgz
