# 리뷰 0264 후속 수정 (M-3, L-1, L-4)

`0264-ten-unit-batch-independent-review.md`의 발견 사항 중 M-3(다음 단위 ROM PC를 "routing 밖" 탐침으로 사용), L-1(기대 오류가 실패 위치를 확인하지 않음), L-4(삭제된 U06 fixture)를 고친 기록이다.

- 대상: worktree `/Users/start/Workspce/metalslug-m3fix`, branch `claude/m3fix-wip`, 기준 `2c7e5a4`(B3a 병합 직후).
- 작업자: Claude Sonnet 5.5 / high. 커밋하지 않았다. `engine/src` 실행부는 바꾸지 않았다.
- 표기: [F] 사실(실행·코드로 확인), [I] 추론, [U] 미확인.
- ROM은 읽기 전용으로만 썼다(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`). V1 보고서의 `inputs_unchanged_after`가 모두 참이다.
- 환경 [F]: macOS(Darwin 25.4.0), Apple clang++, Python 3.14 venv, Unicorn 2.1.4. V1은 선언된 seed rebase 래퍼(`D.SEED_DIR := artifacts/stage_entry_body`, 역사 seed)로 돌렸다. 래퍼와 로그는 scratch(`/Users/start/Workspce/ms5-scratch/m3fix/`)에만 있고 저장소에는 없다.

## M-3 다음 단위 ROM PC 탐침을 work RAM으로 이동

규칙(worker-rules, F4 단위 시험 경계 관례): "routing 밖" 탐침은 `10fe00..10fefe`의 짝수 work RAM PC만 쓴다(RAM에서는 코드가 실행되지 않으므로 routing이 절대 소유하지 않는다). 2c7e5a4에서 spec 13개와 C++ 시험 전체를 다시 훑었다.

### 처리 원칙
1. **탐침 이동.** 시작 PC가 ROM 이웃/범위 끝이던 `unsupported animation machine PC` 행은 값과 이름만 RAM PC로 바꿨다. 행 수는 그대로다.
2. **범위 끝 정확성 유지.** ROM 이웃이 없어지면 "단위 범위가 정확히 거기서 끝난다"는 확인이 사라진다. 그래서 spec은 `build()`에서 `unit_of(hi) != 자기 단위`와 `unit_of(lo-2) != 자기 단위`를, C++ 시험은 `assert(!in_ranges(ROM 이웃))`를 둔다. 다른 단위가 그 PC를 나중에 소유해도 깨지지 않는다.
3. **실제 경계는 stop-only.** 단위 코드가 고정 ROM 주소(JMP/BRA/JSR/fall-through)로 단위를 벗어나는 경우는 RAM으로 옮길 수 없다. 오류 기대 대신 "그 PC를 stop으로 둔 run이 성공하고 정확히 거기서 끝난다"를 확인한다(spec은 native와 C++ 비교의 `match`, C++ 시험은 `run(...)`과 `s.pc==stop`). 나중에 그 PC를 다른 단위가 소유해도 stop-only는 깨지지 않는다.
4. **계산된 도착(RAM 불가).** 이번에 남긴 항목은 없다. B3a가 한 `335f6 -> 2b5fe` 행은 이미 stop 짝 fixture(`table-335f6-landing-2b5fe`)가 있어 그대로 두었다.

### V1 spec 변경 (탐침 매핑)

| spec | 이전 ROM PC | 이후 | 비고 |
| --- | --- | --- | --- |
| b1a | `78660 78716 78776 78d5a 79320 79654 79746 b7d4a cc8b4 79400 7942e 79454 7949c 794e2`(14) | `10fe00..10fe1a`(이 순서, 14) | `error-unrouted-*` 14행 |
| b1a | `error-boundary-78d3a-cc8b4`, `error-boundary-78564-78776` | `boundary-stop-78d3a-cc8b4`(stop `cc8b4`), `boundary-stop-78564-78776`(stop `78776`) | 오류 -> stop-only match |
| b1b | `3d526 3d982 3dd42 3def2 3df1a 3e0aa 3e302 b1c90 b1c92 b1c9c 3d234 3da6c`(12) | `10fe00..10fe16`(이 순서, 12) | `b1b-error-boundary-*`. 기본 node(`bases[0]`/`[1]`)는 이전 PC와 같게 유지 |
| b1b | `b1b-error-trap-b1c82-{zero,seven,x100,ffff}` | `b1b-boundary-stop-trap-b1c82-*`(stop `b1c90`) | TRAP #f 경계를 stop-only로 |
| b1c | `error-outside-30d6c` | `error-outside-10fe80` | N30 이웃 4개는 다른 단위의 interior 오류라 그대로 |
| b2a | `4b6f4 5eed0 5f4b0 5f502 60514 6093a` | `10fe00 10fe02 10fe04 10fe06 10fe0c 10fe0e` | `10fe08`·`10fe0a`는 기존 RAM 탐침 |
| b2a | `error-boundary-4b6f4`(`5ef66`에서 JSR `4b6f4`) | `boundary-stop-4b6f4`(stop `4b6f4`) | stop-only |
| b2b | `4c3ba 4c3c2 3a4d6 3a4d8 4b6f4 3a048 3a0d2` | `10fe0a 10fe0c 10fe0e 10fe10 10fe12 10fe14 10fe16` | `10fe04`·`10fe08`은 기존. `+ (0x4c3c2,)` 중복 검사 제거 |
| b2c | `3ab80 3ab98 3abde 3af6c 3af74 3b03c 3b4bc 3b4e0 1bf94 1d1b0 4b6f4 3ad48`(12) | `10fe10 10fe12 10fe14 10fe16 10fe18 10fe1a 10fe1c 10fe1e 10fe20 10fe22 10fe24 10fe26` | |
| b2d | `error-394e2-3a5be-3a60a`(A0 = `3a60a`), 무작위 `82(A6)` 값 `3a60a` | `error-394e2-3a5be-10fe00`(A0 = `10fe00`), `10fe00` | **spec이 2c7e5a4에서 build 자체가 실패했다**: `3a60a is routed: update the 3a5be error fixture`(B2c 병합 뒤 `require(unit_of(0x3a60a) is None)`가 깨짐). [F] 이번에 고쳐 1,489/1,489 통과 |
| b2e | `3abec 3b68a 44600 4464a 4db16 4dc66 e66a8 e6836 e6838 e6896 e693a e89d8 e89e4 3b4e0 4b6f4`(15) | `10fe10 10fe12 ... 10fe2c`(짝수 연속, 15) | |
| b2e | `error-e682e-trap`(TRAP `e6836`) | `boundary-stop-e682e-e6836`(stop `e6836`) | stop-only |
| c1 | `error-outside-30ec 370c ca22 ca3a 4a8f8 4a9e2` | `10fe10 10fe12 10fe14 10fe16 10fe18 10fe1a` | 종전 `if not routed(pc)`로 조용히 빠지던 방식을 `require`로 바꿔 조용한 누락을 없앴다. BIOS `c00450`·`c00444`는 유지 |
| c2 | `error-outside-1022 bbfa c6ce 48250 e630a b362 a770 a8d0` | `10fe10 10fe12 ... 10fe1e`(8) | BIOS `c00444`·`c00468` 유지 |
| c3b | `error-outside-c6ce c6d8 4fb4a 4fb18` | `10fe10 10fe12 10fe14 10fe16` | BIOS `c00444` 유지 |

b3a, f6a, f6b, f6c, selftest spec은 바꿀 PC가 없었다(`f6b`의 `10fe00`은 이미 RAM).

### C++ 시험 변경 (탐침 매핑)

| 시험 | 이전 | 이후 |
| --- | --- | --- |
| `card_menu_close_test` | `bbfa` | `10fe22` |
| `card_menu_save_test` | `bbfa` | `10fe20` |
| `card_menu_open_test` | `a770`, `370c` | `10fe18`, `10fe16` |
| `stage_catalog_test` | `48250` | `10fe24` |
| `frame_helpers_test` | `4d9b8` | `10fe2c` |
| `controller_c1_test` | `c6ce 1022 bbfa` | `10fe10 10fe12 10fe14` |
| `controller_c2_test` | `1022 bbfa c6ce 48250 e630a b362 a770 a8d0` | `10fe10 ... 10fe1e`(8) |
| `controller_c3_test` | `c6ce 4fb4a` | `10fe10 10fe12` |
| `objects_b1a_test` | 이웃 9개(`78660 ... cc8b4`) | RAM 9개 `10fe00..10fe10`. `78564`, `78d3a`는 stop `78776`·`cc8b4` stop-only |
| `objects_b1b_test` | 이웃 12개 | RAM 12개 `10fe00..10fe16`. `b1c82` 4행은 stop `b1c90` stop-only |
| `objects_b1c_test` | `30d6c` | `10fe80`(+ `assert(!in_ranges(0x30d6c))`) |
| `objects_b2a_test` | `4b6f4 5eed0 5f4b0 5f502 60514 6093a` | RAM 7개. `5ef66 -> 4b6f4`는 stop-only. `5f5da` rollback은 stop `4b6f4`에서 install store가 확정되는지로 바꿈(종전은 `4b6f4`가 routing 밖이라는 가정에 의존) |
| `objects_b2b_test` | ROM 16개 + RAM 3개 | RAM 19개 `10fe00..10fe24`, ROM 16개는 `!in_ranges` 확인만 |
| `objects_b2c_test` | ROM 8개 | RAM 11개(기존 `10fe02 10fe04 10fe06` 포함), ROM은 `!in_ranges` 확인만 |
| `objects_b2e_test` | ROM 14개, `e682e` TRAP | RAM 14개 `10fe10..10fe2a`. `e682e`는 stop `e6836` stop-only |

- 건드리지 않은 것: `motion_walk_test`의 `far[]` 표(F6c ROM 주소는 계산된 도착이 아니라 routing된 실제 PC의 오류 문구이며 `10fda` 등은 cell 실행 오류), `frame_test`의 BIOS 재개 PC(`c37c` `4a992` 등은 BIOS 재개 의미의 선언 값), `card_menu_*`의 BIOS 항목.
- [U] **남은 항목.** 이번 묶음 이전에 작성된 F4 시험(`n01..n35`, `u01..u20b`, `input`, `stage_area`, `stage_event*` 등) 55개 파일의 `outside[]`/`neighbours[]`에는 ROM PC 약 427개가 남아 있다. worker-rules가 "U36/U37 전에 옮긴다"고 적은 것과 같은 범위이며 이번 리뷰 대상(`cc88bde..e5bfb73`)이 아니라 건드리지 않았다. 후속 단위가 그 PC를 소유하면 해당 시험을 같은 방식으로 옮겨야 한다.

## L-1 기대 오류 fixture의 실패 PC 확인

### V1 변경 (`tools/verify_animation_machine_unit_fixtures.py`, 국소 변경)
- `Fixture`에 선택 인자 `fail_pc`를 더했다(`digest()`는 `fail_pc`가 있을 때만 반영해 기존 fixture digest는 바뀌지 않는다).
- `check_fail_pc()`와 `pc_routed()`를 더했다(`run_one()`의 기대 오류 분기에서 호출). C++ 오류는 atomic이고 PC를 싣지 않으므로 실패 PC `P`를 세 가지 사실로 고정한다.
  1. `P`를 stop으로 둔 같은 C++ run(상태·큐·release 동일)이 성공하고 정확히 `P`에서 끝난다. 즉 실패한 run은 같은 경로로 `P`에 닿는다.
  2. 공용 문구 `unsupported animation machine PC`: `P`는 현재 `animation_machine.cpp` dispatch 사슬(텍스트를 파싱)에 실행부가 없고 짝수다. 따라서 dispatcher가 `P`에서 실패한 것이지 그 뒤가 아니다.
  3. 공용 문구 `unaligned animation machine PC`: `P`는 홀수다. 짝수 시작에서 홀수 도착(`JSR (A0)` 등 계산된 도착)은 `fail_pc`를 선언해야 하고, 홀수 stop은 허용되지 않아 도달 확인은 못 한다(보고서 `fail_pc`에 `reach: odd landing ...`로 남긴다).
- 기본값: 공용 문구 두 가지는 `fail_pc`가 없으면 C++ 입력의 시작 PC를 실패 PC로 본다. 시작 PC가 routing된 단위 PC이면 실패한다(= 의미가 바뀐 채 통과하지 못한다). 실행부 고유 문구(`unsupported animation objects b2a PC` 등)는 `fail_pc`를 선언한 행만 확인한다.
- 한계 [F]: 공용 문구가 아닌 기대 오류(고유 문구)는 실패 PC를 일반적으로 확인하지 않는다. 대부분은 단위 interior PC에서 시작하는 행이라 시작 PC 자체가 실패 위치다.
- **다른 작업자의 seed 옵션 편집과의 병합**: `verify_animation_machine_unit_fixtures.py`의 변경은 (a) `import re`, (b) `Fixture.__init__`/`digest`/docstring의 `fail_pc`, (c) `run_one()` 앞의 새 함수 `pc_routed`·`check_fail_pc`와 기대 오류 분기의 `else:` 블록, (d) `make_report()`의 `limits` 문구 한 줄이다. seed 경로(`D.SEED_DIR`/`natural_cases`/`seed_frames`) 근처는 건드리지 않았다.

### spec 쪽 갱신
- `d9.py:50` `error-c560-open-c3b-boundary` -> **`error-c560-open-bios-c00444`**, `fail_pc=0xc00444`.
  - 증거 [F]: 2c7e5a4에서 이 run은 C3b 경계 `c56e`에서 끝나지 않는다. C2·C3b 병합 뒤 `c56e..c598`이 routing되어 `JMP c00444`까지 실행하고 BIOS 진입 `c00444`에서 `unsupported animation machine PC`로 끝난다. 이름과 docstring을 실제 목적(BIOS 진입 stop 직전까지의 경로)에 맞췄다.
  - 반증 [F]: 수정 전 기대(시작 `c560`을 실패 PC로 가정)는 새 검사에서 `fail-pc-routed-or-odd`로 거부된다. `fail_pc=c56e`(routed)도 거부되고, 도달하지 않는 `c00450`은 `fail-pc-not-reached`로 거부되며, `c00444`만 통과한다(scratch `neg_failpc.py`, 4가지 변형).
- 시작 PC가 routing된 단위 PC인 공용 문구 행에 `fail_pc`를 선언했다.

| spec | 행 | `fail_pc` | 근거 |
| --- | --- | --- | --- |
| c1 | `error-live-jsr-unrouted` | `10fe00` | A1 = RAM 도착 |
| c1 | `error-live-jsr-odd` | `3651` | A1 = 홀수 도착 |
| c3b | `error-bios-return-c598`, `-c5a6` | `c00444` | `JMP c00444.l` |
| b2b | `error-3a5be-unrouted-10fe00` | `10fe00` | A0 |
| b2b | `error-3a5be-odd-target` | `3a5d3` | A0 홀수 |
| b2c | `error-3ab7e-ram-target` / `error-3abc0-ram-target` / `error-3a5be-ram-substate` | `10fe00` / `10fe40` / `10fe80` | JMP/JSR (A0) 도착 |
| b2c | `error-3ab7e-odd-target` | `3a62b` | A0 홀수 |
| b2c | `error-3abc0-odd-target` | `3a655` | 도착 = 팝한 `3a63d` + 4 x ROM BYTE `3abe1`(=06) [I] 계산값, 홀수라 stop 확인은 못 함 |
| b2d | `error-394e2-3a5be-10fe00` | `10fe00` | A0 |
| b2e | `error-4dc40-ram-target` / `error-4dc40-odd-target` | `10fe00` / `4dc29` | JSR (A1) 도착 |

- 나머지(시작 PC가 곧 실패 PC인 `error-unrouted-*`, `error-outside-*`, `error-odd-*` 등 수백 행)는 기본값으로 모두 확인된다. 보고서의 `fail_pc` 필드가 있는 행 수는 아래 표와 같다.

## L-4 U06 시험의 삭제된 fixture 복원

대상: `engine/tests/animation_machine_objects_u06_test.cpp`. `error-boundary-101c`(행 삭제)와 `eb81e-mode-1`의 `boundaries()` 탐침(삭제)이다.

- 원인 [F]: `101c`는 C2 block(`MOVE.B D0,-7fe9(A5); RTS`)이다. 종전에는 `jsr $101c.l`이 routing 밖이라 stop이 없으면 `unsupported animation machine PC`였고, 이제는 실행해서 `eb9a0..eb9b2`를 지나 `jsr $16ea4`(스프라이트 block)에 닿는다.
- 현재 동작 [F](scratch `u06_probe`, C++): `eb980`과 `eb81e-mode-1`을 stop `ff000`으로 돌리면 `unsupported sprite callback target`로 실패하고 상태는 보존된다. 같은 입력에 stop `16ea4`를 주면 성공한다.
- 원본 대조 [F](scratch `u06_native.py`, Unicorn, 원본 ROM + 시험과 같은 입력 RAM·PVC bank `200000`/`00a0`/`1000`, 시험과 같은 FNV-1a digest):

| 행 | 원본 digest | C++ digest | 레지스터·bank·port |
| --- | --- | --- | --- |
| `eb980` stop `16ea4` | `b26131d763ffab0a` | `b26131d763ffab0a` | D0=0 ... D7=0, A7=`10effc`, bank `200000`, port 0 |
| `eb81e-mode-1` stop `16ea4` | `62e98dab82712e0c` | `62e98dab82712e0c` | D7=`14345`, 나머지 동일, port 0 |

- 시험에 더한 행(FIXTURES, 3개):
  - `eb980-to-16ea4`, `eb81e-mode-1-to-16ea4`: 위 원본 digest를 기대값으로 둔 성공 행. 실패 PC `16ea4`의 증거다.
  - `error-through-101c-sprite-16ea4`: 복원한 `error-boundary-101c`. 입력은 원래와 같고(`eb980`, stop `ff000`, puts 없음) 기대 오류는 `unsupported sprite callback target`(정확한 문구, 상태 보존). 이름은 목적이 바뀌어 바꿨다(101c는 더 이상 경계가 아니다).
  - `boundaries()`에 `eb81e-mode-1`/`eb980`을 stop 없이 돌려 같은 오류를 확인하고, 각 `-to-16ea4` 행의 최종 PC가 `16ea4`인지 assert한다.
- 네이티브는 stop 없이 계속 실행하므로 `16ea4`의 스프라이트 루틴을 그대로 수행한다. C++ 오류는 그 block이 이 입력에서 미모델 callback을 거부하는 선언된 checked error다(원본 동작이 아니다).
- 결과: U06 시험 151개 fixture(오류 13개), 종료 0.

## 검증 명령과 결과

모든 명령은 `/Users/start/Workspce/metalslug-m3fix`에서 실행했다. 공통: `.venv/bin/python -I /Users/start/Workspce/ms5-scratch/m3fix/runwrap_m3.py <ROOT> verify_animation_machine_unit_fixtures --spec tools/unit_fixture_specs/<s>.py --out <scratch>/v1/<s> --workers 3`.

### V1 (spec 17개, 모두 `ok: true`, `inputs_unchanged_after: true`)

| spec | fixture | 통과 | match | 기대 오류 | 음성 | `fail_pc` 행 | 이전 대비 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| selftest | 40 | 40 | 27 | 4 | 9 | 1 | 동일(0264: 40/27/4/9) |
| d9 | 26 | 26 | 19 | 4 | 3 | 2 | 동일 |
| c1 | 1,741 | 1,741 | 1,347 | 387 | 7 | 34 | 동일 |
| c2 | 1,607 | 1,607 | 974 | 625 | 8 | 42 | 동일 |
| c3b | 480 | 480 | 249 | 223 | 8 | 15 | 동일 |
| b1a | 2,807 | 2,807 | 1,704 | 1,089 | 14 | 32 | match +2, 오류 -2 (stop-only 2행) |
| b1b | 1,892 | 1,892 | 983 | 897 | 12 | 46 | match +4, 오류 -4 (TRAP stop-only 4행) |
| b1c | 1,842 | 1,842 | 1,031 | 802 | 9 | 10 | 오류 802 동일(0264의 1,840은 B3a가 더한 match 2행 전) |
| b2a | 1,386 | 1,386 | 560 | 816 | 10 | 9 | match +1, 오류 -1 (stop-only 1행) |
| b2b | 1,419 | 1,419 | 560 | 849 | 10 | 14 | 동일 |
| b2c | 1,707 | 1,707 | 835 | 862 | 10 | 27 | 오류 862 동일 |
| b2d | 1,489 | 1,489 | 553 | 926 | 10 | 2 | 2c7e5a4에서 build 실패 -> 통과 |
| b2e | 1,054 | 1,054 | 489 | 555 | 10 | 20 | match +1, 오류 -1 (stop-only 1행) |
| b3a | 1,468 | 1,468 | 550 | 908 | 10 | 1 | 동일 |
| f6a | 320 | 320 | 294 | 26 | 0 | 0 | 동일 |
| f6b | 726 | 726 | 690 | 33 | 3 | 2 | 동일 |
| f6c | 1,538 | 1,538 | 1,370 | 168 | 0 | 2 | 동일 |

- 래퍼 없이 실행하면 0264 M-2대로 `artifacts/linux_rebase/stage_entry_body`가 없어 실패한다. 이번 변경은 그 경로를 건드리지 않는다(다른 작업자의 seed 옵션 담당).

### C++ 시험
- 변경 시험 16개 개별 빌드·실행: 전부 종료 0, 경고 0 (`controller_c1/c2/c3`, `objects_b1a/b1b/b1c/b2a/b2b/b2c/b2e`, `objects_u06`, `card_menu_close/open/save`, `frame_helpers`, `stage_catalog`).
- `make -j3 all test` 결과는 이 문서 말미 "최종 전체 시험"에 적는다.

## 미해결·제약
- 위 [U] 항목(F4 이전 시험의 ROM 탐침 약 427개, 55개 파일).
- V1 한계 [F]: 실행부 고유 문구의 기대 오류는 실패 PC를 일반적으로 확인하지 않는다. 짝수 시작에서 홀수 도착 행은 선언값을 믿는다(홀수 stop 불가).
- b1b에는 `unit_of` 같은 routing 도우미가 없어 범위 끝 정확성 assert를 spec에 넣지 못했다. 같은 확인은 C++ `objects_b1b_test`의 `assert(!in_ranges(...))`가 맡는다.
- `10fe00..10fefe` 안의 PC가 spec/시험 안에서 서로 겹치지 않음은 파일별로 확인했다(예: b1b의 stop `10fe40`, b2c의 `10fe40`/`10fe80` 도착 값과 겹치지 않는다).

## 최종 전체 시험
- `make -j3 all test` -> **종료 0**(로그 `/Users/start/Workspce/ms5-scratch/m3fix/make_all_test.log`, 저장소 밖). 컴파일 경고 0, `Assert`/assertion 줄 0, Python `Ran 310 tests ... OK`.
- ROM `extracted/program/maincpu.decrypted.be.bin`: SHA256 `29112a94...c860f`, mtime `1791291625`가 시작과 끝에 같다.


## M-3 잔여: F4 이전 C++ 시험의 ROM 탐침 이전

대상: `outside[]`에 ROM PC를 둔 55개 C++ 시험(`n01`~`n35`(`n02` 없음, `n32b` 포함), `u01`~`u20b`의 해당 파일, `input`, `area_clear`, `buffer_cue`, `card_child`, `card_menu`, `card_menu_close/input/open/save`, `fade_card`, `frame_helpers`, `scene_core`, `scene_update`, `script_placement`, `stage_area`, `stage_catalog`, `stage_entry`, `stage_event`, `stage_event_ops`). 이미 이전한 `b1a`~`b2e`의 `ends[]`는 대상이 아니다.

- 이전한 탐침: **427개**(짝수 ROM PC, 55개 파일). `2baf4..2c0fc`, `2c96a..2ca68` 안의 PC는 이 배열에 없어 건너뛴 것이 없다.
- 규칙 [F]: 각 `outside[]`의 짝수 ROM PC를 파일 안에서 겹치지 않는 짝수 작업 RAM PC `10fe00..10fefe`로 바꿨다(그 파일에 이미 쓰인 `0x10fe..` 값은 피함, 낮은 주소부터 순서대로). 기대 결과(`unsupported animation machine PC` 롤백)와 다른 기대 상태는 바꾸지 않았다. BIOS 값(`c004xx`, `BIOS`, `TRAP_*` 상수), 이미 RAM인 값, 홀수 PC(`unaligned` 검사)는 그대로 둔다.
- 범위 끝 정보 보존: `in_ranges()`가 있는 38개 파일은 이전한 ROM PC를 `{const std::uint32_t rom_outside[]={...};...assert(!in_ranges(rom_outside[i]));}`로 확인한다(모두 통과). `in_ranges()`가 없는 17개 파일 중 `area_clear`, `stage_entry`는 `RANGES[][2]`로 같은 확인을 넣었다. `input`, `stage_area`, `stage_catalog`는 `RANGES`가 블록 구간 목록일 뿐 routing이 아니라서(일부 이전 PC가 구간 안의 비블록 PC) 같은 확인을 넣으면 실패한다 [F: 시도 후 철회]. 나머지 12개(card 계열, `buffer_cue`, `fade_card`, `frame_helpers`, `scene_core/update`, `script_placement`)는 범위 표가 없어 정적 확인이 없다 [U].
- 의도적으로 유지: 실제 경계 stop 시험, 계산된 도착(`input` 시험의 `targets[]` 등 `JSR (A1)` 도착값), BIOS 항목, 홀수 PC.
- 전체 매핑표(파일별 `old->new`)는 저장소 밖 `/Users/start/Workspce/ms5-scratch/m3b/mapping.md`, 기계 판독용은 같은 폴더의 `map.json`.

### 검증
- 변경 시험 55개를 개별 빌드·실행: 전부 종료 0, 경고 0, `Assert` 줄 0.
- `make -j3 all test` -> 종료 0(로그 `/Users/start/Workspce/ms5-scratch/m3b/make_all_test.log`), 경고 0, `Assert` 줄 0.
- 도구(`tools/*.py`)와 `engine/src`는 변경하지 않았다.
