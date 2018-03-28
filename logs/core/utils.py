from typing import List, Dict

import discord

from logs.core import Module, _

from cog_shared.odinair_libs.formatting import flatten

__all__ = ('add_descriptions', 'status_embed')


def add_descriptions(items: List[str], descriptions: Dict[str, str] = None) -> str:
    if descriptions is None:
        descriptions = {}
    for item in items:
        index = items.index(item)
        items[index] = f"**{item}** \N{EM DASH} {descriptions.get(item, _('No description set'))}"
    return "\n".join(items)


def status_embed(module: Module) -> discord.Embed:
    module_opts = flatten(module.settings, sep=":")
    for opt in module_opts.copy():
        if opt not in module.opt_keys:
            module_opts.pop(opt)

    enabled = add_descriptions([x for x in module_opts if module_opts[x]], module.option_descriptions)
    disabled = add_descriptions([x for x in module_opts if not module_opts[x]], module.option_descriptions)

    dest = _("Disabled")
    if isinstance(module.log_to, discord.Webhook):
        dest = _("Webhook")
    elif isinstance(module.log_to, discord.TextChannel):
        dest = _("Channel {}").format(module.log_to.mention)

    embed = discord.Embed(colour=discord.Colour.blurple(), description=module.module_description)
    embed.add_field(name=_("Logging"), value=dest, inline=False)
    embed.set_author(name=_("{} module settings").format(module.friendly_name), icon_url=module.icon_uri())
    embed.add_field(name=_("Enabled"),
                    value=enabled or _("**None** \N{EM DASH} All of this module's options are disabled"),
                    inline=False)
    embed.add_field(name=_("Disabled"),
                    value=disabled or _("**None** \N{EM DASH} All of this module's options are enabled"),
                    inline=False)
    return embed
