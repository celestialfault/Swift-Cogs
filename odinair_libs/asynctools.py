__all__ = ('CallableAsyncGenerator', 'async_gen_to_list')


async def _gen():
    yield

CallableAsyncGenerator = type(_gen)
del _gen


async def async_gen_to_list(generator: CallableAsyncGenerator, *args, **kwargs):
    lst = []
    async for item in generator(*args, **kwargs):
        lst.append(item)
    return lst
