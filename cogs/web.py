from quart import Quart
from quart_cors import cors

app = Quart(__name__)
app = cors(app)

TASK = None

@app.get('/')
async def index():
    return {'message': 'Hello World!'}

@app.get('/stats')
async def stats():
    total_command_uses = await app.bot.db.fetchval('SELECT SUM(uses) FROM commands_usage')
    most_used_command = await app.bot.db.fetchval('SELECT command FROM commands_usage ORDER BY uses DESC LIMIT 1')
    latency = await app.bot.self_test()

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
    }


async def setup(bot):
    global TASK

    app.bot = bot

    if TASK:
        await teardown(bot)

    TASK = bot.loop.create_task(app.run_task(host='0.0.0.0', port=8082))

async def teardown(bot):
    global TASK

    await app.shutdown()

    if TASK is not None:
        TASK.cancel()

        await TASK
