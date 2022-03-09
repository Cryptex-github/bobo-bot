from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE

from core import BoboContext
from core import Cog
from core import command
from core import Regexs


class Owner(Cog):
    def cog_check(self, ctx: BoboContext) -> bool:
        return ctx.author.id == self.bot.owner_id

    @command()
    async def pull(self, ctx: BoboContext):
        proc = await create_subprocess_exec("git", "pull", stdout=PIPE, stderr=PIPE)

        stdout, stderr = await proc.communicate()

        stdout, stderr = stdout.decode(), stderr.decode()
        res = f"```\n{stdout}\n\n{stderr}```"

        cogs = Regexs.COG_REGEX.findall(res)
        for cog in cogs:
            try:
                cog_file = cog.replace("/", ".").replace(".py", "")
                if cog_file in self.bot.extensions:
                    self.bot.reload_extension(cog_file)
                else:
                    self.bot.load_extension(cog_file)
            except Exception as e:
                res += f"\n{cog!r} failed to reload: {e}"

        embed = ctx.embed(title="Pulled from Github", description=res)
        embed.add_field(
            name="Reloaded Cog(s)", value=", ".join(cogs) if cogs else "No Cog reloaded"
        )

        return embed


setup = Owner.setup
