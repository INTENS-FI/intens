# Intermediate image for Simsvc with Matlab runtime.
# Build-arg base is Simsvc base image, mcr is Matlab runtime zip package.
# Env. var. MCR will be set to the location of the installed runtime
# (currently /mcr).

ARG base
ARG build_base=$base
FROM $build_base AS build-stage

USER root:root
ARG mcr
WORKDIR /mcr
RUN apt-get update && apt-get install -y unzip
COPY $mcr /
RUN unzip /$mcr

FROM $base
COPY --from=build-stage /mcr /mcr
ENV MCR=$mcr
