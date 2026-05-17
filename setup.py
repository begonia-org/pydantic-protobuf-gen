"""
Custom setuptools build command that recompiles pydantic.proto before packaging.
This runs automatically when executing:
    python -m build
    pip install -e .
    python setup.py build
"""

import subprocess
import sys
from setuptools import setup
from setuptools.command.build_py import build_py


class BuildProtoThenPy(build_py):
    """Compile pydantic.proto before the normal Python build step."""

    def run(self) -> None:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "grpc_tools.protoc",
                "--proto_path=.",
                "--python_out=.",
                "--pyi_out=.",
                "--grpc_python_out=.",
                "protobuf_pydantic_gen/pydantic.proto",
            ]
        )
        super().run()


setup(
    cmdclass={"build_py": BuildProtoThenPy},
)
