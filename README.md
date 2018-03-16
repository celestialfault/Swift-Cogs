<h1 align="center">odinair's cogs</h1>
<p align="center">Some home-grown cogs, which may or may not be useful.</p>
<p align="center">
  <a href="https://python.org/"><img src="https://img.shields.io/badge/Python-3.6-red.svg?style=flat-square"></a>
  <a href="https://github.com/Cog-Creators/Red-DiscordBot"><img src="https://img.shields.io/badge/Red--DiscordBot-3.0.0-blue.svg?style=flat-square"></a>
  <a href="http://makeapullrequest.com"><img src="https://img.shields.io/badge/PRs-welcome-green.svg?style=flat-square"></a>
</p>

# Installation

```
[p]repo add odinair https://github.com/notodinair/Red-Cogs.git v3
[p]cog install odinair <cog>
[p]load <cog>
```

# Contact

If you've either found a bug or would like to make a suggestion, please [open an issue](https://github.com/notodinair/Red-Cogs/issues/new),
as this is by far the best way to make sure that I notice it.

Otherwise, you can contact me on Discord (`odinair#0001`) or Twitter (`@odinair_`).

# Cogs

**A lot of these cogs reference servers as guilds in their command output and help docs,
and as such this readme also references them as such.**

Any references to `[p]` should be replaced with your bots command prefix.

<details>
<summary>Bot Monitor</summary>

Monitors specified bots and sends a message in the specified channel when they go offline or when they come back up.

#### To install

```
[p]cog install odinair botmonitor
[p]load botmonitor
```
</details>

<details>
<summary>Cog Whitelist</summary>

Restricts specific cogs to guilds that have been whitelisted by the bot owner.

Note that bot owners or co-owners *always bypass this cog's checks*, regardless of a guilds whitelist status.

#### To install

```
[p]cog install odinair cogwhitelist
[p]load cogwhitelist
```
</details>

<details>
<summary>Logs</summary>

Log anything and everything that may happen in your guild.

#### To install

```
[p]cog install odinair logs
[p]load logs
```
</details>

<details>
<summary>Misc Tools</summary>

Quick and dirty utilities.

This is mostly useful if you're either making a cog, or for advanced server moderation/administration.
Otherwise, this cog may be entirely useless to you.

#### To install

```
[p]cog install odinair misctools
[p]load misctools
```
</details>

<details>
<summary>Quotes</summary>

Save and retrieve quotes. Quotes also support author attribution, and editing the content post-creation.

#### To install

```
[p]cog install odinair quotes
[p]load quotes
```
</details>

<details>
<summary>Require Role</summary>

Require members to have one of (or the lack of) any roles out of a set list to use the bot's commands in a guild.

#### To install

```
[p]cog install odinair requirerole
[p]load requirerole
```
</details>

<details>
<summary>Random Activity</summary>

Randomly change your bots activity status on a set delay to one in a set list of statuses, which support placeholders. 

#### To install

```
[p]cog install odinair rndactivity
[p]load rndactivity
```
</details>

<details>
<summary>Role Mention</summary>

Mention configurable roles on demand.
This can be helpful if you have roles which you don't want everyone to be able to mention,
but still need to mention from time to time.

#### To install

```
[p]cog install odinair rolemention
[p]load rolemention
```
</details>

<details>
<summary>Starboard</summary>

Send messages to a per-guild starboard channel, all from star reactions.

#### To install

```
[p]cog install odinair starboard
[p]load starboard
```
</details>

<details>
<summary>Timed Role</summary>

Adds one or more roles to a member for a set amount of time

#### To install

```
[p]cog install odinair timedrole
[p]load timedrole
```
</details>

<details>
<summary>Timed Mute</summary>

Mute a member for a set amount of time, with integration for the core Red modlog.

*This cog requires my `timedrole` cog to function.*

#### To install

```
[p]cog install odinair timedmute
[p]load timedmute
```
</details>

<details>
<summary>UInfo</summary>

Yet another variation on `[p]userinfo`

#### To install

```
[p]cog install odinair uinfo
[p]load uinfo
```
</details>
