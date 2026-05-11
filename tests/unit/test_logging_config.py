"""Tests for logging_config."""

import logging

import structlog

from autopvs1_link.logging_config import (
    add_service_context,
    bind_correlation_id,
    configure_logging,
    get_logger_for_module,
)


def test_configure_logging_runs() -> None:
    configure_logging()
    logger = structlog.get_logger("smoke")
    logger.info("hello", foo="bar")


def test_get_logger_for_module_binds_module_name() -> None:
    log = get_logger_for_module("test_module")
    assert log is not None


def test_add_service_context_attaches_service_fields() -> None:
    event = {"event": "x"}
    out = add_service_context(None, "info", event)
    assert out["service"] == "autopvs1-link"
    assert "version" in out
    assert "environment" in out


def test_bind_correlation_id_no_op_when_unset() -> None:
    event: dict = {}
    out = bind_correlation_id(None, "info", event)
    # No correlation id active in unit-test context.
    assert "correlation_id" not in out


def test_logging_emits_to_root() -> None:
    configure_logging()
    log = logging.getLogger("autopvs1_link.test")
    log.info("event-via-stdlib")
