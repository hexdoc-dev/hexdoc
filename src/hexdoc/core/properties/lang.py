from hexdoc.model.strip_hidden import StripHiddenModel


class LangProps(StripHiddenModel):
    """Configuration for a specific book language."""

    quiet: bool = False
    """If `True`, do not log warnings for missing translations.

    Using this option for the default language is not recommended.
    """
    ignore_errors: bool = False
    """If `True`, log fatal errors for this language instead of failing entirely.

    Using this option for the default language is not recommended.
    """
