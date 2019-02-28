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
USER root:root
COPY --from=build-stage /mcr /mcr
# MCR dynamically loads libXt at run-time (even if the app does no graphics).
RUN apt-get update && apt-get install -y libxt6
ARG ver
# No idea what the second var is, but it seems to be required.
ENV MCR=/mcr/$ver MCR_CACHE_ROOT=/tmp/mcr-cache

USER $SIMSVC_USER
