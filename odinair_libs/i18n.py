from typing import Callable

from redbot.core.i18n import CogI18n


class LazyI18n(CogI18n):
    """A lazy version of the Red CogI18n class

    Strings passed into this class will only be translated when called twice, which effectively
    means the following:

    >>> _ = CogI18n(...)
    >>> _("Test String")  # => Translated String

    Would be turned into the following:

    >>> _ = LazyI18n(...)
    >>> _("Lazy String")()  # => Translated String
    """

    def __call__(self, untranslated: str) -> Callable[..., str]:
        supr = super()
        return lambda: supr.__call__(untranslated)


i18n = LazyI18n("odinair_libs", __file__)
