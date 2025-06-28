from pydantic import BaseModel


def scheme_to_query_params(scheme: BaseModel) -> dict:
    params = scheme.model_dump(exclude_none=True)
    if not params:
        return None
    for key, value in params.items():
        if isinstance(value, list):
            params[key] = ",".join(map(str, value))
        if isinstance(value, bool):
            params[key] = str(value).lower()
    return params
