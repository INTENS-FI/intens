# Build a model image
# Pass the model as build-arg model.  Can be a module or a package.

ARG base=simsvc
FROM $base

WORKDIR /app
USER root
ARG model
COPY $model model/
RUN mdl=`basename $model`; \
    if [ -z "${mdl%%*.py}" ]; \
    then mv "model/$mdl" model.py; \
         rmdir model; \
    fi
ENV PYTHONPATH=/app:$PYTHONPATH

# Contrary to the docs, USER does not affect CMD or ENTRYPOINT that follows it.
# Instead, as one might surmise, the last USER command defines who the
# image runs as.  I haven't tested but suspect it is the same with WORKDIR.
USER $SIMSVC_USER
WORKDIR /run
