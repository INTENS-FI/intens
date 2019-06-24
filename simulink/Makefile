# Build a FMU from a Simulink model with Simulink Coder and Simulix.
# For GNU Make.  Code generation options have to be configured in
# Simulink - they are saved in the model file - as described in
# https://github.com/Kvixen/Simulix and README.md.

# Simulink model files without extension (.slx).
MODEL = model

# Matlab executable and flags
MAT = matlab
MATFLAGS = 

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

%.zip: %.slx build_rtw.m
	SL_MODEL="$*" $(MAT) $(MATFLAGS) -batch build_rtw
