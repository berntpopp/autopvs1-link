"""Tests for the defusedxml hardening shim."""

import xml.sax


def test_xml_sax_is_defused() -> None:
    """``autopvs1_link`` import patches xml.sax.make_parser to defusedxml."""
    import defusedxml.sax as defused_sax

    import autopvs1_link  # noqa: F401  # triggers defuse_stdlib

    assert xml.sax.make_parser is defused_sax.make_parser
