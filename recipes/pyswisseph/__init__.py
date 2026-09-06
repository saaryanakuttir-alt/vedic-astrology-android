"""
Custom python-for-android recipe for pyswisseph.

WHY THIS EXISTS: pyswisseph (the Swiss Ephemeris Python binding this whole
app's chart math depends on) has NO official recipe in python-for-android's
built-in recipe collection, so `buildozer`/`p4a` cannot cross-compile it for
Android out of the box. This recipe fills that gap.

pyswisseph's own setup.py is a plain distutils Extension build (it compiles
pyswisseph.c plus every .c file under its bundled libswe/ directory into one
C extension module) with no exotic build steps, so python-for-android's
generic `CompiledComponentsPythonRecipe` — which just runs the package's own
setup.py under the NDK cross-compilation toolchain p4a sets up — should be
sufficient. This has NOT been build-tested end-to-end in the environment
this project was developed in (that sandbox has no network access to the
Android NDK/SDK at all — see chart_engine/BUILD_FROM_SOURCE.md for the
parallel story with the desktop build). If the Android build fails inside
this recipe specifically, the likely fixes, roughly in order of likelihood:

  1. pyswisseph's setup.py probes for a system `pkg-config libswe` and only
     falls back to building its bundled libswe/ sources from scratch if that
     probe fails. Cross-compiling toolchains sometimes still have a *host*
     pkg-config on PATH that answers this probe incorrectly. If the build
     log shows it trying to link a host libswe, unset PKG_CONFIG_PATH (or
     point it somewhere empty) in get_recipe_env below.
  2. libswe's C code uses some standard-but-not-always-present headers/
     functions (e.g. can assume a filesystem layout for its default
     ephemeris-file search path). If you see missing-header or missing-
     symbol errors, they're almost always fixable with an extra -D define
     added to extra_compile_args below — check libswe's own INSTALL notes
     for the exact flag.
  3. If straightforward compilation fails outright, pin `version` below to
     an older pyswisseph release and retry — very old libswe C code
     occasionally trips over newer NDK clang's stricter defaults.

This app does not need pyswisseph's optional "high precision" JPL/DE431
support (it only calls the default Moshier/Swiss Ephemeris analytical
model), so no ephemeris data files need to be bundled — see ephemeris.py's
own docstring in engine/ephemeris.py for confirmation of which mode this
project actually uses.
"""
from pythonforandroid.recipe import CompiledComponentsPythonRecipe


class PyswissephRecipe(CompiledComponentsPythonRecipe):
    # PyPI normalizes pyswisseph's own internal '2.10.03.2' version string
    # to this form for the actual published package/sdist filename.
    version = "2.10.3.2"
    # NOTE: the old "pypi.org/packages/source/p/<name>/..." URL pattern was
    # PyPI's legacy (pre-Warehouse) redirector and was retired years ago —
    # it 404s today. The real, current sdist lives on files.pythonhosted.org
    # under a content-hash path (confirmed via pypi.org/project/pyswisseph
    # on 2026-09-06):
    url = "https://files.pythonhosted.org/packages/66/a6/db70d67a00dda42ebd033538c086879328f4c17f670eafe8aca2f11abfef/pyswisseph-{version}.tar.gz"
    depends = ["python3"]

    # pyswisseph's setup.py must run under the TARGET (Android) Python
    # build environment, not the host build Python, so its Extension gets
    # compiled with the NDK cross-compiler rather than the host's gcc.
    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch=None, with_flags_in_cc=True):
        env = super().get_recipe_env(arch, with_flags_in_cc)
        # See point 1 in the module docstring above: make sure setup.py's
        # `pkg-config libswe` probe cannot accidentally succeed against a
        # HOST-installed libswe-dev and skip building the bundled sources.
        env["PKG_CONFIG_PATH"] = ""
        env["PKG_CONFIG_LIBDIR"] = ""
        return env


recipe = PyswissephRecipe()
