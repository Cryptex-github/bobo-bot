from __future__ import annotations

from typing import TYPE_CHECKING

import discord
from discord.ext.commands import param, Author

from textwrap import dedent
from jishaku.codeblocks import codeblock_converter

from core import Cog, command
from core.constants import SAFE_SEND, Constant

if TYPE_CHECKING:
    from core.context import BoboContext


class Utility(Cog):
    @command(aliases=['ui'])
    async def userinfo(
        self, ctx: BoboContext, user: discord.Member | discord.User = Author
    ) -> discord.Embed:
        """
        Get information about a user.
        """
        user_avatar = user.display_avatar.with_static_format('png').url

        embed = ctx.embed()
        embed.set_author(name=user.display_name, icon_url=user_avatar)
        embed.set_thumbnail(url=user_avatar)

        bot_status = (
            'Verified Bot'
            if user.public_flags.verified_bot
            else 'Bot'
            if user.bot
            else 'Not Bot'
        )

        general_field = dedent(
            f"""
        **Name:** {user.name}
        **Display Name:** {user.display_name}
        **Discriminator:** {user.discriminator}
        **ID:** {user.id}
        **Created At:** {user.created_at.strftime('%Y-%m-%d %H:%M:%S')} ({discord.utils.format_dt(user.created_at, style='R')})
        **Bot Status:** {bot_status}
        """
        )

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

        members = sorted(
            user.guild.members,
            key=lambda m: m.joined_at if m.joined_at else m.created_at,
            reverse=False,
        )
        # Just to fool type checker because i do not want to import datetime and create a dummy object just for this

        join_position = f'{members.index(user) + 1}/{len(members)}'

        guild_field = dedent(
            f"""
        **Joined At:** {joined_at}
        **Total Roles:** {len(user.roles)}
        **Top Role:** {user.top_role.mention}
        **All Roles:** {', '.join(role.mention for role in user.roles)}
        **Status:** {user_status}
        **Join Position:** {join_position}
        """
        )

        embed.add_field(name='Guild Informations', value=guild_field)

        return embed

    @command(aliases=['eval', 'run'])
    async def evaluate(
        self, ctx, *, code: tuple[str, str] = param(converter=codeblock_converter)
    ) -> str | tuple[str, Constant]:
        """
        Evaluate code.

        Currently, the only supported language is `python3`
        """
        language, code_ = code

        if language not in ('python3', 'py', 'python'):
            return f'Language `{language}` is not supported.'

        return_code_map = {137: 'SIGKILL', 255: 'Fatal Error'}

        if language in ('python3', 'py', 'python'):
            with open('./assets/code_eval_prepend.py', 'r') as f:
                code_to_prepend = f.read()

                code_ = code_to_prepend.replace('# code to evaluate', code_)

        async with self.bot.session.post(
            'https://eval.bobobot.cf/eval', json={'input': code_}
        ) as resp:
            json = await resp.json()

            return_code = json['returncode']

            return (
                dedent(
                    f"""
            ```{language}
            {json['stdout']}
            Return code: {return_code} {"(" + return_code_map.get(return_code, 'Unknown') + ")" if return_code != 0 else ''}
            ```
            """
                ), SAFE_SEND
            )


setup = Utility.setup
