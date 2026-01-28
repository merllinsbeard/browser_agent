"""Tests for action result models."""

from browser_agent.models.result import (
    FailureResult,
    SuccessResult,
    failure_result,
    success_result,
)
from browser_agent.models.snapshot import PageSnapshot


class TestSuccessResult:
    def test_creation(self) -> None:
        result = SuccessResult(message="Clicked button")
        assert result.message == "Clicked button"
        assert result.success is True
        assert result.error is None
        assert result.new_snapshot is None

    def test_with_snapshot(self) -> None:
        snap = PageSnapshot(url="https://example.com", title="Example")
        result = SuccessResult(message="Navigated", new_snapshot=snap)
        assert result.new_snapshot is not None
        assert result.new_snapshot.url == "https://example.com"

    def test_success_property_always_true(self) -> None:
        result = SuccessResult(message="OK")
        assert result.success is True

    def test_error_property_always_none(self) -> None:
        result = SuccessResult(message="OK")
        assert result.error is None


class TestFailureResult:
    def test_creation(self) -> None:
        result = FailureResult(message="Failed to click", error="Element not found")
        assert result.message == "Failed to click"
        assert result.error == "Element not found"
        assert result.success is False
        assert result.new_snapshot is None

    def test_success_property_always_false(self) -> None:
        result = FailureResult(message="Error", error="Something broke")
        assert result.success is False

    def test_new_snapshot_always_none(self) -> None:
        result = FailureResult(message="Error", error="Oops")
        assert result.new_snapshot is None

    def test_error_required(self) -> None:
        from pydantic import ValidationError
        import pytest

        with pytest.raises(ValidationError):
            FailureResult(message="Error")  # type: ignore[call-arg]


class TestFactoryFunctions:
    def test_success_result_factory(self) -> None:
        result = success_result("Done")
        assert isinstance(result, SuccessResult)
        assert result.success is True
        assert result.message == "Done"

    def test_success_result_factory_with_snapshot(self) -> None:
        snap = PageSnapshot(url="https://example.com", title="Example")
        result = success_result("OK", new_snapshot=snap)
        assert isinstance(result, SuccessResult)
        assert result.new_snapshot is not None  # type: ignore[union-attr]

    def test_failure_result_factory(self) -> None:
        result = failure_result("Failed", error="Timeout")
        assert isinstance(result, FailureResult)
        assert result.success is False
        assert result.error == "Timeout"  # type: ignore[union-attr]

    def test_failure_result_factory_defaults_error_to_message(self) -> None:
        result = failure_result("Connection lost")
        assert isinstance(result, FailureResult)
        assert result.error == "Connection lost"  # type: ignore[union-attr]
