<h1 align="center">Swift Cogs</h1>
<p align="center">Some moderation, bot management, and other various cogs.</p>
<p align="center">
  <a href="https://circleci.com/gh/notodinair/Swift-Cogs"><img src="https://circleci.com/gh/notodinair/Swift-Cogs.svg?style=svg" /></a>
  <a href="https://python.org/"><img src="https://img.shields.io/badge/Python-3.6-red.svg?style=flat-square" /></a>
  <a href="https://github.com/Cog-Creators/Red-DiscordBot"><img src="https://img.shields.io/badge/Red--DiscordBot-3.0.0-blue.svg?style=flat-square" /></a>
  <a href="http://makeapullrequest.com"><img src="https://img.shields.io/badge/PRs-welcome-green.svg?style=flat-square" /></a>
</p>

# Installation

### Required Reading

- **These cogs require Python 3.6 to properly function.** Some cogs may be able to work on 3.5, but your mileage may vary.
- Until Red V3 is considered stable, these cogs should be considered prone to breaking changes being made at any time, with or without warning, nor with any backward compatibility of any sort.

----

```
[p]repo add swift-cogs https://github.com/notodinair/Swift-Cogs.git
[p]cog install swift-cogs <cog>
[p]load <cog>
```

# Contact

If you've either found a bug or would like to make a suggestion, please [open an issue](https://github.com/notodinair/Swift-Cogs/issues/new),
as this is by far the best way to make sure that I notice it.

Otherwise, you can contact me on Discord (`Emma#5555`) or Twitter (`@odinair_`).

# Cogs

**A lot of these cogs reference servers as guilds in their command output and help docs,
and as such this readme also references them as such.**

Any references to `[p]` should be replaced with your bots command prefix.

<details>
<summary>Cog Whitelist</summary>

Restricts specific cogs to guilds that have been whitelisted by the bot owner.

Note that the bot owner and co-owners *always bypass this cog's checks*, regardless of a guilds whitelist status.

#### To install

```
[p]cog install swift-cogs cogwhitelist
[p]load cogwhitelist
```

#### Requirements

- None

#### Additional Notes

- None
</details>

<details>
<summary>Logs</summary>

Log anything and everything that may happen in your guild.

#### To install

```
[p]cog install swift-cogs logs
[p]load logs
```

#### Requirements

- None

#### Additional Notes

- None
</details>

<details>
<summary>Misc Tools</summary>

Various quick and dirty utilities.

This is mostly useful if you're either making a cog, or for advanced server moderation/administration.
Otherwise, this cog may be entirely useless to you.

#### To install

```
[p]cog install swift-cogs misctools
[p]load misctools
```

#### Requirements

- None

#### Additional Notes

- None
</details>

<details>
<summary>Quotes</summary>

Save and retrieve quotes. Quotes also support author attribution, and editing the content post-creation.

#### To install

```
[p]cog install swift-cogs quotes
[p]load quotes
```

#### Requirements

- None

#### Additional Notes

- None
</details>

<details>
<summary>Require Role</summary>

Require members to have one of (or the lack of) any roles out of a set list to use the bot's commands in a guild.

#### To install

```
[p]cog install swift-cogs requirerole
[p]load requirerole
```

#### Requirements

- None

#### Additional Notes

- None
</details>

<details>
<summary>Random Activity</summary>

Randomly change your bots activity status on a set delay to one in a set list of statuses, which support placeholders. 

#### To install

```
[p]cog install swift-cogs rndactivity
[p]load rndactivity
```

#### Requirements

- None

#### Additional Notes

- This cog creates a timer that runs on the configured loop delay
</details>

<details>
<summary>Role Mention</summary>

Mention configurable roles on demand.
This can be helpful if you have roles which you don't want everyone to be able to mention,
but still need to mention from time to time.

#### To install

```
[p]cog install swift-cogs rolemention
[p]load rolemention
```

#### Requirements

- None

#### Additional Notes

- None
</details>

<details>
<summary>Starboard</summary>

Send messages to a per-guild starboard channel, via means of reacting with :star:

#### To install

```
[p]cog install swift-cogs starboard
[p]load starboard
```

#### Requirements

- None

#### Additional Notes

- This cog creates several timers:
    - An internal cache cleaner that runs every 10 minutes
    - An update queue handler that runs every 10 seconds
- This cog may use a fair amount of memory, due to the internal message cache
</details>

<details>
<summary>Timed Role</summary>

Adds one or more roles to a member for a set amount of time

#### To install

```
[p]cog install swift-cogs timedrole
[p]load timedrole
```

#### Requirements

- None

#### Additional Notes

- This cog creates a timer that runs once every 3 minutes.
</details>

<details>
<summary>Timed Mute</summary>

Mute a member for a set amount of time, with integration for the core Red modlog.

#### To install

```
[p]cog install swift-cogs timedmute
[p]load timedmute
```

#### Requirements

- `Timed Role` cog

#### Additional Notes

- None
</details>

<details>
<summary>UInfo</summary>

Yet another variation on `[p]userinfo`

#### To install

```
[p]cog install swift-cogs uinfo
[p]load uinfo
```

#### Requirements

- None

#### Additional Notes

- None
</details>
