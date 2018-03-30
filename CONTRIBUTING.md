Hi, thanks for taking the time to contribute!

The following is a set of guidelines (not rules!) to contributing. Use your best judgement, and feel free
to propose changes to this document in a pull request.

# Code style guidelines

Aside from pep8 requirements, there's not much in terms of guidelines as to how you should style your code.

However, I do ask that you avoid the following:

- `*` imports
- Unnecessary code duplication
- Lines that are over 120 characters long
- Practically unreadable code (read: [do anything but this](https://gist.github.com/Eros/177f87042cc8a4d8bf97baaeabab266b))

# Submitting a pull request

Please ensure the pull request description clearly describes what has been changed. If a relevant issue is open, please mention it!

If your pull request changes any features in a substantial way, **please open an issue first** before you start working on it,
so I can provide feedback before you spend time working on the pull request itself.

In most cases, if your changes deviate a cog from the core design, or significantly changes how the cog behaves, I'll usually ask you to either:

- Move your changes into a separate cog that integrates with the initial cog
- Make your own fork with the changes you made

However, please keep in mind that exceptions may occasionally be made, such as if a pull request helps improve usability in a notable way.
