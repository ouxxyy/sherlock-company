# 企查查 MCP / CLI / OpenAPI：官方一手资料核验

> 核验日期：2026-09-28（Asia/Shanghai）  
> 来源边界：仅访问 `agent.qcc.com`、其官方导航直接链接的 `openapi.qcc.com`，以及这些页面明确链接的企查查官方站点；未访问第三方教程、社区帖子或第三方包页面。  
> 安全边界：未注册账号、未登录、未获取或记录任何 API Key，未安装软件，也未发起真实数据调用。

## 结论先行

- **已证实**：企查查智能体数据平台同时提供 MCP 与 CLI，两者共用同一 API Key 和权益额度。MCP 公开配置包含 10 个核心远端 Server；智能文档解析另有一个本地 `npx` 入口，并不意味着多出一个“核心 Server”。官方总览称当前为 **4 大领域、10 个核心 Server、203 个工具**。[平台首页](https://agent.qcc.com/)｜[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)
- **已证实**：远端 MCP 通过 HTTP `Authorization: Bearer YOUR_API_KEY` 鉴权；CLI 用 `qcc init --authorization "Bearer YOUR_API_KEY"` 绑定；本地文档解析 MCP 用环境变量 `QCC_DOCUMENT_AUTHORIZATION` 传同样的 Bearer 凭证。[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)
- **已证实**：CLI 官方安装命令是 `npm install -g qcc-agent-cli`；本地文档解析入口是 `npx -y qcc-document-mcp`，且官方明确要求 **Node.js 20+**。远端 MCP 不需要安装本地企查查包，只需在兼容 MCP 的客户端配置 URL 与请求头。[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)
- **已证实**：企查查开放平台 OpenAPI 是另一套直接 REST 接入方式，不要求安装 `qcc-agent-cli`。其公开接口页使用 `api.qichacha.com` 接口地址，查询参数携带 `key=AppKey`，请求头携带 `Timespan` 与 `Token=MD5(key+Timespan+SecretKey)`（32 位大写）。[开放平台常见问题](https://openapi.qcc.com/services/after/faq)｜[企业三要素核验接口示例](https://openapi.qcc.com/dataApi/856)
- **未证实且不得混用**：官方页面没有说明智能体平台的 Bearer API Key 与开放平台的 AppKey/SecretKey 可以互换。两边的域名、取 Key 路径和鉴权格式均不同，应按两套凭证体系处理。
- **已证实**：个人可注册使用，企业实名认证不是全部能力的前置条件；但 **历史存档 Server 仅企业认证后开通**。企业认证可用电子营业执照或对公账户打款，有效期一年。[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)｜[认证服务协议](https://agent.qcc.com/auth-service-agreement)
- **已证实**：平台按积分计费；当前公开规则是注册赠 500 分（30 天）、每日普通/VIP/SVIP 分别赠 100/150/200 分（当日有效），充值比例 1 元=10 分。不同工具单次消耗不同，官方积分页称为 1/3/5/20 分不等。[积分说明](https://agent.qcc.com/credits)
- **已证实且应优先评估**：用户协议禁止境外主体注册/登录/访问，也禁止境外 IP 访问；通过服务取得的数据只应在中国大陆境内存储和使用，不得向境外传输或允许境外主体查询、调取、下载、导出。[用户服务协议](https://agent.qcc.com/user-agreement)
- **未证实**：官方公开页未给出 CLI 当前版本号、CLI 自身所需的最低 Node.js 版本、macOS arm64 的单独兼容声明、请求速率/RPS、并发上限、SLA、每个标讯/文档工具的完整公开清单、npm 包许可类型；开放平台公开帮助页也未给出统一 RPS/并发/SLA。不能据此声称这些项目已得到官方确认。

## 1. 注册、登录与 API Key

### 已证实

1. 注册/登录需要手机号、账号密码或验证码；同一手机号只能注册一个平台账号。也可在授权后使用企查查主站账号或企查查开放平台账号快捷注册/登录。[隐私政策](https://agent.qcc.com/privacy-policy)｜[用户服务协议](https://agent.qcc.com/user-agreement)
2. API Key 获取路径：登录后点击右上角头像，选择“获取我的 API KEY”（个人中心）。公开入口为 [获取 API Key](https://agent.qcc.com/profile/api-key)，未登录访问会进入登录流程。[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)
3. API Key 的名称/备注可编辑；密钥本身不能在原 Key 上直接重置。如泄露，官方流程是新建 Key、更新应用配置并验证，再删除旧 Key。旧 Key 删除后立即失效且不可恢复。[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)
4. 每个账号最多可创建 5 个 Key，且至少保留 1 个。[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)
5. 平台会生成并验证 API Key，用于确认数据调用合法性与安全性；用户必须妥善保管，任何用该凭证发起的行为均被视为本人或授权行为。[隐私政策](https://agent.qcc.com/privacy-policy)

### 未证实

- 无登录状态下无法核实注册表单全部字段、验证码频率、API Key 的具体字符格式、Key 是否有固定到期日。
- 官方公开页未说明是否支持 IP 白名单、细粒度权限、Key 级别配额、只读/读写权限划分。

## 2. MCP 入口与鉴权配置

### 10 个官方远端 Server（已证实）

| 配置名 | 官方 URL | 能力范围 |
|---|---|---|
| `qcc-company` | `https://agent.qcc.com/mcp/company/stream` | 企业基座 |
| `qcc-risk` | `https://agent.qcc.com/mcp/risk/stream` | 企业风险 |
| `qcc-ipr` | `https://agent.qcc.com/mcp/ipr/stream` | 知识产权 |
| `qcc-operation` | `https://agent.qcc.com/mcp/operation/stream` | 企业经营 |
| `qcc-history` | `https://agent.qcc.com/mcp/history/stream` | 历史存档；需企业认证 |
| `qcc-executive` | `https://agent.qcc.com/mcp/executive/stream` | 董监高画像 |
| `qcc-legal-regulation` | `https://agent.qcc.com/mcp/regulation/stream` | 法规法条 |
| `qcc-legal-case` | `https://agent.qcc.com/mcp/case/stream` | 司法案例 |
| `qcc-tender` | `https://agent.qcc.com/mcp/tender/stream` | 招投标 |
| `qcc-document` | `https://agent.qcc.com/mcp/document/stream` | 在线链接文档解析 |

以上均来自 [官方接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)。每个远端 Server 的请求头格式为：

```json
{
  "Authorization": "Bearer YOUR_API_KEY"
}
```

这里的 `YOUR_API_KEY` 仅为官方占位符；本文未获取、保存或展示任何真实密钥。

### 本地文档解析入口（已证实）

本地文件解析不是额外的远端核心 Server，而是通过本机命令启动：

```json
{
  "command": "npx",
  "args": ["-y", "qcc-document-mcp"],
  "env": {
    "QCC_DOCUMENT_AUTHORIZATION": "Bearer YOUR_API_KEY"
  }
}
```

- 用途：解析本机上传/拖入的文件或明确给出的本地路径。
- 环境要求：Node.js 20+。
- 在线 URL 则由远端 `qcc-document` 解析，并要求 URL 可被公网访问。
- 两个文档入口可同时配置，客户端按文档来源选择。

来源：[官方接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)

### 客户端接入（已证实）

- 官方列举可粘贴通用 MCP 配置的客户端包括 Claude Desktop、CherryStudio、Trae、Cursor、阿里云百炼、Codex 等。
- WorkBuddy、QoderWork、IMA（ima.copilot）在官方 FAQ 中列为已打通的一键授权应用；指南同时展示豆包、QwenWork、TraeWork、DeepSeek Harness、MiniMax 等平台的专门接入方式。
- 配置保存后需按具体客户端提示重启或重新连接，首次真实工具调用成功才算接入验证。

来源：[官方接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)

## 3. CLI 安装、配置与调用

### 已证实

官方 CLI 包名为 `qcc-agent-cli`，全局安装与初始化命令如下：

```bash
npm install -g qcc-agent-cli
qcc init --authorization "Bearer YOUR_API_KEY"
```

官方示例表明 CLI 以 `qcc <领域> <工具> <参数>` 形式调用，返回原始 JSON，不经过 LLM；MCP 与 CLI 可同时使用，共用同一 API Key、数据源与权益额度。公开示例包括：

```bash
qcc company get_company_registration_info "企查查科技股份有限公司"
qcc regulation get_legal_regulation_search "数据出境"
qcc case get_judicial_case_search "卖方违约的买卖合同纠纷判决"
qcc tender search_tenders "智慧工地"
qcc document parse_document --file_path "./财报.pdf"
qcc document parse_document --file_url "https://example.com/财报.pdf"
qcc document get_parse_result "TASK_ID"
```

来源：[官方接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)

### 未证实

- CLI 当前发布版本、更新策略、完整命令帮助、退出码约定和重试策略。
- CLI 本身的最低 Node.js 版本；官网只明确本地 `qcc-document-mcp` 要求 Node.js 20+。
- macOS arm64 原生兼容性、是否包含原生二进制依赖。安装方式是 npm，但仅凭这一点不能把 arm64 兼容视为官方已确认。
- CLI 凭证具体落盘位置、文件权限和是否使用系统钥匙串。

## 4. OpenAPI：注册、鉴权、能力与限制

OpenAPI 位于独立的[企查查开放平台](https://openapi.qcc.com/)。官网顶部导航将 API、企业户、MCP、离线数据库、SDK 分列，MCP 链接回 `agent.qcc.com`；因此本文将 OpenAPI 与智能体平台 MCP/CLI 分开记录。

### 注册与开通（已证实）

1. [开放平台登录页](https://openapi.qcc.com/login)支持中国大陆 `+86` 手机号和短信验证码快捷登录；无账号时会自动注册，也可使用账号密码登录。
2. 官网首页公布的标准流程是：注册开放平台账号（或联系客服代注册）→ 提交资料完成企业实名认证 → 在线或联系客服申请开通接口 → 在线测试后接入业务系统。[开放平台官网](https://openapi.qcc.com/)
3. Key 获取路径：登录后进入“账号安全”，验证账号绑定手机号后取得接口请求所需 Key。[开放平台常见问题](https://openapi.qcc.com/services/after/faq)
4. 账号安全页支持设置 IP 白名单；配置成功后，仅白名单内 IP 可正常取数。[开放平台常见问题](https://openapi.qcc.com/services/after/faq)
5. 多个抽查接口页明确标注“限企业实名用户使用”及“需提供应用场景审核”；这能证明这些接口有相应门槛，但不能据此断言 167 个接口全部采用同一门槛。[企业三要素核验](https://openapi.qcc.com/dataApi/856)｜[招投标信息](https://openapi.qcc.com/dataApi/958)

### 鉴权与请求入口（已证实）

OpenAPI 不使用 MCP/CLI 的 Bearer 头。官方接口页给出的通用形态是：

```text
Query:   key=AppKey
Headers: Timespan=<北京时间对应的 10 位 Unix 秒级时间戳>
         Token=MD5(key + Timespan + SecretKey) 的 32 位大写字符串
```

- `Timespan` 有效期为 5 分钟；标准加密方式仅公开 MD5，其他方式需联系官方定制。
- 实际数据接口位于 `https://api.qichacha.com/...`，各接口单独公布 GET/POST、参数和返回字段。例如企业三要素核验为 GET，财税数据下单示例为 POST。
- 开放平台也提供在线“调试 API”；前提是接口已开通且有足够次数或余额。

来源：[开放平台常见问题](https://openapi.qcc.com/services/after/faq)｜[企业三要素核验](https://openapi.qcc.com/dataApi/856)｜[测试流程](https://openapi.qcc.com/services/after/test)

### 能力范围（已证实）

当前“所有 API”页面口径为 **167 个接口**，分类如下：

| 分类 | 接口数 |
|---|---:|
| 工商信息 | 30 |
| 法律诉讼 | 34 |
| 经营风险 | 22 |
| 经营信息 | 16 |
| 企业发展 | 6 |
| 知识产权 | 7 |
| 历史信息 | 31 |
| 增值服务 | 8 |
| 全球企业 | 4 |
| 特色推荐 | 9 |

官方首页展示的典型场景包括企业信息核验、客户身份识别和综合风险排查；接口目录还包含工商详情、模糊搜索、司法诉讼、知识产权、历史信息、招投标及全球企业等。[开放平台 API 首页](https://openapi.qcc.com/data)｜[招投标信息接口及完整分类导航](https://openapi.qcc.com/dataApi/958)

### 计费与额度（已证实）

- OpenAPI 按接口分别定价；所有有效请求正常收费。接口详情页会展示单次价格、次数套餐、免费试用次数或“价格面议”等不同口径，不能把某一个接口价格推广到全部接口。
- 2026-09-28 核验时，热门 API 页显示的示例价格包括：企业工商信息 0.20 元/次、企业模糊搜索 0.10 元/次、企业信息核验 1.00 元/次；招投标信息页显示 1.00 元/次并列出免费试用 20 次及次数套餐。价格可能变化，购买前应以接口详情和结算页为准。[热门 API](https://openapi.qcc.com/data)｜[招投标信息](https://openapi.qcc.com/dataApi/958)
- 官方 FAQ 称接口次数和余额充值当前有效期均为 2 年，未用额度不能延期；额度不足时会根据使用量提供不足 10 天或 5 天的默认提醒，另可配置余额提醒。[开放平台常见问题](https://openapi.qcc.com/services/after/faq)

### 已明确的限制与未证实项

- **已证实**：时间戳只在 5 分钟内有效；IP 白名单启用后仅白名单 IP 可调用；未开通接口或次数/余额不足会导致调用失败。[开放平台常见问题](https://openapi.qcc.com/services/after/faq)｜[测试流程](https://openapi.qcc.com/services/after/test)
- **未证实**：统一 RPS/QPS、并发上限、SLA、重试策略、统一分页上限；具体接口可能有自己的参数限制。例如招投标搜索公开说明为最近 2 年、最多返回 2000 条，但这不是所有接口的通用规则。[招投标信息](https://openapi.qcc.com/dataApi/958)
- **未证实**：开放平台用户协议页在本次未登录公开抓取中只显示协议标题和 2026-09-28 的更新/生效日期，正文未呈现。因此不能把智能体平台用户协议中的地域、转授权或数据再分发限制自动套用于 OpenAPI；实际接入前应登录阅读[开放平台用户服务协议](https://openapi.qcc.com/services/protocol/tos)并以签约合同为准。
- **未证实**：开放平台 AppKey/SecretKey 的固定到期日、轮换流程、最多创建数量，以及它们与智能体平台 Bearer API Key 的任何互通关系。

## 5. MCP/CLI 能力范围

### 官方总口径（已证实）

[平台首页](https://agent.qcc.com/) 当前宣称：**4 大领域、10 个核心 Server、203 个工具**。

- 企业数据：6 个 Server。
- 法律数据：2 个 Server。
- 标讯数据：1 个 Server。
- 智能文档解析：1 个 Server。

### 企业数据（已证实）

[企业数据能力页](https://agent.qcc.com/data) 明确为 6 个 Server、185 个原子工具：

| Server | 工具数 | 官方描述要点 |
|---|---:|---|
| 企业基座 `qcc-company` | 16 | 工商、股东、实控人、受益所有人、财务等 |
| 风控大脑 `qcc-risk` | 38 | 失信、被执行、限高、裁判文书、严重违法等 |
| 知产引擎 `qcc-ipr` | 18 | 商标、专利、软著、作品著作权、数字资产等 |
| 经营罗盘 `qcc-operation` | 35 | 招投标、资质荣誉、新闻舆情、招聘、土地等 |
| 历史存档 `qcc-history` | 34 | 历史股东、法代、失信、投资等；企业认证后开通 |
| 董监高画像 `qcc-executive` | 44 | 个人司法风险、关联企业、UBO；需“企业名称+董监高姓名”双参数锚定 |

企业能力页还明确：企业完整名称或 18 位统一社会信用代码可直接精确匹配；企业简称、不完整名等应先调用 `get_company_by_query`，返回唯一精确匹配或最多 5 个候选供人工确认。

### 法律数据（已证实）

[法律数据页](https://agent.qcc.com/legal) 明确列出 10 个工具，分为法规法条 5 个、司法案例 3 个、引用溯源 2 个，覆盖：

- 法条语义/关键词检索、法条详情；
- 法规关键词检索、法规详情；
- 普通/权威案例检索、案例详情；
- 法规引用与案例案号的真实性、效力、来源核验。

### 标讯与文档（部分已证实）

- 标讯官方示例工具为 `search_tenders`，可按关键词、地区、招采方式、预算等筛选。
- 文档官方示例工具为 `parse_document` 与异步结果查询 `get_parse_result`；支持本地文件和公网 URL。
- **未证实**：官方公开页没有提供这两个领域各自完整的工具数量与逐项清单。虽然总数 203 减去企业 185、法律 10 得到 8，但不能仅凭算术确认标讯与文档各自的准确拆分。

来源：[平台首页](https://agent.qcc.com/)｜[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)

## 6. MCP/CLI 计费、额度与分页限制

### 已证实

- 注册体验积分：500 分，有效期 30 天。
- 每日赠送：普通 100、VIP 150、SVIP 200；每日 02:00 发放，当日有效、不累积。
- 企业认证奖励：200 分，有效期 90 天。
- 邀请奖励：每成功激活 1 人 100 分，每月最多 5 人，每笔 90 天有效。
- 在线充值：1 元=10 分；公开套餐为 50/100/500 元或自定义金额；支持微信、支付宝、对公转账。
- 消耗顺序：每日赠送 → 注册体验 → 认证奖励 → 邀请奖励 → 充值积分。
- 不同工具按 1/3/5/20 分不等计费，准确单价以工具详情页实时展示为准。
- 已购买积分用于实际服务后不可恢复、不可返还；除法律法规另有强制规定外，已购积分不退款、不转让、不兑换现金；具体有效期和价格以购买/结算页为准。

来源：[积分说明](https://agent.qcc.com/credits)｜[用户服务协议](https://agent.qcc.com/user-agreement)

### 同一主体月度封顶（已证实，但适用范围有限）

| 主体 | 自然月封顶 |
|---|---:|
| 企业 | 100 分 |
| 个体工商户 | 20 分 |
| 董监高自然人 | 100 分 |

该封顶**只适用于企业数据下按特定企业/个体户/董监高计费的 MCP 服务**。法律数据、标讯数据、智能文档解析，以及企业实体识别，均按调用量计费且不适用上述封顶。[积分说明](https://agent.qcc.com/credits)

### 分页与批量（已证实）

- 部分工具（官网举例为商标、专利）支持分页；确需分页要向企查查申请并说明理由，开通后方可使用。
- 分页会额外消耗积分。
- 企业批量调用或大额采购需联系商务；官网公布电话为 400-088-8275。
- **未证实**：公开页面没有给出统一的 RPS、QPS、并发数、日调用次数、响应大小或超时上限。

来源：[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)

## 7. MCP/CLI 认证条件

### 已证实

- 普通个人用户可使用 9 个 Server；只有历史存档 Server 要求企业实名认证。
- 企业认证方式：提交电子营业执照，或从企业对公账户完成平台指定的小额打款验证。
- 对公验证金额不超过 1 元，审核完成后 10 个工作日内原路退回。
- 认证有效期一年；要保持认证状态，应在到期前 90 日内发起下一周期申请。
- 认证通过后，历史存档 Server 自动开通，原 API Key 不变；当前活动规则另赠 200 分、90 天有效。
- 教师、机关单位等非标准企业主体可联系官方商务，可能需要相应证明材料。

来源：[接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)｜[认证服务协议](https://agent.qcc.com/auth-service-agreement)

## 8. MCP/CLI 许可、合规与使用限制

### 已证实

1. **这不是公开数据的自由许可。** 平台、软件、程序、数据、算法、模型等权利归企查查；未经书面授权，不得反向工程、反编译、反汇编、抓取、复制、转载、传输、镜像或自动获取平台资料，也不得将取得的数据提供第三方使用。[用户服务协议](https://agent.qcc.com/user-agreement)
2. 账号及购买/赠送服务仅限本人使用，不得赠与、借用、转让或售卖；一个账号同一时间只能在一台同类型设备登录。[用户服务协议](https://agent.qcc.com/user-agreement)
3. 不得恶意或非法连续、频繁查询，不得用机器抓取、复制、镜像等方式不合理地大批量获取数据；平台可限制、冻结或注销账号，并可封禁同一 IP 下的相关账号。[用户服务协议](https://agent.qcc.com/user-agreement)
4. 不得把获取的数据用于与企查查相同/类似的业务或产品，也不得用于为第三方提供数据类服务。[用户服务协议](https://agent.qcc.com/user-agreement)
5. 仅限中国大陆境内：不支持境外主体注册、登录或访问，不支持境外 IP；取得的数据仅应在中国大陆境内存储/使用，不得向境外传输或允许境外主体查询、调取、下载、导出。[用户服务协议](https://agent.qcc.com/user-agreement)
6. 用户必须基于合法、正当用途调用；涉及他人个人信息或组织信息时，应取得必要、合法、有效的授权。[用户服务协议](https://agent.qcc.com/user-agreement)｜[隐私政策](https://agent.qcc.com/privacy-policy)
7. 官方不保证服务连续性、稳定性、及时性，以及数据内容的准确性、真实性、完整性和时效性；使用者作出判断或决策前仍需自行核验。[用户服务协议](https://agent.qcc.com/user-agreement)
8. 收费、计费方式、功能、字段和服务规则可因监管、业务、数据来源或技术变化调整，最终以实时产品页面为准。[用户服务协议](https://agent.qcc.com/user-agreement)

### 未证实

- `qcc-agent-cli` 与 `qcc-document-mcp` npm 包分别采用何种开源/商业软件许可证。官方公开页面只给出了安装命令和平台协议，没有给出包级许可证文本。
- 是否允许把查询结果长期缓存、再分发给关联公司、嵌入面向外部客户的产品；公开协议含较严格限制，若有此类场景应向企查查取得书面确认，不能默认许可。

## 9. 本次没有做的事

- 没有登录或注册企查查账号。
- 没有点击生成、展示、复制任何真实 API Key。
- 没有把密钥写入文件、命令、日志或环境变量。
- 没有执行 npm 安装，也没有检查第三方 npm 页面。
- 没有对 MCP/CLI 发起真实调用，因此本文属于**官方文档核验**，不是运行时可用性证明。
- 没有生成 OpenAPI 的 AppKey/SecretKey，也没有对 `api.qichacha.com` 发起真实业务请求；OpenAPI 部分同样只是官方文档核验。

## 10. 实际访问的官方 URL

- [https://agent.qcc.com/](https://agent.qcc.com/)
- [https://agent.qcc.com/guide?source=openapi&term=nav](https://agent.qcc.com/guide?source=openapi&term=nav)
- [https://agent.qcc.com/data](https://agent.qcc.com/data)
- [https://agent.qcc.com/legal](https://agent.qcc.com/legal)
- [https://agent.qcc.com/credits](https://agent.qcc.com/credits)
- [https://agent.qcc.com/profile/api-key](https://agent.qcc.com/profile/api-key)
- [https://agent.qcc.com/user-agreement](https://agent.qcc.com/user-agreement)
- [https://agent.qcc.com/privacy-policy](https://agent.qcc.com/privacy-policy)
- [https://agent.qcc.com/auth-service-agreement](https://agent.qcc.com/auth-service-agreement)
- [https://openapi.qcc.com/](https://openapi.qcc.com/)
- [https://openapi.qcc.com/data](https://openapi.qcc.com/data)
- [https://openapi.qcc.com/login](https://openapi.qcc.com/login)
- [https://openapi.qcc.com/services/after/faq](https://openapi.qcc.com/services/after/faq)
- [https://openapi.qcc.com/services/after/test](https://openapi.qcc.com/services/after/test)
- [https://openapi.qcc.com/services/protocol/tos](https://openapi.qcc.com/services/protocol/tos)
- [https://openapi.qcc.com/dataApi/856](https://openapi.qcc.com/dataApi/856)
- [https://openapi.qcc.com/dataApi/958](https://openapi.qcc.com/dataApi/958)

为核验特定平台接入示例，还访问了以下官方指南变体：

- [https://agent.qcc.com/guide?platform=workbuddy](https://agent.qcc.com/guide?platform=workbuddy)
- [https://agent.qcc.com/guide?platform=qwenwork](https://agent.qcc.com/guide?platform=qwenwork)
- [https://agent.qcc.com/guide?platform=traework](https://agent.qcc.com/guide?platform=traework)
- [https://agent.qcc.com/guide?platform=minimax](https://agent.qcc.com/guide?platform=minimax)
- [https://agent.qcc.com/guide?platform=lobsterai](https://agent.qcc.com/guide?platform=lobsterai)
- [https://agent.qcc.com/guide?platform=wpscomate](https://agent.qcc.com/guide?platform=wpscomate)
