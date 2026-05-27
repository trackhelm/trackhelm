from __future__ import annotations

from typing import Any
from typing import List
from typing import Optional

from .models import BanListEntry
from .models import BillState
from .models import BoolSetting
from .models import CallVoteInfo
from .models import ChallengeInfo
from .models import DetailedPlayerInfo
from .models import ForcedMod
from .models import ForcedMods
from .models import ForcedMusic
from .models import ForcedSkin
from .models import GameInfo
from .models import GameInfos
from .models import GameInfoSettings
from .models import IntSetting
from .models import LadderServerLimits
from .models import LocalizedText
from .models import LoginEntry
from .models import ManialinkPageAnswer
from .models import NetworkStats
from .models import PlayerInfo
from .models import PlayerRanking
from .models import PlayerScore
from .models import ServerOptions
from .models import ServerOptionsUpdate
from .models import StartServerInternetConfig
from .models import StatusInfo
from .models import SystemInfo
from .models import VersionInfo


class GbxMethodsMixin:
    """Minimal typed wrappers around the GBX XML-RPC methods.

    These are thin, runtime-light adapters over `GbxClient.call()` that
    coerce the dynamic XML-RPC results into convenient Python types.
    Use by subclassing: ``class TypedGbxClient(GbxMethodsMixin, GbxClient): ...``
    """

    async def call(
        self,
        method: str,
        params: list[Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        raise NotImplementedError

    async def authenticate(self, username: str, password: str) -> bool:
        """Authenticate with the server.

        Returns True on success, False otherwise.
        """
        result = await self.call("Authenticate", [username, password])
        return bool(result)

    async def change_auth_password(self, login: str, new_password: str) -> bool:
        """Change password for a login. Returns boolean success."""
        result = await self.call("ChangeAuthPassword", [login, new_password])
        return bool(result)

    async def enable_callbacks(self, enable: bool) -> bool:
        """Enable or disable callbacks from the server."""
        result = await self.call("EnableCallbacks", [enable])
        return bool(result)

    async def list_methods(self) -> List[str]:
        """Return a list of available XML-RPC methods."""
        result = await self.call("system.listMethods", [])
        if not result:
            return []
        return [str(x) for x in result]

    async def method_signature(self, name: str) -> List[List[str]]:
        """Return method signatures for `name` as a list of string lists."""
        result = await self.call("system.methodSignature", [name])
        if not result:
            return []
        return [[str(i) for i in sig] for sig in result]

    async def method_help(self, name: str) -> str:
        """Return the help string for `name`."""
        result = await self.call("system.methodHelp", [name])
        return "" if result is None else str(result)

    async def multicall(self, calls: List[tuple[str, list[Any]]]) -> Any:
        """Execute multiple XML-RPC calls in a single request.

        `calls` should be a list of tuples `(method_name, params)`; each tuple
        will be converted into the struct expected by the XML-RPC
        `system.multicall` method. Returns the raw multicall result.
        """
        return await self.call(
            "system.multicall", [[{"methodName": m, "params": p} for m, p in calls]]
        )

    async def get_version(self) -> VersionInfo:
        """Return a struct describing the remote server version.

        The returned mapping typically contains keys such as
        'Name', 'Version' and 'Build'. An empty dict is returned on
        unexpected/None responses.
        """
        result = await self.call("GetVersion", [])
        return VersionInfo.from_dict({} if result is None else dict(result))

    async def call_vote(self, cmd: str) -> bool:
        """Start a standard call vote using the given XML command string.

        Returns True on success, False otherwise.
        """
        result = await self.call("CallVote", [cmd])
        return bool(result)

    async def call_vote_ex(self, cmd: str, ratio: float, timeout: int, who: int) -> bool:
        """Start an extended call vote with additional parameters.

        `ratio` is the required passing ratio, `timeout` the vote timeout
        and `who` indicates who may vote. Returns True on success.
        """
        result = await self.call("CallVoteEx", [cmd, ratio, timeout, who])
        return bool(result)

    async def internal_call_vote(self) -> bool:
        """Trigger an internal call vote (used by the game internally).

        Returns True on success, False otherwise.
        """
        result = await self.call("InternalCallVote", [])
        return bool(result)

    async def cancel_vote(self) -> bool:
        """Cancel the currently active vote.

        Returns True on success, False otherwise.
        """
        result = await self.call("CancelVote", [])
        return bool(result)

    async def get_current_call_vote(self) -> CallVoteInfo:
        """Return information about the currently active call vote.

        The returned mapping generally contains fields like
        'CallerLogin', 'CmdName' and 'CmdParam'. An empty dict is returned
        when no vote is active or the response is None.
        """
        result = await self.call("GetCurrentCallVote", [])
        return CallVoteInfo.from_dict({} if result is None else dict(result))

    async def set_call_vote_timeout(self, timeout: int) -> bool:
        """Set the default timeout (in seconds) for call votes.

        A timeout of 0 disables call votes. Returns True on success.
        """
        result = await self.call("SetCallVoteTimeOut", [timeout])
        return bool(result)

    async def get_call_vote_timeout(self) -> IntSetting:
        """Get the current and next configured call vote timeouts.

        Returns a mapping with keys like 'CurrentValue' and 'NextValue'.
        """
        result = await self.call("GetCallVoteTimeOut", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_call_vote_ratio(self, ratio: float) -> bool:
        """Set the default ratio (0..1) required for a call vote to pass.

        Returns True on success.
        """
        result = await self.call("SetCallVoteRatio", [ratio])
        return bool(result)

    async def get_call_vote_ratio(self) -> float:
        """Return the current default call vote ratio as a float in [0, 1].

        Returns 0.0 if the response is None or cannot be converted.
        """
        result = await self.call("GetCallVoteRatio", [])
        return float(result) if result is not None else 0.0

    async def set_call_vote_ratios(self, ratios: list[Any]) -> bool:
        """Set specific ratios for individual call vote commands.

        `ratios` should be an array of structs like {Command, Ratio}.
        Returns True on success.
        """
        result = await self.call("SetCallVoteRatios", [ratios])
        return bool(result)

    async def get_call_vote_ratios(self) -> List[Any]:
        """Retrieve configured call vote ratios for specific commands.

        Returns a list of ratio mappings or an empty list on None.
        """
        result = await self.call("GetCallVoteRatios", [])
        return [] if result is None else list(result)

    async def chat_send_server_message(self, text: str) -> bool:
        """Send a server-originated chat message to all clients.

        The message is sent without a server login. Returns True on
        successful delivery.
        """
        result = await self.call("ChatSendServerMessage", [text])
        return bool(result)

    async def chat_send_server_message_to_language(
        self, texts: list[LocalizedText], login: Optional[str]
    ) -> bool:
        """Send localized server messages to clients.

        `texts` is an array of structures like {Lang, Text}. Optionally target
        a specific `login` (single or comma-separated list). Returns True on
        success.
        """
        localized_texts = [text.to_dict() for text in texts]
        params = [localized_texts, login] if login is not None else [localized_texts]
        result = await self.call("ChatSendServerMessageToLanguage", params)
        return bool(result)

    async def chat_send_server_message_to_id(self, text: str, player_id: int) -> bool:
        """Send a server-originated chat message to a player by id.

        Returns True on success.
        """
        result = await self.call("ChatSendServerMessageToId", [text, player_id])
        return bool(result)

    async def chat_send_server_message_to_login(self, text: str, login: str) -> bool:
        """Send a server-originated chat message to a player by login.

        `login` may be a single login or a comma-separated list. Returns True
        on success.
        """
        result = await self.call("ChatSendServerMessageToLogin", [text, login])
        return bool(result)

    async def chat_send(self, text: str) -> bool:
        """Send a chat message to all clients (as an admin action).

        Returns True on success.
        """
        result = await self.call("ChatSend", [text])
        return bool(result)

    async def chat_send_to_language(
        self, texts: list[LocalizedText], login: Optional[str]
    ) -> bool:
        """Send localized chat messages to clients or a particular login.

        `texts` is an array of {Lang, Text} structures. Optionally supply a
        `login` to limit recipients. Returns True on success.
        """
        localized_texts = [text.to_dict() for text in texts]
        params = [localized_texts, login] if login is not None else [localized_texts]
        result = await self.call("ChatSendToLanguage", params)
        return bool(result)

    async def chat_send_to_login(self, text: str, login: str) -> bool:
        """Send a chat message to a specific login (or list of logins).

        Returns True on success.
        """
        result = await self.call("ChatSendToLogin", [text, login])
        return bool(result)

    async def chat_send_to_id(self, text: str, player_id: int) -> bool:
        """Send a chat message to a specific player identified by id.

        Returns True on success.
        """
        result = await self.call("ChatSendToId", [text, player_id])
        return bool(result)

    async def get_chat_lines(self) -> List[Any]:
        """Return the most recent chat lines (up to server limit).

        Returns a list of chat line structures or an empty list on None.
        """
        result = await self.call("GetChatLines", [])
        return [] if result is None else list(result)

    async def get_player_info(self, login: str, struct_version: int = 1) -> PlayerInfo:
        """Return server-side player info for the given login.

        On TMNF/Nations-era servers this may include extra keys such as
        `Nation` in addition to the standard player info structure; those
        additional fields are ignored by the dataclass conversion.
        """
        result = await self.call("GetPlayerInfo", [login, struct_version])
        return PlayerInfo.from_dict({} if result is None else dict(result))

    async def chat_enable_manual_routing(
        self, enable: bool, auto_forward: Optional[bool] = None
    ) -> bool:
        """Enable or disable manual routing of chat messages.

        When enabled, chat messages are delivered to callbacks and must be
        forwarded manually. If `auto_forward` is True, server messages are
        automatically forwarded. Returns True on success.
        """
        params: list[Any] = [enable]
        if auto_forward is not None:
            params.append(auto_forward)
        result = await self.call("ChatEnableManualRouting", params)
        return bool(result)

    async def chat_forward_to_login(self, text: str, sender: str, dest: str) -> bool:
        """Forward a chat message on behalf of `sender` to `dest` login(s).

        `dest` may be empty (all) or a comma-separated list of logins. Returns
        True on success.
        """
        result = await self.call("ChatForwardToLogin", [text, sender, dest])
        return bool(result)

    async def send_notice(self, text: str, login: str, max_duration: Optional[int] = None) -> bool:
        """Display a notice to all clients, optionally with an avatar login.

        `max_duration` specifies how long (seconds) the notice should remain.
        Returns True on success.
        """
        params: list[Any] = [text, login]
        if max_duration is not None:
            params.append(max_duration)
        result = await self.call("SendNotice", params)
        return bool(result)

    async def send_notice_to_id(
        self, uid: int, text: str, avatar_uid: int, max_duration: Optional[int] = None
    ) -> bool:
        """Display a notice to a specific client by UId.

        `avatar_uid` selects the avatar to display beside the notice. Returns
        True on success.
        """
        params = [uid, text, avatar_uid]
        if max_duration is not None:
            params.append(max_duration)
        result = await self.call("SendNoticeToId", params)
        return bool(result)

    async def send_notice_to_login(
        self, login: str, text: str, avatar_login: str, max_duration: Optional[int] = None
    ) -> bool:
        """Display a notice to a client identified by login.

        `login` can be a single login or comma-separated list. Returns True on
        success.
        """
        params: list[Any] = [login, text, avatar_login]
        if max_duration is not None:
            params.append(max_duration)
        result = await self.call("SendNoticeToLogin", params)
        return bool(result)

    async def send_display_manialink_page(
        self, xml: str, timeout: int, hide_on_click: bool
    ) -> bool:
        """Display a manialink (XML) page to all clients.

        `timeout` is seconds (0 = permanent). `hide_on_click` indicates whether
        the page should hide when the user clicks. Returns True on success.
        """
        result = await self.call("SendDisplayManialinkPage", [xml, timeout, hide_on_click])
        return bool(result)

    async def send_display_manialink_page_to_id(
        self, uid: int, xml: str, timeout: int, hide_on_click: bool
    ) -> bool:
        """Display a manialink page to a specific client by UId.

        Returns True on success.
        """
        result = await self.call(
            "SendDisplayManialinkPageToId", [uid, xml, timeout, hide_on_click]
        )
        return bool(result)

    async def send_display_manialink_page_to_login(
        self, login: str, xml: str, timeout: int, hide_on_click: bool
    ) -> bool:
        """Display a manialink page to a client identified by login.

        `login` may be a comma-separated list. Returns True on success.
        """
        result = await self.call(
            "SendDisplayManialinkPageToLogin", [login, xml, timeout, hide_on_click]
        )
        return bool(result)

    async def send_hide_manialink_page(self) -> bool:
        """Hide any currently displayed manialink page for all clients.

        Returns True on success.
        """
        result = await self.call("SendHideManialinkPage", [])
        return bool(result)

    async def send_hide_manialink_page_to_id(self, uid: int) -> bool:
        """Hide the currently displayed manialink page for a specific client.

        Returns True on success.
        """
        result = await self.call("SendHideManialinkPageToId", [uid])
        return bool(result)

    async def send_hide_manialink_page_to_login(self, login: str) -> bool:
        """Hide the currently displayed manialink page for a client by login.

        Returns True on success.
        """
        result = await self.call("SendHideManialinkPageToLogin", [login])
        return bool(result)

    async def get_manialink_page_answers(self) -> List[ManialinkPageAnswer]:
        """Return the latest answers submitted on the current manialink page.

        Returns a list of mappings with fields such as 'Login', 'PlayerId' and
        'Result'. Empty list returned on None.
        """
        result = await self.call("GetManialinkPageAnswers", [])
        if result is None:
            return []
        return [ManialinkPageAnswer.from_dict(dict(item)) for item in result]

    async def kick(self, login: str, message: Optional[str] = None) -> bool:
        """Kick a player by login with an optional message.

        Returns True on success.
        """
        params = [login]
        if message is not None:
            params.append(message)
        result = await self.call("Kick", params)
        return bool(result)

    async def kick_id(self, player_id: int, message: Optional[str] = None) -> bool:
        """Kick a player by their numeric id with an optional message.

        Returns True on success.
        """
        params: list[Any] = [player_id]
        if message is not None:
            params.append(message)
        result = await self.call("KickId", params)
        return bool(result)

    async def ban(self, login: str, message: Optional[str] = None) -> bool:
        """Ban a player by login with an optional message.

        Returns True on success.
        """
        params: list[Any] = [login]
        if message is not None:
            params.append(message)
        result = await self.call("Ban", params)
        return bool(result)

    async def ban_and_blacklist(
        self, login: str, message: Optional[str] = None, save: Optional[bool] = None
    ) -> bool:
        """Ban and optionally blacklist a login; optionally save the list.

        Returns True on success.
        """
        params: list[Any] = [login]
        if message is not None:
            params.append(message)
        if save is not None:
            params.append(save)
        result = await self.call("BanAndBlackList", params)
        return bool(result)

    async def ban_id(self, player_id: int, message: Optional[str] = None) -> bool:
        """Ban a player by numeric id with an optional message.

        Returns True on success.
        """
        params: list[Any] = [player_id]
        if message is not None:
            params.append(message)
        result = await self.call("BanId", params)
        return bool(result)

    async def unban(self, client_name: str) -> bool:
        """Remove a ban for the client identified by name.

        Returns True on success.
        """
        result = await self.call("UnBan", [client_name])
        return bool(result)

    async def clean_ban_list(self) -> bool:
        """Clear all entries from the server's ban list.

        Returns True on success.
        """
        result = await self.call("CleanBanList", [])
        return bool(result)

    async def get_ban_list(self, max_infos: int, start: int) -> List[BanListEntry]:
        """Retrieve a slice of the ban list.

        `max_infos` is the maximum number of entries to return and `start` is
        the starting index. Returns a list of ban info mappings.
        """
        result = await self.call("GetBanList", [max_infos, start])
        if result is None:
            return []
        return [BanListEntry.from_dict(dict(item)) for item in result]

    async def blacklist(self, login: str) -> bool:
        """Add a login to the server blacklist.

        Returns True on success.
        """
        result = await self.call("BlackList", [login])
        return bool(result)

    async def blacklist_id(self, player_id: int) -> bool:
        """Add a player (by id) to the server blacklist.

        Returns True on success.
        """
        result = await self.call("BlackListId", [player_id])
        return bool(result)

    async def unblacklist(self, login: str) -> bool:
        """Remove a login from the server blacklist.

        Returns True on success.
        """
        result = await self.call("UnBlackList", [login])
        return bool(result)

    async def clean_blacklist(self) -> bool:
        """Clear all entries from the server's blacklist.

        Returns True on success.
        """
        result = await self.call("CleanBlackList", [])
        return bool(result)

    async def get_blacklist(self, max_infos: int, start: int) -> List[LoginEntry]:
        """Retrieve a slice of the server blacklist.

        `max_infos` and `start` control paging. Returns a list of blacklist
        entries or an empty list on None.
        """
        result = await self.call("GetBlackList", [max_infos, start])
        if result is None:
            return []
        return [LoginEntry.from_dict(dict(item)) for item in result]

    async def load_blacklist(self, filename: str) -> bool:
        """Load a blacklist from a file on the server.

        `filename` is the server-relative file to load. Returns True on
        success.
        """
        result = await self.call("LoadBlackList", [filename])
        return bool(result)

    async def save_blacklist(self, filename: str) -> bool:
        """Save the current blacklist to a file on the server.

        `filename` is the server-relative destination path. Returns True on
        success.
        """
        result = await self.call("SaveBlackList", [filename])
        return bool(result)

    async def add_guest(self, login: str) -> bool:
        """Add a login to the server guest list.

        Returns True on success.
        """
        result = await self.call("AddGuest", [login])
        return bool(result)

    async def add_guest_id(self, player_id: int) -> bool:
        """Add a player (by id) to the server guest list.

        Returns True on success.
        """
        result = await self.call("AddGuestId", [player_id])
        return bool(result)

    async def remove_guest(self, login: str) -> bool:
        """Remove a login from the server guest list.

        Returns True on success.
        """
        result = await self.call("RemoveGuest", [login])
        return bool(result)

    async def remove_guest_id(self, player_id: int) -> bool:
        """Remove a player (by id) from the server guest list.

        Returns True on success.
        """
        result = await self.call("RemoveGuestId", [player_id])
        return bool(result)

    async def clean_guest_list(self) -> bool:
        """Clear all entries from the server's guest list.

        Returns True on success.
        """
        result = await self.call("CleanGuestList", [])
        return bool(result)

    async def get_guest_list(self, max_infos: int, start: int) -> List[LoginEntry]:
        """Retrieve a slice of the guest list with paging parameters.

        Returns a list of guest info mappings or an empty list on None.
        """
        result = await self.call("GetGuestList", [max_infos, start])
        if result is None:
            return []
        return [LoginEntry.from_dict(dict(item)) for item in result]

    async def load_guest_list(self, filename: str) -> bool:
        """Load a guest list from a server-side file.

        Returns True on success.
        """
        result = await self.call("LoadGuestList", [filename])
        return bool(result)

    async def save_guest_list(self, filename: str) -> bool:
        """Save the current guest list to a server-side file.

        Returns True on success.
        """
        result = await self.call("SaveGuestList", [filename])
        return bool(result)

    async def set_buddy_notification(self, login: str, enabled: bool) -> bool:
        """Enable or disable buddy notifications for a given login.

        `login` may be an empty string to change the global default. Returns
        True on success.
        """
        result = await self.call("SetBuddyNotification", [login, enabled])
        return bool(result)

    async def get_buddy_notification(self, login: str) -> bool:
        """Return whether buddy notifications are enabled for `login`.

        `login` may be an empty string to query the global setting.
        """
        result = await self.call("GetBuddyNotification", [login])
        return bool(result)

    async def write_file(self, filename: str, data_base64: Any) -> bool:
        """Write base64-encoded data to a server-side file under Tracks path.

        Returns True on success.
        """
        result = await self.call("WriteFile", [filename, data_base64])
        return bool(result)

    async def tunnel_send_data_to_id(self, uid: int, data_base64: Any) -> bool:
        """Send raw base64-encoded tunnel data to a specific player id.

        Returns True on success.
        """
        result = await self.call("TunnelSendDataToId", [uid, data_base64])
        return bool(result)

    async def tunnel_send_data_to_login(self, login: str, data_base64: Any) -> bool:
        """Send raw base64-encoded tunnel data to client(s) by login.

        `login` may be a comma-separated list. Returns True on success.
        """
        result = await self.call("TunnelSendDataToLogin", [login, data_base64])
        return bool(result)

    async def echo(self, a: str, b: str) -> bool:
        """Send an echo call to the server which logs parameters and triggers callbacks.

        Useful for inter-client messages or custom vote messages. Returns True
        on success.
        """
        result = await self.call("Echo", [a, b])
        return bool(result)

    async def ignore(self, login: str) -> bool:
        """Add `login` to the ignore list.

        Returns True on success.
        """
        result = await self.call("Ignore", [login])
        return bool(result)

    async def ignore_id(self, player_id: int) -> bool:
        """Add a player (by id) to the ignore list.

        Returns True on success.
        """
        result = await self.call("IgnoreId", [player_id])
        return bool(result)

    async def unignore(self, login: str) -> bool:
        """Remove `login` from the ignore list.

        Returns True on success.
        """
        result = await self.call("UnIgnore", [login])
        return bool(result)

    async def unignore_id(self, player_id: int) -> bool:
        """Remove a player (by id) from the ignore list.

        Returns True on success.
        """
        result = await self.call("UnIgnoreId", [player_id])
        return bool(result)

    async def clean_ignore_list(self) -> bool:
        """Clear all entries from the server's ignore list.

        Returns True on success.
        """
        result = await self.call("CleanIgnoreList", [])
        return bool(result)

    async def get_ignore_list(self, max_infos: int, start: int) -> List[LoginEntry]:
        """Retrieve a slice of the ignore list.

        `max_infos` and `start` control paging. Returns a list of ignore info
        mappings or an empty list on None.
        """
        result = await self.call("GetIgnoreList", [max_infos, start])
        if result is None:
            return []
        return [LoginEntry.from_dict(dict(item)) for item in result]

    async def pay(self, login: str, coppers: int, label: str) -> int:
        """Pay `coppers` from the server account to `login` with a `label`.

        Returns the newly created BillId, or 0 on failure.
        """
        result = await self.call("Pay", [login, coppers, label])
        return int(result) if result is not None else 0

    async def send_bill(
        self, login_from: str, coppers: int, label: str, login_to: Optional[str] = None
    ) -> int:
        """Create and send a bill, returning the BillId.

        `login_from` is the payer, `login_to` optionally overrides the payee.
        Returns the BillId or 0 on failure.
        """
        params = [login_from, coppers, label]
        if login_to is not None:
            params.append(login_to)
        result = await self.call("SendBill", params)
        return int(result) if result is not None else 0

    async def get_bill_state(self, bill_id: int) -> BillState:
        """Return the current state of a bill identified by `bill_id`.

        The returned mapping contains fields such as 'State', 'StateName' and
        'TransactionId'. An empty dict is returned on None.
        """
        result = await self.call("GetBillState", [bill_id])
        return BillState.from_dict({} if result is None else dict(result))

    async def get_server_coppers(self) -> int:
        """Return the current number of coppers on the server account.

        Returns 0 on failure or None responses.
        """
        result = await self.call("GetServerCoppers", [])
        return int(result) if result is not None else 0

    async def get_system_info(self) -> SystemInfo:
        """Return various system information and stats about the server.

        The mapping typically includes connection rates and other metrics.
        Returns an empty dict on None.
        """
        result = await self.call("GetSystemInfo", [])
        return SystemInfo.from_dict({} if result is None else dict(result))

    async def start_server_lan(self) -> bool:
        """Start the server in LAN mode using the current configuration.

        Returns True on success.
        """
        result = await self.call("StartServerLan", [])
        return bool(result)

    async def start_server_internet(self, config: StartServerInternetConfig) -> bool:
        """Start the server on the internet using provided `config`.

        The config payload carries the server 'Login' and 'Password'. Returns
        True on success.
        """
        result = await self.call("StartServerInternet", [config.to_dict()])
        return bool(result)

    async def get_status(self) -> StatusInfo:
        """Return the current status of the server as a mapping.

        Returns an empty dict on None.
        """
        result = await self.call("GetStatus", [])
        return StatusInfo.from_dict({} if result is None else dict(result))

    async def quit_game(self) -> bool:
        """Request the server/application to quit.

        Returns True on success.
        """
        result = await self.call("QuitGame", [])
        return bool(result)

    async def game_data_directory(self) -> str:
        """Return the server's game data directory path as a string.

        Returns an empty string if the response is None.
        """
        result = await self.call("GameDataDirectory", [])
        return "" if result is None else str(result)

    async def get_tracks_directory(self) -> str:
        """Return the server's tracks directory path as a string.

        Returns an empty string if the response is None.
        """
        result = await self.call("GetTracksDirectory", [])
        return "" if result is None else str(result)

    async def get_skins_directory(self) -> str:
        """Return the server's skins directory path as a string.

        Returns an empty string if the response is None.
        """
        result = await self.call("GetSkinsDirectory", [])
        return "" if result is None else str(result)

    async def set_connection_rates(self, download_rate: int, upload_rate: int) -> bool:
        """Set the server download and upload rates in kbps.

        Returns True on success.
        """
        result = await self.call("SetConnectionRates", [download_rate, upload_rate])
        return bool(result)

    async def set_server_name(self, name: str) -> bool:
        """Set the UTF-8 server name.

        Returns True on success.
        """
        result = await self.call("SetServerName", [name])
        return bool(result)

    async def get_server_name(self) -> str:
        """Return the UTF-8 server name.

        Returns an empty string on None responses.
        """
        result = await self.call("GetServerName", [])
        return "" if result is None else str(result)

    async def set_server_comment(self, comment: str) -> bool:
        """Set the UTF-8 server comment.

        Returns True on success.
        """
        result = await self.call("SetServerComment", [comment])
        return bool(result)

    async def get_server_comment(self) -> str:
        """Return the UTF-8 server comment.

        Returns an empty string on None responses.
        """
        result = await self.call("GetServerComment", [])
        return "" if result is None else str(result)

    async def set_hide_server(self, mode: int) -> bool:
        """Set whether the server is hidden from public listings.

        `mode` is typically 0, 1 or 2. Returns True on success.
        """
        result = await self.call("SetHideServer", [mode])
        return bool(result)

    async def get_hide_server(self) -> int:
        """Return the current server visibility mode.

        Returns 0 on None responses.
        """
        result = await self.call("GetHideServer", [])
        return int(result) if result is not None else 0

    async def is_relay_server(self) -> bool:
        """Return whether the current server is a relay server."""
        result = await self.call("IsRelayServer", [])
        return bool(result)

    async def set_server_password(self, password: str) -> bool:
        """Set the server password.

        Returns True on success.
        """
        result = await self.call("SetServerPassword", [password])
        return bool(result)

    async def get_server_password(self) -> str:
        """Return the server password or password-needed indicator.

        Returns an empty string on None responses.
        """
        result = await self.call("GetServerPassword", [])
        return "" if result is None else str(result)

    async def set_server_password_for_spectator(self, password: str) -> bool:
        """Set the spectator-mode password.

        Returns True on success.
        """
        result = await self.call("SetServerPasswordForSpectator", [password])
        return bool(result)

    async def get_server_password_for_spectator(self) -> str:
        """Return the spectator-mode password or requirement indicator.

        Returns an empty string on None responses.
        """
        result = await self.call("GetServerPasswordForSpectator", [])
        return "" if result is None else str(result)

    async def set_max_players(self, max_players: int) -> bool:
        """Set the next maximum number of players.

        Returns True on success.
        """
        result = await self.call("SetMaxPlayers", [max_players])
        return bool(result)

    async def get_max_players(self) -> IntSetting:
        """Return the current and next configured player limits."""
        result = await self.call("GetMaxPlayers", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_max_spectators(self, max_spectators: int) -> bool:
        """Set the next maximum number of spectators.

        Returns True on success.
        """
        result = await self.call("SetMaxSpectators", [max_spectators])
        return bool(result)

    async def get_max_spectators(self) -> IntSetting:
        """Return the current and next configured spectator limits."""
        result = await self.call("GetMaxSpectators", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def enable_p2p_upload(self, enable: bool) -> bool:
        """Enable or disable server peer-to-peer upload."""
        result = await self.call("EnableP2PUpload", [enable])
        return bool(result)

    async def is_p2p_upload(self) -> bool:
        """Return whether server peer-to-peer upload is enabled."""
        result = await self.call("IsP2PUpload", [])
        return bool(result)

    async def enable_p2p_download(self, enable: bool) -> bool:
        """Enable or disable peer-to-peer download for the server."""
        result = await self.call("EnableP2PDownload", [enable])
        return bool(result)

    async def is_p2p_download(self) -> bool:
        """Return whether peer-to-peer download is enabled."""
        result = await self.call("IsP2PDownload", [])
        return bool(result)

    async def allow_challenge_download(self, allow: bool) -> bool:
        """Allow or disallow challenge downloads from the server."""
        result = await self.call("AllowChallengeDownload", [allow])
        return bool(result)

    async def is_challenge_download_allowed(self) -> bool:
        """Return whether clients may download challenges from the server."""
        result = await self.call("IsChallengeDownloadAllowed", [])
        return bool(result)

    async def auto_save_replays(self, enable: bool) -> bool:
        """Enable or disable automatic saving of all replays."""
        result = await self.call("AutoSaveReplays", [enable])
        return bool(result)

    async def auto_save_validation_replays(self, enable: bool) -> bool:
        """Enable or disable automatic saving of validation replays."""
        result = await self.call("AutoSaveValidationReplays", [enable])
        return bool(result)

    async def is_auto_save_replays_enabled(self) -> bool:
        """Return whether automatic replay saving is enabled."""
        result = await self.call("IsAutoSaveReplaysEnabled", [])
        return bool(result)

    async def is_auto_save_validation_replays_enabled(self) -> bool:
        """Return whether automatic validation replay saving is enabled."""
        result = await self.call("IsAutoSaveValidationReplaysEnabled", [])
        return bool(result)

    async def save_current_replay(self, filename: str) -> bool:
        """Save the current replay to `filename` or auto-name when empty."""
        result = await self.call("SaveCurrentReplay", [filename])
        return bool(result)

    async def save_best_ghosts_replay(self, login: str, filename: str) -> bool:
        """Save a replay containing best ghosts for one or all players."""
        result = await self.call("SaveBestGhostsReplay", [login, filename])
        return bool(result)

    async def get_validation_replay(self, login: str) -> Any:
        """Return the validation replay payload for the player `login`."""
        return await self.call("GetValidationReplay", [login])

    async def set_ladder_mode(self, mode: int) -> bool:
        """Set the next ladder mode.

        Returns True on success.
        """
        result = await self.call("SetLadderMode", [mode])
        return bool(result)

    async def get_ladder_mode(self) -> IntSetting:
        """Return the current and next ladder mode."""
        result = await self.call("GetLadderMode", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def get_ladder_server_limits(self) -> LadderServerLimits:
        """Return the ladder point limits allowed on this server."""
        result = await self.call("GetLadderServerLimits", [])
        return LadderServerLimits.from_dict({} if result is None else dict(result))

    async def set_vehicle_net_quality(self, quality: int) -> bool:
        """Set the next network vehicle quality mode."""
        result = await self.call("SetVehicleNetQuality", [quality])
        return bool(result)

    async def get_vehicle_net_quality(self) -> IntSetting:
        """Return the current and next network vehicle quality mode."""
        result = await self.call("GetVehicleNetQuality", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_server_options(self, options: ServerOptionsUpdate) -> bool:
        """Set multiple server options using the provided struct."""
        result = await self.call("SetServerOptions", [options.to_dict()])
        return bool(result)

    async def get_server_options(self, struct_version: Optional[int] = None) -> ServerOptions:
        """Return the configured server options mapping.

        `struct_version` may be omitted or set for compatibility.
        """
        params: List[Any] = []
        if struct_version is not None:
            params.append(struct_version)
        result = await self.call("GetServerOptions", params)
        return ServerOptions.from_dict({} if result is None else dict(result))

    async def set_server_pack_mask(self, pack_mask: str) -> bool:
        """Set the server pack mask.

        Returns True on success.
        """
        result = await self.call("SetServerPackMask", [pack_mask])
        return bool(result)

    async def get_server_pack_mask(self) -> str:
        """Return the current server pack mask."""
        result = await self.call("GetServerPackMask", [])
        return "" if result is None else str(result)

    async def set_forced_mods(self, override: bool, mods: List[ForcedMod]) -> bool:
        """Set forced client mods for one or more environments."""
        result = await self.call("SetForcedMods", [override, [mod.to_dict() for mod in mods]])
        return bool(result)

    async def get_forced_mods(self) -> ForcedMods:
        """Return the current forced mods configuration."""
        result = await self.call("GetForcedMods", [])
        return ForcedMods.from_dict({} if result is None else dict(result))

    async def set_forced_music(self, override: bool, url_or_filename: str) -> bool:
        """Set forced music for clients.

        Returns True on success.
        """
        result = await self.call("SetForcedMusic", [override, url_or_filename])
        return bool(result)

    async def get_forced_music(self) -> ForcedMusic:
        """Return the current forced music configuration."""
        result = await self.call("GetForcedMusic", [])
        return ForcedMusic.from_dict({} if result is None else dict(result))

    async def set_forced_skins(self, skins: List[ForcedSkin]) -> bool:
        """Set the forced-skin remapping list."""
        result = await self.call("SetForcedSkins", [[skin.to_dict() for skin in skins]])
        return bool(result)

    async def get_forced_skins(self) -> List[ForcedSkin]:
        """Return the current forced-skin remappings."""
        result = await self.call("GetForcedSkins", [])
        if result is None:
            return []
        return [ForcedSkin.from_dict(dict(item)) for item in result]

    async def get_last_connection_error_message(self) -> str:
        """Return the last internet connection error message."""
        result = await self.call("GetLastConnectionErrorMessage", [])
        return "" if result is None else str(result)

    async def set_referee_password(self, password: str) -> bool:
        """Set the referee password."""
        result = await self.call("SetRefereePassword", [password])
        return bool(result)

    async def get_referee_password(self) -> str:
        """Return the referee password or requirement indicator."""
        result = await self.call("GetRefereePassword", [])
        return "" if result is None else str(result)

    async def set_referee_mode(self, mode: int) -> bool:
        """Set the referee validation mode."""
        result = await self.call("SetRefereeMode", [mode])
        return bool(result)

    async def get_referee_mode(self) -> int:
        """Return the current referee validation mode."""
        result = await self.call("GetRefereeMode", [])
        return int(result) if result is not None else 0

    async def set_use_changing_validation_seed(self, enable: bool) -> bool:
        """Set whether the validation seed should change between runs."""
        result = await self.call("SetUseChangingValidationSeed", [enable])
        return bool(result)

    async def get_use_changing_validation_seed(self) -> BoolSetting:
        """Return the current and next validation-seed behavior."""
        result = await self.call("GetUseChangingValidationSeed", [])
        return BoolSetting.from_dict({} if result is None else dict(result))

    async def set_warm_up(self, enable: bool) -> bool:
        """Enable or disable the server warm-up phase."""
        result = await self.call("SetWarmUp", [enable])
        return bool(result)

    async def get_warm_up(self) -> bool:
        """Return whether the server is currently in warm-up."""
        result = await self.call("GetWarmUp", [])
        return bool(result)

    async def challenge_restart(self, dont_clear_cup_scores: Optional[bool] = None) -> bool:
        """Restart the current challenge.

        Optionally keep cup scores when supported.
        """
        params: List[Any] = []
        if dont_clear_cup_scores is not None:
            params.append(dont_clear_cup_scores)
        result = await self.call("ChallengeRestart", params)
        return bool(result)

    async def restart_challenge(self, dont_clear_cup_scores: Optional[bool] = None) -> bool:
        """Restart the current challenge.

        Optionally keep cup scores when supported.
        """
        params: List[Any] = []
        if dont_clear_cup_scores is not None:
            params.append(dont_clear_cup_scores)
        result = await self.call("RestartChallenge", params)
        return bool(result)

    async def next_challenge(self, dont_clear_cup_scores: Optional[bool] = None) -> bool:
        """Advance to the next challenge.

        Optionally keep cup scores when supported.
        """
        params: List[Any] = []
        if dont_clear_cup_scores is not None:
            params.append(dont_clear_cup_scores)
        result = await self.call("NextChallenge", params)
        return bool(result)

    async def stop_server(self) -> bool:
        """Stop the server process."""
        result = await self.call("StopServer", [])
        return bool(result)

    async def force_end_round(self) -> bool:
        """Force the current round to end immediately."""
        result = await self.call("ForceEndRound", [])
        return bool(result)

    async def set_game_infos(self, game_infos: GameInfoSettings) -> bool:
        """Set next game settings using the provided struct."""
        result = await self.call("SetGameInfos", [game_infos.to_dict()])
        return bool(result)

    async def get_current_game_info(self, struct_version: Optional[int] = None) -> GameInfo:
        """Return the current game settings struct."""
        params: List[Any] = []
        if struct_version is not None:
            params.append(struct_version)
        result = await self.call("GetCurrentGameInfo", params)
        return GameInfo.from_dict({} if result is None else dict(result))

    async def get_next_game_info(self, struct_version: Optional[int] = None) -> GameInfo:
        """Return the next challenge's game settings struct."""
        params: List[Any] = []
        if struct_version is not None:
            params.append(struct_version)
        result = await self.call("GetNextGameInfo", params)
        return GameInfo.from_dict({} if result is None else dict(result))

    async def get_game_infos(self, struct_version: Optional[int] = None) -> GameInfos:
        """Return both current and next game settings structs."""
        params: List[Any] = []
        if struct_version is not None:
            params.append(struct_version)
        result = await self.call("GetGameInfos", params)
        return GameInfos.from_dict({} if result is None else dict(result))

    async def set_game_mode(self, mode: int) -> bool:
        """Set the next game mode."""
        result = await self.call("SetGameMode", [mode])
        return bool(result)

    async def get_game_mode(self) -> int:
        """Return the current game mode."""
        result = await self.call("GetGameMode", [])
        return int(result) if result is not None else 0

    async def set_chat_time(self, chat_time: int) -> bool:
        """Set the next podium/chat time in milliseconds."""
        result = await self.call("SetChatTime", [chat_time])
        return bool(result)

    async def get_chat_time(self) -> IntSetting:
        """Return the current and next chat time settings."""
        result = await self.call("GetChatTime", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_finish_timeout(self, timeout: int) -> bool:
        """Set the next finish timeout value."""
        result = await self.call("SetFinishTimeout", [timeout])
        return bool(result)

    async def get_finish_timeout(self) -> IntSetting:
        """Return the current and next finish timeout values."""
        result = await self.call("GetFinishTimeout", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_all_warm_up_duration(self, duration: int) -> bool:
        """Set automatic warm-up duration for all modes."""
        result = await self.call("SetAllWarmUpDuration", [duration])
        return bool(result)

    async def get_all_warm_up_duration(self) -> IntSetting:
        """Return the current and next warm-up duration settings."""
        result = await self.call("GetAllWarmUpDuration", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_disable_respawn(self, disable: bool) -> bool:
        """Set whether players may respawn."""
        result = await self.call("SetDisableRespawn", [disable])
        return bool(result)

    async def get_disable_respawn(self) -> BoolSetting:
        """Return whether respawn is disabled now and after restart."""
        result = await self.call("GetDisableRespawn", [])
        return BoolSetting.from_dict({} if result is None else dict(result))

    async def set_force_show_all_opponents(self, value: int) -> bool:
        """Set opponent visibility override behavior."""
        result = await self.call("SetForceShowAllOpponents", [value])
        return bool(result)

    async def get_force_show_all_opponents(self) -> IntSetting:
        """Return opponent visibility override settings."""
        result = await self.call("GetForceShowAllOpponents", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_time_attack_limit(self, limit: int) -> bool:
        """Set the next time-attack limit."""
        result = await self.call("SetTimeAttackLimit", [limit])
        return bool(result)

    async def get_time_attack_limit(self) -> IntSetting:
        """Return the current and next time-attack limit."""
        result = await self.call("GetTimeAttackLimit", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_time_attack_synch_start_period(self, period: int) -> bool:
        """Set the next synchronized start period for time attack mode."""
        result = await self.call("SetTimeAttackSynchStartPeriod", [period])
        return bool(result)

    async def get_time_attack_synch_start_period(self) -> IntSetting:
        """Return current and next sync-start periods for time attack mode."""
        result = await self.call("GetTimeAttackSynchStartPeriod", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_laps_time_limit(self, limit: int) -> bool:
        """Set the next laps-mode time limit."""
        result = await self.call("SetLapsTimeLimit", [limit])
        return bool(result)

    async def get_laps_time_limit(self) -> IntSetting:
        """Return the current and next laps-mode time limit."""
        result = await self.call("GetLapsTimeLimit", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_nb_laps(self, laps: int) -> bool:
        """Set the next number of laps for laps mode."""
        result = await self.call("SetNbLaps", [laps])
        return bool(result)

    async def get_nb_laps(self) -> IntSetting:
        """Return the current and next number of laps for laps mode."""
        result = await self.call("GetNbLaps", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_round_forced_laps(self, laps: int) -> bool:
        """Set the next forced lap count for rounds mode."""
        result = await self.call("SetRoundForcedLaps", [laps])
        return bool(result)

    async def get_round_forced_laps(self) -> IntSetting:
        """Return the current and next forced lap count for rounds mode."""
        result = await self.call("GetRoundForcedLaps", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_round_points_limit(self, points_limit: int) -> bool:
        """Set the next points limit for rounds mode."""
        result = await self.call("SetRoundPointsLimit", [points_limit])
        return bool(result)

    async def get_round_points_limit(self) -> IntSetting:
        """Return the current and next points limit for rounds mode."""
        result = await self.call("GetRoundPointsLimit", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_round_custom_points(
        self, points: List[int], relax_constraints: Optional[bool] = None
    ) -> bool:
        """Set the custom point table for rounds mode."""
        params: List[Any] = [points]
        if relax_constraints is not None:
            params.append(relax_constraints)
        result = await self.call("SetRoundCustomPoints", params)
        return bool(result)

    async def get_round_custom_points(self) -> List[int]:
        """Return the custom point table used in rounds mode."""
        result = await self.call("GetRoundCustomPoints", [])
        return [] if result is None else [int(x) for x in result]

    async def set_use_new_rules_round(self, enable: bool) -> bool:
        """Set whether rounds mode uses the new rules."""
        result = await self.call("SetUseNewRulesRound", [enable])
        return bool(result)

    async def get_use_new_rules_round(self) -> BoolSetting:
        """Return whether rounds mode uses the new rules now and next."""
        result = await self.call("GetUseNewRulesRound", [])
        return BoolSetting.from_dict({} if result is None else dict(result))

    async def set_team_points_limit(self, points_limit: int) -> bool:
        """Set the next points limit for team mode."""
        result = await self.call("SetTeamPointsLimit", [points_limit])
        return bool(result)

    async def get_team_points_limit(self) -> IntSetting:
        """Return the current and next points limit for team mode."""
        result = await self.call("GetTeamPointsLimit", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_max_points_team(self, max_points: int) -> bool:
        """Set the next maximum points per round for team mode."""
        result = await self.call("SetMaxPointsTeam", [max_points])
        return bool(result)

    async def get_max_points_team(self) -> IntSetting:
        """Return the current and next maximum points per team round."""
        result = await self.call("GetMaxPointsTeam", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_use_new_rules_team(self, enable: bool) -> bool:
        """Set whether team mode uses the new rules."""
        result = await self.call("SetUseNewRulesTeam", [enable])
        return bool(result)

    async def get_use_new_rules_team(self) -> BoolSetting:
        """Return whether team mode uses the new rules now and next."""
        result = await self.call("GetUseNewRulesTeam", [])
        return BoolSetting.from_dict({} if result is None else dict(result))

    async def set_cup_points_limit(self, points_limit: int) -> bool:
        """Set the points needed for victory in cup mode."""
        result = await self.call("SetCupPointsLimit", [points_limit])
        return bool(result)

    async def get_cup_points_limit(self) -> IntSetting:
        """Return the current and next cup-mode points limit."""
        result = await self.call("GetCupPointsLimit", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_cup_rounds_per_challenge(self, rounds: int) -> bool:
        """Set cup-mode rounds per challenge."""
        result = await self.call("SetCupRoundsPerChallenge", [rounds])
        return bool(result)

    async def get_cup_rounds_per_challenge(self) -> IntSetting:
        """Return cup-mode rounds per challenge."""
        result = await self.call("GetCupRoundsPerChallenge", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_cup_warm_up_duration(self, duration: int) -> bool:
        """Set cup-mode warm-up duration."""
        result = await self.call("SetCupWarmUpDuration", [duration])
        return bool(result)

    async def get_cup_warm_up_duration(self) -> IntSetting:
        """Return cup-mode warm-up duration now and next."""
        result = await self.call("GetCupWarmUpDuration", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def set_cup_nb_winners(self, winners: int) -> bool:
        """Set how many winners determine the end of a cup match."""
        result = await self.call("SetCupNbWinners", [winners])
        return bool(result)

    async def get_cup_nb_winners(self) -> IntSetting:
        """Return the configured number of cup winners now and next."""
        result = await self.call("GetCupNbWinners", [])
        return IntSetting.from_dict({} if result is None else dict(result))

    async def get_current_challenge_index(self) -> int:
        """Return the current challenge index or -1 if unavailable."""
        result = await self.call("GetCurrentChallengeIndex", [])
        return int(result) if result is not None else -1

    async def get_next_challenge_index(self) -> int:
        """Return the next scheduled challenge index."""
        result = await self.call("GetNextChallengeIndex", [])
        return int(result) if result is not None else -1

    async def set_next_challenge_index(self, index: int) -> bool:
        """Set the next challenge index."""
        result = await self.call("SetNextChallengeIndex", [index])
        return bool(result)

    async def get_current_challenge_info(self) -> ChallengeInfo:
        """Return information about the current challenge."""
        result = await self.call("GetCurrentChallengeInfo", [])
        return ChallengeInfo.from_dict({} if result is None else dict(result))

    async def get_next_challenge_info(self) -> ChallengeInfo:
        """Return information about the next challenge."""
        result = await self.call("GetNextChallengeInfo", [])
        return ChallengeInfo.from_dict({} if result is None else dict(result))

    async def get_challenge_info(self, filename: str) -> ChallengeInfo:
        """Return information for the challenge at `filename`."""
        result = await self.call("GetChallengeInfo", [filename])
        return ChallengeInfo.from_dict({} if result is None else dict(result))

    async def check_challenge_for_current_server_params(self, filename: str) -> bool:
        """Return whether the challenge matches current server settings."""
        result = await self.call("CheckChallengeForCurrentServerParams", [filename])
        return bool(result)

    async def get_challenge_list(self, max_infos: int, start: int) -> List[ChallengeInfo]:
        """Return a paged list of challenges in the current selection."""
        result = await self.call("GetChallengeList", [max_infos, start])
        if result is None:
            return []
        return [ChallengeInfo.from_dict(dict(item)) for item in result]

    async def add_challenge(self, filename: str) -> bool:
        """Add a challenge to the end of the current selection."""
        result = await self.call("AddChallenge", [filename])
        return bool(result)

    async def add_challenge_list(self, filenames: List[str]) -> int:
        """Add multiple challenges to the end of the current selection."""
        result = await self.call("AddChallengeList", [filenames])
        return int(result) if result is not None else 0

    async def remove_challenge(self, filename: str) -> bool:
        """Remove a challenge from the current selection."""
        result = await self.call("RemoveChallenge", [filename])
        return bool(result)

    async def remove_challenge_list(self, filenames: List[str]) -> int:
        """Remove multiple challenges from the current selection."""
        result = await self.call("RemoveChallengeList", [filenames])
        return int(result) if result is not None else 0

    async def insert_challenge(self, filename: str) -> bool:
        """Insert a challenge after the current challenge."""
        result = await self.call("InsertChallenge", [filename])
        return bool(result)

    async def insert_challenge_list(self, filenames: List[str]) -> int:
        """Insert multiple challenges after the current challenge."""
        result = await self.call("InsertChallengeList", [filenames])
        return int(result) if result is not None else 0

    async def choose_next_challenge(self, filename: str) -> bool:
        """Set an existing challenge as the next one to be played."""
        result = await self.call("ChooseNextChallenge", [filename])
        return bool(result)

    async def choose_next_challenge_list(self, filenames: List[str]) -> int:
        """Queue multiple selected challenges as upcoming challenges."""
        result = await self.call("ChooseNextChallengeList", [filenames])
        return int(result) if result is not None else 0

    async def load_match_settings(self, filename: str) -> int:
        """Load match settings and playlist from `filename`."""
        result = await self.call("LoadMatchSettings", [filename])
        return int(result) if result is not None else 0

    async def append_playlist_from_match_settings(self, filename: str) -> int:
        """Append a playlist from the specified match settings file."""
        result = await self.call("AppendPlaylistFromMatchSettings", [filename])
        return int(result) if result is not None else 0

    async def save_match_settings(self, filename: str) -> int:
        """Save match settings and playlist to `filename`."""
        result = await self.call("SaveMatchSettings", [filename])
        return int(result) if result is not None else 0

    async def insert_playlist_from_match_settings(self, filename: str) -> int:
        """Insert a playlist from the specified match settings file."""
        result = await self.call("InsertPlaylistFromMatchSettings", [filename])
        return int(result) if result is not None else 0

    async def get_player_list(
        self, max_infos: int, start: int, struct_version: Optional[int] = None
    ) -> List[PlayerInfo]:
        """Return a paged list of players currently on the server."""
        params: List[Any] = [max_infos, start]
        if struct_version is not None:
            params.append(struct_version)
        result = await self.call("GetPlayerList", params)
        if result is None:
            return []
        return [PlayerInfo.from_dict(dict(item)) for item in result]

    async def get_detailed_player_info(self, login: str) -> DetailedPlayerInfo:
        """Return detailed information for the player `login`."""
        result = await self.call("GetDetailedPlayerInfo", [login])
        return DetailedPlayerInfo.from_dict({} if result is None else dict(result))

    async def get_main_server_player_info(
        self, struct_version: Optional[int] = None
    ) -> PlayerInfo:
        """Return the player-info struct for the main or local server player."""
        params: List[Any] = []
        if struct_version is not None:
            params.append(struct_version)
        result = await self.call("GetMainServerPlayerInfo", params)
        return PlayerInfo.from_dict({} if result is None else dict(result))

    async def get_current_ranking(self, max_infos: int, start: int) -> List[PlayerRanking]:
        """Return a paged slice of the current race ranking."""
        result = await self.call("GetCurrentRanking", [max_infos, start])
        if result is None:
            return []
        return [PlayerRanking.from_dict(dict(item)) for item in result]

    async def get_current_ranking_for_login(self, login: str) -> List[PlayerRanking]:
        """Return current ranking information for one or more logins."""
        result = await self.call("GetCurrentRankingForLogin", [login])
        if result is None:
            return []
        return [PlayerRanking.from_dict(dict(item)) for item in result]

    async def force_scores(
        self, scores: List[PlayerScore], silent_mode: Optional[bool] = None
    ) -> bool:
        """Force current scores in rounds or team mode."""
        params: List[Any] = [[score.to_dict() for score in scores]]
        if silent_mode is not None:
            params.append(silent_mode)
        result = await self.call("ForceScores", params)
        return bool(result)

    async def force_player_team(self, login: str, team: int) -> bool:
        """Force the specified player login onto a team."""
        result = await self.call("ForcePlayerTeam", [login, team])
        return bool(result)

    async def force_player_team_id(self, player_id: int, team: int) -> bool:
        """Force the specified player id onto a team."""
        result = await self.call("ForcePlayerTeamId", [player_id, team])
        return bool(result)

    async def force_spectator(self, login: str, spectator_mode: int) -> bool:
        """Force the spectating status for the player `login`."""
        result = await self.call("ForceSpectator", [login, spectator_mode])
        return bool(result)

    async def force_spectator_id(self, player_id: int, spectator_mode: int) -> bool:
        """Force the spectating status for a player by id."""
        result = await self.call("ForceSpectatorId", [player_id, spectator_mode])
        return bool(result)

    async def force_spectator_target(
        self, spectator_login: str, target_login: str, camera_type: int
    ) -> bool:
        """Force spectators to watch a specific target login."""
        result = await self.call(
            "ForceSpectatorTarget", [spectator_login, target_login, camera_type]
        )
        return bool(result)

    async def force_spectator_target_id(
        self, spectator_id: int, target_id: int, camera_type: int
    ) -> bool:
        """Force spectators to watch a specific target id."""
        result = await self.call("ForceSpectatorTargetId", [spectator_id, target_id, camera_type])
        return bool(result)

    async def spectator_release_player_slot(self, login: str) -> bool:
        """Release the preserved player slot held by a spectator login."""
        result = await self.call("SpectatorReleasePlayerSlot", [login])
        return bool(result)

    async def spectator_release_player_slot_id(self, player_id: int) -> bool:
        """Release the preserved player slot held by a spectator id."""
        result = await self.call("SpectatorReleasePlayerSlotId", [player_id])
        return bool(result)

    async def manual_flow_control_enable(self, enable: bool) -> bool:
        """Enable or disable manual game-flow control."""
        result = await self.call("ManualFlowControlEnable", [enable])
        return bool(result)

    async def manual_flow_control_proceed(self) -> bool:
        """Allow the game to proceed to the next blocked transition."""
        result = await self.call("ManualFlowControlProceed", [])
        return bool(result)

    async def manual_flow_control_is_enabled(self) -> int:
        """Return whether manual game-flow control is enabled."""
        result = await self.call("ManualFlowControlIsEnabled", [])
        return int(result) if result is not None else 0

    async def manual_flow_control_get_cur_transition(self) -> str:
        """Return the currently blocked manual-flow transition."""
        result = await self.call("ManualFlowControlGetCurTransition", [])
        return "" if result is None else str(result)

    async def check_end_match_condition(self) -> str:
        """Return the current match-ending state string."""
        result = await self.call("CheckEndMatchCondition", [])
        return "" if result is None else str(result)

    async def get_network_stats(self) -> NetworkStats:
        """Return network statistics for the server and connected players."""
        result = await self.call("GetNetworkStats", [])
        return NetworkStats.from_dict({} if result is None else dict(result))
