from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def _as_str(value: Any) -> str:
    return "" if value is None else str(value)


def _as_int(value: Any) -> int:
    return int(value) if value is not None else 0


def _as_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _as_bool(value: Any) -> bool:
    return bool(value)


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


@dataclass(slots=True)
class RpcRequest:
    """RPC request container.

    Attributes:
        request_id: Numeric request identifier.
        method: RPC method name.
        params: List of parameters for the request.
    """

    request_id: int
    method: str
    params: list[Any]


@dataclass(slots=True)
class RpcResponse:
    """RPC response container.

    Attributes:
        request_id: Numeric request identifier corresponding to the request.
        result: Result payload for the request.
        error: Error message if the request failed, otherwise None.
    """

    request_id: int
    result: Any
    error: str | None = None


@dataclass(slots=True)
class RpcCallback:
    """RPC callback/notification container.

    Attributes:
        method: Name of the callback method.
        params: Parameters passed with the callback.
    """

    method: str
    params: list[Any]


@dataclass(slots=True)
class StartServerInternetConfig:
    """Configuration for `StartServerInternet`."""

    login: str
    password: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "Login": self.login,
            "Password": self.password,
        }


@dataclass(slots=True)
class LocalizedText:
    """Localized chat or server-message entry."""

    lang: str
    text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "Lang": self.lang,
            "Text": self.text,
        }


@dataclass(slots=True)
class PlayerScore:
    """Score override entry for `ForceScores`."""

    player_id: int
    score: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "PlayerId": self.player_id,
            "Score": self.score,
        }


@dataclass(slots=True)
class ChallengeInfo:
    """Challenge (map) information model.

    Attributes:
        uid: Unique challenge identifier.
        name: Challenge name.
        file_name: Filename of the challenge.
        author: Author name.
        environment: Environment string.
        mood: Mood string.
        bronze_time: Bronze time in milliseconds.
        silver_time: Silver time in milliseconds.
        gold_time: Gold time in milliseconds.
        author_time: Author time in milliseconds.
        copper_price: Copper price value.
        lap_race: True if the challenge is a lap race.
        nb_laps: Number of laps.
        nb_checkpoints: Number of checkpoints.
    """

    uid: str
    name: str
    file_name: str
    author: str
    environment: str
    mood: str
    bronze_time: int
    silver_time: int
    gold_time: int
    author_time: int
    copper_price: int
    lap_race: bool
    nb_laps: int
    nb_checkpoints: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChallengeInfo":
        return cls(
            uid=_as_str(data.get("Uid")),
            name=_as_str(data.get("Name")),
            file_name=_as_str(data.get("FileName")),
            author=_as_str(data.get("Author")),
            environment=_as_str(data.get("Environnement")),
            mood=_as_str(data.get("Mood")),
            bronze_time=_as_int(data.get("BronzeTime")),
            silver_time=_as_int(data.get("SilverTime")),
            gold_time=_as_int(data.get("GoldTime")),
            author_time=_as_int(data.get("AuthorTime")),
            copper_price=_as_int(data.get("CopperPrice")),
            lap_race=_as_bool(data.get("LapRace")),
            nb_laps=_as_int(data.get("NbLaps")),
            nb_checkpoints=_as_int(data.get("NbCheckpoints")),
        )


@dataclass(slots=True)
class PlayerRanking:
    """Player ranking information for a finished race.

    Attributes:
        login: Player login/name.
        nick_name: Player nickname.
        player_id: Numeric player id.
        rank: Finishing rank.
        best_time: Best time in milliseconds.
        best_checkpoints: List of best checkpoint times/scores.
        score: Player score.
        nbr_laps_finished: Number of laps finished.
        ladder_score: Ladder score as float.
    """

    login: str
    nick_name: str
    player_id: int
    rank: int
    best_time: int
    best_checkpoints: list[int]
    score: int
    nbr_laps_finished: int
    ladder_score: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerRanking":
        return cls(
            login=_as_str(data.get("Login")),
            nick_name=_as_str(data.get("NickName")),
            player_id=_as_int(data.get("PlayerId")),
            rank=_as_int(data.get("Rank")),
            best_time=_as_int(data.get("BestTime")),
            best_checkpoints=[_as_int(item) for item in _as_list(data.get("BestCheckpoints"))],
            score=_as_int(data.get("Score")),
            nbr_laps_finished=_as_int(data.get("NbrLapsFinished")),
            ladder_score=_as_float(data.get("LadderScore")),
        )


@dataclass(slots=True)
class PlayerInfo:
    """Player information model.

    Attributes:
        login: Player login/name.
        nick_name: Player nickname.
        player_id: Numeric player id.
        team_id: Team id number.
        spectator_status: Spectator status code.
        ladder_ranking: Ladder ranking value.
        flags: Player flags bitmask.
    """

    login: str
    nick_name: str
    player_id: int
    team_id: int
    spectator_status: int
    ladder_ranking: int
    flags: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerInfo":
        return cls(
            login=_as_str(data.get("Login")),
            nick_name=_as_str(data.get("NickName")),
            player_id=_as_int(data.get("PlayerId")),
            team_id=_as_int(data.get("TeamId")),
            spectator_status=_as_int(data.get("SpectatorStatus")),
            ladder_ranking=_as_int(data.get("LadderRanking")),
            flags=_as_int(data.get("Flags")),
        )


@dataclass(slots=True)
class VersionInfo:
    """Remote application version information."""

    name: str
    version: str
    build: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VersionInfo":
        return cls(
            name=_as_str(data.get("Name")),
            version=_as_str(data.get("Version")),
            build=_as_str(data.get("Build")),
        )


@dataclass(slots=True)
class CallVoteInfo:
    """Current call vote information."""

    caller_login: str
    cmd_name: str
    cmd_param: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CallVoteInfo":
        return cls(
            caller_login=_as_str(data.get("CallerLogin")),
            cmd_name=_as_str(data.get("CmdName")),
            cmd_param=_as_str(data.get("CmdParam")),
        )


@dataclass(slots=True)
class IntSetting:
    """Current and next integer configuration values."""

    current_value: int
    next_value: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IntSetting":
        return cls(
            current_value=_as_int(data.get("CurrentValue")),
            next_value=_as_int(data.get("NextValue")),
        )


@dataclass(slots=True)
class BoolSetting:
    """Current and next boolean configuration values."""

    current_value: bool
    next_value: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BoolSetting":
        return cls(
            current_value=_as_bool(data.get("CurrentValue")),
            next_value=_as_bool(data.get("NextValue")),
        )


@dataclass(slots=True)
class ManialinkPageAnswer:
    """Answer payload for a displayed manialink page."""

    login: str
    player_id: int
    result: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ManialinkPageAnswer":
        return cls(
            login=_as_str(data.get("Login")),
            player_id=_as_int(data.get("PlayerId")),
            result=_as_int(data.get("Result")),
        )


@dataclass(slots=True)
class BanListEntry:
    """One entry from the server ban list."""

    login: str
    client_name: str
    ip_address: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BanListEntry":
        return cls(
            login=_as_str(data.get("Login")),
            client_name=_as_str(data.get("ClientName")),
            ip_address=_as_str(data.get("IPAddress")),
        )


@dataclass(slots=True)
class LoginEntry:
    """One entry containing only a login string."""

    login: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LoginEntry":
        return cls(login=_as_str(data.get("Login")))


@dataclass(slots=True)
class BillState:
    """State information for a bill."""

    state: int
    state_name: str
    transaction_id: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BillState":
        return cls(
            state=_as_int(data.get("State")),
            state_name=_as_str(data.get("StateName")),
            transaction_id=_as_int(data.get("TransactionId")),
        )


@dataclass(slots=True)
class SystemInfo:
    """System information returned by the GBX server.

    The exact field set differs across game/server versions, so the raw
    mapping is preserved here.
    """

    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SystemInfo":
        return cls(raw=dict(data))


@dataclass(slots=True)
class StatusInfo:
    """Server status information.

    The exact field set differs across game/server versions, so the raw
    mapping is preserved here.
    """

    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StatusInfo":
        return cls(raw=dict(data))


@dataclass(slots=True)
class LadderServerLimits:
    """Ladder point limits allowed on the server."""

    ladder_server_limit_min: int
    ladder_server_limit_max: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LadderServerLimits":
        return cls(
            ladder_server_limit_min=_as_int(data.get("LadderServerLimitMin")),
            ladder_server_limit_max=_as_int(data.get("LadderServerLimitMax")),
        )


@dataclass(slots=True)
class ForcedMod:
    """Forced mod entry for one environment."""

    environment_name: str
    url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForcedMod":
        return cls(
            environment_name=_as_str(data.get("EnvName")),
            url=_as_str(data.get("Url")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "EnvName": self.environment_name,
            "Url": self.url,
        }


@dataclass(slots=True)
class ForcedMods:
    """Forced mod settings."""

    override: bool
    mods: list[ForcedMod]
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForcedMods":
        return cls(
            override=_as_bool(data.get("Override")),
            mods=[ForcedMod.from_dict(_as_dict(item)) for item in _as_list(data.get("Mods"))],
            raw=dict(data),
        )


@dataclass(slots=True)
class ForcedMusic:
    """Forced music settings.

    The server response shape is not fully specified by the XML-RPC docs, so
    the parsed raw mapping is preserved in addition to common fields.
    """

    override: bool
    url_or_file_name: str
    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForcedMusic":
        return cls(
            override=_as_bool(data.get("Override")),
            url_or_file_name=_as_str(
                data.get("UrlOrFileName", data.get("Music", data.get("FileName")))
            ),
            raw=dict(data),
        )


@dataclass(slots=True)
class ForcedSkin:
    """Forced skin remapping entry."""

    orig: str
    name: str
    checksum: str
    url: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ForcedSkin":
        return cls(
            orig=_as_str(data.get("Orig")),
            name=_as_str(data.get("Name")),
            checksum=_as_str(data.get("Checksum")),
            url=_as_str(data.get("Url")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "Orig": self.orig,
            "Name": self.name,
            "Checksum": self.checksum,
            "Url": self.url,
        }


@dataclass(slots=True)
class ServerOptionsUpdate:
    """Configuration payload for `SetServerOptions`."""

    name: str
    comment: str
    password: str
    password_for_spectator: str
    next_max_players: int
    next_max_spectators: int
    is_p2p_upload: bool
    is_p2p_download: bool
    next_ladder_mode: int
    next_vehicle_net_quality: int
    next_call_vote_timeout: int
    call_vote_ratio: float
    allow_challenge_download: bool
    auto_save_replays: bool
    referee_password: str | None = None
    referee_mode: int | None = None
    auto_save_validation_replays: bool | None = None
    hide_server: int | None = None
    use_changing_validation_seed: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "Name": self.name,
            "Comment": self.comment,
            "Password": self.password,
            "PasswordForSpectator": self.password_for_spectator,
            "NextMaxPlayers": self.next_max_players,
            "NextMaxSpectators": self.next_max_spectators,
            "IsP2PUpload": self.is_p2p_upload,
            "IsP2PDownload": self.is_p2p_download,
            "NextLadderMode": self.next_ladder_mode,
            "NextVehicleNetQuality": self.next_vehicle_net_quality,
            "NextCallVoteTimeOut": self.next_call_vote_timeout,
            "CallVoteRatio": self.call_vote_ratio,
            "AllowChallengeDownload": self.allow_challenge_download,
            "AutoSaveReplays": self.auto_save_replays,
        }
        if self.referee_password is not None:
            data["RefereePassword"] = self.referee_password
        if self.referee_mode is not None:
            data["RefereeMode"] = self.referee_mode
        if self.auto_save_validation_replays is not None:
            data["AutoSaveValidationReplays"] = self.auto_save_validation_replays
        if self.hide_server is not None:
            data["HideServer"] = self.hide_server
        if self.use_changing_validation_seed is not None:
            data["UseChangingValidationSeed"] = self.use_changing_validation_seed
        return data


@dataclass(slots=True)
class ServerOptions:
    """Server options returned by `GetServerOptions`."""

    name: str
    comment: str
    password: str
    password_for_spectator: str
    current_max_players: int
    next_max_players: int
    current_max_spectators: int
    next_max_spectators: int
    is_p2p_upload: bool
    is_p2p_download: bool
    current_ladder_mode: int
    next_ladder_mode: int
    current_vehicle_net_quality: int
    next_vehicle_net_quality: int
    current_call_vote_timeout: int
    next_call_vote_timeout: int
    call_vote_ratio: float
    allow_challenge_download: bool
    auto_save_replays: bool
    referee_password: str
    referee_mode: int
    auto_save_validation_replays: bool
    hide_server: int
    current_use_changing_validation_seed: bool
    next_use_changing_validation_seed: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ServerOptions":
        return cls(
            name=_as_str(data.get("Name")),
            comment=_as_str(data.get("Comment")),
            password=_as_str(data.get("Password")),
            password_for_spectator=_as_str(data.get("PasswordForSpectator")),
            current_max_players=_as_int(data.get("CurrentMaxPlayers")),
            next_max_players=_as_int(data.get("NextMaxPlayers")),
            current_max_spectators=_as_int(data.get("CurrentMaxSpectators")),
            next_max_spectators=_as_int(data.get("NextMaxSpectators")),
            is_p2p_upload=_as_bool(data.get("IsP2PUpload")),
            is_p2p_download=_as_bool(data.get("IsP2PDownload")),
            current_ladder_mode=_as_int(data.get("CurrentLadderMode")),
            next_ladder_mode=_as_int(data.get("NextLadderMode")),
            current_vehicle_net_quality=_as_int(data.get("CurrentVehicleNetQuality")),
            next_vehicle_net_quality=_as_int(data.get("NextVehicleNetQuality")),
            current_call_vote_timeout=_as_int(data.get("CurrentCallVoteTimeOut")),
            next_call_vote_timeout=_as_int(data.get("NextCallVoteTimeOut")),
            call_vote_ratio=_as_float(data.get("CallVoteRatio")),
            allow_challenge_download=_as_bool(data.get("AllowChallengeDownload")),
            auto_save_replays=_as_bool(data.get("AutoSaveReplays")),
            referee_password=_as_str(data.get("RefereePassword")),
            referee_mode=_as_int(data.get("RefereeMode")),
            auto_save_validation_replays=_as_bool(data.get("AutoSaveValidationReplays")),
            hide_server=_as_int(data.get("HideServer")),
            current_use_changing_validation_seed=_as_bool(
                data.get("CurrentUseChangingValidationSeed")
            ),
            next_use_changing_validation_seed=_as_bool(data.get("NextUseChangingValidationSeed")),
        )


@dataclass(slots=True)
class GameInfo:
    """Game mode settings for the current or next challenge."""

    game_mode: int
    chat_time: int
    nb_challenge: int
    rounds_points_limit: int
    rounds_use_new_rules: bool
    rounds_forced_laps: int
    time_attack_limit: int
    time_attack_synch_start_period: int
    team_points_limit: int
    team_max_points: int
    team_use_new_rules: bool
    laps_nb_laps: int
    laps_time_limit: int
    finish_timeout: int
    all_warm_up_duration: int
    disable_respawn: bool
    force_show_all_opponents: int
    rounds_points_limit_new_rules: int
    team_points_limit_new_rules: int
    cup_points_limit: int
    cup_rounds_per_challenge: int
    cup_nb_winners: int
    cup_warm_up_duration: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameInfo":
        return cls(
            game_mode=_as_int(data.get("GameMode")),
            chat_time=_as_int(data.get("ChatTime")),
            nb_challenge=_as_int(data.get("NbChallenge")),
            rounds_points_limit=_as_int(data.get("RoundsPointsLimit")),
            rounds_use_new_rules=_as_bool(data.get("RoundsUseNewRules")),
            rounds_forced_laps=_as_int(data.get("RoundsForcedLaps")),
            time_attack_limit=_as_int(data.get("TimeAttackLimit")),
            time_attack_synch_start_period=_as_int(data.get("TimeAttackSynchStartPeriod")),
            team_points_limit=_as_int(data.get("TeamPointsLimit")),
            team_max_points=_as_int(data.get("TeamMaxPoints")),
            team_use_new_rules=_as_bool(data.get("TeamUseNewRules")),
            laps_nb_laps=_as_int(data.get("LapsNbLaps")),
            laps_time_limit=_as_int(data.get("LapsTimeLimit")),
            finish_timeout=_as_int(data.get("FinishTimeout")),
            all_warm_up_duration=_as_int(data.get("AllWarmUpDuration")),
            disable_respawn=_as_bool(data.get("DisableRespawn")),
            force_show_all_opponents=_as_int(data.get("ForceShowAllOpponents")),
            rounds_points_limit_new_rules=_as_int(data.get("RoundsPointsLimitNewRules")),
            team_points_limit_new_rules=_as_int(data.get("TeamPointsLimitNewRules")),
            cup_points_limit=_as_int(data.get("CupPointsLimit")),
            cup_rounds_per_challenge=_as_int(data.get("CupRoundsPerChallenge")),
            cup_nb_winners=_as_int(data.get("CupNbWinners")),
            cup_warm_up_duration=_as_int(data.get("CupWarmUpDuration")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "GameMode": self.game_mode,
            "ChatTime": self.chat_time,
            "NbChallenge": self.nb_challenge,
            "RoundsPointsLimit": self.rounds_points_limit,
            "RoundsUseNewRules": self.rounds_use_new_rules,
            "RoundsForcedLaps": self.rounds_forced_laps,
            "TimeAttackLimit": self.time_attack_limit,
            "TimeAttackSynchStartPeriod": self.time_attack_synch_start_period,
            "TeamPointsLimit": self.team_points_limit,
            "TeamMaxPoints": self.team_max_points,
            "TeamUseNewRules": self.team_use_new_rules,
            "LapsNbLaps": self.laps_nb_laps,
            "LapsTimeLimit": self.laps_time_limit,
            "FinishTimeout": self.finish_timeout,
            "AllWarmUpDuration": self.all_warm_up_duration,
            "DisableRespawn": self.disable_respawn,
            "ForceShowAllOpponents": self.force_show_all_opponents,
            "RoundsPointsLimitNewRules": self.rounds_points_limit_new_rules,
            "TeamPointsLimitNewRules": self.team_points_limit_new_rules,
            "CupPointsLimit": self.cup_points_limit,
            "CupRoundsPerChallenge": self.cup_rounds_per_challenge,
            "CupNbWinners": self.cup_nb_winners,
            "CupWarmUpDuration": self.cup_warm_up_duration,
        }


@dataclass(slots=True)
class GameInfoSettings:
    """Configuration payload for `SetGameInfos`."""

    game_mode: int
    chat_time: int
    rounds_points_limit: int
    rounds_use_new_rules: bool
    rounds_forced_laps: int
    time_attack_limit: int
    time_attack_synch_start_period: int
    team_points_limit: int
    team_max_points: int
    team_use_new_rules: bool
    laps_nb_laps: int
    laps_time_limit: int
    finish_timeout: int
    all_warm_up_duration: int | None = None
    disable_respawn: bool | None = None
    force_show_all_opponents: int | None = None
    rounds_points_limit_new_rules: int | None = None
    team_points_limit_new_rules: int | None = None
    cup_points_limit: int | None = None
    cup_rounds_per_challenge: int | None = None
    cup_nb_winners: int | None = None
    cup_warm_up_duration: int | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "GameMode": self.game_mode,
            "ChatTime": self.chat_time,
            "RoundsPointsLimit": self.rounds_points_limit,
            "RoundsUseNewRules": self.rounds_use_new_rules,
            "RoundsForcedLaps": self.rounds_forced_laps,
            "TimeAttackLimit": self.time_attack_limit,
            "TimeAttackSynchStartPeriod": self.time_attack_synch_start_period,
            "TeamPointsLimit": self.team_points_limit,
            "TeamMaxPoints": self.team_max_points,
            "TeamUseNewRules": self.team_use_new_rules,
            "LapsNbLaps": self.laps_nb_laps,
            "LapsTimeLimit": self.laps_time_limit,
            "FinishTimeout": self.finish_timeout,
        }
        if self.all_warm_up_duration is not None:
            data["AllWarmUpDuration"] = self.all_warm_up_duration
        if self.disable_respawn is not None:
            data["DisableRespawn"] = self.disable_respawn
        if self.force_show_all_opponents is not None:
            data["ForceShowAllOpponents"] = self.force_show_all_opponents
        if self.rounds_points_limit_new_rules is not None:
            data["RoundsPointsLimitNewRules"] = self.rounds_points_limit_new_rules
        if self.team_points_limit_new_rules is not None:
            data["TeamPointsLimitNewRules"] = self.team_points_limit_new_rules
        if self.cup_points_limit is not None:
            data["CupPointsLimit"] = self.cup_points_limit
        if self.cup_rounds_per_challenge is not None:
            data["CupRoundsPerChallenge"] = self.cup_rounds_per_challenge
        if self.cup_nb_winners is not None:
            data["CupNbWinners"] = self.cup_nb_winners
        if self.cup_warm_up_duration is not None:
            data["CupWarmUpDuration"] = self.cup_warm_up_duration
        return data


@dataclass(slots=True)
class GameInfos:
    """Current and next game settings."""

    current_game_infos: GameInfo
    next_game_infos: GameInfo

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GameInfos":
        return cls(
            current_game_infos=GameInfo.from_dict(_as_dict(data.get("CurrentGameInfos"))),
            next_game_infos=GameInfo.from_dict(_as_dict(data.get("NextGameInfos"))),
        )


@dataclass(slots=True)
class FileRef:
    """File reference structure used for avatars and skin pack descriptions."""

    file_name: str
    checksum: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FileRef":
        return cls(
            file_name=_as_str(data.get("FileName")),
            checksum=_as_str(data.get("Checksum")),
        )


@dataclass(slots=True)
class PlayerSkin:
    """Skin information for one environment."""

    environment: str
    pack_desc: FileRef

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerSkin":
        return cls(
            environment=_as_str(data.get("Environnement")),
            pack_desc=FileRef.from_dict(_as_dict(data.get("PackDesc"))),
        )


@dataclass(slots=True)
class LadderStats:
    """Player ladder statistics.

    The XML-RPC docs only name this nested struct, so the raw mapping is
    preserved.
    """

    raw: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LadderStats":
        return cls(raw=dict(data))


@dataclass(slots=True)
class DetailedPlayerInfo:
    """Extended player information."""

    login: str
    nick_name: str
    player_id: int
    team_id: int
    ip_address: str
    download_rate: int
    upload_rate: int
    language: str
    is_spectator: bool
    is_in_official_mode: bool
    avatar: FileRef
    skins: list[PlayerSkin]
    ladder_stats: LadderStats
    hours_since_zone_inscription: int
    online_rights: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DetailedPlayerInfo":
        return cls(
            login=_as_str(data.get("Login")),
            nick_name=_as_str(data.get("NickName")),
            player_id=_as_int(data.get("PlayerId")),
            team_id=_as_int(data.get("TeamId")),
            ip_address=_as_str(data.get("IPAddress")),
            download_rate=_as_int(data.get("DownloadRate")),
            upload_rate=_as_int(data.get("UploadRate")),
            language=_as_str(data.get("Language")),
            is_spectator=_as_bool(data.get("IsSpectator")),
            is_in_official_mode=_as_bool(data.get("IsInOfficialMode")),
            avatar=FileRef.from_dict(_as_dict(data.get("Avatar"))),
            skins=[PlayerSkin.from_dict(_as_dict(item)) for item in _as_list(data.get("Skins"))],
            ladder_stats=LadderStats.from_dict(_as_dict(data.get("LadderStats"))),
            hours_since_zone_inscription=_as_int(data.get("HoursSinceZoneInscription")),
            online_rights=_as_int(data.get("OnlineRights")),
        )


@dataclass(slots=True)
class PlayerNetInfo:
    """Per-player network statistics."""

    login: str
    ip_address: str
    last_transfer_time: int
    delta_between_two_last_net_state: int
    packet_loss_rate: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlayerNetInfo":
        return cls(
            login=_as_str(data.get("Login")),
            ip_address=_as_str(data.get("IPAddress")),
            last_transfer_time=_as_int(data.get("LastTransferTime")),
            delta_between_two_last_net_state=_as_int(data.get("DeltaBetweenTwoLastNetState")),
            packet_loss_rate=_as_float(data.get("PacketLossRate")),
        )


@dataclass(slots=True)
class NetworkStats:
    """Server-wide network statistics."""

    uptime: int
    nbr_connection: int
    mean_connection_time: int
    mean_nbr_player: int
    recv_net_rate: int
    send_net_rate: int
    total_receiving_size: int
    total_sending_size: int
    player_net_infos: list[PlayerNetInfo]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "NetworkStats":
        return cls(
            uptime=_as_int(data.get("Uptime")),
            nbr_connection=_as_int(data.get("NbrConnection")),
            mean_connection_time=_as_int(data.get("MeanConnectionTime")),
            mean_nbr_player=_as_int(data.get("MeanNbrPlayer")),
            recv_net_rate=_as_int(data.get("RecvNetRate")),
            send_net_rate=_as_int(data.get("SendNetRate")),
            total_receiving_size=_as_int(data.get("TotalReceivingSize")),
            total_sending_size=_as_int(data.get("TotalSendingSize")),
            player_net_infos=[
                PlayerNetInfo.from_dict(_as_dict(item))
                for item in _as_list(data.get("PlayerNetInfos"))
            ],
        )
