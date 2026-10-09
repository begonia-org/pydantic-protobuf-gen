#!/bin/sh
# Run the regression suite across the supported protobuf range.
#
#   sh tmp/probe-enum-map/matrix.sh                 # ephemeral envs via `uv run --with` (default)
#   PROBE_VENVS=1 sh tmp/probe-enum-map/matrix.sh   # reuse pre-built tmp/probe*/venv (faster, but ~300MB)
#
# Why isolation is unavoidable: protobuf is one-version-per-interpreter, so a
# 4-version matrix needs 4 interpreters. The default path keeps them inside uv's
# shared cache (`~/.cache/uv`), so nothing lands in this working tree.
#
# This is the *runtime* matrix: nothing here installs protoc/grpcio-tools, so it can
# probe releases that do not co-resolve with the declared dependency set (e.g.
# 7.34.0, blocked by grpcio-tools 1.83+ requiring protobuf>=7.35.1). The install-level
# matrix — what a consumer can actually pip install — lives in
# .github/workflows/tests.yml and uses 7.35.1 instead of 7.34.0.
set -u

REPO=${REPO:-/app}
TESTS="$REPO/example/tests"
PYTEST_ARGS="-q -p no:cacheprovider --ignore=$TESTS/test_performance.py"
DEPS="--with sqlmodel --with pytest --with pytest-asyncio --with googleapis-common-protos \
--with jinja2 --with grpcio --with autopep8 --with inflection --with peewee \
--with pgvector --with zstandard --with requests --with pydantic-settings"

summarize() {
    grep -E 'passed|failed|error' | tail -1
}

if [ "${PROBE_VENVS:-0}" = "1" ]; then
    for venv in probe529 probe633 probe-floor probe7; do
        py=$REPO/tmp/$venv/venv/bin/python
        if [ ! -x "$py" ]; then
            printf '%-12s (venv missing)\n' "$venv"
            continue
        fi
        printf '%-12s ' "$("$py" -c 'import google.protobuf as p; print(p.__version__)' 2>/dev/null)"
        PYTHONPATH=$REPO "$py" -m pytest "$TESTS" $PYTEST_ARGS 2>&1 | summarize
    done
    exit 0
fi

for version in 5.29.0 6.33.6 7.34.0 7.35.1 7.36.2; do
    printf '%-12s ' "$version"
    PYTHONPATH=$REPO uv run --no-project --python 3.11 --with "protobuf==$version" $DEPS \
        python -m pytest "$TESTS" $PYTEST_ARGS 2>&1 | summarize
done
