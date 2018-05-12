gen_cog.py
--------------
    This generates a cog that has a single with a simple response.

    This is designed to help quicken the cog development process by removing some
    tedious boilerplate work.


    Usage
    -------

    $ python gen_cog.py MyCog


gen_readme
--------------
    Generates a nice cog list in your repository's README file (or any other desginated file).

    This requires the `Jinja2` library.

    All configuration is done with a `gen_readme.json` file in the same directory as the script's __main__.py file.


    Usage
    -------

    $ python -m gen_readme [cogs...]


gen_locales.py
------------------
    Generate cog locales with `redgettext`.


    Usage
    -------

    $ python gen_locales.py [cogs...] [optional --flag options...]


test.sh
-----------
    A quick test script, primarily designed for this repository.

    This checks the following:

    - ensure all cogs at least compile
    - flake8
    - black (currently this check doesn't exit with a non-zero code if a failure is encountered)

    You won't find this all too useful unless you're creating a patch for a cog in this repository.


    Usage
    -------

    $ sh test.sh
