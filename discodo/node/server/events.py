import random
from ... import getStat


def need_data(*keys):
    def decorator(func):
        async def wrapper(self, Data, **kwargs):
            if not Data:
                payload = {
                    "op": func.__name__,
                    "d": {"BAD_REQUEST": "This event needs `d`."},
                }
                return await self.sendJson(payload)

            if keys:
                NeedKeys = [key for key in keys if not key in Data.keys()]
                if NeedKeys:
                    payload = {
                        "op": func.__name__,
                        "d": {'"BAD_REQUEST': f"This event needs `{NeedKeys[0]}`."},
                    }
                    return await self.sendJson(payload)

            return await func(self, Data, **kwargs)

        return wrapper

    return decorator


def need_manager(func):
    def wrapper(self, *args, **kwargs):
        if not self.AudioManager:
            payload = {"op": func.__name__, "d": {
                "NOT_IDENTIFIED": "Identify first."}}

            return self.sendJson(payload)
        return func(self, *args, **kwargs)

    return wrapper


class WebsocketEvents:
    async def HEARTBEAT(self, Data):
        payload = {"op": "HEARTBEAT_ACK", "d": Data}

        await self.sendJson(payload)

    async def GET_STAT(self, Data):
        payload = {"op": "STAT", "d": getStat()}

        if self.AudioManager:
            payload["d"]["TotalPlayers"] = len(self.AudioManager.voiceClients)

        await self.sendJson(payload)

    @need_data("user_id")
    async def IDENTIFY(self, Data):
        if self.AudioManager:
            payload = {
                "op": "IDENTIFY",
                "d": {"ALREADY_IDENTIFIED": "This connection already identified."},
            }
        else:
            await self.initialize_manager(Data["user_id"])
            payload = {"op": "IDENTIFIED", "d": "AudioManager initialized."}

        await self.sendJson(payload)

    @need_manager
    @need_data()
    async def DISCORD_EVENT(self, Data):
        self.AudioManager.discordDispatch(Data)

    @need_manager
    @need_data("guild_id", "volume")
    async def setVolume(self, Data):
        if not Data["volume"] or not (
            isinstance(Data["volume"], int) or Data["volume"].isdigit()
        ):
            payload = {
                "op": "setVolume",
                "d": {"BAD_REQUEST": "`Volume` must be intenger.."},
            }
            return await self.sendJson(payload)

        value = int(Data["volume"])

        if value < 0 or value > 100:
            payload = {
                "op": "setVolume",
                "d": {"BAD_REQUEST": "`Volume` must be `0~100`.."},
            }
            return await self.sendJson(payload)

        self.AudioManager.setVolume(Data["guild_id"], value / 100)

        payload = {
            "op": "setVolume",
            "d": {"guild_id": Data["guild_id"], "volume": Data["volume"]},
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id", "crossfade")
    async def setCrossfade(self, Data):
        try:
            value = float(Data["crossfade"])
        except ValueError:
            payload = {
                "op": "setCrossfade",
                "d": {"BAD_REQUEST": "`crossfade` must be int or float.."},
            }
            return await self.sendJson(payload)

        self.AudioManager.setCrossfade(Data["guild_id"], value)

        payload = {
            "op": "setCrossfade",
            "d": {"guild_id": Data["guild_id"], "crossfade": Data["crossfade"]},
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id", "autoplay")
    async def setAutoplay(self, Data):
        if not isinstance(Data["autoplay"], bool):
            payload = {
                "op": "setAutoplay",
                "d": {"BAD_REQUEST": "`autoplay` must be bool.."},
            }
            return await self.sendJson(payload)

        self.AudioManager.setAutoplay(Data["guild_id"], Data["autoplay"])

        payload = {
            "op": "setAutoplay",
            "d": {"guild_id": Data["guild_id"], "autoplay": Data["autoplay"]},
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id", "filter")
    async def setFilter(self, Data):
        if not isinstance(Data["filter"], dict):
            payload = {
                "op": "setFilter",
                "d": {"BAD_REQUEST": "`filter` must be json.."},
            }
            return await self.sendJson(payload)

        self.AudioManager.getVC(Data["guild_id"]).filter = Data["filter"]

        payload = {
            "op": "setFilter",
            "d": {"guild_id": Data["guild_id"], "filter": Data["filter"]},
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id", "query")
    async def loadSong(self, Data):
        await self.AudioManager.loadSong(Data["guild_id"], Data["query"])

    @need_manager
    @need_data("guild_id")
    async def skip(self, Data):
        offset = (
            int(Data["offset"])
            if "offset" in Data
            and (isinstance(Data["offset"], int) or Data["offset"].isdigit())
            else 1
        )
        self.AudioManager.skip(Data["guild_id"], offset)

        payload = {
            "op": "skip",
            "d": {
                "guild_id": Data["guild_id"],
                "remain": len(self.AudioManager.getVC(Data["guild_id"]).Queue),
            },
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id")
    async def seek(self, Data):
        if not isinstance(Data["offset"], (int, float)):
            payload = {
                "op": "seek",
                "d": {"BAD_REQUEST": "`offset` must be int or float.."},
            }
            return await self.sendJson(payload)

        self.AudioManager.seek(Data["guild_id"], Data["offset"])

        payload = {
            "op": "seek",
            "d": {"guild_id": Data["guild_id"], "offset": Data["offset"]},
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id")
    async def getQueue(self, Data):
        vc = self.AudioManager.getVC(Data["guild_id"])

        payload = {
            "op": "Queue",
            "d": {
                "guild_id": Data["guild_id"],
                "entries": [Item.toDict() for Item in vc.Queue],
            },
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id")
    async def shuffle(self, Data):
        vc = self.AudioManager.getVC(Data["guild_id"])

        random.shuffle(vc.Queue)

        payload = {
            "op": "shuffle",
            "d": {
                "guild_id": Data["guild_id"],
                "entries": [Item.toDict() for Item in vc.Queue],
            },
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id", "index")
    async def remove(self, Data):
        if not isinstance(Data["index"], (int)):
            payload = {"op": "remove", "d": {
                "BAD_REQUEST": "`index` must be int.."}}
            return await self.sendJson(payload)

        vc = self.AudioManager.getVC(Data["guild_id"])

        removed = vc.Queue[Data["index"]]
        del vc.Queue[Data["index"]]

        payload = {
            "op": "remove",
            "d": {
                "guild_id": Data["guild_id"],
                "removed": removed.toDict(),
                "entries": [Item.toDict() for Item in vc.Queue],
            },
        }
        return await self.sendJson(payload)

    @need_manager
    @need_data("guild_id")
    async def VC_DESTROY(self, Data):
        self.AudioManager.delVC(Data["guild_id"])