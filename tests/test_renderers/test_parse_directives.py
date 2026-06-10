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


class TestColonFenceBoundaryConditions:
    """Boundary condition tests for stopping directive-option parsing at colon fences."""

    def test_content_starts_with_colon_fence_no_options(self):
        """Content starting with ::: should NOT enter option parsing block."""
        result = parse_directive_text(Note, "", ":::{warning}\ninner\n:::")
        assert result.options == {}
        assert result.body == [":::{warning}", "inner", ":::"]
        assert result.body_offset == 0

    def test_content_starts_with_four_colon_fence(self):
        """Content starting with :::: should NOT enter option parsing block."""
        result = parse_directive_text(Note, "", "::::{important}\ninner\n::::")
        assert result.options == {}
        assert result.body == ["::::{important}", "inner", "::::"]
        assert result.body_offset == 0

    def test_double_colon_line_stops_option_parsing(self):
        """Lines starting with :: (2 colons) should stop option parsing.

        A valid option line starts with exactly one colon.
        :: is never a valid option prefix.
        """
        result = parse_directive_text(Note, "", ":class: xxx\n::not-an-option\nbody")
        assert result.options == {"class": ["xxx"]}
        assert result.body == ["::not-an-option", "body"]

    def test_option_then_nested_colon_fence(self):
        """Options followed by a nested colon fence directive."""
        result = parse_directive_text(
            Note, "", ":class: tip\n::::{important}\ninner\n::::"
        )
        assert result.options == {"class": ["tip"]}
        assert result.body == ["::::{important}", "inner", "::::"]

    def test_option_then_three_colon_fence(self):
        """Options followed by a ::: fence (minimum fence length)."""
        result = parse_directive_text(
            Note, "", ":class: tip\n:::{warning}\ninner\n:::"
        )
        assert result.options == {"class": ["tip"]}
        assert result.body == [":::{warning}", "inner", ":::"]

    def test_multiple_options_then_nested_fence(self):
        """Multiple options followed by a nested colon fence."""
        result = parse_directive_text(
            Note, "", ":class: tip\n:name: mynote\n::::{important}\ninner\n::::"
        )
        assert result.options == {"class": ["tip"], "name": ["mynote"]}
        assert result.body == ["::::{important}", "inner", "::::"]

    def test_closing_fence_only_in_body(self):
        """A closing fence ::: alone should not be parsed as an option."""
        result = parse_directive_text(Note, "", ":class: tip\nbody\n:::")
        assert result.options == {"class": ["tip"]}
        assert result.body == ["body", ":::"]

    def test_option_value_with_colons(self):
        """Option value containing :: should not be mistaken for a fence."""
        result = parse_directive_text(Note, "", ":class: ::special\nbody")
        assert result.options == {"class": ["::special"]}
        assert result.body == ["body"]

    def test_option_value_with_three_colons(self):
        """Option value containing ::: should not be mistaken for a fence."""
        result = parse_directive_text(Note, "", ":name: :::triple\nbody")
        assert result.options == {"name": [":::triple"]}
        assert result.body == ["body"]

    def test_empty_option_value(self):
        """Option with empty value should parse correctly."""
        result = parse_directive_text(Note, "", ":class:\nbody")
        assert result.options == {"class": []}
        assert result.body == ["body"]

    def test_flag_option_no_value(self):
        """Flag option (no value) with CodeBlock directive."""
        result = parse_directive_text(CodeBlock, "", ":linenos:\nbody")
        assert result.options == {"linenos": None}
        assert result.body == ["body"]

    def test_indented_option_then_colon_fence(self):
        """Indented option lines followed by a colon fence."""
        result = parse_directive_text(
            Note, "", "  :class: tip\n  :::{warning}\n  inner\n  :::"
        )
        assert result.options == {"class": ["tip"]}
        assert result.body == ["  :::{warning}", "  inner", "  :::"]

    def test_indented_colon_fence_no_options(self):
        """Indented content starting with ::: should not enter option parsing."""
        result = parse_directive_text(Note, "", "  :::{warning}\n  inner\n  :::")
        assert result.options == {}
        assert result.body == ["  :::{warning}", "  inner", "  :::"]

    def test_option_with_blank_line_then_fence(self):
        """Options, blank line, then colon fence - blank line stops options."""
        result = parse_directive_text(
            Note, "", ":class: tip\n\n::::{important}\ninner\n::::"
        )
        assert result.options == {"class": ["tip"]}
        assert result.body == ["::::{important}", "inner", "::::"]

    def test_no_option_spec_with_colon_fence_content(self):
        """Directive with no option_spec should not attempt option parsing."""
        result = parse_directive_text(Admonition, "title", ":::{note}\ninner\n:::")
        assert result.options == {}
        assert result.arguments == ["title"]
        assert result.body == [":::{note}", "inner", ":::"]

    def test_yaml_block_option_not_affected(self):
        """YAML block (---) options should not be affected by colon fence fix."""
        result = parse_directive_text(
            Note, "", "---\nclass: tip\n---\n::::{important}\ninner\n::::"
        )
        assert result.options == {"class": ["tip"]}
        assert result.body == ["::::{important}", "inner", "::::"]

    def test_deeply_nested_colon_fences(self):
        """Multiple levels of nested colon fences in body."""
        result = parse_directive_text(
            Note,
            "",
            ":class: tip\n:::::{important}\n::::{warning}\n:::{note}\ndeep\n:::\n::::\n:::::",
        )
        assert result.options == {"class": ["tip"]}
        assert result.body == [
            ":::::{important}",
            "::::{warning}",
            ":::{note}",
            "deep",
            ":::",
            "::::",
            ":::::",
        ]

    def test_colon_fence_with_arguments(self):
        """Colon fence with arguments after directive name."""
        result = parse_directive_text(
            Note, "", ":class: tip\n::::{admonition} My Title\ninner\n::::"
        )
        assert result.options == {"class": ["tip"]}
        assert result.body == ["::::{admonition} My Title", "inner", "::::"]

    def test_has_options_block_false_when_no_options(self):
        """has_options_block should be False when content starts with colon fence."""
        result = parse_directive_text(Note, "", ":::{warning}\ninner\n:::")
        assert result.body_offset == 0

    def test_first_line_body_with_colon_fence_content(self):
        """First line as body + colon fence content, no options block."""
        result = parse_directive_text(
            Note, "first line", ":::{warning}\ninner\n:::"
        )
        assert result.options == {}
        assert result.body == ["first line", ":::{warning}", "inner", ":::"]

