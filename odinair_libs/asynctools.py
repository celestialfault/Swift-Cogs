__all__ = ('CallableAsyncGenerator', 'async_gen_to_list')

try:
    # noinspection PyCompatibility
    async def _gen():
        yield

    CallableAsyncGenerator = type(_gen)
    del _gen

    async def async_gen_to_list(generator: CallableAsyncGenerator, *args, **kwargs):
        lst = []
        async for item in generator(*args, **kwargs):
            lst.append(item)
        return lst
except SyntaxError:
    # py3.5 polyfill
    CallableAsyncGenerator = None

    # noinspection PyUnusedLocal
    async def async_gen_to_list(*args, **kwargs):
        raise RuntimeError('not running on python 3.6')
