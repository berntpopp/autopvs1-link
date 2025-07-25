# AutoPVS1 Link

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![MCP](https://img.shields.io/badge/MCP-2.2+-orange.svg)](https://spec.modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A unified server providing both REST API and MCP (Model Context Protocol) interfaces for accessing PVS1 variant classification data from [AutoPVS1](https://autopvs1.bgi.com). Built with FastAPI and FastMCP for seamless integration with AI assistants and web applications.

## 🎯 Core Features

- **Unified API Architecture**: Modern FastAPI-based REST API with full OpenAPI documentation
- **MCP Integration**: Native support for AI assistants via Model Context Protocol
- **Comprehensive Data Access**: Extracts variant info, PVS1 flowcharts, and disease mechanisms
- **Smart Caching**: Built-in async LRU caching with configurable TTL for optimal performance
- **Type Safety**: Full type hints with Pydantic models and mypy compliance
- **Production Ready**: Structured logging, error handling, health checks, and CORS support
- **Multi-Transport**: Supports HTTP, STDIO, and unified transport modes
- **Rate Limiting**: Respectful request handling with configurable timeouts

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/autopvs1-link.git
cd autopvs1-link

# Install with development dependencies
pip install -e ".[dev]"
```

### Environment Configuration

Create a `.env` file in the project root:

```env
# AutoPVS1 Configuration
AUTOPVS1_BASE_URL=https://autopvs1.bgi.com
REQUEST_TIMEOUT=30

# Caching Configuration  
CACHE_SIZE=256
CACHE_TTL_HOURS=24

# Server Configuration
LOG_LEVEL=INFO
LOG_JSON=false
CORS_ORIGINS=*
```

### Server Startup

#### Unified Mode (REST API + MCP HTTP)
```bash
# Start unified server with both REST and MCP endpoints
python server.py

# Server will be available at:
# - REST API: http://localhost:8000
# - MCP HTTP: http://localhost:8000/mcp  
# - API Docs: http://localhost:8000/docs
```

#### STDIO Mode (For Claude Desktop)
```bash
# Run MCP server via STDIO for Claude Desktop integration
python mcp_server.py
```

#### HTTP-Only Mode
```bash
# Start only the REST API server
uvicorn server:app --host 0.0.0.0 --port 8000
```

## 📚 API Documentation

### Variant Analysis Endpoints

#### Get Variant PVS1 Data
```bash
GET /variant/{genome_build}/{variant_id}

# Example: Get PVS1 analysis for a nonsense variant
curl "http://localhost:8000/variant/hg38/X-83508928-A-T"
```

**Response:**
```json
{
  "genome_build": "hg38",
  "variant_info": {
    "variant_id": "X-83508928-A-T",
    "variant_type": "Nonsense",
    "gene_symbol": "POU3F4",
    "pli_score": 0.72,
    "chgvs": "NM_000307.5:c.604A>T",
    "phgvs": "NP_000298.3:p.Lys202Ter",
    "external_links": {
      "OMIM": "https://mirror.omim.org/entry/300039",
      "gnomAD": "https://gnomad.broadinstitute.org/variant/X-83508928-A-T"
    }
  },
  "pvs1_flowchart": {
    "preliminary_decision_path": "NF5",
    "final_strength": "Strong"
  },
  "disease_mechanisms": [
    {
      "gene": "POU3F4",
      "disease": "nonsyndromic genetic deafness",
      "inheritance": "XL",
      "clinical_validity": "Definitive",
      "adjusted_strength": "Strong"
    }
  ]
}
```

#### Search Variants
```bash
GET /variant/search?q={gene}&genome_version={build}

# Example: Search for MYH9 variants
curl "http://localhost:8000/variant/search?q=MYH9&genome_version=hg19"

# Example: Search with default genome version (hg19)  
curl "http://localhost:8000/variant/search?q=BRCA1"
```

#### CNV Analysis
```bash
GET /cnv/{genome_build}/{cnv_id}

# Example: Get PVS1 analysis for a deletion CNV
curl "http://localhost:8000/cnv/hg19/11-2797090-2869333-DEL"

# Example: Complex duplication CNV
curl "http://localhost:8000/cnv/hg19/tdup(17:7577936-7585058)"
```

### System Endpoints

```bash
# Health check
GET /health

# API information
GET /
```

## 🔧 MCP Integration

### Claude Desktop Configuration

Add to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "autopvs1-link": {
      "command": "python",
      "args": ["/path/to/autopvs1-link/mcp_server.py"],
      "env": {
        "AUTOPVS1_BASE_URL": "https://autopvs1.bgi.com",
        "CACHE_SIZE": "256",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### Web-based AI Configuration

For web-based AI assistants using HTTP transport:

```json
{
  "mcpServers": {
    "autopvs1-link": {
      "url": "http://localhost:8000/mcp",
      "headers": {
        "Authorization": "Bearer your-token-here"
      }
    }
  }
}
```

### Available MCP Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `get_variant_pvs1_data` | Get PVS1 analysis for genetic variants | `genome_build`, `variant_id` |
| `search_variants` | Search variants by gene symbol | `query`, `genome_version` |
| `get_cnv_pvs1_data` | Get PVS1 analysis for CNVs | `genome_build`, `cnv_id` |
| `get_cache_statistics` | View cache performance metrics | None |
| `clear_cache` | Clear all service caches | None |

### Transport Modes

#### STDIO Transport (Recommended for Claude Desktop)
```bash
python mcp_server.py
```

#### HTTP Transport (For web-based AI)
```bash
python server.py
# MCP tools available at: http://localhost:8000/mcp
```

#### Unified Transport (Both REST + MCP)
```bash  
python server.py
# REST API: http://localhost:8000
# MCP HTTP: http://localhost:8000/mcp
```

## 🏗️ Architecture

```
autopvs1-link/
├── autopvs1_link/
│   ├── api/
│   │   ├── routes/              # FastAPI route handlers
│   │   │   ├── variant.py       # Variant endpoints
│   │   │   └── cnv.py          # CNV endpoints
│   │   ├── autopvs1_client.py  # HTTP client & HTML parsing
│   │   └── client_manager.py   # Client lifecycle management
│   ├── models/
│   │   └── autopvs1_models.py  # Pydantic data models
│   ├── services/
│   │   ├── autopvs1_service.py # Business logic with caching
│   │   └── service_manager.py  # Service lifecycle management
│   ├── middleware/
│   │   └── logging_middleware.py # Request logging
│   ├── config.py               # Application configuration
│   └── logging_config.py       # Structured logging setup
├── tests/
│   ├── fixtures/               # HTML fixtures for testing
│   │   ├── variant_hg38_X-83508928-A-T.html
│   │   └── cnv_hg19_11-2797090-2869333-DEL.html
│   ├── test_scraper_parsers.py # Unit tests for parsing
│   └── test_api_endpoints.py   # Integration tests for API
├── server.py                   # FastAPI application (unified mode)
├── mcp_server.py              # MCP server (STDIO mode)
└── pyproject.toml             # Project configuration
```

## ⚙️ Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTOPVS1_BASE_URL` | `https://autopvs1.bgi.com` | Base URL for AutoPVS1 service |
| `REQUEST_TIMEOUT` | `30` | HTTP request timeout in seconds |
| `CACHE_SIZE` | `256` | Maximum number of cached responses |
| `CACHE_TTL_HOURS` | `24` | Cache time-to-live in hours |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_JSON` | `false` | Enable JSON structured logging |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `ENVIRONMENT` | `development` | Application environment |

### Cache Configuration

The service uses async LRU caching to improve performance:

```python
# Cache settings
CACHE_SIZE = 256        # Max cached responses
CACHE_TTL_HOURS = 24   # Cache expiration time

# Cache hit rates (typical)
# - Variant queries: ~85% hit rate
# - Search queries: ~70% hit rate  
# - CNV queries: ~80% hit rate
```

### Performance Tuning

```env
# High-performance configuration
CACHE_SIZE=1024
CACHE_TTL_HOURS=48
REQUEST_TIMEOUT=45

# Memory-optimized configuration  
CACHE_SIZE=128
CACHE_TTL_HOURS=12
REQUEST_TIMEOUT=20
```

## 🧪 Development

### Setup Development Environment

```bash
# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks (optional)
pre-commit install
```

### Code Quality Tools

```bash
# Run linting and formatting
ruff check . --fix
black .

# Type checking
mypy autopvs1_link/

# Run all quality checks
ruff check . && black --check . && mypy autopvs1_link/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=autopvs1_link --cov-report=html

# Run only unit tests (skip integration)
pytest -m "not integration"

# Run specific test categories
pytest -m "not slow"                    # Skip slow tests
pytest tests/test_scraper_parsers.py   # Specific test file
pytest -k "test_variant"               # Tests matching pattern
```

### Test Categories

- **Unit Tests**: Fast tests with mocked dependencies
- **Integration Tests**: Tests with real HTTP calls (marked as `integration`)
- **Live Tests**: Tests against real AutoPVS1 service (marked as `slow`)

## 🚀 Production Deployment

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY . .
RUN pip install -e .

# For REST API + MCP HTTP
EXPOSE 8000
CMD ["python", "server.py"]

# For MCP STDIO only
# CMD ["python", "mcp_server.py"]
```

```bash
# Build and run
docker build -t autopvs1-link .
docker run -p 8000:8000 --env-file .env autopvs1-link
```

### Health Monitoring

```bash
# Health check endpoint
curl http://localhost:8000/health

# Expected response
{
  "status": "healthy",
  "service": "autopvs1-link",
  "version": "1.0.0",
  "uptime": "2h 15m 30s"
}

# Cache statistics
curl http://localhost:8000/api/cache/stats
```

### Production Environment Variables

```env
# Production configuration
ENVIRONMENT=production
LOG_LEVEL=WARNING
LOG_JSON=true
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Performance optimization
CACHE_SIZE=1024
CACHE_TTL_HOURS=48
REQUEST_TIMEOUT=30
```

## 📊 Supported Data Types

### Variant Types
- **Point Mutations**: SNVs, insertions, deletions
- **Complex Variants**: Multi-nucleotide variants, indels
- **Splice Variants**: Canonical and non-canonical splice sites
- **Nonsense/Frameshift**: Protein-truncating variants

### CNV Types  
- **Deletions**: Single and multi-exon deletions
- **Duplications**: Tandem and interspersed duplications
- **Complex Rearrangements**: Translocations, inversions

### Genome Builds
- **hg19/GRCh37**: Legacy build support
- **hg38/GRCh38**: Current reference genome

## ⚠️ Limitations & Considerations

### Rate Limiting
- Be respectful of the AutoPVS1 service
- Built-in request timeouts and retry logic
- Caching reduces upstream requests

### Data Accuracy  
- Parsing depends on HTML structure stability
- Always verify critical clinical interpretations
- Cache may serve stale data (TTL: 24h default)

### Service Dependencies
- Requires internet access to autopvs1.bgi.com
- Service availability depends on upstream status
- No offline mode available

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes following the coding standards
4. Run the full test suite (`pytest`)
5. Ensure code quality (`ruff check . && black . && mypy autopvs1_link/`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Coding Standards
- **Linting**: Ruff for fast Python linting
- **Formatting**: Black for consistent code style  
- **Type Hints**: Full mypy compliance required
- **Testing**: Pytest with >90% coverage target
- **Documentation**: Docstrings for all public methods

## 📚 Related Projects

- **[genereviews-link](../genereviews-link)**: MCP/API for GeneReviews clinical summaries
- **[gnomad-link](../gnomad-link)**: GraphQL API wrapper for gnomAD population data
- **[pubtator-link](../pubtator-link)**: PubTator API integration for biomedical literature
- **[litvar-link](../litvar-link)**: Literature variant search and analysis

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[AutoPVS1](https://autopvs1.bgi.com)** - BGI's automated PVS1 interpretation tool
- **[FastMCP](https://github.com/jlowin/fastmcp)** - Model Context Protocol implementation  
- **[FastAPI](https://fastapi.tiangolo.com/)** - Modern web framework for Python APIs
- **[Anthropic](https://anthropic.com)** - MCP specification and Claude integration

---

**Status**: ✅ Active Development | **Version**: 1.0.0 | **Python**: 3.9+ | **License**: MIT

> **Disclaimer**: This tool is for research and educational purposes. Always verify critical genetic variant interpretations through official clinical channels and certified diagnostic laboratories.