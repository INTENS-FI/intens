# Build a Simsvc base image with FMI support.
# Just add FMU and Dask configuration to /app in a derived image.
# Optionally also add /app/model/custom.py.

ARG base=simsvc
FROM $base

WORKDIR /app
USER root
RUN conda install --yes -c conda-forge fmpy
COPY *.py model/
ENV PYTHONPATH=/app:$PYTHONPATH DASK_CONFIG=/app

USER $SIMSVC_USER
