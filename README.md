<h1 align="center">odinair's cogs</h1>
<p align="center">Some home-grown cogs, which may or may not be useful.</p>
<p align="center">
  <a href="https://python.org/"><img src="https://img.shields.io/badge/Python-3.6-red.svg"></a>
  <a href="https://github.com/Cog-Creators/Red-DiscordBot"><img src="https://img.shields.io/badge/Red--DiscordBot-3.0.0-brightgreen.svg"></a>
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
and as such this readme also references them as such as well.**

Any references to `[p]` should be replaced with your bots command prefix.

<details>
<summary>Bot Monitor</summary>

Monitors specified bots and sends a message in the specified channel when they go offline or when they come back up.

**To install:**

- `[p]cog install odinair botmonitor`
- `[p]load botmonitor`

**Basic usage:**

- `[p]botmonitor channel <channel>` - sets the bot monitor channel - this option is global, and can only be set to one channel
- `[p]botmonitor monitor <bot>` - monitors `bot`, posting in the set channel when it goes offline or comes online again
</details>

<details>
<summary>Cog Whitelist</summary>

Restricts specific cogs to guilds that have been whitelisted by the bot owner.

Note that bot owners or co-owners *always bypass this cog's checks*, regardless of a guilds whitelist status.

**To install:**

- `[p]cog install odinair cogwhitelist`
- `[p]load cogwhitelist`

**Basic usage:**

- Enable Developer Mode in your Appearance settings so you can copy guild IDs
- Copy a guild ID by right clicking on a server in your list, and selecting `Copy ID`
- `[p]cogwhitelist add <cog> [guild id]` - adds `cog` to the list of whitelist-required cogs, optionally also allowing the guild with the specified id to use it
- `[p]cogwhitelist remove <cog> [guild id]` - does the reverse of `[p]cogwhitelist add`
</details>

<details>
<summary>Logs</summary>

Log anything and everything that may happen in your guild.

**To install:**

- `[p]cog install odinair logs`
- `[p]load logs`

**Basic usage:**

- `[p]logset logchannel <channel> all` - set all log channels to `channel`
- `[p]help logset`
</details>

<details>
<summary>Misc Tools</summary>

Quick and dirty utilities.

This is mostly useful if you're either making a cog, or for advanced server moderation/administration.
Otherwise, this cog may be entirely useless to you.

**To install:**

- `[p]cog install odinair misctools`
- `[p]load misctools`

**Basic usage:**

- `[p]charinfo <characters...>` - returns the unicode name for some characters
- `[p]pingtime` - retrieve the time it took for the bot to respond to a message
- `[p]rtfs <command>` - retrieve the source code for a command or sub-command
- `[p]snowflake <snowflakes...>` - retrieve the creation time for one or more snowflake ids
</details>

<details>
<summary>Quotes</summary>

Save and retrieve quotes. Quotes also support author attribution, and editing the content post-creation!

**To install:**

- `[p]cog install odinair quotes`
- `[p]load quotes`

**Basic usage:**

- `[p]quote add This is a quote!` - add a quote with the text `This is a quote!`
- `[p]quote message <message id>` - add a quote by retrieving the message from the id given; this automatically attributes the quote to the message author
- `[p]quote attribute <quote> <member>` - attributes `quote` to the member specified
- `[p]quote 1` - retrieve the added quote
- `[p]quote remove 1` - removes the added quote; this requires you to be the quote creator, attributed author, and/or a moderator/administrator
</details>

<details>
<summary>Require Role</summary>

Require one (or lack of any) out of a set list of roles to use the bot's commands in a guild. 

**To install:**

- `[p]cog install odinair requirerole`
- `[p]load requirerole`

**Basic usage:**

- `[p]requirerole "Bot Allowed" "~Bot Denied"` - allows members with `Bot Allowed` to use the bot, except if they have `Bot Denied`
</details>

<details>
<summary>Random Activity</summary>

Randomly change your bots activity status on a set delay to one in a set list of statuses, which support placeholders. 

**To install:**

- `[p]cog install odinair rndactivity`
- `[p]load rndactivity`

**Basic usage:**

Currently added placeholders:
- `{GUILDS}` - the amount of guilds on the current shard
- `{MEMBERS}` - the amount of members in each guild on the current shard
- `{SHARD}` - the current shard id
- `{SHARDS}` - the amount of shards the bot currently has
- `{COMMANDS}` - the amount of commands currently loaded
- `{COGS}` - the amount of cogs currently loaded

Commands:
- `[p]rndactivity add with {GUILDS} guilds` -> adds the activity status `with {GUILDS} guilds`
- `[p]rndactivity (watching|listening) <status>` -> adds a watching or listening activity status
- `[p]rndactivity list` -> lists added statuses
- `[p]rndactivity list true` -> lists added statuses, but also parses placeholders and displays their current return value
</details>

<details>
<summary>Role Mention</summary>

Mention configurable roles on demand.
This can be helpful if you have roles which you don't want everyone to be able to mention,
but still need to mention from time to time.

**To install:**

- `[p]cog install odinair rolemention`
- `[p]load rolemention`

**Basic usage:**

- `[p]rolemention add <role>` - allows mentioning of a role
- `<{mention role: @role}>` - mention a role in a message
- `[p]rolemention mention <role> <text>` - mention a role via commands
</details>

<details>
<summary>Starboard</summary>

Send messages to a per-guild starboard channel, all from star reactions.

**To install:**

- `[p]cog install odinair starboard`
- `[p]load starboard`

**Basic usage:**

- `[p]star <message id>` - stars a message by id; this is an alternative to adding a star reaction to a message
- `[p]unstar <message id>` - does the reverse of `[p]star`
- `[p]starboard channel <channel>` - set the guilds starboard channel
- `[p]starboard requirerole` - toggles integration with the `requirerole` cog; defaults to enabled
- `[p]starboard minstars <amount>` - set the minimum amount of stars a message must receive to be sent to the starboard
- `[p]starboard (unignore|ignore) <channel>` - ignore or unignore a channel from the guilds starboard
- `[p]stars (block|unblock) <member>` - blocks or unblocks a member from the guilds starboard
- `[p]stars (hide|unhide) <message id>` - hides or unhides a message from the guilds starboard
</details>

<details>
<summary>Timed Role</summary>

Adds one or more roles to a member for a set amount of time

**To install:**

- `[p]cog install odinair timedrole`
- `[p]load timedrole`

**Basic usage:**

- `[p]timedrole add <member> <duration> <roles...>` - adds one or more roles to `member` for `duration`
- `[p]timedrole list` - lists the timed roles currently active
</details>

<details>
<summary>Timed Mute</summary>

Mute a member for a set amount of time, with integration for the core Red modlog.

*This cog requires my `timedrole` cog to function.*

**To install:**

- `[p]cog install odinair timedmute`
- `[p]load timedmute`

**Basic usage:**

- `[p]timedmute <member> <duration> [reason]` - mutes `member` for `duration`, with an optional reason
</details>

<details>
<summary>UInfo</summary>

Yet another variation on `[p]userinfo`

**To install:**

- `[p]cog install odinair uinfo`
- `[p]load uinfo`

**Basic usage:**

- `[p]uinfo [member]`
</details>
