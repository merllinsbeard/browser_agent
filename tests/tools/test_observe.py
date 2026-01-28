"""Tests for ARIA snapshot parsing in observe module."""

import yaml  # type: ignore[import-untyped]

from browser_agent.tools.observe import _extract_interactive_elements, _traverse_aria_tree


# Real ARIA snapshot from example.com (Playwright output)
EXAMPLE_COM_ARIA = """\
- heading "Example Domain" [level=1]
- paragraph: This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.
- paragraph:
  - link "More information..."
"""

# A more complex snapshot with multiple interactive elements
COMPLEX_ARIA = """\
- banner:
  - navigation "Main":
    - link "Home"
    - link "About"
    - link "Contact"
- main:
  - heading "Welcome" [level=1]
  - textbox "Search"
  - button "Go"
  - checkbox "Remember me"
  - link "Forgot password?"
"""

# Snapshot with nested structure
NESTED_ARIA = """\
- dialog "Login":
  - textbox "Username"
  - textbox "Password"
  - button "Sign in"
  - link "Reset password"
"""


class TestTraverseAriaTree:
    def test_basic_string_items(self) -> None:
        parsed = yaml.safe_load(EXAMPLE_COM_ARIA)
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(parsed, elements)
        roles = [e["role"] for e in elements]
        assert "link" in roles

    def test_skips_text_role(self) -> None:
        parsed = yaml.safe_load(EXAMPLE_COM_ARIA)
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(parsed, elements)
        roles = [e["role"] for e in elements]
        assert "text" not in roles

    def test_complex_snapshot_element_count(self) -> None:
        parsed = yaml.safe_load(COMPLEX_ARIA)
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(parsed, elements)
        # Expected: Home, About, Contact (links), Search (textbox), Go (button),
        # Remember me (checkbox), Forgot password? (link), navigation, main, banner
        roles = [e["role"] for e in elements]
        assert roles.count("link") == 4  # Home, About, Contact, Forgot password?
        assert roles.count("button") == 1  # Go
        assert roles.count("textbox") == 1  # Search
        assert roles.count("checkbox") == 1  # Remember me

    def test_nested_dialog(self) -> None:
        parsed = yaml.safe_load(NESTED_ARIA)
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(parsed, elements)
        roles = [e["role"] for e in elements]
        assert "dialog" in roles
        assert roles.count("textbox") == 2  # Username, Password
        assert roles.count("button") == 1  # Sign in
        assert roles.count("link") == 1  # Reset password

    def test_extracts_names(self) -> None:
        parsed = yaml.safe_load(NESTED_ARIA)
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(parsed, elements)
        names = [e["name"] for e in elements]
        assert "Username" in names
        assert "Password" in names
        assert "Sign in" in names

    def test_skips_metadata_keys(self) -> None:
        # Simulate a snapshot with /url metadata
        data = yaml.safe_load('- link "Test"')
        # Wrap in a dict with /url key
        wrapped = {"/url": "https://example.com", "main": data}
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(wrapped, elements)
        names = [e.get("name") for e in elements]
        # Should find "Test" link but not process /url
        assert "Test" in names

    def test_empty_yaml_returns_empty(self) -> None:
        parsed = yaml.safe_load("")
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(parsed, elements)
        assert elements == []

    def test_none_input(self) -> None:
        elements: list[dict] = []  # type: ignore[type-arg]
        _traverse_aria_tree(None, elements)
        assert elements == []


class TestExtractInteractiveElements:
    def test_example_com(self) -> None:
        elements = _extract_interactive_elements(EXAMPLE_COM_ARIA, max_elements=60)
        assert len(elements) >= 1
        link_elem = next(e for e in elements if e.role == "link")
        assert "More information" in link_elem.name

    def test_complex_snapshot(self) -> None:
        elements = _extract_interactive_elements(COMPLEX_ARIA, max_elements=60)
        roles = [e.role for e in elements]
        assert "button" in roles
        assert "textbox" in roles
        assert "link" in roles

    def test_max_elements_limit(self) -> None:
        elements = _extract_interactive_elements(COMPLEX_ARIA, max_elements=2)
        assert len(elements) <= 2

    def test_elements_have_refs(self) -> None:
        elements = _extract_interactive_elements(COMPLEX_ARIA, max_elements=60)
        refs = [e.ref for e in elements]
        for i, ref in enumerate(refs):
            assert ref == f"elem-{i}"

    def test_sorted_by_priority(self) -> None:
        elements = _extract_interactive_elements(COMPLEX_ARIA, max_elements=60)
        # Buttons (priority 10) should come before navigation (priority 1)
        if len(elements) >= 2:
            button_idx = next(
                (i for i, e in enumerate(elements) if e.role == "button"), None
            )
            nav_idx = next(
                (i for i, e in enumerate(elements) if e.role == "navigation"), None
            )
            if button_idx is not None and nav_idx is not None:
                assert button_idx < nav_idx

    def test_invalid_yaml_returns_empty(self) -> None:
        elements = _extract_interactive_elements(":::invalid yaml{{[", max_elements=60)
        assert elements == []

    def test_bbox_is_none(self) -> None:
        elements = _extract_interactive_elements(EXAMPLE_COM_ARIA, max_elements=60)
        for elem in elements:
            assert elem.bbox is None
