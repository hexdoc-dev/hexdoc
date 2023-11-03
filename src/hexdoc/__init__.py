# attempt to reduce the amount of breaking changes from moving hexdoc out of hexmod
try:
    import hexdoc_hexcasting as hexcasting  # type: ignore
except ImportError:
    pass
