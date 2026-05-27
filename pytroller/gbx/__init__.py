"""GBX client helpers.

Import the main client directly from this package::

        from pytroller.gbx import GbxClient

Usage example (minimal):

        client = GbxClient(
                host="127.0.0.1",
                port=14001,
                username="user",
                password="pass",
                event_bus=some_event_bus,
        )

        await client.connect()
        ok = await client.authenticate("user", "pass")
        await client.enable_callbacks(True)
"""

from .client import GbxClient


__all__ = ["GbxClient"]
