# Build a FMU from a Simulink model with Simulink Coder and Simulix.
# For GNU Make.  Code generation options have to be configured in
# Simulink - they are saved in the model file - as described in
# https://github.com/Kvixen/Simulix and README.md.

# Simulink model file without extension (.slx).
# Can have a path though.
MODEL = model

# Matlab executable and flags
MAT = matlab
MATFLAGS =

# Setup Matlab script.  If provided, executed before code generation using
# the Matlab run function.  In particular, Matlab temporarily changes to
# the directory of the script for its execution.
MAT_SETUP =

# Simulix executable and flags.
SIMULIX = python3 $(HOME)/src/Simulix/Simulix.py
SXFLAGS =

# Should not need to modify below.

CLEANDIRS = %_grt_rtw %_fmu
CLEANFILES = % %.zip %.fmu

.PHONY: all clean
.SECONDARY: $(MODEL:%=%.zip)

all: $(MODEL:%=%.fmu)

clean:
	rm -rf $(addsuffix slprj, $(dir $(MODEL)))
	rm -rf $(foreach d, $(CLEANDIRS), $(MODEL:%=$d))
	rm -f $(foreach f, $(CLEANFILES), $(MODEL:%=$f))

%.fmu: %.zip
	mkdir -p $*_fmu
	$(SIMULIX) $(SXFLAGS) -p $*_fmu $*
	mv $*_fmu/$(@F) $@

%.zip: %.slx $(MAT_SETUP) build_rtw.m
	MAT_SETUP="$(MAT_SETUP)" SL_MODEL="$*" \
		$(MAT) $(MATFLAGS) -batch build_rtw
