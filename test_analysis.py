"""
详细分析 _parse_directive_options 中 colon fence 的解析问题
"""
import re

# 模拟当前的解析逻辑（简化版）
def current_parse_options(content):
    options_block = None
    if content.startswith("---"):
        return ("YAML", content)
    elif content.lstrip().startswith(":"):
        content_lines = content.splitlines()
        yaml_lines = []
        while content_lines:
            stripped = content_lines[0].lstrip()
            # 当前逻辑：不以 : 开头 或 以 ::: 开头 → 停止
            if not stripped.startswith(":") or stripped.startswith(":::"):
                break
            yaml_lines.append(content_lines.pop(0).lstrip()[1:])
        options_block = "\n".join(yaml_lines)
        content = "\n".join(content_lines)
        return (options_block, content)
    return (None, content)


# ============ 测试场景 ============

print("=" * 60)
print("场景 1: 前导空行（render_colon_fence 插入 \\n 导致）")
print("=" * 60)
content1 = "\n:::{subnote}\n:class: inner\ncontent\n:::"
result = current_parse_options(content1)
print(f"输入: {repr(content1)}")
print(f"  content_lines = {content1.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print()

print("=" * 60)
print("场景 2: 正常选项 + 嵌套 fence")
print("=" * 60)
content2 = ":class: outer\n::::{other}\ncontent\n::::"
result = current_parse_options(content2)
print(f"输入: {repr(content2)}")
print(f"  content_lines = {content2.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print()

print("=" * 60)
print("场景 3: 单冒号文本（非选项格式）被贪婪吸收")
print("=" * 60)
content3 = ":class: outer\n:just-text-no-colon-after\ncontent"
result = current_parse_options(content3)
print(f"输入: {repr(content3)}")
print(f"  content_lines = {content3.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print(f"  问题: ':just-text-no-colon-after' 被错误当作选项，")
print(f"        这行格式是 ':text'，缺少第二个冒号（非 :key:value 格式）")
print()

print("=" * 60)
print("场景 4: 双冒号前缀（不是 fence 也不是合法选项）")
print("=" * 60)
content4 = ":class: outer\n::double-colon-text\ncontent"
result = current_parse_options(content4)
print(f"输入: {repr(content4)}")
print(f"  content_lines = {content4.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print(f"  问题: '::double-colon-text' 被当作选项，")
print(f"        处理后变成 ':double-colon-text'（lstrip()[1:]），")
print(f"        YAML 解析会产生 key=':double-colon-text' 的无效键")
print()

print("=" * 60)
print("场景 5: 选项值中包含冒号")
print("=" * 60)
content5 = ":key: value:with:colons\ncontent"
result = current_parse_options(content5)
print(f"输入: {repr(content5)}")
print(f"  content_lines = {content5.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print(f"  这个场景是正确的 - 选项值中的冒号保留")
print()

print("=" * 60)
print("场景 6: 空选项")
print("=" * 60)
content6 = ":class:\n:name: \ncontent"
result = current_parse_options(content6)
print(f"输入: {repr(content6)}")
print(f"  content_lines = {content6.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print()

print("=" * 60)
print("场景 7: 精确 fence 检测 - 3 个冒号后跟花括号")
print("=" * 60)
content7 = ":class: outer\n:::{directive}{option: value}\ncontent"
result = current_parse_options(content7)
print(f"输入: {repr(content7)}")
print(f"  content_lines = {content7.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print(f"  这个当前工作正常 - ::: 开头正确识别为 fence")
print()

print("=" * 60)
print("场景 8: 前导空行 + 真实选项")
print("=" * 60)
content8 = "\n\n:class: outer\ncontent"
result = current_parse_options(content8)
print(f"输入: {repr(content8)}")
print(f"  content_lines = {content8.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print(f"  问题: 前导空行导致 while 循环立即 break，选项未被解析")
print()

print("=" * 60)
print("场景 9: 缩进的选项行")
print("=" * 60)
content9 = "  :class: outer\n  :name: test\ncontent"
result = current_parse_options(content9)
print(f"输入: {repr(content9)}")
print(f"  content_lines = {content9.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print()

print("=" * 60)
print("场景 10: 仅 fence（无选项）")
print("=" * 60)
content10 = ":::note\ncontent\n:::"
result = current_parse_options(content10)
print(f"输入: {repr(content10)}")
print(f"  content_lines = {content10.splitlines()}")
print(f"  options_block = {repr(result[0])}")
print(f"  body content = {repr(result[1])}")
print(f"  这个当前工作正常 - ::: 开头正确识别为 fence，没有选项块")
print()


# ============ 修复后的解析逻辑 ============
print("\n" + "=" * 60)
print("修复后的解析逻辑测试")
print("=" * 60)

# 匹配一行开头的 3+ 个连续冒号（fence 标记）
_COLON_FENCE_RE = re.compile(r'^:{3,}')


def fixed_parse_options(content):
    options_block = None
    if content.startswith("---"):
        return ("YAML", content)
    elif content.lstrip().startswith(":"):
        content_lines = content.splitlines()
        yaml_lines = []

        # 修复 1: 先跳过前导空行
        while content_lines and not content_lines[0].strip():
            content_lines.pop(0)

        while content_lines:
            stripped = content_lines[0].lstrip()

            # 修复 2: 使用正则精确检测 colon fence（3+ 个连续冒号开头）
            if _COLON_FENCE_RE.match(stripped):
                break

            # 修复 3: 遇到非冒号开头的行停止
            if not stripped.startswith(":"):
                break

            # 修复 4: 验证选项行格式 - 去掉前导冒号后，检查是否是 key: value 格式
            after_first_colon = stripped[1:]  # 去掉第一个冒号
            # 必须能解析成 key: value 格式（key 后必须跟冒号）
            # 注意：after_first_colon 可能是 "key: value"、"key:" 或 "just-text"
            # 我们不需要在这里完全验证，只需要检查:
            # 如果去掉第一个冒号后不以 ':' 开头（避免 :::xxx 被漏网）
            # 且包含至少一个冒号或为空（空值选项）
            if after_first_colon.startswith(":"):
                # 这行是 "::xxx" 格式，不是合法选项
                break

            yaml_lines.append(content_lines.pop(0).lstrip()[1:])

        options_block = "\n".join(yaml_lines)
        content = "\n".join(content_lines)
        return (options_block, content)
    return (None, content)


print("\n--- 使用修复后的逻辑测试问题场景 ---")

print("\n场景 3 (单冒号文本):")
content3 = ":class: outer\n:just-text-no-colon-after\ncontent"
old_result = current_parse_options(content3)
new_result = fixed_parse_options(content3)
print(f"  旧逻辑: options={repr(old_result[0])}, body={repr(old_result[1])}")
print(f"  新逻辑: options={repr(new_result[0])}, body={repr(new_result[1])}")

print("\n场景 4 (双冒号前缀):")
content4 = ":class: outer\n::double-colon-text\ncontent"
old_result = current_parse_options(content4)
new_result = fixed_parse_options(content4)
print(f"  旧逻辑: options={repr(old_result[0])}, body={repr(old_result[1])}")
print(f"  新逻辑: options={repr(new_result[0])}, body={repr(new_result[1])}")

print("\n场景 8 (前导空行+选项):")
content8 = "\n\n:class: outer\ncontent"
old_result = current_parse_options(content8)
new_result = fixed_parse_options(content8)
print(f"  旧逻辑: options={repr(old_result[0])}, body={repr(old_result[1])}")
print(f"  新逻辑: options={repr(new_result[0])}, body={repr(new_result[1])}")

print("\n场景 1 (嵌套 fence + 前导换行):")
content1 = "\n:::{subnote}\n:class: inner\ncontent\n:::"
old_result = current_parse_options(content1)
new_result = fixed_parse_options(content1)
print(f"  旧逻辑: options={repr(old_result[0])}, body={repr(old_result[1])}")
print(f"  新逻辑: options={repr(new_result[0])}, body={repr(new_result[1])}")
