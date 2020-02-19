Title: Converting Simulink models to FMUs
Author: Timo Korvola

# Converting Simulink models to FMUs

## Prerequisites

- Matlab, Simulink and Simulink Coder
- [Simulix][] and its requirements (Python 3, lxml, CMake and a C
  Compiler).
- It is simplest if the whole kit is on your target platform.  It is
  probably possible to run Simulink Coder on a different platform and
  transfer the zip file to the target platform for compilation with
  Simulix.  It might even work to cross-compile the C code outside the
  target platform.  Good luck if you want to try.

[Simulix]: https://github.com/Kvixen/Simulix

## Code generation options in Simulink

See [Simulix documentation][Simulix].  In addition:

- Interface / Shared code placement must be Auto.
- Interface / Code interface must be Nonreusable function.
- Optimization / Default parameter behaviour must usually be Inlined
  (name conflicts are likely with Tunable).
- Generate code only may be set.  Simulix compiles from C in any case.

## Interface

Ports seem to get exported automatically, although I have only tested
with outports.  The port name is used in the FMU; the optional
signal name seems to be ignored.  Muxed outputs appear as scalars
with an index (1-based) in brackets appended to the port name.

Scopes seem to get harmlessly ignored, probably other widgets as well.

For each parameter that should be visible in the FMU, open the model
explorer and create a new parameter in the model workspace (not base
workspace).  Set its storage class to `ExportedGlobal`.  It should
show up in the interface report when you build and end up in the FMU
with the name of the variable.

## Building & simulation

The Makefile here builds from Simulink (`.slx`) to FMU.  See its
beginning for parameters: you'll need to set at least `MODEL`, e.g.,
`make MODEL=demo/demo` (without the `.slx`).  Output files are placed
in the same directory as the input model.  Simulix produces version
2.0 cosimulation FMUs.

If you are working interactively in Simulink you can also build a zip
package from there (Ctrl-B) and run make afterwards to build from zip
to FMU.

For simulation I have used [FMPy][].  It is rather rudimentary and
somewhat buggy.  It is simple to install though, as its dependencies
are few and readily available.

[FMPy]: https://github.com/CATIA-Systems/FMPy

## FMI Toolbox from Modelon

The commercially licensed FMI Toolbox from Modelon can be used as an
alternative to Simulix.  You will also need its Coder add-on.  I had
version 2.7 of the toolbox.  There are some differences from Simulix.

- There are Coder targets for different types of FMUs.  I have mostly
  used fmu_cs2.tlc, which is co-simulation, FMI version 2.
- "Generate code only" should be unset, having Coder invoke the
  compiler.  The generated build system is hairy; you don't want to
  touch it yourself.  Thus Matlab must be running on the target
  platform.
- I had to patch Modelon's makefile template because it passed
  `rt_nonfinite.o` to the linker twice.  I removed it from
  `OTHER_SRC`.
- The correct storage class for parameters appears to be "Model
  default".  If you use `ExportedGlobal` as with Simulix, an error
  message tells you to change it, but the suggested replacement does
  not exist.
- I had to unset FMU Export / Structured names for parameters.  When
  set it caused an internal error in the TLC definition.
