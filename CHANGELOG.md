# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-03

### Added
- Natal chart generation (full and compact versions)
- Solar return charts (full and compact versions)
- Progressed charts (full and compact versions)
- Composite charts (full and compact versions)
- Synastry aspects (full and compact versions)
- Transit charts (full and compact versions)
- Chart summaries with essential information (Sun/Moon/Rising signs, chart shape, moon phase)
- Planetary positions with simplified format
- Configuration management for Immanuel library settings
- Comprehensive input validation and error handling
- Support for multiple coordinate formats (decimal, traditional DMS)
- Custom compact JSON serializer for optimized LLM token usage
- Comprehensive test suite with detailed result tracking

### Features
- MCP server integration for Claude Desktop and other MCP-compatible clients
- Flexible coordinate parsing (supports formats like "32n43", "32.71", "51°23'30\"N")
- Dynamic settings configuration (house systems, orbs, calculation methods)
- Detailed error messages with helpful suggestions
- Full logging support for debugging and monitoring

[0.1.0]: https://github.com/Jasperb3/Immanuel-MCP/releases/tag/v0.1.0
