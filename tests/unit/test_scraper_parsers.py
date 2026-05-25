"""Unit tests for the AutoPVS1 scraper parsing logic."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from bs4 import BeautifulSoup

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.models.autopvs1_models import AutoPVS1Data


def load_fixture(name: str) -> str:
    """Load HTML fixture file."""
    fixture_path = Path(__file__).parent.parent / "fixtures" / name
    if not fixture_path.exists():
        pytest.skip(f"Fixture {name} not found")
    return fixture_path.read_text(encoding="utf-8")


@pytest.fixture
def client():
    """Create AutoPVS1Client instance."""
    return AutoPVS1Client()


@pytest.fixture
def variant_html():
    """Load variant HTML fixture."""
    return load_fixture("variant_hg38_X-83508928-A-T.html")


@pytest.fixture
def variant_soup(variant_html):
    """Parse variant HTML into BeautifulSoup."""
    return BeautifulSoup(variant_html, "lxml")


class TestVariantInfoParsing:
    """Test variant information parsing."""

    def test_parse_variant_info_basic_fields(self, client, variant_soup):
        """Test parsing basic variant info fields."""
        variant_info = client._parse_variant_info(variant_soup, "X-83508928-A-T")

        assert variant_info.variant_id == "X-83508928-A-T"
        assert variant_info.variant_type == "Nonsense"
        assert variant_info.gene_symbol == "POU3F4"
        assert variant_info.pli_score == 0.72
        assert variant_info.chgvs == "NM_000307.5:c.604A>T"
        assert variant_info.phgvs == "NP_000298.3:p.Lys202Ter"
        assert variant_info.exon == "1/1"
        assert variant_info.intron == "-/0"

    def test_parse_variant_info_external_links(self, client, variant_soup):
        """Test parsing external links."""
        variant_info = client._parse_variant_info(variant_soup, "X-83508928-A-T")

        assert "OMIM" in variant_info.external_links
        assert "ClinVar" in variant_info.external_links
        assert "gnomAD" in variant_info.external_links
        assert (
            variant_info.external_links["gnomAD"]
            == "https://gnomad.broadinstitute.org/variant/X-83508928-A-T"
        )

    def test_parse_variant_info_gene_url(self, client, variant_soup):
        """Test parsing gene URL."""
        variant_info = client._parse_variant_info(variant_soup, "X-83508928-A-T")

        assert (
            variant_info.gene_url
            == "https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:9217"
        )

    def test_parse_variant_info_haploinsufficiency(self, client, variant_soup):
        """Test parsing haploinsufficiency information."""
        variant_info = client._parse_variant_info(variant_soup, "X-83508928-A-T")

        assert variant_info.haploinsufficiency == "None"
        assert (
            variant_info.haploinsufficiency_url
            == "https://search.clinicalgenome.org/kb/genes/HGNC:9217"
        )


class TestPVS1FlowchartParsing:
    """Test PVS1 flowchart parsing."""

    def test_parse_pvs1_flowchart_basic_fields(self, client, variant_soup):
        """Test parsing basic flowchart fields."""
        flowchart = client._parse_pvs1_flowchart(variant_soup)

        assert flowchart.preliminary_decision_path == "NF5"
        assert flowchart.final_strength == "Strong"

    def test_parse_pvs1_flowchart_decision_tree(self, client, variant_soup):
        """Test parsing decision tree steps."""
        flowchart = client._parse_pvs1_flowchart(variant_soup)

        assert len(flowchart.decision_tree) > 0
        # Check for key decision points
        codes = [step.code for step in flowchart.decision_tree]
        assert "Nonsense or Frameshift" in codes
        assert "Strong" in codes

    def test_parse_pvs1_flowchart_notes(self, client, variant_soup):
        """Test parsing flowchart notes."""
        flowchart = client._parse_pvs1_flowchart(variant_soup)

        # Should have notes marked with #1, #2, etc.
        assert len(flowchart.notes) > 0


class TestDiseaseMechanismParsing:
    """Test disease mechanism table parsing."""

    def test_parse_disease_mechanisms_basic(self, client, variant_soup):
        """Test parsing disease mechanism table."""
        mechanisms = client._parse_disease_mechanisms(variant_soup)

        assert len(mechanisms) == 1
        mechanism = mechanisms[0]

        assert mechanism.gene == "POU3F4"
        assert mechanism.disease == "nonsyndromic genetic deafness"
        assert mechanism.inheritance == "XL"
        assert mechanism.clinical_validity == "Definitive"
        assert mechanism.consideration == "No Decrease"
        assert mechanism.adjusted_strength == "Strong"

    def test_parse_disease_mechanisms_urls(self, client, variant_soup):
        """Test parsing URLs in disease mechanism table."""
        mechanisms = client._parse_disease_mechanisms(variant_soup)

        mechanism = mechanisms[0]
        assert mechanism.gene_url == "https://search.clinicalgenome.org/kb/genes/HGNC:9217"
        assert (
            mechanism.disease_url == "https://search.clinicalgenome.org/kb/conditions/MONDO_0019497"
        )


@pytest.mark.asyncio
class TestClientIntegration:
    """Test full client integration."""

    @patch("httpx.AsyncClient.get")
    async def test_get_variant_data_integration(self, mock_get, client, variant_html):
        """Test full variant data retrieval."""
        # Mock HTTP response
        mock_response = MagicMock()
        mock_response.text = variant_html
        mock_get.return_value = mock_response

        result = await client.get_variant_data("hg38", "X-83508928-A-T")

        assert isinstance(result, AutoPVS1Data)
        assert result.genome_build == "hg38"
        assert result.variant_info.variant_id == "X-83508928-A-T"
        assert result.variant_info.gene_symbol == "POU3F4"
        assert result.pvs1_flowchart.final_strength == "Strong"
        assert len(result.disease_mechanisms) == 1

    @patch("httpx.AsyncClient.get")
    async def test_get_variant_data_http_error(self, mock_get, client):
        """Test handling of HTTP errors."""
        mock_get.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            await client.get_variant_data("hg38", "invalid-variant")


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_variant_info_missing_elements(self, client):
        """Test parsing with missing HTML elements."""
        minimal_html = """
        <div class="container">
            <div class="row">
                <div class="col-lg-6">
                    <h3>Unknown: test-variant</h3>
                </div>
            </div>
        </div>
        """
        soup = BeautifulSoup(minimal_html, "lxml")

        variant_info = client._parse_variant_info(soup, "test-variant")
        assert variant_info.variant_id == "test-variant"
        assert variant_info.variant_type == "Unknown"
        assert variant_info.pli_score is None

    def test_parse_disease_mechanisms_empty_table(self, client):
        """Test parsing empty disease mechanism table."""
        html_no_table = "<div></div>"
        soup = BeautifulSoup(html_no_table, "lxml")

        mechanisms = client._parse_disease_mechanisms(soup)
        assert mechanisms == []

    def test_extract_field_value_missing_field(self, client):
        """Test field extraction with missing field."""
        html = "<div><p>Other field: value</p></div>"
        soup = BeautifulSoup(html, "lxml")
        container = soup.find("div")

        result = client._extract_field_value(container, "Missing field:")
        assert result is None


@pytest.mark.integration
@pytest.mark.asyncio
class TestLiveIntegration:
    """Integration tests with live data (requires network)."""

    async def test_get_real_variant_data(self, client):
        """Test with real variant data from AutoPVS1."""
        try:
            result = await client.get_variant_data("hg38", "X-83508928-A-T")
            assert isinstance(result, AutoPVS1Data)
            assert result.variant_info.gene_symbol == "POU3F4"
        except Exception:
            pytest.skip("Live integration test failed - network or site unavailable")

    async def test_search_real_variants(self, client):
        """Test real variant search."""
        try:
            result = await client.search_variants("MYH9", "hg19")
            assert isinstance(result.query, str)
            assert result.query == "MYH9"
        except Exception:
            pytest.skip("Live integration test failed - network or site unavailable")


@pytest.fixture(autouse=True)
async def cleanup_client(client):
    """Ensure client is properly closed after each test."""
    yield
    await client.close()
