from __future__ import annotations

from pydantic import BaseModel
from pydantic import ConfigDict


class PluginConfig(BaseModel):
    """Base class for plugin configuration models."""

    model_config = ConfigDict(extra="ignore", frozen=True)
