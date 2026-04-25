"""Application credentials platform for TickTick."""
from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant
from .const import OAUTH_AUTHORIZE_URL, OAUTH_TOKEN_URL

async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH_AUTHORIZE_URL,
        token_url=OAUTH_TOKEN_URL,
    )
