"""Fenced code blocks are parsed as directives,
if the block starts with ``{directive_name}``,
followed by arguments on the same line.

Directive options are read from a YAML block,
if the first content line starts with ``---``, e.g.

::

    ```{directive_name} arguments
    ---
    option1: name
    option2: |
        Longer text block
    ---
    content...
    ```

Or the option block will be parsed if the first content line starts with ``:``,
as a YAML block consisting of every line that starts with a ``:``, e.g.

::

    ```{directive_name} arguments
    :option1: name
    :option2: other

    content...
    ```

If the first line of a directive's content is blank, this will be stripped
from the content.
This is to allow for separation between the option block and content.

"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from textwrap import dedent
from typing import Any

import yaml
from docutils.parsers.rst import Directive
from docutils.parsers.rst.directives import flag
from docutils.parsers.rst.directives.misc import TestDirective
from docutils.parsers.rst.states import MarkupError

from myst_parser.warnings_ import MystWarnings

from .options import Position, TokenizeError, options_to_items


@dataclass
class ParseWarnings:
    msg: str
    lineno: int | None = None
    type: MystWarnings = MystWarnings.DIRECTIVE_PARSING


@dataclass
class DirectiveParsingResult:
    arguments: list[str]
    """The arguments parsed from the first line."""
    options: dict
    """Options parsed from the YAML block."""
    body: list[str]
    """The lines of body content"""
    body_offset: int
    """The number of lines to the start of the body content."""
    warnings: list[ParseWarnings]
    """List of non-fatal errors encountered during parsing.
    (message, line_number)
    """


def parse_directive_text(
    directive_class: type[Directive],
    first_line: str,
    content: str,
    *,
    line: int | None = None,
    validate_options: bool = True,
    additional_options: dict[str, str] | None = None,
) -> DirectiveParsingResult:
    """Parse (and validate) the full directive text.

    :param first_line: The text on the same line as the directive name.
        May be an argument or body text, dependent on the directive
    :param content: All text after the first line. Can include options.
    :param validate_options: Whether to validate the values of options
        This is actually only here to be used by myst-nb cells,
        which converts options directly to JSON metadata, using the full YAML spec.
    :param additional_options: Additional options to add to the directive,
        above those parsed from the content (content options take priority).

    :raises MarkupError: if there is a fatal parsing/validation error
    """
    parse_warnings: list[ParseWarnings]
    options: dict[str, Any]
    body_lines: list[str]
    content_offset: int
    has_options_block: bool

    if directive_class.option_spec:
        # only look for an option block if there are possible options
        # body, options, option_errors = _parse_directive_options(
        result = _parse_directive_options(
            content,
            directive_class,
            line=line,
            as_yaml=not validate_options,
            additional_options=additional_options,
        )
        parse_warnings = result.warnings
        has_options_block = result.has_options
        options = result.options
        body_lines = result.content.splitlines()
        content_offset = len(content.splitlines()) - len(body_lines)
    else:
        parse_warnings = []
        has_options_block = False
        options = {}
        body_lines = content.splitlines()
        content_offset = 0

    if not (directive_class.required_arguments or directive_class.optional_arguments):
        # If there are no possible arguments, then the body can start on the argument line
        if first_line.strip():
            if has_options_block and any(body_lines):
                parse_warnings.append(
                    ParseWarnings(
                        "Splitting content across first line and body, "
                        "when an options block is present, is not recommended"
                    )
                )
            body_lines.insert(0, first_line)
            content_offset = 0
        arguments = []
    else:
        arguments = parse_directive_arguments(directive_class, first_line)

    # remove first line of body if blank
    # this is to allow space between the options and the content
    if body_lines and not body_lines[0].strip():
        body_lines = body_lines[1:]
        content_offset += 1

    # check for body content
    if body_lines and not directive_class.has_content:
        parse_warnings.append(ParseWarnings("Has content, but none permitted"))

    return DirectiveParsingResult(
        arguments, options, body_lines, content_offset, parse_warnings
    )


@dataclass
class _DirectiveOptions:
    content: str
    options: dict[str, Any]
    warnings: list[ParseWarnings]
    has_options: bool


def _parse_directive_options(
    content: str,
    directive_class: type[Directive],
    as_yaml: bool,
    line: int | None,
    additional_options: dict[str, str] | None = None,
) -> _DirectiveOptions:
    """Parse (and validate) the directive option section.

    Supports both YAML-style options and inline key=value syntax with quoted values.
    
    Examples of supported syntax:
        :name: value
        :class: "my class with spaces"
        :class: 'my class with spaces'
        :name: 'value with "quotes" inside'
    
    :returns: (content, options, validation_errors)
    """
    options_block: None | str = None
    if content.startswith("---"):
        line = None if line is None else line + 1
        content = "\n".join(content.splitlines()[1:])
        match = re.search(r"^-{3,}", content, re.MULTILINE)
        if match:
            options_block = content[: match.start()]
            content = content[match.end() + 1 :]  # TODO advance line number
        else:
            options_block = content
            content = ""
        options_block = dedent(options_block)
    elif content.lstrip().startswith(":"):
        content_lines = content.splitlines()
        yaml_lines = []
        while content_lines:
            stripped = content_lines[0].lstrip()
            # Stop at lines that don't start with a colon or have 3+ colons, which are colon fences
            # (e.g. nested directives like `::::{other}`)
            if not stripped.startswith(":") or stripped.startswith(":::"):
                break
            yaml_lines.append(content_lines.pop(0).lstrip()[1:])
        options_block = "\n".join(yaml_lines)
        content = "\n".join(content_lines)

    has_options_block = options_block is not None

    if as_yaml:
        yaml_errors: list[ParseWarnings] = []
        try:
            yaml_options = yaml.safe_load(options_block or "") or {}
        except (yaml.parser.ParserError, yaml.scanner.ScannerError):
            yaml_options = {}
            yaml_errors.append(
                ParseWarnings(
                    "Invalid options format (bad YAML)",
                    line,
                    MystWarnings.DIRECTIVE_OPTION,
                )
            )
        if not isinstance(yaml_options, dict):
            yaml_options = {}
            yaml_errors.append(
                ParseWarnings(
                    "Invalid options format (not a dict)",
                    line,
                    MystWarnings.DIRECTIVE_OPTION,
                )
            )
        return _DirectiveOptions(content, yaml_options, yaml_errors, has_options_block)

    validation_errors: list[ParseWarnings] = []

    options: dict[str, str] = {}
    if options_block is not None:
        try:
            options = _parse_options_block(options_block)
        except TokenizeError as err:
            return _DirectiveOptions(
                content,
                options,
                [
                    ParseWarnings(
                        f"Invalid options format: {err.problem}",
                        line,
                        MystWarnings.DIRECTIVE_OPTION,
                    )
                ],
                has_options_block,
            )

    if issubclass(directive_class, TestDirective):
        # technically this directive spec only accepts one option ('option')
        # but since its for testing only we accept all options
        return _DirectiveOptions(content, options, [], has_options_block)

    if additional_options:
        # The options block takes priority over additional options
        options = {**additional_options, **options}

    # check options against spec
    options_spec: dict[str, Callable] = directive_class.option_spec
    unknown_options: list[str] = []
    new_options: dict[str, Any] = {}
    value: str | None
    for name, value in options.items():
        try:
            converter = options_spec[name]
        except KeyError:
            unknown_options.append(name)
            continue
        if not value:
            # restructured text parses empty option values as None
            value = None
        if converter is flag:
            # flag will error if value is not empty,
            # but to be more permissive we allow any value
            value = None
        try:
            converted_value = converter(value)
        except (ValueError, TypeError) as error:
            validation_errors.append(
                ParseWarnings(
                    f"Invalid option value for {name!r}: {value}: {error}",
                    line,
                    MystWarnings.DIRECTIVE_OPTION,
                )
            )
        else:
            new_options[name] = converted_value

    if unknown_options:
        validation_errors.append(
            ParseWarnings(
                f"Unknown option keys: {sorted(unknown_options)} "
                f"(allowed: {sorted(options_spec)})",
                line,
                MystWarnings.DIRECTIVE_OPTION,
            )
        )

    return _DirectiveOptions(content, new_options, validation_errors, has_options_block)


def parse_directive_arguments(
    directive_cls: type[Directive], arg_text: str
) -> list[str]:
    """Parse (and validate) the directive argument section."""
    required = directive_cls.required_arguments
    optional = directive_cls.optional_arguments
    arguments = arg_text.split()
    if len(arguments) < required:
        raise MarkupError(f"{required} argument(s) required, {len(arguments)} supplied")
    elif len(arguments) > required + optional:
        if directive_cls.final_argument_whitespace:
            arguments = arg_text.split(None, required + optional - 1)
        else:
            raise MarkupError(
                f"maximum {required + optional} argument(s) allowed, "
                f"{len(arguments)} supplied"
            )
    return arguments


def _parse_options_block(options_block: str) -> dict[str, str]:
    """Parse a directive options block into a structured dict.
    
    Supports both YAML-style colon syntax and inline key=value syntax.
    
    Examples:
        name: value
        class: "my class with spaces"
        class: 'my class with spaces'
        name: 'value with "quotes" inside'
    
    :param options_block: The options block text (without leading colons).
    :returns: A dict of option key-value pairs.
    :raises TokenizeError: If the options block is malformed.
    """
    options: dict[str, str] = {}
    lines = options_block.splitlines()
    
    for line_num, line in enumerate(lines, start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        
        colon_pos = stripped.find(":")
        if colon_pos == -1:
            raise TokenizeError(
                f"Expected ':' in option line: {stripped!r}",
                Position(0, line_num, 0),
            )
        
        key = stripped[:colon_pos].strip()
        value_str = stripped[colon_pos + 1:].strip()
        
        if not key:
            raise TokenizeError(
                f"Empty option key in line: {stripped!r}",
                Position(0, line_num, 0),
            )
        
        value = _parse_option_value(value_str)
        options[key] = value
    
    return options


def _parse_option_value(value_str: str) -> str:
    """Parse an option value, handling quotes properly.
    
    Supports:
        - Unquoted values: value with spaces -> "value with spaces"
        - Double-quoted values: "my class" -> "my class"
        - Single-quoted values: 'my class' -> "my class"
        - Escaped quotes within quoted values
    
    :param value_str: The raw value string after the colon.
    :returns: The parsed value with quotes removed but internal spaces preserved.
    """
    if not value_str:
        return ""
    
    first_char = value_str[0]
    
    if first_char in ('"', "'"):
        quote_char = first_char
        end_pos = _find_closing_quote(value_str, quote_char)
        if end_pos == -1:
            return value_str[1:]
        return value_str[1:end_pos]
    
    return value_str


def _find_closing_quote(s: str, quote_char: str, start: int = 1) -> int:
    """Find the position of the closing quote, handling escape sequences.
    
    :param s: The string to search in.
    :param quote_char: The quote character to match (' or ").
    :param start: The position to start searching from.
    :returns: The position of the closing quote, or -1 if not found.
    """
    i = start
    while i < len(s):
        if s[i] == "\\" and i + 1 < len(s):
            i += 2
            continue
        if s[i] == quote_char:
            return i
        i += 1
    return -1
