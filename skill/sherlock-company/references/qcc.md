# 企查查可选接入

> 文档核验日期：2026-09-28。安装前重新查看[官方接入指南](https://agent.qcc.com/guide?source=openapi&term=nav)，计费、工具数和授权条件可能调整。

## 这个 Skill 如何使用企查查

只在需要确认法律主体、工商登记、股东与实控人、公开风险、司法记录或经营事项时调用。企查查返回的事实不是“是否值得去”的决策，也不能证明目标团队的加班、管理、奖金兑现或试用期体验。

优先使用 MCP；需要脚本自动化或取原始 JSON 时使用 CLI。两者共用智能体平台 Bearer API Key 和权益额度。OpenAPI 的 AppKey/SecretKey/MD5 Token 是另一套凭证与计费体系，不得与 MCP/CLI Key 混用。

## 用户安装与配置

1. 打开[企查查智能体数据平台](https://agent.qcc.com/)，使用中国大陆手机号注册/登录。
2. 右上角头像 →“获取我的 API KEY”，或打开[API Key 页](https://agent.qcc.com/profile/api-key)。
3. 把 Key 配置在个人的 MCP 客户端或 CLI；不写进 Skill、项目文件、案例 JSON、截图或提交记录。
4. 如 Key 曾经发送到聊天、公开文档或命令日志，官方做法是新建 Key、更新配置并验证，再删除旧 Key。

针对求职核验的最小 MCP 配置可从下列服务开始：

```json
{
  "mcpServers": {
    "qcc-company": {
      "url": "https://agent.qcc.com/mcp/company/stream",
      "headers": {"Authorization": "Bearer YOUR_API_KEY"}
    },
    "qcc-risk": {
      "url": "https://agent.qcc.com/mcp/risk/stream",
      "headers": {"Authorization": "Bearer YOUR_API_KEY"}
    },
    "qcc-legal-case": {
      "url": "https://agent.qcc.com/mcp/case/stream",
      "headers": {"Authorization": "Bearer YOUR_API_KEY"}
    }
  }
}
```

官方指南当前列出 10 个远程 Server；只配任务所需的 Server，避免无目的批量查询和积分消耗。历史存档 Server 需企业认证。

CLI 官方命令：

```bash
npm install -g qcc-agent-cli
qcc init --authorization "Bearer YOUR_API_KEY"
qcc check
qcc company get_company_registration_info "企查查科技股份有限公司"
```

安装会修改本机 npm 全局环境，必须由用户授权。`qcc init --authorization` 会把凭证作为命令行参数，可能进入 shell history 或进程列表；优先使用支持密钥存储的 MCP 客户端，必须用 CLI 时只在个人本机终端执行，并按所用 shell 的官方方法处理敏感历史。本项目在 Apple M1 Mac 上用临时 `npx qcc-agent-cli@1.0.10 --help` 成功启动；这是本次运行证据，不是企查查对 macOS arm64 的永久官方承诺。本地文档解析入口 `qcc-document-mcp` 官方要求 Node.js 20+。

## 调用纪律

1. 品牌、简称或不完整企业名先调用 `get_company_by_query`；多候选时让用户选，不自动选第一个。
2. 只查与用户关切有关的当前主体、主题和时间窗；不对所有关联方做散弹式扫描。
3. 记录实际 `tool_code`、查询主体、返回字段、取数时间和数据更新口径。不自行重算或缩位工具返回的百分比和聚合值。
4. 0 条写“在该数据源未发现公开记录”；字段缺失写“未返回”；调用失败写“工具调用失败”。三者不混用。
5. 每个 QCC 事实都标“来源：企查查”，并与 Skill 的推理相邻分开。

## 已验证的运行证据（2026-09-28）

- 使用用户提供的 Key 向 `qcc-company` 发起 MCP `initialize`：HTTP 200，返回 `QCC MCP 1.0.0` 与 `protocolVersion 2025-03-26`。
- 调用 `get_company_by_query(searchKey="企查查科技股份有限公司")`：返回“唯一精确匹配”和统一社会信用代码。
- Key 没有写入本仓库、测试文件或最终 HTML。该结果证明本次凭证和企业基座 Server 当时可用，不保证其它 Server 权限、未来可用性或所有数据准确性。

安装包之外的完整一手调研记录保存在开发项目的 `research/qcc-official.md`；独立安装 Skill 时以上述官方链接为准。
