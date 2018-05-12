Hi, thanks for taking the time to contribute!

The following is a set of guidelines (not rules!) to contributing. Use your best judgement, and feel free
to propose changes to this document in a pull request.

# Code style guidelines

These cogs follow the [Black](https://github.com/ambv/black) code style; it's recommended that you setup `pre-commit`
to format your changes to conform to this style before committing:

```bash
pip install -r requirements-dev.txt
pre-commit install
```

There's a multitude of helpful scripts located in `swift_libs/scripts/` that may make working on
these cogs much quicker. Some of these scripts are primarily designed for how this repository
is setup, but can likely be used in other repositories without too many modifications.

----

- Please do the following:
    - Ensure your changes work on at least Windows, Mac OSX, and Linux
    - Ensure that all Python features used exist and function properly on 3.5 and above
- Avoid the following:
    - Submit purely cosmetic whitespace change pull requests
    - Unnecessary code duplication
    - Lines with a character length of over 100 characters
    - `*` imports
- Don't do any of the following:
    - Use of any blocking functions, methods, and/or libraries (e.g. `requests`)

# Submitting a pull request

Please ensure the pull request description clearly describes what has been changed. If a relevant issue is open,
please mention it!

If your pull request introduces any new features, or changes any features in a substantial way,
**please open an issue first** before you start working on it, so I can provide feedback
before you spend time working on the pull request itself.
