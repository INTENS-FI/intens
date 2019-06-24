# Notes on using Simulix

## Code generation options

See [Simulix documentation](https://github.com/Kvixen/Simulix).  In addition:

- Interface / Shared code placement must be Auto.
- Interface / Code interface must be Nonreusable function.
- Optimization / Default parameter behaviour must usually be Inlined
  (name conflicts are likely with Tunable).
- Generate code only may be set.  Simulix compiles from C in any case.

## Parameters

For each parameter that should be visible in the FMU, create a model
workspace variable with value `Simulink.Parameter(`x`)` where x is the
default value.  Set its storage class to `ExportedGlobal`.  It should
show up in the interface report when you build and end up in the FMU
with the name of the variable.
