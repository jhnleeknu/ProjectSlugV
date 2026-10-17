# N28 범위 밖 사슬의 `28ae` 자식 셋과 callee `1c114` 구현 계약 B3c

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. 범위는 B3b 계약 "B3c 후보" 절(`28ae` 자식 `2d7be` `2d916` `2db06`, callee `1c114`와 `2291a` 꼬리, 약 71 block)이다. 아래 수치와 목록은 작업자가 정적 디코드로 다시 계산했다. 결정 항목(끝)은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다. bank 창 읽기 `200094..2000a0`은 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다(아래 "자료 표"). ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `d1fdda8`(branch `claude/b-followups` = PR #3 + legacy trace + demo 문서 + U06b). routing 기준 `engine/src/animation_machine.cpp`. dispatch 사슬을 Python 조건식으로 옮겨 "routing된 PC"를 판정했다(scratch `hroute.py`, B3b 도구와 같은 방식, 경로만 이 작업 트리).
- [F] 정적 디코드: capstone M68000. block 시작 규칙은 B1 계약 "기준 입력"과 같다(분기 대상·fall-through, JSR/BSR 복귀 PC, `MOVE.L #imm,(A6)` 설치 값). 진입은 `2d7be` `2d916` `2db06`(`28ae` 자식 값)과 `1c114`(callee), routing된 PC에서 멈춘다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/b3c/`
  - `sdec.py` `hroute.py` `closure.py` `b3adis.py` `refs.py`(B3b scratch 복사, 경로만 바꿈), `unit_b3c.py`(단위 정의·분류), `probe_scan.py`(기존 시험의 범위 안 상수 검색).
  - `starts.txt`(시작 71개) SHA256 `dcd0a4222271d0789a31fd12d08d8ce00c58170ba7572e9a77bb2ae1de4580ae`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 요약

- [F] **범위·block 수**(B3b 계약 "B3c 후보" 표 재현: 20 + 14 + 16 + 21 = 71):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `1c114..1c1ba` | 166 | `bfe412c7229494024feaa4ea468e4675becc75d9c6d15886a6e0ee6a847747f7` | 15 | 83 |
| `2291a..2296a` | 80 | `9dc051370cad7256e55deaae31ecb6aaf4abc9dc05e6e2933655af4f5aa9b9b9` | 6 | 40 |
| `2d7be..2d8b8` | 250 | `f3fc1a38fcfd7cab03177ab2497ab852ab2c054078f5a9959b624396a5e7a733` | 20 | 125 |
| `2d916..2d9dc` | 198 | `5322051262f0efd8cca0d558c6660aa5c07cd08c393088d3b78b62552a60903d` | 14 | 99 |
| `2db06..2dbda` | 212 | `1151ca9a3ce1f84ea2a5490f4d21ca6ece233010f0703c73639b670d4b7836ba` | 16 | 106 |
| 합계 B3c | 906 | 이어 붙인 바이트 `b6e9cf25520f98ad88c51b860e8f9a9372231061e983f5412aaa2b7297de6cf3` | **71** | 453(내부 382) |

- [F] 명령 220개, 정적 closure가 다섯 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 연속 Bcc 묶음 없음, 간접 분기 없음(계산 jump 표 없음), 새 `28ae` 자식 값 없음, TRAP·I/O port·bank 변경·X 소비(ADDX/SUBX/ROX) 없음.
- [F] **현재 routing과의 관계**: 다섯 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃: `1c112`(routing 밖, 다른 함수 `RTS`)·`1c1ba`(routing 밖, 아래 결정 1), `22918`(routing 밖, `22916 MOVE.B #ff,D0`의 중간)·`2296a`(routing 밖 다른 함수), `2d7bc`(B2d `RTS`)·`2d8b8`(routing 밖 자료), `2d914`·`2d9dc`(routing 밖 자료), `2db04`(routing 밖 다른 객체 코드)·`2dbda`(routing 밖 자료, 애니메이션 목록).
- [F] **나가는 곳은 모두 routing돼 있다**: callee `289e` `288c` `2986` `4c2fa` `8ebe` `43e34` `43e08` `49f8c` `49fc6` `1d198` `1bf80` `49290` `491c4`, 출구 `JMP 2a00`(삭제), `JMP 491b6`(꼬리 호출). routing 밖 값은 자료뿐이다(아래 "자료 표"). 그래서 B3a + B3b + B3c 뒤 사슬 `2ba50`은 `2986`이 만드는 자식(표 `227fc..2284c`의 값, 이후 pass)을 빼고 C++로 실행된다.
- [F] **참조**: `1c114`는 B3a `2b636 JSR`과 routing 밖 `33f08 JSR`이 부른다. `2291a`는 `1c1b6 BRA.W`(이 단위)와 routing 밖 `22738 BSR.W`가 쓴다(공유 꼬리). `2d7be`는 B3a `2b54e`, `2d916`은 B3a `2ba56`과 routing 밖 `2cf02`, `2db06`은 B3b `2bdc2`가 `MOVEA.L #값,A0` 뒤 `JSR 28ae`로 자식 callback으로 넘긴다.
- [I] 의미: `2d7be`(`2d810` 설치) / `2d87a`(`2d8a0` 설치)는 부모 BYTE `15` bit 7에 따라 갈리는 부속 효과 객체(부모 위치를 따라가며 BYTE `13`으로 감쇠), `2d916`(`2d98e` 설치)은 부모 BYTE `7c`(방향 index 0..16 [I])에 맞춰 위치를 잡는 총구·조준 표시류, `2db06`(`2dbac` 설치)은 부모 BYTE `7c`/`7d`·LONG `36` 부호로 방향을 정해 화면 좌표(`10d38e` 기준)로 놓는 발사체/효과, `1c114`는 플레이어 구조체(`100cb8`/`100da8`, D0.W로 선택)의 BYTE `9e`·`8c` 기록 BYTE `6`으로 고른 자식을 `2986`으로 만들고 위치를 설정하는 생성 helper다. 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

B1 계약 "공통 규칙"과 "공통 native 검증 계획", B2 계약 "자식(`28ae`) 진입 fixture", B2c~B3b 계약의 공유 파일·macOS seed 관례를 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_b3c.cpp`, 함수 `animation_objects_b3c_block`. 오류 문자열은 `unsupported animation objects b3c PC`(범위 안 내부 PC 직접 진입)와 `objects b3c caller requires known carry`(C 소비 block에 Unknown C; 소비자가 있으므로 둔다)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(다섯 범위), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 6개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, test 목록 실행 줄, 시험 target; Codex의 object 재사용 구조 유지, SOURCES·HEADERS 줄은 각각 하나), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 이 단위에서 routing 밖으로 나가는 실행 PC는 없다. B3a 시험·spec이 stop으로 확인하던 `1c114`, B3a/B3b 시험의 `28ae` 진입 stop(A0 = `2d7be` `2d916` `2db06`)은 그대로 통과해야 한다(stop 판정은 routing보다 먼저; 회귀로 확인). rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다(F4 관례).
- **오류 fixture의 실패 PC**(리뷰 0264 L-1). 기대 오류 fixture마다 실패 PC를 적는다. 실패 PC가 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지(성공) 함께 확인한다. 같으면 그 사실을 fixture 이름·주석에 적는다.
- **자료 읽기**(live bus, F1 결정 3): 모든 표 읽기는 원본 주소 계산 그대로 live bus로 읽는다. 상한 검사는 원본에 없으므로 두지 않는다(index가 표 밖이면 원본처럼 그 주소의 바이트를 읽는다; 물리 ROM에 없는 바이트면 bus의 checked 오류). 대상: LONG `20009c`/`200094`(bank 창), WORD `2d904 + 2·(D0 & ff)`, LONG `(LONG 22(A6)) + sext(4·WORD)`, WORD `2d8fc + sext(2·WORD 8a)`, WORD 쌍 `2d8b8 + 4·BYTE 7c`, WORD 쌍 `2d9dc + 8·BYTE 7c`, LONG `2284c + 4·BYTE 9e`, LONG `(표) + 4·k`(k < 4). 단위 시험은 이 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `1c14c MOVEM.W D0/D2-D3,-(A7)`는 D3.W, D2.W, D0.W 순으로 WORD 3개를 넣고(낮은 주소에 D0.W) `1c18a MOVEM.W (A7)+,D0/D2-D3`는 D0, D2, D3 순으로 꺼내 각 WORD를 32 bit로 부호 확장한다(flag 불변). 그 사이 `JSR 2986`(복귀 LONG `1c18a`)이 같은 스택을 쓴다.
- **정수 연산.** `ADDQ.B #1` + `BCS`(BYTE 올림, 같은 block), `MULS.W`(부호 16 × 16 → 32), `ASR.L #8`·`ASR.W #3`(부호 bit 채움, `ASR.W`는 하위 WORD만), `SUBI.W #ff`(WORD), `SUB.B D0,13(A6)`, `EXT.W`(BYTE → WORD, 상위 WORD 유지), `NEG.W`·`NEG.B`, `ADDI.B #80`, `ADDQ.B #4`, `ADDI.W #100`, `LSL.W #3`, `ADD.W D0,D0` 두 번(WORD), `ADDA.W`·`(An,Dn.W)` index(부호 확장), `CMPA.W #0,An`(32 bit 비교), `TST.L` + `BPL`(bit 31), `CMPI.B #4` + `BCS`(무부호, 같은 block), `ADD.L`/`SUB.L`(32 bit wrap), `LEA d16(A5)`(부호 확장 변위: `-7348` → A5 − `7348`, `538e` → A5 + `538e`)를 68000 폭 그대로 명시 구현한다. X·DIV·TRAP·I/O port·bank 변경은 없다.
- **macOS seed.** 자연 seed가 필요한 V1·D1 실행은 B3a/B3b와 같은 scratch wrapper가 `D.SEED_DIR`만 역사 관측 `artifacts/stage_entry_body`(SHA256 `1f65100f…`)로 바꾼다(도구 파일은 고치지 않음).

## carry

- [F] **소비 block 6개**(callee가 돌려준 C를 읽음; 각 block은 Bcc 하나):
  - `1c128 BCS.W 1c12e`: `289e`(readiness; `CMPI.L #270e,(A0)` 같으면 Clear, 다르면 `28a8 ORI` Set). Clear → `1c12c`(RTS), Set → `1c12e`.
  - `2d85e BCC.W 2d868` / `2d8ac BCC.W 2d8b6` / `2d9c6 BCC.W 2d9da` / `2dbce BCC.W 2dbd8`: `49fc6`(interpreter known C). Clear → 분기 대상, Set → `JMP 2a00` block(`2d862` `2d8b0` `2d9ca` `2dbd2`).
  - `2dbb2 BCS.W 2dbbc`: `288c`(LONG `c(A6)` = 0이면 `2898 ORI` Set, 아니면 `289e`). Clear → `2dbb6`(`JMP 2a00`), Set → `2dbbc`.
- [F] 6개만 `carry_preserving_pc`에 넣는다(B2c~B3b 꼴). Unknown C로 들어오면 checked 오류다. 이 단위에는 다른 block이 소비하는 known C 생산자가 없다(ORI/ANDI CCR 없음). `1c14c`의 `CMPI.B #4` + `BCS`, `2d816`의 `ADDQ.B #1` + `BCS`, `2db32`의 `TST.L` + `BPL`, `22920`/`22944`의 `CMPA.W` + `BEQ`는 같은 block 안에서 만들고 소비한다. 그 밖의 모든 block은 진입 때 Unknown이 된다.
- [F] `1c114`를 부른 쪽(B3a `2b63c RTS`, routing 밖 `33f0e JSR 491b6`)은 `1c114`가 돌려준 C를 읽지 않는다. 그래서 `1c12c`/`1c146 RTS`(원본은 각각 C Clear를 돌려줌)는 Unknown을 돌려도 소비자가 없다(소비자 없는 carry 보존은 만들지 않는다).
- [F] block 경계를 건너 다시 계산하는 flag는 없다(모든 Bcc는 같은 block 안의 비교나 callee C를 읽는다).

## callee `1c114..1c1ba`(15)와 공유 꼬리 `2291a..2296a`(6)

- **`1c114`**: A0 := A5 − `7348`(`100cb8`, A5 = `108000`일 때), WORD D0 = 0 → `1c122`. `1c11e`: A0 := A5 − `7258`(`100da8`). `1c122`: `JSR 289e`.
- **`1c128`**(소비자): C Clear → `1c12c RTS`, Set → `1c12e`.
- **`1c12e`**: A4 := LONG `8c(A0)`, BYTE `10f001` bit 2 ≠ 0 → `1c14c`. `1c13e`: BYTE `7(A4)` ≠ 0 → `1c148`, 아니면 `1c146 RTS`. `1c148`: BYTE `7(A4)` −= 1(BYTE wrap), `1c14c`로 이어짐.
- **`1c14c`**: `MOVEM.W D0/D2-D3,-(A7)`, D0 := BYTE `9e(A0)`(MOVEQ 뒤, 상위 0), D0.W := 4·D0.W(WORD), A1 := LONG `(2284c + sext(D0.W))`, D0 := BYTE `6(A4)`, 그 값 < 4(무부호) → `1c172`, 아니면 `1c170`(D0 := 0).
- **`1c172`**: D0.W := 4·D0.W, A0 := LONG `(A1 + sext(D0.W))`, D0.W := `a`, A1 := `100bf4`, `JSR 2986`(복귀 `1c18a`).
- **`1c18a`**: BYTE `60(A0)` := BYTE `60(A6)`, `MOVEM.W (A7)+,D0/D2-D3`, WORD `76(A0)` := D0.W, D0.B := `20`, BYTE `15(A6)` bit 0 = 0 → `1c1ae`. `1c1a6`: D0.B := −D0.B + `80`(BYTE, 즉 `60`), D2.W := −D2.W. `1c1ae`: BYTE `78(A0)` := D0.B, D0.B := `ff`, `BRA.W 2291a`.
- **`2291a`**: `JSR 4c2fa`(복귀 `22920`). `22920`: A2 := LONG `3e(A6)`, D0 := LONG `36(A6)`, D1 := LONG `3a(A6)`, A2 = 0 → `22944`. `22934`: D0 += LONG `14(A2)` − LONG `1c(A2)`, D1 += LONG `18(A2)` − LONG `20(A2)`(읽는 순서 `14` `1c` `18` `20`). `22944`: A1 = 0 → `2295c`. `2294c`: D0 −= LONG `14(A1)`, D0 += LONG `1c(A1)`, D1 −= LONG `18(A1)`, D1 += LONG `20(A1)`. `2295c`: LONG `36(A0)` := D0, LONG `3a(A0)` := D1, `JMP 491b6`.
- [F] `2986` 실패(아래 결정 4): `28ae`가 실패하면(`28ba` WORD 한도, `28c2` A0 입력 0) A0 = A5 − `7168`(`100e98`, 더미 node)이고 `1c18a` 이하가 그 더미에 쓴다. C++에서는 buffer_cue `298e`가 caller X를 요구해 checked 오류다(`cue wrapper failure requires known caller X`). 표 `227fc..2284c`의 slot 0은 넷 모두 LONG 0이므로 BYTE `6(A4)` = 0 또는 ≥ 4이면 항상 이 실패 경로다.
- [F] `1c1ba MOVEM.W (A7)+,D0/D2-D3; RTS`(`1c1ba..1c1c0`)는 `1c1b6 BRA.W` 뒤에 있고 정적 참조가 없다(도달하지 않는 코드, 결정 1).

## `28ae` 자식 `2d7be..2d8b8`(20)

- **`2d7be`**: WORD `20` := `f2`, LONG `22` := LONG `20009c`(bank 창, live bus), D0.W := `208`, D1.B := 0, `JSR 8ebe`.
- **`2d7da`**: A0 := LONG `c(A6)`(부모), BYTE `7c` := BYTE `7c(A0)`, BYTE `7e` := BYTE `7e(A0)`, BYTE `15(A0)` bit 7 = 0 → `2d87a`.
- **`2d7f4`**: A1 := `2dbda`(`LEA` 뒤 `MOVEA.L`, 같은 값), D0.W := `100`, `JSR 49f8c`. `2d80a`: 설치 `2d810`.
- **`2d810`**(설치 값): `JSR 43e34`. `2d816`: D0 := BYTE `13`(MOVEQ 뒤), D0.B += 1, 올림(원래 BYTE = `ff`) → `2d830`. `2d822`: D0 := sext(D0.W) × sext(WORD `3a`)(MULS.W), `ASR.L #8`, D0.W −= WORD `3a`, WORD `46` −= D0.W.
- **`2d830`**: D0.B := BYTE `8e`, D1.B := BYTE `8f`, `EXT.W` 둘, BYTE `15` bit 0 = 0 → `2d848`, 아니면 `2d846 NEG.W D0`. `2d848`: D0.W −= WORD `36`, D1.W −= WORD `3a`, WORD `42` −= D0.W, WORD `46` −= D1.W, `JSR 49fc6`.
- **`2d85e`**(소비자): Clear → `2d868`, Set → `2d862 JMP 2a00`. `2d868`: D0 := BYTE `13`, D0.W −= `ff`(WORD), `ASR.W #3`, BYTE `13` −= D0.B, `RTS`.
- **`2d87a`**: D0.W := WORD `36`, D1.W := WORD `3a`, WORD `2e` += D0.W, WORD `32` += D1.W, A1 := `2df6a`, D0.W := `100`, `JSR 49f8c`. `2d89a`: 설치 `2d8a0`.
- **`2d8a0`**(설치 값): `JSR 43e34`. `2d8a6`: `JSR 49fc6`. `2d8ac`(소비자): Clear → `2d8b6 RTS`, Set → `2d8b0 JMP 2a00`.

## `28ae` 자식 `2d916..2d9dc`(14)

- **`2d916`**: A0 := LONG `c(A6)`, D0.W := WORD `8a(A0)`, `JSR 1d198`(1d198이 LONG `22`·WORD `20`을 씀).
- **`2d924`**: A0 := LONG `c(A6)`, D0.W := WORD `88`, `JSR 1bf80`(D0.B := 플레이어 BYTE `9f`).
- **`2d932`**: D0.W &= `ff`, D0.W *= 2, A0 := `2d904`, D0.W := WORD `(2d904 + sext(D0.W))`, D7.W := D0.W, D0.W := `100`, A0 := A6 + `26`, A1 := LONG `22`, D7.W := 4·D7.W(WORD), A1 := LONG `(A1 + sext(D7.W))`, `JSR 49f8c`.
- **`2d95c`**: A4 := LONG `c(A6)`, D0.W := WORD `8a(A4)`, A0 := `2d8fc`, D0.W := WORD `(2d8fc + sext(2·D0.W))`, D1.B := 0, `JSR 8ebe`.
- **`2d978`**: D0 := 0, D1 := 0, `JSR 49290`. `2d982`: `JSR 491c4`. `2d988`: 설치 `2d98e`.
- **`2d98e`**(설치 값): A0 := LONG `c(A6)`, D0 := BYTE `7c(A0)`, D0.W := 4·D0.W, A4 := `2d8b8` + sext(D0.W), D0.W := WORD `(A4)+`, D1.W := WORD `(A4)+`, BYTE `15` bit 0 = 0 → `2d9b2`, 아니면 `2d9b0 NEG.W D0`.
- **`2d9b2`**: WORD `2e` := D0.W, WORD `32` := D1.W, `JSR 43e34`. `2d9c0`: `JSR 49fc6`. `2d9c6`(소비자): Clear → `2d9da RTS`, Set → `2d9ca`: A0 := LONG `c(A6)`, BYTE `62(A0)` := `ff`, `JMP 2a00`.

## `28ae` 자식 `2db06..2dbda`(16)

- **`2db06`**: WORD `20` := `e2`, LONG `22` := LONG `200094`(bank 창), A1 := `2ed9c`, D0.W := `100`, `JSR 49f8c`. `2db24`: D0.W := `204`, D1.B := 0, `JSR 8ebe`.
- **`2db32`**: A0 := LONG `c(A6)`, D0 := BYTE `9c(A0)`, D0.W += `100`, WORD `2c` := D0.W, BYTE `7d` := BYTE `7d(A0)`, BYTE `7c` := BYTE `7c(A0)`, LONG `36(A0)` bit 31 = 0 → `2db6a`. `2db58`: `BSET #0,15(A6)`, BYTE `7d` := 4 − BYTE `7d`(`NEG.B` + `ADDQ.B #4`, BYTE wrap; D0.B에도).
- **`2db6a`**: D0 := BYTE `7c`(MOVEQ 뒤), D0.W := D0.W << 3, A1 := `2d9dc` + sext(D0.W), D0.W := WORD `(A1)+`, D1.W := WORD `(A1)+`, BYTE `15` bit 0 = 0 → `2db88`, 아니면 `2db86 NEG.W D0`.
- **`2db88`**: D0.W += WORD `42(A0)`, D1.W += WORD `46(A0)`, A1 := A5 + `538e`, D0.W −= WORD `14(A1)`, D1.W −= WORD `18(A1)`, A0 := A6 + `2e`, `JSR 43e08`. (A0는 `2db32`가 실은 부모; 직접 진입이면 들어온 A0.) `2dba6`: 설치 `2dbac`.
- **`2dbac`**(설치 값): `JSR 288c`(A0 := LONG `c(A6)`). `2dbb2`(소비자): Clear → `2dbb6 JMP 2a00`, Set → `2dbbc`: WORD `1e` := WORD `1e(A0)`, `JSR 43e34`. `2dbc8`: `JSR 49fc6`. `2dbce`(소비자): Clear → `2dbd8 RTS`, Set → `2dbd2 JMP 2a00`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다. index 범위는 원본에 상한 검사가 없어 [I]로 적는다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다.

| 표 | 범위 | 바이트·SHA256 | 읽는 곳 | 내용 |
| --- | --- | --- | --- | --- |
| 방향 위치(WORD 쌍) | `2d8b8..2d8fc` | 68(아래 셋과 함께 `2d8b8..2d916` 94바이트 `0047cd0f8c78a5d85ca243de2dcdf23124632d8bb4352e6e690d41512807a508`) | `2d98e`(index BYTE `7c(부모)`, [I] 0..16) | 0:(`0015`,`0015`) 1:(`0013`,`0017`) 2:(`0011`,`0019`) 3:(`000e`,`001a`) 4:(`000b`,`001c`) 5:(`0009`,`001d`) 6:(`0006`,`001d`) 7:(`0003`,`001e`) 8:(`0000`,`001e`) 9:(`fffd`,`001e`) 10:(`fffa`,`001d`) 11:(`fff7`,`001d`) 12:(`fff5`,`001c`) 13:(`fff2`,`001a`) 14:(`ffef`,`0019`) 15:(`ffed`,`0017`) 16:(`ffeb`,`0015`) |
| 소리(WORD) | `2d8fc..2d904` | 8 | `2d95c`(index WORD `8a(부모)`, [I] 0..3) | `0376` `0377` `0004` `0005` |
| 애니메이션 index(WORD) | `2d904..2d916` | 18 | `2d932`(index 플레이어 BYTE `9f`, [I] 0..8) | `0145` `0146` `0147` `0148` `0149` `014a` `014b` `0145` `0145` |
| 방향 위치(WORD 4개) | `2d9dc..2da64` | 136, `cfdbeebd1e6cdd915d44d36c5361636a208383512e7d567384404be709aa6c3b` | `2db6a`(index BYTE `7c`, [I] 0..16; 앞 WORD 2개만 읽음) | 0:(`fff4`,`000b`,`000b`,`fff4`) 1:(`fff3`,`000a`,`000c`,`fff5`) 2:(`fff2`,`0008`,`000d`,`fff7`) 3:(`fff1`,`0007`,`000e`,`fff8`) 4:(`fff1`,`0006`,`000e`,`fff9`) 5:(`fff0`,`0004`,`000f`,`fffb`) 6:(`fff0`,`0003`,`000f`,`fffc`) 7:(`fff0`,`0001`,`000f`,`fffe`) 8:(`fff0`,`0000`,`0010`,`0000`) 9:(`fff0`,`fffe`,`000f`,`0001`) 10:(`fff0`,`fffc`,`000f`,`0003`) 11:(`fff0`,`fffb`,`000f`,`0004`) 12:(`fff1`,`fff9`,`000e`,`0006`) 13:(`fff1`,`fff8`,`000e`,`0007`) 14:(`fff2`,`fff7`,`000d`,`0008`) 15:(`fff3`,`fff5`,`000c`,`000a`) 16:(`fff4`,`fff4`,`000b`,`000b`) |
| 자식 표(LONG ×4, 넷) | `227fc..2284c` | 80(아래와 함께 `227fc..2285c` 96바이트 `917d2b1aede37caac99a2166ced301939e05f25e9b687eee94d4b5e70fa7a843`) | `1c172`(index BYTE `6(A4)`, < 4 아니면 0) | `227fc`: 0 `22b04` `23058` `22dbc`; `2280c`: 0 `22ad4` `2308e` `22d94`; `2281c`: 0 `235ca` `235ca` `235ca`; `2282c`: 0 `23a3e` `23a3e` `23a3e` |
| 자식 표 선택(LONG) | `2284c..2285c` | 16 | `1c14c`(index 플레이어 BYTE `9e`, [I] 0..3) | `227fc` `2280c` `2281c` `2282c` |
| bank LONG | CPU `200094..2000a0`(bank 창) | 12; bank_base = 물리 `200000`일 때 `7db246a3dbbe1303b71b57c8a9313b8302342b6d2c770ec58dc8acb79c2076a7` | `2db06`(`200094`), `2d7be`(`20009c`) | 물리 `200000` bank: `200094` = `002996ec`, `20009c` = `0029c910`(다른 bank면 그 bank의 값) |

- [F] 자식 표 값(`22b04` `23058` `22dbc` `22ad4` `2308e` `22d94` `235ca` `23a3e`)은 모두 routing 밖이다. `2986`이 만드는 자식의 callback이며 실행은 이후 pass다(이 단위 범위 밖, 결정 5). `2283c..2284c`(0, `23830` ×3)는 이 단위가 읽지 않는 다음 표다.
- [F] 애니메이션 목록 값 `2dbda` `2df6a` `2ed9c`(A1, `49f8c`)와 LONG `22` 표 내용은 interpreter 자료다.
- [I] index가 [I] 범위 밖이면 원본은 다음 코드·표 바이트를 자료로 읽는다. C++도 같은 주소를 live bus로 읽는다(단위 시험에서는 합성 바이트 밖이라 bus checked 오류).

## 경계·routing 밖 출구

- [F] routing 밖 실행 PC: 없음. routing 밖 값은 위 자료뿐이다.
- [F] routing된 출구·callee: `289e` `288c` `2986` `4c2fa` `8ebe` `43e34` `43e08` `49f8c` `49fc6` `1d198` `1bf80` `49290` `491c4`, `JMP 2a00`, `JMP 491b6`. 반환은 `RTS` 여섯 곳(`1c12c` `1c146` `2d8b6` `2d9da` `2dbd8`, 그리고 `2d868` block 끝의 RTS).
- [F] 공유 꼬리 `2291a`: routing 밖 `22900..2291a`(다른 함수 끝, `22916 MOVE.B #ff,D0`)가 fall-through로 들어오고 `22738 BSR.W`가 부른다. 이후 그 함수를 넣는 단위는 `2291a`(이 단위의 block 시작)로 끝나야 한다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, B3a/B3b spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 N28 node(A6)에 선언 편집(레지스터, node field, LONG `c(A6)` := 다른 자연 node(부모), 부모 field, 플레이어 구조체 `100cb8`/`100da8`의 BYTE `9e`·LONG `(A0)`, LONG `8c` 기록 BYTE `6`·`7`, BYTE `10f001`, PC).
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다(`289e` → `1c128`(`1c122` 진입), `288c` → `2dbb2`(`2dbac`), `49fc6` → `2d85e` `2d8ac` `2d9c6` `2dbce`(V1·실제 ROM 차분; 단위 시험은 선언 C)).
- node fixture: 설치 값(`2d810` `2d8a0` `2d98e` `2dbac`)과 자식 진입(`2d7be` `2d916` `2db06`)을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다. `1c114`는 callee로 들어간다(복귀 LONG = sentinel).
- 단위 시험(Unicorn 생성기, B3b/U06b 꼴): 시작 71개 × 들어오는 C 3가지, zero-step, 내부 PC 382개 정확한 오류, 경계 stop, rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC.

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `probe_scan.py`: 다섯 범위 안 값, `engine/tests` `tools/unit_fixture_specs` `tools/*.py`): B3a 시험의 `1c114` stop·fixture(`2b636` → `1c114`, `2b608` 경로), B3a/B3b 시험 출력의 A0 = `2d7be` `2d916` `2db06`(28ae stop), B2d 시험·spec의 범위 끝 `2d7be`(배타)뿐이다. stop은 routing 판정보다 먼저라 그대로 통과한다. "routing 밖" rollback 기대로 이 범위 PC를 쓰는 곳은 없다.
- [I] 계산 PC로 이 범위에 착지하는 숨은 탐침은 구현 뒤 `make test`로 찾는다. 찾으면 결정 6대로 옮기고 이 절에 더한다.
- [I] 자연 400 frame은 `2ba3e` 설치가 자연 경로에 없어 B3a/B3b 사슬의 자식을 만들지 않는다. 다만 `1c114`(`33f08` 호출자)·`2d916`(`2cf02`)·`2291a`(`22738`)는 다른 routing 밖 코드에서도 쓰이므로 자연 경로 도달 여부는 frame 회귀(D1·controller·IRQ)로 확인한다(다음 작업자).

## 결정

1. **범위.** 71 block을 한 단위로 구현한다(B3b 계약 "B3c 후보" 그대로). 도달하지 않는 `1c1ba..1c1c0`(정적 참조 없음)은 넣지 않고 routing 밖으로 둔다(작업자 권고).
2. **자료.** 표·bank 읽기는 live bus, 상한 검사 없음(F1 결정 3). 표 바이트 범위(`2d8b8..2d916` `2d9dc..2da64` `227fc..2285c`)는 routing하지 않는다.
3. **carry 보존 목록.** 소비자 6개만 넣는다.
4. **`2986` 실패 경로.** buffer_cue 결정 1(caller-X 한계는 의도된 checked 오류)을 그대로 둔다. BYTE `6(A4)` = 0 또는 ≥ 4(자식 표 slot 0 = LONG 0)이거나 node 한도에 걸리면 C++는 `298e`에서 `cue wrapper failure requires known caller X`로 멈춘다. [I] 원본은 그 뒤 더미 node `100e98`에 쓰고 `4c2fa`로 간다. 자연 빈도가 높으면 메인이 caller X 일반화(`1c14c` 이전 X 생산자 추적)를 별도 단위로 정한다.
5. **`2986` 자식 값.** 표 `227fc..2284c`의 자식 callback 8개(`22ad4`부터)는 이 단위에 넣지 않는다(이후 pass, 새 단위 후보).
6. **숨은 탐침 이전.** 기존 시험이 계산 PC로 이 범위에 착지하면 B3a 결정 5와 같이 RAM `10fexx` 탐침으로 옮기고, 옮길 수 없으면 기대 문자열만 이 단위 오류로 바꾸고 실패 PC를 stop으로 확인한다.

## 미확인

- [U] BYTE `13` `7c` `7d` `7e` `8e` `8f`, WORD `2c` `2e` `32` `42` `46`, 플레이어 BYTE `9e` `9f`, LONG `8c` 기록 BYTE `6` `7`, BYTE `10f001` bit 2의 의미.
- [U] 세 자식과 `1c114`가 만드는 자식의 화면상 이름, 표 index의 실제 범위.
- [U] `4c2fa`가 X를 읽는지(결정 4의 실패 경로 뒤 X 전파 영향).
- [U] 자연 400 frame 밖에서 `33f08`/`2cf02`/`22738` 경로의 도달.

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_b3c.cpp`(case label 71 = scratch `starts.txt`와 집합 일치), `engine/tests/animation_machine_objects_b3c_test.cpp`(생성 구역 + 수작성 규칙: MOVEM.W 저장·복원과 `2986` 호출, 자료 PC 10개의 dispatcher 오류), `tools/generate_animation_machine_objects_b3c_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음), `tools/unit_fixture_specs/b3c.py`(V1 spec, 아직 실행 전). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다. 다른 단위의 시험·spec은 고치지 않았다(무효 탐침 없음).
- [F] 단위 시험 world의 A7은 `10ef00`이다. `1c12e`가 읽는 BYTE `10f001`이 `10f000` 복귀 LONG과 겹치기 때문이다(B3b 시험·차분 harness는 이 겹침 때문에 BYTE `10f001`이 늘 `0f`).
- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 줄 0, 시험 실행 268개, Python 310개 통과. B3a·B3b 줄은 변경 전과 같다. B3c 시험 줄: `258 fixtures (165 single-block, 52 path, 9 producer chain, 12 declared C, 20 checked error (4 with a later failing PC), 21 kept C), 71 blocks, 1383 calls, 41191 checks`. 내부 PC 382개 정확한 오류.
- [F] 검증 작업자(Sonnet 5.5 / medium)가 위 항목을 실행했다. 코드·시험·생성기·spec은 바꾸지 않았다(결함 없음). 모든 출력은 scratch `/Users/start/Workspce/ms5-scratch/b3c/`.
  - `make -j3 all test`: 종료 0, 경고 0, Assert 0, Python 310개 OK, B3c 줄 258 fixtures / 71 blocks / 1383 calls / 41191 checks, Makefile의 `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 줄 각 1개.
  - UBSan(`build_ubsan.sh`): 종료 0, `runtime error` 0, 같은 B3c 줄.
  - 변이: `killed 38 of 38`(생존 0).
  - 실제 ROM 차분(Unicorn 대 C++, bank 200000/300000, 5 x 1,500 = 7,500건): 불일치 0 전부, 시작 71/71 모두 덮임. 문서화된 차이 "2986 실패 경로는 caller X 필요"(알려진 checked 오류 부류) 건수: s1 156, s2 136, s3 146, f4 188, f5 202. 소비자 6개(`1c128 2d85e 2d8ac 2d9c6 2dbb2 2dbce`)는 실제 생산자 뒤 native 분기와 비교됨. harness 수정 없음(`build.sh`는 실행 비트가 없어 `bash build.sh`로 실행).
  - V1(`MS5_SEED_DIR=artifacts/stage_entry_body`): b3c 625/625 ok(visited 71/71, missing successors 없음, unreachable outcomes 없음, `carry oracle ok` Unknown/Clear/Set = 205/8/6), 두 번 실행의 `[(name,digest)]` 625건 동일. 회귀 b3a 1,468/1,468, b3b 1,360/1,360(기준과 같은 수).
  - frame(`--workers 2`): D1 driver, controller `--declare game`, IRQ 각각 종료 0, complete 54,400/54,400, natural 불일치 0(natural_frames 54,401 중 비완료 1은 기준과 같은 native stop), deterministic / negative_ok true. controller `--declare demo` 전체: 종료 0, complete 45,684/45,684, complete-mismatch 0, 137 seed.
  - [F] 파일 SHA256 앞 16자리: `animation_machine_objects_b3c.cpp` a62d33b05245c42a, 시험 d21882565e86f32a, 생성기 7da903b863703da4, spec 176483af3065d9a2.
  - [U] 미확인은 위 "미확인" 절 그대로다(의미·자연 400 frame 밖 `33f08`/`2cf02`/`22738` 도달).

## block 목록

[F] scratch `starts.txt`(SHA256 `dcd0a4222271d0789a31fd12d08d8ce00c58170ba7572e9a77bb2ae1de4580ae`)와 같다.

- **`1c114..1c1ba`(15)**: `1c114 1c11e 1c122 1c128 1c12c 1c12e 1c13e 1c146 1c148 1c14c 1c170 1c172 1c18a 1c1a6 1c1ae`
- **`2291a..2296a`(6)**: `2291a 22920 22934 22944 2294c 2295c`
- **`2d7be..2d8b8`(20)**: `2d7be 2d7da 2d7f4 2d80a 2d810 2d816 2d822 2d830 2d846 2d848 2d85e 2d862 2d868 2d87a 2d89a 2d8a0 2d8a6 2d8ac 2d8b0 2d8b6`
- **`2d916..2d9dc`(14)**: `2d916 2d924 2d932 2d95c 2d978 2d982 2d988 2d98e 2d9b0 2d9b2 2d9c0 2d9c6 2d9ca 2d9da`
- **`2db06..2dbda`(16)**: `2db06 2db24 2db32 2db58 2db6a 2db86 2db88 2dba6 2dbac 2dbb2 2dbb6 2dbbc 2dbc8 2dbce 2dbd2 2dbd8`
