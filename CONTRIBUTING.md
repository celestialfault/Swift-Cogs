Hi, thanks for taking the time to contribute!

The following is a set of guidelines (not rules!) to contributing. Use your best judgement, and feel free
to propose changes to this document in a pull request.

# Getting started

**If you are not intending to develop on these cogs directly, please follow the instructions in the
[README.md](https://github.com/notodinair/Swift-Cogs/blob/master/README.md) file instead!**

Setting up a development instance of this repository can be somewhat tricky due to how this repository
is setup, but this should help ease the process:

- Clone this repository somewhere on your machine that your bot can access
- Symlink `swift_libs` to your bot's `cog_shared` directory - the correct path can be obtained by running `[p]debug bot.get_cog('Downloader').SHAREDLIB_PATH`
    - You may have to restart your bot with the `--dev` flag to be able to execute the above debug command
- Add the repository path to your bot paths - `[p]addpath <the path you cloned to>`

# Code style guidelines

These cogs follow the [Black](https://github.com/ambv/black) code style, with a maximum line length
of 100 characters.

- Please do the following:
    - Ensure your changes work on at least Windows, Mac OSX, and Linux
    - Ensure that all Python features used exist and function properly on 3.6 and above
- Avoid the following if at all possible:
    - Unnecessary code duplication
    - `*` imports
    - Use of any blocking functions, methods, and/or libraries (e.g. `requests`)

### Command Responses

The stance for command responses in this repository is that, unless you absolutely must use embeds,
such as for rich data display (think something along the lines of `[p]userinfo`), or if a plain-text variation
would look vastly worse, **you should use normal content-only responses instead of embeds**.

In essence, this means usage of `ctx.maybe_send_embed` isn't something I'll accept in a pull request.

# Submitting a pull request

Please ensure that your pull request description clearly describes what has been changed.
If a relevant issue is open, please mention it!

If your pull request introduces any new features, or changes any features in a substantial way,
**please open an issue first** before you start working on it, so I can provide feedback
before you spend time working on the pull request itself.
