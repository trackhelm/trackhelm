from __future__ import annotations

import struct


GBX_HEADER = b"GBXRemote 2"


class Protocol:
    @staticmethod
    def pack(payload: bytes, *, handle: int | None = None) -> bytes:
        """
        Pack payload for GBXRemote.

        If `handle` is provided, use protocol v2 header (size + handle).
        Otherwise send a 4-byte size header (used for handshake).
        """
        if handle is None:
            return struct.pack("<I", len(payload)) + payload

        return struct.pack("<I", len(payload)) + struct.pack("<I", handle) + payload

    @staticmethod
    def unpack_header(header: bytes) -> tuple[int, bool, int | None]:
        """
        Unpack header bytes.

        Returns (size, is_callback, handle).
        `handle` is None when header contains only 4 bytes (handshake).
        For 8-byte headers, `is_callback` is True when the handle indicates a callback
        (i.e. MSB of handle is 0 in the GBX convention used by Nadeo/PHP clients).
        """
        if len(header) == 4:
            size = struct.unpack("<I", header)[0]
            return size, False, None

        if len(header) == 8:
            size, handle = struct.unpack("<II", header)
            # In Nadeo/GbxRemote, callbacks have MSB == 0
            is_callback = (handle & 0x80000000) == 0
            return size, is_callback, handle

        raise ValueError("Invalid GBX header length")
