"""Constants for the Synology Photo Sync integration."""

# Domain identifier for the integration
DOMAIN = "synology_photo_sync"

# Default Values
DEFAULT_NAME = "Synology Photo Sync"

# Configuration keys
CONF_SOURCES = "sources"
CONF_URL = "url"
CONF_FOLDER_NAME = "folder_name"
CONF_DATA_DIR = "data_dir"

# Supported image extensions
SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".heic", ".heif"}

# Sync status
SYNC_STATUS_IDLE = "idle"
SYNC_STATUS_RUNNING = "running"
SYNC_STATUS_COMPLETED = "completed"
SYNC_STATUS_ERROR = "error"

