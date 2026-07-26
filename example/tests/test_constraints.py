"""Regression coverage for protobuf_pydantic_gen PR01.

Guards two generator defects:

* Defect 1 — a falsy numeric bound such as ``ge: 0`` (== the double default)
  used to be dropped by protoc before reaching the generator, so only the
  non-default ``le: 1`` survived. The fix gives the constraint scalars proto3
  field presence (``optional``) so explicit zeros are preserved.
* Defect 2 — generated proto enums used stdlib ``enum.Enum`` which has no
  value ordering. They now subclass ``enum.IntEnum`` so ``<`` / ``>`` /
  ``sorted()`` work by value.
"""

import pytest
from pydantic import ValidationError

from example.models.constraints_model import ConfidenceAssessment, MasteryStage


def _bounds(model_cls, field_name):
    """Return {constraint_name: value} for numeric bounds on a field.

    Reads Pydantic v2 field metadata (annotated_types.Ge/Gt/Lt/Le), which is
    independent of how the generated source is formatted.
    """
    metadata = model_cls.model_fields[field_name].metadata
    bounds = {}
    for item in metadata:
        name = type(item).__name__.lower()  # Ge -> 'ge', Le -> 'le', ...
        if name in {"ge", "gt", "lt", "le"}:
            bounds[name] = getattr(item, name)
    return bounds


# --------------------------------------------------------------------------- #
# Defect 1: falsy numeric bounds (ge: 0) must survive generation
# --------------------------------------------------------------------------- #
def test_generated_self_report_keeps_both_ge_and_le_bounds():
    """``ge: 0`` (a falsy double) must survive alongside ``le: 1``."""
    bounds = _bounds(ConfidenceAssessment, "self_report")
    assert bounds.get("ge") == 0.0, bounds
    assert bounds.get("le") == 1.0, bounds


def test_out_of_bounds_values_are_rejected():
    """``ge: 0`` / ``le: 1`` must actually reject out-of-range values."""
    for bad in (-0.1, -1, 1.1, 2, 100):
        with pytest.raises(ValidationError):
            ConfidenceAssessment(self_report=bad)


def test_in_bounds_values_are_accepted_including_zero():
    """Zero is a valid lower bound (inclusive ``ge: 0``); it must not be
    mistaken for "unspecified" and dropped."""
    for good in (0, 0.0, 0.5, 1, 1.0):
        ConfidenceAssessment(self_report=good)  # must not raise


def test_unconstrained_numeric_field_has_no_spurious_bounds():
    """``score`` declares no bounds, so it must accept negatives and carry no
    stray ge/gt/lt/le constraints."""
    assert _bounds(ConfidenceAssessment, "score") == {}
    ConfidenceAssessment(score=-123.4)  # must not raise


# --------------------------------------------------------------------------- #
# Defect 2: generated enums must compare by value (IntEnum)
# --------------------------------------------------------------------------- #
def test_enum_subclasses_int_enum():
    from enum import IntEnum

    assert issubclass(MasteryStage, IntEnum)


def test_enum_supports_value_comparison_and_sorting():
    assert MasteryStage.SEEN < MasteryStage.UNDERSTOOD < MasteryStage.RETRIEVED
    shuffled = [
        MasteryStage.MASTERED,
        MasteryStage.SEEN,
        MasteryStage.UNDERSTOOD,
    ]
    assert sorted(shuffled) == [
        MasteryStage.SEEN,
        MasteryStage.UNDERSTOOD,
        MasteryStage.MASTERED,
    ]


def test_enum_members_behave_as_ints():
    """IntEnum members are ints, so they interoperate with numeric code paths."""
    assert MasteryStage.SEEN == 1
    assert int(MasteryStage.MASTERED) == 5
