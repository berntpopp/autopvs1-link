"""Inventory checks for real upstream HTML fixtures required by parser tests."""

from pathlib import Path

FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"

REQUIRED_VERYSTRONG_FIXTURES = {
    "variant_hg19_BRCA1_17-41276045-ACT-A.html": {
        "url": "https://autopvs1.bgi.com/variant/hg19/17-41276045-ACT-A",
        "genome_build": "hg19",
        "kind": "variant",
        "id": "17-41276045-ACT-A",
    },
    "cnv_hg19_MYO15A_17-15000000-20000000-DEL.html": {
        "url": "https://autopvs1.bgi.com/cnv/hg19/17-15000000-20000000-DEL",
        "genome_build": "hg19",
        "kind": "cnv",
        "id": "17-15000000-20000000-DEL",
    },
}


def test_required_verystrong_fixtures_are_real_upstream_captures() -> None:
    for filename, metadata in REQUIRED_VERYSTRONG_FIXTURES.items():
        path = FIXTURE_DIR / filename
        assert path.exists(), f"Missing required fixture: {filename}"
        text = path.read_text(encoding="utf-8")
        assert f"Captured from {metadata['url']}" in text
        assert f"genome_build={metadata['genome_build']}" in text
        assert f"{metadata['kind']}_id={metadata['id']}" in text
        assert "<code>VeryStrong</code>" in text
