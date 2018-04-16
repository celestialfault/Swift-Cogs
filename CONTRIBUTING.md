Hi, thanks for taking the time to contribute!

The following is a set of guidelines (not rules!) to contributing. Use your best judgement, and feel free
to propose changes to this document in a pull request.

-------

# Code style guidelines

Aside from enforced pep8 compliance (with the exception of allowing up to 120 character long lines),
there's not much in terms of guidelines as to how you should style your code.

#### Do the following

- Ensure all Python features used exist and properly work in 3.6 and above

#### Please avoid the following

**Do note:** Pull requests that include any of these criteria won't necessarily be immediately closed,
but I'll usually ask you to fix it, unless it has a valid technical reason for being included.

- `*` imports
- Unnecessary and/or excessive code duplication
- Lines that are over 120 characters long
- Practically unreadable code

#### Any pull requests including the following will be closed

- Pull requests that only change whitespace in a cosmetic way
- Use of any blocking methods / libraries (e.g. `requests`)

# Submitting a pull request

Please ensure the pull request description clearly describes what has been changed. If a relevant issue is open,
please mention it!

If your pull request introduces any new features, or changes any features in a substantial way,
**please open an issue first** before you start working on it, so I can provide feedback
before you spend time working on the pull request itself.
