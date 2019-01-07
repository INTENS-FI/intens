# The simulation service base image for Linux.
# Intended to be used from the Makefile.
# Installs simsvc from a wheel in dist.
# Build-arg simsvc_whl is the wheel file name without path.
# The server listens at build-arg port, default 8080.
# Derived images should leave WORKDIR as /run and USER as $SIMSVC_USER

FROM daskdev/dask:latest

RUN conda install --yes flask flask-socketio \
    && conda install --yes -c conda-forge zodb zodburi eventlet

WORKDIR /tmp
ARG simsvc_whl
COPY dist/$simsvc_whl .
RUN pip install $simsvc_whl && rm $simsvc_whl

WORKDIR /run
ARG port=8080
ENV SIMSVC_USER=nobody:nogroup \
    WORK_DIR=/work \
    JOB_DB=file:///db/simsvc.fs \
    SIMSVC_ADDR=:$port
RUN mkdir -p /work /db && chown $SIMSVC_USER /work /db .
USER $SIMSVC_USER
CMD ["python3", "-m", "simsvc"]
EXPOSE $port
