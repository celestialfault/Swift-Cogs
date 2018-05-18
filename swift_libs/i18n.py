"""Internationalization related tools"""

from redbot.core.i18n import Translator


class LazyString:

    def __init__(self, untranslated: str, translator: Translator):
        self.untranslated = untranslated
        self._translator = translator  # type: Translator

    def __call__(self) -> str:
        return self._translator.__call__(self.untranslated)

    def __str__(self):
        return self()

    def __repr__(self):
        return "<LazyString untranslated={!r} cog={!r}>".format(
            self.untranslated, self._translator.cog_name
        )

    def __hash__(self):
        return hash(self.untranslated)

    def format(self, *args, **kwargs):
        return self().format(*args, **kwargs)

    def split(self, *args, **kwargs):
        return self().split(*args, **kwargs)


class LazyTranslator(Translator):
    """A lazy version of the Red Translator class

    Strings passed into this class will only be translated when the result is either manually
    coerced into a str, or called like a normal function.

    This effectively means the following snippet:

    >>> _ = Translator(...)
    >>> _("Test String")  # => Translated String

    Would be turned into the following:

    >>> _ = LazyTranslator(...)
    >>> _("Lazy String")  # => <LazyString untranslated='Lazy String' cog='MyCog'>
    >>> _("Lazy String")()  # => 'Translated String'
    >>> # .. or:
    >>> str(_("Lazy String"))  # => 'Translated String'
    >>> # .. or even:
    >>> _("String with {}").format("placeholders!")  # => 'String with placeholders!'
    """

    def __call__(self, untranslated: str) -> LazyString:
        return LazyString(untranslated, super())


def to_lazy_translator(translator: Translator):
    return LazyTranslator(translator.cog_name + "_LazyI18n", translator.cog_folder / "__init__.py")


def _fi18n(text):
    """Used to fake translations to ensure pygettext retrieves all the strings we want to translate.

    Outside of the aforementioned use case, this is exceptionally useless,
    since this just returns the given input string without
    any modifications made.
    """
    return text


# And now, we see 'how to keep pygettext from complaining in a possibly disgusting way':
fi18n = _fi18n
del _fi18n

i18n = Translator("swift_libs", __file__)
lazyi18n = to_lazy_translator(i18n)
