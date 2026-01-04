# Synology Photo Sync Home Assistant Integration

A Home Assistant custom integration that syncs/downloads images from Synology QuickConnect sharing links into organized folders.

## Features

- **Multiple Sources**: Configure multiple Synology sharing URLs, each syncing to its own subfolder
- **Automatic Organization**: Images are organized by source in separate folders
- **Service-Based Sync**: Trigger sync operations via Home Assistant services
- **Status Monitoring**: Sensors to track sync status, last sync time, and files downloaded
- **Duplicate Prevention**: Skips files that already exist locally

## Installation

1. Copy the `synology_photo_sync` folder to your Home Assistant `custom_components` directory:
   ```
   <config>/custom_components/synology_photo_sync/
   ```

2. Restart Home Assistant

3. Go to **Settings** > **Devices & Services** > **Add Integration**

4. Search for "Synology Photo Sync" and follow the setup wizard

## Configuration

### Initial Setup

During setup, you'll be asked to provide:
- **Integration Name**: A friendly name for the integration
- **Sources**: A JSON array of sources, each with:
  - `url`: The Synology QuickConnect sharing URL (e.g., `https://your-nas.quickconnect.to/mo/sharing/abc123`)
  - `folder_name`: The name of the subfolder where images will be stored

Example sources JSON:
```json
[
  {
    "url": "https://jpknoll-nas.quickconnect.to/mo/sharing/dRCQK2EDv",
    "folder_name": "family_photos"
  },
  {
    "url": "https://jpknoll-nas.quickconnect.to/mo/sharing/xyz789",
    "folder_name": "vacation_photos"
  }
]
```

### Data Storage

Images are stored in:
```
<config>/synology_photo_sync/<folder_name>/
```

Where `<config>` is your Home Assistant configuration directory.

## Usage

### Services

#### `synology_photo_sync.sync_all`
Sync all configured sources.

**Service Data:**
- None required

**Example:**
```yaml
service: synology_photo_sync.sync_all
```

#### `synology_photo_sync.sync_source`
Sync a specific source by folder name.

**Service Data:**
- `source_name` (required): The folder name of the source to sync

**Example:**
```yaml
service: synology_photo_sync.sync_source
data:
  source_name: family_photos
```

### Sensors

The integration provides the following sensors:

- **Sync Status**: Current sync status (`idle`, `running`, `completed`, `error`)
- **Last Sync**: Timestamp of the last sync operation
- **Files Downloaded**: Total number of files downloaded across all sources

### Automation Example

```yaml
automation:
  - alias: "Sync Photos Daily"
    trigger:
      - platform: time
        at: "02:00:00"
    action:
      - service: synology_photo_sync.sync_all
```

## How It Works

This integration uses the official Synology DSM FileStation API to:
1. List files in the sharing link using `SYNO.FileStation.List`
2. Download image files using `SYNO.FileStation.Download`

The integration automatically extracts the sharing ID from the QuickConnect URL and constructs the appropriate API endpoints.

## Limitations

- Only image files are downloaded (JPEG, PNG, GIF, BMP, WEBP, HEIC, HEIF)
- Currently only syncs files from the root of the sharing link (subdirectories are skipped)
- Sharing links must be publicly accessible or the integration must have appropriate permissions

## Troubleshooting

1. **No files downloaded**: 
   - Check that the sharing link is publicly accessible
   - Verify the URL format is correct
   - Check Home Assistant logs for errors

2. **Sync fails**:
   - Ensure the sharing link is accessible from your Home Assistant instance
   - Check network connectivity
   - Review logs for specific error messages

## Development

This integration uses:
- `aiohttp` for HTTP requests
- Synology DSM FileStation API for listing and downloading files

## License

See LICENSE file for details.

