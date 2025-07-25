# AutoPVS1 Link 🧬

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-2.2+-orange.svg)](https://spec.modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A production-ready unified server providing both REST API and MCP (Model Context Protocol) interfaces for accessing PVS1 variant classification data from [AutoPVS1](https://autopvs1.bgi.com). Built with FastAPI and FastMCP for seamless integration with AI assistants and web applications.

## ✨ Advanced Features

### 🏗️ Architecture
- **Unified Server**: Single server supporting both REST API and MCP protocols
- **Multi-Transport Support**: HTTP, STDIO, and unified transport modes
- **Singleton Managers**: Thread-safe resource management with proper lifecycle
- **STDIO Protection**: Reliable MCP communication with output suppression
- **Circuit Breaker**: Resilient external service calls with automatic recovery

### 🚀 Performance & Reliability
- **Advanced Caching**: Enhanced async LRU caching with detailed statistics and event logging
- **Retry Logic**: Exponential backoff with configurable retries and circuit breaker
- **Rate Limiting**: Respectful request handling to avoid service overload
- **Connection Pooling**: Efficient HTTP connection management
- **Health Monitoring**: Comprehensive health checks and status reporting

### 🔧 Developer Experience
- **Rich CLI**: Beautiful command-line interface with colors and progress indicators
- **Advanced Configuration**: Multi-level configuration with validation and environment support
- **Structured Logging**: Correlation IDs, performance metrics, and JSON output
- **Type Safety**: Full type hints with Pydantic models and mypy compliance
- **Hot Reload**: Development mode with automatic code reloading

### 📊 Observability
- **Request Correlation**: Unique IDs for tracking requests across components
- **Performance Logging**: Detailed timing and cache statistics
- **Cache Analytics**: Hit rates, miss counts, and performance metrics
- **Circuit Breaker Status**: Real-time service health monitoring
- **Error Tracking**: Comprehensive error logging with context

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/autopvs1-link.git
cd autopvs1-link

# Install with development dependencies
pip install -e ".[dev]"
```

### Basic Usage

#### CLI Interface (Recommended)

```bash
# Start the unified server (REST + MCP)
autopvs1-link server

# Start MCP server only (STDIO)
autopvs1-link mcp

# Start MCP server (HTTP transport)
autopvs1-link mcp --http --port 3000

# Show configuration
autopvs1-link config

# Check health status
autopvs1-link health

# View cache statistics
autopvs1-link cache

# Clear all caches
autopvs1-link clear-cache
```

#### Direct Python

```bash
# Unified server
python -m autopvs1_link.unified_server

# MCP STDIO mode
python -m autopvs1_link.cli mcp

# Legacy compatibility (redirects to unified server)
python server.py
python mcp_server.py
```

## 🌐 API Endpoints

### REST API

The server provides a comprehensive REST API with OpenAPI documentation:

- **Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`
- **Cache Stats**: `http://localhost:8000/api/cache/stats`
- **Circuit Breakers**: `http://localhost:8000/api/circuit-breakers`

#### Core Endpoints

```bash
# Get variant PVS1 analysis
GET /api/variant/{genome_build}/{variant_id}

# Search variants by gene
GET /api/search?q={gene_name}&genome_version={version}

# Get CNV PVS1 analysis
GET /api/cnv/{genome_build}/{cnv_id}

# Management endpoints
GET /api/cache/stats
POST /api/cache/clear
GET /api/circuit-breakers
```

### MCP Tools

The server exposes the following tools via MCP:

- `get_variant_analysis` - Get comprehensive PVS1 analysis for variants
- `search_genetic_variants` - Search for variants by gene or criteria
- `get_cnv_analysis` - Get PVS1 analysis for copy number variants
- `get_cache_statistics` - View cache performance metrics
- `clear_all_caches` - Clear all service caches

## ⚙️ Configuration

### Environment Variables

The server supports comprehensive configuration via environment variables:

```bash
# API Configuration
AUTOPVS1_API_BASE_URL=https://autopvs1.bgi.com
AUTOPVS1_API_REQUEST_TIMEOUT=30
AUTOPVS1_API_MAX_RETRIES=3
AUTOPVS1_API_RETRY_DELAY=1.0
AUTOPVS1_API_RATE_LIMIT_DELAY=1.0

# Cache Configuration
AUTOPVS1_CACHE_ENABLED=true
AUTOPVS1_CACHE_SIZE=256
AUTOPVS1_CACHE_TTL_HOURS=24
AUTOPVS1_CACHE_STATISTICS_ENABLED=true
AUTOPVS1_CACHE_EVENT_LOGGING=false

# Server Configuration
AUTOPVS1_SERVER_HOST=0.0.0.0
AUTOPVS1_SERVER_PORT=8000
AUTOPVS1_SERVER_RELOAD=false
AUTOPVS1_SERVER_CORS_ORIGINS=*
AUTOPVS1_SERVER_WORKERS=1

# Logging Configuration
AUTOPVS1_LOG_LEVEL=INFO
AUTOPVS1_LOG_JSON_FORMAT=false
AUTOPVS1_LOG_STRUCTURED=true
AUTOPVS1_LOG_CORRELATION_IDS=true
AUTOPVS1_LOG_PERFORMANCE_LOGGING=true

# MCP Configuration
AUTOPVS1_MCP_NAME="AutoPVS1 Link"
AUTOPVS1_MCP_ENABLE_STDIO_PROTECTION=true
AUTOPVS1_MCP_CUSTOM_TOOL_NAMES=true

# Environment
ENVIRONMENT=development  # development, staging, production
DEBUG=true
```

### Configuration File

Create a `.env` file in the project root:

```env
# Example .env file
ENVIRONMENT=development
DEBUG=true
AUTOPVS1_API_REQUEST_TIMEOUT=30
AUTOPVS1_CACHE_SIZE=512
AUTOPVS1_LOG_LEVEL=DEBUG
```

## 🧪 Development

### Code Quality

```bash
# Run linting
ruff check . --fix

# Format code
black .

# Type checking
mypy autopvs1_link/

# Run all checks
ruff check . --fix && black . && mypy autopvs1_link/
```

### Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=autopvs1_link --cov-report=html

# Run specific test
pytest tests/test_service.py::test_variant_caching
```

### Architecture

The project follows a clean, modular architecture:

```
autopvs1_link/
├── api/                    # API layer
│   ├── autopvs1_client.py # HTTP client with retry logic
│   ├── client_manager.py  # Singleton client management
│   └── routes/            # FastAPI route definitions
├── services/              # Business logic layer
│   ├── autopvs1_service.py # Core service with caching
│   └── service_manager.py  # Singleton service management
├── models/                # Data models (Pydantic)
├── middleware/           # Custom middleware
├── utils/                # Utilities
│   ├── cache_manager.py  # Advanced cache management
│   └── retry_handler.py  # Retry logic and circuit breaker
├── config.py             # Configuration management
├── logging_config.py     # Logging setup
├── cli.py               # Rich CLI interface
└── unified_server.py    # Main server implementation
```

## 📊 Monitoring & Observability

### Health Checks

```bash
# CLI health check
autopvs1-link health

# HTTP health check
curl http://localhost:8000/health
```

Response includes:
- Overall service status
- Client connection health
- Service layer status
- Circuit breaker states
- Cache configuration
- Environment information

### Cache Statistics

```bash
# View cache stats via CLI
autopvs1-link cache

# HTTP endpoint
curl http://localhost:8000/api/cache/stats
```

Provides detailed metrics:
- Hit/miss rates per method
- Average response times
- Error counts
- Cache evictions
- Total requests

### Circuit Breaker Status

```bash
# View circuit breaker status
curl http://localhost:8000/api/circuit-breakers
```

Shows:
- Current state (closed/open/half-open)
- Failure counts
- Recovery timeouts
- Success thresholds

## 🔌 MCP Integration

### Claude Desktop

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "autopvs1-link": {
      "command": "autopvs1-link",
      "args": ["mcp"],
      "env": {
        "AUTOPVS1_CACHE_SIZE": "512",
        "AUTOPVS1_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Other MCP Clients

For STDIO transport:
```bash
autopvs1-link mcp
```

For HTTP transport:
```bash
autopvs1-link mcp --http --port 3000
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and linting (`pytest && ruff check . --fix && black .`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [AutoPVS1](https://autopvs1.bgi.com) for providing the PVS1 variant classification service
- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [FastMCP](https://github.com/modelcontextprotocol/fast-mcp) for MCP integration
- [Pydantic](https://docs.pydantic.dev/) for data validation and settings management

## 📞 Support

- 📖 [Documentation](./CLAUDE.md)
- 🐛 [Issue Tracker](https://github.com/your-username/autopvs1-link/issues)
- 💬 [Discussions](https://github.com/your-username/autopvs1-link/discussions)

---

Built with ❤️ for the genomics and AI community.