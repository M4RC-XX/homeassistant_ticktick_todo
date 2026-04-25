import logging
from homeassistant.helpers import config_entry_oauth2_flow
from .const import DOMAIN

class TickTickOAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Handle standard OAuth2 flow for TickTick."""
    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)