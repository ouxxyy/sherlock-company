#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report.html 交付前实测检查（阶段 A 验收证据）。
检查项：
  1. 离线打开：offline 上下文加载 file://，捕获任何网络请求失败（=页面若依赖网络即暴露）；
  2. 无横向溢出：1200px 与 375px 视口下 documentElement.scrollWidth <= clientWidth，
     并逐元素找超出视口右边界的元素；
  3. 链接安全：全部 <a> 仅 http/https，且 target=_blank、rel 含 noopener noreferrer；
  4. 内容编号一致：E1–E17（含 E5b/E7b）19 条 + X1–X6 与 case-record.json 集合相等；
  5. 双端截图：桌面 1200×(2x) 与 375×(2x) 全页 PNG。
运行：python3 verify_report_html.py
"""
import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

CASE = Path(__file__).resolve().parent
HTML = CASE / "report.html"
rec = json.loads((CASE / "case-record.json").read_text("utf-8"))

results, fails = [], []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    if not ok:
        fails.append(f"{name}: {detail}")


doc = HTML.read_text("utf-8")

# ---- 4. 编号一致（静态） ------------------------------------------------
want_ev = {e["id"] for e in rec["evidence"]}
got_ev = set(re.findall(r'<span class="eid">([A-Z]\d+b?)</span>', doc))
check("编号一致·19 条证据全部在页", got_ev == want_ev,
      f"缺失={sorted(want_ev - got_ev)} 多余={sorted(got_ev - want_ev)} 共{len(got_ev)}")
want_x = {f"X{i}" for i in range(1, 7)}
got_x = set(re.findall(r'<span class="xid">(X\d)</span>', doc))
check("编号一致·X1–X6 全部在页", got_x == want_x, f"实际={sorted(got_x)}")

# ---- 静态离线红线：无 script/外链资源 ----------------------------------
check("无 <script> 块", "<script" not in doc.lower())
check("无外链样式/字体/图片",
      not re.search(r'<(link|img|iframe|embed|object)\b', doc, re.I),
      "发现外链资源标签")
check("无 @import/@font-face/url() 引用",
      not re.search(r'@import|@font-face|url\(', doc, re.I))

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)

    # ---- 1. 离线打开（offline 上下文 + file://） -------------------------
    ctx = browser.new_context(offline=True, viewport={"width": 1200, "height": 900})
    page = ctx.new_page()
    net_attempts = []
    page.on("requestfailed", lambda r: net_attempts.append(r.url))
    page.on("request", lambda r: net_attempts.append(r.url) if not r.url.startswith("file://") else None)
    page.goto(HTML.as_uri(), wait_until="load")
    body_text = page.inner_text("body")
    for probe in ["★ 3.5", "置信度定级：低", "E17", "X6", "绝不等于「无负面」",
                  "机会层：未生成", "签约主体核验提示", "资本开支参照注记",
                  "未证实", "单源媒体推断", "88.97"]:
        check(f"离线加载·页面含「{probe}」", probe in body_text)
    check("离线加载·零网络请求", not net_attempts, f"网络请求={net_attempts[:5]}")
    ctx.close()

    # ---- 2+3. 双端视口：溢出与链接安全；并截图 ---------------------------
    for label, vw, vh, dsf, out in [
        ("desktop", 1200, 900, 2, CASE / "report-html-desktop.png"),
        ("mobile", 375, 812, 2, CASE / "report-html-mobile.png"),
    ]:
        ctx = browser.new_context(
            viewport={"width": vw, "height": vh}, device_scale_factor=dsf)
        pg = ctx.new_page()
        pg.goto(HTML.as_uri(), wait_until="load")
        sw = pg.evaluate("document.documentElement.scrollWidth")
        cw = pg.evaluate("document.documentElement.clientWidth")
        check(f"{label}·无横向溢出（scrollWidth {sw} <= clientWidth {cw}）", sw <= cw,
              f"scrollWidth={sw} clientWidth={cw}")
        wide = pg.evaluate("""() => {
          const bad = [];
          document.querySelectorAll('body *').forEach(el => {
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.right > window.innerWidth + 1) {
              bad.push(el.tagName + '.' + String(el.className).split(' ')[0] + '@' + Math.round(r.right));
            }
          });
          return bad.slice(0, 8);
        }""")
        check(f"{label}·无元素越出视口", not wide, f"越界元素={wide}")
        anchors = pg.evaluate("""() => Array.from(document.querySelectorAll('a')).map(a => ({
            href: a.href, target: a.target || '', rel: a.rel || ''}))""")
        bad_scheme = [a["href"] for a in anchors if not re.match(r"^https?://", a["href"])]
        bad_rel = [a["href"] for a in anchors
                   if a["target"] != "_blank" or "noopener" not in a["rel"] or "noreferrer" not in a["rel"]]
        check(f"{label}·链接仅 http/https", not bad_scheme, f"非安全协议={bad_scheme}")
        check(f"{label}·链接全部 target=_blank + noopener noreferrer", not bad_rel,
              f"缺属性={bad_rel}")
        uniq = {a["href"] for a in anchors}
        rec_urls = set()
        for e in rec["evidence"]:
            rec_urls |= set(re.findall(r"https?://[^\s；;（)，。]+", e.get("url", "")))
        rec_urls = {u.rstrip("。，、）.”\"'") for u in rec_urls}
        check(f"{label}·外链集合与 case-record.json 同源", uniq == rec_urls,
              f"HTML独有={sorted(uniq - rec_urls)} record独有={sorted(rec_urls - uniq)}")
        pg.screenshot(path=str(out), full_page=True)
        check(f"{label}·全页截图已生成", out.exists(), str(out))
        ctx.close()
    browser.close()

print("=" * 72)
ok_all = True
for name, ok, detail in results:
    mark = "PASS" if ok else "FAIL"
    if not ok:
        ok_all = False
    print(f"[{mark}] {name}" + (f" —— {detail}" if detail and not ok else ""))
print("=" * 72)
print(f"共 {len(results)} 项检查，{'全部通过' if ok_all else str(len(fails)) + ' 项未通过'}")
sys.exit(0 if ok_all else 1)
