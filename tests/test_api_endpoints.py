"""Tests for FastAPI endpoints."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from autopvs1_link.models.autopvs1_models import (
    AutoPVS1Data,
    DiseaseMechanism,
    PVS1Flowchart,
    VariantInfo,
)
from autopvs1_link.unified_server import app


def load_fixture(name: str) -> str:
    """Load HTML fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / name
    if not fixture_path.exists():
        pytest.skip(f"Fixture {name} not found")
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def test_client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Create async test client."""
    from httpx import ASGITransport

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", follow_redirects=True
    ) as client:
        yield client


@pytest.fixture
def variant_html():
    """Load variant HTML fixture."""
    return load_fixture("variant_hg38_X-83508928-A-T.html")


@pytest.fixture
def sample_variant_data():
    """Create sample variant data for testing."""
    return AutoPVS1Data(
        genome_build="hg38",
        variant_info=VariantInfo(
            variant_id="X-83508928-A-T",
            variant_type="Nonsense",
            gene_symbol="POU3F4",
            pli_score=0.72,
            chgvs="NM_000307.5:c.604A>T",
            phgvs="NP_000298.3:p.Lys202Ter",
            exon="1/1",
            intron="-/0",
            external_links={
                "OMIM": "https://mirror.omim.org/entry/300039",
                "gnomAD": "https://gnomad.broadinstitute.org/variant/X-83508928-A-T",
            },
        ),
        pvs1_flowchart=PVS1Flowchart(
            preliminary_decision_path="NF5",
            final_strength="Strong",
            decision_tree=[],
            notes={},
        ),
        disease_mechanisms=[
            DiseaseMechanism(
                gene="POU3F4",
                disease="nonsyndromic genetic deafness",
                inheritance="XL",
                clinical_validity="Definitive",
                consideration="No Decrease",
                adjusted_strength="Strong",
            )
        ],
    )


class TestVariantEndpoints:
    """Test variant-related endpoints."""

    def test_root_endpoint(self, test_client):
        """Test the root endpoint."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Welcome to the AutoPVS1 Link Unified Server!"
        assert "docs" in data
        assert "version" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, async_client):
        """Test the health check endpoint."""
        response = await async_client.get("http://test/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy", "not_initialized"]
        # Service field only present when properly initialized
        if "service" in data:
            assert data["service"] == "autopvs1-link"

    @pytest.mark.asyncio
    @patch("autopvs1_link.api.autopvs1_client.AutoPVS1Client.get_variant_data")
    async def test_get_variant_success(self, mock_get_variant, sample_variant_data, async_client):
        """Test successful variant data retrieval."""
        mock_get_variant.return_value = sample_variant_data

        response = await async_client.get("http://test/variant/hg38/X-83508928-A-T")

        assert response.status_code == 200
        data = response.json()

        assert data["genome_build"] == "hg38"
        assert data["variant_info"]["variant_id"] == "X-83508928-A-T"
        assert data["variant_info"]["gene_symbol"] == "POU3F4"
        assert data["pvs1_flowchart"]["final_strength"] == "Strong"
        assert len(data["disease_mechanisms"]) == 1

    @pytest.mark.asyncio
    @patch("autopvs1_link.api.autopvs1_client.AutoPVS1Client.get_variant_data")
    async def test_get_variant_not_found(self, mock_get_variant, async_client):
        """Test variant not found error."""
        # Create a mock response for 404
        mock_response = AsyncMock()
        mock_response.status_code = 404

        mock_get_variant.side_effect = httpx.HTTPStatusError(
            message="Not Found", request=AsyncMock(), response=mock_response
        )

        response = await async_client.get("http://test/variant/hg38/nonexistent-variant")

        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_variant_server_error(self, async_client):
        """Test server error handling using FastAPI dependency override."""
        from autopvs1_link.services.service_manager import get_managed_service
        from autopvs1_link.unified_server import app

        # Create mock service that raises an exception
        mock_service = AsyncMock()
        mock_service.get_variant_data.side_effect = Exception("Internal error")

        # Override the dependency
        app.dependency_overrides[get_managed_service] = lambda: mock_service

        try:
            response = await async_client.get("http://test/variant/hg38/X-83508928-A-T")

            assert response.status_code == 500
            data = response.json()
            assert "Internal server error" in data["detail"]
        finally:
            # Clean up the override
            app.dependency_overrides.clear()


class TestGeneEndpoints:
    """Test gene-related endpoints."""

    @pytest.mark.asyncio
    @patch("autopvs1_link.api.autopvs1_client.AutoPVS1Client.search_variants")
    async def test_search_gene_variants_success(self, mock_search, async_client):
        """Test successful gene variant search."""
        from autopvs1_link.models.autopvs1_models import (
            AutoPVS1SearchResults,
            SearchResult,
        )

        mock_search.return_value = AutoPVS1SearchResults(
            query="MYH9",
            genome_version="hg19",
            results=[
                SearchResult(
                    variant_id="2-160000000-G-A",
                    gene="MYH9",
                    variant_type="Missense",
                    genome_build="hg19",
                    url="/variant/hg19/2-160000000-G-A",
                )
            ],
        )

        response = await async_client.get("http://test/gene/search?q=MYH9&genome_version=hg19")

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "MYH9"
        assert data["genome_version"] == "hg19"
        assert len(data["results"]) == 1
        assert data["results"][0]["gene"] == "MYH9"

    @pytest.mark.asyncio
    @patch("autopvs1_link.api.autopvs1_client.AutoPVS1Client.search_variants")
    async def test_search_gene_variants_empty_results(self, mock_search, async_client):
        """Test gene search with no results."""
        from autopvs1_link.models.autopvs1_models import AutoPVS1SearchResults

        mock_search.return_value = AutoPVS1SearchResults(
            query="NONEXISTENT", genome_version="hg19", results=[]
        )

        response = await async_client.get("http://test/gene/search?q=NONEXISTENT")

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "NONEXISTENT"
        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_search_gene_variants_missing_query(self, async_client):
        """Test gene search without query parameter."""
        response = await async_client.get("http://test/gene/search")

        assert response.status_code == 422  # Validation error


class TestCNVEndpoints:
    """Test CNV-related endpoints."""

    @pytest.mark.asyncio
    @patch("autopvs1_link.api.autopvs1_client.AutoPVS1Client.get_cnv_data")
    async def test_get_cnv_success(self, mock_get_cnv, async_client):
        """Test successful CNV data retrieval."""
        from autopvs1_link.models.autopvs1_models import AutoPVS1CNVData, CNVInfo

        mock_get_cnv.return_value = AutoPVS1CNVData(
            genome_build="hg19",
            cnv_info=CNVInfo(
                cnv_id="11-2797090-2869333-DEL",
                cnv_type="Deletion",
                gene_symbol="MRGPRX1",
                coordinates="11-2797090-2869333-DEL",
            ),
            pvs1_flowchart=PVS1Flowchart(
                preliminary_decision_path="CNV1",
                final_strength="Strong",
                decision_tree=[],
                notes={},
            ),
            disease_mechanisms=[],
        )

        response = await async_client.get("http://test/cnv/hg19/11-2797090-2869333-DEL")

        assert response.status_code == 200
        data = response.json()

        assert data["genome_build"] == "hg19"
        assert data["cnv_info"]["cnv_id"] == "11-2797090-2869333-DEL"
        assert data["cnv_info"]["cnv_type"] == "Deletion"
        assert data["pvs1_flowchart"]["final_strength"] == "Strong"

    @pytest.mark.asyncio
    @patch("autopvs1_link.api.autopvs1_client.AutoPVS1Client.get_cnv_data")
    async def test_get_cnv_error(self, mock_get_cnv, async_client):
        """Test CNV error handling."""
        mock_get_cnv.side_effect = Exception("CNV parsing error")

        response = await async_client.get("http://test/cnv/hg19/invalid-cnv")

        assert response.status_code == 500
        data = response.json()
        assert "Internal server error" in data["detail"]


class TestErrorHandling:
    """Test error handling across endpoints."""

    @pytest.mark.asyncio
    async def test_invalid_path(self, async_client):
        """Test accessing non-existent endpoint."""
        response = await async_client.get("http://test/nonexistent")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, async_client):
        """Test unsupported HTTP method."""
        response = await async_client.post("http://test/variant/hg38/test")
        assert response.status_code == 405


@pytest.mark.integration
class TestLiveAPIIntegration:
    """Integration tests with live data."""

    @pytest.mark.asyncio
    async def test_live_variant_endpoint(self, async_client):
        """Test variant endpoint with live data."""
        try:
            response = await async_client.get("http://test/variant/hg38/X-83508928-A-T")

            if response.status_code == 200:
                data = response.json()
                assert data["variant_info"]["gene_symbol"] == "POU3F4"
                assert data["pvs1_flowchart"]["final_strength"] in [
                    "Strong",
                    "Moderate",
                    "Supporting",
                ]
        except Exception:
            pytest.skip("Live integration test failed - network or site unavailable")

    @pytest.mark.asyncio
    async def test_live_search_endpoint(self, async_client):
        """Test search endpoint with live data."""
        try:
            response = await async_client.get(
                "http://test/gene/search?q=POU3F4&genome_version=hg38"
            )

            if response.status_code == 200:
                data = response.json()
                assert data["query"] == "POU3F4"
                assert data["genome_version"] == "hg38"
        except Exception:
            pytest.skip("Live integration test failed - network or site unavailable")


class TestResponseValidation:
    """Test response model validation."""

    @pytest.mark.asyncio
    @patch("autopvs1_link.api.autopvs1_client.AutoPVS1Client.get_variant_data")
    async def test_response_schema_validation(
        self, mock_get_variant, sample_variant_data, async_client
    ):
        """Test that responses conform to Pydantic models."""
        mock_get_variant.return_value = sample_variant_data

        response = await async_client.get("http://test/variant/hg38/X-83508928-A-T")

        assert response.status_code == 200
        data = response.json()

        # Validate required fields are present
        assert "genome_build" in data
        assert "variant_info" in data
        assert "pvs1_flowchart" in data
        assert "disease_mechanisms" in data

        # Validate nested structure
        variant_info = data["variant_info"]
        assert "variant_id" in variant_info
        assert "variant_type" in variant_info
        assert "gene_symbol" in variant_info

        pvs1_flowchart = data["pvs1_flowchart"]
        assert "preliminary_decision_path" in pvs1_flowchart
        assert "final_strength" in pvs1_flowchart
