#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
report.html 同源生成器（阶段 A）
事实基准：cases/4399/case-record.json（v4）+ report.md
版式基准：cases/4399/sherlock-dossier-4399.op（视觉复核通过稿 v4.0）
输出：cases/4399/report.html —— 单文件离线 HTML：
  - 全部案件文本经 html.escape 转义后注入；
  - 仅内联 CSS，无 <script>、无外链字体/图片/样式；
  - 超链接仅 http/https，一律 target="_blank" rel="noopener noreferrer"。
运行：python3 build_report_html.py
"""
import html
import json
import re
import sys
from pathlib import Path

CASE_DIR = Path(__file__).resolve().parent
RECORD = CASE_DIR / "case-record.json"

E = html.escape  # noqa: N816  案件文字统一转义


def load_record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


# ---------------------------------------------------------------- 链接处理
# 仅接受显式带 http/https 的直链（与 case-record.json url 字段同源提取）。
# 展示文案用短域名标签，避免长 URL 在 375px 视口撑破版面。
URL_RE = re.compile(r"https?://[^\s；;（)，。]+")
LINK_LABELS = {
    "www.4399.com": "4399.com 官网",
    "my.4399.com": "my.4399.com/joinus 招聘站",
    "web.4399.com": "web.4399.com/campus 校招官网",
    "finance.sina.com.cn": "finance.sina.com.cn（运营商财经网转稿）",
    "investxiamen.org.cn": "investxiamen.org.cn（厦门市投资促进局转载）",
    "news.qq.com": "news.qq.com（厦门日报社官方账号）",
    "games.sina.com.cn": "games.sina.com.cn（中新网 2014-04-28）",
    "news.17173.com": "news.17173.com（17173 转载）",
    "gamersky.com": "gamersky.com（2019-11 判决报道）",
    "thnet.gov.cn": "thnet.gov.cn（天河区政府网 2024-11-12）",
}


def extract_links(url_field: str):
    """从 record 的 url 字段提取安全直链，返回 [(url, label)]。"""
    if not url_field:
        return []
    out = []
    for m in URL_RE.findall(url_field):
        u = m.rstrip("。，、）.”\"'")
        netloc = re.sub(r"^https?://", "", u).split("/")[0]
        label = LINK_LABELS.get(netloc, netloc)
        out.append((u, label))
    return out


def first_link(links):
    return links[0][0] if links else None


def a_tag(url: str, label: str) -> str:
    """安全外链：仅 http/https；统一 target/_blank + rel/noopener noreferrer。"""
    if not re.match(r"^https?://", url):
        raise ValueError(f"拒绝非安全协议链接: {url!r}")
    return (
        f'<a class="ext" href="{E(url, quote=True)}" target="_blank" '
        f'rel="noopener noreferrer">{E(label)} <span class="arr" aria-hidden="true">&#8599;</span></a>'
    )


# ---------------------------------------------------------------- 小部件
def badge(text, cls=""):
    return f'<span class="bdg {cls}">{E(text)}</span>'


def eid(idtext):
    return f'<span class="eid">{E(idtext)}</span>'


# ---------------------------------------------------------------- 区块
def build_header(rec):
    ev_count = len(rec["evidence"])
    return f"""
<header class="hdr">
  <div class="row-tags">
    <div class="tag-row">
      {badge("SHERLOCK-DOSSIER // CASE-4399 · " + E(rec["meta"]["record_version"].upper()), "bdg-sky")}
      {badge("离线侦探档案 · 商业雇主尽调", "bdg-dim")}
      {badge("密级：内部调查样板", "bdg-red")}
    </div>
    <div class="meta-line">调查日期：{E(rec["meta"]["investigation_date"])}（+08:00）｜ 输入：「{E(rec["meta"]["input"])}」｜ 证据登记：E1–E17（含 E5b/E7b，共 {ev_count} 条，v4 定点核查版）</div>
  </div>
  <div class="title-row">
    <div>
      <h1>4399（四三九九）雇主调查样板档案</h1>
      <p class="sub">主体范围覆盖：厦门四三九九网络（总部）为主，广州四三九九信息科技（研发）及北京四三九九为关联主体</p>
    </div>
    {badge("企业层分析 · 非入职建议", "bdg-amber")}
  </div>
  <div class="banner-amber" role="note">
    <span class="warn-ico" aria-hidden="true">&#9888;</span>
    <span>调查范围声明：本档案基于公开可检事实与多源交叉印证制作。一手在职员工体验证据为零（主流职场平台被反爬或拦截），不能作为个人入职绝对背书，求职者务必针对具体签约主体与社保地线下核实。</span>
  </div>
  <div class="layer-strip">
    {badge("本报告层级：企业层（enterprise）——判断雇主对象是否值得继续接触", "bdg-green")}
    {badge("机会层：未生成——" + E(rec["meta"]["opportunity_layer_reason"]) + "；企业星不是任何个人 Offer 建议", "bdg-dim")}
  </div>
</header>"""


def build_verdict(rec):
    r = rec["rating"]
    rev = r["review"]
    cond_items = "".join(f"<li>{E(c)}</li>" for c in r["change_conditions"])
    return f"""
<section class="card verdict">
  <h2 class="card-tt">综合裁决 // THE VERDICT</h2>
  <div class="star-line">
    <div class="star-big">★ {E(str(r["stars"]))}</div>
    <div>
      <div class="dim-note">企业推荐星级（满分 5.0）</div>
      <div class="star-label">{E(r["stars_label"])}</div>
    </div>
  </div>
  <div class="conf-box">
    <span class="warn-ico" aria-hidden="true">&#9432;</span>
    <div>
      <div class="conf-tt">置信度定级：{E(r["confidence"])}（LOW CONFIDENCE）</div>
      <div class="conf-note">一手在职体验记录为 0 条 · 统计限制表明非企业必然劣质</div>
    </div>
  </div>
  <div class="adj-box">
    <div class="adj-tt">相邻档位裁决理由：</div>
    <ul class="plain">
      <li>为何不给 4 星：{E(r["adjacent"]["why_not_4"])}</li>
      <li>为何不降 3 星：{E(r["adjacent"]["why_not_3"])}</li>
    </ul>
  </div>
  <div class="review-box">
    <div class="review-tt">独立评分复核（{E(rev["file"])}）：</div>
    <div class="review-note">reviewer 先盲评后对照，与初评差异 {E(str(rev["blind_diff"]))}，未触发裁决程序；盲评底稿 _blind-review-scratch.md 原件留存。</div>
  </div>
  <div class="cond-box">
    <div class="cond-tt">底线声明与改分条件（出现即重评）：</div>
    <p class="cond-line">{E(r["bottom_line"])}</p>
    <ul class="plain cond-list">
      {cond_items}
    </ul>
  </div>
</section>"""


# 五维展示：名称/配色沿用已通过设计稿，方向判定文字取 case-record.json 原文。
DIMENSIONS = [
    ("业务稳定性", "稳定", "green",
     "E5b 百强第 30 位原文已核、连续十三年入选；E17 拿地仅作资本开支参照，不列入评级支柱"),
    ("待遇与福利", "待遇", "amber",
     "官方宣传双休包三餐（E3/E10 同源传播）；E5 营收 88.97 亿为单源媒体推断"),
    ("成长与空间", "成长", "slate",
     "无一手晋升通道公开数据；招股书签署日无正在执行的股权激励（E4）"),
    ("工作强度", "强度", "red",
     "双休自述与项目组惨烈并存（E12/E16）；社区显性关注加班强度"),
    ("管理风格", "管理", "red",
     "2014 未证实裁员传闻（E7）／高管股权争议（E6）／2019 侵权败诉（E8）"),
]


def build_dimensions(rec):
    rec_dims = {d["name"]: d for d in rec["rating"]["dimensions"]}
    rows = []
    for label, key, color, basis in DIMENSIONS:
        d = rec_dims[key]
        rows.append(f"""
      <div class="dim-row">
        <div class="dim-head"><span class="dim-name">{E(label)}</span><span class="pill pill-{color}">{E(d["direction"])}</span></div>
        <div class="dim-basis">{E(basis)}　<span class="evi-ids">依据：{'、'.join(E(x) for x in d['basis'])}</span></div>
      </div>""")
    kj = "".join(f"<p>{E(t)}</p>" for t in rec["key_judgments"])
    return f"""
<section class="card dims">
  <h2 class="card-tt">五维深度评级 // DIMENSIONS SCAN</h2>
  <div class="dim-stack">{''.join(rows)}</div>
  <div class="kj-box">
    <div class="kj-tt">三条核心判断：</div>
    {kj}
  </div>
</section>"""


def build_entities(rec):
    s = rec["subjects"]
    pri = s["primary"]
    gz = s["subsidiaries"][0]
    bj = s["subsidiaries"][1]
    links = {ev["id"]: extract_links(ev.get("url", "")) for ev in rec["evidence"]}
    e5b = a_tag(*links["E5b"][0])
    e17 = a_tag(*links["E17"][0])
    return f"""
<section class="blk">
  <div class="blk-head">
    <h2>主体范围与用工防混淆矩阵 // ENTITY SCOPE &amp; RISK MATRIX</h2>
    {badge("求职防御提示 · 面试须核验合同签约主体与社保地", "bdg-amber")}
  </div>
  <div class="grid-2">
    <div class="card ent">
      <div>{badge("母公司 / 总部 / 招聘主体", "bdg-green")}</div>
      <h3>{E(pri["name"])}</h3>
      <ul class="plain ent-list">
        <li>城市/地址：{E(pri["city"])} · {E(pri["address"])}</li>
        <li>核心职能：{E(pri["role"])}（E1/E2）</li>
        <li>股权结构（2016 招股书口径）：{E(s["shareholding_at_prospectus"])}</li>
        <li>沿革：{E(s["lineage"])}（E4）</li>
        <li>现时地位：2025 中国互联网综合实力百强第 30 位、连续十三年入选 {e5b}（E5b 原文已核）</li>
      </ul>
    </div>
    <div class="card ent">
      <div>{badge("全资子公司 / 游戏自研与发行", "bdg-indigo")}</div>
      <h3>{E(gz["name"])}</h3>
      <ul class="plain ent-list">
        <li>城市/地址：{E(gz["city"])} · {E(gz["address"])}</li>
        <li>核心职能：{E(gz["role"])}</li>
        <li>历史记录：2014 未证实裁员传闻（E7，仅证明传闻被媒体报道，E7b 同向转载旁证）；2019 暴雪案侵权败诉赔约 400 万（E8，媒体口径双源一致）</li>
        <li>现时投入：2024-11 竞得天河金融城东区 AT101828 地块、约 6.03 亿元建未来总部 {e17}（E17 政府源原文已核。注：属资本开支参照注记，不作为稳定性评级依据）</li>
        <li>待核事项：注册地（天河）与办公地（黄埔）迁移未核；「B 轮 3.5 亿融资」与 100% 全资并存的股权链条未核</li>
      </ul>
    </div>
  </div>
  <div class="ent-strip">
    <div class="strip-top">
      <div class="strip-left">{badge("关联主体", "bdg-dim")}<span>{E(bj["name"])}：{E(bj["role"])}（E2/E4）；另含{E("、".join(s["related"]))}。</span></div>
      <div class="strip-x2">X2 更正：厦门买地传闻排除（未发现任何厦门拿地记录）；真实对应物为广州 6.03 亿拿地（E17），系地域张冠李戴。</div>
    </div>
    <div class="verify-band">
      {badge("签约主体核验提示", "bdg-amber")}
      <span>广州研发属全资子公司，但公开招聘多以厦门母公司名义发布。签约与社保地公开信息无法确认，以面试及 Offer 阶段书面核实为准，本档案不预设——防范跨主体调配风险。</span>
    </div>
  </div>
</section>"""


# 证据三级分栏：栏内每条均从 case-record.json 渲染 supports/limits 原文，19 条全部在页。
HARD_IDS = ["E1", "E2", "E3", "E4", "E5b", "E17"]
SOFT_IDS = ["E5", "E6", "E7", "E7b", "E8", "E9", "E10", "E11", "E12", "E13", "E14", "E15", "E16"]


def evidence_item(ev, links):
    anchors = "　".join(a_tag(u, lab) for u, lab in links)
    link_html = f'<span class="evi-links">{anchors}</span>' if anchors else ""
    note = ""
    if ev["id"] == "E4":
        note = '<div class="evi-note">原文存档：cases/4399/attachments/（来源 csrc.gov.cn，申报稿 2016-06-06）</div>'
    return f"""
    <li>
      <div class="evi-head">{eid(ev["id"])}<span class="evi-title">{E(ev["title"])}</span>{link_html}</div>
      <div class="evi-sup">支持：{E(ev["supports"])}</div>
      <div class="evi-lim">限定：{E(ev["limits"])}</div>
      {note}
    </li>"""


def build_evidence(rec):
    evmap = {ev["id"]: ev for ev in rec["evidence"]}
    links = {k: extract_links(evmap[k].get("url", "")) for k in evmap}
    hard = "".join(evidence_item(evmap[i], links[i]) for i in HARD_IDS)
    soft = "".join(evidence_item(evmap[i], links[i]) for i in SOFT_IDS)
    gaps = "".join(f"<li>{E(g)}</li>" for g in rec["coverage_gaps"])
    xs = "".join(
        f'<li><span class="xid">{E(x["id"])}</span> {E(x["item"])}——{E(x["reason"])}</li>'
        for x in rec["exclusions"]
    )
    return f"""
<section class="blk">
  <div class="blk-head">
    <h2>证据链账本与可溯源事实 // EVIDENCE LEDGER &amp; AUDIT TRAIL</h2>
    <span class="blk-note">三级来源分类：✅ 原文已核 ｜ 🟡 摘要转述/定性收紧 ｜ ⛔ 渠道缺口拦截 · 全部 {len(rec["evidence"])} 条证据（E1–E17 含 E5b/E7b）在页可查</span>
  </div>
  <div class="grid-3">
    <div class="card led led-hard">
      <div>{badge("✅ 原文已核 · 硬证据骨架", "bdg-green")}</div>
      <ul class="plain evi">{hard}</ul>
    </div>
    <div class="card led led-soft">
      <div>{badge("🟡 摘要转述 · 审慎定性与收紧", "bdg-amber")}</div>
      <ul class="plain evi">{soft}</ul>
    </div>
    <div class="card led led-gap">
      <div>{badge("⛔ 覆盖缺口与误报排除（X1–X6）", "bdg-red")}</div>
      <ul class="plain gap-list">{gaps}</ul>
      <p class="gap-line">渠道缺口声明：以上渠道拦截与缺口绝不等于「无负面」。</p>
      <div class="x-box">
        <div class="x-tt">已排查排除项清单（X1–X6）：</div>
        <ul class="plain x-list">{xs}</ul>
      </div>
    </div>
  </div>
</section>"""


# 竞争假设：结构取 case-record.json reasoning（议题/证据组），
# H1/H2 展开文字沿用已通过设计稿口径并对齐账本限定，禁止超出证据强度的断言。
HYPOTHESES = [
    {
        "topic": "工作强度与作息节奏", "verdict_tone": "red",
        "h1_t": "整体节奏温和", "h1": "校招与内推统一口径双休、包三餐、年底双薪（E3/E10，同一信息源传播，未获独立印证）。",
        "h2_t": "组间分化", "h2": "匿名自述「正常上下班双休」与「其他组听说很惨」并存（E12，自认不具代表性）；社区显性关注面试试探下班时间（E16）。",
    },
    {
        "topic": "薪资兑现与长期激励", "verdict_tone": "amber",
        "h1_t": "现金薪资稳定兑现", "h1": "2012 运营岗口径为低底薪+高奖金（E11，11 年前）；官方与内推帖宣传年底双薪、六险一金（E3/E10 同源）。",
        "h2_t": "长期承诺有缩水先例", "h2": "高管股权口头承诺曾由 1.5% 缩水至万分之七（E6）；2014 有过乐游家持股安排，招股书签署日已无正在执行的激励制度（E4）。",
    },
    {
        "topic": "主体归属与调配风险", "verdict_tone": "slate",
        "h1_t": "母子结构清晰", "h1": "广州为招股书时点 100% 全资子公司、法定代表人骆海坚，总部直接管理（E4）。",
        "h2_t": "混同/调配风险（未排除）", "h2": "若在广州办公而合同签厦门母公司或第三方，将面临跨主体跨城调配与社保地变化——签约主体实际操作未知，面试必问（E2 招聘主体与用工主体可能分离）。",
    },
    {
        "topic": "经营稳定性与业绩底色", "verdict_tone": "green",
        "h1_t": "稳健经营（占优）", "h1": "2025 互联网百强第 30 位、连续十三年入选（E5b 原文已核可复核）；校招社招持续放量（E2/E3）；广州主体竞得未来总部用地（E17，仅作参照注记）。",
        "h2_t": "依赖存量/外部不可核", "h2": "未上市无强制披露，业绩依赖度外部不可核；88.97 亿营收为单源转述且年份系媒体推断（E5）；IPO 已于 2019-09 终止审查（E5）。",
    },
    {
        "topic": "历史负面与现时关联", "verdict_tone": "amber",
        "h1_t": "已翻篇", "h1": "股权争议（2014-2015）、裁员传闻（2014）、实名举报（2017）、侵权败诉（2019）距今已久，未发现现时延续证据。",
        "h2_t": "隐性延续（无法排除）", "h2": "「无现时延续证据」部分源于员工讨论渠道不可达；组织惯性是否延续，现有证据不支持任何一侧，不视为彻底翻篇。",
    },
]


def build_hypotheses(rec):
    rec_rea = {r["topic"]: r for r in rec["reasoning"]}
    # record 的主题名与展示议题一一对应
    topic_map = ["强度", "待遇", "主体/城市", "稳定", "历史负面现时关联"]
    cards = []
    for i, (h, key) in enumerate(zip(HYPOTHESES, topic_map), 1):
        rr = rec_rea[key]
        chips = "".join(f'<span class="chip">{E(x)}</span>' for x in rr["evidence"])
        cards.append(f"""
    <div class="hyp">
      <div class="hyp-head"><span class="hyp-tt">议题{'一二三四五'[i-1]}：{E(h["topic"])}</span>{badge("裁决：" + rr["judgment"], f"bdg-{h['verdict_tone']}")}</div>
      <div class="grid-2">
        <div class="hyp-box hyp-h1">
          <div class="hyp-t1">假设 H1（偏正向）：{E(h["h1_t"])}</div>
          <div class="hyp-body">{E(h["h1"])}</div>
        </div>
        <div class="hyp-box hyp-h2">
          <div class="hyp-t1">假设 H2（偏警惕）：{E(h["h2_t"])}</div>
          <div class="hyp-body">{E(h["h2"])}</div>
        </div>
      </div>
      <div class="chip-row"><span class="chip-lab">证据组：</span>{chips}</div>
    </div>""")
    return f"""
<section class="blk">
  <div class="blk-head">
    <h2>竞争假设与推断对抗 // HYPOTHESIS DIALECTICS（H1 vs H2）</h2>
    <span class="blk-note">严禁单一化偏听偏信 · 5 大核心议题正反多维推断</span>
  </div>
  {''.join(cards)}
</section>"""


INTERVIEW = [
    ("Q1 · 签约主体与社保地（防偷梁换柱）",
     "「请问我的劳动合同签约主体全称是哪一家公司？社保公积金在广州还是厦门缴纳？」",
     "调查意图：锁定是否与研发实体签约，防范空壳或第三方外包混同。"),
    ("Q2 · 真实下班与上线节奏（破除滤镜）",
     "「目标项目组过去三个月平均几点下班？版本更新上线前后的节奏一般是怎样的？」",
     "调查意图：突破 HR 统一口径，获取项目组真实作息方差。"),
    ("Q3 · 加班补偿与书面制度（防无偿奉献）",
     "「项目组加班有无正式书面审批制度？加班是按法定标准给调休还是折算加班费？」",
     "调查意图：检验加班是否受公司规章承认，是否属于隐形义务加班。"),
    ("Q4 · 奖金历史发放率（防空头支票）",
     "「薪酬结构中的绩效与年终奖，近两年团队的实际发放比例大概是多少？发放月份在哪个月？」",
     "调查意图：核对画饼待遇的现金兑现度，识别年终奖扣发与延发套路。"),
    ("Q5 · 团队离职率与流转（测部门温度）",
     "「目标业务线近两年的离职率如何？上一位负责该岗位的同事是因为什么原因离职的？」",
     "调查意图：通过前任动向探测主管管理风格、项目稳定性与内耗程度。"),
    ("Q6 · 跨主体与跨城调配（防被动发配）",
     "「合同中是否含有跨城市（如广州⇄厦门）或跨关联主体的无条件调动条款？」",
     "调查意图：封堵公司在项目裁撤或变动时强制异地降薪调岗的霸王条款。"),
    ("Q7 · 长期股权与期权制度（口头承诺即废纸）",
     "「公司现阶段是否面向骨干员工设立了正在执行的期权或持股计划？是否有明确书面行权规则？」",
     "调查意图：吸取历史 E6 股权缩水教训，任何长期期权没有白纸黑字一律视为零。"),
]


def build_interview():
    qs = []
    for tt, q, intent in INTERVIEW:
        qs.append(f"""
      <div class="card qcard">
        <div>{badge(tt, "bdg-sky")}</div>
        <div class="q-text">{E(q)}</div>
        <div class="q-intent">{E(intent)}</div>
      </div>""")
    recon = f"""
      <div class="card qcard qcard-recon">
        <div>{badge("现场勘察技巧（保利鱼珠港 G3 / 厦门软件园）", "bdg-amber")}</div>
        <div class="q-text2">建议约在傍晚 18:30-19:30 面试：观察大楼亮灯率与员工神态；离开时检查前台外卖堆积量与班车排队情况，这是刺破虚假双休的最直观物理证据。</div>
        <div class="q-intent">调查意图：通过办公物理环境反推团队真实作息与管理弹性。</div>
      </div>"""
    return f"""
<section class="blk">
  <div class="blk-head">
    <h2>求职者实战面试追问清单 // INTERVIEW WEAPONRY（7 QUESTIONS）</h2>
    {badge("线下反问终极武器 · 破除官方滤镜", "bdg-red")}
  </div>
  <div class="grid-2 qgrid">{''.join(qs)}
    {recon}
  </div>
</section>"""


def build_footer(rec):
    r = rec["rating"]
    return f"""
<footer class="ftr">
  <div>数据同源校验：本页由 cases/4399/case-record.json（{E(rec["meta"]["record_version"])}）+ report.md 同源生成 ｜ 独立复核：reviewer 盲评差异 {E(str(r["review"]["blind_diff"]))} 通过（08-评分复核.md）</div>
  <div>自行复核建议：从 04-证据账本.md（E1–E17）与 attachments/ 招股书 PDF 原文开始 ｜ 调查日期：{E(rec["meta"]["investigation_date"])}（主搜证至拿地核查 14:17–16:05，+08:00）</div>
  <div>Sherlock Company 离线侦探档案 · report.html {E(rec["meta"]["record_version"])}.0（阶段 A）· 本页无外部字体/脚本/图片依赖，可完全离线打开</div>
</footer>"""


CSS = """:root{color-scheme:dark}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:#0B0F19;color:#CBD5E1;font-family:-apple-system,BlinkMacSystemFont,"SF Pro SC","PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans CJK SC",sans-serif;font-size:14px;line-height:1.6}
.wrap{max-width:1200px;margin:0 auto;padding:32px 40px}
h1{font-size:28px;font-weight:700;color:#F8FAFC;line-height:1.3}
h2{font-size:16px;font-weight:700;color:#F8FAFC}
h3{font-size:16px;font-weight:700;color:#F8FAFC}
p,li,div,span{overflow-wrap:anywhere}
a.ext{color:#38BDF8;text-decoration:none;border-bottom:1px solid rgba(56,189,248,.4)}
a.ext:hover{color:#7DD3FC}
.arr{font-size:.85em}
.bdg{display:inline-block;padding:4px 10px;border-radius:4px;font-size:11px;font-weight:600;line-height:1.4;white-space:normal}
.bdg-sky{background:#1E293B;color:#38BDF8;border:1px solid #38BDF8}
.bdg-dim{background:#0F172A;color:#94A3B8;border:1px solid #334155}
.bdg-red{background:#2D1A1E;color:#F87171;border:1px solid #DC2626}
.bdg-amber{background:#2A1E14;color:#F59E0B;border:1px solid #D97706}
.bdg-green{background:#0F2D24;color:#34D399;border:1px solid #059669}
.bdg-indigo{background:#1E2238;color:#818CF8;border:1px solid #4F46E5}
.bdg-slate{background:#1E293B;color:#94A3B8;border:1px solid #64748B}
.eid{display:inline-block;background:#1C2638;color:#7DD3FC;border-radius:4px;padding:1px 7px;font-size:11px;font-weight:700;letter-spacing:.02em}
.chip{display:inline-block;background:#16202F;color:#94A3B8;border-radius:999px;padding:1px 9px;font-size:11px;font-weight:600}
.chip-lab{font-size:11px;color:#64748B;margin-right:4px}
.chip-row{margin-top:8px}
.hdr{border-bottom:1px solid #26344A;padding-bottom:16px}
.tag-row{display:flex;flex-wrap:wrap;gap:10px}
.meta-line{font-size:12px;color:#94A3B8;margin-top:10px}
.title-row{display:flex;justify-content:space-between;align-items:flex-start;gap:16px;margin-top:14px;flex-wrap:wrap}
.sub{font-size:13px;color:#94A3B8;margin-top:4px}
.banner-amber{display:flex;gap:12px;align-items:flex-start;background:#1F2430;border:1px solid #B45309;border-radius:6px;padding:10px 16px;margin-top:14px;font-size:12px;color:#FDE68A}
.warn-ico{color:#F59E0B;font-size:15px;line-height:1.4;flex:none}
.layer-strip{display:flex;flex-wrap:wrap;gap:10px;margin-top:12px}
.top-grid{display:grid;grid-template-columns:450px 1fr;gap:20px;margin-top:24px}
.card{background:#131B28;border:1px solid #2A384F;border-radius:8px;padding:18px}
.card-tt{font-size:12px;font-weight:700;color:#38BDF8;letter-spacing:.04em;margin-bottom:10px}
.star-line{display:flex;gap:16px;align-items:center;margin-bottom:10px}
.star-big{font-size:42px;font-weight:800;color:#F59E0B;line-height:1.1}
.dim-note{font-size:12px;color:#94A3B8}
.star-label{font-size:13px;font-weight:600;color:#F1F5F9;margin-top:2px}
.conf-box{display:flex;gap:12px;background:#182232;border:1px solid #B45309;border-radius:6px;padding:12px 14px;margin-bottom:10px}
.conf-tt{font-size:14px;font-weight:700;color:#FBBF24}
.conf-note{font-size:11px;color:#94A3B8}
.adj-box,.review-box{background:#111827;border:1px solid #1F2937;border-radius:6px;padding:12px 14px;margin-bottom:10px}
.adj-tt,.review-tt,.cond-tt{font-size:12px;font-weight:700;color:#94A3B8;margin-bottom:6px}
.review-tt{color:#38BDF8}
.review-note{font-size:11px;color:#94A3B8}
.plain{list-style:none}
.plain li{font-size:11px;color:#CBD5E1;margin-bottom:4px}
.plain li::before{content:"• ";color:#64748B}
.cond-box{background:#111827;border:1px solid #1F2937;border-radius:6px;padding:12px 14px}
.cond-line{font-size:12px;font-weight:600;color:#FBBF24;margin-bottom:8px}
.cond-list li{font-size:11px}
.dims .dim-stack{display:flex;flex-direction:column;gap:8px}
.dim-row{background:#1C2638;border-radius:6px;padding:8px 12px}
.dim-head{display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
.dim-name{font-size:13px;font-weight:600;color:#F8FAFC}
.pill{font-size:12px;font-weight:600}
.pill-green{color:#34D399}.pill-amber{color:#FBBF24}.pill-slate{color:#94A3B8}.pill-red{color:#F87171}
.dim-basis{font-size:11px;color:#94A3B8;margin-top:3px}
.evi-ids{color:#64748B}
.kj-box{background:#0D131F;border:1px solid #1E293B;border-radius:6px;padding:10px 12px;margin-top:10px}
.kj-tt{font-size:12px;font-weight:700;color:#38BDF8;margin-bottom:6px}
.kj-box p{font-size:12px;color:#CBD5E1;margin-bottom:6px}
.blk{margin-top:28px}
.blk-head{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:12px}
.blk-note{font-size:12px;color:#94A3B8}
.grid-2{display:grid;grid-template-columns:1fr 1fr;gap:20px}
.grid-3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px}
.ent{background:#121D2C;border:1px solid #20334D}
.ent h3{margin:10px 0 8px}
.ent-list li{font-size:12px;margin-bottom:6px}
.ent-strip{background:#0F172A;border:1px solid #1E293B;border-radius:8px;padding:12px 18px;margin-top:20px}
.strip-top{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap}
.strip-left{display:flex;gap:10px;align-items:flex-start;font-size:12px;color:#CBD5E1}
.strip-x2{font-size:11px;color:#38BDF8}
.verify-band{display:flex;gap:10px;align-items:flex-start;background:#182232;border:1px solid #334155;border-radius:6px;padding:8px 12px;margin-top:10px;font-size:12px;color:#CBD5E1}
.led ul.evi{margin-top:10px}
.led li{margin-bottom:10px}
.evi-head{margin-bottom:2px}
.evi-title{font-size:12px;font-weight:600;color:#F1F5F9;margin:0 6px 0 6px}
.evi-links{display:inline-block;margin-left:4px}
.evi-links .ext{font-size:11px}
.evi-sup,.evi-lim{font-size:11px;color:#94A3B8}
.evi-lim{color:#F87171;background:rgba(248,113,113,.06);border-radius:4px;padding:2px 6px;display:inline-block;margin-top:2px}
.evi-note{font-size:11px;color:#64748B;margin-top:2px}
.led-hard{background:#111B24;border-color:#1E3835}
.led-soft{background:#1A181C;border-color:#3B2D26}
.led-soft .evi-lim{background:rgba(248,113,113,.08)}
.led-gap{background:#1A151C;border-color:#3B202A}
.gap-list li{font-size:12px;color:#FCA5A5}
.gap-line{font-size:12px;font-weight:700;color:#EF4444;margin:8px 0}
.x-box{background:#111827;border-radius:6px;padding:8px 10px}
.x-tt{font-size:11px;font-weight:700;color:#94A3B8;margin-bottom:4px}
.x-list li{font-size:11px}
.xid{font-weight:700;color:#FBBF24}
.hyp{background:#121927;border:1px solid #223048;border-radius:8px;padding:12px 16px;margin-bottom:10px}
.hyp-head{display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.hyp-tt{font-size:13px;font-weight:700;color:#38BDF8}
.hyp-box{border-radius:6px;padding:8px 12px;border:1px solid #26344A}
.hyp-h1{background:#1A2536}
.hyp-h2{background:#2A1C24}
.hyp-t1{font-size:12px;font-weight:600;margin-bottom:4px}
.hyp-h1 .hyp-t1{color:#34D399}
.hyp-h2 .hyp-t1{color:#F87171}
.hyp-body{font-size:12px;color:#94A3B8}
.qgrid{align-items:stretch}
.qcard{background:#121B28;border:1px solid #20334D}
.qcard .bdg{white-space:normal}
.q-text{font-size:13px;font-weight:600;color:#F8FAFC;margin:8px 0 4px}
.q-text2{font-size:12px;color:#CBD5E1;margin:8px 0 4px}
.q-intent{font-size:12px;color:#94A3B8}
.qcard-recon{background:#1E1922;border-color:#432838}
.ftr{border-top:1px solid #26344A;margin-top:28px;padding-top:16px;font-size:12px;color:#94A3B8;display:flex;flex-direction:column;gap:4px}
@media (max-width:900px){
  .wrap{padding:20px 16px}
  h1{font-size:20px}
  .top-grid,.grid-2,.grid-3{grid-template-columns:1fr}
  .grid-3{gap:12px}
  .star-big{font-size:36px}
  .blk{margin-top:22px}
  .card{padding:14px}
  .hyp{padding:10px 12px}
}
"""


def main():
    rec = load_record()
    body = (
        build_header(rec)
        + f'<div class="top-grid">{build_verdict(rec)}{build_dimensions(rec)}</div>'
        + build_entities(rec)
        + build_evidence(rec)
        + build_hypotheses(rec)
        + build_interview()
        + build_footer(rec)
    )
    doc = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>4399（四三九九）雇主调查报告 · 企业层（Sherlock Company 离线档案 v4）</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
{body}
</div>
</body>
</html>
"""
    out = CASE_DIR / "report.html"
    out.write_text(doc, encoding="utf-8")
    n_links = doc.count('class="ext"')
    print(f"OK 已生成 {out}")
    print(f"   大小 {out.stat().st_size} 字节；证据 {len(rec['evidence'])} 条；外链 {n_links} 个")


if __name__ == "__main__":
    sys.exit(main())
