import os
import patch_ng


def patch_h2_protocol():
    """
    Patch the h2 protocol to support gRPC over HTTP/2.
    This is necessary for compatibility with FastAPI and other ASGI frameworks.
    """
    directory = os.path.dirname(__file__)
    patch_file = os.path.join(directory, "hypercorn_h2.patch")
    patchset = patch_ng.fromfile(patch_file)
    import hypercorn

    hypercorn_path = os.path.dirname(hypercorn.__file__)
    root_path = os.path.dirname(hypercorn_path)  # 上一级目录
    patchset.apply(root_path)
