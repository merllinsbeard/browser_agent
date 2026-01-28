"""Tests for PageSnapshot model."""

import pytest
from pydantic import ValidationError

from browser_agent.models.element import InteractiveElement
from browser_agent.models.snapshot import PageSnapshot


class TestPageSnapshot:
    def test_creation(self) -> None:
        snap = PageSnapshot(url="https://example.com", title="Example")
        assert snap.url == "https://example.com"
        assert snap.title == "Example"

    def test_default_values(self) -> None:
        snap = PageSnapshot(url="https://example.com", title="Example")
        assert snap.interactive_elements == []
        assert snap.visible_text_excerpt == ""
        assert snap.screenshot_path is None
        assert snap.notes == []
        assert snap.version == 0

    def test_with_elements(self) -> None:
        elem = InteractiveElement(ref="elem-0", role="link", name="Home")
        snap = PageSnapshot(
            url="https://example.com",
            title="Example",
            interactive_elements=[elem],
        )
        assert len(snap.interactive_elements) == 1
        assert snap.interactive_elements[0].role == "link"

    def test_with_version(self) -> None:
        snap = PageSnapshot(url="https://example.com", title="Example", version=0)
        new_snap = snap.with_version(5)
        assert new_snap.version == 5
        assert new_snap.url == snap.url
        assert new_snap.title == snap.title

    def test_frozen_immutability(self) -> None:
        snap = PageSnapshot(url="https://example.com", title="Example")
        with pytest.raises(ValidationError):
            snap.url = "https://other.com"  # type: ignore[misc]

    def test_url_and_title_required(self) -> None:
        with pytest.raises(ValidationError):
            PageSnapshot(url="https://example.com")  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            PageSnapshot(title="Example")  # type: ignore[call-arg]

    def test_notes_list(self) -> None:
        snap = PageSnapshot(
            url="https://example.com",
            title="Example",
            notes=["Popup detected", "Loading..."],
        )
        assert len(snap.notes) == 2
        assert "Popup detected" in snap.notes
