"""
A [Jinja](https://jinja.palletsprojects.com/en/3.1.x/)-based documentation generator for [Patchouli](https://github.com/VazkiiMods/Patchouli) books.
"""

# attempt to reduce the amount of breaking changes from moving hexdoc out of hexmod
try:
    import hexdoc_hexcasting as hexcasting  # type: ignore
except ImportError:
    pass
