"""Config flow for the sensorhub integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_PORT

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Optional(CONF_PORT, "Port", 8234): int,
    }
)


class IndigoSpringsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Configure the Indigo Springs integration."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors: dict[str, str] = {}
        if user_input:
            identifier = "hackware"  # await client.get_identifier()

            await self.async_set_unique_id(identifier)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title="Indigo Springs",
                data=user_input,
            )
        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )
