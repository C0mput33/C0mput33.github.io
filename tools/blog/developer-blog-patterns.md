# 실제 개발 블로그에서 가져온 편집 기준

유명 블로그의 말투를 따라 쓰는 목록이 아니다. 실제 글에서 반복되는 문제·증거·판단·한계의 배치만 공개 저장소의 편집 규칙으로 옮긴다. 조사 근거와 상세 비교는 `personal-brain/blog/reference/developer-blog-patterns.md`가 정본이다.

## 글 유형별 골격

- 문제 해결: 영향·재현 → 관찰 → 가설과 배제 → 원인 → 수정 → 같은 조건의 검증 → 남은 한계
- 장애 회고: 영향·시간대 → 타임라인 → 직접 원인과 기여 요인 → 복구 → 재발 방지 → 미완료 조치
- 실험·평가: 질문 → 데이터·버전·기준선 → 절차 → 결과 → 해석 → 한계 → 다음 의사결정
- 설계·마이그레이션: 규모·제약 → 기존 병목 → 대안 → 선택 이유 → 전환·검증 → 결과 → 되돌림 조건
- TIL: 막힌 지점 → 최소 재현 예제 → 확인한 원리 → 적용 범위와 예외

헤딩을 그대로 복사하거나 해당하지 않는 단계를 만들지 않는다. 실제로 확인한 연결만 남긴다.

## 발행 전에 확인할 것

1. 첫 문단에 상황, 확인한 결과, 글의 범위가 있는가?
2. 로그·코드·수치가 결론과 직접 연결되는가?
3. 배제한 가설과 선택하지 않은 대안이 실제 확인에 근거하는가?
4. 같은 조건에서 변경을 다시 검증했는가?
5. 환경·버전·기간·표본·단위가 재현에 충분한가?
6. 남은 한계와 되돌릴 조건을 밝혔는가?

## 참고한 실제 글

- Julia Evans, [Blogging principles I use](https://jvns.ca/blog/2017/03/20/blogging-principles/), [Write good examples by starting with real code](https://jvns.ca/blog/2021/07/08/writing-great-examples/)
- Simon Willison, [What to blog about](https://simonwillison.net/2022/Nov/6/what-to-blog-about/)
- Martin Fowler, [Advocate, educator, and authorial stance](https://martinfowler.com/articles/authorial-stance.html)
- GitHub, [Move Fast and Fix Things](https://github.blog/engineering/move-fast/)
- Cloudflare, [Cloudflare outage on July 17, 2020](https://blog.cloudflare.com/todays-outage-post-mortem/)
- Discord, [How Discord moved engineering to cloud development environments](https://discord.com/blog/how-discord-moved-engineering-to-cloud-development-environments)
- 카카오, [실시간 댓글 개발기](https://tech.kakao.com/posts/390)
- 우아한형제들, [장애 대응 프로세스를 만들어가는 이야기](https://techblog.woowahan.com/4886/)
- 네이버 D2, [CUBRID DBLink로 오라클 데이터 조회하기](https://d2.naver.com/helloworld/809802)
- 토스, [기술 글쓰기의 고객을 정의하는 법](https://toss.tech/article/25217)
