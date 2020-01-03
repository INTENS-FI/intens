# Makefile for simsvc Docker base image generation
# This image contains simsvc but no model, thus is not directly runnable.
# It is intended as a base for runnable images that add a model.

PYTHON=python3
WHEEL=Simsvc-0.4-py3-none-any.whl
BASE=daskdev/dask
IMAGE=simsvc
SIMSVC_USER=nobody:nogroup
PERM=u+rwx

.PHONY: build clean

build: dist/$(WHEEL)
	docker build $(DOCKERFLAGS) -t $(IMAGE) \
		--build-arg base=$(BASE) --build-arg simsvc_whl=$(WHEEL) \
		--build-arg user=$(SIMSVC_USER) --build-arg perm=$(PERM) .

clean:
	$(PYTHON) setup.py clean

dist/$(WHEEL): setup.py simsvc/*
	$(PYTHON) setup.py bdist_wheel
