from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

from google.protobuf.json_format import MessageToDict
from pydantic import BaseModel


def _load_any_transformer():
    module_path = (
        Path(__file__).resolve().parents[2]
        / "protobuf_pydantic_gen"
        / "any_type_transformer.py"
    )
    spec = spec_from_file_location(
        "protobuf_pydantic_gen.any_type_transformer", module_path
    )
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module.AnyTransformer


AnyTransformer = _load_any_transformer()


class Facts(BaseModel):
    retries: int
    success: bool


def test_python_to_struct_handles_scalar_and_nested_values():
    payload = {
        "i": 1,
        "b": True,
        "f": 1.5,
        "s": "ok",
        "n": None,
        "outer": {
            "count": 2,
            "flags": [True, False],
            "items": [{"name": "a"}, {"name": "b"}],
        },
    }

    struct_value = AnyTransformer.python_to_struct(payload)

    assert MessageToDict(struct_value) == payload
    assert struct_value.fields["b"].bool_value is True
    assert struct_value.fields["i"].number_value == 1.0
    assert struct_value.fields["n"].null_value == 0


def test_python_to_struct_dumps_nested_pydantic_models():
    payload = {"facts": Facts(retries=2, success=True)}

    struct_value = AnyTransformer.python_to_struct(payload)

    assert MessageToDict(struct_value) == {"facts": {"retries": 2, "success": True}}


def test_python_to_value_keeps_bool_before_number():
    value = AnyTransformer.python_to_value(True)

    assert value.WhichOneof("kind") == "bool_value"
    assert value.bool_value is True


def test_python_to_struct_rejects_unsupported_types():
    try:
        AnyTransformer.python_to_struct({"bad": object()})
    except TypeError as exc:
        assert "Unsupported Struct value type" in str(exc)
        assert "object" in str(exc)
    else:
        raise AssertionError("Expected TypeError for unsupported Struct value")
