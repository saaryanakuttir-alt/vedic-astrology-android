"""ui/version.py must match buildozer.spec, so the version shown in the app is the one that was built."""
import os
import re

APP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_shown_version_matches_buildozer_spec():
    spec = open(os.path.join(APP, "buildozer.spec"), encoding="utf-8").read()
    built = re.search(r"^version\s*=\s*(\S+)", spec, re.M).group(1)
    shown = re.search(r'VERSION = "([^"]+)"', open(os.path.join(APP, "ui", "version.py"), encoding="utf-8").read()).group(1)
    assert built == shown
