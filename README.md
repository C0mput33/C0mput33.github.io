# C0mput33's Dev Log

<https://c0mput33.github.io>의 Jekyll 소스다. Ruby 3.4.10, Chirpy 7.6.0, GitHub Pages Actions로 빌드한다.

## 로컬 검사

```bash
python3 -m pip install -r tools/blog/requirements.txt
python3 -m unittest discover -s tools/blog/tests -v
python3 tools/blog/validate_post.py . --strict-style
python3 tools/blog/sync_tooltip_dictionary.py --check
python3 tools/blog/insert_tooltips.py _posts --check-coverage
bundle install
bundle exec jekyll serve
```

새 용어는 `tools/blog/tooltip_dict.json`에만 추가한다. 문서와 본문은 동기화 도구로 갱신한다.
글의 문제 해결 흐름과 유형별 골격은 [`tools/blog/developer-blog-patterns.md`](tools/blog/developer-blog-patterns.md)에 정리했다.

## 배포

검사를 통과한 `main` push는 GitHub Pages 배포를 시작한다. Actions의 `Build and Deploy`가 Python 정책 검사, Jekyll build, htmlproofer를 차례로 통과해야 실제 사이트가 바뀐다. 자세한 편집 규칙은 [AGENTS.md](AGENTS.md)에 있다.
