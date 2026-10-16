# N28 범위 밖 설치 사슬 `2ba50`(앞 머리·뒤 상태·공통 꼬리·helper) 구현 계약 B3a

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안, 메인 확인 전.** 이 문서를 먼저 쓰고 그대로 구현한다. 아래 수치와 목록은 작업자가 정적 디코드로 독립 계산했다. 결정 항목(끝)은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 문서의 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다. 고정 ROM 자료 읽기(`2d8b8` `2b6c4` 표, LONG `9e(A6)` 기록 등)는 live bus로 읽는다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `04d5c2f`(= `origin/main` + B2d + B2c-a). routing 기준 `engine/src/animation_machine.cpp`(dispatch 규칙 111개). 이 파일의 dispatch 사슬을 Python 조건식으로 옮겨 "routing된 PC"를 판정했다(scratch `hroute.py`, B2d 도구와 같은 방식).
- [F] 정적 디코드: capstone M68000. block 시작 규칙은 B1 계약 "기준 입력"과 같다(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` 설치, `MOVEA.L #imm,A0` + `JSR 28ae` 자식, 연속 Bcc 묶음; routing된 PC에서 멈춤).
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/b3a/`
  - `sdec.py`(디코더, B2d `sdec.py`와 같음), `hroute.py`(routing 해석), `unit_b3a.py`(단위 정의·분류), `refs.py`(LONG·PC 상대 참조), `b3adis.py`(선형 디코드).
  - `closure_all.txt`(사슬 전체 385 block), `blocks_b3a.txt`(B3a block별 명령), `starts.txt`(B3a block 시작 216개) SHA256 `f09abc47990fea67f9f4428be6739c073c73a6eda926a44a50e06184a7ec17cf`, `starts_b3b.txt`(B3b 207개) SHA256 `23d489ae6f5f5955089d51b896637c083ed5273d3080cb49d9245326e023def1`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인. "자연 400 frame"은 D1 구동기 기록(137 seed × 400 frame)을 말한다.

## 요약

- [F] **사슬 전체**(B2d 계약 "결정 4 대상" 재현): N28 `2ba3e MOVE.L #2ba50,(A6)`의 설치 값 `2ba50`에서 시작하는 정적 closure는 `2ba50..2c760` 연속 3,344바이트, 명령 756개, block 시작 **360개**다. routing 밖 helper `2b532` `2b608` `2b63e`(`2b532..2b668`, 25 block)를 넣으면 **385**다. 여기서 더 나가는 routing 밖 PC는 `8d34`(leaf, 8 block), `1c114`(`2b636 JSR`), `2c96a`(분기 출구, `2c94c..` 함수)와 `28ae` 자식 값 `2d7be` `2d916` `2db06`이다.
- [F] **둘로 나눈다**(결정 1). 사슬은 상태 callback 여럿이 공통 꼬리 `2c562..2c71a`와 helper `2c71a` `2b418`(N28) `2b532` `2b608` `2b63e`로 모이는 한 상태기계다. 나누는 자리는 앞이 `BRA.W 2c562`로 끝나는 코드 경계 `2baf4`·`2c0fc`다.
  - **B3a(이 단위) 216 block**: 설치 머리 `2ba50..2baf4`(17), 뒤 상태들과 공통 꼬리·`2c71a` helper `2c0fc..2c760`(166), helper `2b532..2b668`(25), leaf `8d34..8da2`(8). 앞 머리의 세 상태(`2ba50` `2ba70` `2bab2`)는 B3a 안(`2c0fc` `2c6cc` `2c562` `2c71a`)으로만 나가므로 N28이 설치한 값부터 꼬리까지 C++에서 끝난다.
  - **B3b(다음 단위) 207 block**: 가운데 상태 `2baf4..2c0fc`(177)와 분기 출구 상태 `2c96a..2ca68`(30). 아래 "B3b" 절에 범위·진입·block 목록을 적는다.
- [F] **현재 routing과의 관계**: B3a 네 범위의 모든 짝수 PC는 현재 routing 밖이다(겹침 0). 경계 이웃: `8d32`(hud)·`8da2`(routing됨), `2b530`(N28)·`2b668`(N28), `2ba4e`(N28)·`2baf4`(B3b, routing 밖), `2c0fa`(B3b, routing 밖)·`2c760`(N28).
- [F] **도달성**: 진입 `2ba50`은 routing된 N28 `2ba3e`가 설치한다. `8d34`는 routing된 N33 `3b2b8`·B1b `3df22`가 `JMP`한다. 그 밖 진입은 사슬 안 설치·분기다. 자연 400 frame은 어느 B3a PC도 실행하지 않는다([F] D1 54,400/54,400 일치 기록: 이 PC들은 routing 밖이었으므로 실행됐다면 C++ 오류로 불일치가 났다; N28 계약: `2ba10` `4d2d4` Clear로 `2ba3e` 설치가 자연 경로에 없다). 검증은 typed fixture와 V1 선언 fixture(원본 ROM native 대 C++)로 한다.
- [I] 의미: seed 116/117 N28 객체(walker/점프하는 적 계열)의 이동 상태기계다. `2ba50` 등장 머리, `2c0fc`(달리기) `2c1ae`(공격) `2c212`/`2c236`(공중 이동) `2c300`(낙하) `2c390`/`2c3f6`/`2c460`/`2c4aa`(피격·넉백) `2c6cc`(정지) 상태와 매 frame 공통 꼬리(`2c562`: 무적 타이머, 경로 목록, 착지·충돌 판정, 다음 상태 설치)다.

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `8d34..8da2` | 110 | `7dfbdcc60413ed8f28107c36d7277ccf601b415fcdf9f03c1fa5f93b85894852` | 8 | 55 |
| `2b532..2b668` | 310 | `13aa62ccdc7a389e07fde063f02398b77601c7c9ed6003d07142de3691673600` | 25 | 155 |
| `2ba50..2baf4` | 164 | `7a57ba075fc9a595985ad39a4d5021cfa5843a1237b1595535d121dffe200a04` | 17 | 82 |
| `2c0fc..2c760` | 1,636 | `ae6bde9e3f0c4691bc6be8fc382331f930d83000fea5c99c42197b86ea4585fa` | 166 | 818 |
| 합계 B3a | 2,220 | 이어 붙인 바이트 `a33246c97cf605778d95a374c32a21ed3e1f871b02facef7b375df7fd8ffbc1d` | **216** | 1,110(내부 894) |

## 공통 규칙·native 검증 계획

B1 계약 "공통 규칙"(실행부·이름, routing, 경계, known C, 표, banked 읽기, `2986`, interpreter)과 "공통 native 검증 계획"(V1, `U.natural_cases()` = D1 `declared_rebase()` + `R.prepared(case)`, `U.seed_node_fixture` + `U.with_host_writes`, block 직접 진입·오류·표·음성·회귀), B2 계약 "자식(`28ae`) 진입 fixture"·"helper 진입 fixture", B2c/B2d 계약의 공유 파일·macOS seed 관례를 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_b3a.cpp`, 함수 `animation_objects_b3a_block`. 오류 문자열은 `unsupported animation objects b3a PC`(범위 안 내부 PC 직접 진입)와 `objects b3a caller requires known carry`(C 소비 block에 Unknown C)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(네 범위), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 10개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES`, test 목록, 시험 target·실행 줄; Codex의 object 재사용 구조 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** B3a 밖으로 나가는 routing 밖 PC는 넷이다: B3b 진입 `2bef6` `2bfcc`(분기), `2c96a`(분기, B3b), callee `1c114`(`2b636`). 단위 시험은 그 PC에서 stop만 확인한다(F4 관례). 설치 값 `2baf4`(B3b)와 `28ae` 자식 값 `2d7be` `2d916`은 자료이고 실행 PC가 아니다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. 다른 단위의 PC(B3b 포함)를 "미연결 탐침"으로 쓰지 않는다.
- **자료 읽기**(live bus, F1 결정 3: 상한 검사 없음):
  - `2b64c`: `LEA 2d8b8(PC),A4; ADDA.W D1,A4`, D1.W = 4·BYTE `7c`(0..`3fc`) → WORD 두 개(`2d8b8..2dcb7`).
  - `2c23e`: `LEA 2b6c4(PC),A0; MOVE.W (A0,D0.W),D0`, D0.W = 2·BYTE `7d`(0..`1fe`) → WORD 하나(`2b6c4..2b8c3`).
  - LONG `9e(A6)`가 가리키는 기록(N28 자료 포인터 `2b3d0` 등): LONG `0` `8` `10` `14`, WORD `6` `e`. LONG `78(A6)` 기록의 BYTE `2..5`. LONG `98(A6)` 경로 목록(WORD, `ffff` 다음 WORD는 되감기 변위). `49be0` 반환 A0의 WORD `0`. leaf `8d34`의 work RAM 목록 `104d92`.
  - 단위 시험은 이 읽기들 중 고정 ROM 주소(`2d8b8..` `2b6c4..`, `9e` 기록)에만 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** `ASR.L Dn,Dm`(`2c264` `2c2ac` `2c4c4` `2c50c` `2c74e`): 회수 = Dn & 63, 32 이상이면 결과는 부호 bit로 채운 값(`0` 또는 `ffffffff`). `MOVE.W 6(A4),D6`는 D6의 하위 WORD만 바꾸고 회수는 그 D6 & 63이다. `ASR.L #1`(`2c49e`), `EXT.W`, `NEG.W`, `ADDA.W`(부호 확장), `CMPA.W #0,A0`(32 bit 비교), `LSL.W #4`, `SUBQ.B`, `ST.B`, `SCC.B`를 68000 폭 그대로 명시 구현한다(부호 있는 shift는 부호 bit를 명시적으로 채움, 미정의 동작 없음). X·DIV·MUL·TRAP·I/O port·bank 변경은 없다.
- **macOS seed.** 이 컴퓨터에는 `artifacts/linux_rebase/stage_entry_body`가 없다. 자연 seed가 필요한 V1·D1 실행은 scratch wrapper가 `D.SEED_DIR`만 역사 관측 `artifacts/stage_entry_body`(SHA256 `1f65100f…` = D1 검증기의 `HISTORIC_SEED_SHA`)로 바꾼다(도구 파일은 고치지 않음, B2c/B2d와 같음).

## carry

- [F] **소비 block 10개**(callee가 돌려준 C를 읽음):
  - `2b544 BCC.W 2b602`: `4d6b4`(B2b leaf)의 C(`4d6c4`·`4d6ea` Set, `4d6f0` Clear).
  - `2ba66 SCC.B 62(A6)`: `28ae`의 C(C3b `4fb3c` 관례). 같은 block의 `MOVE.L #2ba70,(A6)`이 C를 지우므로 block 끝 C는 Clear다(MOVE 규칙, 앞 block과 무관한 정확한 재계산).
  - `2bac8` `2c1a0` `2c2d0` `2c382` `2c43c` `2c6fc` `BCC.W`: `2b418`(N28, `JMP 49fc6`)의 C(interpreter known C).
  - `2c618 BCC.W 2c622`: `4d766`(N23 known C).
  - `2c626 BCS.W 2c642`: `2b63e`(이 단위) → `JMP 4d418`(B2b)의 C.
  - 소비 block 10개를 `carry_preserving_pc`에 넣는다. Unknown C로 들어오면 checked 오류다. `2ba66` 밖의 소비 block은 Bcc 하나뿐이라 C를 그대로 둔다.
- [F] **known C 생산 2개**: `2b5fc ORI.B #1,CCR; RTS`(Set), `2b602 ANDI.B #fe,CCR; RTS`(Clear). `2b532`의 C는 B3b 소비자 `2bb66` `2bd06` `2bea2` `2bf9c`(BCS)가 읽는다. B3a 안 호출자 `2c1ea` `2c2ba` `2c376`은 읽지 않는다.
- [F] 그 밖 RTS(`2b63c` `2c72e` `2c75a` `8d4c` `8da0`)의 C는 소비자가 없어 Unknown으로 둔다(B2c·B2d 관례). FLOW block은 carry 보존 목록에 넣지 않는다(B2c 관례, 결정 3). 같은 block 안에서 만들고 소비하는 flag(`CMPI`/`CMP`/`TST`/`BTST`/`BCLR`/`ANDI`/`SUBQ` + Bcc)는 block 안에서 계산한다.

## 설치 머리 `2ba50..2baf4`(17)

- **진입**([F]): `2ba50`(N28 `2ba3e` 설치). 범위 안 설치 `2ba70`(`2ba6a`, fall-through) `2bab2`(`2baac`, fall-through).
- **의미**([F] 바이트, [I] 해석):
  - `2ba50`: WORD `92` := 0, `28ae` 자식 `2d916`(D0.W = 0; 자료 값, routing 밖). `2ba66`: BYTE `62` := (`28ae` C Clear면 `ff`, Set이면 0), 설치 `2ba70`.
  - `2ba70`: BYTE `86` := `f`. BYTE `62` ≠ 0 → `2ba92`. 아니면 LONG `64` := 0, `JSR 2c71a`, `JSR 2b418`(N28), `BRA 2c562`.
  - `2ba92`: 소리 `1a60`(`3af8`), 애니메이션 `64674`(`49f8c`, D0.W = `100`), 설치 `2bab2`.
  - `2bab2`: BYTE `86` := `f`, LONG `64` := 0, `JSR 2c71a`, `BSR 2b418`, C Set → 설치 `2c0fc`(`2bacc`). `2bad2`: `49be0`(D0.W = WORD `88`), WORD `(A0)` & `22` = `22` → 설치 `2c6cc`. `BRA 2c562`.

## 뒤 상태·공통 꼬리 `2c0fc..2c760`(166)

공통 "입력 속도" 꼴(`2c156` `2c33c` `2c412`, B3b의 같은 꼴 포함): `49be0`(D0.W = WORD `88`), D0.W = WORD `(A0)`, D7 = 0(`2c33c`는 1), D6 = LONG `(LONG 9e)`, D0 bit 3이면 D7 += D6, bit 2이면 D7 −= D6, LONG `64` := D7.

공통 "접근" 꼴(`2c250`/`2c4aa` 앞부분, `2c734`): A4 = LONG `9e`, LONG `3a` += (LONG `10(A4)` − LONG `3a`) ASR (WORD `6(A4)` & 63). 수평 꼴(`2c274`/`2c4d4`): D7 = 0, D6.W = WORD `6(A4)`, D5 = LONG `8(A4)`, D4.W = WORD `e(A4)`; D0 bit 2이면 D7 −= D5, D6.W := D4.W; bit 3이면 D7 += D5, D6.W := D4.W; LONG `36` += (D7 − LONG `36`) ASR (D6 & 63).

- **`2c0fc`**(설치 `2bacc`, B3b 분기 `2bd12` `2beae` `2c05c` `2c0c8`): 소리 `1a62`, BYTE `82` := BYTE `7e`, 애니메이션 `64c44`, 설치 `2c122`. `2c122`: BYTE `15` bit 7 = 0 → `2c212`. BYTE `7e` ≠ BYTE `82` → BYTE `82` := `7e`, 애니메이션 `64c44`. `2c14c`: 입력 속도. bit 7 → `2c96a`(B3b), bit 5 → `2c1ae`, bit 1 → `2bfcc`(B3b), bit 6 → `2bef6`(B3b). 아니면 `2c71a`, `2b418`, C Set → 설치 `2baf4`(B3b 값). `BRA 2c562`.
- **`2c1ae`**(B3b 분기, `2c180` `2c362`): 소리 `1a60`, LONG `3a` := 0, 애니메이션 `6bdb6`, 설치 `2c1d6`. `2c1d6`: 입력, bit 6 → `BSR 2b532`. `2c1ee`: A0 = LONG `94`, `JSR 4c390`(B2b), WORD `8c` := D0.W, `BSR 2b418`(C 무시). LONG `3a` ≠ 0 → 설치 `2c236`. `BRA 2c562`.
- **`2c212`**(B3b `2bb22` 등, `2bda4` 설치, 범위 안 `2c128` `2c32e`): A1 = BYTE `7f` = 0이면 `65f56`, 아니면 `64c44`; 애니메이션, 설치 `2c236`. `2c236`: D0.W = WORD `2b6c4[BYTE 7d]`, A0 = LONG `94`, `JSR 4c408`(N34). `2c250`: 접근, 입력. `2c274`: 수평. bit 6 → `BSR 2b532`. `2c2be`: `4c390`, WORD `8c` := D0.W, `BSR 2b418`, C Set → 애니메이션 `65f56`. `2c2e4`: BYTE `15` bit 7 이고 LONG `3a` < 0 → 설치 `2c300`. `BRA 2c562`.
- **`2c300`**(`2c2f6` 설치): 소리 `1a61`, 애니메이션 `6c176`, LONG `64` := 0, 설치 `2c328`. `2c328`: bit 7 = 0 → `2c212`. 입력 속도(D7 초기 1). bit 5 → `2c1ae`, bit 1 → `2bfcc`(B3b), bit 6 → `BSR 2b532`. `2c71a`, `2b418`, C Set → 설치 `2baf4`. `BRA 2c562`.
- **`2c390`**(꼬리 `2c67a` 설치): BYTE `5e` := 0. BYTE `15` bit 7 = 0 → `2c460`. BYTE `5f` 부호로 소리 `1a59` + A1 `6e11c` / 소리 `1a5a` + A1 `6e73c`; LONG `9e` = `2b3d0`이면 A1 = `6e8e2`. 애니메이션, LONG `64` := 0, 설치 `2c3f6`. `2c3f6`: BYTE `86` |= `3e`. LONG `9e` = `2b3d0`이면 입력 속도. `2c434`: `2c71a`, `2b418`, C Set → LONG `98` := 0, 설치 `2baf4`, WORD `54` = 0이면 설치 `2c7fe`(N28 값). `BRA 2c562`.
- **`2c460`**: BYTE `5f` 부호로 소리 `1a59` + A1 `6d7ec` / `1a5a` + `6d84e`, 애니메이션. `2c496`: LONG `3a` += LONG `14(LONG 9e)` ASR 1, 설치 `2c4aa`. `2c4aa`: BYTE `86` |= `3e`, 접근, 입력, 수평, A0 = LONG `94`, `JSR 4c390`, WORD `8c` := D0.W. BYTE `15` bit 7 → (BYTE `5f` 부호로 A1 `6d890`/`6dca2`) 애니메이션, LONG `64` := 0, 설치 `2c3f6`. `2c55a`: `BSR 2b418`(C 무시), `BRA 2c562`.
- **공통 꼬리 `2c562`**(모든 상태의 `BRA.W`): D7.B := BYTE `7f` < 7(무부호)이면 1, 아니면 0. `4d98a`(D0.W = WORD `88`). WORD `92` ≠ 0 → WORD `92` −= 1. `BCLR.B #6,61(A6)`: 원래 bit가 1이고 BYTE `5e` ≠ `18` → `BCLR #7,61`, BYTE `5e` := 0.
  - `2c5ae`: A0 = LONG `98`. A0 ≠ 0 → BYTE `14` := BYTE `1a`, D1.W = WORD `(A0)+`, `ffff`면 A0 += sext(WORD `(A0)`), D1.W = WORD `(A0)+`; LONG `98` := A0, D0.B := BYTE `14`, `JSR 8d34`, `BSET #6,61`, → `2c612`. A0 = 0 → BYTE `14` := BYTE `1b`; BYTE `86` ≠ 0 → BYTE `86` −= 1, 새 값 bit 0 = 1이면 BYTE `14` := BYTE `19`, BYTE `90` := `ff`; `BSET #6,61`.
  - `2c612`: `JSR 4d766`, C Set → `BSET #6,61`. `2c622`: `BSR 2b63e`. C Clear → `4d4b4`(D0.W = WORD `88`, D1.B = 1), 설치 `2b96c`(N28), → `2c65c`. C Set → `4d7a6`(D0.W = WORD `88`), D0.B = 1이면 BYTE `83` := D1.B, `84` := D2.B.
  - `2c65c`: `4d734`(WORD `88`), `4b54e`. BYTE `5e` ≠ 0 → `BSET #6,61`, 설치 `2c390`; `5e` = `18`이면 설치 `2ca68`(N28); `5e` = `19`이면 WORD `54` := 0. `2c69e`: BYTE `15` bit 7이고 WORD `64` ≠ 0이면 `4ae4a`(A0 = `2c92e`). `2c6ba`: `4d9ba`(D0.W = WORD `88`, A1 = LONG `56`), `BRA 2c8ca`(N28 공유 꼬리).
- **`2c6cc`**(설치 `2baea`, B3b `2bd22` `2bebe` `2c054` `2c0d8`): 소리 `1a62`, 애니메이션 `6495e`, LONG `64` := 0, 설치 `2c6f4`. `2c6f4`: `2c71a`, `2b418`, C Set → `4d4b4`(WORD `88`, D1.B = 1). `2c70e`: LONG `56` := 0, `BRA 2c562`.
- **helper `2c71a`**(BSR/JSR 여럿): A0 = LONG `94`. BYTE `15` bit 7 → `JSR 4c3cc`(B2b), WORD `8c` := D0.W, RTS. 아니면 LONG `36` := LONG `64`, 접근, `JSR 4c390`, WORD `8c` := D0.W, RTS.

## helper `2b532..2b668`(25)

- **`2b532`**(B3a `2c1ea` `2c2ba` `2c376`, B3b `2bb62` `2bd02` `2be9e` `2bf98`): WORD `92` ≠ 0 → `2b602`. `4d6b4`(D0.W = WORD `88`) C Clear → `2b602`. 아니면 WORD `92` := `18`, `28ae` 자식 `2d7be`(D0.W = `a`; 자료 값, routing 밖). `2b55e`: D0 = D1 = 0, `49214`, `491b6`. `2b56e`: A4 = LONG `78`, D2.W = sext BYTE `4(A4)`, D3.W = sext BYTE `5(A4)`, BYTE `15` bit 0 → `NEG.W D2`. `2b58a`: WORD `36(A0)` := D2.W, `3a(A0)` := D3.W, `1e(A0)` := WORD `1e(A6)`. BYTE `84` = 5 → `28ae` 자식 `2d57a`, 아니면 `2d3ae`(둘 다 D0.W = `a`, B2d). `2b5c6`: BYTE `60(A0)` := BYTE `60(A6)`, D0.W = WORD `8c`, D2/D3 다시, bit 0 → D0.W += `8000`, `NEG.W D2`. `2b5f0`: WORD `76(A0)` := D0.W, D0 := `ffffffff`(MOVEQ), `4c2fa`(B2b). `2b5fc`: `ORI` Set, RTS. `2b602`: `ANDI` Clear, RTS.
- **`2b608`**(B3b `2bd2e` `2beca` `2c068` `2c0e4`): WORD `92` ≠ 0 → RTS. WORD `92` := 6, D0.W = WORD `88`, D2.W/D3.W = sext BYTE `2(A4)`/`3(A4)`(A4 = LONG `78`), bit 0 → `NEG.W D2`, `JSR 1c114`(경계), RTS.
- **`2b63e`**(꼬리 `2c622`, N28 `2ba18` `2c89a`): D0.W = WORD `88`, D1 = BYTE `7c`(MOVEQ 뒤), ×4(WORD), A4 = `2d8b8` + sext(D1.W), D2.W = WORD `(A4)+`, D3.W = WORD `(A4)+`, bit 0 → `NEG.W D2`, `JMP 4d418`(B2b, known C).

## leaf `8d34..8da2`(8)

- **진입**([F]): 꼬리 `2c5d6 JSR`, N33 `3b2b8`(`JMP`), B1b `3df22`(`JMP`), B3b `2c9d0 JSR`. 범위 밖 사용처도 이 단위 실행부로 간다.
- **의미**([F] 바이트, [I] sprite 우선순위 목록 갱신): D0.W := (D0.W & `ff`) << 4, A1 = `104d92`, A2 = A1 + sext(D0.W). WORD `8(A2)` = 0 → RTS(`8d4c`). WORD `a(A2)` = D1.W이고 WORD `c(A2)` = D1.W → RTS(`8da0`). 아니면(`8d5c`) D4.W = ((D1.W & `ff`) << 4) + 4, A4 = A1 + sext(D4.W). WORD `2(A4)` = D0.W → `8d92`. 아니면(`8d72`) D2.W = WORD `(A2)`, D3.W = WORD `2(A2)`, WORD `(A1 + sext D3.W)` := D2.W, WORD `2(A1 + sext D2.W)` := D3.W, D3.W = WORD `2(A4)`, WORD `(A1 + sext D3.W)` := D0.W, WORD `2(A2)` := D3.W, WORD `(A2)` := D4.W, WORD `2(A4)` := D0.W. `8d92`: WORD `a(A2)` := D1.W, WORD `c(A2)` := D1.W, `BSET #7,f(A2)`. RTS.
- 주소는 32 bit 그대로 계산하고 bus가 24 bit로 자른다(원본과 같음). 홀수 WORD 주소는 C++ checked 오류다(Unicorn은 68000 address error를 흉내내지 않음; 차분에서 따로 센다).

## 경계·routing 밖 출구

- [F] routing 밖으로 나가는 곳: 분기 `2bef6` `2bfcc` `2c96a`(B3b), callee `1c114`(`2b636`; `289e`·`2986`·`2291a` 꼬리, 약 21 block [I]). 단위 시험은 stop만 확인한다.
- [F] routing된 출구·callee(이 단위에는 `JMP 2a00` 삭제 출구가 없다): `28ae` `2b418` `2b96c`(설치 값만) `2c7fe` `2ca68`(설치 값만) `2c8ca`(N28), `3af8` `49f8c` `49be0` `49214` `491b6` `4ae4a` `4b54e` `4c2fa` `4c390` `4c3cc` `4c408` `4d418` `4d4b4` `4d6b4` `4d734` `4d766` `4d7a6` `4d98a` `4d9ba`.
- [F] `28ae` 자식 값 `2d916` `2d7be`(routing 밖, 각각 약 14·20 block [I])와 `2d3ae` `2d57a`(B2d)는 자료다. 자식 실행은 이후 pass다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`). V1 기반 world: seed 116/117 frame 2의 자연 node(B2d spec과 같은 `BASE_CALLBACKS`; N28 node가 이 사슬의 실제 주인)에 선언 편집(레지스터, node field, 포인터 field `78` `94` `98` `9e`, PC).
- 포인터 field는 자연 값(`9e` = `2b3d0` 등) 또는 work RAM 기록을 선언한다. `9e` 기록의 WORD `6`·`e`는 ASR 회수 경계(0, 1, 31, 32, 63, 64 이상)를 포함한다.
- 사슬(chain) fixture: 소비자 10개를 실제 생산자로 들어간다(`28ae` → `2ba66`, `4d6b4` → `2b544`, `2b418` → `2bac8` `2c1a0` `2c2d0` `2c382` `2c43c` `2c6fc`, `4d766` → `2c618`, `2b63e`→`4d418` → `2c626`).
- node fixture: 설치 값(`2ba50` `2ba70` `2bab2` `2c0fc` `2c122` `2c1d6` `2c236` `2c328` `2c3f6` `2c4aa` `2c6f4` `2c390` `2c6cc`)을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- `8d34`: work RAM 목록 `104d92`의 node·list WORD를 선언한다(같은 list, 다른 list, 끝 node 갱신, WORD `8` = 0).

## B3b(다음 단위, 이 계약에서 구현하지 않음)

- [F] **범위와 block 수**: `2baf4..2c0fc`(1,544바이트, 짝수 PC 772, SHA256 `9f077c389801ddc51d2ec819974648c33566261e1d4fd2977fbfa30e4cae3697`, 177 block)와 `2c96a..2ca68`(254바이트, 짝수 PC 127, SHA256 `413ed8715ea82b0e4c5a16632846a90eb06bdd7f944404ab707818392be99266`, 30 block) = **207 block**(짝수 PC 899, 내부 692). scratch `starts_b3b.txt`(SHA256 `23d489ae…`).
- [F] **진입**: 설치 값 `2baf4`(B3a `2c1a4` `2c386` `2c448`, B3b `2beec` `2bfac` `2bfc2`), 범위 안 설치 `2bb1c` `2bc70` `2be36` `2bf1e` `2bff2` `2c088` `2c09e` `2c9a8`, 분기 진입 `2bef6`(B3a `2c194`), `2bfcc`(B3a `2c18c` `2c36a`), `2c96a`(B3a `2c17c`; B3b `2bb46` 등). `2c96a`는 `2c94c..` 함수(앞 `2c94c..2c96a`는 자료)의 코드 시작이며 끝 `2ca64 BRA 2c8ca`(N28)·`2ca60 BRA 2ca68`(N28)로 나간다.
- [F] **표**: `2ca20 JMP 2ca24(PC,D0.W)`(앞 `CMPI.W #9,D0; BCC`), 9 slot `2ca24..2ca44`(F1 결정 3).
- [F] **known C 소비**: `2bb66` `2bd06` `2bea2` `2bf9c` `BCS`(`2b532`, B3a), `2bac8`와 같은 꼴 `2bee8` `2bfa8` `2c074` `BCC`(`2b418`), `2ca52 BCC`(`1ab02`).
- [F] **나가는 곳**: B3a(`2c562` `2c71a` `2b532` `2b608` `2c0fc` `2c1ae` `2c212` `2c6cc` `8d34`), N28(`2b418` `2c760` `2c8ca` `2ca68`), routed callee(`28ae` `3af8` `49be0` `49f8c` `4ae4a` `4d4b4` `1ab02`). routing 밖은 `28ae` 자식 값 `2db06`(자료)뿐이다. 즉 B3a 병합 뒤 B3b는 끝까지 C++에서 실행된다.
- block 목록(207): `2baf4 2bb06 2bb16 2bb1c 2bb26 2bb30 2bb3a 2bb42 2bb4a 2bb52 2bb5a 2bb62 2bb66 2bb6a 2bb76 2bb7a 2bb7e 2bb96 2bb9a 2bba0 2bbb2 2bbb6 2bbd2 2bbd6 2bbdc 2bbf2 2bbf6 2bc06 2bc10 2bc20 2bc2a 2bc3a 2bc44 2bc54 2bc5a 2bc64 2bc70 2bc7a 2bc84 2bc8e 2bc94 2bc9c 2bca6 2bcac 2bcb4 2bcbc 2bcc0 2bcc8 2bcd0 2bcd4 2bcd8 2bce2 2bcea 2bcf2 2bcfa 2bd02 2bd06 2bd0a 2bd0e 2bd16 2bd1e 2bd26 2bd2e 2bd32 2bd36 2bd48 2bd56 2bd58 2bd5c 2bd6c 2bd72 2bd76 2bd86 2bd8c 2bd96 2bd9a 2bda4 2bdaa 2bdb4 2bdbe 2bdd2 2bdd6 2bde0 2bdfe 2be0a 2be1c 2be1e 2be28 2be36 2be40 2be4a 2be54 2be5c 2be60 2be68 2be70 2be74 2be7e 2be86 2be8e 2be96 2be9e 2bea2 2bea6 2beaa 2beb2 2beba 2bec2 2beca 2bece 2bee0 2bee4 2bee8 2beec 2bef2 2bef6 2bf08 2bf18 2bf1e 2bf28 2bf32 2bf3c 2bf4c 2bf4e 2bf56 2bf58 2bf60 2bf68 2bf70 2bf78 2bf80 2bf88 2bf90 2bf98 2bf9c 2bfa0 2bfa4 2bfa8 2bfac 2bfb2 2bfba 2bfc2 2bfc8 2bfcc 2bfd6 2bfec 2bff2 2bffe 2c012 2c01c 2c026 2c038 2c03a 2c042 2c044 2c050 2c058 2c060 2c068 2c06c 2c070 2c074 2c078 2c084 2c088 2c098 2c09e 2c0a8 2c0b2 2c0bc 2c0c4 2c0cc 2c0d4 2c0dc 2c0e4 2c0e8 2c0f0 2c0f4 2c0f8 2c96a 2c974 2c98c 2c99a 2c9a8 2c9b4 2c9c4 2c9c8 2c9d6 2c9e6 2c9e8 2c9f6 2c9fa 2ca0a 2ca14 2ca1c 2ca24 2ca28 2ca2c 2ca30 2ca34 2ca38 2ca3c 2ca40 2ca44 2ca48 2ca52 2ca56 2ca60 2ca64`.
- [I] 남는 작은 사슬(어느 계약에도 없음): `28ae` 자식 `2d7be`(약 20 block), `2d916`(약 14), `2db06`(약 16), callee `1c114`(+`2291a` 꼬리, 약 21). 합 약 71이라 한 단위(B3c 후보)로 묶을 수 있다.

## `4c390` `4c3a2` `4c3cc` 진입 조각(B2 결정 3)

- [F] 세 조각은 이미 B2b가 routing한다(`animation_machine_objects_b2b.cpp` `case 0x4c390: case 0x4c3a2: case 0x4c3cc`, routing `4c390..4c3ba` `4c3cc..4c3de`). B2 결정 3은 `4c3ba`(정적 참조 0) 하나만 미사용 후보로 남겼다.
- [F] B3a는 `4c390`의 남은 호출자 `2c1f2` `2c2c2` `2c516` `2c754`와 `4c3cc`의 호출자 `2c728`을 routing한다. 그래서 이 조각들은 B3a fixture에서 실제 호출자로 실행된다. B3a는 `4c3ba`를 참조하지 않는다(전체 closure의 callee 목록에 없음).
- **판단**: 세 조각을 B3a로 옮기지 않는다(같은 실행부에 두 번 routing할 수 없고, 이미 B2b 시험이 진입을 덮음). `4c3ba`는 계속 routing하지 않고 "미사용 후보 [I]"로 둔다(결정 4).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색: B3a PC를 쓰는 기존 시험은 모두 stop 확인이다(stop은 routing 판정보다 먼저라 그대로 통과).
  - `animation_machine_objects_n28_test.cpp`: stop `2b63e` `2c71a` `8d34`, RANGES 이웃 `2b532` `2ba50`(홀수 탐침 `2b531` `2ba4f`는 여전히 unaligned).
  - `animation_machine_objects_n33_test.cpp`(stop `8d34`), `animation_machine_objects_b1b_test.cpp`·`tools/unit_fixture_specs/b1b.py`(stop/후속 `8d34`).
  - `n34`·`b1c`·`u20` 시험의 같은 값은 레지스터·자료 값이다. 그 밖 `8d3x` 상수는 RAM `108d3x`(A5 기준) 등 다른 의미다.
- [F] 구현 뒤 `make test`가 찾은 무효 탐침 1건(16진 상수 검색으로는 보이지 않던 계산 PC): B1c 표 block `335f6`에 D0.W = `2000`을 넣으면 PC = `335fe` + sext(`8000`) = `2b5fe`다. 원래 "routing 밖" 기대(`unsupported animation machine PC`)였고, 이제 B3a block `2b5fc`(`ORI.B #1,CCR`) 내부라 `unsupported animation objects b3a PC`가 된다. 이 표의 착지 범위는 `335fe` ± 32 KiB라 RAM `10fexx` 값으로 옮길 수 없다. 메인 결정(아래)대로 기대 문자열만 바꾸고, 같은 상태를 stop `2b5fe`로 실행해 착지 PC가 정확히 `2b5fe`임도 확인한다(시험 `animation_machine_objects_b1c_test.cpp`, V1 spec `b1c.py` 픽스처 `error-table-335f6-unrouted-s116/117`·`table-335f6-landing-2b5fe-s116/117`). 그 밖 rollback 기대는 B3a PC를 쓰지 않는다(B1a·B2a·B2b·B2c spec의 `UNROUTED_NEIGHBOURS`·c1·c2·c3b 이웃 목록 확인).
- [I] 자연 경로를 바꾸지 않으므로 D1 구동기(Skip), controller `Execute`(ii), 실제 IRQ 비교는 54,400/54,400 그대로여야 한다(회귀로 확인).

## 결정 필요 (MAIN DECISION NEEDED)

1. **분할.** 385 + `8d34` 8 = 393 block을 B3a(216: `2ba50..2baf4` `2c0fc..2c760` `2b532..2b668` `8d34..8da2`)와 B3b(207: `2baf4..2c0fc` `2c96a..2ca68`)로 나눈다(작업자 권고·구현). 대안: `8d34`를 빼고 B3a 208.
2. **`8d34` 포함.** 어느 계약에도 없던 공용 leaf(8 block)를 B3a에 넣는다(꼬리 `2c5d6`가 부르고 N33·B1b·B3b의 경계를 함께 줄임). 대안: 경계로 두고 `98(A6)` ≠ 0 경로는 `8d34`에서 stop.
3. **carry 보존 목록.** 소비자 10개만 넣는다(B2c 꼴). 대안: FLOW block 전부(B2d 꼴).
4. **`4c3ba`.** 계속 routing하지 않는다(B2 결정 3 유지). `4c390` `4c3a2` `4c3cc`는 B2b에 둔다.
5. **`2ba66`의 block 끝 C.** `SCC` 뒤 `MOVE.L #2ba70,(A6)`이 C를 지우므로 Clear로 둔다(정확한 재계산).

## 메인 결정

메인(2026-10-16) 결정: 1) B3a 216 / B3b 207 분할 채택. 2) `8d34`를 B3a에 넣음. 3) carry 보존 목록은 소비자 10개만. 4) `4c3ba` routing 안 함, `4c390` `4c3a2` `4c3cc`는 B2b에 둠. 5) B1c 탐침 이전(`335f6` D0.W = `2000` → `2b5fe`, B3a 내부 오류) 채택, 실패 PC `2b5fe`도 확인할 것(리뷰 0264 L-1). 이 문서와 구현은 결정과 같다.

## 구현·검증 기록

- 파일: `engine/src/animation_machine_objects_b3a.cpp`(실행부), `engine/tests/animation_machine_objects_b3a_test.cpp`(단위 시험), `tools/unit_fixture_specs/b3a.py`(V1 spec). 공유 수정은 "공통 규칙"의 다섯 곳과 B1c 탐침 이전 두 파일뿐이다.
- [F] `make -j3 all test`: 종료 0, 새 경고 0, Assert 줄 0. 시험 실행 264개(기준 263 + B3a), Python 310개 통과.
- [F] 단위 시험(`run_animation_machine`만): 651 fixture(단일 block 442, 경로 125, 실제 생산자 사슬 45, 선언 C 20, checked 오류 19). 모든 시작 × 들어오는 C 3가지, zero-step, 내부 PC 894개 정확한 오류, 경계 stop `2bef6` `2bfcc` `2c96a` `1c114`, RTS block 7개의 RAM 탐침(`10fe90`) rollback, 소비자 10개 Unknown C 오류, `2ba66` SCC 두 값. fixture 표는 scratch 생성기(Unicorn, 합성 byte `2d8b8..` `2b6c4..` `2b3d0..`)가 만든 native 정지 상태다. UBSan(`-fsanitize=undefined -fno-sanitize-recover`) 빌드도 통과했다.
- [F] 변이 18개(ASR 32 이상, 표 배율, SCC 반전, block 끝 C, `CMPI` 경계, `ADDA.W` 부호, list offset, shift mask, BCLR 분기, MOVEQ 초기값, EXT, 소비자 분기, 별칭 읽기 순서 등) 모두 단위 시험이 잡았다.
- [F] V1(`verify_animation_machine_unit_fixtures.py` + `b3a.py`, seed 116/117 frame 2의 자연 N28 node, macOS seed wrapper): 1,467/1,467 일치(match 549, 오류 908, 음성 10). 시작 216/216 방문, 모든 조건분기 양쪽과 소비자 10개의 실제 생산자 사슬 양쪽(`2b418` Set은 LONG `26(A6)` = 0, `4d766` Set은 BYTE `10f000` bit 7, `4d418` Set은 player callback ≠ `270e`) 도달. carry oracle 일치(끝 C Unknown/Clear/Set 524/14/11). 두 번 실행한 report가 시간 항목 밖에서 같다. 자연 node 상태 위 선언 편집이라 "자연 실행"이 아니다(자연 400 frame은 이 PC들을 실행하지 않음).
- [F] 실제 ROM 차분(scratch `realrom/real_b3a.py`, Unicorn 대 C++ + `program_rom_*.ms5d` 8개, bank `200000`/`300000`, 무작위 work RAM, native는 STOP·C++ routing 밖 첫 PC·interpreter 선언 stop에서 멈춤): 5 batch × 1,500 = 7,500 case 불일치 0. 시작 216/216(batch 하나는 213). 실제 생산자 뒤 소비자 native 분기 비교 수천 회(`2c618` `2c626` 각 batch 400~600회). 홀수 주소·`2986` X·Unknown C 진입 차이 0.
- [F] 프레임 회귀(D1 구동기, controller `Execute --declare game`, 실제 IRQ; 출력 scratch): 각 54,400/54,400 일치, 136 seed 완주, B2c 작업 트리 보고서와 시간·입력 항목 밖에서 같다.
- [F] B1c 이전 확인: 단위 시험 통과, V1 `--only` 4/4 일치.

## 미확인

- [U] LONG `94(A6)`(`4c390`/`4c3cc`/`4c408`의 A0)·`78(A6)`(BYTE 쌍 기록)·`9e(A6)` 기록 각 field의 의미(위치·속도 표로 추정).
- [U] `8d34`가 다루는 `104d92` 목록의 화면 의미(sprite 우선순위 list로 추정).
- [U] `2c96a`·`1c114`·자식 `2d7be` `2d916` `2db06`의 의미.
- [U] 400 frame 밖·응답 `00`·controller 생략 해제 시의 자연 도달(`2ba3e` 설치 조건 `4d2d4` Set).

## block 목록

[F] scratch `starts.txt`(SHA256 `f09abc47990fea67f9f4428be6739c073c73a6eda926a44a50e06184a7ec17cf`)와 같다.

- **`8d34..8da2`(8)**: `8d34 8d4c 8d4e 8d54 8d5c 8d72 8d92 8da0`
- **`2b532..2b668`(25)**: `2b532 2b53a 2b544 2b548 2b55e 2b568 2b56e 2b588 2b58a 2b5a2 2b5b2 2b5b6 2b5c6 2b5ea 2b5f0 2b5fc 2b602 2b608 2b610 2b634 2b636 2b63c 2b63e 2b660 2b662`
- **`2ba50..2baf4`(17)**: `2ba50 2ba66 2ba70 2ba7e 2ba8a 2ba8e 2ba92 2ba9c 2baac 2bab2 2bac4 2bac8 2bacc 2bad2 2badc 2baea 2baf0`
- **`2c0fc..2c760`(166)**: `2c0fc 2c106 2c11c 2c122 2c12c 2c138 2c14c 2c156 2c168 2c16a 2c172 2c174 2c180 2c188 2c190 2c198 2c19c 2c1a0 2c1a4 2c1aa 2c1ae 2c1b8 2c1d0 2c1d6 2c1e0 2c1ea 2c1ee 2c1f8 2c200 2c208 2c20e 2c212 2c220 2c226 2c230 2c236 2c250 2c274 2c298 2c29c 2c2a4 2c2a8 2c2ba 2c2be 2c2c8 2c2d0 2c2d4 2c2e4 2c2ee 2c2f6 2c2fc 2c300 2c30a 2c31a 2c328 2c332 2c33c 2c34e 2c350 2c358 2c35a 2c366 2c36e 2c376 2c37a 2c37e 2c382 2c386 2c38c 2c390 2c3a0 2c3a8 2c3b2 2c3bc 2c3c6 2c3cc 2c3d8 2c3de 2c3e8 2c3f6 2c408 2c412 2c424 2c426 2c42e 2c430 2c434 2c438 2c43c 2c440 2c456 2c45c 2c460 2c468 2c472 2c47c 2c486 2c48c 2c496 2c4aa 2c4d4 2c4f8 2c4fc 2c504 2c508 2c51c 2c52a 2c532 2c53c 2c542 2c54c 2c55a 2c55e 2c562 2c56c 2c574 2c578 2c582 2c58a 2c58e 2c598 2c5a2 2c5ae 2c5ba 2c5ca 2c5ce 2c5dc 2c5e6 2c5f4 2c602 2c60c 2c612 2c618 2c61c 2c622 2c626 2c62a 2c638 2c642 2c64c 2c654 2c65c 2c666 2c66c 2c674 2c68a 2c690 2c69a 2c69e 2c6a8 2c6b0 2c6ba 2c6c8 2c6cc 2c6d6 2c6e6 2c6f4 2c6f8 2c6fc 2c700 2c70e 2c71a 2c728 2c72e 2c734 2c75a`
