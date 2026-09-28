import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skill" / "sherlock-company" / "scripts" / "render_report.py"
CASE = ROOT / "cases" / "4399" / "decision-report.json"

spec = importlib.util.spec_from_file_location("render_report", SCRIPT)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)


class RenderReportTests(unittest.TestCase):
    def load_case(self):
        return json.loads(CASE.read_text("utf-8"))

    def test_case_record_is_valid(self):
        self.assertEqual(module.validate_record(self.load_case()), [])

    def test_renderer_escapes_user_text_and_embeds_no_script(self):
        record = self.load_case()
        record["decision"]["headline"] = '<script>alert("x")</script>'
        output = module.render(record, "")
        self.assertIn("&lt;script&gt;alert", output)
        self.assertNotIn('<script>alert("x")</script>', output)
        self.assertNotIn("<script", output.lower())

    def test_renderer_rejects_unsafe_source_urls(self):
        record = self.load_case()
        record["sources"][0]["url"] = "javascript:alert(1)"
        errors = module.validate_record(record)
        self.assertTrue(any("http/https" in error for error in errors))

    def test_validator_rejects_unregistered_evidence_ids(self):
        record = self.load_case()
        record["concerns"][0]["evidence_ids"].append("E404")
        errors = module.validate_record(record)
        self.assertTrue(any("未登记来源: E404" in error for error in errors))

    def test_validator_rejects_invented_decision_state(self):
        record = self.load_case()
        record["decision"]["state"] = "五星推荐"
        errors = module.validate_record(record)
        self.assertTrue(any("四种决策状态" in error for error in errors))

    def test_validator_rejects_signal_source_as_verified_fact(self):
        record = self.load_case()
        record["verified"][0]["evidence_ids"].append("E3")
        errors = module.validate_record(record)
        self.assertTrue(any("非 verified 来源 E3" in error for error in errors))

    def test_employee_experience_claim_needs_evidence(self):
        record = self.load_case()
        record["employee_experience"]["coverage"] = "adequate"
        errors = module.validate_record(record)
        self.assertTrue(any("limited/adequate" in error for error in errors))

    def test_render_requires_completed_privacy_review(self):
        record = self.load_case()
        record["privacy_review"]["completed"] = False
        errors = module.validate_record(record)
        self.assertTrue(any("privacy_review.completed" in error for error in errors))

    def test_pii_scan_blocks_phone_number(self):
        record = self.load_case()
        record["decision"]["headline"] = "请联系 13800138000"
        errors = module.validate_record(record)
        self.assertTrue(any("中国大陆手机号" in error for error in errors))

    def test_verified_source_must_be_accessed_or_local(self):
        record = self.load_case()
        record["sources"][0]["access_status"] = "blocked"
        record["sources"][0]["locator"] = "search snippet"
        errors = module.validate_record(record)
        self.assertTrue(any("accessed/local" in error for error in errors))

    def test_employee_experience_cannot_use_corporate_source(self):
        record = self.load_case()
        record["employee_experience"]["coverage"] = "adequate"
        record["employee_experience"]["evidence_ids"] = ["E1"]
        errors = module.validate_record(record)
        self.assertTrue(any("非 employee_experience 来源 E1" in error for error in errors))

    def test_unresolved_identity_blocks_company_findings(self):
        record = self.load_case()
        record["identity"]["status"] = "unresolved"
        errors = module.validate_record(record)
        self.assertTrue(any("unresolved 时不得生成公司级 verified" in error for error in errors))

    def test_negative_decision_needs_verified_basis(self):
        record = self.load_case()
        record["decision"]["state"] = "先不接受"
        record["decision"]["basis_ids"] = []
        errors = module.validate_record(record)
        self.assertTrue(any("必须提供 verified basis_ids" in error for error in errors))

    def test_output_has_required_multi_card_sections(self):
        output = module.render(self.load_case(), "data:image/jpeg;base64,ZmFrZQ==")
        for text in (
            "证据分盒",
            "先确认“谁在招你”",
            "你最关心的问题",
            "有没有目标团队的真实体验",
            "接受录用前的核实清单",
            "这些结论从哪里来",
        ):
            self.assertIn(text, output)
        self.assertGreaterEqual(output.count('class="concern-card'), 4)
        self.assertNotIn("信息完整度", output)
        self.assertNotIn("STARS", output)

    def test_output_uses_v2_visual_template_and_plain_chinese_ui(self):
        output = module.render(self.load_case(), "")
        self.assertIn('data-template="evidence-dossier-v2"', output)
        self.assertIn("--accent:#d9573b", output)
        for forbidden in (
            "SHERLOCK COMPANY · OFFER",
            "INTERACTIVE CLUE CARDS",
            "INTERVIEW CHEAT SHEET",
            "SERIES #",
            "不猜公司好不好",
            "——",
        ):
            self.assertNotIn(forbidden, output)

    def test_output_translates_internal_enums(self):
        output = module.render(self.load_case(), "")
        self.assertIn("主体确认到哪一步：部分确认", output)
        self.assertNotIn("主体确认到哪一步：partial", output)
        self.assertIn("主体与工商", output)
        for kind in module.EVIDENCE_KINDS:
            self.assertNotIn(f"证据类型 {kind}", output)

    def test_cli_validate_only_needs_no_output(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), str(CASE), "--validate-only"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("结构有效", result.stdout)

    def test_cli_writes_self_contained_html(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "report.html"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(CASE), "--output", str(target)],
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            doc = target.read_text("utf-8")
            self.assertIn("data:image/jpeg;base64,", doc)
            self.assertNotIn("<script", doc.lower())
            self.assertNotIn("<link", doc.lower())
            self.assertNotIn("@import", doc.lower())
            self.assertNotIn("@font-face", doc.lower())


if __name__ == "__main__":
    unittest.main()
