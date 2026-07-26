from google.protobuf import descriptor_pb2 as _descriptor_pb2
from protobuf_pydantic_gen import pydantic_pb2 as _pydantic_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MasteryStage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MASTERY_STAGE_UNSPECIFIED: _ClassVar[MasteryStage]
    SEEN: _ClassVar[MasteryStage]
    UNDERSTOOD: _ClassVar[MasteryStage]
    RETRIEVED: _ClassVar[MasteryStage]
    CONSOLIDATING: _ClassVar[MasteryStage]
    MASTERED: _ClassVar[MasteryStage]
MASTERY_STAGE_UNSPECIFIED: MasteryStage
SEEN: MasteryStage
UNDERSTOOD: MasteryStage
RETRIEVED: MasteryStage
CONSOLIDATING: MasteryStage
MASTERED: MasteryStage

class ConfidenceAssessment(_message.Message):
    __slots__ = ("self_report", "score", "stage")
    SELF_REPORT_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    STAGE_FIELD_NUMBER: _ClassVar[int]
    self_report: float
    score: float
    stage: MasteryStage
    def __init__(self, self_report: _Optional[float] = ..., score: _Optional[float] = ..., stage: _Optional[_Union[MasteryStage, str]] = ...) -> None: ...
