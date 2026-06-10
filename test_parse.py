import sys
from myst_parser.parsers.directives import parse_directive_text
from docutils.parsers.rst.directives.admonitions import Note

content = """:class: xxx
:::[directive]{option: value}
content
:::"""
print(parse_directive_text(Note, "", content))
