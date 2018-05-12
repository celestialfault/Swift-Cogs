"""Internationalization related tools"""

from redbot.core.i18n import Translator


class LazyString:

    def __init__(self, untranslated: str, i18n_obj: Translator):
        self.untranslated = untranslated
        self._i18n = i18n_obj  # type: Translator

    def __call__(self) -> str:
        return self._i18n.__call__(self.untranslated)

    def __str__(self):
        return self()

    def __repr__(self):
        return "<LazyString untranslated={!r} cog={!r}>".format(
            self.untranslated, self._i18n.cog_name
        )

    def __hash__(self):
        return hash(self.untranslated)

    def format(self, *args, **kwargs):
        return self().format(*args, **kwargs)

    def split(self, *args, **kwargs):
        return self().split(*args, **kwargs)


class LazyTranslator(Translator):
    """A lazy version of the Red CogI18n class

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

    # how to dodge pygettext warnings in an insane way:
    def _normal_i18n(self, untranslated: str) -> str:
        return super().__call__(untranslated)

    normal_i18n = _normal_i18n
    del _normal_i18n

    def __call__(self, untranslated: str) -> LazyString:
        return LazyString(untranslated, super())


def to_lazy_translator(translator: Translator):
    return LazyTranslator(translator.cog_name + "_LazyI18n", translator.cog_folder / "__init__.py")


i18n = Translator("odinair_libs", __file__)
lazyi18n = to_lazy_translator(i18n)
