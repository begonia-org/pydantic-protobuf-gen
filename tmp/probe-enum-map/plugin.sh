#!/bin/sh
# Run the in-repo generator source as a protoc plugin.
#
#   PROBE_PYTHON : interpreter to run the plugin with (default: python3)
#   PROBE_REPO   : repo root holding the protobuf_pydantic_gen package (default: /app)
#
# Container (declared-range protobuf):
#   PROBE_REPO=/app python3 -m grpc_tools.protoc --plugin=protoc-gen-pydantic=$PWD/plugin.sh ...
# Host (protobuf 6.33.6 in an existing venv):
#   PROBE_PYTHON=/data/work/ahaeureka/ai-infer/.venv/bin/python \
#   PROBE_REPO=/data/work/begonia-org/pydantic-protobuf-gen python3 -m grpc_tools.protoc ...
exec env PYTHONPATH="${PROBE_REPO:-/app}${PYTHONPATH:+:$PYTHONPATH}" "${PROBE_PYTHON:-python3}" -c "from protobuf_pydantic_gen.generator import main; raise SystemExit(main())"
