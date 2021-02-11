# The simulation service base image for Linux.
# Intended to be used from the Makefile.
# Installs simsvc from a wheel in dist.
# Build-arg simsvc_whl is the wheel file name without path.
# The server runs as build-arg user, default nobody:nogroup,
# and listens at build-arg port, default 8080.
# Build arg base is the base image, which must have conda.
# Build arg perm is passed to chmod for setting permissions of writable
# directories, default is u+rwx.
# Derived images should leave WORKDIR as /apprun and USER as $SIMSVC_USER.

ARG base=daskdev/dask
FROM $base

WORKDIR /tmp
ARG simsvc_whl
COPY dist/$simsvc_whl .
RUN pip install dask-kubernetes $simsvc_whl && rm $simsvc_whl

WORKDIR /apprun
ARG user=nobody:nogroup
ARG perm=u+rwx
ARG port=8080
ARG dbdir=/db
ENV SIMSVC_USER=$user \
    JOB_DB=file://$dbdir/simsvc.fs \
    WORK_DIR=/work \
    SIMSVC_ADDR=:$port
RUN mkdir -p $WORK_DIR $dbdir \
    && chown $SIMSVC_USER $WORK_DIR $dbdir . \
    && chmod $perm $WORK_DIR $dbdir .
USER $SIMSVC_USER
CMD ["python3", "-m", "simsvc"]
EXPOSE $port
