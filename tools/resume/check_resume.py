"""Check the standalone portfolio's links, headings and evidence boundaries."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[2]
HTML = ROOT / "resume" / "index.html"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.assets = []
        self.text = []
        self.h1_count = 0
        self.scripts = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        if tag == "a":
            self.links.append(attrs.get("href", ""))
        if tag == "link" and attrs.get("rel") == "stylesheet":
            self.assets.append(attrs["href"])
        if tag == "script":
            self.scripts.append(attrs.get("src", ""))
            self.assets.append(attrs.get("src", ""))
        if tag == "h1":
            self.h1_count += 1

    def handle_data(self, text):
        self.text.append(text)


class PortfolioChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = HTML.read_text(encoding="utf-8")
        cls.page = PageParser()
        cls.page.feed(cls.source)
        cls.text = " ".join(cls.page.text)

    def test_single_h1_and_unique_ids(self):
        self.assertEqual(self.page.h1_count, 1)
        self.assertEqual(len(self.page.ids), len(set(self.page.ids)))

    def test_internal_anchors_exist(self):
        for href in self.page.links:
            if href.startswith("#"):
                self.assertIn(href[1:], self.page.ids, href)

    def test_local_assets_exist(self):
        for src in self.page.assets:
            self.assertTrue((HTML.parent / src).is_file(), src)

    def test_no_private_source_or_identity_links(self):
        joined = " ".join(self.page.links)
        for private_path in ("/little-bard", "bookkiki-server", "bookkiki-workers", "atlassian.net"):
            self.assertNotIn(private_path, joined)
        for sensitive_fragment in ("01059232630", "2000.03.16", "주민등록번호", "병역증명서"):
            self.assertNotIn(sensitive_fragment, self.source)

    def test_training_and_serving_scopes(self):
        for required in ("과학기술정보통신부", "연수생", "수료 예정", "MLX API 서빙", "QLoRA"):
            self.assertIn(required, self.text)
        self.assertNotIn("과학기술정보통신부 소속", self.text)
        self.assertNotIn("vLLM 운영 완료", self.text)

    def test_metrics_keep_conditions(self):
        for required in ("합성 실험", "140회", "20회", "0.883", "0.931", "약 2,600명이 참여한 온라인 예선", "팀 private 20위", "팀 9위", "단일 CLI"):
            self.assertIn(required, self.text)

    def test_no_placeholders_or_unsecured_links(self):
        self.assertNotRegex(self.source, r"TODO|YOUR_ORG|example\.com|lorem ipsum")
        for href in self.page.links:
            self.assertTrue(href.startswith(("https://", "#")) or href == "mailto:sowilloo@naver.com", href)

    def test_contact_email_matches_requested_address(self):
        contact = self.source.split('id="contact"', 1)[1].split("</section>", 1)[0]
        self.assertIn('href="mailto:sowilloo@naver.com">Email · sowilloo@naver.com</a>', contact)

    def test_intro_and_evaluation_purpose(self):
        intro = self.source.split('class="intro-text">', 1)[1].split("</p>", 1)[0]
        for required in ("LLM-as-a-Judge", "Qwen3.6 학습 실험", "MLX API 서빙", "RAG 기반 검색"):
            self.assertIn(required, intro)
        evaluation = self.source.split('id="eval-heading"', 1)[1].split("</section>", 1)[0]
        for required in ("난이도", "평가 기준", "파인튜닝", "튜닝 전후", "같은 조건"):
            self.assertIn(required, evaluation)
        self.assertNotIn("낭독 리듬", evaluation)

    def test_service_links_and_project_coverage(self):
        for href in ("https://bookkiki.com/download", "https://www.instagram.com/bookkiki.official/"):
            self.assertIn(href, self.page.links)
        self.assertNotIn("fbclid", self.source)
        for project in ("eval", "worker", "observability", "qwen", "cueview", "segmentation", "detection", "forecast", "phishing"):
            self.assertIn(f"{project}-heading", self.page.ids)

    def test_intro_type_is_body_sized_and_regular_weight(self):
        css = (HTML.parent / "style.css").read_text(encoding="utf-8")
        self.assertRegex(css, r"\.intro-text\s*\{[^}]*font-size:\s*18px;[^}]*font-weight:\s*400;")

    def test_print_and_responsive_styles(self):
        css = (HTML.parent / "style.css").read_text(encoding="utf-8")
        self.assertIn("@media print", css)
        self.assertIn("@media (max-width: 700px)", css)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("focus-visible", css)
        self.assertEqual(self.page.scripts, ["./resume.js"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
