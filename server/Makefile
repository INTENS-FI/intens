# Makefile for simsvc Docker base image generation
# This image contains simsvc but no model, thus is not directly runnable.
# It is intended as a base for runnable images that add a model.

PYTHON=python3
WHEEL=Simsvc-0.2-py3-none-any.whl
IMAGE=intens.azurecr.io/simsvc

.PHONY: build

build: dist/$(WHEEL)
	docker build $(DOCKERFLAGS) -t $(IMAGE) \
		--build-arg simsvc_whl=$(WHEEL) .

dist/$(WHEEL): setup.py simsvc/*
	$(PYTHON) setup.py bdist_wheel
