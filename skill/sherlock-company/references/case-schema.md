# 案件记录 Schema

`scripts/render_report.py` 读取 UTF-8 JSON。最小结构如下：

```json
{
  "meta": {
    "company": "公司或品牌",
    "position": "岗位；未提供就明写",
    "city": "城市/团队；未提供就明写",
    "investigation_date": "YYYY-MM-DD",
    "scope": "本次实际覆盖的主体和范围"
  },
  "privacy_review": {
    "completed": true,
    "notes": "已遮盖联系方式、证件号、地址、签名和无关姓名",
    "allowed_pii": []
  },
  "identity": {
    "status": "partial",
    "headline": "品牌与企业群已识别，本次签约主体未知",
    "note": "meta.company 是展示名；需要匿名时不在展示记录里写真实主体",
    "actors": [
      {"label": "品牌", "value": "某品牌", "status": "verified", "evidence_ids": ["E1"]},
      {"label": "合同甲方", "value": "未知", "status": "unknown", "evidence_ids": []}
    ]
  },
  "decision": {
    "state": "核实后再接受",
    "basis_ids": [],
    "boundary_trigger": "",
    "remaining_gaps_material": true,
    "headline": "一句话结论",
    "reason": "为什么",
    "next_move": "立即做什么"
  },
  "verified": [{"title": "事实", "detail": "范围和意义", "evidence_ids": ["E1"]}],
  "signals": [{"title": "线索或冲突", "detail": "不确定性", "evidence_ids": ["E2"]}],
  "conflicts": [{"title": "相互冲突的说法", "detail": "两边的适用范围与不足", "evidence_ids": ["E3", "E4"]}],
  "unknowns": [{"title": "未知项", "impact": "对决定的影响", "next_check": "如何核实"}],
  "concerns": [{
    "title": "用户关心的问题",
    "status": "unknown",
    "known": "已知",
    "unknown": "未知",
    "impact": "影响",
    "next_check": "下一步",
    "evidence_ids": []
  }],
  "employee_experience": {
    "coverage": "none",
    "scope": "目标城市、职能和团队",
    "evidence_ids": [],
    "summary": "当前覆盖",
    "can_say": "能说什么",
    "cannot_say": "不能说什么",
    "next_steps": ["便宜的补证路线"]
  },
  "checklist": [{
    "stage": "HR 最终沟通前",
    "item": "要核实的事",
    "ask": "可复制问法",
    "evidence_to_get": "应取得的书面材料",
    "warning": "需警惕的回复"
  }],
  "materials": [{"name": "Offer", "status": "missing", "use": "核对签约主体与薪酬"}],
  "sources": [{
    "id": "E1",
    "title": "来源名称",
    "url": "https://example.com",
    "access_status": "accessed",
    "evidence_kind": "corporate_identity",
    "source_type": "官方原文",
    "subject": "适用主体",
    "event_date": "事件/发布日期",
    "retrieved_at": "取证日期",
    "supports": "能证明什么",
    "limits": "不能证明什么",
    "status": "verified"
  }],
  "coverage_gaps": ["未覆盖渠道及其影响"]
}
```

`identity.status` 可用 `confirmed` / `partial` / `unresolved`；其它 `status` 可用 `verified` / `signal` / `conflict` / `unknown`；`materials.status` 可用 `provided` / `missing` / `not_applicable`；`employee_experience.coverage` 可用 `none` / `limited` / `adequate`。`access_status` 可用 `accessed` / `local` / `blocked` / `login_required` / `not_found` / `failed`；无 URL 或本地原文需提供 `locator`。

`evidence_kind` 可用 `corporate_identity` / `company_promise` / `operating` / `legal` / `employee_experience` / `user_offer_material` / `media` / `other`。`privacy_review.completed` 必须为 `true` 才能渲染；明显手机号、身份证、银行卡或邮箱会被拒绝，仅可把经人工复核必须保留的公开业务信息逐项写入 `allowed_pii: [{"value":"...", "reason":"..."}]`。

`employee_experience.coverage` 为 `limited` 或 `adequate` 时必须有 `evidence_kind=employee_experience` 的已登记来源；为 `none` 时 `evidence_ids` 应为空。`decision.state=先不接受` 必须提供已证实的 `basis_ids` 和 `boundary_trigger`；`decision.state=已足够决定` 要求所有关切均有证据且 `remaining_gaps_material=false`。

QCC 来源可额外记录 `provider: "企查查"`、`tool_code`、`updated_as_of`；展示时仍与推理分开。

## 默认预警的记录方式

新调查须按 [company-warnings.md](company-warnings.md) 检查并在 `concerns` 前部保留“规模与初创”“感恩与业绩标语”“居民楼办公”三类结果，与重复的用户关切合并。任一触发时在 `decision.reason` 提醒，并加入对应 `checklist` 核实问题。人数与初创是独立条件，规模卡应分别说明两者。

卡片标题用“预警：…”或“待核实预警：…”区分依据强度，`status` 仍只用四态，不填 `warning`。例如标题“待核实预警：注册地址在居民楼，实际办公地未知”可用 `signal`，而单独已核实的注册地址事实放入 `verified`；没有任何地址依据时卡片为 `unknown`。每项引用已登记的 `evidence_ids`，缺证时为空并写明补证路线。

这是调查内容要求，不是新增结构字段。渲染器仅校验结构与证据引用，不能自动判断人数、初创阶段或图片内容；旧案仍可渲染，不代表已经补查这三类预警。
