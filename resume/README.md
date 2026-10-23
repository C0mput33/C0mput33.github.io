# 김해찬 포트폴리오

공개 주소: <https://c0mput33.github.io/resume/>

독립 HTML/CSS/JavaScript 페이지다. 기존 블로그의 테마와 게시물을 변경하지 않는다. Jekyll이 `resume/`를 정적 파일로 복사하며, 현재 Pages 워크플로로 배포한다.

큰 소개 제목, 기관·기간과 프로젝트를 나눈 2열 구성, Description / What did I do / Tech Stack의 정보 순서는 [이현섭님의 이력서](https://hyunseob.github.io/resume/)를 참고했다. 본문·스타일·구현은 별도로 작성했다.

## 편집 기준

- 회사 경력이 아닌 활동은 프로그램·기관과 연수생/교육생 역할을 함께 표시한다.
- 팀 성과, 개인 작업, 합성 실험, 실측과 계산 예시를 구분한다.
- 과거 스케줄러 수치를 현재 평가 정책의 무조건적 성능으로 바꾸지 않는다.
- Mac·MLX API 서빙은 완료한 범위로 표시한다. QLoRA 학습 완료와 GPU·vLLM 서빙 운영은 별개로 다룬다.
- 비공개 저장소의 코드, 원문 로그, 증명서와 개인 식별정보를 공개하지 않는다.

## 확인

```bash
python3 tools/resume/check_resume.py
node --check resume/resume.js
```

저장소 `AGENTS.md`의 전체 검사와 Jekyll 빌드도 실행한다. 브라우저에서 데스크톱·좁은 화면의 텍스트 줄바꿈, 앵커 이동과 인쇄용 스타일을 확인한다.
