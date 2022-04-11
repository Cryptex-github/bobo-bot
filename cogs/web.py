from quart import Quart

app = Quart(__name__)

TASK = None

@app.get('/')
async def index():
    return {'message': 'Hello World!'}


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

