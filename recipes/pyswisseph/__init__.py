"""
Custom python-for-android recipe for pyswisseph.

WHY THIS EXISTS: pyswisseph (the Swiss Ephemeris Python binding this whole
app's chart math depends on) has NO official recipe in python-for-android's
built-in recipe collection, so `buildozer`/`p4a` cannot cross-compile it for
Android out of the box. This recipe fills that gap.

pyswisseph's own setup.py is (almost) a plain distutils Extension build (it
compiles pyswisseph.c plus every .c file under its bundled libswe/ directory
into one C extension module), so python-for-android's generic
`CompiledComponentsPythonRecipe` — which just runs the package's own
setup.py under the NDK cross-compilation toolchain p4a sets up — is
sufficient, with one patch (see prebuild_arch below): a real build attempt
(2026-09-06, Buildozer 1.5.0 + python-for-android v2024.01.21, Docker/
Ubuntu 22.04) got all the way into pyswisseph's own setup_ext build with no
C-level cross-compilation issues at all — the only failure was setup.py's
`from setuptools import ...` import, since p4a's hostpython3 (which runs
setup.py here) is built --without-ensurepip and has no setuptools.
prebuild_arch below patches that one import to distutils.core instead
(every setup() argument used is plain-distutils-compatible - see the
patch's own comment). Re-verify after that patch; if the build fails for a
*different* reason, the speculative fixes below (still unconfirmed) are
the next things to try:

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
import os
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

    def prebuild_arch(self, arch):
        super().prebuild_arch(arch)
        # p4a's own hostpython3 (the interpreter that actually RUNS this
        # setup.py, since call_hostpython_via_targetpython is False above)
        # is built with --without-ensurepip, so it has no setuptools - only
        # the stdlib. setup.py's only use of setuptools is the single
        # `from setuptools import setup, Extension` import; every argument
        # passed to setup() below that (name/version/description/author/
        # classifiers/ext_modules/...) is plain distutils-compatible, so
        # swapping the import for distutils.core (still present in the
        # Python 3.11 this recipe builds) needs nothing else to change.
        setup_py = self.get_build_dir(arch.arch) + "/setup.py"
        if os.path.exists(setup_py):
            with open(setup_py, "r", encoding="utf-8") as f:
                content = f.read()
            patched = content.replace(
                "from setuptools import setup, Extension",
                "from distutils.core import setup, Extension",
            )
            if patched != content:
                with open(setup_py, "w", encoding="utf-8") as f:
                    f.write(patched)


recipe = PyswissephRecipe()
