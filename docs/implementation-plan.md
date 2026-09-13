# Human-ton Implementation Plan

> 같은 작업 세션에서 실행하는 계획이다. 하위 작업은 설치 도구, 문자열 대조 도구, 스킬 편집 지침으로 나누며 파일 소유 범위를 겹치지 않게 한다.

**Goal:** 의미와 목소리를 보존하는 윤문 스킬을 만들고 세 CLI에서 설치·사용할 수 있게 한다.

**Architecture:** `skills/human-ton/` 하나를 설치 원본으로 사용한다. 언어·리듬·장르 참고 문서는 조건부로 읽고, Kiro 에이전트 설정은 설치 단계에서 경로만 맞춘다.

**Tech Stack:** Markdown, YAML, JSON, Python 3.9+ 표준 라이브러리.

**Spec:** [design.md](design.md).

## 공통 조건

- 세 도구의 원고 편집 기준은 동일하다.
- 스킬 실행에는 Python·하위 에이전트·외부 서비스가 필수가 아니다.
- 설치 도구는 기존 사용자 파일을 임의로 덮어쓰지 않는다.
- 평가 결과는 실제 수행한 범위만 보고한다.

## 1. 공통 스킬

- [x] 지정한 세 저장소의 내용·커밋·라이선스를 확인한다.
- [x] 스킬 없는 대조군을 다섯 번 실행한다.
- [x] `SKILL.md`와 언어·리듬·목소리·예시 참고 문서를 작성한다.
- [x] 동일 요청과 별도 사례를 스킬과 함께 실행한다.
- [x] 실제 실패가 드러난 지침만 고쳐 다시 검증한다.

검증 명령:

```bash
python3 /home/ec2-user/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/human-ton
```

첫 번째 명령은 제작 환경의 검증 도구다. 패키지 사용자의 설치 조건이 아니다.
Claude의 플러그인 검증 명령은 이 환경에서 스킬 검사 항목을 반환하지 않아 성공 근거로 쓰지 않았다. 실제 `/human-ton` 호출로 별도 확인했다.

## 2. 설치 도구

파일: `scripts/install.py`, `tests/test_install.py`, `integrations/kiro/human-ton.json`.

- [x] 임시 디렉터리에서 복사·경로·충돌·재실행·백업·드라이런·심볼릭 링크 사례를 시험한다.
- [x] `--target`, `--scope`, `--project-dir`, `--dry-run`, `--replace`를 구현한다.
- [x] 세 대상 설치 후 원본 저장소 없이도 참고 파일이 열리는지 확인한다.

```bash
python3 -m unittest discover -s tests -p 'test_install.py' -v
kiro-cli agent validate --path integrations/kiro/human-ton.json
```

## 3. 선택적 문자열 점검

파일: `skills/human-ton/scripts/check_literals.py`, `tests/test_check_literals.py`.

- [x] 수치·단위·URL·인용·코드·보호 문자열 변경 시험을 먼저 실행한다.
- [x] 읽기 전용 비교와 JSON 출력, 종료 코드 `0/1/2`를 구현한다.
- [x] 같은 숫자의 대상 교환을 놓치는 한계도 시험으로 남긴다.

```bash
python3 -m unittest discover -s tests -p 'test_check_literals.py' -v
```

## 4. 전달

- [x] 출처·적용 한계·원 저작권 고지를 패키지에 넣는다.
- [x] 사용 예시와 도구별 설치·호출·제거 방법을 README에 적는다.
- [x] 전체 검증을 실행하고 평가 기록을 정리한다.
- [x] 검증된 스킬을 설치하고 실제 설치 위치를 확인한다.
