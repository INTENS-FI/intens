# Makefile for simsvc Docker base image generation
# This image contains simsvc but no model, thus is not directly runnable.
# It is intended as a base for runnable images that add a model.

PYTHON = python3
BASE = daskdev/dask
IMAGE = simsvc
SIMSVC_USER = nobody:nogroup
PERM = u+rwx

VERSION := $(shell $(PYTHON) setup.py --version)
WHEEL = Simsvc-$(VERSION)-py3-none-any.whl

.PHONY: image wheel clean

image: wheel
	docker build $(DOCKERFLAGS) -t $(IMAGE) \
		--build-arg base=$(BASE) --build-arg simsvc_whl=$(WHEEL) \
		--build-arg user=$(SIMSVC_USER) --build-arg perm=$(PERM) .

wheel: dist/$(WHEEL)

clean:
	$(PYTHON) setup.py clean

dist/$(WHEEL): setup.py simsvc/*
	$(PYTHON) setup.py bdist_wheel
