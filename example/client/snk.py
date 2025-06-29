def to_snake_case(name: str) -> str:
    """Convert CamelCase or PascalCase to snake_case, handling consecutive uppercase letters correctly."""
    import re

    # Replace transitions from lower-to-upper or digit-to-upper with _
    s1 = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    # Replace transitions from uppercase followed by uppercase+lower (e.g., HTTPRequest -> HTTP_Request)
    s2 = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", s1)
    return s2.lower()


print(
    f"Converted 'HTTPRequest' to '{to_snake_case('HTTPRequest')}'"
)  # Should print 'http_request'
