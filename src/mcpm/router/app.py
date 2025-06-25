import logging
import os

from mcpm.core.utils.log_manager import get_log_directory
from mcpm.monitor.event import monitor
from mcpm.router.router import MCPRouter
from mcpm.router.router_config import RouterConfig
from mcpm.utils.config import ConfigManager

LOG_DIR = get_log_directory("mcpm")
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "router.log"
CORS_ENABLED = os.environ.get("MCPM_ROUTER_CORS")

logging.basicConfig(
    level=logging.INFO if not os.environ.get("MCPM_DEBUG") else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
logger = logging.getLogger("mcpm.router.daemon")

config = ConfigManager().get_router_config()
api_key = config.get("api_key")
auth_enabled = config.get("auth_enabled", False)


allow_origins = None
if CORS_ENABLED:
    allow_origins = os.environ.get("MCPM_ROUTER_CORS", "").split(",")

router = MCPRouter(reload_server=True, router_config=RouterConfig(api_key=api_key, auth_enabled=auth_enabled))
app = router.get_remote_server_app(allow_origins=allow_origins, include_lifespan=True, monitor=monitor)
