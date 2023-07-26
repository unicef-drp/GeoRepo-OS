

def version_gt(version: str, value: int) -> bool:
    """
    Compare version, e.g. v1, is greater than value
    Example:
        version_gt('v1', 2) = False
        version_gt('v2', 1) = True
    """
    version_int = 1
    if version:
        version_int = int(version[1:])
    return version_int > value
