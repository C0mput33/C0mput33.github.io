# AGENTS.md

이 저장소는 공개 블로그의 소스이자 실제 배포 단위다.

## 변경 규칙

- 확인한 경험·수치만 쓴다. 레거시 평가 결과는 정책 버전과 비교 한계를 함께 적는다.
- 첫 문단에서 상황·결과·범위를 밝힌다. 홍보성 형용사, 빈 요약, 강제된 반전, 과한 볼드를 피한다.
- 문제 해결 글은 관찰→가설→확인→결정의 연결을 남긴다. 실험 글은 기준선·표본·환경·버전·단위와 해석 한계를, 설계 글은 규모·제약·대안·검증·되돌림 조건을 실제 확인한 범위에서 밝힌다.
- 실제 코드·로그·데이터에서 예제를 만들고 핵심을 보존한 채 무관한 부분만 덜어낸다. 확인하지 않은 원인 배제나 회고는 쓰지 않는다.
- 수치와 외부 기술 주장에는 가능한 한 1차 출처와 관측 날짜를 붙인다.
- 툴팁 정의는 `tools/blog/tooltip_dict.json`, 근거는 `tools/blog/tooltip_sources.json`에서 함께 관리한다. 공식 문서·표준·원 논문 또는 실제 프로젝트 경로가 없는 용어는 추가하지 않는다.
- 다의어는 정확한 표면형으로 분리하고, 더 긴 용어 안에 다른 뜻의 짧은 용어를 넣지 않는다.
- `Gemfile.lock`과 `tools/blog/POLICY_VERSION`을 커밋한다.

글 유형별 구조와 실제 개발 블로그 비교는 [`tools/blog/developer-blog-patterns.md`](tools/blog/developer-blog-patterns.md)를 참고한다. 유명 블로그의 말투를 복제하지 않고 문제·증거·판단·한계를 배치하는 방식만 적용한다.

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
