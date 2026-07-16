# libfive headless pipeline research and validation

Date: 2026-07-15

## Question

Can libfive / Studio be used as a headless pipeline here, and what setup is
required?

## Findings from upstream docs

libfive is a solid-modeling framework with several layers:

- a C++ kernel and C API;
- a standard library of shapes and CSG operations;
- optional Guile Scheme bindings;
- optional Python bindings;
- Studio, which is the GUI app.

The upstream README states that headless use is supported by building an
application on top of the Scheme bindings, and that Studio is optional rather
than required. It also lists the Linux dependencies for building libfive:
`cmake`, `pkg-config`, `libeigen3-dev`, `libpng-dev`, `libboost-all-dev`,
optional `guile-3.0-dev`, optional `qtbase5-dev`, and `python3`. Studio is
documented as requiring Guile or Python bindings plus Qt 5.12 or later.

Sources:

- [libfive home](https://libfive.com/)
- [libfive README](https://github.com/libfive/libfive)

## Local validation

Repository scan:

- no in-repo `libfive` integration points were present before this report;
- no existing setup script or pipeline target for libfive was found.

Toolchain check on this host:

- `python3`: present
- `cmake`: absent
- `pkg-config`: absent
- `guile`: absent
- Qt 5 Core via `pkg-config`: absent

This host also cannot complete package installation in-session because `sudo`
is not usable for package management here.

## Conclusion

libfive can support a headless pipeline, but only as a custom application built
on the kernel/bindings. Studio itself is a GUI app and is not the headless
interface.

This environment is not ready for a full install/test cycle until the missing
build dependencies are provisioned.

## Active-state note

This is documented research, not an active Monad backlog item. The repo's
live work should treat the libfive generation path as non-active until a new,
explicit implementation order is issued.

## Recommended next step

Provision a build-capable environment, then build the kernel plus the binding
set you actually want:

- kernel-only for a minimal CLI/service pipeline;
- kernel + Guile for the documented headless path;
- kernel + Python + Qt only if Studio is also desired.
