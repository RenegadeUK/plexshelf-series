
# PlexShelf Series Manager

A Docker-based Python application with a modern web UI for organizing Plex audiobooks into series collections.

## Features

- 🎧 **Automatic Series Detection**: Intelligently matches audiobooks to series using multiple algorithms
- 🔍 **Fuzzy Matching**: Uses fuzzy string matching to find series even with inconsistent naming
- ✅ **User Approval System**: Review and approve/reject all matches before applying to Plex
- 🎛️ **Manual Override**: Manually match audiobooks to series when automatic matching fails
- 💾 **SQLite Database**: Stores all audiobook metadata and series matches locally
- 🐳 **Docker Ready**: Fully containerized with automatic builds via GitHub Actions
- 🌐 **Web UI**: Modern web interface (Flask + HTML/JS/CSS) for all management tasks
- 📋 **Activity Log**: See the last 20 (configurable) actions in the web UI, including granular backend steps
- 🤖 **External Series Lookup**: Uses OpenAI and Google Books APIs for advanced series detection

## Quick Start


### Using Docker Compose (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/yourusername/plexshelf-series.git
cd plexshelf-series
```

2. Start the container:
```bash
docker-compose up -d
```

3. Open the web UI:
   - Visit [http://localhost:8080](http://localhost:8080) in your browser

### Using Docker Run

```bash
docker run -d \
  --name plexshelf-series \
  -v $(pwd)/config:/config \
  -v $(pwd)/data:/data \
  -p 8080:8080 \
  yourusername/plexshelf-series:latest
```

> **Note:** Legacy VNC/GUI access is no longer required. All features are available via the web UI on port 8080.

## Configuration


### First Time Setup

1. Open the web UI at [http://localhost:8080](http://localhost:8080)
2. Go to **Settings**
3. Enter your Plex server details:
  - **Plex Server URL**: e.g., `http://192.168.1.100:32400`
  - **Plex Token**: [How to find your Plex token](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/)
  - **Library Name**: Name of your audiobooks library (default: "Audiobooks")

### Finding Your Plex Token

1. Open Plex Web App in your browser
2. Play any media item
3. Click the more (...) button
4. Select "Get Info" → "View XML"
5. Look for `X-Plex-Token=` in the URL

## Usage Workflow


### 1. Scan Plex Library
Click **Scan Plex Library** in the web UI to fetch all audiobooks from your Plex server. This stores the metadata in the local database.

### 2. Match Series
Click **Match Series** to run the automatic matching algorithm. This will:
- Extract series information from metadata
- Parse titles for series patterns (e.g., "Series Name - Book 1")
- Use fuzzy matching to group related audiobooks
- Assign confidence scores to each match
- Optionally use OpenAI or Google Books for advanced series lookup

### 3. Review & Approve
Go to the **Review Matches** tab to:
- View all detected series matches
- Filter by status (pending, approved, rejected)
- Approve or reject individual matches
- Auto-approve high-confidence matches (≥90%)
- Manually create or edit matches

### 4. Apply to Plex
Once you've reviewed and approved matches, click **Apply to Plex** to:
- Create collections in Plex for each approved series
- Collections will be named "[Series Name] Series"
- Only approved matches are applied

### 5. Activity Log
The **Activity Log** in the web UI shows the last 20 actions (configurable), including granular backend steps such as OpenAI/Google Books lookups, matching progress, and errors. This log is non-persistent and resets on page reload.

## Architecture


### Project Structure

```
plexshelf-series/
├── .github/
│   └── workflows/
│       └── docker-build.yml     # GitHub Actions for Docker builds
├── src/
│   ├── main.py                  # Web app entry point (Flask)
│   ├── web_app.py               # Flask app and routes
│   ├── config/
│   │   └── config_manager.py    # Configuration management
│   ├── database/
│   │   ├── models.py            # SQLAlchemy models
│   │   └── db_manager.py        # Database manager
│   ├── external/
│   │   └── series_lookup.py     # OpenAI/Google Books lookup
│   ├── matching/
│   │   └── series_matcher.py    # Series matching algorithms
│   ├── plex/
│   │   └── plex_client.py       # Plex API client
│   ├── templates/
│   │   ├── index.html           # Web UI (activity log, actions)
│   │   ├── matches.html         # Review matches UI
│   │   └── settings.html        # Settings UI
│   └── utils/
│       └── logger.py            # Logging configuration
├── config/                       # Configuration files (mounted volume)
├── data/                         # Database files (mounted volume)
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
└── requirements.txt
```

### Database Schema

- **AudiobookItem**: Stores audiobook metadata from Plex
- **Series**: Stores detected series information
- **SeriesMatch**: Links audiobooks to series with confidence scores
- **PlexCollection**: Tracks collections created in Plex

## GitHub Actions

The project includes automatic Docker image building:

1. **On Push to Main/Develop**: Builds and pushes Docker images
2. **On Tag (v*)**: Creates versioned releases
3. **Multi-Architecture**: Builds for both AMD64 and ARM64

### Setup GitHub Secrets

Add these secrets to your GitHub repository:
- `DOCKER_USERNAME`: Your Docker Hub username
- `DOCKER_PASSWORD`: Your Docker Hub password/token

Images are pushed to:
- Docker Hub: `yourusername/plexshelf-series`
- GitHub Container Registry: `ghcr.io/yourusername/plexshelf-series`

## Configuration Files

### config.yaml

Located in `/config/config.yaml` (auto-generated on first run):

```yaml
plex:
  url: ''
  token: ''
  library_name: 'Audiobooks'
  timeout: 30

matching:
  confidence_threshold: 70
  auto_approve_threshold: 95
  fuzzy_match_enabled: true

ui:
  theme: 'default'
  window_size: '1024x768'
  auto_refresh: false

logging:
  level: 'INFO'
  file: '/config/plexshelf.log'
```

## Development


### Local Development

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
cd src
python main.py
```

4. Open the web UI at [http://localhost:8080](http://localhost:8080)


### Building Docker Image

```bash
docker build -t plexshelf-series .
```

### Running in Docker

```bash
docker run --rm -p 8080:8080 -v $(pwd)/config:/config -v $(pwd)/data:/data plexshelf-series:latest
```

Then open [http://localhost:8080](http://localhost:8080) in your browser.

## Troubleshooting

### Can't Connect to Plex
- Verify your Plex server URL is accessible
- Check that your token is valid
- Ensure the library name matches exactly

### No Series Detected
- Check that your audiobooks have proper metadata
- Try manually matching a few books to establish patterns
- Review the matching algorithms in the code


### Web UI Not Accessible
- Ensure port 8080 is not blocked by firewall
- Check container logs: `docker logs plexshelf-series`


### Database Issues
- The database is stored in `/data/plexshelf.db`
- To reset: stop container, delete `data/plexshelf.db`, restart

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details


## Credits

Built with:
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [PlexAPI](https://github.com/pkkid/python-plexapi) - Python bindings for Plex API
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
- [fuzzywuzzy](https://github.com/seatgeek/fuzzywuzzy) - Fuzzy string matching
- [OpenAI](https://platform.openai.com/docs/api-reference) - Series lookup (optional)
- [Google Books API](https://developers.google.com/books/docs/v1/using) - Series lookup (optional)

## Support


For issues, questions, or suggestions:
- Open an issue on GitHub
- Check existing issues for solutions
- Review logs in `/config/plexshelf.log`
- For web UI errors, check the browser console and activity log for details
