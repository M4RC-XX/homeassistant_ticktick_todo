"""Constants for the TickTick To-Do integration."""

from datetime import timedelta

DOMAIN = "ticktick_todo"

# TickTick OAuth2 Configuration
OAUTH_AUTHORIZE_URL = "https://ticktick.com/oauth/authorize"
OAUTH_TOKEN_URL = "https://ticktick.com/oauth/token"
OAUTH_SCOPES = "tasks:write tasks:read"

# TickTick Open API v1
API_BASE_URL = "https://api.ticktick.com/open/v1"
INBOX_PROJECT_ID = "inbox"

# Coordinator & HTTP Settings
DEFAULT_UPDATE_INTERVAL = timedelta(seconds=60)
MAX_CONCURRENT_REQUESTS = 5
REQUEST_TIMEOUT = 15

# TickTick Task Status Constants
TICKTICK_STATUS_NORMAL = 0
TICKTICK_STATUS_COMPLETED = (2, -1)
