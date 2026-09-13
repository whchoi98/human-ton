# Human-ton

의미와 필자의 목소리를 지키면서 문장과 문단의 호흡을 다듬는 스킬입니다. 한국어를 중심으로 영어·혼합 원고도 다룹니다. 같은 스킬을 **Codex, Claude Code, Kiro CLI**에 설치할 수 있습니다.

“검토를 진행했습니다”는 “검토했습니다”로 줄일 수 있습니다. “검토할 수 있습니다”는 가능성을 담고 있으므로 “검토하겠습니다”로 바꾸지 않습니다. 이미 잘 읽히는 글은 그대로 둡니다.

## 설치

이 저장소 폴더에서 실행합니다. 설치 도구는 Python 3.9 이상만 필요합니다.

```bash
# 설치 위치와 충돌 여부 먼저 확인
python3 scripts/install.py --target all --scope user --dry-run

# 세 도구에 개인 스킬로 설치
python3 scripts/install.py --target all --scope user
```

한 도구만 설치하려면 `--target claude`, `--target kiro`, `--target codex`를 사용합니다. 특정 프로젝트에 설치하려면 다음처럼 실행합니다.

```bash
python3 scripts/install.py --target all --scope project --project-dir "/내/프로젝트"
```

| 도구 | 개인 설치 | 프로젝트 설치 |
| --- | --- | --- |
| Codex | `~/.agents/skills/human-ton/` | `.agents/skills/human-ton/` |
| Claude Code | `~/.claude/skills/human-ton/` | `.claude/skills/human-ton/` |
| Kiro CLI | `~/.kiro/skills/human-ton/` | `.kiro/skills/human-ton/` |

Kiro에는 같은 범위의 `.kiro/agents/human-ton.json`도 설치합니다. 전용 에이전트가 `skill://` 리소스로 스킬을 읽습니다. 이 에이전트에는 파일 읽기·편집 도구가 있고, 읽기만 자동 허용합니다.

설치 내용이 같으면 아무것도 바꾸지 않습니다. 기존 내용과 충돌하면 중단합니다. 업데이트할 때는 `--replace`를 붙이면 이전 내용을 설치 기준 폴더의 `.human-ton/backups/`에 보관한 뒤 교체합니다. 백업은 스킬 탐색 경로 밖에 둡니다.

스킬 실행 자체에는 Python이 필수가 아닙니다. 수동 설치하려면 `skills/human-ton` **폴더 전체**를 위 경로로 복사하세요. Kiro 전용 에이전트도 사용하려면 `integrations/kiro/human-ton.json`을 `.kiro/agents/`에 복사하고, 개인 설치에서는 `resources`를 `["skill://~/.kiro/skills/human-ton/SKILL.md"]`로 바꿉니다.

## 사용

새 세션을 열거나 설치된 스킬 목록을 새로 불러옵니다.

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

시작한 대화에 원고와 함께 요청합니다.

```text
human-ton 스킬로 아래 원고를 자연스럽게 다듬어 줘. 사실과 말투는 유지해 줘.
```

설치 후에도 스킬이 보이지 않으면 이름이 `human-ton`이고 폴더 안에 `SKILL.md`가 있는지 확인하세요. Kiro에서 다른 커스텀 에이전트를 사용 중이면 해당 에이전트의 `resources`에 이 스킬의 `skill://` 경로를 추가해야 할 수 있습니다. 전용 `human-ton` 에이전트에는 경로가 이미 들어 있습니다.

## 요청 예시

- `가볍게 다듬어 줘. 내 말투는 최대한 살려 줘.`
- `기술 블로그 독자에게 맞춰 문장과 문단의 연결을 적극적으로 다듬어 줘.`
- `이 문서의 둘째 문단만 고치고 나머지는 그대로 둬.`
- `진단만 해 줘. 읽기 어려운 부분과 이유를 알려 줘.`
- `해요체로 바꿔 줘. 인용문은 그대로 둬.`
- `이 샘플의 담백한 문체를 참고해 줘. 샘플의 내용은 가져오지 마.`
- `draft.md를 윤문해서 draft.polished.md에 저장해 줘.`
- `Polish this paragraph while keeping its meaning, register, and voice.`

기본은 완성된 본문을 돌려줍니다. 전후 비교나 변경 이유는 요청할 때 덧붙입니다. 자연스럽게 바꾸는 일과 요약·번역·새 내용 집필을 구분합니다.

## 편집 기준

원문의 사실·수치·인용·조건·부정·확신 정도를 보존합니다. 불필요한 명사 나열과 번역투를 풀고, 정보가 이어지는 순서와 문단의 역할을 살핍니다. 어미나 문장 길이를 일정한 공식에 맞추지 않으며, 자연스럽게 보이려고 새 경험담·감정·성과·오탈자를 보태지 않습니다.

엠대시(—)로 설명을 반복해서 끊거나 가운뎃점(·)으로 산문의 명사를 과하게 묶는 경우도 다룹니다. 문장 분리나 쉼표, 조사로 풀어 쓰되 인용문, 고유명사, 코드, 수식의 표기는 보존합니다. 필요하면 “엠대시와 가운뎃점을 빼고 다듬어 줘”라고 명시할 수 있습니다.

문자열 점검이 필요하면 선택적으로 실행할 수 있습니다.

```bash
python3 skills/human-ton/scripts/check_literals.py original.md revised.md \
  --protect "제품명" --protect "p95"
```

이 도구는 수집한 문자열의 추가·누락을 찾습니다. 의미나 자연스러움을 판단하지 않습니다. 자세한 범위는 [문자열 대조 안내](skills/human-ton/references/literal-checks.md)에 있습니다.

## 구성과 검증

- [SKILL.md](skills/human-ton/SKILL.md): 공통 편집 절차와 출력 기준
- [references](skills/human-ton/references): 한국어·영어, 리듬, 목소리, 예시, 참고 자료
- [설치 도구](scripts/install.py): 복사·충돌 확인·백업
- [평가 기록](docs/evaluation.md): 대조군, 스킬 적용 결과, 도구별 확인 범위
- [평가 원고](evals/cases.json): 원문과 검토 기준

```bash
python3 -m unittest discover -s tests -v
```

제거하려면 설치 표에 있는 **`human-ton` 폴더만** 삭제하고, Kiro는 같은 범위의 `agents/human-ton.json`도 삭제합니다. 교체 전 상태로 돌아가려면 `.human-ton/backups/`에서 해당 항목을 원래 경로로 복원합니다.

## 참고와 라이선스

사용자가 지정한 `epoko77-ai/im-not-ai`, `Squirbie/im-not-ai-codex`, `amondnet/yoonmoon`의 실제 지침을 비교하고, 번역투 연구와 공식 문서 작성 지침을 함께 참고했습니다. 적용한 방법과 한계는 [출처 문서](skills/human-ton/references/sources.md)에 기록했습니다.

[MIT](LICENSE). 참고 프로젝트의 저작권·허가 고지는 설치되는 폴더의 [THIRD_PARTY_NOTICES.md](skills/human-ton/THIRD_PARTY_NOTICES.md)에 포함되어 있습니다.
