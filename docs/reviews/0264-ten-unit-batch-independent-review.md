# 10개 주 작업 단위 묶음 독립 리뷰 (2026-10-16)

`0263-ten-unit-batch.md`에서 건너뛴 독립 리뷰다. 대상은 PR #2가 병합한 범위 `cc88bde..e5bfb73`(41 commit, 84 file, +26,142/−90)이다.

- 단위: M1, V1, C1, C2, C3a/C3b, D9, F6a, F6b, F6c, F6-D, B1a/B1b/B1c, B2a/B2b.
- 리뷰어: Claude Opus 5.5 / high. 독립 작업자이며 코드와 도구는 고치지 않았다.
- 작업 위치: worktree `/Users/start/Workspce/metalslug-review`(branch `claude/review-wip`, `e5bfb73` = `origin/main`). scratch 출력은 `/Users/start/Workspce/ms5-scratch/review0264/`에 두었다.
- 환경: macOS 원 환경(Darwin 25.4.0), Apple clang++, Python 3.14 venv, capstone 5.0.6, Unicorn 2.1.4.
- ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8,388,608바이트. 읽기 전용으로 썼다. 리뷰 시작과 끝에 SHA·mtime이 같았다(`mtime 1791291625`). 이 문서의 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다.
- 표기: [F] 사실, [I] 추론, [U] 미확인.

## 요약
- **C++ 실행부의 원본 대응에서 결함은 찾지 못했다.** 확인한 범위는 routing 겹침 0, carry 보존 목록 510 PC 위반 0, 표본 ROM 대조, 정수 연산 UB 없음이다.
- 실행 비교도 모두 통과했다.
  - V1 spec 13개 15,782/15,782
  - D1 전체 54,400/54,400(역사 seed)
  - D9 (ii)·(iii)·F6-D 3 seed 표본
  - `make -j3 all test` 종료 0
- **문제는 검증 체계와 회귀 관리 쪽이다.**
  - pin된 예전 검증기 2개가 실제로 실패한다(M-1).
  - 자연 seed 검증기가 macOS 원 환경에서 실행되지 않는다(M-2).
  - 다음 단위 PC를 탐침으로 고정했다(M-3).
  - 기대 오류의 위치를 확인하지 않는다(L-1).
  - acceptance가 `verifier-error`를 세지 않는다(L-2).
  - Makefile 헤더 목록 중복(L-3, 메인이 `b6bc035`에서 수정), 예전 fixture 삭제(L-4).

## 방법
1. **변경 읽기.** 단위별 diff를 읽었다. 대상은 실행부 11개, `animation_machine.cpp` routing·carry 목록·palette 장치, frame 구동기, 하네스 3개, V1, spec 13개, 계약 문서다.
2. **ROM 대조.** capstone M68000으로 직접 역어셈블해 실행부 case와 대조했다. 이번에 대조한 것은 아래와 같다.
   - C1: `ca06` SBCD, `ca32`, `4a974..4a9e0`, `30bc` `30d4` `314c`, `c988..ca20`
   - C3: `c52a..c64c`, `c6da..c720`, `4fb1a..4fb48`, `8b64..8bbc`
   - C2: `49a1a..49a56`, `c686`, menu 표 `a810`
   - F6a: `20c..2d6`, `a2c..b0a`, `c8c..d54`, `3cac..3d38`, `16092`/`166a0` 머리, `16cfa`, `16e7a..16ea2`
   - F6b: `72f0..7326`, `871a..8b64`
   - 그 밖에 wait block 6곳, B1c `30b6c` 표·`335e8` 표, B1b `3da98..3dacc`, B2a `60670..6069c`, IRQ vector `64` `68` `6c`
   - 표·반복 구조는 스크립트로 바이트를 대조했다.
3. **routing 겹침.** `animation_machine.cpp` dispatch 사슬 109개 규칙을 Python 조건식으로 옮겼다(`stage_event_ops_trap`은 참으로 둔 상위 집합). 새 11개 실행부가 차지하는 짝수 PC 전부를 다른 모든 규칙과 대조했다.
4. **carry 목록.** `carry_preserving_pc`에 이번에 더한 510개 PC를 확인했다. 각 PC부터 같은 실행부의 다음 case 시작 전까지를 ROM에서 역어셈블해, C를 쓰는 명령이 있는지 정적으로 검사했다. 이어서 known-C 생산자(`r.carry=` Set/Clear) 전부를 ROM 명령과 대조했다.
5. **실행 검증.** 아래 "검증 명령과 결과"에 적은 명령을 최대 3 process로 돌렸다. 출력은 모두 scratch에 두고 공유 `artifacts/`에는 쓰지 않았다.
   - 전체 `make -j3 all test`
   - V1 spec 13개 전부
   - F6c 템플릿 증명
   - pin된 예전 검증기 3개(fade_card, card_menu_close, stage_catalog): OUT만 scratch로 바꾼 사본으로 실행
   - D9·F6-D·D1 원본 비교

## 발견 사항 (심각도 순)

### M-1 (중간) pin된 예전 검증기의 기대값이 새 routing으로 깨졌는데 대부분 기록되지 않았다
`0263`의 "기록되지 않은 시험 기대값"은 `verify_animation_machine_frame_controller.py`의 c3b 경계와 fade_card `4c3a2` 두 가지만 적었다. 이번 리뷰에서 확인한 범위는 더 넓다. C++ 단위 시험(`engine/tests/*`)은 고쳤지만 같은 PC를 쓰는 Python 검증기는 그대로다.

| 검증기:행 | 기대 | 새 소유 | 결과 |
| --- | --- | --- | --- |
| `tools/verify_animation_machine_fade_card.py:154`, `:425` | guard `guard-alloc-return-clobbered`: 대상 `4c3a2`에서 `unsupported animation machine PC` | B2b(`4c390..4c3ba`) | **[F] 실행 실패.** `AssertionError: ('guard-alloc-return-clobbered', 'program bus requires even WORD/LONG address')` |
| `tools/verify_animation_machine_card_menu_close.py:658-661` | `outside = (0x9ee6, 0xc2fa, 0xc2fc)` → `unsupported animation machine PC` | C2(`c2fa..c364`; `c2fa`는 block 시작, `c2fc`는 내부 PC) | **[F] 실행 실패.** `('outside_range_entry_00c2fc', 'unsupported animation controller c2 PC', 'unsupported animation machine PC')` |
| `tools/verify_animation_machine_stage_catalog.py:1095-1096` | 이웃 `0x4755e`, `0x48156` → `unsupported animation machine PC` | C2(`4755e..47594`), F6a(`48156..48180`) | [F] 실행은 종료 0이다. 그러나 두 탐침은 이제 C2·F6a 코드를 실행하고, 다른 routing 밖 PC에서 같은 문구로 끝나서 통과한다(보고서 `negatives/rows[219..220]`). 탐침의 의미가 바뀐 채 통과한다(L-1 유형). |
| `tools/verify_animation_machine_motion_walk.py:90`, `:929` | guard `guard-oor-18fd2-type8000` 목표 `0x10fda` → `expected_pc_error`(routing 밖) | F6c(`f226..11792`) | [I] 오류 문구가 바뀐다. C++ 시험 `animation_machine_motion_walk_test.cpp`는 `far[e]` 표로 이미 바꿨다. 실행하지 않았다([U]). |

- B2 계약 `docs/analysis/animation-machine-deferred-b2-contract.md:211`은 "C++ routing을 더해도 이 native guard 선언은 바뀌지 않는다([I], 병합 때 확인)"라고 적었다. 실제 실행으로 이 추론은 **틀렸다**.
  - native guard 자체(observer의 `unsupported_code_target`, `4c3a2`)는 그대로다.
  - 그러나 C++가 이제 `4c3a2`(`MOVE.L A0,5c8e(A5)` …)를 실행한다. 그래서 guard 상태에서 다른 checked error로 끝나고, 검증기의 `causes`와 맞지 않는다.
- 실패 시나리오: 다음 회귀나 인수 감사에서 fade_card·card_menu_close를 다시 돌리면 실패한다(이미 확인). 원인이 기록되어 있지 않아 C++ 결함으로 오인할 수 있다. stage_catalog는 탐침 의미가 바뀐 채 통과하므로, 실제 경계 회귀가 생겨도 잡지 못할 수 있다.
- 권고: 각 검증기를 기존 관례(`SUPERSEDED_GUARD_CAUSES`, `SUPERSEDED_CAUSES`)대로 고친다. 새 오류 문구를 보존된 기록과 함께 남기고, 역사 pin은 바꾸지 않는다. 고치기 전에는 목록을 STATUS/0263에 추가한다.

### M-2 (중간) 자연 seed 원본 비교 검증기가 macOS 원 환경에서 바로 실패한다(Linux 경로 고정)
- [F] `tools/verify_animation_machine_frame_driver.py:43`은 `SEED_DIR = ROOT / 'artifacts/linux_rebase/stage_entry_body'`로 고정돼 있다. 기대 SHA는 `:44`의 `f74048bb…`다.
- 이 경로는 Linux 클라우드 세션에만 있다. 다음 도구가 모두 `D.setup_native()`로 이 값을 쓴다.
  - D1 `verify_animation_machine_frame_driver.py`
  - D9 `verify_animation_machine_frame_controller.py:765`
  - F6-D `verify_animation_machine_frame_irq.py:754`
  - V1의 자연 seed 도우미 `natural_cases`·`seed_frames`(`verify_animation_machine_unit_fixtures.py:653-658`). spec 13개가 모두 이를 거친다.
- [F] 이 Mac에서 V1 spec 13개(selftest 포함)를 그대로 실행했더니 모두 `FileNotFoundError: …/artifacts/linux_rebase/stage_entry_body/observation.json`로 끝났다(종료 1).
- [F] 이 Mac에는 역사 seed `artifacts/stage_entry_body/observation.json`이 있고 SHA는 `1f65100f…`로 역사 pin(`HISTORIC_SEED_SHA`, `observe_animation_machine_scheduler.py:60`)과 같다.
- 리뷰에서는 scratch wrapper `rv_seedwrap.py`를 썼다. 이 wrapper는 `D.SEED_DIR`만 역사 경로로 바꾸고 도구는 고치지 않는다. 결과는 "검증 명령과 결과"에 적었다.
  - 이 결과로 `0262`·`0263`이 [U]로 남긴 "역사 seed와의 동등성"을 일부 해소했다. 역사 seed에서도 V1 15,782 fixture와 아래 frame 비교가 통과했다.
- 권고: `--seed-dir`(또는 환경별 routing 파일) 옵션으로 seed 경로를 받게 한다. WORKFLOW "환경과 경로 재현"의 원칙(기계별 입력은 옵션, 실패를 성공으로 처리하지 않음)과 맞춘다. 보고서 `declared_platform_rebase.why` 문구도 실제 사용 경로에 맞게 남긴다.

### M-3 (중간) 새 시험이 바로 다음 단위의 ROM PC를 "routing 밖" 탐침으로 쓴다(작업 규칙 위반)
worker-rules "F4 unit test boundary convention"은 새 rollback/unrouted 탐침에 work RAM PC `10fe00..10fefe`만 쓰라고 정했다. 그런데 이번 묶음의 V1 spec과 C++ 시험 수정이 다음 단위 후보의 ROM PC를 `unsupported animation machine PC` 기대값으로 고정했다.
- [F] V1 spec(보고서 `expect=('error','unsupported animation machine PC')`):
  - b1a: `error-unrouted-cc8b4`, `78660` `78716` `78776` `78d5a` `79320` `79400` `7942e` `79454` …(16개)
  - b1b: `b1b-error-boundary-3d526` `3d982` `3dd42` `3def2` …(16개)
  - b2a: `error-unrouted-4b6f4` `44602`, `error-boundary-4b6f4` `44602`
  - b2b: `error-3a5be-unrouted-3a60a`, `error-unrouted-3b5a6` `4db18` `4b6f4`, `error-boundary-3b5a6` `4db18`
  - c1: `error-outside-30ec` `ca22` `ca3a` `4a8f8` `4a9e2`
  - c2: `error-outside-1022` `bbfa` `48250` `a770` `a8d0` `b362` `e630a`
  - c3b: `error-outside-4fb18`
- [F] C++ 시험 수정(이번 범위)도 같은 문제가 있다. `bbfa`(card_menu_close/save), `a770`(card_menu_open), `48250`(stage_catalog), `4d9b8`(frame_helpers)는 모두 ROM 코드 진입점이다. 탐침으로 바꾼 PC는 다음과 같다.
  - `animation_machine_card_menu_close_test.cpp`: `c2fa` → `bbfa`
  - `animation_machine_card_menu_save_test.cpp`: `bbd4` → `bbfa`
  - `animation_machine_card_menu_open_test.cpp`: `a75a` → `a770`, `3670` → `370c`
  - `animation_machine_stage_catalog_test.cpp`: `4755e` → `48250`
  - `animation_machine_frame_helpers_test.cpp`: `4d9d4` → `4d9b8`
  - (`370c`는 숫자 문자열 자료라 상대적으로 안전하다.)
- 실패 시나리오: STATUS가 적은 다음 단위 후보를 연결하면 위 fixture·시험이 바로 실패한다. 후보는 B2c `3a60a..3abde`, `44602` `4b6f4` `4db18` `3b5a6`, `3d526`, `cc8b4`, `78776` 그룹이다. 이번 병합에서 반복된 "탐침 옮기기"가 다시 생긴다.
- 권고: 이 탐침들을 `10fe00..10fefe`로 옮긴다. 경계 callee는 "stop 성공"만 확인한다.

### L-1 (낮음) 기대 오류 fixture가 실패 위치를 확인하지 않아 의미가 바뀐 채 통과한다
- [F] V1의 `('error', text)` 판정(`verify_animation_machine_unit_fixtures.py:496-503`)은 "C++ 실패 + 오류 문자열 포함 + 실패 호출의 상태 보존"만 본다. 실패 PC와 실패 직전 상태는 보지 않고, native도 실행하지 않는다.
- 예: `tools/unit_fixture_specs/d9.py:50`의 `error-c560-open-c3b-boundary`.
  - 원래 의미는 C3b 경계(`c56e`) 미연결이었다.
  - C2·C3b 병합 뒤에는 실행이 `c56e`부터 `c598` `JMP c00444`까지 가고, `c00444`에서 같은 문구 `unsupported animation machine PC`로 실패한다. 그래서 의미가 바뀐 채 계속 통과한다.
- `verify_animation_machine_frame_controller.py:606-611`의 c3b 경계 행(`ac75f6d`에서 수정)도 오류 문구와 native 정지 이유만 비교한다. system return에 닿기까지의 C++ 경로·상태는 비교하지 않는다.
  - 수정 자체는 근거(native `fr['c']['reason']=='system-return'`)가 있어 기대값 약화로 보지 않는다.
- V1 기대 오류 비율이 크다(b2a 817/1,386, b2b 849/1,419, b1a 1,091/2,807). 대부분 내부 PC 진입(실행부 고유 문구)이라 문제는 작다. 그러나 `unsupported animation machine PC`·`unaligned` 같은 공용 문구 행은 위치 확인이 없다.
- 권고: 오류 fixture에 실패 PC(또는 마지막 성공 stop)를 함께 기록하는 방식을 검토한다. 예: 실패 PC를 stop으로 둔 짝 fixture가 성공하는지 확인한다.

### L-2 (낮음) frame 검증기의 수용 판정이 `verifier-error` 행을 실패로 세지 않는다
- [F] `verify_animation_machine_frame_irq.py:561-563`, `verify_animation_machine_frame_controller.py:523`, `verify_animation_machine_frame_driver.py:590`은 비교 중 예외가 나면 `category='verifier-error', checks={}` 행을 만든다.
- 그러나 `aggregate`(`frame_irq.py:698`)의 `bad_fail = [x for x in nonc if not all(c.get('ok') for c in x['checks'].values())]`는 빈 `checks`를 참으로 본다. `full_chain_step`(`:495`)도 `c is None`이면 `alive=False`만 하고 `first_divergence`를 남기지 않는다.
- 결과: 검증기 예외가 난 frame이 있어도 `acceptance`의 `all_complete_match`·`non_completions_checked`·`chain_no_divergence`가 모두 참일 수 있다. 전체 실행에서는 `natural_complete_400`(native 기준)만 따로 비교한다.
- 이번 리뷰 실행에서는 `categories`에 `verifier-error`가 없었다(아래). 수치상 문제는 없지만 판정 구멍이다.
- 권고: `verifier-error` 개수가 0이 아니면 acceptance를 거짓으로 한다.

### L-3 (낮음, 수정됨) Makefile 헤더 목록에 `.cpp`가 중복으로 들어갔다
- **상태: 메인이 `b6bc035`(branch `claude/next-work-cycle`)에서 수정했다.** 중복된 `controller_c2.cpp` 두 개를 헤더 목록에서 뺐다. 이 리뷰가 독립적으로 찾은 항목과 같다. 수정 commit은 이 리뷰의 대상 범위(`e5bfb73`) 밖이라 재검증하지 않았다(commit 메시지 기록: `make -j4 all test` 종료 0).
- 출처 기록의 차이: `b6bc035` 메시지는 "B1a 병합이 중복시켰다"고 적었다. 각 commit의 Makefile에서 `controller_c2.cpp` 개수를 세면 `6ae5161`(B1a 병합) 0, `50dda0f`(C2) 1, `cd9be14`(C2 병합) 2다. 따라서 중복은 C2 병합에서 생겼다[F].
- [F] `Makefile:1325` `ANIMATION_MACHINE_HEADERS = … engine/include/ms5/animation_machine_irq.h engine/src/animation_machine_controller_c2.cpp engine/src/animation_machine_controller_c2.cpp`
- 출처: C2 작업자 branch(`50dda0f`)가 헤더 목록에 `.cpp` 7개를 넣었고, 병합(`cd9be14`)이 그중 `controller_c2.cpp`를 두 번 남겼다.
- 영향: 모든 animation_machine 시험의 의존성에 C2 소스가 붙는다(재빌드 증가). 링크 누락은 아니다.
- 링크 목록 점검 결과는 다음과 같다(b584065 같은 누락 없음).
  - [F] `engine/src/animation_machine*.cpp` 전부가 `ANIMATION_MACHINE_SOURCES`(114개, 중복 0)에 있다.
  - `tools/verify_animation_machine.py SOURCES`는 Makefile과 같다(누락 0).
  - V1·frame 검증기는 Makefile 줄을 직접 읽는다.

### L-4 (낮음) 예전 C++ 시험 fixture를 기대값 갱신 대신 삭제했다
- [F] `engine/tests/animation_machine_objects_u06_test.cpp`에서 `error-boundary-101c` fixture와 `eb81e-mode-1` probe를 삭제했다. 다른 PC로 옮기지 않았다(`101c`는 C2 `100e..1022`가 routing).
- `animation_machine_objects_u02_test.cpp`의 `8f4e`/`8f5a`는 시험용 합성 ROM에 BCD 문자열이 없다. 그래서 기대값을 `missing or ambiguous physical program bus ROM byte`로 바꿨다. 의미 변화는 주석에 남아 있다.
- U06 `eb81e` 모드 1 경로가 C2 진입까지 이어지는 행은 이제 어느 시험에도 없다([I] 커버리지 감소).

### 참고(결함 아님)
- **V1 carry 비교 범위.** V1은 C를 비교하지 않는다(선언된 한계). carry 오류는 소비 block의 native 분기 결과로만 드러난다.
- **V1 음성 검사 분포.** F6a·F6c spec에는 `mismatch` 음성 fixture가 없다. 비교기 자체의 음성 검사는 selftest 9개가 맡는다.
- **F6a clear run 381 진입.** native fixture는 `run` 38개와 자연 경로만 본다. 다만 [F] `160ae..1669e`가 `2c80 d082`(MOVE.L D0,(A6); ADD.L D2,D0) 380쌍 + `1669e RTS`로 균일하다. 그래서 일부 진입 비교와 C++ 시험 4,617회로 충분하다고 본다([I]).
- **C1 fixture 수.** 이번 실행은 1,741개로, `0263` 표의 1,748과 다르다. spec이 병합 상태·seed에서 fixture를 생성하므로 생길 수 있는 차이다. 어느 쪽이 원인인지는 [U]다(Linux 보고서 없음).

## 원본 근거 확인 (이상 없음)
- [F] **routing 겹침 0.** 새 실행부 11개가 차지하는 짝수 PC는 b1c 992, f6a 2,001, f6c 9,564, b2b 1,036, c3 254, b1b 1,050, f6b 3,125, c1 429, b2a 970, b1a 1,251, c2 717개다. 이 PC 중 다른 규칙과 겹치거나 앞 규칙에 가려지는 것은 없다.
- [F] **carry 보존 목록 510 PC.** 실행부 case 단위로 C를 쓰는 명령이 없다(위반 0). C 생산자 `r.carry=`도 ROM 명령과 맞았다.
  - `ORI/ANDI CCR`: C1 `30c8` `30ce` …, B1a `79240` `79250` …, B1b `b1cc2`, B2a/B2b
  - `CMPI.B #aa`: `ca32`
  - `CMP.W (A4),D7`: `4d4e0`의 무부호 borrow
  - `MOVE`/`TST`가 만드는 Clear: B2b `33948` `4d4e8` `4d502` …
  - RTE: SR bit 0
- [F] **wait block 6곳의 들어오는 C는 죽어 있다.** `ef2 MOVE.B/CMP.B`, `16bd0`·`cda4`·`3aea CMP.W`, `47af0`·`478de JSR 72f0`(`72f0 MOVE.B; SUBI.B #80`; RTS)이다. 그래서 IRQ 전달 뒤 RTE가 만드는 Clear(선언 SR `2000`)가 원본과 다른 C를 소비시키지 않는다.
- [F] **IRQ vector.** `64`=`20c`, `68`=`29c`, `6c`=`20c`다. 예외 frame(PC LONG, SR WORD, A7−6)과 RTE pop 순서는 68000과 같다. `224` MOVEM `-(A7)` 저장 순서, `248` MOVEM.W 복원의 부호 확장, `cf0` task 복원의 "복원된 A5" 사용도 맞다.
- [F] **F6b.** cell 255개(`732e + 14·(k−1)`)가 모두 `08a8 0007 d; 670c; 4ce8 00ff d; 48e9 00ff d`(d = `20·k`)다. `8752..8b52`는 `MOVEM.L D0-D7,-(A0)` 256개 + `SUBI.W #2000` + `BNE.W 8b60`이다. 실행부와 일치한다.
- [F] **palette bank 선택.** pin된 MAME `neogeo.cpp:1715`(`hc259 write_a3`, umask `00ff`)와 `:1936`(Q7 → `set_palette_bank`), `:1719`(`400000..401fff` mirror `3fe000`)으로 보면 `3a000f`는 bank 0, `3a001f`는 bank 1이다. `animation_machine_irq.h`의 E6 모델과 같다. BYTE 쓰기의 실제 하드웨어 동작은 [U]이며, 이번 코드는 MOVEM.L·MOVE.W만 쓴다.
- [F] **F6c.** `tools/check_animation_irq_f6c_template.py`가 종료 0으로 통과했다.
  - family A: 8 routine, 624 시작, Duff 128
  - family B: 8 routine, 616 시작, Duff 128
  - 계약 SHA와 C++ 표가 일치했다.
- [F] **B2 계약 `4c3ba` 미참조.** 8 MiB 전체에서 LONG `0004c3ba`가 0건이다. ±32 KiB PC 상대 16bit 변위와 8bit 분기도 0건이다.
- [F] **C2 계약.** WORD `000180`=`0000`, `c686 TST.W 180.l; BEQ`, menu 표 `a810`의 (`a7e2` "GAME START", `a856`) (`a7f4` "HOW TO PLAY", `a876`) (`a7ed` "OPTION", `a896`) (`a80a` "EXIT", `a8bc`)를 확인했다.
- [F] **정수 연산.** UB 위험 지점을 확인했다.
  - SBCD(`ac1_sbcd`, `f6a_sbcd_one`; `a62 SUB.W D6,D6`로 X=0 확인)
  - MULU.W(`49a44`, 16×16 무부호 32bit 안)
  - MULS.W(F6c, 부호 확장한 32bit 곱의 mod 2^32)
  - ASR.L Dn(B1c 반복문, count&63)
  - BSET Dn,Dn(&31)
  - 가변 shift: 모두 마스크되어 UB가 없다.
  - 부호 있는 비교는 `^0x8000` 방식이다.

## 검증 명령과 결과
모든 명령은 worktree `/Users/start/Workspce/metalslug-review`에서 실행했다. `W`=`/Users/start/Workspce/ms5-scratch/review0264/scripts/rv_seedwrap.py`(역사 seed wrapper)다.

1. `make -j3 all test` → **종료 0**(10분 1초).
   - C++ animation_machine 시험 바이너리 112개 PASS, 전체 `./build/*` 실행 261개
   - Python `Ran 310 tests … OK`
   - 컴파일 경고 0(Linux에서 보고된 `-Wmisleading-indentation` 10개는 이 환경에서 없음)
   - 로그: `review0264/make_all_test.log`
2. V1 원본 비교: `python W verify_animation_machine_unit_fixtures --spec tools/unit_fixture_specs/<u>.py --out review0264/v1/<u> --workers 3`. 13개 모두 `ok: true`이고 `inputs_unchanged_after: true`다. 합계 15,782/15,782.

   | spec | fixture | 통과 | match | 기대 오류 | 음성 |
   | --- | ---: | ---: | ---: | ---: | ---: |
   | selftest | 40 | 40 | 27 | 4 | 9 |
   | c3b | 480 | 480 | 249 | 223 | 8 |
   | d9 | 26 | 26 | 19 | 4 | 3 |
   | c1 | 1,741 | 1,741 | 1,347 | 387 | 7 |
   | c2 | 1,607 | 1,607 | 974 | 625 | 8 |
   | f6a | 320 | 320 | 294 | 26 | 0 |
   | f6b | 726 | 726 | 690 | 33 | 3 |
   | f6c | 1,538 | 1,538 | 1,370 | 168 | 0 |
   | b1a | 2,807 | 2,807 | 1,702 | 1,091 | 14 |
   | b1b | 1,892 | 1,892 | 979 | 901 | 12 |
   | b1c | 1,840 | 1,840 | 1,029 | 802 | 9 |
   | b2a | 1,386 | 1,386 | 559 | 817 | 10 |
   | b2b | 1,419 | 1,419 | 560 | 849 | 10 |

   - wrapper 없이 같은 명령을 실행하면 13개 모두 종료 1(M-2)이다.
3. `.venv/bin/python -I tools/check_animation_irq_f6c_template.py --json review0264/f6c_template.json` → 종료 0.
4. pin된 예전 검증기(OUT만 scratch로 바꾼 사본 `review0264/scripts/rv_verify_<name>.py`, ROOT는 이 worktree):
   - fade_card: **종료 1**. `('guard-alloc-return-clobbered', 'program bus requires even WORD/LONG address')`(M-1). 원본 관측 감사와 일반 비교는 guard 단계 전까지 통과했다.
   - card_menu_close / stage_catalog: 아래 "예전 검증기 실행"
5. frame 원본 비교(역사 seed): 아래 "frame 비교 실행"
6. 정적 스크립트(scratch `review0264/scripts/`): `route_overlap.py`, `carry_check2.py`, `stale_probes*.py`, `rv_dis.py`. 결과는 같은 폴더의 `*.txt`에 있다.

### 예전 검증기 실행
OUT만 scratch로 바꾼 사본으로 실행했다. 원본 도구는 고치지 않았고, 공유 `artifacts/`의 native 관측은 읽기만 했다.

| 검증기 | 결과 |
| --- | --- |
| fade_card | 종료 1(73초): `AssertionError: ('guard-alloc-return-clobbered', 'program bus requires even WORD/LONG address')` |
| card_menu_close | 종료 1(3,684초): `AssertionError: ('outside_range_entry_00c2fc', 'unsupported animation controller c2 PC', 'unsupported animation machine PC')` |
| stage_catalog | 종료 0(2,758초), `OK`, 534 case, 보고서 SHA256 `6b82bdf1…e02e`. 다만 이웃 탐침 `4755e` `48156`은 의미가 바뀐 채 통과한다(M-1). |

- card_menu_close의 prefix·비교 단계는 실패 지점 전까지 통과했다.
- 같은 목록의 `c2fa`는 assert를 통과했다. C2가 `c2fa`부터 실행한 뒤 다른 routing 밖 PC에서 같은 문구로 끝났기 때문으로 보인다([I], L-1과 같은 유형).
- scratch 출력(약 4.9 GB)은 결과를 기록한 뒤 지웠다.

### frame 비교 실행
모두 `python W <도구> … --out review0264/frames/<이름>`로 실행했다. seed는 역사 `stage_entry_body`(`1f65100f…`)다.

| 이름 | 명령 인자 | 결과 |
| --- | --- | --- |
| d1_full | `verify_animation_machine_frame_driver --workers 3` | 종료 0, 836초. 정상 frame 54,400/54,400 일치, 불일치 0. 원본 정지 6개(`fetch-unmapped` 5, `odd-pc` 1)는 기대 checked error로 짝지어졌다. C++ 단독 연쇄는 136 seed 400 frame 완주, 1 seed 원본 정지, 어긋남 0. `historic_all_equal: true`, 결정성·부정 검사 통과. 보고서 SHA256 `8eb065f5…16f8` |
| fc_game | `verify_animation_machine_frame_controller --cases 0,32,116 --frames 400 --declare game --workers 3` | 종료 0. 1,200/1,200 일치, 연쇄 1,200 frame 일치. controller 경로 `c7fc>c7fc` 724, `c7fc>c79a` 3, `c79a>c79a` 470. fixtures·부정·결정성 통과. `3852de47…3d04` |
| fc_iii | `… --cases 0,32,116 --frames 120 --workers 3`(선언 없음, 구성 (iii)) | 종료 0. 360/360 일치, 경로 `c52a>c560` 3, `c560>c560` 354. `62853389…beff` |
| firq | `verify_animation_machine_frame_irq --cases 0,32,116 --frames 400 --workers 3` | 종료 0. 1,200/1,200 일치, IRQ 2,394회 전달, 연쇄 어긋남 0, acceptance 전 항목 참. `categories`에 `verifier-error` 없음. `093499961…6f08` |

- [F] D1 전체 실행이 역사 seed로 Linux 결과(`0262`: 54,400/54,400, 136 완주, 1 정지)와 같은 집계를 냈다. 따라서 `0262`/`0263`의 "역사 seed 동등성 [U]"는 **집계 수준에서** 해소된다. Linux rebase seed와의 바이트 동등성은 여기서 비교하지 않았다(Linux 파일 없음).
- D9 (ii)·F6-D는 3 seed 표본만 돌렸다. 137 seed × 400 frame 전체는 이 환경에서 다시 실행하지 않았다([U], `0263` 기록에 의존).

## 미확인 사항
- 실제 하드웨어 값은 이 리뷰에서도 [U]다: vblank 시점, BIOS `c0044a`·`c00444`·`c00450`의 효과, Z80 응답, video status, palette RAM BYTE 쓰기.
- motion_walk guard `10fda`의 새 오류 문구는 실행으로 확인하지 않았다(M-1 표).
- `0263`의 Linux 실행 수치와 이번 macOS 역사 seed 실행 수치의 차이(C1 1,741 대 1,748)의 원인은 [U]다.
- N22b 153 대 154의 차이 1 block은 [U]로 남는다(계약 기록 그대로).
- M1 커버리지 기준선(48.4%)은 다시 측정하지 않았다. 도구가 출력 위치를 `artifacts/` 안으로 강제하기 때문이다(`tools/measure_code_coverage.py:799`). 현재 routing은 기준선 시점(`c7318132…`)보다 넓어 수치가 달라진다. 수치는 R층 자기참조를 포함한다는 문서의 단서와 함께 읽어야 한다.
