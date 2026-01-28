"""Tests for safety checks module."""

from browser_agent.tools.safety import is_destructive_action


class TestIsDestructiveAction:
    def test_destructive_delete(self) -> None:
        assert is_destructive_action("delete account") is True

    def test_destructive_remove(self) -> None:
        assert is_destructive_action("remove item") is True

    def test_destructive_submit(self) -> None:
        assert is_destructive_action("submit form") is True

    def test_destructive_payment(self) -> None:
        assert is_destructive_action("payment process") is True

    def test_destructive_checkout(self) -> None:
        assert is_destructive_action("checkout now") is True

    def test_destructive_confirm(self) -> None:
        assert is_destructive_action("confirm order") is True

    def test_destructive_purchase(self) -> None:
        assert is_destructive_action("purchase item") is True

    def test_destructive_buy(self) -> None:
        assert is_destructive_action("buy now") is True

    def test_destructive_order(self) -> None:
        assert is_destructive_action("order placed") is True

    def test_destructive_spam(self) -> None:
        assert is_destructive_action("spam report") is True

    def test_safe_click_search(self) -> None:
        assert is_destructive_action("click search") is False

    def test_safe_navigate(self) -> None:
        assert is_destructive_action("navigate home") is False

    def test_safe_link(self) -> None:
        assert is_destructive_action("link Learn more") is False

    def test_safe_textbox(self) -> None:
        assert is_destructive_action("textbox Username") is False

    def test_case_insensitive(self) -> None:
        assert is_destructive_action("DELETE Account") is True
        assert is_destructive_action("Delete Account") is True

    def test_empty_string(self) -> None:
        assert is_destructive_action("") is False

    def test_keyword_must_be_whole_word(self) -> None:
        # "ordering" contains "order" but split by whitespace means "ordering" != "order"
        assert is_destructive_action("ordering system") is False
        # But "order" as standalone word is destructive
        assert is_destructive_action("order system") is True
