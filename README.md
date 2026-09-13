# Human-ton

원문의 뜻과 말투를 살리면서 문장과 문단의 호흡을 다듬는 스킬입니다. 한국어를 주로 다루며, 영어 원고나 두 언어가 섞인 글에도 쓸 수 있습니다. **Codex, Claude Code, Kiro CLI**에 같은 스킬을 설치해 사용합니다.

“검토를 진행했습니다”는 “검토했습니다”로 줄일 수 있습니다. 하지만 “검토할 수 있습니다”를 “검토하겠습니다”로 바꾸면 가능성이 약속으로 달라집니다. 이런 차이를 지키면서 다듬고, 이미 잘 읽히는 글은 그대로 둡니다.

## 설치

설치 도구는 Python 3.9 이상만 있으면 실행할 수 있습니다. 저장소 폴더에서 아래 명령을 실행하세요.

```bash
# 설치 위치와 충돌 여부 먼저 확인
python3 scripts/install.py --target all --scope user --dry-run

# 세 도구에 개인 스킬로 설치
python3 scripts/install.py --target all --scope user
```

한 도구에만 설치하려면 `--target claude`, `--target kiro`, `--target codex` 중 하나를 지정하세요. 특정 프로젝트에서만 쓰려면 설치할 폴더를 다음처럼 지정합니다.

```bash
python3 scripts/install.py --target all --scope project --project-dir "/내/프로젝트"
```

| 도구 | 개인 설치 | 프로젝트 설치 |
| --- | --- | --- |
| Codex | `~/.agents/skills/human-ton/` | `.agents/skills/human-ton/` |
| Claude Code | `~/.claude/skills/human-ton/` | `.claude/skills/human-ton/` |
| Kiro CLI | `~/.kiro/skills/human-ton/` | `.kiro/skills/human-ton/` |

Kiro에는 같은 범위의 `.kiro/agents/human-ton.json`도 설치됩니다. 이 전용 에이전트는 `skill://` 리소스로 스킬을 읽습니다. 파일을 읽고 편집하는 도구가 있으며, 읽기만 자동으로 허용합니다.

이미 같은 내용이 설치되어 있으면 건너뜁니다. 기존 내용과 다르면 설치를 멈춥니다. 업데이트하려면 `--replace`를 붙이세요. 이전 내용을 설치 기준 폴더의 `.human-ton/backups/`에 보관한 뒤 교체합니다. 백업 폴더는 스킬을 찾는 경로 밖에 있습니다.

직접 설치하려면 `skills/human-ton` **폴더 전체**를 위 표의 경로로 복사하세요. 스킬을 사용하는 데는 Python이 꼭 필요하지 않습니다.

Kiro 전용 에이전트도 쓰려면 `integrations/kiro/human-ton.json`을 선택한 범위의 `.kiro/agents/`에 복사합니다. 개인 설치라면 `resources`를 `["skill://~/.kiro/skills/human-ton/SKILL.md"]`로 바꾸세요.

## 사용

설치를 마쳤으면 새 세션을 열거나 스킬 목록을 새로 불러오세요.

**Codex**

```text
$human-ton 아래 원고의 의미와 말투를 유지하면서 자연스럽게 다듬어 줘.
```

**Claude Code**

```text
/human-ton 이 글의 번역투를 줄이고 문장 호흡을 다듬어 줘. 결과만 보여 줘.
```

**Kiro CLI**

```bash
kiro-cli chat --agent human-ton
```

대화가 시작되면 원고와 함께 다음처럼 요청하세요.

```text
human-ton 스킬로 아래 원고를 자연스럽게 다듬어 줘. 사실과 말투는 유지해 줘.
```

스킬이 보이지 않으면 폴더 이름이 `human-ton`인지, 그 안에 `SKILL.md`가 있는지 확인하세요.

Kiro에서 다른 커스텀 에이전트를 쓰고 있다면 그 에이전트의 `resources`에 이 스킬의 `skill://` 경로를 추가해야 할 수 있습니다. 전용 `human-ton` 에이전트에는 경로가 이미 들어 있습니다.

## 요청 예시

- `가볍게 다듬어 줘. 내 말투는 최대한 살려 줘.`
- `기술 블로그 독자에게 맞춰 문장과 문단의 연결을 적극적으로 다듬어 줘.`
- `이 문서의 둘째 문단만 고치고 나머지는 그대로 둬.`
- `진단만 해 줘. 읽기 어려운 부분과 이유를 알려 줘.`
- `해요체로 바꿔 줘. 인용문은 그대로 둬.`
- `이 샘플의 담백한 문체를 참고해 줘. 샘플의 내용은 가져오지 마.`
- `draft.md를 윤문해서 draft.polished.md에 저장해 줘.`
- `Polish this paragraph while keeping its meaning, register, and voice.`

기본 응답은 다듬은 본문입니다. 전후 비교나 바꾼 이유가 필요하면 함께 요청하세요. 요약이나 번역, 새 내용을 쓰는 작업은 윤문과 구분해 처리합니다.

## 편집 기준

원문의 사실과 수치, 인용을 지킵니다. 조건이나 부정 표현이 빠지지 않았는지, 조심스러운 판단이 단정으로 바뀌지 않았는지도 확인합니다.

문장을 손볼 때는 불필요한 명사 나열과 번역투를 풀고, 앞뒤 정보가 잘 이어지는지 살핍니다. 문단마다 어떤 내용을 전하는지도 봅니다. 어미와 문장 길이를 공식에 맞추거나, 자연스럽게 보이려고 없던 경험담과 감정, 성과, 오탈자를 보태지는 않습니다.

엠대시(—)로 설명을 자꾸 끊거나 가운뎃점(·)으로 명사를 길게 묶은 산문도 다듬습니다. 문장을 나누거나 쉼표와 조사로 풀어 쓰되, 인용문과 고유명사, 코드, 수식의 표기는 보존합니다. 원하는 경우 “엠대시와 가운뎃점을 빼고 다듬어 줘”라고 요청하세요.

원문과 수정본의 문자열을 점검하려면 다음 도구를 사용할 수 있습니다.

```bash
python3 skills/human-ton/scripts/check_literals.py original.md revised.md \
  --protect "제품명" --protect "p95"
```

이 도구는 찾아낸 문자열 가운데 무엇이 추가되거나 빠졌는지 확인합니다. 뜻이 같은지, 글이 자연스러운지는 판단하지 않습니다. 확인할 수 있는 범위는 [문자열 대조 안내](skills/human-ton/references/literal-checks.md)에 정리했습니다.

## 구성과 검증

- [SKILL.md](skills/human-ton/SKILL.md): 공통 편집 절차와 출력 기준
- [references](skills/human-ton/references): 한국어와 영어의 편집 기준, 리듬과 말투에 관한 설명, 예시와 참고 자료
- [설치 도구](scripts/install.py): 스킬 복사, 기존 파일과의 충돌 확인, 백업
- [평가 기록](docs/evaluation.md): 대조군, 스킬 적용 결과, 도구별 확인 범위
- [평가 원고](evals/cases.json): 원문과 검토 기준
- [변경 이력](CHANGELOG.md): 버전별로 추가하거나 고친 내용

설치 도구와 문자열 대조 도구의 테스트는 다음 명령으로 실행합니다.

```bash
python3 -m unittest discover -s tests -v
```

## 제거와 복원

스킬을 제거하려면 설치 표에 있는 **`human-ton` 폴더만** 삭제하세요. Kiro는 같은 범위의 `agents/human-ton.json`도 삭제합니다.

교체 전 상태로 돌아가려면 `.human-ton/backups/`에 보관된 항목을 원래 경로로 복원하세요.

## 참고한 자료와 라이선스

스킬을 만들며 `epoko77-ai/im-not-ai`, `Squirbie/im-not-ai-codex`, `amondnet/yoonmoon`의 지침을 읽고 비교했습니다. 번역투 연구와 공식 문서 작성 지침도 참고했습니다. 어떤 방법을 적용했고 어디까지 참고했는지는 [출처 문서](skills/human-ton/references/sources.md)에 기록했습니다.

[MIT](LICENSE) 라이선스로 제공합니다. 참고한 프로젝트의 저작권 고지와 이용 허가문은 설치 폴더의 [THIRD_PARTY_NOTICES.md](skills/human-ton/THIRD_PARTY_NOTICES.md)에 담았습니다.
