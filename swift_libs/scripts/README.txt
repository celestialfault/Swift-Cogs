gen_cog.py
--------------
    Generates a cog that has a single command with a simple response.

    This is designed to help quicken the cog development process by removing some
    tedious boilerplate work.


    Usage
    -------

    $ python gen_cog.py MyCog


gen_readme
--------------
    Generates a nice cog list in your repository's README file (or any other designated file).

    This requires the `Jinja2` library.

    All configuration is done with a `gen_readme.json` file in the same directory as the script's __main__.py file.


    Usage
    -------

    $ python -m gen_readme [cogs...] [--config CONFIG]


gen_locales.py
------------------
    Generates cog locales with `redgettext`.


    Usage
    -------

    $ python gen_locales.py [cogs...] [--docstrings] [--verbose] [-p|--output-dir OUTPUT DIR]
                            [-k|--keyword KEYWORD [KEYWORD ...]]


test.sh
-----------
    A quick test script, primarily designed for this repository.

    This checks the following:

    - all cogs compile
    - flake8
    - black code style

    You won't find this all too useful unless you're creating a patch for a cog in this repository.


    Usage
    -------

    $ sh test.sh
