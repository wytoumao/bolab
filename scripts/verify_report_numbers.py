#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""财报整理 report.html 数字保真门：生成的 HTML 与源 PDF 抽取文本双向比对数字 token。

- 正向（防漏抄）：源 layout 抽取里的每个数字，HTML 可见文本里必须有。
  只用 -layout（分词边界可靠）；-raw 会把相邻文本段粘连（如 FY2024+20-F→202420）制造工件。
  token 覆盖检查与列位置无关，layout 单侧即是完整数字清单。
  残余粘连兜底：无逗号无小数的整数 token 若可拆成两半且都在 HTML 中 → 降级为警告，人工过目。
- 反向（防编造）：HTML 可见文本里的每个数字，必须在 layout∪raw 里出现过。
  （柱状图高度等表现层数值随 HTML 标签/属性剥离，不参与比对。）
- 两侧对称剔除含 URL 特征（/、http、www.、.htm）的词——PDF 里 URL 断行会产生数字碎片。

用法:
  python3 scripts/verify_report_numbers.py <生成的report.html> <源layout.txt> <源raw.txt> [输出diff文件]
有漏抄或编造 → 退出码 1，人工复核后方可提交；仅警告 → 退出码 0。
"""
import html as html_mod
import re
import sys
from collections import Counter

# 负向后顾：紧跟在字母/数字后的不算数字起点——排除 URL slug（year-2024-results）、
# 代码（FY2024、Q42024、20-F 编号）等非财务语境，两侧对称生效
NUM_RE = re.compile(r"(?<![A-Za-z\d])[+\-−–]?\d[\d,，]*(?:\.\d+)?%?")
# 源文本中要剔除的整行（打印页脚、页码等排版工件）
FOOTER_RE = re.compile(r"据公开资料独立整理|^第\s*\d+\s*页|^\s*\d{1,3}\s*$")


def normalize(tok: str) -> str:
    tok = tok.replace("，", ",").replace("−", "-").replace("–", "-")
    tok = tok.replace(",", "")          # 去千分位
    tok = tok.lstrip("+")               # +59% 与 59% 视同
    return tok


# 斜杠仅在紧邻数字时视为 URL 特征（549802/000119…、139926/d788…）；
# 中文行文里的「分红/回购」这类斜杠不能整词误杀——CJK 无空格，一"词"可能是整段话
URLISH_RE = re.compile(r"http|www\.|\.htm|[?&=]|\d/|/\d", re.IGNORECASE)
LIST_IDX_RE = re.compile(r"^\d{1,2}\.$")   # 行首「5.」这类列表编号——HTML 用 <ol> 渲染，无文本数字


def tokens_from_text(text: str, drop_footer: bool) -> Counter:
    out = Counter()
    for line in text.splitlines():
        if drop_footer and FOOTER_RE.search(line):
            continue
        # 逐词过滤 URL 特征词（两侧对称）与行首列表编号，再在剩余词内提取数字
        for wi, word in enumerate(line.split()):
            if URLISH_RE.search(word):
                continue
            if wi == 0 and LIST_IDX_RE.match(word):
                continue
            for m in NUM_RE.findall(word):
                out[normalize(m)] += 1
    return out


def splittable_into(tok: str, pool: Counter) -> bool:
    """粘连兜底：纯整数 token 能否拆成两半、两半都在 pool 里。"""
    if "." in tok or "%" in tok or not tok.isdigit() or len(tok) < 3:
        return False
    return any(tok[:i] in pool and tok[i:] in pool for i in range(1, len(tok)))


def visible_text_of_html(path: str) -> str:
    src = open(path, encoding="utf-8").read()
    src = re.sub(r"<!--.*?-->", " ", src, flags=re.S)
    src = re.sub(r"<style.*?</style>", " ", src, flags=re.S)
    src = re.sub(r"<script.*?</script>", " ", src, flags=re.S)
    src = re.sub(r"<[^>]+>", " ", src)   # 剥标签（含 style="height:62%" 等属性）
    return html_mod.unescape(src)


def context_lines(path: str, needle_norm: str, limit: int = 2) -> list:
    """在文件里找包含该数字(任意写法)的行，给 ±0 行上下文即可定位。"""
    hits = []
    for i, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
        for m in NUM_RE.findall(line):
            if normalize(m) == needle_norm:
                hits.append(f"  L{i}: {line.strip()[:120]}")
                break
        if len(hits) >= limit:
            break
    return hits


def main() -> int:
    if len(sys.argv) < 4:
        print(__doc__)
        return 2
    html_path, layout_path, raw_path = sys.argv[1:4]
    diff_path = sys.argv[4] if len(sys.argv) > 4 else None

    layout_tokens = tokens_from_text(open(layout_path, encoding="utf-8").read(), drop_footer=True)
    raw_tokens = tokens_from_text(open(raw_path, encoding="utf-8").read(), drop_footer=True)
    html_tokens = tokens_from_text(visible_text_of_html(html_path), drop_footer=False)
    src_union = layout_tokens + raw_tokens  # 反向侧用并集，减少误报

    missing, warned = [], []
    for t in sorted(layout_tokens):          # 正向门：只用 layout
        if t in html_tokens:
            continue
        (warned if splittable_into(t, html_tokens) else missing).append(t)
    invented = sorted(t for t in html_tokens
                      if t not in src_union and not splittable_into(t, src_union))

    lines = []
    if missing:
        lines.append(f"== 漏抄（源有 HTML 无）: {len(missing)} 个 ==")
        for t in missing:
            lines.append(f"[{t}]")
            lines += context_lines(layout_path, t)
    if invented:
        lines.append(f"== 多出（HTML 有 源无）: {len(invented)} 个 ==")
        for t in invented:
            lines.append(f"[{t}]")
            lines += context_lines(html_path, t)
    if warned:
        lines.append(f"== 警告（疑似抽取粘连，已按可拆分放行，请过目）: {len(warned)} 个 ==")
        for t in warned:
            lines.append(f"[{t}]")
            lines += context_lines(layout_path, t)

    report = "\n".join(lines)
    if diff_path:
        open(diff_path, "w", encoding="utf-8").write(report + ("\n" if report else ""))
    if missing or invented:
        print(report)
        print(f"\n❌ {html_path}: 漏抄 {len(missing)} / 多出 {len(invented)} / 警告 {len(warned)}（详见 {diff_path or 'stdout'}）")
        return 1
    status = f"，粘连警告 {len(warned)} 个待过目" if warned else "，无警告"
    print(f"✅ {html_path}: 数字保真门通过（layout {len(layout_tokens)} 个唯一 token 全覆盖，无编造{status}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
