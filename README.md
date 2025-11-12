# Cleanarr

[![Tests](https://github.com/maateen/cleanarr/workflows/Tests/badge.svg)](https://github.com/maateen/cleanarr/actions)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

🧹 **Automated Media Library Cleanup Tool**

> ⚠️ **This project is under heavy development. Install directly from the main branch for the latest features and fixes.**

Cleanarr automatically identifies and removes watched movies and TV series from your Radarr/Sonarr libraries with multiple safety protections to prevent accidental deletion of content you want to keep.

## ✨ Features

### 🛡️ **Multiple Safety Layers**
- **Favorites Protection** - Never deletes content marked as favorite in Jellyfin
- **qBittorrent Integration** - Skips content you're actively seeding
- **Dry-run by Default** - Preview what will be deleted before taking action
- **Smart Matching** - Uses fuzzy matching with configurable similarity thresholds

### 🔗 **Service Integration**
- **Jellyfin** - Identifies watched content across all users
- **Radarr** - Manages movie library cleanup
- **Sonarr** - Manages TV series library cleanup
- **qBittorrent** - Cross-checks against active torrents

### ⚙️ **Flexible Configuration**
- **Auto-configuration** - Creates example config on first run
- **Multiple Auth Methods** - API keys + HTTP Basic Auth support
- **Granular Control** - Movies-only, series-only, similarity thresholds
- **Comprehensive Logging** - Debug info to file, clean output to console

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/maateen/cleanarr.git
cd cleanarr
pip install -r requirements.txt
```

### First Run

```bash
# Creates example configuration at ~/.config/cleanarr/config.cfg
python run.py --help
```

### Configuration

Edit `~/.config/cleanarr/config.cfg` with your server details:

```ini
[jellyfin]
server_url = http://localhost:8096
api_key = your_jellyfin_api_key_here
default_user = maateen

[radarr]
server_url = http://localhost:7878
api_key = your_radarr_api_key_here

[sonarr]
server_url = http://localhost:8989
api_key = your_sonarr_api_key_here

[qbittorrent]
server_url = http://localhost:8080
username = your_qbt_username
password = your_qbt_password
use_basic_auth = true

[auth]
# HTTP Basic Auth for Radarr/Sonarr (if required)
username = your_username
password = your_password
```

### Usage

```bash
# Preview what will be deleted (safe, default behavior)
python run.py

# Actually delete the content
python run.py --delete

# Process only movies
python run.py --movies-only

# Process only TV series
python run.py --series-only

# Keep files but remove from Radarr/Sonarr
python run.py --delete --keep-files

# Custom similarity threshold
python run.py --similarity-threshold 0.9
```

## 📋 How It Works

1. **Discovers Watched Content** - Scans Jellyfin for movies/series marked as watched by any user
2. **Applies Safety Filters**:
   - Skips anything marked as favorite ⭐
   - Skips anything being seeded in qBittorrent 🌊
3. **Matches with *arr Services** - Uses fuzzy matching to find content in Radarr/Sonarr
4. **Previews Actions** - Shows exactly what will be deleted in dry-run mode
5. **Executes Cleanup** - Removes content from *arr services and deletes files/folders

## 🛡️ Safety Features

### Automatic Protections
- **Dry-run by default** - Must explicitly use `--delete` to make changes
- **Favorites immunity** - Content marked as favorite in Jellyfin is never deleted
- **Seeding protection** - Content in qBittorrent completed torrents is skipped
- **Similarity thresholds** - Only matches with high confidence (configurable)

### Manual Overrides
- `--keep-files` - Remove from *arr but keep files on disk
- `--similarity-threshold` - Adjust matching sensitivity (0.0-1.0)
- `--movies-only` / `--series-only` - Limit scope of operations

## 📊 Example Output

```
🚀 Starting Cleanarr cleanup process
✅ Radarr connection successful
✅ Sonarr connection successful
✅ qBittorrent connection successful - version: v4.3.9
🔍 Finding cleanup candidates...
🌟 Protected favorites: 2 movies, 1 series
🛡️  Safety filter: Skipped 3 movies and 0 series found in qBittorrent

📊 Cleanup Summary:
  Movies to delete: 4
  Series to delete: 1
  🛡️  Protected by qBittorrent: 3 movies, 0 series

📽️  Movies to delete:
────────────────────────────────────────────────────────────────────────────
  • Jellyfin: The Movie (2023)
    Radarr:   The Movie (2023)
    Match score: 0.95
    In qBittorrent: ❌ No (safe to delete)

🔒 DRY RUN MODE - No files will be deleted
   Use --delete to actually delete content
```

## 🔧 Configuration Options

### Command Line Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--delete` | Actually delete content (disables dry-run) | `false` |
| `--dry-run` | Preview mode - show what would be deleted | `true` |
| `--keep-files` | Remove from *arr but keep files on disk | `false` |
| `--movies-only` | Process only movies | `false` |
| `--series-only` | Process only TV series | `false` |
| `--watched-before-days` | Only delete items watched at least N days ago | `unset` |
| `--similarity-threshold` | Minimum match confidence (0.0-1.0) | `0.8` |
| `--log-level` | Logging verbosity (DEBUG/INFO/WARNING/ERROR) | `INFO` |

## 🤖 Automation

### Cron Job Example

```bash
# Run cleanup daily at 3 AM
0 3 * * * /usr/bin/python3 /path/to/cleanarr/run.py --delete >> /var/log/cleanarr.log 2>&1
```

### Systemd Timer

Create `/etc/systemd/system/cleanarr.service`:

```ini
[Unit]
Description=Cleanarr Media Cleanup
After=network.target

[Service]
Type=oneshot
User=media
ExecStart=/usr/bin/python3 /opt/cleanarr/run.py --delete
WorkingDirectory=/opt/cleanarr
```

Create `/etc/systemd/system/cleanarr.timer`:

```ini
[Unit]
Description=Run Cleanarr daily
Requires=cleanarr.service

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
```

Enable with:
```bash
sudo systemctl enable cleanarr.timer
sudo systemctl start cleanarr.timer
```

## 🔍 Troubleshooting

### Common Issues

**"No configuration file found"**
- Run any command once to auto-create the config file
- Edit `~/.config/cleanarr/config.cfg` with your server details

**"Cannot connect to [service]"**
- Verify server URLs are correct and accessible
- Check API keys are valid and have required permissions
- For Radarr/Sonarr: Ensure API key has admin privileges

**"No content to clean up"**
- Check that content is actually marked as watched in Jellyfin
- Verify the content exists in both Jellyfin and Radarr/Sonarr
- Lower `--similarity-threshold` if matches aren't being found

### Debug Mode

```bash
# Enable debug logging to file
python run.py --log-level DEBUG

# Check log file
tail -f ~/.config/cleanarr/cleanarr.log
```

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
git clone https://github.com/maateen/cleanarr.git
cd cleanarr
pip install -r requirements.txt
```

### Running Tests

```bash
# No unit tests yet - contributions welcome!
# Basic functionality test:
python run.py --help
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool permanently deletes files from your system. Always:
- Test with `--dry-run` first
- Keep backups of important content
- Mark must-keep content as favorites in Jellyfin
- Understand what the tool will do before using `--delete`

Use at your own risk.

## 🙏 Acknowledgments

- [Jellyfin](https://jellyfin.org/) - The free media server
- [Radarr](https://radarr.video/) - Movie collection manager
- [Sonarr](https://sonarr.tv/) - TV series collection manager
- [qBittorrent](https://www.qbittorrent.org/) - BitTorrent client

---

**Made with ❤️ for the self-hosted media community**
