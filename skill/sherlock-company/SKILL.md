---
name: sherlock-company
description: Use when a job seeker wants to investigate a company, role, JD, Offer, or HR claims before deciding whether to continue interviewing or accept an offer, especially when evidence is incomplete or employee experience is hard to obtain.
---

# Sherlock Company

Help the user answer three questions: what is verified, what remains unknown, and what must be checked before accepting the Offer. The deliverable is a decision aid, not a corporate verdict.

## Start from the decision

Collect or infer only what the user supplied: company/brand, role, city or team, decision deadline, concerns, and available JD/Offer/HR materials. Search public evidence by default. Ask the user only when company identity remains ambiguous or a missing preference would materially change the decision.

Anchor the legal employer before investigating. Treat brand, parent company, recruiting entity, contract entity, payroll entity, social-insurance entity, city, and team as separate fields. A famous brand never proves the user's contracting entity.

If identity remains unresolved, still produce a clearly labeled **stage report** containing candidate entities, missing identifiers, generic material checks, and the next question. Do not attach company-specific findings to an unconfirmed candidate. Keep the exact research identity separate from the display name when the user asks for an anonymized report.

## Build one evidence record

Read [references/evidence-contract.md](references/evidence-contract.md) before research or analysis. Keep every claim in one of four states: `verified`, `signal`, `conflict`, or `unknown`. Record access failure separately; zero results never mean zero risk.

Use primary sources first, then reliable reporting, then user-supplied experience material. A company's own site can prove what it promises, not that it consistently delivers. Search snippets, AI summaries, scraped aggregations, and anonymous posts are leads until their original context is checked.

When legal or employment rules matter, verify current authoritative sources and keep them separate from company-specific facts. Do not turn a legal minimum into proof of actual company practice.

## Choose tools narrowly

Use ordinary web research for public sources. If an official QCC MCP or CLI is available, read [references/qcc.md](references/qcc.md) and use it only for exact entity, corporate, operating, public-risk, or legal-record facts. QCC is optional and never a substitute for employee experience.

If the user supplies JD, Offer, contract drafts, HR chat, or review screenshots, read [references/user-materials.md](references/user-materials.md). Ask for redaction of phone numbers, IDs, addresses, bank details, signatures, and unrelated names before analysis.

If employee experience cannot be obtained, read [references/employee-experience.md](references/employee-experience.md). Do not manufacture an experience score, completeness percentage, or sample-size threshold.

## Decide without fake precision

Default to a plain-language state:

- `可以继续聊`：no confirmed deal-breaker, but material unknowns remain.
- `核实后再接受`：contract, compensation, probation, work pattern, or team evidence is still decision-critical.
- `已足够决定`：the user's concerns have current, relevant evidence and the remaining gaps are not material.
- `先不接受`：a verified fact crosses a boundary the user actually stated.

Never derive a star rating or numeric confidence/completeness score unless the user explicitly requests a defined scoring model and the record supports it. Unknown is not negative evidence. A red flag is a verified fact or a refusal/inconsistency in the user's actual process, not merely missing web coverage.

Move from `核实后再接受` to `先不接受` only when a verified fact crosses the user's stated boundary, written terms conflict on a decision-critical condition and the conflict is not resolved, or the responsible party refuses to confirm a decision-critical item before the deadline. Move to `已足够决定` only when each stated concern is answered with relevant evidence and remaining gaps would not change the user's choice.

If the user explicitly requests scoring, define dimensions, weights, hard boundaries, and missing-value treatment before calculating. Keep unknowns unknown, show the unweighted facts alongside the score, and include sensitivity to any subjective weight. Do not silently reuse a company-level score as an Offer-level score.

## Deliver the report

Lead with one sentence the user can act on. Then show:

1. the exact company/role/scope checked;
2. verified facts, leads/conflicts, and unknowns in separate groups;
3. one card per user concern: known, unknown, impact, and next check;
4. an Offer-stage checklist with copyable questions and desired evidence;
5. employee-experience coverage and the next feasible evidence route;
6. source ledger, dates, scope, limits, and blocked channels.

For HTML, read [references/html-report.md](references/html-report.md), fill the case schema in [references/case-schema.md](references/case-schema.md), then run `scripts/render_report.py`. The renderer loads `assets/report-v2.css` by default; standalone sample pages are visual references, not executable templates. Keep Markdown and HTML derived from the same record. Use the detective IP as a visual guide, not as a source of theatrical claims.

Write visible interface text and case conclusions in natural Chinese. Prefer “职位说明”“录用通知”“招聘人员” over unexplained `JD` / `Offer` / `HR`. Keep English only when it is part of a legal entity name, source title, URL, product name, or a necessary term that is explained on first use. Do not add decorative English labels.

Stop when the identity is resolved or explicitly blocked, each concern has a result or named gap, decisive claims have sources and counterchecks, and the next actions are specific enough to use before the deadline.
