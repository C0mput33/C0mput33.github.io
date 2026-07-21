from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

from insert_tooltips import transform, validate_text  # noqa: E402
from sync_tooltip_dictionary import render  # noqa: E402
from validate_post import check_post  # noqa: E402


class TooltipTests(unittest.TestCase):
    dictionary = {
        "부트스트랩": "복원추출로 통계량의 변동을 추정하는 방법.",
        "DPO": "검증된 선호쌍으로 정책을 최적화하는 방법.",
    }

    def test_compound_particle_and_idempotence(self):
        source = "부트스트랩에서는 군집 단위를 먼저 정해야 한다. 부트스트랩 결과다."
        first, added, updated = transform(source, self.dictionary)
        second, added_again, updated_again = transform(first, self.dictionary)
        self.assertIn(">부트스트랩</span>에서는", first)
        self.assertEqual((added, updated), (1, 0))
        self.assertEqual(second, first)
        self.assertEqual((added_again, updated_again), (0, 0))

    def test_multiline_footnote_and_fences_are_protected(self):
        source = """[^note]: 부트스트랩 설명
  다음 줄에도 DPO가 있다.

```text
부트스트랩 DPO
```

본문의 부트스트랩과 DPO.
"""
        transformed, added, _ = transform(source, self.dictionary)
        self.assertEqual(added, 2)
        self.assertIn("[^note]: 부트스트랩 설명", transformed)
        self.assertIn("다음 줄에도 DPO가 있다", transformed)
        self.assertIn("본문의 <span class=\"term\"", transformed)

    def test_stale_definition_is_refreshed(self):
        source = '<span class="term" data-tip="old">DPO</span> 데이터'
        transformed, added, updated = transform(source, self.dictionary)
        self.assertEqual((added, updated), (0, 1))
        self.assertIn(self.dictionary["DPO"], transformed)
        _, errors = validate_text(transformed, self.dictionary)
        self.assertEqual(errors, [])

    def test_link_and_reference_definition_are_protected(self):
        source = "[DPO 안내](/dpo)\n[DPO]: /reference\n본문 DPO"
        transformed, added, _ = transform(source, self.dictionary)
        self.assertEqual(added, 1)
        self.assertIn("[DPO 안내](/dpo)", transformed)
        self.assertIn("[DPO]: /reference", transformed)
        self.assertIn("본문 <span", transformed)

    def test_dictionary_render_is_deterministic(self):
        self.assertEqual(render({"B": "둘", "a": "하나"}), render({"a": "하나", "B": "둘"}))


class ValidatorTests(unittest.TestCase):
    def _write_post(self, root: Path, name: str, front: str, body: str = "본문입니다.\n") -> Path:
        posts = root / "_posts"
        posts.mkdir(parents=True, exist_ok=True)
        path = posts / name
        path.write_text(f"---\n{front}\n---\n{body}", encoding="utf-8")
        return path

    def _valid_front(self, date: str = "2026-07-21 12:00:00 +0900") -> str:
        return f"""title: 재현 가능한 글
date: {date}
categories: [Learning, AI Engineering]
tags: [testing, writing]
description: 검증기 테스트에 쓰는 설명입니다."""

    def test_valid_post_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = self._write_post(root, "2026-07-21-valid.md", self._valid_front())
            errors, _, _ = check_post(
                post,
                {"valid"},
                root,
                now=dt.datetime(2026, 7, 22, tzinfo=dt.timezone.utc),
            )
            self.assertEqual(errors, [])

    def test_placeholder_template_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = self._write_post(
                root,
                "2026-07-21-placeholder.md",
                """title: 제목
date: YYYY-MM-DD HH:MM:SS +0900
categories: [대분류, 소분류]
tags: [소문자-태그]
description: 설명""",
                "```language\ncode\n```\n",
            )
            errors, _, _ = check_post(post, {"placeholder"}, root)
            self.assertTrue(any("placeholder" in error for error in errors))

    def test_invalid_yaml_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = self._write_post(root, "2026-07-21-invalid.md", "title: [broken")
            errors, _, _ = check_post(post, {"invalid"}, root)
            self.assertTrue(any("invalid YAML" in error for error in errors))

    def test_timezone_aware_future_check(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = self._write_post(
                root,
                "2026-07-22-future.md",
                self._valid_front("2026-07-22 00:00:00 +0900"),
            )
            errors, _, _ = check_post(
                post,
                {"future"},
                root,
                now=dt.datetime(2026, 7, 21, 14, 30, tzinfo=dt.timezone.utc),
            )
            self.assertTrue(any("future publication date" in error for error in errors))

    def test_filename_date_must_match_front_matter(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = self._write_post(root, "2026-07-20-mismatch.md", self._valid_front())
            errors, _, _ = check_post(
                post,
                {"mismatch"},
                root,
                now=dt.datetime(2026, 7, 22, tzinfo=dt.timezone.utc),
            )
            self.assertTrue(any("filename date" in error for error in errors))

    def test_inline_footnote_before_colon_and_multiline_definition(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            post = self._write_post(
                root,
                "2026-07-21-footnote.md",
                self._valid_front(),
                "본문의 전략[^note]: 네 가지다.\n\n[^note]: 첫 줄\n  이어지는 정의 안의 [^ghost]\n",
            )
            errors, warnings, _ = check_post(
                post,
                {"footnote"},
                root,
                now=dt.datetime(2026, 7, 22, tzinfo=dt.timezone.utc),
            )
            self.assertEqual(errors, [])
            self.assertFalse(any("footnote" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
