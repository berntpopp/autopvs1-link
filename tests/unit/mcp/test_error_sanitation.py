"""Unit contract for ``sanitize_message`` (error-message code-point stripping).

``sanitize_message`` is the defensive backstop applied to every caller-visible
error message/detail string so a hostile upstream (or a caller-influenced
4xx/5xx error body) can never smuggle control, zero-width, bidirectional, or
NUL code points into an error frame the model reads. It reuses the untrusted
fence's ``FORBIDDEN_CODEPOINTS`` so the two paths stay in lockstep.
"""

from __future__ import annotations

from autopvs1_link.mcp.untrusted_content import (
    FORBIDDEN_CODEPOINTS,
    MAX_MESSAGE_CHARS,
    sanitize_message,
)


def test_strips_nul_zwj_bom_and_bidi_override() -> None:
    dirty = "boom\x00‍﻿‮ tail"
    cleaned = sanitize_message(dirty)
    for cp in ("\x00", "‍", "﻿", "‮"):
        assert cp not in cleaned
    # ordinary prose survives verbatim; only the control code points are removed
    assert cleaned == "boom tail"


def test_preserves_ordinary_prose_and_safe_whitespace() -> None:
    # Newlines and tabs are NOT in the forbidden set; ordinary punctuation and
    # scientific notation survive untouched.
    text = "AutoPVS1 rejected c.5266dup\tas invalid.\nRetry with a canonical id."
    assert sanitize_message(text) == text


def test_length_capped_at_max_message_chars() -> None:
    assert MAX_MESSAGE_CHARS == 280
    capped = sanitize_message("x" * 5000)
    assert len(capped) == MAX_MESSAGE_CHARS


def test_removes_every_forbidden_codepoint() -> None:
    dirty = "".join(chr(cp) for cp in sorted(FORBIDDEN_CODEPOINTS)) + "visible"
    cleaned = sanitize_message(dirty)
    assert cleaned == "visible"
    assert all(ord(c) not in FORBIDDEN_CODEPOINTS for c in cleaned)
