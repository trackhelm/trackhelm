from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field
import re
from typing import Any
from typing import Callable
from typing import ClassVar
from typing import Optional
from typing import Type
from typing import TYPE_CHECKING
from typing import TypeVar


if TYPE_CHECKING:
    from trackhelm.gbx import models as gbx_models


@dataclass(slots=True)
class Event:
    """Raw event container with name and untyped payload.

    Attributes:
        name: The event name provided by GBX.
        payload: Raw payload dict as received from the server.
    """

    name: str
    payload: dict[str, Any] = field(default_factory=dict)


E = TypeVar("E", bound="BaseEvent")


@dataclass(slots=True)
class BaseEvent:
    """Typed event base class. Concrete events should set `gbx_name` and typed fields."""

    # GBX callback name, e.g. "TrackMania.PlayerConnect"
    gbx_name: ClassVar[str] = ""

    @classmethod
    def from_gbx_params(cls: Type[E], params: list[Any]) -> E:
        # Default implementation maps positional params to dataclass fields.
        # Use string annotations to avoid importing GBX models at module import time.
        annotations = getattr(cls, "__annotations__", {})
        field_names = [n for n in annotations.keys() if n != "gbx_name"]

        # Lazy import models when needed to avoid circular imports
        gbx_models: Any = None

        def resolve_model_by_name(name: str) -> Any:
            nonlocal gbx_models
            if gbx_models is None:
                from trackhelm.gbx import models as gbx_models_local

                gbx_models = gbx_models_local

            return getattr(gbx_models, name, None)

        list_inner_re = re.compile(r"list\[(.+)\]")

        kwargs: dict[str, Any] = {}
        for idx, name in enumerate(field_names):
            expected_ann = annotations.get(name)
            if idx < len(params):
                val = params[idx]

                # handle list[...] annotations
                if isinstance(expected_ann, str):
                    m = list_inner_re.match(expected_ann)
                    if m:
                        inner_name = m.group(1).split(".")[-1]
                        inner_cls = resolve_model_by_name(inner_name)
                        if inner_cls and isinstance(val, list):
                            converted = []
                            for x in val:
                                converted.append(
                                    inner_cls.from_dict(x) if isinstance(x, dict) else x
                                )
                            kwargs[name] = converted
                            continue

                    # single model reference like 'gbx_models.PlayerInfo' or 'PlayerInfo'
                    simple = expected_ann.split(".")[-1]
                    model_cls = resolve_model_by_name(simple)
                    if model_cls and isinstance(val, dict):
                        kwargs[name] = model_cls.from_dict(val)
                        continue

                # default passthrough
                kwargs[name] = val
            else:
                kwargs[name] = None

        return cls(**kwargs)


# Registry for GBX callback name -> Event class
_EVENT_REGISTRY: dict[str, Type[BaseEvent]] = {}


def register_event(gbx_name: str) -> Callable[[Type[BaseEvent]], Type[BaseEvent]]:
    def _decorator(cls: Type[BaseEvent]) -> Type[BaseEvent]:
        cls.gbx_name = gbx_name
        _EVENT_REGISTRY[gbx_name] = cls
        return cls

    return _decorator


def lookup_event_class(gbx_name: str) -> Optional[Type[BaseEvent]]:
    return _EVENT_REGISTRY.get(gbx_name)


@register_event("TrackMania.PlayerConnect")
@dataclass(slots=True)
class PlayerConnect(BaseEvent):
    """Fired when a player connects to the server.

    Attributes:
        login: Player login/name.
        is_spectator: True if the player is connecting as a spectator.
    """

    login: str
    is_spectator: bool


@register_event("TrackMania.PlayerDisconnect")
@dataclass(slots=True)
class PlayerDisconnect(BaseEvent):
    """Fired when a player disconnects from the server.

    Attributes:
        login: Player login/name.
    """

    login: str


@register_event("TrackMania.PlayerChat")
@dataclass(slots=True)
class PlayerChat(BaseEvent):
    """Fired when a player sends a chat message.

    Attributes:
        player_uid: Unique player id.
        login: Player login/name.
        text: Chat message text.
        is_registred_cmd: Whether the message is a registered command.
    """

    player_uid: int
    login: str
    text: str
    is_registred_cmd: bool


@register_event("TrackMania.PlayerManialinkPageAnswer")
@dataclass(slots=True)
class PlayerManialinkPageAnswer(BaseEvent):
    """Fired when a player answers a Manialink page.

    Attributes:
        player_uid: Unique player id.
        login: Player login/name.
        answer: Selected answer index.
    """

    player_uid: int
    login: str
    answer: int


@register_event("TrackMania.Echo")
@dataclass(slots=True)
class Echo(BaseEvent):
    """Echo event used for internal/public messages from the server.

    Attributes:
        internal: Internal message string.
        public: Public message string.
    """

    internal: str
    public: str


@register_event("TrackMania.ServerStart")
@dataclass(slots=True)
class ServerStart(BaseEvent):
    """Fired when the server starts."""


@register_event("TrackMania.ServerStop")
@dataclass(slots=True)
class ServerStop(BaseEvent):
    """Fired when the server stops."""


@register_event("TrackMania.BeginRace")
@dataclass(slots=True)
class BeginRace(BaseEvent):
    """Fired when a race begins.

    Attributes:
        challenge: Challenge info model.
    """

    challenge: gbx_models.ChallengeInfo


@register_event("TrackMania.EndRace")
@dataclass(slots=True)
class EndRace(BaseEvent):
    """Fired when a race ends.

    Attributes:
        rankings: List of player rankings.
        challenge: Challenge info model.
    """

    rankings: list[gbx_models.PlayerRanking]
    challenge: gbx_models.ChallengeInfo


@register_event("TrackMania.BeginChallenge")
@dataclass(slots=True)
class BeginChallenge(BaseEvent):
    """Fired when a challenge begins.

    Attributes:
        challenge: Challenge info model.
        warm_up: True if this is a warm-up.
        match_continuation: True if this continues a previous match.
    """

    challenge: gbx_models.ChallengeInfo
    warm_up: bool
    match_continuation: bool


@register_event("TrackMania.EndChallenge")
@dataclass(slots=True)
class EndChallenge(BaseEvent):
    """Fired when a challenge ends.

    Attributes:
        rankings: List of player rankings.
        challenge: Challenge info model.
        was_warm_up: True if it was a warm-up.
        match_continues_on_next_challenge: True if match continues.
        restart_challenge: True if the challenge will be restarted.
    """

    rankings: list[gbx_models.PlayerRanking]
    challenge: gbx_models.ChallengeInfo
    was_warm_up: bool
    match_continues_on_next_challenge: bool
    restart_challenge: bool


@register_event("TrackMania.BeginRound")
@dataclass(slots=True)
class BeginRound(BaseEvent):
    """Fired when a round begins."""


@register_event("TrackMania.EndRound")
@dataclass(slots=True)
class EndRound(BaseEvent):
    """Fired when a round ends."""


@register_event("TrackMania.StatusChanged")
@dataclass(slots=True)
class StatusChanged(BaseEvent):
    """Fired when the server status changes.

    Attributes:
        status_code: Numeric status code.
        status_name: Human readable status name.
    """

    status_code: int
    status_name: str


@register_event("TrackMania.PlayerCheckpoint")
@dataclass(slots=True)
class PlayerCheckpoint(BaseEvent):
    """Fired when a player hits a checkpoint.

    Attributes:
        player_uid: Unique player id.
        login: Player login/name.
        time_or_score: Time or score value.
        cur_lap: Current lap index.
        checkpoint_index: Index of the checkpoint.
    """

    player_uid: int
    login: str
    time_or_score: int
    cur_lap: int
    checkpoint_index: int


@register_event("TrackMania.PlayerFinish")
@dataclass(slots=True)
class PlayerFinish(BaseEvent):
    """Fired when a player finishes a race.

    Attributes:
        player_uid: Unique player id.
        login: Player login/name.
        time_or_score: Time or score value.
    """

    player_uid: int
    login: str
    time_or_score: int


@register_event("TrackMania.PlayerIncoherence")
@dataclass(slots=True)
class PlayerIncoherence(BaseEvent):
    """Fired when a player's state becomes incoherent.

    Attributes:
        player_uid: Unique player id.
        login: Player login/name.
    """

    player_uid: int
    login: str


@register_event("TrackMania.BillUpdated")
@dataclass(slots=True)
class BillUpdated(BaseEvent):
    """Fired when a bill/transaction is updated.

    Attributes:
        bill_id: Bill identifier.
        state: State code.
        state_name: State name.
        transaction_id: Associated transaction id.
    """

    bill_id: int
    state: int
    state_name: str
    transaction_id: int


@register_event("TrackMania.TunnelDataReceived")
@dataclass(slots=True)
class TunnelDataReceived(BaseEvent):
    """Fired when tunnel data is received from a player.

    Attributes:
        player_uid: Unique player id.
        login: Player login/name.
        data: Raw tunnel data string.
    """

    player_uid: int
    login: str
    data: str


@register_event("TrackMania.ChallengeListModified")
@dataclass(slots=True)
class ChallengeListModified(BaseEvent):
    """Fired when the challenge list is modified.

    Attributes:
        cur_challenge_index: Current challenge index.
        next_challenge_index: Next challenge index.
        is_list_modified: True if the list was modified.
    """

    cur_challenge_index: int
    next_challenge_index: int
    is_list_modified: bool


@register_event("TrackMania.PlayerInfoChanged")
@dataclass(slots=True)
class PlayerInfoChanged(BaseEvent):
    """Fired when player information is changed.

    Attributes:
        player_info: Player info model.
    """

    player_info: gbx_models.PlayerInfo


@register_event("TrackMania.ManualFlowControlTransition")
@dataclass(slots=True)
class ManualFlowControlTransition(BaseEvent):
    """Fired on manual flow control transitions.

    Attributes:
        transition: Transition identifier or name.
    """

    transition: str


@register_event("TrackMania.VoteUpdated")
@dataclass(slots=True)
class VoteUpdated(BaseEvent):
    """Fired when a vote is updated.

    Attributes:
        state_name: Name of the vote state.
        login: Player login/name who voted.
        cmd_name: Command name associated with the vote.
        cmd_param: Command parameter associated with the vote.
    """

    state_name: str
    login: str
    cmd_name: str
    cmd_param: str
