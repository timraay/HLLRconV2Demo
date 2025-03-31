import asyncio
from datetime import timedelta
from functools import wraps
import json
from typing import Any, Callable, Coroutine, Mapping, ParamSpec, TypeVar
from lib.executor import RconExecutor
from lib.responses import (
    AdminLogResponse, GetAllCommandsResponse, GetCommandDetailsResponse, GetMapRotationResponse,
    GetPlayerResponse, GetPlayersResponse, GetServerConfigResponse, GetServerSessionResponse,
)

P = ParamSpec('P')
DictT = TypeVar('DictT', bound=Mapping[Any, Any])
def cast_response_to_dict(dict_type: type[DictT]) -> Callable[
    [Callable[P, Coroutine[Any, Any, str]]],
    Callable[P, Coroutine[Any, Any, DictT]]
]:
    def decorator(func: Callable[P, Coroutine[Any, Any, str]]) -> Callable[P, Coroutine[Any, Any, DictT]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs):
            result = await func(*args, **kwargs)
            with open('debug.txt', 'w+') as f:
                f.write(result)
            return json.loads(result)
        return wrapper
    return decorator

class RconCommands:
    def __init__(self, executor: RconExecutor) -> None:
        self.executor = executor

    async def add_admin(self, player_id: str, admin_group: str, comment: str):
        await self.executor.execute("AddAdmin", 2, {
            "PlayerId": player_id,
            "AdminGroup": admin_group,
            "Comment": comment
        })

    async def remove_admin(self, player_id: str):
        await self.executor.execute("AddAdmin", 2, {
            "PlayerId": player_id,
        })
    
    @cast_response_to_dict(AdminLogResponse)
    async def admin_log(self, seconds_span: int, filter: str | None = None):
        return await self.executor.execute("AdminLog", 2, {
            "LogBackTrackTime": seconds_span,
            "Filters": filter or "",
        })
    
    async def change_map(self, map_name: str):
        await self.executor.execute("ChangeMap", 2, {
            "MapName": map_name,
        })

    async def change_sector_layout(self, sector1: str, sector2: str, sector3: str, sector4: str, sector5: str):
        await self.executor.execute("ChangeSectorLayout", 2, {
            "Sector_1": sector1,
            "Sector_2": sector2,
            "Sector_3": sector3,
            "Sector_4": sector4,
            "Sector_5": sector5,
        })

    async def add_map_to_rotation(self, map_name: str, index: int):
        await self.executor.execute("AddMapToRotation", 2, {
            "MapName": map_name,
            "Index": index,
        })

    async def remove_map_from_rotation(self, index: int):
        await self.executor.execute("RemoveMapFromRotation", 2, {
            "Index": index,
        })

    async def add_map_to_sequence(self, map_name: str, index: int):
        await self.executor.execute("AddMapToSequence", 2, {
            "MapName": map_name,
            "Index": index,
        })

    async def remove_map_from_sequence(self, index: int):
        await self.executor.execute("RemoveMapFromSequence", 2, {
            "Index": index,
        })

    async def set_map_shuffle_enabled(self, enabled: bool):
        await self.executor.execute("ShuffleMapSequence", 2, {
            "Enable": enabled,
        })

    async def move_map_from_sequence(self, old_index: int, new_index: int):
        await self.executor.execute("MoveMapFromSequence", 2, {
            "CurrentIndex": old_index,
            "NewIndex": new_index,
        })

    @cast_response_to_dict(GetAllCommandsResponse)
    async def get_all_commands(self):
        return await self.executor.execute("DisplayableCommands", 2)

    async def set_team_switch_cooldown(self, minutes: int):
        await self.executor.execute("SetTeamSwitchCooldown", 2, {
            "TeamSwitchTimer": minutes,
        })

    async def set_max_queued_players(self, num: int):
        await self.executor.execute("SetMaxQueuedPlayers", 2, {
            "MaxQueuedPlayers": num,
        })

    async def set_idle_kick_duration(self, minutes: int):
        await self.executor.execute("SetIdleKickDuration", 2, {
            "IdleTimeoutMinutes": minutes,
        })

    async def message_all_players(self, message: str):
        await self.executor.execute("SendServerMessage", 2, {
            "Message": message,
        })

    @cast_response_to_dict(GetPlayerResponse)
    async def get_player(self, player_id: str):
        return await self.executor.execute("ServerInformation", 2, {
            "Name": "player",
            "Value": player_id
        })

    @cast_response_to_dict(GetPlayersResponse)
    async def get_players(self):
        return await self.executor.execute("ServerInformation", 2, {
            "Name": "players",
            "Value": ""
        })

    @cast_response_to_dict(GetMapRotationResponse)
    async def get_map_rotation(self):
        return await self.executor.execute("ServerInformation", 2, {
            "Name": "maprotation",
            "Value": ""
        })

    @cast_response_to_dict(GetMapRotationResponse)
    async def get_map_sequence(self):
        return await self.executor.execute("ServerInformation", 2, {
            "Name": "mapsequence",
            "Value": ""
        })

    @cast_response_to_dict(GetServerSessionResponse)
    async def get_server_session(self):
        return await self.executor.execute("ServerInformation", 2, {
            "Name": "session",
            "Value": ""
        })

    @cast_response_to_dict(GetServerConfigResponse)
    async def get_server_config(self):
        return await self.executor.execute("ServerInformation", 2, {
            "Name": "serverconfig",
            "Value": ""
        })

    async def broadcast(self, message: str):
        await self.executor.execute("ServerBroadcast", 2, {
            "Message": message,
        })

    async def set_high_ping_threshold(self, ms: int):
        await self.executor.execute("SetHighPingThreshold", 2, {
            "HighPingThresholdMs": ms,
        })

    @cast_response_to_dict(GetCommandDetailsResponse)
    async def get_command_details(self, command: str):
        return await self.executor.execute("ClientReferenceData", 2, command)

    async def message_player(self, player_id: str, message: str):
        await self.executor.execute("SendServerMessage", 2, {
            "Message": message,
            "PlayerId": player_id,
        })

    async def kill_player(self, player_id: str, message: str):
        await self.executor.execute("PunishPlayer", 2, {
            "PlayerId": player_id,
            "Reason": message,
        })

    async def kick_player(self, player_id: str, message: str):
        await self.executor.execute("Kick", 2, {
            "PlayerId": player_id,
            "Reason": message,
        })

    async def ban_player(self, player_id: str, reason: str, admin_name: str, duration_hours: int | None = None):
        if duration_hours:
            await self.executor.execute("TemporaryBan", 2, {
                "PlayerId": player_id,
                "Duration": duration_hours,
                "Reason": reason,
                "AdminName": admin_name,
            })
        else:
            await self.executor.execute("PermanentBan", 2, {
                "PlayerId": player_id,
                "Reason": reason,
                "AdminName": admin_name,
            })
    
    async def remove_temporary_ban(self, player_id: str):
        await self.executor.execute("RemoveTemporaryBan", 2, {
            "PlayerId": player_id,
        })

    async def remove_permanent_ban(self, player_id: str):
        await self.executor.execute("RemovePermanentBan", 2, {
            "PlayerId": player_id,
        })

    async def remove_ban(self, player_id: str):
        await asyncio.gather(
            self.remove_temporary_ban(player_id),
            self.remove_permanent_ban(player_id),
        )

    async def set_auto_balance_enabled(self, enabled: bool):
        await self.executor.execute("SetAutoBalance", 2, {
            "EnableAutoBalance": enabled,
        })

    async def set_auto_balance_threshold(self, player_threshold: int):
        await self.executor.execute("AutoBalanceThreshold", 2, {
            "AutoBalanceThreshold": player_threshold,
        })

    async def set_vote_kick_enabled(self, enabled: bool):
        await self.executor.execute("EnableVoteToKick", 2, {
            "Enabled": enabled,
        })

    async def reset_vote_kick_thresholds(self):
        await self.executor.execute("ResetVoteToKickThreshold", 2)

    async def set_vote_kick_thresholds(self, thresholds: list[tuple[int, int]]):
        await self.executor.execute("SetVoteToKickThreshold", 2, {
            "ThresholdValue": ",".join([f"{p},{v}" for p, v in thresholds]),
        })
