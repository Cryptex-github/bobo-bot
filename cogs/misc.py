from __future__ import annotations

import json
from asyncio import to_thread
from asyncio.subprocess import DEVNULL, PIPE, create_subprocess_exec
from datetime import datetime
from platform import node
from textwrap import dedent
from typing import TYPE_CHECKING

import humanize
import psutil

from core import Cog, command

if TYPE_CHECKING:
    from core import BoboContext
    from discord import Embed


class Misc(Cog):
    async def cog_load(self) -> None:
        with open('./events.lua', 'r') as f:
            self.get_event_counts = self.bot.redis.register_script(f.read())

    @command()
    async def ping(self, ctx: BoboContext) -> str:
        """Pong!"""
        res = await self.bot.self_test()

        return dedent(
            f"""
            PostgreSQL latency: {res.postgres}ms
            Redis latency: {res.redis}ms
            Discord REST latency: {res.discord_rest}ms
            Discord WS latency: {res.discord_ws}ms
            Bobo API latency: {res.bobo_api}ms
            Bobo CDN latency: {res.bobo_cdn}ms
            Bobo eval API latency: {res.bobo_eval_api}ms
        """
        )

    @command()
    async def sys(self, ctx: BoboContext) -> Embed:
        proc = psutil.Process()

        with proc.oneshot():
            mem = proc.memory_full_info()
            net = psutil.net_io_counters()
            disk = psutil.disk_usage('/')

            embed = ctx.embed(title='System Info')

            embed.description = dedent(
                f"""
                ```prolog
                Node: {node()}

                CPU:
                    Usage: {await to_thread(psutil.cpu_percent, interval=0.3)}%

                Process:
                    PID: {proc.pid}
                    Threads: {proc.num_threads()}
                    Memory:
                        Physical: {humanize.naturalsize(mem.rss)}
                        Virtual: {humanize.naturalsize(mem.vms)}

                Disk:
                    Total: {humanize.naturalsize(disk.total)}
                    Free: {humanize.naturalsize(disk.free)}
                    Used: {humanize.naturalsize(disk.used)}
                    Used Percent: {disk.percent}%
                
                Network:
                    Bytes Sent: {humanize.naturalsize(net.bytes_sent)}
                    Bytes Received: {humanize.naturalsize(net.bytes_recv)}
                    Packets Sent: {net.packets_sent:,}
                    Packets Received: {net.packets_recv:,}
                
                System:
                    Boot Time: {datetime.fromtimestamp(psutil.boot_time()).strftime('%Y-%m-%d %H:%M:%S')}
                ```
            """
            )

        return embed

    @command()
    async def speedtest(self, ctx: BoboContext) -> Embed | str:
        """Runs a speedtest."""
        async with ctx.typing():
            proc = await create_subprocess_exec(
                'speedtest', '--format', 'json', stdout=PIPE, stderr=DEVNULL
            )

            stdout, _ = await proc.communicate()

            if proc.returncode != 0:
                return 'Failed to run speedtest.'

            stdout = stdout.decode()
            json_ = json.loads(stdout)

            if json_['type'] != 'result':
                return 'Failed to run speedtest.'

            embed = ctx.embed(title='Speedtest', url=json_['result']['url'])

            embed.add_field(
                name='Ping',
                value=f'Latency: {json_["ping"]["latency"]}ms | Jitter: {json_["ping"]["jitter"]}ms',
                inline=False,
            )

            download_bytes = json_['download']['bytes']
            upload_bytes = json_['upload']['bytes']

            embed.add_field(
                name='Download',
                value=f'{round((((download_bytes / json_["download"]["elapsed"])) * 8.0) / 1000, 2)}Mbps (Data used: {humanize.naturalsize(download_bytes)})',
                inline=False,
            )
            embed.add_field(
                name='Upload',
                value=f'{round((((upload_bytes / json_["upload"]["elapsed"])) * 8.0) / 1000, 2)}Mbps (Data used: {humanize.naturalsize(upload_bytes)})',
                inline=False,
            )

            embed.add_field(
                name='Server',
                value=f'{json_["server"]["name"]} (ID: {json_["server"]["id"]})',
                inline=False,
            )
            embed.add_field(
                name='Packet Lost', value=f'{json_["packetLoss"]}%', inline=False
            )

            embed.set_footer(text=f'Test ID: {json_["result"]["id"]}')

            return embed

    @command()
    async def events(self, ctx: BoboContext) -> str:
        """Shows the number of events since the bot was started."""
        events_count = await self.get_event_counts()

        time_difference = (
            float(datetime.now().timestamp())
            - float(await self.bot.redis.get('events_start_time'))
        ) / 60

        return dedent(
            f"""
            Total WS Events: {events_count}
            Average WS Events per minute: {events_count // time_difference}
        """
        )


setup = Misc.setup
