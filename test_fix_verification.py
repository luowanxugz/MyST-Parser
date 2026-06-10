"""Standalone test for the colon-fence option parsing fix."""
import re
from typing import Final

# Copy of the fixed regex and parsing logic
_COLON_FENCE_RE: Final[re.Pattern[str]] = re.compile(r"^:{3,}")


def parse_colon_options(content):
    """Simulates the fixed colon-option parsing from _parse_directive_options."""
    if not content.lstrip().startswith(":"):
        return (None, content)

    content_lines = content.splitlines()
    yaml_lines = []

    # Skip leading blank lines
    while content_lines and not content_lines[0].strip():
        content_lines.pop(0)

    while content_lines:
        stripped = content_lines[0].lstrip()

        # Stop at colon fence (3+ consecutive colons)
        if _COLON_FENCE_RE.match(stripped):
            break

        # Stop at lines that don't start with a colon
        if not stripped.startswith(":"):
            break

        # Stop at double-colon prefix (::xxx) which is not a valid option line
        if stripped.startswith("::"):
            break

        yaml_lines.append(content_lines.pop(0).lstrip()[1:])

    options_block = "\n".join(yaml_lines)
    remaining_content = "\n".join(content_lines)
    return (options_block, remaining_content)


def assert_eq(actual, expected, msg=""):
    if actual != expected:
        raise AssertionError(f"{msg}\n  Expected: {expected!r}\n  Got:      {actual!r}")
    print(f"  PASS: {msg}")


def test(name, content, expected_options, expected_body):
    options, body = parse_colon_options(content)
    print(f"\n[{name}]")
    print(f"  Input: {content!r}")
    assert_eq(options, expected_options, "options_block")
    assert_eq(body, expected_body, "body")


# ---------------------------------------------------------------------------
# Run all tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # 1. Basic nested fence
    test(
        "Basic nested fence",
        ":class: xxx\n::::{other}\ncontent\n::::",
        "class: xxx",
        "::::{other}\ncontent\n::::",
    )

    # 2. Option value with colons
    test(
        "Option value with colons",
        ":key: value:with:colons\ncontent",
        "key: value:with:colons",
        "content",
    )

    # 3. Triple-colon fence
    test(
        "Triple-colon fence stops parsing",
        ":class: outer\n:::note\nbody\n:::",
        "class: outer",
        ":::note\nbody\n:::",
    )

    # 4. Bare fence line
    test(
        "Bare fence line (::: only)",
        ":class: xxx\n:::\nfenced\n:::",
        "class: xxx",
        ":::\nfenced\n:::",
    )

    # 5. Fence with attributes
    test(
        "Fence with {directive}{option: value}",
        ":class: outer\n:::{note}{option: value}\ncontent\n:::",
        "class: outer",
        ":::{note}{option: value}\ncontent\n:::",
    )

    # 6. Double-colon prefix stops parsing (anti-greedy)
    test(
        "Double-colon prefix stops parsing",
        ":class: outer\n::not-an-option-line\ncontent",
        "class: outer",
        "::not-an-option-line\ncontent",
    )

    # 7. Leading blank lines (from render_colon_fence insertion)
    test(
        "Leading blank lines skipped",
        "\n\n:class: outer\ncontent",
        "class: outer",
        "content",
    )

    # 8. Indented option lines
    test(
        "Indented option lines",
        "  :class: outer\n  :name: test\ncontent",
        "class: outer\nname: test",
        "content",
    )

    # 9. Content starts with fence (no options)
    test(
        "Content starts with fence",
        ":::note\n:class: inner\nbody\n:::",
        "",
        ":::note\n:class: inner\nbody\n:::",
    )

    # 10. Single option + body
    test(
        "Single option + body",
        ":class: important\nThis is body text.",
        "class: important",
        "This is body text.",
    )

    # 11. Multiple options
    test(
        "Multiple options",
        ":class: one\n:name: two\n:align: center\nbody",
        "class: one\nname: two\nalign: center",
        "body",
    )

    # 12. 4-colon fence
    test(
        "4-colon fence",
        ":class: outer\n::::{admonition} title\ninner\n::::",
        "class: outer",
        "::::{admonition} title\ninner\n::::",
    )

    # 13. 5+ colon fence
    test(
        "5+ colon fence",
        ":class: outer\n:::::\nfenced\n:::::",
        "class: outer",
        ":::::\nfenced\n:::::",
    )

    # 14. Non-colon line stops parsing
    test(
        "Non-colon line stops parsing",
        ":class: one\nplain text\n:ignored: two",
        "class: one",
        "plain text\n:ignored: two",
    )

    # 15. No options block (content doesn't start with colon)
    test(
        "No options block",
        "just body content\nmore body",
        None,
        "just body content\nmore body",
    )

    # 16. Empty option values
    test(
        "Empty option values",
        ":class:\n:name: \ncontent",
        "class:\nname: ",
        "content",
    )

    # 17. Options then fence with leading newline (from render_colon_fence)
    test(
        "Leading newline + fence",
        "\n:::{subnote}\n:class: inner\ncontent\n:::",
        "",
        ":::{subnote}\n:class: inner\ncontent\n:::",
    )

    print("\n" + "=" * 60)
    print("All tests passed!")
    print("=" * 60)
