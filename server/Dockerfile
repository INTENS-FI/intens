# The simulation service base image.
# Intended to be used from the Makefile.
# For Linux.

FROM daskdev/dask:latest

RUN conda install --yes flask flask-socketio \
    && conda install --yes -c conda-forge zodb eventlet

WORKDIR /tmp
ARG simsvc_whl
COPY dist/$simsvc_whl .
RUN pip install $simsvc_whl

WORKDIR /run
RUN chown nobody:nogroup .
USER nobody:nogroup
CMD ["python3", "-m", "simsvc"]
