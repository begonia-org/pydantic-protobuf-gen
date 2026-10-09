#!/bin/sh
# Run the regression suite across the supported protobuf range.
#
#   sh tmp/probe-enum-map/matrix.sh
#
# The venvs are disposable (they match the gitignored `venv/` rule); see
# tmp/probe-enum-map/README.md for the rebuild commands.
set -u
REPO=${REPO:-/app}
IGNORE="--ignore=$REPO/example/tests/test_performance.py"

for venv in probe529 probe633 probe-floor probe7; do
    py=$REPO/tmp/$venv/venv/bin/python
    [ -x "$py" ] || { echo "$venv: (venv missing)"; continue; }
    version=$($py -c 'import google.protobuf as p; print(p.__version__)' 2>/dev/null)
    printf '%-26s ' "protobuf $version"
    PYTHONPATH=$REPO $py -m pytest "$REPO/example/tests" $IGNORE -q -p no:cacheprovider 2>&1 |
        tail -1
done
