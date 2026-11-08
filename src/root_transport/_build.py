"""Build the bundled numerical kernel once per source/compiler configuration."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import tempfile

FLAGS = ("-O3", "-std=c++17", "-shared", "-fPIC", "-ffp-contract=off", "-frounding-math")


def native_library_path() -> Path:
    """Return a cached GNU/Linux library, compiling if its source key is new.

    GCC and libquadmath are required. No generated binary is written into the
    installed package. Set ROOT_TRANSPORT_CACHE to choose the build directory.
    """
    if platform.system() != "Linux":
        raise RuntimeError("The numerical backend currently supports GNU/Linux with GCC/libquadmath.")
    compiler = shlex.split(os.environ.get("CXX", "g++"))
    if not compiler or shutil.which(compiler[0]) is None:
        raise RuntimeError("GNU g++ is required. Install g++ (including libquadmath) or set CXX.")
    source = Path(__file__).parent / "native" / "iast_engine.cpp"
    header = source.parent / "baselines" / "ruptura_finite_pwl.hpp"
    identity = subprocess.run(compiler + ["--version"], check=True, capture_output=True).stdout
    key = hashlib.sha256(source.read_bytes() + header.read_bytes() + identity
                         + repr((FLAGS, compiler, platform.machine())).encode()).hexdigest()[:24]
    cache = Path(os.environ.get("ROOT_TRANSPORT_CACHE", str(Path(os.environ.get(
        "XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "root-transport")))
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"iast-{key}.so"
    if target.exists():
        return target
    fd, temporary = tempfile.mkstemp(prefix="iast-", suffix=".so", dir=cache)
    os.close(fd)
    try:
        process = subprocess.run(compiler + list(FLAGS) + [str(source), "-o", temporary, "-lquadmath"],
                                 capture_output=True, text=True)
        if process.returncode:
            raise RuntimeError("Native IAST compilation failed:\n" + process.stderr)
        os.replace(temporary, target)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return target
