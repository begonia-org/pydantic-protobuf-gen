"""
Custom setuptools build command that recompiles pydantic.proto before packaging.
This runs automatically when executing:
    python -m build
    pip install -e .
    python setup.py build
"""

import subprocess
import sys
import warnings
from importlib.util import find_spec
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


PROTO_SOURCE_FILE = Path("protos/protobuf_pydantic_gen/pydantic.proto")
PROTO_IMPORT_FILE = Path("protobuf_pydantic_gen/pydantic.proto")
GENERATED_FILES = (
    Path("protobuf_pydantic_gen/pydantic_pb2.py"),
    Path("protobuf_pydantic_gen/pydantic_pb2.pyi"),
    Path("protobuf_pydantic_gen/pydantic_pb2_grpc.py"),
)


def _generated_files_missing() -> bool:
    return any(not generated_file.exists() for generated_file in GENERATED_FILES)


def _generated_files_outdated() -> bool:
    proto_mtime = PROTO_SOURCE_FILE.stat().st_mtime
    return any(
        generated_file.stat().st_mtime < proto_mtime
        for generated_file in GENERATED_FILES
    )


def _grpc_tools_available() -> bool:
    return find_spec("grpc_tools.protoc") is not None


class BuildProtoThenPy(build_py):
    """Compile pydantic.proto before the normal Python build step."""

    def run(self) -> None:
        should_compile = _generated_files_missing() or _generated_files_outdated()

        if should_compile and _grpc_tools_available():
            subprocess.check_call(
                [
                    sys.executable,
                    "-m",
                    "grpc_tools.protoc",
                    "--proto_path=protos",
                    "--python_out=.",
                    "--pyi_out=.",
                    "--grpc_python_out=.",
                    str(PROTO_IMPORT_FILE),
                ]
            )
        elif should_compile:
            missing_or_outdated = (
                "missing" if _generated_files_missing() else "out of date"
            )
            warnings.warn(
                "Skipping protobuf regeneration because grpcio-tools is not installed; "
                f"packaging will continue with checked-in generated files, which are {missing_or_outdated}.",
                stacklevel=2,
            )

        super().run()


setup(
    cmdclass={"build_py": BuildProtoThenPy},
)
