# 참고한 방법과 적용 한계

확인일: **2026-09-13**. 저장소는 아래 커밋의 실제 파일을 읽었고, 제품 사양은 공식 문서를 확인했다. 이 문서는 출처·설계 배경이 필요한 경우에만 읽는다.

## 사용자가 지정한 세 저장소

| 자료 | 확인한 버전 | 반영한 관점 | 이 스킬의 선택 |
| --- | --- | --- | --- |
| [epoko77-ai/im-not-ai](https://github.com/epoko77-ai/im-not-ai) | `9747f036cdc28a1a8aea4dc71fef1f7846eb96f7` · 2026-09-07 · MIT | 한국어 표현을 문맥별로 살피는 분류, 의미·양태 보존, 수정 후 원문 대조 | 복잡한 실행 경로와 정량 게이트 대신 짧은 공통 절차를 둔다 |
| [Squirbie/im-not-ai-codex](https://github.com/Squirbie/im-not-ai-codex) | `028957ddbfe51c70b573d1fa37f8ab5c28e34866` · 2026-05-08 · MIT | 다른 런타임으로 옮길 때 역할의 행동과 도구 호출을 분리하는 방식 | 특정 `Agent` 도구·모델·환경변수 없이 같은 문서로 실행한다 |
| [amondnet/yoonmoon](https://github.com/amondnet/yoonmoon) | `c88853106c8fa8448447136f5aa3fc8bb9650303` · 2026-09-11 · MIT | 번역투 교정과 톤 전환의 구분, 삭제 뒤 의미가 미달하는 문제, 필요한 단계만 적용 | 하나의 스킬에서 요청 범위를 정하고 필요한 참고 문서만 읽는다 |

주요 열람 파일:

- `im-not-ai`: `skills/humanize-korean/SKILL.md`, 관련 파일 목록, `LICENSE`.
- `im-not-ai-codex`: `plugins/im-not-ai/skills/humanize-korean/SKILL.md`, `SOURCE.md`, `LICENSE`.
- `yoonmoon`: `skills/humanize/SKILL.md`, `skills/polish-all/SKILL.md`, `skills/restyle/SKILL.md`, `rewriting-guide.md`, `katfishnet-research.md`, `translationese-research.md`, `docs/research.md`, `LICENSE`.

지침·예시·설치 도구·문자열 점검 코드는 이 패키지에서 새로 작성했다. 세 저장소의 프롬프트·분류표·코드·수치 기준을 그대로 이식한 패키지는 아니다. 참고 저장소의 MIT 고지는 [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md)에 함께 둔다.

## 언어 연구와 편집 지침

### KatFishNet — 한국어의 특성을 따로 볼 근거

Shinwoo Park, Shubin Kim, Do-Kyung Kim, Yo-Sub Han. 2025. *KatFishNet: Detecting LLM-Generated Korean Text through Linguistic Feature Analysis*. ACL, pp. 21189–21222.

- [ACL 원 페이지](https://aclanthology.org/2025.acl-long.1030/)
- 확인 범위: 서지와 초록. 한국어의 띄어쓰기·품사 다양성·쉼표 사용을 분석하며 영어 중심 접근을 그대로 옮기기 어려움을 설명한다.
- 적용: 한국어와 영어 참고 문서를 나누고, 쉼표·표현·구조를 문맥 안에서 점검한다.
- 한계: **탐지 연구의 성능이 윤문 품질을 입증하지는 않는다.** 쉼표를 지우거나 품사 다양성을 높이면 좋은 글이 된다는 규칙으로 사용하지 않는다. 참고 저장소 사이에서도 다양성의 방향을 다르게 설명하는 부분이 있어 그 방향이나 임계값을 채택하지 않았다.

### Post-editese — 매끈함과 좋은 문체를 구분할 근거

Antonio Toral. 2019. *Post-editese: an Exacerbated Translationese*. Machine Translation Summit XVII: Research Track, pp. 273–281.

- [ACL 원 페이지](https://aclanthology.org/W19-6627/) · [논문 PDF](https://aclanthology.org/W19-6627.pdf)
- 확인 범위: 서지와 PDF의 초록·도입부. 기계번역 후편집과 처음부터 수행한 인간 번역을 비교하고 단순화·규범화·출발어 간섭을 조사한다.
- 적용: 매끄러워 보인다는 이유만으로 계속 고치지 않고, 필자의 어휘와 리듬이 필요 없이 평준화되지 않았는지 본다.
- 한계: 연구 대상은 특정 데이터셋과 번역 방향이다. 모든 한국어 LLM 문장이나 Human-ton의 효과에 대한 실험으로 해석하지 않는다.

### Google 개발자 문서 작성 지침 — 독자와 의미를 중심에 두는 편집

- [Voice and tone](https://developers.google.com/style/tone): 본문 확인. 독자가 필요한 정보를 얻도록 돕는 자연스러운 문체, 지나친 구어·장난의 배제, 읽어 보며 흐름을 확인하는 접근을 참고했다.
- [Sentence structure](https://developers.google.com/style/sentence-structure): 본문 확인. 독자가 지시의 적용 여부를 먼저 판단할 수 있게 조건·맥락을 배치하는 방식을 참고했다.
- 적용 한계: 개발자 문서의 지침이다. 기술 문서에서 유용한 원칙을 참고하되 에세이나 모든 한국어 높임 체계에 같은 말투를 강제하지 않는다. 해당 페이지의 예문이나 본문을 이 패키지에 복제하지 않았다.

### 국립국어원 — 글의 목적과 유형 확인

- [쉬운 공문서 쓰기 길잡이](https://www.korean.go.kr/front/etcData/etcDataView.do?etc_seq=700), 2022 자료, 2023-02-02 등록.
- 확인 범위: 공식 소개 페이지와 목차. 공공언어의 요건, 작성 단계, 문서 유형을 구분한 구성을 참고했다.
- 이 작업에서는 첨부 PDF의 개별 규범 조항을 인용하거나 새 맞춤법 규칙을 만들지 않았다.

## 공통 형식과 런타임 문서

| 공식 자료 | 사용한 내용 |
| --- | --- |
| [Agent Skills specification](https://agentskills.io/specification) | `SKILL.md`, 이름·설명, 폴더 구조, 단계적으로 참고 자료 읽기 |
| [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills) | Codex의 `.agents/skills`, 명시적 `$` 호출, `agents/openai.yaml` |
| [Claude Code: Skills](https://code.claude.com/docs/en/skills) | `.claude/skills`, `/스킬명`, 같은 폴더에 두는 참고 자료 |
| [Kiro: Agent Skills](https://kiro.dev/docs/skills/) | `.kiro/skills`, `skill://` 리소스, 공통 스킬 형식 |
| [Kiro: Agent configuration](https://kiro.dev/docs/custom-agents/configuration-reference/) | 별도 에이전트의 `resources`와 이름·설명·프롬프트 |

Kiro 문서의 페이지마다 커스텀 에이전트의 기본 리소스 상속에 관한 설명에 차이가 있었다. 설치하는 전용 에이전트에 정확한 `skill://` 경로를 넣어 기본 상속 여부에 의존하지 않게 했다. 버전별 실제 확인 결과는 저장소의 `docs/evaluation.md`에서 구분한다.

## 자체 설계와 평가의 경계

내용 보존 검수, 리듬 편집, 이미 좋은 글을 유지하는 판단을 결합한 것은 이 프로젝트의 설계다. “짧게-길게” 비율, 변경률 `30%/50%`, AI 판정 점수, 출처 데이터셋의 평균값을 보편적인 합격선으로 사용하지 않는다.

평가는 원문과 결과를 대조하는 소규모 사례 시험이다. 에이전트가 스킬을 따르는지 확인하는 데 도움이 되지만, 사람 독자의 선호나 모든 모델·장르에서의 성능을 증명하는 연구는 아니다.
