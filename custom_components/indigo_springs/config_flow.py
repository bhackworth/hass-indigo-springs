"""Config flow for the sensorhub integration."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


class IndigoSpringsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the Indigo Springs integration."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""

        identifier = "indigo_springs"
        await self.async_set_unique_id(identifier)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title="Indigo Springs",
            data={},
        )
