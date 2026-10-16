#!/usr/bin/env bash
# Source this from cross-build entrypoints after activating host build tools.
# Conda's host x86_64 -L, rpath, includes, and compiler overrides must never
# leak into clang --target=aarch64-linux-gnu or CMake's ARM64 sysroot.
# Keep PATH and CONDA_PREFIX: Mesa's shader generators run natively on host.
unset CFLAGS CXXFLAGS CPPFLAGS LDFLAGS
unset CPATH C_INCLUDE_PATH CPLUS_INCLUDE_PATH OBJC_INCLUDE_PATH
unset LIBRARY_PATH LD_RUN_PATH
unset CMAKE_PREFIX_PATH CMAKE_LIBRARY_PATH CMAKE_INCLUDE_PATH
unset CC CXX FC F77 F90 AR RANLIB
unset PKG_CONFIG_PATH PKG_CONFIG_LIBDIR PKG_CONFIG_SYSROOT_DIR
unset PKG_CONFIG_ALLOW_SYSTEM_CFLAGS PKG_CONFIG_ALLOW_SYSTEM_LIBS
