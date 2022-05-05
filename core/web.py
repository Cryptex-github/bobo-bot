from __future__ import annotations

from discord.http import Route
from typing import TYPE_CHECKING, Literal, TypeAlias, cast

from datetime import datetime

from quart import Quart, request
from quart_cors import cors

from config import client_secret
from .bot import BoboBot


if TYPE_CHECKING:
    METHODS: TypeAlias = Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    JSON: TypeAlias = dict[str, str | int]

    class _Quart(Quart):        
        bot: BoboBot
    
    Quart = _Quart


app = Quart(__name__)

app.config['JSON_SORT_KEYS'] = False

app = cors(app)

async def discord_request(method: METHODS, route: str, data: JSON) -> JSON | tuple[JSON, int]:
    try:
        token = request.args['Access-Token']
    except KeyError:
        return {'error': 'Missing Access-Token header'}, 401
    
    route = Route.BASE + route
    headers = {'Authorization': 'Bearer ' + token}

    async with app.bot.session.request(method, route, headers=headers, json=data) as resp:
        if not resp.ok:
            return {
                'error': f'{resp.status}: {await resp.text()}'
            }, 400
        
        return await resp.json()

@app.get('/')
async def index():
    return {'message': 'Hello World!'}

@app.get('/stats')
async def stats():
    async with app.bot.db.acquire() as conn:
        total_command_uses = await conn.fetchval('SELECT SUM(uses) FROM commands_usage')
        most_used_command = await conn.fetchval(
            'SELECT command FROM commands_usage ORDER BY uses DESC LIMIT 1'
        )

    latency = await app.bot.self_test()

    events = await app.bot.get_cog('Misc').get_event_counts()

    time_difference = (
        float(datetime.now().timestamp())
        - float(await app.bot.redis.get('events_start_time'))
    ) / 60

    return {
        'Servers': len(app.bot.guilds),
        'Users': len(app.bot.users),
        'Channels': len(list(app.bot.get_all_channels())),
        'Commands': len(list(app.bot.walk_commands())),
        'Total Command Uses': int(total_command_uses),
        'Most Used Command': most_used_command,
        'Postgres Latency': f'{latency.postgres} ms',
        'Redis Latency': f'{latency.redis} ms',
        'Discord REST Latency': f'{latency.discord_rest} ms',
        'Discord WebSocket Latency': f'{latency.discord_ws} ms',
        'Total Gateway Events': f'{events:,}',
        'Average Events per minute': f'{events // time_difference}',
    }

@app.post('/exchange-code')
async def exchange_code() -> JSON | tuple[JSON, int]:
    try:
        code = request.args['code']
    except KeyError:
        return {'error': 'No code provided'}, 400
    
    data = {
        'client_id': app.bot.user.id,
        'client_secret': client_secret,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': 'https://bobobot.cf'
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    async with app.bot.session.post(Route.BASE + '/oauth2/token', data=data, headers=headers) as resp:
        if not resp.ok:
            return {
                'error': f'{resp.status}: {await resp.text()}'
            }, 400
        
        return await resp.json()

@app.get('/commands')
async def commands() -> JSON | tuple[JSON, int]:
    bot = cast(BoboBot, app.bot)
    json = []

    for command in bot.walk_commands():
        cooldown_fmted = None

        if bucket := getattr(command, '_buckets'):
            if cooldown := getattr(bucket, '_cooldown'):
                cooldown_fmted = f'{cooldown.rate} time(s) per {cooldown.per} second(s)'

        json.append({
            'name': command.qualified_name,
            'args': command.signature,
            'category': command.cog_name,
            'description': (
                command.description or command.short_doc or 'No Help Provided'
            ),
            'aliases': command.aliases,
            'cooldown': cooldown_fmted
        })

    cogs = [cog.qualified_name for cog in bot.cogs.values() if not getattr(cog, 'ignore', False)]
    del cogs[cogs.index('Jishaku')]

    return {'commands': json, 'categories': cogs}
