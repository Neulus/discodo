import os
from functools import wraps

from sanic import Sanic, response
from sanic.exceptions import abort

from ...AudioSource import AudioData
from ...planner import IPRotator
from ...stat import getStat
from .websocket import app as WebsocketBlueprint

PASSWORD = os.getenv("PASSWORD", "hellodiscodo")
USABLE_IP = os.getenv("USABLE_IP", "").split("|")

app = Sanic(__name__)

app.planner = IPRotator() if USABLE_IP else None
for IP in USABLE_IP if USABLE_IP else []:
    app.planner.add(IP)

app.register_blueprint(WebsocketBlueprint)


def authorized(func):
    def wrapper(request, *args, **kwargs):
        if request.headers.get("Authorization") != PASSWORD:
            abort(403, "Password mismatch.")

        return func(request, *args, **kwargs)

    return wrapper


@app.route("/stat")
async def stat(request):
    return response.json(getStat())


@app.route("/getSong")
@authorized
async def getSong(request):
    query = "".join(request.args.get("query", [])).strip()

    if not query:
        abort(400, "Missing parameter query.")

    return response.json(await AudioData.create(query))
