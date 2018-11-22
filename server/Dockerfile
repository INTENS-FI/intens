# The simulation service base image for Linux.
# Intended to be used from the Makefile.
# Installs simsvc from a wheel in dist.
# Build-arg simsvc_whl is the wheel file name without path.
# The server listens at build-arg port, default 8080.
# Derived images should leave WORKDIR as /run and USER as $SIMSVC_USER

FROM daskdev/dask:latest

RUN conda install --yes flask flask-socketio \
    && conda install --yes -c conda-forge zodb eventlet

WORKDIR /tmp
ARG simsvc_whl
COPY dist/$simsvc_whl .
RUN pip install $simsvc_whl && rm $simsvc_whl

WORKDIR /work
ENV SIMSVC_USER=nobody:nogroup
RUN chown $SIMSVC_USER .
ENV WORK_DIR=/work

WORKDIR /run
RUN chown $SIMSVC_USER .
USER $SIMSVC_USER
ARG port=8080
ENV SIMSVC_ADDR=:$port
CMD ["python3", "-m", "simsvc"]
EXPOSE $port
