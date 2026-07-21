# AGENTS.md

이 저장소는 공개 블로그의 소스이자 실제 배포 단위다.

## 변경 규칙

- 확인한 경험·수치만 쓴다. 레거시 평가 결과는 정책 버전과 비교 한계를 함께 적는다.
- 첫 문단에서 상황·결과·범위를 밝힌다. 홍보성 형용사, 빈 요약, 강제된 반전, 과한 볼드를 피한다.
- 수치와 외부 기술 주장에는 가능한 한 1차 출처와 관측 날짜를 붙인다.
- 툴팁 정의는 `tools/blog/tooltip_dict.json`만 직접 편집한다.
- `Gemfile.lock`과 `tools/blog/POLICY_VERSION`을 커밋한다.

## 필수 검사

```bash
python3 -m pip install -r tools/blog/requirements.txt
python3 -m unittest discover -s tools/blog/tests -v
python3 tools/blog/validate_post.py . --strict-style
python3 tools/blog/sync_tooltip_dictionary.py --check
python3 tools/blog/insert_tooltips.py _posts --check-coverage
bundle exec jekyll build
```

검사를 통과한 블로그 변경은 `main`에 직접 push할 수 있다. push 뒤 Actions 성공과 공개 URL 렌더링을 확인한다.
