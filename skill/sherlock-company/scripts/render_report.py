#!/usr/bin/env python3
"""Render a Sherlock Company case JSON as a self-contained offline HTML report."""

from __future__ import annotations

import argparse
import base64
import html
import json
import mimetypes
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse


HERE = Path(__file__).resolve().parent
DEFAULT_IP = HERE.parent / "assets" / "sherlock_ip_pop.jpg"
DEFAULT_STYLE = HERE.parent / "assets" / "report-v2.css"
TEMPLATE_ID = "evidence-dossier-v2"
ALLOWED_STATUSES = {"verified", "signal", "conflict", "unknown"}
DECISION_STATES = {"可以继续聊", "核实后再接受", "已足够决定", "先不接受"}
ACCESS_LABELS = {
    "accessed": "原文已读",
    "local": "本地原文",
    "blocked": "访问受限",
    "login_required": "需登录",
    "not_found": "未发现记录",
    "failed": "调用失败",
}
EVIDENCE_KINDS = {
    "corporate_identity",
    "company_promise",
    "operating",
    "legal",
    "employee_experience",
    "user_offer_material",
    "media",
    "other",
}
PII_PATTERNS = {
    "中国大陆手机号": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
    "身份证号": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    "银行卡号": re.compile(r"(?<!\d)(?:\d[ -]?){15,18}\d(?!\d)"),
    "邮箱": re.compile(r"(?<![\w.+-])[\w.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?![\w.-])"),
}
STATUS_LABELS = {
    "verified": "已证实",
    "signal": "有线索",
    "conflict": "说法冲突",
    "unknown": "还不知道",
}
MATERIAL_LABELS = {
    "provided": "已收到",
    "missing": "待补充",
    "not_applicable": "不适用",
}
IDENTITY_STATUS_LABELS = {
    "confirmed": "已确认",
    "partial": "部分确认",
    "unresolved": "未确认",
}
EVIDENCE_KIND_LABELS = {
    "corporate_identity": "主体与工商",
    "company_promise": "官方承诺",
    "operating": "经营动态",
    "legal": "法定规则",
    "employee_experience": "员工体验",
    "user_offer_material": "用户材料",
    "media": "媒体报道",
    "other": "其它",
}
EXPERIENCE_LABELS = {
    "none": "未取得目标团队体验",
    "limited": "有少量相关线索",
    "adequate": "已取得较相关的体验材料",
}


def e(value: object) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_record(record: dict) -> list[str]:
    errors: list[str] = []
    require(isinstance(record, dict), "根节点必须是 JSON object", errors)
    if not isinstance(record, dict):
        return errors

    meta = record.get("meta")
    require(isinstance(meta, dict), "meta 必须是 object", errors)
    if isinstance(meta, dict):
        for key in ("company", "position", "city", "investigation_date", "scope"):
            require(bool(str(meta.get(key, "")).strip()), f"meta.{key} 不能为空", errors)

    decision = record.get("decision")
    require(isinstance(decision, dict), "decision 必须是 object", errors)
    if isinstance(decision, dict):
        for key in ("state", "headline", "reason", "next_move"):
            require(bool(str(decision.get(key, "")).strip()), f"decision.{key} 不能为空", errors)
        require(decision.get("state") in DECISION_STATES, f"decision.state 必须是四种决策状态之一：{sorted(DECISION_STATES)}", errors)
        require(isinstance(decision.get("basis_ids"), list), "decision.basis_ids 必须是 array", errors)
        require(isinstance(decision.get("remaining_gaps_material"), bool), "decision.remaining_gaps_material 必须是 boolean", errors)

    privacy = record.get("privacy_review")
    require(isinstance(privacy, dict), "privacy_review 必须是 object", errors)
    if isinstance(privacy, dict):
        require(privacy.get("completed") is True, "privacy_review.completed 必须为 true 后才能渲染", errors)
        require(bool(str(privacy.get("notes", "")).strip()), "privacy_review.notes 不能为空", errors)
        allowed_pii = privacy.get("allowed_pii", [])
        require(isinstance(allowed_pii, list), "privacy_review.allowed_pii 必须是 array", errors)
        allowed_values: set[str] = set()
        if isinstance(allowed_pii, list):
            for index, item in enumerate(allowed_pii):
                require(isinstance(item, dict), f"privacy_review.allowed_pii[{index}] 必须是 object", errors)
                if isinstance(item, dict):
                    value = str(item.get("value", "")).strip()
                    reason = str(item.get("reason", "")).strip()
                    require(bool(value), f"privacy_review.allowed_pii[{index}].value 不能为空", errors)
                    require(bool(reason), f"privacy_review.allowed_pii[{index}].reason 不能为空", errors)
                    if value:
                        allowed_values.add(value)
        pii_payload = json.dumps({key: value for key, value in record.items() if key != "privacy_review"}, ensure_ascii=False)
        for value in allowed_values:
            pii_payload = pii_payload.replace(value, "[ALLOWED_PII]")
        for label, pattern in PII_PATTERNS.items():
            matches = sorted(set(pattern.findall(pii_payload)))
            if matches:
                require(False, f"发现疑似{label}，请脱敏或在 allowed_pii 中逐项说明：{matches[:3]}", errors)

    for key in ("verified", "signals", "conflicts", "unknowns", "concerns", "checklist", "materials", "sources", "coverage_gaps"):
        require(isinstance(record.get(key), list), f"{key} 必须是 array", errors)

    ids: set[str] = set()
    source_statuses: dict[str, str] = {}
    for index, source in enumerate(record.get("sources", [])):
        require(isinstance(source, dict), f"sources[{index}] 必须是 object", errors)
        if not isinstance(source, dict):
            continue
        source_id = str(source.get("id", "")).strip()
        require(bool(source_id), f"sources[{index}].id 不能为空", errors)
        require(source_id not in ids, f"来源 id 重复: {source_id}", errors)
        ids.add(source_id)
        for key in ("title", "source_type", "subject", "event_date", "retrieved_at", "supports", "limits"):
            require(bool(str(source.get(key, "")).strip()), f"{source_id or index}.{key} 不能为空", errors)
        status = source.get("status", "unknown")
        require(status in ALLOWED_STATUSES, f"{source_id or index} 状态无效: {status}", errors)
        source_statuses[source_id] = status
        access_status = source.get("access_status")
        require(access_status in ACCESS_LABELS, f"{source_id or index}.access_status 无效", errors)
        url = str(source.get("url", "")).strip()
        if url:
            require(urlparse(url).scheme in {"http", "https"}, f"{source_id or index} URL 只允许 http/https", errors)
        if access_status == "local":
            require(bool(str(source.get("locator", "")).strip()), f"{source_id or index} 为本地原文时必须提供 locator", errors)
        if not url and access_status != "local":
            require(bool(str(source.get("locator", "")).strip()), f"{source_id or index} 无 URL 时必须提供 locator", errors)
        evidence_kind = source.get("evidence_kind")
        require(evidence_kind in EVIDENCE_KINDS, f"{source_id or index}.evidence_kind 无效", errors)
        if status == "verified":
            require(access_status in {"accessed", "local"}, f"{source_id or index} 为 verified 时 access_status 必须是 accessed/local", errors)

    if isinstance(decision, dict) and isinstance(decision.get("basis_ids"), list):
        for source_id in decision.get("basis_ids", []):
            require(source_id in ids, f"decision.basis_ids 引用了未登记来源: {source_id}", errors)
        if decision.get("state") == "先不接受":
            require(bool(decision.get("basis_ids")), "decision.state 为先不接受时必须提供 verified basis_ids", errors)
            require(bool(str(decision.get("boundary_trigger", "")).strip()), "decision.state 为先不接受时必须说明 boundary_trigger", errors)
            for source_id in decision.get("basis_ids", []):
                if source_id in source_statuses:
                    require(source_statuses[source_id] == "verified", f"先不接受的依据 {source_id} 必须是 verified", errors)

    for section in ("verified", "signals", "conflicts"):
        for index, item in enumerate(record.get(section, [])):
            require(isinstance(item, dict), f"{section}[{index}] 必须是 object", errors)
            if not isinstance(item, dict):
                continue
            for key in ("title", "detail"):
                require(bool(str(item.get(key, "")).strip()), f"{section}[{index}].{key} 不能为空", errors)
            evidence_ids = item.get("evidence_ids", [])
            require(isinstance(evidence_ids, list), f"{section}[{index}].evidence_ids 必须是 array", errors)
            if isinstance(evidence_ids, list):
                for source_id in evidence_ids:
                    require(source_id in ids, f"{section}[{index}] 引用了未登记来源: {source_id}", errors)
                    if section == "verified" and source_id in source_statuses:
                        require(source_statuses[source_id] == "verified", f"{section}[{index}] 不能把非 verified 来源 {source_id} 用作已证实事实", errors)

    identity = record.get("identity")
    require(isinstance(identity, dict), "identity 必须是 object", errors)
    if isinstance(identity, dict):
        require(identity.get("status") in {"confirmed", "partial", "unresolved"}, "identity.status 无效", errors)
        require(bool(str(identity.get("headline", "")).strip()), "identity.headline 不能为空", errors)
        actors = identity.get("actors")
        require(isinstance(actors, list), "identity.actors 必须是 array", errors)
        if isinstance(actors, list):
            for index, actor in enumerate(actors):
                require(isinstance(actor, dict), f"identity.actors[{index}] 必须是 object", errors)
                if not isinstance(actor, dict):
                    continue
                require(actor.get("status") in ALLOWED_STATUSES, f"identity.actors[{index}].status 无效", errors)
                for key in ("label", "value"):
                    require(bool(str(actor.get(key, "")).strip()), f"identity.actors[{index}].{key} 不能为空", errors)
                evidence_ids = actor.get("evidence_ids", [])
                require(isinstance(evidence_ids, list), f"identity.actors[{index}].evidence_ids 必须是 array", errors)
                if isinstance(evidence_ids, list):
                    for source_id in evidence_ids:
                        require(source_id in ids, f"identity.actors[{index}] 引用了未登记来源: {source_id}", errors)
                        if actor.get("status") == "verified" and source_id in source_statuses:
                            require(source_statuses[source_id] == "verified", f"identity.actors[{index}] 不能把非 verified 来源 {source_id} 用作已证实主体", errors)

        if identity.get("status") == "unresolved":
            require(not record.get("verified"), "identity.status 为 unresolved 时不得生成公司级 verified 结论", errors)
            require(not record.get("signals"), "identity.status 为 unresolved 时不得生成公司级 signals 结论", errors)
            require(not record.get("conflicts"), "identity.status 为 unresolved 时不得生成公司级 conflicts 结论", errors)
            if isinstance(decision, dict):
                require(decision.get("state") in {"可以继续聊", "核实后再接受"}, "主体 unresolved 时决策只能是可以继续聊/核实后再接受", errors)

    for index, item in enumerate(record.get("unknowns", [])):
        require(isinstance(item, dict), f"unknowns[{index}] 必须是 object", errors)
        if isinstance(item, dict):
            for key in ("title", "impact", "next_check"):
                require(bool(str(item.get(key, "")).strip()), f"unknowns[{index}].{key} 不能为空", errors)

    for index, concern in enumerate(record.get("concerns", [])):
        require(isinstance(concern, dict), f"concerns[{index}] 必须是 object", errors)
        if isinstance(concern, dict):
            status = concern.get("status", "unknown")
            require(status in ALLOWED_STATUSES, f"concerns[{index}].status 无效: {status}", errors)
            for key in ("title", "known", "unknown", "impact", "next_check"):
                require(bool(str(concern.get(key, "")).strip()), f"concerns[{index}].{key} 不能为空", errors)
            evidence_ids = concern.get("evidence_ids", [])
            require(isinstance(evidence_ids, list), f"concerns[{index}].evidence_ids 必须是 array", errors)
            if isinstance(evidence_ids, list):
                for source_id in evidence_ids:
                    require(source_id in ids, f"concerns[{index}] 引用了未登记来源: {source_id}", errors)

    for index, item in enumerate(record.get("checklist", [])):
        require(isinstance(item, dict), f"checklist[{index}] 必须是 object", errors)
        if isinstance(item, dict):
            for key in ("stage", "item", "ask", "evidence_to_get", "warning"):
                require(bool(str(item.get(key, "")).strip()), f"checklist[{index}].{key} 不能为空", errors)

    for index, item in enumerate(record.get("materials", [])):
        require(isinstance(item, dict), f"materials[{index}] 必须是 object", errors)
        if isinstance(item, dict):
            require(item.get("status") in MATERIAL_LABELS, f"materials[{index}].status 无效", errors)
            for key in ("name", "use"):
                require(bool(str(item.get(key, "")).strip()), f"materials[{index}].{key} 不能为空", errors)

    experience = record.get("employee_experience")
    require(isinstance(experience, dict), "employee_experience 必须是 object", errors)
    if isinstance(experience, dict):
        require(experience.get("coverage") in EXPERIENCE_LABELS, "employee_experience.coverage 无效", errors)
        for key in ("scope", "summary", "can_say", "cannot_say"):
            require(bool(str(experience.get(key, "")).strip()), f"employee_experience.{key} 不能为空", errors)
        evidence_ids = experience.get("evidence_ids")
        require(isinstance(evidence_ids, list), "employee_experience.evidence_ids 必须是 array", errors)
        if isinstance(evidence_ids, list):
            for source_id in evidence_ids:
                require(source_id in ids, f"employee_experience 引用了未登记来源: {source_id}", errors)
            if experience.get("coverage") in {"limited", "adequate"}:
                require(bool(evidence_ids), "employee_experience.coverage 为 limited/adequate 时必须提供 evidence_ids", errors)
                for source_id in evidence_ids:
                    source = next((item for item in record.get("sources", []) if item.get("id") == source_id), {})
                    require(source.get("evidence_kind") == "employee_experience", f"员工体验覆盖不能引用非 employee_experience 来源 {source_id}", errors)
                    if experience.get("coverage") == "adequate":
                        require(source.get("access_status") in {"accessed", "local"}, f"adequate 员工体验来源 {source_id} 必须为 accessed/local", errors)
            if experience.get("coverage") == "none":
                require(not evidence_ids, "employee_experience.coverage 为 none 时 evidence_ids 应为空", errors)
        require(isinstance(experience.get("next_steps"), list), "employee_experience.next_steps 必须是 array", errors)

    if isinstance(decision, dict) and decision.get("state") == "已足够决定":
        require(decision.get("remaining_gaps_material") is False, "已足够决定时 remaining_gaps_material 必须为 false", errors)
        if isinstance(identity, dict):
            require(identity.get("status") != "unresolved", "已足够决定时主体不能 unresolved", errors)
        for index, concern in enumerate(record.get("concerns", [])):
            if isinstance(concern, dict):
                require(concern.get("status") != "unknown", f"已足够决定时 concerns[{index}] 不能为 unknown", errors)
                require(bool(concern.get("evidence_ids")), f"已足够决定时 concerns[{index}] 必须有 evidence_ids", errors)

    return errors


def image_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def badge(status: str) -> str:
    return f'<span class="status status-{e(status)}">{e(STATUS_LABELS.get(status, status))}</span>'


def chips(ids: list[str] | None) -> str:
    if not ids:
        return ""
    return '<div class="chips">' + "".join(f'<span class="chip">{e(item)}</span>' for item in ids) + "</div>"


def safe_link(url: str, label: str) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"不安全的 URL: {url}")
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(label)} ↗</a>'


def render_summary_list(items: list[dict], kind: str) -> str:
    if not items:
        return '<p class="empty">本类暂无记录。</p>'
    rows = []
    for item in items:
        if kind == "unknown":
            rows.append(
                f"""<article class="evidence-row">
                  <h4>{e(item.get('title'))}</h4>
                  <p><strong>为什么重要：</strong>{e(item.get('impact'))}</p>
                  <p><strong>怎么补：</strong>{e(item.get('next_check'))}</p>
                </article>"""
            )
        else:
            rows.append(
                f"""<article class="evidence-row">
                  <h4>{e(item.get('title'))}</h4>
                  <p>{e(item.get('detail'))}</p>
                  {chips(item.get('evidence_ids'))}
                </article>"""
            )
    return "".join(rows)


def render_concerns(concerns: list[dict]) -> str:
    cards = []
    for number, item in enumerate(concerns, 1):
        status = item.get("status", "unknown")
        cards.append(
            f"""<article class="concern-card status-edge-{e(status)}">
              <div class="concern-top"><span class="number">{number:02d}</span>{badge(status)}</div>
              <h3>{e(item.get('title'))}</h3>
              <dl>
                <div><dt>已知</dt><dd>{e(item.get('known'))}</dd></div>
                <div><dt>未知</dt><dd>{e(item.get('unknown'))}</dd></div>
                <div><dt>对你的影响</dt><dd>{e(item.get('impact'))}</dd></div>
                <div class="next"><dt>下一步</dt><dd>{e(item.get('next_check'))}</dd></div>
              </dl>
              {chips(item.get('evidence_ids'))}
            </article>"""
        )
    return "".join(cards)


def render_identity(identity: dict) -> str:
    cards = []
    for actor in identity.get("actors", []):
        status = actor.get("status", "unknown")
        cards.append(
            f"""<article class="actor actor-{e(status)}">
              <div class="actor-label">{e(actor.get('label'))}</div>
              <div class="actor-value">{e(actor.get('value'))}</div>
              <div class="actor-foot">{badge(status)}{chips(actor.get('evidence_ids'))}</div>
            </article>"""
        )
    return "".join(cards)


def render_checklist(items: list[dict]) -> str:
    groups: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        groups[str(item.get("stage", "接受 Offer 前"))].append(item)
    rendered = []
    count = 0
    for stage, stage_items in groups.items():
        cards = []
        for item in stage_items:
            count += 1
            cards.append(
                f"""<article class="check-card">
                  <div class="check-head"><span class="check-box" aria-hidden="true"></span><h4>{e(item.get('item'))}</h4></div>
                  <div class="ask"><span>可以直接问</span><p>{e(item.get('ask'))}</p></div>
                  <p><strong>要到的材料：</strong>{e(item.get('evidence_to_get'))}</p>
                  <p class="warning"><strong>需警惕：</strong>{e(item.get('warning'))}</p>
                </article>"""
            )
        rendered.append(f'<section class="stage"><h3>{e(stage)}</h3><div class="check-grid">{"".join(cards)}</div></section>')
    return "".join(rendered)


def render_materials(items: list[dict]) -> str:
    rows = []
    for item in items:
        status = item.get("status", "missing")
        rows.append(
            f"""<li>
              <span class="material-state material-{e(status)}">{e(MATERIAL_LABELS.get(status, status))}</span>
              <div><strong>{e(item.get('name'))}</strong><p>{e(item.get('use'))}</p></div>
            </li>"""
        )
    return "".join(rows)


def render_sources(items: list[dict]) -> str:
    rows = []
    for item in items:
        status = item.get("status", "unknown")
        metadata = [
            item.get("source_type"),
            item.get("subject"),
            f"发布/事件 {item.get('event_date')}" if item.get("event_date") else "",
            f"取证 {item.get('retrieved_at')}" if item.get("retrieved_at") else "",
            f"更新口径 {item.get('updated_as_of')}" if item.get("updated_as_of") else "",
            f"数据方 {item.get('provider')}" if item.get("provider") else "",
            f"工具 {item.get('tool_code')}" if item.get("tool_code") else "",
            f"证据类型 {EVIDENCE_KIND_LABELS.get(str(item.get('evidence_kind')), item.get('evidence_kind'))}" if item.get("evidence_kind") else "",
        ]
        metadata = " · ".join(e(x) for x in metadata if x)
        access = ACCESS_LABELS.get(str(item.get("access_status", "failed")), str(item.get("access_status", "")))
        if item.get("url"):
            location = safe_link(str(item.get("url", "")), "打开原文")
        elif item.get("locator"):
            location = f'<span class="no-link">定位：{e(item.get("locator"))}</span>'
        else:
            location = '<span class="no-link">无可用定位</span>'
        rows.append(
            f"""<details class="source">
              <summary><span class="source-id">{e(item.get('id'))}</span><span class="source-title">{e(item.get('title'))}</span>{badge(status)}</summary>
              <div class="source-body">
                <p class="source-meta">访问状态：{e(access)} · {metadata}</p>
                <p><strong>能证明：</strong>{e(item.get('supports'))}</p>
                <p><strong>不能证明：</strong>{e(item.get('limits'))}</p>
                <p>{location}</p>
              </div>
            </details>"""
        )
    return "".join(rows)


def render(record: dict, image_uri: str, stylesheet: str | None = None) -> str:
    meta = record["meta"]
    decision = record["decision"]
    identity = record["identity"]
    experience = record["employee_experience"]
    privacy = record["privacy_review"]
    verified_count = len(record.get("verified", []))
    signal_count = len(record.get("signals", []))
    conflict_count = len(record.get("conflicts", []))
    unknown_count = len(record.get("unknowns", []))
    ip_html = f'<img src="{image_uri}" alt="戴猎鹿帽、手持放大镜的小夏侦探公仔">' if image_uri else '<div class="ip-fallback">小夏<br>侦探</div>'
    experience_steps = "".join(f"<li>{e(item)}</li>" for item in experience.get("next_steps", []))
    gaps = "".join(f"<li>{e(item)}</li>" for item in record.get("coverage_gaps", [])) or "<li>无额外缺口记录。</li>"
    title = f"{e(meta['company'])} | {e(meta['position'])} | 录用前核实报告"
    stylesheet = stylesheet if stylesheet is not None else DEFAULT_STYLE.read_text("utf-8")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <meta name="description" content="{e(meta['company'])}的录用前证据核实报告">
  <meta name="generator" content="Sherlock Company {TEMPLATE_ID}">
  <title>{title}</title>
  <style>{stylesheet}</style>
</head>
<body data-template="{TEMPLATE_ID}">
<a class="skip-link" href="#main-content">跳到主要内容</a>
<main class="page" id="main-content">
  <div class="hero-wrap">
    <header class="hero">
      <figure class="ip">{ip_html}<figcaption><span>小夏证据侦探</span><span>公开证据版</span></figcaption></figure>
      <div>
        <span class="eyebrow">小夏企业调查 · 接受录用前核实</span>
        <h1>{e(meta['company'])}<br>{e(meta['position'])}</h1>
        <p class="hero-lede">这份报告分清已经查到的事实、仍缺的信息，以及接受录用前必须问清的事。</p>
        <div class="meta"><span><b>城市或团队</b>{e(meta['city'])}</span><span><b>调查日期</b>{e(meta['investigation_date'])}</span><span><b>调查范围</b>{e(meta['scope'])}</span></div>
      </div>
    </header>
  </div>

  <section class="decision" aria-labelledby="decision-title">
    <div><div class="decision-kicker">小夏的当前结论：{e(decision['state'])}</div><h2 id="decision-title">{e(decision['headline'])}</h2><p class="decision-reason">{e(decision['reason'])}</p><div class="next-move"><strong>现在先做：</strong>{e(decision['next_move'])}</div></div>
    <div class="stats"><div class="stat"><strong>{verified_count}</strong><span>条已证实</span></div><div class="stat"><strong>{signal_count}</strong><span>条待核实线索</span></div><div class="stat"><strong>{conflict_count}</strong><span>组冲突说法</span></div><div class="stat"><strong>{unknown_count}</strong><span>个重要未知</span></div></div>
  </section>

  <section class="identity" aria-labelledby="identity-title">
    <div class="identity-head"><div><h2 id="identity-title">先确认“谁在招你”</h2><p>{e(identity.get('headline'))}</p></div><span class="identity-state">主体确认到哪一步：{e(IDENTITY_STATUS_LABELS.get(identity.get('status', ''), identity.get('status', '')))}</span></div>
    <div class="actor-grid">{render_identity(identity)}</div>
    <p class="source-meta">{e(identity.get('note'))}</p>
  </section>

  <section class="section">
    <div class="section-head"><div><h2>证据分盒</h2><p>未知不是负面；线索也还不是事实。</p></div></div>
    <div class="evidence-grid"><div class="tray"><h3><span class="dot dot-ok"></span>已证实</h3>{render_summary_list(record['verified'], 'verified')}</div><div class="tray"><h3><span class="dot dot-signal"></span>有线索</h3>{render_summary_list(record['signals'], 'signal')}</div><div class="tray"><h3><span class="dot dot-conflict"></span>说法冲突</h3>{render_summary_list(record['conflicts'], 'conflict')}</div><div class="tray"><h3><span class="dot dot-unknown"></span>还不知道</h3>{render_summary_list(record['unknowns'], 'unknown')}</div></div>
  </section>

  <section class="section">
    <div class="section-head"><div><h2>你最关心的问题</h2><p>每张卡只回答一件事：现在知道什么，接下来怎么查。</p></div></div>
    <div class="concern-grid">{render_concerns(record['concerns'])}</div>
  </section>

  <section class="section">
    <div class="section-head"><div><h2>有没有目标团队的真实体验</h2><p>工商和司法数据可以补主体与公开风险，但不能代替目标团队员工的实际经历。</p></div></div>
    <div class="experience"><article class="experience-card"><span class="status">{e(EXPERIENCE_LABELS.get(experience['coverage'], experience['coverage']))}</span><h3>{e(experience.get('summary'))}</h3><p><strong>适用范围：</strong>{e(experience.get('scope'))}</p><p><strong>目前能说：</strong>{e(experience.get('can_say'))}</p><p><strong>目前不能说：</strong>{e(experience.get('cannot_say'))}</p>{chips(experience.get('evidence_ids'))}</article><article class="experience-actions"><h3>接下来怎么补证</h3><ol>{experience_steps}</ol></article></div>
  </section>

  <section class="section">
    <div class="section-head"><div><h2>接受录用前的核实清单</h2><p>只问对方能够具体回答的事，并尽量拿到书面版本。</p></div></div>
    {render_checklist(record['checklist'])}
  </section>

  <section class="section records">
    <article class="panel"><h2>这次拿到了什么材料</h2><ul class="materials">{render_materials(record['materials'])}</ul><div class="next-move"><strong>隐私复核已完成：</strong>{e(privacy.get('notes'))}</div><h3>还缺什么</h3><ul class="gaps">{gaps}</ul></article>
    <article class="panel"><h2>这些结论从哪里来</h2><p>展开每条来源，可以查看它能证明什么，以及它的局限。</p>{render_sources(record['sources'])}</article>
  </section>

  <footer>Sherlock Company 小夏企业调查 | 这份报告只提供基于当前证据的决策参考，不保证企业、法律或个人职业结果。</footer>
</main>
</body>
</html>"""


def main() -> int:
    parser = argparse.ArgumentParser(description="将 Sherlock Company 案件 JSON 渲染为离线 HTML")
    parser.add_argument("input", type=Path, help="案件 JSON")
    parser.add_argument("--output", "-o", type=Path, default=None, help="输出 HTML；仅校验时可省略")
    parser.add_argument("--ip-image", type=Path, default=DEFAULT_IP, help="要嵌入的侦探 IP 图")
    parser.add_argument("--style", type=Path, default=DEFAULT_STYLE, help="要嵌入的报告样式模板")
    parser.add_argument("--validate-only", action="store_true", help="只校验 JSON，不写输出")
    args = parser.parse_args()
    if args.output is None and not args.validate_only:
        parser.error("渲染时必须提供 --output（或改用 --validate-only）")

    try:
        record = json.loads(args.input.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"ERROR: 无法读取 {args.input}: {exc}", file=sys.stderr)
        return 2

    errors = validate_record(record)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.validate_only:
        print(f"OK: {args.input} 结构有效")
        return 0

    try:
        output = render(record, image_data_uri(args.ip_image), args.style.read_text("utf-8"))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, "utf-8")
    except (OSError, ValueError) as exc:
        print(f"ERROR: 渲染失败: {exc}", file=sys.stderr)
        return 2

    print(f"OK: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
