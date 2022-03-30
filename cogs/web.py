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

    return {
        'guilds': len(app.bot.guilds),
        'users': len(app.bot.users),
        'channels': len(list(app.bot.get_all_channels())),
        'commands': len(list(app.bot.walk_commands())),
        'total_command_uses': total_command_uses,
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
