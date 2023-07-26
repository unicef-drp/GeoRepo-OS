from uuid import UUID


def get_uuid_value(value: str):
    """Try to parse UUID value"""
    val = None
    try:
        val = UUID(value)
    except ValueError:
        pass
    return val
