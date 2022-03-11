from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE
from io import StringIO

from discord import File
from tabulate import tabulate

from core import Cog, BoboContext, command, Regexs, Timer

class Owner(Cog):
    async def cog_check(self, ctx: BoboContext) -> bool:
        return await self.bot.is_owner(ctx.author)
    
    @command()
    async def pull(self, ctx: BoboContext):
        proc = await create_subprocess_exec("git", "pull", stdout=PIPE, stderr=PIPE)

        stdout, stderr = await proc.communicate()

        stdout, stderr = stdout.decode(), stderr.decode()
        res = f'```\n{stdout}\n\n{stderr}```'

        cogs = Regexs.COG_REGEX.findall(res)
        for cog in cogs:
            try:
                cog_file = cog.replace('/', '.').replace('.py', '')
                if cog_file in self.bot.extensions:
                    self.bot.reload_extension(cog_file)
                else:
                    self.bot.load_extension(cog_file)
            except Exception as e:
                res += f'\n{cog!r} failed to reload: {e}'
        
        embed = ctx.embed(title='Pulled from Github', description=res)
        embed.add_field(name='Reloaded Cog(s)', value=', '.join(cogs) if cogs else 'No Cog reloaded')

        return embed
    
    @command()
    async def sql(self, ctx: BoboContext, *, query: str):
        with Timer() as timer:
            res = await self.bot.db.fetch(query)
        
        fmted = '```sql\n'

        if res:
            fmted += tabulate(res, headers='keys', tablefmt='psql') + '\n```'
        
        fmted += f'\n\n{len(res)} result(s) in {float(timer):.2f} seconds'
    
        if res <= 2000:
            return res, True
        
        return File(StringIO(fmted), filename='sql.txt'), True
        


setup = Owner.setup
