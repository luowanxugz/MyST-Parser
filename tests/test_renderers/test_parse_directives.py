import json
from pathlib import Path

import pytest
import yaml
from docutils.parsers.rst.directives.admonitions import Admonition, Note
from docutils.parsers.rst.directives.body import Rubric
from markdown_it import MarkdownIt
from sphinx.directives.code import CodeBlock

from myst_parser.parsers.directives import MarkupError, parse_directive_text
from myst_parser.parsers.options import TokenizeError, options_to_items

FIXTURE_PATH = Path(__file__).parent.joinpath("fixtures")


@pytest.mark.param_file(FIXTURE_PATH / "option_parsing.yaml", "yaml")
def test_option_parsing(file_params):
    """Test parsing of directive options."""
    result, state = options_to_items(file_params.content)
    file_params.assert_expected(
        json.dumps(
            {"dict": result, "comments": state.has_comments},
            ensure_ascii=False,
            indent=2,
        ),
        rstrip_lines=True,
    )


@pytest.mark.param_file(FIXTURE_PATH / "option_parsing_errors.yaml", "yaml")
def test_option_parsing_errors(file_params):
    """Test parsing of directive options."""
    try:
        options_to_items(file_params.content)
    except TokenizeError as err:
        result = str(err)
    else:
        result = "No error"
    file_params.assert_expected(result, rstrip_lines=True)


@pytest.mark.param_file(FIXTURE_PATH / "directive_parsing.txt")
def test_parsing(file_params):
    """Test parsing of directive text."""
    tokens = MarkdownIt("commonmark").parse(file_params.content)
    assert len(tokens) == 1 and tokens[0].type == "fence"
    name, *first_line = tokens[0].info.split(maxsplit=1)
    if name == "{note}":
        klass = Note
    elif name == "{admonition}":
        klass = Admonition
    elif name == "{code-block}":
        klass = CodeBlock
    else:
        raise AssertionError(f"Unknown directive: {name}")
    try:
        result = parse_directive_text(
            klass, first_line[0] if first_line else "", tokens[0].content, line=0
        )
    except MarkupError as err:
        outcome = f"error: {err}"
    else:
        outcome = yaml.safe_dump(
            {
                "arguments": result.arguments,
                "options": result.options,
                "body": result.body,
                "content_offset": result.body_offset,
                "warnings": [repr(w) for w in result.warnings],
            },
            sort_keys=True,
        )
    file_params.assert_expected(outcome, rstrip_lines=True)


@pytest.mark.parametrize(
    "descript,klass,arguments,content", [("no content", Rubric, "", "a")]
)
def test_parsing_errors(descript, klass, arguments, content):
    with pytest.raises(MarkupError):
        parse_directive_text(klass, arguments, content)


def test_parsing_full_yaml():
    result = parse_directive_text(
        Note, "", "---\na: [1]\n---\ncontent", validate_options=False
    )
    assert not result.warnings
    assert result.options == {"a": [1]}
    assert result.body == ["content"]


def test_additional_options():
    """Allow additional options to be passed to a directive."""
    # this should be fine
    result = parse_directive_text(
        Note, "", "content", additional_options={"class": "bar"}
    )
    assert not result.warnings
    assert result.options == {"class": ["bar"]}
    assert result.body == ["content"]
    # body on first line should also be fine
    result = parse_directive_text(
        Note, "content", "other", additional_options={"class": "bar"}
    )
    assert not result.warnings
    assert result.options == {"class": ["bar"]}
    assert result.body == ["content", "other"]
    # additional option should not take precedence
    result = parse_directive_text(
        Note, "content", ":class: foo", additional_options={"class": "bar"}
    )
    assert not result.warnings
    assert result.options == {"class": ["foo"]}
    assert result.body == ["content"]
    # this should warn about the unknown option
    result = parse_directive_text(
        Note, "", "content", additional_options={"foo": "bar"}
    )
    assert len(result.warnings) == 1
    assert "Unknown option" in result.warnings[0].msg


def test_colon_options_stop_at_colon_fence():
    """Options parsing should stop when encountering a colon fence (3+ colons)."""
    result = parse_directive_text(Note, "", ":class: xxx\n::::{other}\ncontent\n::::")
    assert result.options == {"class": ["xxx"]}
    assert result.body == ["::::{other}", "content", "::::"]


# =============================================================================
#  Colon-fence option parsing boundary condition tests
# =============================================================================


def test_colon_option_with_colons_in_value():
    """Option values containing colons should be preserved intact."""
    result = parse_directive_text(Note, "", ":key: value:with:colons\ncontent")
    assert result.options == {"key": "value:with:colons"}
    assert result.body == ["content"]


def test_colon_option_empty_values():
    """Empty option values (``:key:`` and ``:key: ``) should be parsed correctly."""
    result = parse_directive_text(Note, "", ":class:\n:name: \ncontent")
    assert result.options == {"class": "", "name": ""}
    assert result.body == ["content"]


def test_colon_option_stop_at_triple_colon_fence():
    """``:::`` and ``::::`` (3+ consecutive colons) should stop option parsing."""
    result = parse_directive_text(Note, "", ":class: outer\n:::note\nbody\n:::")
    assert result.options == {"class": ["outer"]}
    assert result.body == [":::note", "body", ":::"]


def test_colon_option_stop_at_triple_colon_only():
    """A line containing only ``:::`` should stop option parsing."""
    result = parse_directive_text(Note, "", ":class: xxx\n:::\nfenced\n:::")
    assert result.options == {"class": ["xxx"]}
    assert result.body == [":::", "fenced", ":::"]


def test_colon_option_nested_fence_with_attributes():
    """``:::{directive}{option: value}`` style fence should stop option parsing."""
    result = parse_directive_text(
        Note, "", ":class: outer\n:::{note}{option: value}\ncontent\n:::"
    )
    assert result.options == {"class": ["outer"]}
    assert result.body == [":::{note}{option: value}", "content", ":::"]


def test_colon_option_stops_at_double_colon_prefix():
    """``::xxx`` (double-colon prefix, not a fence) should stop option parsing.

    This guards against greedy absorption of lines like ``::my-marker`` which are
    not valid ``:key: value`` option lines.
    """
    result = parse_directive_text(
        Note, "", ":class: outer\n::not-an-option-line\ncontent"
    )
    assert result.options == {"class": ["outer"]}
    assert result.body == ["::not-an-option-line", "content"]


def test_colon_option_leading_blank_lines():
    """Leading blank lines in content (e.g. from ``render_colon_fence`` insertion)
    should be skipped so that subsequent ``:option:`` lines are still parsed.
    """
    result = parse_directive_text(Note, "", "\n\n:class: outer\ncontent")
    assert result.options == {"class": ["outer"]}
    assert result.body == ["content"]


def test_colon_option_indented_lines():
    """Indented option lines should be recognised and parsed correctly."""
    result = parse_directive_text(
        Note, "", "  :class: outer\n  :name: test\ncontent"
    )
    assert result.options == {"class": ["outer"], "name": "test"}
    assert result.body == ["content"]


def test_colon_option_content_starting_with_fence():
    """If the first non-blank content is already a fence, there is no option block."""
    result = parse_directive_text(Note, "", ":::note\n:class: inner\nbody\n:::")
    assert result.options == {}
    assert result.body == [":::note", ":class: inner", "body", ":::"]


def test_colon_option_single_option_followed_by_body():
    """A single option line followed by regular body content."""
    result = parse_directive_text(Note, "", ":class: important\nThis is body text.")
    assert result.options == {"class": ["important"]}
    assert result.body == ["This is body text."]


def test_colon_option_multiple_options():
    """Multiple ``:key: value`` lines should all be parsed as options."""
    result = parse_directive_text(
        Note, "", ":class: one\n:name: two\n:align: center\nbody"
    )
    assert result.options == {"class": ["one"], "name": "two", "align": ["center"]}
    assert result.body == ["body"]


def test_colon_option_four_colon_fence_still_stops():
    """``::::`` (4 colons) should also be detected as a colon fence and stop parsing."""
    result = parse_directive_text(
        Note, "", ":class: outer\n::::{admonition} title\ninner\n::::"
    )
    assert result.options == {"class": ["outer"]}
    assert result.body == ["::::{admonition} title", "inner", "::::"]


def test_colon_option_five_or_more_colons():
    """5+ consecutive colons (e.g. ``:::::``) should also be treated as a fence."""
    result = parse_directive_text(
        Note, "", ":class: outer\n:::::\nfenced\n:::::"
    )
    assert result.options == {"class": ["outer"]}
    assert result.body == [":::::", "fenced", ":::::"]


def test_colon_option_stop_at_non_colon_line():
    """Any line not starting with ``:`` must stop option parsing."""
    result = parse_directive_text(Note, "", ":class: one\nplain text\n:ignored: two")
    assert result.options == {"class": ["one"]}
    assert result.body == ["plain text", ":ignored: two"]


def test_colon_option_no_options_block():
    """Content not starting with ``:`` should not produce an options block."""
    result = parse_directive_text(Note, "", "just body content\nmore body")
    assert result.options == {}
    assert result.body == ["just body content", "more body"]


def test_colon_option_full_yaml_mode():
    """Full-YAML mode should still work alongside colon-option parsing."""
    result = parse_directive_text(
        Note, "", "---\nclass: foo\nname: bar\n---\nbody",
        validate_options=False,
    )
    assert not result.warnings
    assert result.options == {"class": "foo", "name": "bar"}
    assert result.body == ["body"]


def test_colon_option_fence_after_options_with_additional_options():
    """``additional_options`` should still be applied when content contains a fence."""
    result = parse_directive_text(
        Note,
        "",
        ":class: outer\n::::note\ninner\n::::",
        additional_options={"name": "test"},
    )
    assert result.options == {"class": ["outer"], "name": "test"}
    assert result.body == ["::::note", "inner", "::::"]
