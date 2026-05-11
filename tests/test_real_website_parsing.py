"""Tests for real website parsing with improved extraction logic."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from bs4 import BeautifulSoup

from autopvs1_link.api.autopvs1_client import AutoPVS1Client
from autopvs1_link.models.autopvs1_models import AutoPVS1Data


def load_fixture(name: str) -> str:
    """Load HTML fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / name
    return fixture_path.read_text(encoding="utf-8")


class TestRealWebsiteParsing:
    """Test parsing with real website HTML data."""

    @pytest.mark.asyncio
    async def test_parse_msh6_variant_with_unmet_strength(self):
        """Test parsing MSH6 variant that should have 'Unmet' final strength."""
        html_content = load_fixture("variant_2_48033984_G_GGATT_hg19.html")

        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.text = html_content

        client = AutoPVS1Client()

        try:
            with patch(
                "autopvs1_link.utils.retry_handler.retry_handler.http_request_with_retry",
                return_value=mock_response,
            ):
                result = await client.get_variant_data("hg19", "2-48033984-G-GGATT")
        finally:
            await client.close()

        # Verify basic structure
        assert isinstance(result, AutoPVS1Data)
        assert result.genome_build == "hg19"

        # Verify variant info with previously missing fields
        variant_info = result.variant_info
        assert variant_info.variant_id == "2-48033984-G-GGATT"
        assert variant_info.variant_type == "Frameshift"
        assert variant_info.gene_symbol == "MSH6"
        assert (
            variant_info.gene_url
            == "https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:7329"
        )

        # Test previously missing fields
        assert variant_info.chgvs == "NM_000179.3:c.4068_4069insGATT"
        assert variant_info.phgvs == "NP_000170.1:p.Ile1357AspfsTer3"
        assert variant_info.exon == "10/10"
        assert variant_info.intron == "-/9"
        assert variant_info.pli_score is None  # "na" should not be converted to float
        assert variant_info.haploinsufficiency == "3"
        assert (
            variant_info.haploinsufficiency_url
            == "https://search.clinicalgenome.org/kb/genes/HGNC:7329"
        )

        # Test external links
        assert "OMIM" in variant_info.external_links
        assert variant_info.external_links["OMIM"] == "https://mirror.omim.org/entry/600678"
        assert "gnomAD" in variant_info.external_links
        assert (
            variant_info.external_links["gnomAD"]
            == "https://gnomad.broadinstitute.org/variant/2-48033984-G-GGATT"
        )

        # Verify PVS1 flowchart - most importantly final_strength
        flowchart = result.pvs1_flowchart
        assert flowchart.preliminary_decision_path == "NF4"
        assert flowchart.final_strength == "Unmet"  # This was previously empty!

        # Verify decision tree contains expected steps
        decision_codes = [step.code for step in flowchart.decision_tree]
        assert "Nonsense or Frameshift" in decision_codes
        assert "Unmet" in decision_codes

        # Verify notes parsing
        assert "#1" in flowchart.notes
        assert "#2" in flowchart.notes
        assert "3.30e-02" in flowchart.notes["#2"]

        # Verify disease mechanisms
        assert len(result.disease_mechanisms) == 3
        mechanisms = result.disease_mechanisms

        # Check first mechanism
        assert mechanisms[0].gene == "MSH6"
        assert mechanisms[0].disease == "hereditary breast carcinoma"
        assert mechanisms[0].inheritance == "AD"
        assert mechanisms[0].clinical_validity == "Disputed"
        assert mechanisms[0].consideration == "Not applicable"
        assert mechanisms[0].adjusted_strength == "Unmet"

        # Check Lynch syndrome mechanism
        lynch_mechanism = next((m for m in mechanisms if "Lynch" in m.disease), None)
        assert lynch_mechanism is not None
        assert lynch_mechanism.disease == "Lynch syndrome"
        assert lynch_mechanism.clinical_validity == "Definitive"
        assert lynch_mechanism.consideration == "No Decrease"
        assert lynch_mechanism.adjusted_strength == "Unmet"

    @pytest.mark.asyncio
    async def test_parse_pou3f4_variant_with_strong_strength(self):
        """Test parsing POU3F4 variant that should have 'Strong' final strength."""
        html_content = load_fixture("variant_X_82763936_A_T_hg19.html")

        # Mock the HTTP response
        mock_response = AsyncMock()
        mock_response.text = html_content

        client = AutoPVS1Client()

        try:
            with patch(
                "autopvs1_link.utils.retry_handler.retry_handler.http_request_with_retry",
                return_value=mock_response,
            ):
                result = await client.get_variant_data("hg19", "X-82763936-A-T")
        finally:
            await client.close()

        # Verify basic structure
        assert isinstance(result, AutoPVS1Data)
        assert result.genome_build == "hg19"

        # Verify variant info with previously missing fields
        variant_info = result.variant_info
        assert variant_info.variant_id == "X-82763936-A-T"
        assert variant_info.variant_type == "Nonsense"
        assert variant_info.gene_symbol == "POU3F4"
        assert (
            variant_info.gene_url
            == "https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:9217"
        )

        # Test previously missing fields
        assert variant_info.chgvs == "NM_000307.5:c.604A>T"
        assert variant_info.phgvs == "NP_000298.3:p.Lys202Ter"
        assert variant_info.exon == "1/1"
        assert variant_info.intron == "-/0"
        assert variant_info.pli_score == 0.72  # Should be parsed as float
        assert variant_info.haploinsufficiency == "None"
        assert (
            variant_info.haploinsufficiency_url
            == "https://search.clinicalgenome.org/kb/genes/HGNC:9217"
        )

        # Verify PVS1 flowchart - most importantly final_strength
        flowchart = result.pvs1_flowchart
        assert flowchart.preliminary_decision_path == "NF5"
        assert flowchart.final_strength == "Strong"  # This should be parsed correctly

        # Verify decision tree contains expected steps
        decision_codes = [step.code for step in flowchart.decision_tree]
        assert "Nonsense or Frameshift" in decision_codes
        assert "Strong" in decision_codes

        # Verify disease mechanisms
        assert len(result.disease_mechanisms) == 1
        mechanism = result.disease_mechanisms[0]
        assert mechanism.gene == "POU3F4"
        assert mechanism.disease == "nonsyndromic genetic deafness"
        assert mechanism.inheritance == "XL"
        assert mechanism.clinical_validity == "Definitive"
        assert mechanism.consideration == "No Decrease"
        assert mechanism.adjusted_strength == "Strong"

    @pytest.mark.asyncio
    async def test_field_extraction_edge_cases(self):
        """Test edge cases in field extraction."""
        # Test HTML with different field formats
        html_with_na_pli = """
        <div class="col-lg-6">
            <p><b>pLI:</b> na</p>
            <p><b>Haploinsufficiency:</b> <a href="test.com">None</a></p>
            <p><b>cHGVS:</b> NM_001234.1:c.123A>T</p>
        </div>
        """

        soup = BeautifulSoup(html_with_na_pli, "lxml")
        container = soup.select_one(".col-lg-6")

        client = AutoPVS1Client()

        try:
            # Test pLI parsing with "na"
            pli_text = client._extract_field_value(container, "pLI:")
            assert pli_text == "na"

            # Test cHGVS parsing
            chgvs = client._extract_field_value(container, "cHGVS:")
            assert chgvs == "NM_001234.1:c.123A>T"

            # Test haploinsufficiency with link
            haploinsuff_p = client._find_field_paragraph(container, "Haploinsufficiency:")
            assert haploinsuff_p is not None
            link = haploinsuff_p.find("a")
            assert link.text.strip() == "None"
            assert link.get("href") == "test.com"
        finally:
            # Cleanup without async issues for sync test
            pass

    def test_final_strength_extraction_comprehensive(self):
        """Test comprehensive final strength extraction with different HTML structures."""
        # Test all possible final strengths
        test_cases = [
            ("Strong", "Strong"),
            ("Moderate", "Moderate"),
            ("Supporting", "Supporting"),
            ("Not applicable", "Not applicable"),
            ("Unmet", "Unmet"),
        ]

        for strength, expected in test_cases:
            html = f"""
            <div class="container">
                <div class="row">
                    <div class="col-lg-6">
                        <ul class="tree">
                            <li><code>Some decision</code>
                                <ul>
                                    <li><code>Another decision</code>
                                        <ul>
                                            <li><code>{strength}</code></li>
                                        </ul>
                                    </li>
                                </ul>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>
            """

            soup = BeautifulSoup(html, "lxml")

            client = AutoPVS1Client()
            try:
                flowchart = client._parse_pvs1_flowchart(soup)
                assert flowchart.final_strength == expected, f"Failed to parse strength: {strength}"
            finally:
                # Cleanup without async issues for sync test
                pass
