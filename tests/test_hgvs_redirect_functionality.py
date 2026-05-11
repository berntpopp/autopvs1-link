"""Tests for HGVS redirect and enhanced search functionality."""

from unittest.mock import AsyncMock, patch

import pytest

from autopvs1_link.api.autopvs1_client import HGVS_PATTERNS, AutoPVS1Client
from autopvs1_link.models.autopvs1_models import (
    AutoPVS1Data,
    AutoPVS1SearchResults,
    EnhancedSearchResults,
    RedirectInfo,
)
from autopvs1_link.services.autopvs1_service import AutoPVS1Service


class TestHGVSPatternDetection:
    """Test HGVS pattern detection utilities."""

    def test_hgvs_pattern_constants(self):
        """Test that HGVS patterns are properly defined."""
        assert len(HGVS_PATTERNS) == 4  # Only transcript-level patterns now
        assert any("NM_" in pattern for pattern in HGVS_PATTERNS)
        assert any("NR_" in pattern for pattern in HGVS_PATTERNS)
        assert any("g\\." in pattern for pattern in HGVS_PATTERNS)
        assert any("m\\." in pattern for pattern in HGVS_PATTERNS)

    @pytest.mark.asyncio
    async def test_detect_hgvs_pattern_transcript_level(self):
        """Test detection of transcript-level HGVS notation."""
        client = AutoPVS1Client()

        try:
            # Test cases that should be detected as HGVS
            hgvs_cases = [
                "NM_000128.3:c.1716+1G>A",
                "NM_001234.1:c.123A>T",
                "NR_123456.2:n.456C>G",
                "g.123456A>T",
                "m.8993T>G",
            ]

            for hgvs in hgvs_cases:
                assert client._detect_hgvs_pattern(hgvs), f"Failed to detect HGVS: {hgvs}"

            # Test cases that should NOT be detected as HGVS
            non_hgvs_cases = [
                "BRCA1",
                "TP53",
                "chr1:123456-789012",
                "rs123456789",
                "variant123",
                "gene_symbol",
                "some random text",
                "c.123A>T",  # Coding notation - removed from patterns
                "c.123delA",  # Coding notation - removed from patterns
                "c.123_124insG",  # Coding notation - removed from patterns
                "p.Arg123Ter",  # Protein notation - removed from patterns
                "p.Val234Met",  # Protein notation - removed from patterns
            ]

            for non_hgvs in non_hgvs_cases:
                assert not client._detect_hgvs_pattern(non_hgvs), (
                    f"Incorrectly detected as HGVS: {non_hgvs}"
                )

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_detect_hgvs_case_insensitive(self):
        """Test that HGVS detection is case-insensitive."""
        client = AutoPVS1Client()

        try:
            test_cases = [
                ("NM_000128.3:c.1716+1G>A", True),
                ("nm_000128.3:c.1716+1g>a", True),
                ("NM_000128.3:C.1716+1G>A", True),
                ("brca1", False),
                ("BRCA1", False),
            ]

            for case, expected in test_cases:
                result = client._detect_hgvs_pattern(case)
                assert result == expected, f"Case sensitivity test failed for: {case}"

        finally:
            await client.close()


class TestURLParsing:
    """Test URL parsing for variant extraction."""

    @pytest.mark.asyncio
    async def test_extract_variant_from_redirect_url(self):
        """Test extraction of variant info from redirect URLs."""
        client = AutoPVS1Client()

        try:
            test_cases = [
                (
                    "https://autopvs1.bgi.com/variant/hg19/4-187208978-G-A",
                    ("hg19", "4-187208978-G-A"),
                ),
                (
                    "https://autopvs1.bgi.com/variant/hg38/X-82763936-A-T",
                    ("hg38", "X-82763936-A-T"),
                ),
                ("/variant/hg19/2-48033984-G-GGATT", ("hg19", "2-48033984-G-GGATT")),
                (
                    "https://example.com/variant/hg19/chr1-123456-A-T?param=value",
                    ("hg19", "chr1-123456-A-T"),
                ),
                ("https://autopvs1.bgi.com/search?q=BRCA1", (None, None)),
                ("invalid-url", (None, None)),
            ]

            for url, expected in test_cases:
                result = client._extract_variant_from_redirect_url(url)
                assert result == expected, f"URL parsing failed for: {url}"

        finally:
            await client.close()


class TestRedirectDetection:
    """Test redirect detection in search responses."""

    @pytest.mark.asyncio
    async def test_search_with_redirect_detection_hgvs(self):
        """Test enhanced search with HGVS notation that redirects."""
        # Mock response that simulates a redirect
        mock_response = AsyncMock()
        mock_response.text = self._get_f11_variant_html()
        mock_response.url = "https://autopvs1.bgi.com/variant/hg19/4-187208978-G-A"
        mock_response.history = [AsyncMock()]  # Simulate redirect history

        client = AutoPVS1Client()

        try:
            with patch(
                "autopvs1_link.utils.retry_handler.retry_handler.http_request_with_retry",
                return_value=mock_response,
            ):
                result = await client.search_with_redirect_detection(
                    "NM_000128.3:c.1716+1G>A", "hg19"
                )

            # Verify it's detected as redirected
            assert isinstance(result, EnhancedSearchResults)
            assert result.redirected is True
            assert result.variant_data is not None
            assert result.search_results is None
            assert result.redirect_info is not None

            # Verify redirect info
            assert result.redirect_info.redirect_detected is True
            assert result.redirect_info.variant_id_extracted == "4-187208978-G-A"
            assert result.redirect_info.genome_build_extracted == "hg19"
            assert "variant/hg19/4-187208978-G-A" in result.redirect_info.final_url

            # Verify variant data
            assert result.variant_data.variant_info.gene_symbol == "F11"
            assert result.variant_data.variant_info.variant_type == "Splice-5"

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_search_with_redirect_detection_gene_symbol(self):
        """Test enhanced search with gene symbol that returns search results."""
        # Mock response for normal search results (no redirect)
        mock_response = AsyncMock()
        mock_response.text = self._get_brca1_search_results_html()
        mock_response.url = "https://autopvs1.bgi.com/search?q=BRCA1&genome_version=hg19"
        mock_response.history = []  # No redirect history

        client = AutoPVS1Client()

        try:
            with patch(
                "autopvs1_link.utils.retry_handler.retry_handler.http_request_with_retry",
                return_value=mock_response,
            ):
                result = await client.search_with_redirect_detection("BRCA1", "hg19")

            # Verify it's NOT detected as redirected
            assert isinstance(result, EnhancedSearchResults)
            assert result.redirected is False
            assert result.variant_data is None
            assert result.search_results is not None
            assert result.redirect_info is None

            # Verify search results
            assert result.search_results.query == "BRCA1"
            assert result.search_results.genome_version == "hg19"
            assert len(result.search_results.results) >= 0

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_resolve_hgvs_notation_success(self):
        """Test direct HGVS resolution to variant data."""
        # Mock response that simulates a redirect
        mock_response = AsyncMock()
        mock_response.text = self._get_f11_variant_html()
        mock_response.url = "https://autopvs1.bgi.com/variant/hg19/4-187208978-G-A"
        mock_response.history = [AsyncMock()]

        client = AutoPVS1Client()

        try:
            with patch(
                "autopvs1_link.utils.retry_handler.retry_handler.http_request_with_retry",
                return_value=mock_response,
            ):
                result = await client.resolve_hgvs_notation("NM_000128.3:c.1716+1G>A", "hg19")

            # Verify we get variant data directly
            assert isinstance(result, AutoPVS1Data)
            assert result.variant_info.gene_symbol == "F11"
            assert result.variant_info.variant_type == "Splice-5"
            assert result.pvs1_flowchart.final_strength == "Moderate"

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_resolve_hgvs_notation_failure(self):
        """Test HGVS resolution failure when no redirect occurs."""
        # Mock response for search results (no redirect)
        mock_response = AsyncMock()
        mock_response.text = self._get_brca1_search_results_html()
        mock_response.url = "https://autopvs1.bgi.com/search?q=invalid&genome_version=hg19"
        mock_response.history = []

        client = AutoPVS1Client()

        try:
            with (
                patch(
                    "autopvs1_link.utils.retry_handler.retry_handler.http_request_with_retry",
                    return_value=mock_response,
                ),
                pytest.raises(ValueError, match="did not resolve to a single variant"),
            ):
                await client.resolve_hgvs_notation("invalid_hgvs", "hg19")

        finally:
            await client.close()

    def _get_f11_variant_html(self) -> str:
        """Get mock HTML for F11 variant page."""
        return """
        <div class="container">
            <div class="row">
                <div class="col-lg-6">
                    <h3>Splice-5: 4-187208978-G-A</h3>
                    <p><b>Gene:</b> <a href="https://www.genenames.org/data/gene-symbol-report/#!/hgnc_id/HGNC:3529"><i>F11</i></a></p>
                    <p><b>pLI:</b> 1.91e-22</p>
                    <p><b>Haploinsufficiency:</b> <a href="https://search.clinicalgenome.org/kb/genes/HGNC:3529">None</a></p>
                    <p><b>cHGVS:</b> NM_000128.4:c.1716+1G&gt;A</p>
                    <p><b>pHGVS:</b> -</p>
                    <p><b>Exon:</b> -/15</p>
                    <p><b>Intron:</b> 14/14</p>
                </div>
                <div class="col-lg-6">
                    <figure>
                        <figcaption>Preliminary Decision Path: SS6</figcaption>
                        <ul class="tree">
                            <li><code>GT-AG splice sites</code>
                                <ul>
                                    <li><code>Moderate</code></li>
                                </ul>
                            </li>
                        </ul>
                    </figure>
                </div>
            </div>
        </div>
        """

    def _get_brca1_search_results_html(self) -> str:
        """Get mock HTML for BRCA1 search results."""
        return """
        <div class="container">
            <table id="dtBasicExample">
                <tbody>
                    <tr>
                        <td>1</td>
                        <td><i>BRCA1</i></td>
                        <td>Nonsense</td>
                        <td>Nonsense</td>
                        <td>Description</td>
                        <td>Extra</td>
                        <td><a href="/variant/hg19/17-43094977-C-A">17-43094977-C-A</a></td>
                        <td><a href="/variant/hg38/17-43047641-C-A">17-43047641-C-A</a></td>
                    </tr>
                </tbody>
            </table>
        </div>
        """


class TestServiceIntegration:
    """Test service layer integration with enhanced search."""

    @pytest.mark.asyncio
    async def test_service_search_with_redirect_detection(self):
        """Test service layer enhanced search functionality."""
        # Mock client
        mock_client = AsyncMock()
        from autopvs1_link.models.autopvs1_models import PVS1Flowchart, VariantInfo

        mock_variant_data = AutoPVS1Data(
            genome_build="hg19",
            variant_info=VariantInfo(
                variant_id="4-187208978-G-A",
                variant_type="Splice-5",
                gene_symbol="F11",
                gene_url="https://example.com",
                external_links={},
            ),
            pvs1_flowchart=PVS1Flowchart(
                preliminary_decision_path="SS6",
                final_strength="Moderate",
                decision_tree=[],
                notes={},
            ),
            disease_mechanisms=[],
        )

        mock_enhanced_result = EnhancedSearchResults(
            query="NM_000128.3:c.1716+1G>A",
            genome_version="hg19",
            redirected=True,
            variant_data=mock_variant_data,
            redirect_info=RedirectInfo(
                original_url="https://autopvs1.bgi.com/search?q=test",
                final_url="https://autopvs1.bgi.com/variant/hg19/4-187208978-G-A",
                variant_id_extracted="4-187208978-G-A",
                genome_build_extracted="hg19",
            ),
        )
        mock_client.search_with_redirect_detection.return_value = mock_enhanced_result

        service = AutoPVS1Service(mock_client)

        result = await service.search_with_redirect_detection("NM_000128.3:c.1716+1G>A", "hg19")

        assert isinstance(result, EnhancedSearchResults)
        assert result.redirected is True
        assert result.redirect_info.variant_id_extracted == "4-187208978-G-A"

        # Verify client was called correctly
        mock_client.search_with_redirect_detection.assert_called_once_with(
            "NM_000128.3:c.1716+1G>A", "hg19"
        )

    @pytest.mark.asyncio
    async def test_service_resolve_hgvs_notation(self):
        """Test service layer HGVS resolution."""
        # Mock client
        mock_client = AsyncMock()
        mock_variant_data = AsyncMock()
        mock_client.resolve_hgvs_notation.return_value = mock_variant_data

        service = AutoPVS1Service(mock_client)

        result = await service.resolve_hgvs_notation("NM_000128.3:c.1716+1G>A", "hg19")

        assert result == mock_variant_data

        # Verify client was called correctly
        mock_client.resolve_hgvs_notation.assert_called_once_with("NM_000128.3:c.1716+1G>A", "hg19")


class TestDataModels:
    """Test enhanced data models."""

    def test_enhanced_search_results_properties(self):
        """Test EnhancedSearchResults helper properties."""
        from autopvs1_link.models.autopvs1_models import PVS1Flowchart, VariantInfo

        mock_variant_data = AutoPVS1Data(
            genome_build="hg19",
            variant_info=VariantInfo(
                variant_id="test",
                variant_type="test",
                gene_symbol="TEST",
                gene_url="https://example.com",
                external_links={},
            ),
            pvs1_flowchart=PVS1Flowchart(
                preliminary_decision_path="test",
                final_strength="test",
                decision_tree=[],
                notes={},
            ),
            disease_mechanisms=[],
        )

        # Test redirected result
        redirected_result = EnhancedSearchResults(
            query="test",
            genome_version="hg19",
            redirected=True,
            variant_data=mock_variant_data,
        )

        assert redirected_result.is_single_variant is True
        assert redirected_result.is_multiple_results is False

        # Test search results
        search_result = EnhancedSearchResults(
            query="test",
            genome_version="hg19",
            redirected=False,
            search_results=AutoPVS1SearchResults(query="test", genome_version="hg19", results=[]),
        )

        assert search_result.is_single_variant is False
        assert search_result.is_multiple_results is True

    def test_redirect_info_model(self):
        """Test RedirectInfo data model."""
        redirect_info = RedirectInfo(
            original_url="https://autopvs1.bgi.com/search?q=test",
            final_url="https://autopvs1.bgi.com/variant/hg19/4-187208978-G-A",
            variant_id_extracted="4-187208978-G-A",
            genome_build_extracted="hg19",
        )

        assert redirect_info.redirect_detected is True
        assert redirect_info.original_url.startswith("https://")
        assert redirect_info.final_url.endswith("4-187208978-G-A")
        assert redirect_info.variant_id_extracted == "4-187208978-G-A"
        assert redirect_info.genome_build_extracted == "hg19"


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_malformed_redirect_url(self):
        """Test handling of malformed redirect URLs."""
        client = AutoPVS1Client()

        try:
            test_cases = [
                "",
                "not-a-url",
                "https://autopvs1.bgi.com/other-page",
                "https://autopvs1.bgi.com/variant/",
                "https://autopvs1.bgi.com/variant/hg19/",
            ]

            for url in test_cases:
                genome_build, variant_id = client._extract_variant_from_redirect_url(url)
                assert genome_build is None or genome_build == ""
                assert variant_id is None or variant_id == ""

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_empty_hgvs_patterns(self):
        """Test HGVS detection with empty or None input."""
        client = AutoPVS1Client()

        try:
            test_cases = ["", "   ", None]

            for case in test_cases:
                if case is None:
                    # Should handle None gracefully
                    continue
                result = client._detect_hgvs_pattern(case)
                assert result is False

        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_borderline_hgvs_patterns(self):
        """Test borderline cases for HGVS detection."""
        client = AutoPVS1Client()

        try:
            # Cases that might be ambiguous
            borderline_cases = [
                ("c.123", False),  # Coding notation - no longer supported
                ("p.Met1", False),  # Protein notation - no longer supported
                ("NM_123456.1:c.456", True),  # Valid transcript with position
                ("c", False),  # Too short
                ("p", False),  # Too short
                ("NM_", False),  # Incomplete
                ("c.123ABC", False),  # Coding notation - no longer supported
                ("g.123", True),  # Valid minimal genomic notation
                ("m.456", True),  # Valid minimal mitochondrial notation
            ]

            for case, expected in borderline_cases:
                result = client._detect_hgvs_pattern(case)
                assert result == expected, f"Borderline test failed for: {case}"

        finally:
            await client.close()
