#!/bin/sh

# Delete all untagged images from ACR.
# https://docs.microsoft.com/en-us/azure/container-registry/container-registry-delete#delete-untagged-images

reg=intens

for repo in `az acr repository list -n $reg -o tsv`
do  echo "Pruning $repo..."
    for img in `az acr repository show-manifests -n $reg --repository "$repo" \
                   --query '[?tags == []].digest' -o tsv`
    do  echo "$repo@$img"
        az acr repository delete -n $reg --image "$repo@$img" --yes
    done
done
