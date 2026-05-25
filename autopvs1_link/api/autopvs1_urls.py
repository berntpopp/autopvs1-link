"""URL construction helpers for AutoPVS1 upstream requests."""

from __future__ import annotations


def variant_url(base_url: str, genome_build: str, variant_id: str) -> str:
    """Return the upstream URL for a variant page."""
    return f"{base_url}/variant/{genome_build}/{variant_id}"


def cnv_url(base_url: str, genome_build: str, cnv_id: str) -> str:
    """Return the upstream URL for a CNV page."""
    return f"{base_url}/cnv/{genome_build}/{cnv_id}"


def search_url(base_url: str) -> str:
    """Return the upstream URL for the search endpoint."""
    return f"{base_url}/search"


def search_display_url(base_url: str, query: str, genome_version: str) -> str:
    """Return the display form of an upstream search URL."""
    return f"{search_url(base_url)}?q={query}&genome_version={genome_version}"
