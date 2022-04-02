from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from textwrap import dedent

from core import Cog, command
from core.utils import cutoff

if TYPE_CHECKING:
    from core.context import BoboContext


class Utility(Cog):
    @command(aliases=['ui'])
    async def userinfo(self, ctx: BoboContext, user: discord.User | discord.Member | None = None) -> discord.Embed:
        """
        Get information about a user.
        """
        if not user:
            user = ctx.author

        user_avatar = user.display_avatar.with_static_format('png').url

        embed = ctx.embed()
        embed.set_author(name=user.display_name, icon_url=user_avatar)
        embed.set_thumbnail(url=user_avatar)

        bot_status = 'Verified Bot' if user.public_flags.verified_bot else 'Bot' if user.bot else 'Not Bot'

        general_field = dedent(f"""
        **Name:** {user.name}
        **Display Name:** {user.display_name}
        **Discriminator:** {user.discriminator}
        **ID:** {user.id}
        **Created At:** {user.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({discord.utils.format_dt(user.created_at, style='R')})
        **Bot Status:** {bot_status}
        """)

        embed.add_field(name='General Informations', value=general_field)

        if not isinstance(user, discord.Member):
            return embed
        
        joined_at = 'N/A'

        if user.joined_at:
            joined_at = f"{user.joined_at.strftime('%Y-%m-%d %H:%M:%S')} ({discord.utils.format_dt(user.joined_at, style='R')})"
        
        user_status = ''

        if status := user.desktop_status:
            if status is not discord.Status.offline:
                user_status += f'{str(status).title()} on Desktop'
        
        if status := user.mobile_status:
            if status is not discord.Status.offline:
                user_status += f'\n{str(status).title()} on Mobile'
        
        if status := user.web_status:
            if status is not discord.Status.offline:
                user_status += f'\n{str(status).title()} on Web'
        
        join_position = f'{user.guild.members.index(user) + 1}/{len(user.guild.members)}'

        guild_field = dedent(f"""
        **Joined At:** {joined_at}
        **Total Roles:** {len(user.roles)}
        **Top Role:** {user.top_role.mention}
        **All Roles:** {', '.join(role.mention for role in user.roles)}
        **Status:** {user_status}
        **Join Position:** {join_position}
        """)

        embed.add_field(name='Guild Informations', value=guild_field)

        return embed

setup = Utility.setup