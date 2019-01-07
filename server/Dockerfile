# The simulation service base image for Linux.
# Intended to be used from the Makefile.
# Installs simsvc from a wheel in dist.
# Build-arg simsvc_whl is the wheel file name without path.
# The server runs as build-arg user, default nobody:nogroup,
# and listens at build-arg port, default 8080.
# Derived images should leave WORKDIR as /run and USER as $SIMSVC_USER.

FROM daskdev/dask:latest

RUN conda install --yes flask flask-socketio \
    && conda install --yes -c conda-forge zodb zodburi eventlet

WORKDIR /tmp
ARG simsvc_whl
COPY dist/$simsvc_whl .
RUN pip install $simsvc_whl && rm $simsvc_whl

WORKDIR /run
ARG user=nobody:nogroup
ARG port=8080
ENV SIMSVC_USER=$user \
    DB_DIR=/db
ENV JOB_DB=file://$DB_DIR/simsvc.fs \
    WORK_DIR=/work \
    SIMSVC_ADDR=:$port
RUN mkdir -p $WORK_DIR $DB_DIR && chown $SIMSVC_USER $WORK_DIR $DB_DIR .
USER $SIMSVC_USER
CMD ["python3", "-m", "simsvc"]
EXPOSE $port
