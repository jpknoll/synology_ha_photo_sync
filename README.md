# Synology Photo Album Home Assistant Integration

This custom Home Assistant integration creates a media source from images in a Synology Photos shared album. It scrapes the sharing page to extract image URLs and makes them available in Home Assistant's media browser.

## Features

- Scrapes Synology Photos sharing pages to extract image URLs
- Creates a media source in Home Assistant's media browser
- Supports browsing and playing images from shared albums
- Configurable via Home Assistant's UI

## Installation

1. Copy the `custom_components/synology_photo_album` directory to your Home Assistant `custom_components` folder:
   ```
   <config>/custom_components/synology_photo_album/
   ```

2. Restart Home Assistant

3. Go to **Settings** → **Devices & Services** → **Add Integration**

4. Search for "Synology Photo Album" and follow the setup wizard

5. Enter your Synology Photos sharing URL (e.g., `https://your-nas.quickconnect.to/mo/sharing/XXXXX`)

## Configuration

The integration requires:
- **Sharing URL**: The full URL to your Synology Photos shared album
- **Update Interval** (optional): How often to refresh the photo list (default: 3600 seconds / 1 hour)

## How It Works

The integration:
1. Extracts the passphrase from the sharing URL
2. Makes API calls to the Synology Photos sharing endpoints (same as the web page does)
3. Retrieves all photos from the shared album
4. Makes them available as a media source in Home Assistant

## Usage

Once configured, you can:
- Browse photos in the Media Browser (Media → Browse Media → Synology Photo Album)
- Use the media source in automations or scripts
- Display photos on dashboards using media players that support images

## Technical Details

The scraper uses the same API endpoints that the Synology Photos web interface uses:
- `SYNO.Foto.Browse.Album` - Gets album information
- `SYNO.Foto.Browse.Item` - Gets photo items from the album
- `/synofoto/api/v2/p/Thumbnail/get` - Gets thumbnail/full image URLs

This approach scrapes the API endpoints rather than parsing HTML, making it more reliable and efficient.

## Requirements

- Home Assistant 2023.1 or later
- Python packages: `aiohttp`, `beautifulsoup4`, `lxml` (installed automatically)

## License

This integration is provided as-is for personal use.

