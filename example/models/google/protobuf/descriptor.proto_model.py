
"""#!/usr/bin/env python
# -*- encoding: utf-8 -*-
'''
@File    :   google/protobuf/descriptor.proto.py
@Time    :   
@Desc    :   
'''



from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class (BaseModel):
    file: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    package: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    dependency: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    public_dependency: 5 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    weak_dependency: 5 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    message_type: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    enum_type: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    service: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    extension: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    source_code_info: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    syntax: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    edition: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    field: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    extension: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    nested_type: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    enum_type: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    extension_range: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    oneof_decl: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    reserved_range: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    reserved_name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    number: 5 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    label: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    type: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    type_name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    extendee: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    default_value: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    oneof_index: 5 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    json_name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    proto3_optional: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    value: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    reserved_range: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    reserved_name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    number: 5 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    method: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    input_type: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    output_type: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    options: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    client_streaming: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    server_streaming: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    java_package: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    java_outer_classname: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    java_multiple_files: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    java_generate_equals_and_hash: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    java_string_check_utf8: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    optimize_for: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    go_package: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    cc_generic_services: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    java_generic_services: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    py_generic_services: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    php_generic_services: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    deprecated: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    cc_enable_arenas: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    objc_class_prefix: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    csharp_namespace: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    swift_prefix: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    php_class_prefix: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    php_namespace: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    php_metadata_namespace: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    ruby_package: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    message_set_wire_format: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    no_standard_descriptor_accessor: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    deprecated: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    map_entry: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    deprecated_legacy_json_field_conflicts: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    ctype: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    packed: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    jstype: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    lazy: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    unverified_lazy: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    deprecated: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    weak: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    debug_redact: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    retention: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    target: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    allow_alias: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    deprecated: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    deprecated_legacy_json_field_conflicts: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    deprecated: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    deprecated: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    deprecated: 8 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    idempotency_level: 14 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    uninterpreted_option: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    name: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    identifier_value: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    positive_int_value: 4 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    negative_int_value: 3 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    double_value: 1 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    string_value: 12 = Field(
        default=,
        alias="",
        title="",
        description=""
    )
    aggregate_value: 9 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    location: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )


class (BaseModel):
    annotation: 11 = Field(
        default=,
        alias="",
        title="",
        description=""
    )

"""