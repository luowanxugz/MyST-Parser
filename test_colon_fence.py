from docutils.parsers.rst.directives.admonitions import Note
from myst_parser.parsers.directives import parse_directive_text

# 测试1: 当前测试用例 - 嵌套指令 fence
result = parse_directive_text(Note, '', ':class: xxx\n::::{other}\ncontent\n::::')
print('Test 1 (nested fence):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试2: 选项中含冒号的情况
result = parse_directive_text(Note, '', ':class: xxx\n:name: test:value')
print('Test 2 (option value with colon):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试3: 仅冒号前缀的 fence 如 ::::note
result = parse_directive_text(Note, '', ':class: xxx\n::::note\ncontent\n::::')
print('Test 3 (colon fence directive):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试4: 空选项
result = parse_directive_text(Note, '', ':class:\n:name: \ncontent')
print('Test 4 (empty options):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试5: 三个冒号的边界情况
result = parse_directive_text(Note, '', ':class: xxx\n:::note\ncontent\n:::')
print('Test 5 (3-colon fence):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试6: 检查精确的 3+ 冒号后跟非冒号字符
result = parse_directive_text(Note, '', ':class: xxx\n:::not_a_fence\ncontent')
print('Test 6 (3 colons + text, no fence):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试7: 多缩进的选项
result = parse_directive_text(Note, '', '  :class: xxx\n  :name: test\ncontent')
print('Test 7 (indented options):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试8: 只有冒号和空白的行
result = parse_directive_text(Note, '', ':class: xxx\n:::\ncontent\n:::')
print('Test 8 (3 colons only):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试9: 两个冒号的行 - 不应停止
result = parse_directive_text(Note, '', ':class: xxx\n::key: value\ncontent')
print('Test 9 (2 colons prefix):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试10: 混合 fence 和选项
result = parse_directive_text(Note, '', ':class: outer\n::::{note}\n:class: inner\ncontent\n::::')
print('Test 10 (mixed nested directive):')
print('  options:', result.options)
print('  body:', result.body)
print()

# 测试11: YAML fence 场景
result = parse_directive_text(Note, '', '---\nclass: xxx\n---\ncontent')
print('Test 11 (YAML options):')
print('  options:', result.options)
print('  body:', result.body)
