# Makefile for building a simsvc-matlab image.
# This is an itermediate image for running Matlab models in Simsvc.

# The Matlab runtime is huge, thus building takes some time and disk
# space.  While Simsvc is in active development it is better to build
# this on top of daskdev/dask and a simsvc image on top of this.  That
# way new simsvc-matlab images can be built quickly.  If Simsvc
# eventually attains a slower update cycle than Matlab, the order can
# be reversed.

BASE = daskdev/dask
IMAGE = dask-matlab

# A jq query on mcr.json for finding the subdirectory (of the requested
# installation directory) where MCR actually gets installed.  
MCR_SUBDIR = "v\(.major)\(.minor)"

.PHONY: all build

all: build

# This downloads the Matlab runtime if you don't have it, which
# requires Matlab and possibly a very long time.  If it has already
# been downloaded, Matlab won't do it again but only writes mcr.json.
# The rule does not run at all if mcr.json exists.  Thus you can also
# edit it manually.  That lets you build for any version of Matlab
# (e.g., build for Linux on Windows) as long as you have the runtime
# package.
mcr.json:
	matlab -nodesktop -r get_mcr

# Symlinks don't work for mcr.zip.
build: mcr.json Dockerfile
	ln -f "`jq -er .file $<`" mcr.zip
	ver=`jq -er '$(MCR_SUBDIR)' $<`; \
	docker build $(DOCKERFLAGS) -t $(IMAGE) --build-arg base=$(BASE) \
		--build-arg mcr=mcr.zip --build-arg ver="$$ver" .
	rm mcr.zip
