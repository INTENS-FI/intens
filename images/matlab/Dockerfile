# Intermediate image for Simsvc with Matlab runtime.
# Build-arg base is Simsvc base image, mcr is Matlab runtime zip package,
# ver is the subdirectory where its installer actually installs: we
# tell it to install in /mcr but it installs in /mcr/$ver.
# Env. var. MCR will be set to /mcr/$ver.

ARG base
ARG build_base=$base
FROM $build_base AS build-stage

USER root:root
ARG mcr
RUN apt-get update && apt-get install -y unzip
COPY $mcr /$mcr
RUN mkdir /mcr-tmp && cd /mcr-tmp && unzip -q "/$mcr" \
    && ./install -mode silent -agreeToLicense yes -destinationFolder /mcr; \
    cd / && rm -rf "/$mcr" /mcr-tmp

FROM $base
COPY --from=build-stage /mcr /mcr
ARG ver
ENV MCR=/mcr/$ver
