# Makefile for building a simsvc-matlab image.
# This is an itermediate image for running Matlab models in Simsvc.

BASE = intens.azurecr.io/simsvc
IMAGE = intens.azurecr.io/simsvc-matlab

.PHONY: all build

all: build

# This downloads the Matlab runtime if you don't have it, which
# requires Matlab and possibly a very long time.  You can link a
# selected runtime to mcr.zip manually instead.  Symlinks don't work
# here, so hard link or copy.  That lets you build for any version of
# Matlab as long as you have the runtime package.
mcr.zip:
	ln "`matlab -nodesktop -r get_mcr \
		| sed -n 's/^Installer: //p'`" $@

build: mcr.zip
	docker build $(DOCKERFLAGS) -t $(IMAGE) --build-arg base=$(BASE) \
		--build-arg mcr=mcr.zip .
