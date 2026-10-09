"""Import + round-trip checks for the probes generated in this directory.

Run with the in-repo generator source ahead of any installed copy:
    cd tmp/probe-enum-map
    PYTHONPATH=/app /app/tmp/probe7/venv/bin/python run_checks.py
"""
import sys
import traceback

sys.path.insert(0, "pb")
sys.path.insert(0, "models")

import google.protobuf  # noqa: E402

import protobuf_pydantic_gen.ext as ext_mod  # noqa: E402

print(f"protobuf {google.protobuf.__version__} / python {sys.version.split()[0]}")
print(f"generator source in use: {ext_mod.__file__}")


def load(mod_name, pb_name):
    try:
        __import__(pb_name)
    except Exception as e:  # noqa: BLE001
        print(f"    pb2 import failed: {type(e).__name__}: {e}")
        return None
    try:
        return __import__(mod_name)
    except Exception as e:  # noqa: BLE001
        print(f"    MODEL IMPORT FAILED: {type(e).__name__}: {str(e)[:300]}")
        traceback.print_exc(limit=3)
        return None


def dump_fields(cls):
    for name, field in cls.model_fields.items():
        print(f"      {name}: {field.annotation} = {field.default!r}")


def check_roundtrip(cls, label, **kwargs):
    try:
        proto = cls(**kwargs).to_protobuf()
        back = cls.from_protobuf(proto)
    except Exception as e:  # noqa: BLE001
        print(f"    [{label}] FAILED: {type(e).__name__}: {str(e)[:200]}")
        return
    which = proto.WhichOneof("value") if proto.DESCRIPTOR.oneofs_by_name.get("value") else None
    print(f"    [{label}] OK bytes={proto.SerializeToString()!r} WhichOneof={which!r} back={back!r}")


print("\n=== probe (enum map + message map + oneof + optional) ===")
m1 = load("probe_model", "probe_pb2")
if m1:
    dump_fields(m1.Union)
    check_roundtrip(m1.Union, "text oneof", metric="M", value="a")
    check_roundtrip(m1.Union, "numeric oneof", metric="M", value=1.5)
    check_roundtrip(m1.Union, "oneof unset", metric="M")
    check_roundtrip(m1.Union, "message map", metric="M", unavailable={"k": m1.Inner(outcome="ok")})
    check_roundtrip(m1.Union, "enum map", metric="M", levels={"k": m1.Level.LEVEL_LOW})
    check_roundtrip(m1.Union, "optional unset", metric="M")
    check_roundtrip(m1.Union, "optional set", metric="M", opt_score=0.0)

print("\n=== probe3 (proto3 optional vs plain double) ===")
m3 = load("probe3_model", "probe3_pb2")
if m3:
    dump_fields(m3.Union)
    for label, kwargs in (
        ("unset", {}),
        ("opt_score=None", {"opt_score": None}),
        ("opt_score=0.0", {"opt_score": 0.0}),
    ):
        try:
            proto = m3.Union(metric="M", **kwargs).to_protobuf()
            print(
                f"    [{label}] HasField('opt_score')={proto.HasField('opt_score')} "
                f"opt={proto.opt_score} plain={proto.plain_score} "
                f"bytes={proto.SerializeToString()!r}"
            )
        except Exception as e:  # noqa: BLE001
            print(f"    [{label}] to_protobuf FAILED: {type(e).__name__}: {str(e)[:200]}")

    empty_cls = __import__("probe3_pb2", fromlist=["Union"]).Union
    try:
        back = m3.Union.from_protobuf(empty_cls())
        print(
            f"    from_protobuf(<empty message>) -> metric={back.metric!r} "
            f"opt_score={back.opt_score!r} plain_score={back.plain_score!r} inner={back.inner!r}"
        )
    except Exception as e:  # noqa: BLE001
        print(f"    from_protobuf FAILED: {type(e).__name__}: {str(e)[:200]}")

print("\n=== probe2 (message map + oneof) ===")
m2 = load("probe2_model", "probe2_pb2")
if m2:
    dump_fields(m2.Union)
    check_roundtrip(m2.Union, "text oneof", metric="M", value="a")
    check_roundtrip(m2.Union, "message map", metric="M", unavailable={"k": m2.Inner(outcome="ok")})
