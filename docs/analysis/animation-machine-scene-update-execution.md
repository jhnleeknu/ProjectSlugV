# `480bc` U4 장면 갱신 `1a7a8` 실행부 검증 기록

**상태: 검증 기록.** 대상은 워크트리 커밋 `b6b79ac`의 `engine/src/animation_machine_scene_update.cpp`(U4 계약 선택 D). [F]=이 검증기가 확인한 사실, [I]=추론, [U]=미확인. 검증기: `tools/verify_animation_machine_scene_update.py`, 결과: `artifacts/animation_machine_scene_update_execution/verification.json`(Git 제외).

## 입력(SHA256 고정)
- 계약 `animation-machine-scene-update-u4-contract.md` `68855b9567d285c4bcd6d3ae3e1024d304384ed03e4b1fc3401dfe0b5a1637dc`.
- 원본 관측 `artifacts/animation_machine_scene_update_native/observation.json` `fdceb7710a9c73ca6ceb7459475ac6f6d05ebd26529510e7b516ab8cc1f9a063`, 관측 도구 `8ea6a0a9881bd48f262c15bff341822d10a9617d4f5b590ab8060a0132f9b981`. 관측 입력 674개와 산출물 파일 전부의 해시를 다시 확인했다. 원본 ROM `29112a94...c886c860f` 불변.

## 정적 검증 [F]
- 계약 바이트 표 10행을 ROM과 대조(코드 1486바이트 405명령, 자료 200바이트). 코드 7범위는 명령 사이 빈틈이 없다.
- block 시작 118(102+16), 묶인 분기 46, FLOW_ONLY 55를 계약에서 읽었고, 원본 opcode에서 독립 유도한 leader 집합·묶인 분기 집합·FLOW_ONLY 집합과 정확히 일치한다. C++ `case` 레이블 집합 = 계약 118.
- C 생산자(ORI/ANDI/EORI/MOVE to CCR) 0, C 소비 block 0. X 사용 명령은 `17258 17278 1b058 1b074`뿐이고 각 생산자가 같은 block 안에 먼저 있다(X는 block 지역).

## 실제 C++ 비교 [F]
- 343 행(정상 325 + guard 18), split 12171 phase, 연속 대조 369 step, 재개 11802회. 매 phase 전체 64KiB RAM·16 레지스터·PC·A7·PVC 장치·bank·순서 있는 port(디버그 격자 1280 LONG 포함, port 233586개)·외부 읽기(0)·status를 원본 기록과 비교했다. 기존 실행부 `43e38 16ff8 1861a 18702 caf0`는 결과 전체로 비교.
- 재개는 직전 실제 C++ 출력 + 선언된 host 변경으로만 했다. 자연 행 22개는 U2(`1a73c`→`1a7a8`)와 U4(→`1a78c`) 두 step을 연속 실행.
- 시작 상태: scene_frame 재구성 22행(관측 provenance SHA와 대조); 실제 C++ 출력에서 만든 시작 131행(scene case 36의 `1afda`/`1a8ce` 기반 + 선언 RAM 쓰기, SHA·레지스터·A7·PVC·bank 확인); SHA 고정 선언 원본 상태 190행. 선언 상태 중 다른 행의 실제 C++ 연쇄 출력과 독립 재현된 것은 6개뿐(나머지 206은 원본 산출물 SHA 고정으로만 보증) [U].
- `1a69e` 진입 행 20개 + guard 1개: `1a69e`의 BSR.W는 C++ 범위가 아니므로 host 측 BSR(복귀 LONG `1a6a2` push, PC `1a7a8`)로 대체하고 원본 phase(레지스터·RAM·단일 쓰기 이벤트)와 독립 대조한 뒤 C++를 `1a7a8`부터 실행했다.
- 원본 split 정지 PC는 모두 U4 block 시작 또는 기존 실행부 진입이거나 최종 정지(`1a78c`/`1a6a2`)여서 병합이 필요 없었다.
- Carry: C++ carry = 원본 opcode 분류(Unknown 11877, Clear 109, Set 165; 자연 행의 U2 구간은 U2 규칙). 매 phase 입력 C=Set/Clear 탐침 2회(24302회), 불일치 0. U4 단독 단일 block 98개 탐침 중 46개가 입력 C 보존(FLOW_ONLY 55 중 단일 block 탐침 가능분). 118개 block 시작 모두 실제 C++ phase의 첫 PC로 실행됨.
- 원본 ROM 읽기 감사: fixed 38470, bank 320164, PVC 쓰기 1164. C++ vs 원본 불일치 0 [F].

## guard·부정 검사 [F]
- 원본 guard 18개를 phase와 전체 step 기준으로 실행: 정확한 오류 문자열과 전체 API 출력 보존(RAM·PVC·bank·레지스터·carry·port marker·status). 홀수 읽기/쓰기/push/RTS = `program bus requires even WORD/LONG address`, ROM 쓰기 = `unsupported animation machine write device`, ROM push = `program bus write requires RAM mirror units`; path opcode 계산 PC: `19e8c`·`19e90` = `unsupported animation scene update PC`, `21e88` = `unsupported animation machine PC`, 홀수 = `unaligned animation machine PC`; 도달하지 않는 stop 2개 = `unsupported animation machine PC`.
- API 전용 부정 653개(총 671 = guard 18 + 653): 내부 명령 PC 287, 피연산자 WORD PC 338, 디버그 표 자료 PC, 범위 밖 이웃·`1a470`·`1a6a2`·`1a69e`, 홀수 PC, 도달하지 않는 stop. 정상 stop 5개 대조군.
- zero-step: 118 block 시작 × carry 3 = 354, 모두 입력과 동일. 경계 zero-step(`1a78c 1a6a2 1a69e 1a7a8`)은 모두 ok.

## 미확인·제한 [U]
- 통제된 fixture이며 자연 스케줄러·IRQ·게임 진행 도달성은 아니다. 미관측 경로(조건 opcode 08/0c/10/14, 1c 등)는 원본 선언 fixture의 host 쓰기로만 검증됐다.
- 실패는 API 출력 보존이지 원본 CPU 예외 롤백이 아니다. 기존 실행부 내부와 U2 꼬리·U5는 이 검증 대상이 아니다.
- 구버전 검증기 `tools/verify_animation_machine_scene_core.py`는 `1a7a8`을 미지원으로 가정(BOUNDARY_PCS, outside 목록, `guard-bad-stop-1a7a8-on-19844-seed`, 한계 문구)하므로 갱신이 필요하다(이 작업에서는 수정하지 않음).
