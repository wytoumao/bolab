#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""给财报整理 report.html（A4 打印稿）追加手机端阅读适配。幂等，可重复运行。

做两件事：
  1. 缺 viewport meta 时，在 <meta charset="UTF-8"> 行后插入；
  2. 以标记块（mobile-screen-patch）在最后一个 </style> 前插入 @media screen CSS；
     已存在同名标记块时整块替换（便于升级 v2/v3）。

全部规则包在 @media screen and (max-width:720px) 内，不触碰 @media print / @page，
headless Chrome --print-to-pdf 输出不受影响。

用法:
  python3 scripts/patch_report_mobile.py <file.html> [...]
  python3 scripts/patch_report_mobile.py --check <file.html> [...]   # 只检查，未打补丁的列出并以非零码退出
"""
import re
import sys

VIEWPORT = '<meta name="viewport" content="width=device-width, initial-scale=1">'

MARK_START = "/* ===== mobile-screen-patch v1 — applied by scripts/patch_report_mobile.py ===== */"
MARK_END = "/* ===== /mobile-screen-patch ===== */"

CSS_BLOCK = MARK_START + """
  @media screen and (max-width: 720px) {
    html { -webkit-text-size-adjust: 100%; }
    body { font-size: 13px; line-height: 1.65; padding: 0 14px 32px;
           max-width: 100%; overflow-x: hidden; overflow-wrap: break-word; }
    .topbar { position: static; height: 6px; }          /* fixed 8mm 顶条 → 细的入流色条 */
    .cover { padding-top: 16px; }
    .cover-title { font-size: 21px; }
    .cover-sub   { font-size: 18px; }
    .cover-meta  { font-size: 11px; }
    h2.sec { font-size: 15px; margin: 18px 0 10px; }
    h3 { font-size: 13px; }
    /* 宽表格：容器内横向滚动，不撑爆页面（纯 CSS，不改 HTML） */
    table { display: block; width: 100%; overflow-x: auto;
            -webkit-overflow-scrolling: touch; font-size: 11px; }
    table caption { display: block; }
    th, td { padding: 5px 7px; }
    .chart { gap: 8px; height: 110px; padding: 8px 4px 0; }
    .chart .cap, .chart .qx { font-size: 9px; }
    .read { font-size: 11.5px; padding: 8px 10px; }
    .toc { font-size: 12px; }
  }
""" + MARK_END

CHARSET_RE = re.compile(r'(<meta\s+charset=["\']?UTF-8["\']?\s*/?>)', re.IGNORECASE)


def is_patched(html: str) -> bool:
    return MARK_START in html and 'name="viewport"' in html


def patch(html: str) -> str:
    # 1) viewport
    if 'name="viewport"' not in html:
        html = CHARSET_RE.sub(r"\1\n" + VIEWPORT, html, count=1)
    # 2) CSS 标记块：已有则整块替换，没有则插到最后一个 </style> 前
    if MARK_START in html:
        pre, rest = html.split(MARK_START, 1)
        _, post = rest.split(MARK_END, 1)
        html = pre + CSS_BLOCK + post
    else:
        idx = html.rfind("</style>")
        if idx == -1:
            raise ValueError("找不到 </style>，不是预期的 report.html")
        html = html[:idx] + CSS_BLOCK + "\n" + html[idx:]
    return html


def main() -> int:
    args = sys.argv[1:]
    check_only = "--check" in args
    files = [a for a in args if a != "--check"]
    if not files:
        print(__doc__)
        return 2
    unpatched = []
    for path in files:
        with open(path, encoding="utf-8") as f:
            html = f.read()
        if is_patched(html):
            print(f"ok      {path}")
            continue
        if check_only:
            unpatched.append(path)
            print(f"MISSING {path}")
            continue
        new_html = patch(html)
        if 'name="viewport"' not in new_html:
            raise ValueError(f"{path}: 未找到 charset meta，viewport 插入失败")
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_html)
        print(f"patched {path}")
    return 1 if unpatched else 0


if __name__ == "__main__":
    sys.exit(main())
