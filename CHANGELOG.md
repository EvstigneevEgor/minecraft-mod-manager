# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-09

### Added
- Initial release of Minecraft Mod Manager
- FastAPI-based HTTP API for mod management
- Modrinth API integration for mod discovery and download
- Automatic Minecraft server version detection
- Recursive dependency resolution for mods
- Automatic mod updates with configurable intervals
- Support for Fabric mod loader (Forge support planned)
- JSON-based state management with backup functionality
- Comprehensive logging system
- Configuration management via JSON and environment variables
- Health check endpoints
- Auto-update management endpoints
- Complete API documentation
- Example usage scripts
- Basic test suite

### Features
- **Mod Installation**: Install mods by name or Modrinth URL
- **Dependency Management**: Automatic resolution and installation of mod dependencies
- **Version Compatibility**: Automatic filtering of compatible mod versions
- **Auto Updates**: Scheduled automatic updates with APScheduler
- **State Persistence**: JSON-based state storage with backup support
- **Error Handling**: Comprehensive error handling for network, API, and file system issues
- **Logging**: Detailed logging with configurable levels
- **Configuration**: Flexible configuration via JSON files and environment variables

### API Endpoints
- `POST /install` - Install a mod and its dependencies
- `GET /mods` - List all installed mods
- `DELETE /mods/{slug}` - Remove a specific mod
- `POST /mods/{slug}/update` - Update a specific mod
- `GET /server/info` - Get Minecraft server information
- `GET /auto-update/status` - Get auto-update status
- `POST /auto-update/enable` - Enable automatic updates
- `POST /auto-update/disable` - Disable automatic updates
- `POST /auto-update/run` - Run update check manually
- `GET /auto-update/logs` - Get update logs
- `GET /health` - Health check endpoint

### Technical Details
- Python 3.10+ support
- FastAPI framework for high-performance API
- Async/await for optimal performance
- APScheduler for background task scheduling
- Pydantic for data validation
- HTTPX for async HTTP requests
- Comprehensive error handling and logging