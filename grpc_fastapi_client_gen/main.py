import os


from grpc_fastapi_client_gen.client_generator import ClientCodeGenerator, to_snake_case
from typing import Any, Dict
from google.protobuf.compiler import plugin_pb2

from protobuf_pydantic_gen.main import code_generation


def _get_grpc_plugin_parameters(parameters: str) -> Dict[str, Any]:
    """
    Get parameters for gRPC plugin from the request.
    """
    params = {}
    if not parameters:
        return params
    for param in parameters.split(','):
        if '=' in param:
            key, value = param.split('=', 1)
            key = key.strip()
            value = value.strip()
            if value.lower() in ('true', 'false'):
                params[key] = value.lower() == 'true'
            else:
                params[key] = value
    return params


def generate_code(
    request: plugin_pb2.CodeGeneratorRequest, response: plugin_pb2.CodeGeneratorResponse
):
    params = _get_grpc_plugin_parameters(request.parameter)
    models_dir = params.get("models_dir", "models")
    package_name = params.get("package_name", ".")
    services_json_path = os.path.join(models_dir, "services.json")
    g = ClientCodeGenerator(os.path.dirname(__file__))
    class_name = params.get("class_name", "Client")
    code = g.generate_client_code(
        services_json_path=services_json_path,
        models_dir=models_dir,
        package_name=package_name,
        class_name=params.get("class_name", "Client"),
        template_name="client.j2"
    )
    import autopep8
    code = autopep8.fix_code(
        code,
        options={
            "max_line_length": 120,
            "in_place": True,
            "aggressive": 5,
        },
    )
    response.file.add(
        name=f"{to_snake_case(class_name)}.py",
        content=code,
    )


def main():
    with code_generation() as (request, response):
        generate_code(request, response)
