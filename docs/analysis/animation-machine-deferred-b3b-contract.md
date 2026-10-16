# N28 범위 밖 설치 사슬 `2ba50`의 가운데 상태·분기 출구 상태 구현 계약 B3b

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안, 결정 1은 메인이 접기로 확정.** 이 문서를 먼저 쓰고 그대로 구현한다. 범위는 B3a 계약 "B3b" 절(메인 결정 1: B3a 216 / B3b 207(결정 1 접기 뒤 구현 206) 분할)이다. 아래 수치와 목록은 작업자가 정적 디코드로 다시 계산했다. 결정 항목(끝)은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 이 문서의 코드 주소는 모두 고정 영역(`<100000`)이라 CPU 주소와 파일 오프셋이 같다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `2c7e5a4`(작업 주기 = `origin/main` + B2c-a + B2d + B2e + B3a). routing 기준 `engine/src/animation_machine.cpp`(dispatch 규칙 113개). 이 사슬을 Python 조건식으로 옮겨 "routing된 PC"를 판정했다(scratch `hroute.py`, B3a 도구와 같은 방식, 경로만 이 작업 트리).
- [F] 정적 디코드: capstone M68000. block 시작 규칙은 B1 계약 "기준 입력"과 같다. 진입은 `2baf4`(설치 값) `2bef6` `2bfcc` `2c96a`(B3a의 분기 대상)와 표 slot 9개(`2ca24 + 4·k`, k = 0..8)다. routing된 PC에서 멈춘다.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/b3b/`
  - `sdec.py` `hroute.py` `b3adis.py`(B3a scratch 복사, 경로만 바꿈), `unit_b3b.py`(단위 정의·분류), `closure.py`(B3c 후보 크기), `lin.txt`(선형 디코드), `blocks.txt`(block별 명령).
  - `starts.txt`(원래 B3b 시작 207개; 접기 뒤 `2bd58`을 뺀 206개는 scratch `starts206.txt` SHA256 `cfdb1f66f348a9022d65065e33a27c08f99630c21d396c7d0d6be58c60720387`) SHA256 `23d489ae6f5f5955089d51b896637c083ed5273d3080cb49d9245326e023def1` — B3a scratch `starts_b3b.txt`와 바이트 단위로 같다.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인. "자연 400 frame"은 D1 구동기 기록(137 seed × 400 frame)을 말한다.

## 요약

- [F] **범위·block 수**(B3a 계약 "B3b" 절 재현):

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `2baf4..2c0fc` | 1,544 | `9f077c389801ddc51d2ec819974648c33566261e1d4fd2977fbfa30e4cae3697` | 177 | 772 |
| `2c96a..2ca68` | 254 | `413ed8715ea82b0e4c5a16632846a90eb06bdd7f944404ab707818392be99266` | 30 | 127 |
| 합계 B3b | 1,798 | 이어 붙인 바이트 `032dec3dbd5616f414c22ac06e19c5f9948c95a24234b5b76e0e6117a92392cb` | **207 → 접기 뒤 206** | 899(내부 692 → 693, `2bd58` 포함) |

- [F] 명령 444개, 정적 closure가 두 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). 연속 Bcc 묶음 없음. 간접 분기는 `2ca20 JMP 2ca24(PC,D0.W)` 하나(정적으로 한정된 9 slot 표).
- [F] **현재 routing과의 관계**: 두 범위의 짝수 PC는 모두 routing 밖이다(겹침 0). 경계 이웃: `2baf2`(B3a `2baf0`)·`2c0fc`(B3a), `2c968`(routing 밖 자료 `2c94c..2c96a`)·`2ca68`(N28).
- [F] **나가는 곳은 모두 routing돼 있다**: B3a(`2c0fc` `2c1ae` `2c212` `2c562` `2c6cc` `2c71a` `2b532` `2b608` `8d34`), N28(`2b418` `2c760` `2c8ca` `2ca68`), routed callee(`28ae` `3af8` `49be0` `49f8c` `4ae4a` `4d4b4` `1ab02`). routing 밖 값은 `28ae` 자식 값 `2db06`(자료, `2bdbe`)뿐이다. 그래서 B3a + B3b 뒤 사슬 `2ba50`은 `28ae` 자식 실행(이후 pass) 밖에서 끝까지 C++로 실행된다.
- [F] **도달성**: 진입 `2baf4`는 B3a `2c1a4` `2c386` `2c440`(설치)과 B3b `2beec` `2bfac` `2bfc2`(설치), `2bddc` `2bedc`(분기)가 쓴다. `2bef6` `2bfcc` `2c96a`는 B3a 분기(`2c194`, `2c18c` `2c36a`, `2c17c`)와 B3b 안 분기가 쓴다. 자연 400 frame은 이 사슬을 실행하지 않는다(B3a 계약 "도달성", N28 `2ba3e` 설치가 자연 경로에 없음). 검증은 typed fixture와 V1 선언 fixture로 한다.
- [I] 의미: seed 116/117 N28 객체(walker 계열)의 지상 상태들이다. `2baf4` 서기, `2bb7e`/`2bb9a`/`2bbb6`/`2bbd6` 걷기 시작(방향·속도), `2bc70` 걷기, `2bdd6`→`2be36` 미끄러져 멈춤, `2bef6`→`2bf1e` 사격 자세, `2bfcc`→`2bff2` 웅크림, `2c088`→`2c09e` 다른 서기 꼴(BYTE `7f` ≥ 7), `2c96a`→`2c9a8` 경로 목록을 따라가는 특수 동작(충돌 판정 `4ae4a`·`1ab02` 뒤 N28 `2ca68`/`2c8ca`로 감)이다.

## 공통 규칙·native 검증 계획

B1 계약 "공통 규칙"과 "공통 native 검증 계획", B2 계약 "자식(`28ae`) 진입 fixture", B2c/B2d/B2e/B3a 계약의 공유 파일·macOS seed 관례를 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_b3b.cpp`, 함수 `animation_objects_b3b_block`. 오류 문자열은 `unsupported animation objects b3b PC`(범위 안 내부 PC 직접 진입)와 `objects b3b caller requires known carry`(C 소비 block에 Unknown C)다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(두 범위), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(소비자 8개), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES`, test 목록 실행 줄, 시험 target; Codex의 object 재사용 구조 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** 이 단위에서 routing 밖으로 나가는 실행 PC는 없다. `28ae` 자식 값 `2db06`은 자료다(단위 시험은 `28ae` 진입에서 A0 = `2db06`, D0.W = `1e`로 stop만 확인한다). B3a 시험이 stop으로 확인하던 `2bef6` `2bfcc` `2c96a`는 이제 이 단위의 block 시작이다. stop 판정은 routing보다 먼저라 B3a 시험·spec은 그대로 통과해야 한다(회귀로 확인). rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1). 기대 오류 fixture마다 실패 PC를 적는다. 실패 PC가 진입 PC와 다르면 같은 상태를 stop = 실패 PC로 실행해 정확히 그 PC에서 멈추는지(성공) 함께 확인한다. 실패 PC가 진입 PC와 같으면(내부 PC, 홀수 PC, Unknown C 소비자, 진입 block 안의 정렬 오류) 그 사실을 fixture 이름·주석에 적는다.
- **자료 읽기**(live bus, F1 결정 3):
  - LONG `9e(A6)` 기록의 LONG `0`(`2bb7e` `2bba0` `2bbb6` `2bbdc` `2bf3c` `2c026`).
  - LONG `98(A6)` 경로 목록(`2c9a8..2c9c8`): WORD, `ffff` 다음 WORD는 되감기 변위(B3a `2c5ae`와 같은 꼴). 설치 값 `2c7a6`은 N28 범위 안 고정 ROM WORD 목록이다(`2c974`).
  - `49be0` 반환 A0의 WORD `0`(입력 bit).
  - 단위 시험은 고정 ROM 주소 읽기(`9e` 기록 = `2b3d0`인 경우, 경로 목록 `2c7a6..`)에만 합성 typed physical byte를 둔다(ROM 자료가 아니다). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **정수 연산.** `NEG.L`(`2bbc2` `2bbe2` `2bd56` `2c9e6`), `EOR.B D0,D1` + `BPL`/`BMI`(결과 BYTE bit 7), `SMI.B 85(A6)`(LONG `64` 부호), `SNE.B D0`(BYTE `15` bit 0), `LSL.B #4,D0`(하위 BYTE만) + `SUB.B D0,9c(A6)` + `BCC`(빌림), `SUBQ.B #1,9d(A6)`, `TST.L` + `BLE`/`BGE`(부호 LONG, V = 0), `CMPI.B #7/#5` + `BCC`/`BCS`(무부호), `CMPA.W #0,A0`(32 bit 비교), `ADDA.W (A0),A0`(부호 확장), `ASR.L #5,D0`(부호 bit 채움), `SUB.L`/`ADD.L`, `CMPI.W #9,D0` + `BCC`, `ADD.W D0,D0` 두 번을 68000 폭 그대로 명시 구현한다. X·MUL·DIV·TRAP·I/O port·bank 변경은 없다.
- **macOS seed.** 이 컴퓨터에는 `artifacts/linux_rebase/stage_entry_body`가 없다. 자연 seed가 필요한 V1·D1 실행은 B3a와 같은 scratch wrapper가 `D.SEED_DIR`만 역사 관측 `artifacts/stage_entry_body`(SHA256 `1f65100f…` = D1 검증기의 `HISTORIC_SEED_SHA`)로 바꾼다(도구 파일은 고치지 않음).

## carry

- [F] **소비 block 8개**(callee가 돌려준 C를 읽음):
  - `2bb66` `2bd06` `2bea2` `2bf9c` `BCS.W 2bef6`: `2b532`(B3a)의 C(`2b5fc ORI` Set, `2b602 ANDI` Clear).
  - `2bee8` `2bfa8` `2c074` `BCC.W`: `2b418`(N28, `JMP 49fc6`)의 C(interpreter known C).
  - `2ca52 BCC.W 2ca64`: `1ab02`(U05; `1aafc` Set / `1ab7a` Clear 꼴의 known C).
- [F] 8개만 `carry_preserving_pc`에 넣는다(B2c·B3a 꼴). Unknown C로 들어오면 checked 오류다. 이 단위에는 다른 block이 소비하는 known C 생산자가 없다(ORI/ANDI CCR 없음). 그 밖의 모든 block은 진입 때 Unknown이 된다. 같은 block 안에서 만들고 소비하는 flag는 block 안에서 계산한다.
- [F] **block 경계를 건너는 N 하나(접기, 메인 결정 1 확정)**: `2bd58 BMI.W 2bd76`은 분기 대상(`2bd52 BEQ`)이고 선행 block이 둘이다: `2bd48`(`MOVE.L 64(A6),D0; BTST.B #0,15(A6); BEQ` — BTST는 Z만 바꾼다)과 `2bd56`(`NEG.L D0`). 프로젝트 규칙(flag는 유일 predecessor에서만 block 경계를 건너 다시 계산)에 따라 선행마다 BMI를 접는다(선례 N04 `ab1a6`, N09 `af7b0`, N15 `71c86`). `2bd48` block은 `MOVE.L; BTST; BEQ`에 이어 taken(`2bd58`)이면 자기 D0 bit 31(MOVE.L의 N)로 `2bd76`/`2bd5c`를, fall이면 `2bd56`을 고른다. `2bd56` block은 `NEG.L D0; BMI.W 2bd76`을 한 block으로 실행해 NEG 결과 bit 31로 `2bd76`/`2bd5c`를 고른다. `2bd58`은 block 시작이 아니라 내부 PC이므로 직접 진입은 `unsupported animation objects b3b PC` 오류다(선례와 같음; N04 `ab1a6` 직접 진입 오류). block은 206개, 내부 PC는 693개다.

## 가운데 상태 `2baf4..2c0fc`(176, 접기 뒤)

공통 "입력 bit" 꼴: `MOVE.W 88(A6),D0; JSR 49be0` 뒤 `MOVE.W (A0),D0`, 이어서 `BTST.B #n,D0` + `BNE`/`BEQ`(Z만). 공통 "입력 속도" 꼴(`2bf3c` `2c026`, B3a `2c156` 꼴): D7 = 0, D6 = LONG `(LONG 9e)`, bit 3이면 D7 += D6, bit 2이면 D7 −= D6, LONG `64` := D7.

- **`2baf4`**(설치 값): LONG `98` := 0. BYTE `7f` ≥ 7(무부호) → `2c088`. 아니면 애니메이션 `65f56`(`49f8c`, D0.W = `100`), 설치 `2bb1c`.
- **`2bb1c`**: BYTE `15` bit 7 = 0 → `2c212`(B3a). 입력: bit 3 → `2bb7e`, bit 2 → `2bbb6`, bit 7 → `2c96a`, bit 5 → `2c1ae`(B3a), bit 1 → `2bfcc`, bit 6이면 `BSR 2b532`, C Set → `2bef6`. `2bb6a`: LONG `64` := 0, `BSR 2c71a`, `BSR 2b418`(C 무시), `BRA 2c562`.
- **걷기 시작 넷**: `2bb7e` BYTE `9d` := 5, LONG `64` := LONG `(LONG 9e)`, BYTE `15` bit 0 = 0 → `2bbf6`, 아니면 `2bc10`. `2bb9a` BYTE `9d` := 3 → `2bba0` LONG `64` := LONG `(9e)`, bit 0 = 0 → `2bc2a`, 아니면 `2bc44`. `2bbb6` BYTE `9d` := 5, LONG `64` := −LONG `(9e)`(D0에도), bit 0 ≠ 0 → `2bbf6`, 아니면 `2bc10`. `2bbd6` BYTE `9d` := 3 → `2bbdc` LONG `64` := −LONG `(9e)`, bit 0 ≠ 0 → `2bc2a`, 아니면 `2bc44`.
- **애니메이션 선택 넷**(`2bbf6` `2bc10` `2bc2a` `2bc44`): A1 := 첫 표(`6795e` `68230` `67e12` `686e4`), BYTE `7f` < 7이면 그대로, 아니면 둘째 표(`68c30` `69502` `690e4` `699b6`). `2bc5a`: 애니메이션. `2bc64`: BYTE `82` := BYTE `7e`, 설치 `2bc70`.
- **`2bc70`**(걷기): 입력. bit 0 → `BSET #5,61` 아니면 `BCLR #5,61`. bit 1 → `BSET #4,61` 아니면 `BCLR #4,61`. bit 3 → LONG `64` ≤ 0(부호)이면 `2bb9a`, 아니면 `2bcd8`. bit 3 = 0, bit 2 → LONG `64` ≥ 0이면 `2bbd6`, 아니면 `2bcd8`. 둘 다 0 → `2bdd6`.
  - `2bcd8`: BYTE `7f` ≥ 5 → `2bd0e`. 아니면 bit 7 → `2c96a`, bit 1 → `2bfcc`, bit 5 → `2c1ae`, bit 6이면 `BSR 2b532`, C Set → `2bef6`; `2bd0a` → `2bd32`.
  - `2bd0e`: bit 1 = 0 → `2c0fc`(B3a). bit 7 → `2c96a`, bit 5 → `2c6cc`(B3a), bit 6이면 `BSR 2b608`(B3a).
  - `2bd32`: `BSR 2c71a`. `2bd36`: D0.B := BYTE `7e`, D1.B := BYTE `82`, BYTE `82` := D0.B, (D0.B ^ D1.B) bit 7 = 0 → `2bd96`. `2bd48`: D0 := LONG `64`, BYTE `15` bit 0 → `NEG.L D0`(`2bd56`). `2bd58`(접힘): D0 bit 31(N) → `2bd76`(A1 `686e4`/`699b6`), 아니면 `2bd5c`(A1 `67e12`/`690e4`; BYTE `7f` < 7이면 첫째). `2bd8c`: 애니메이션.
  - `2bd96`: `BSR 2b418`(C 무시). BYTE `15` bit 7 = 0 → 설치 `2c212`(`2bda4`). `2bdaa`: D0 := BYTE `9d`(MOVEQ 뒤). 0 → `2bdd2`. `2bdb4`: D0.B := (D0.B << 4) & `ff`, BYTE `9c` −= D0.B, 빌림 없음 → `2bdd2`. `2bdbe`: BYTE `9d` −= 1, `28ae` 자식 `2db06`(D0.W = `1e`; 자료 값). `2bdd2`: `BRA 2c562`.
- **`2bdd6`**(멈춤): BYTE `82` := BYTE `7e`, 그 값 = 0 → `2baf4`. `2bde0`: BYTE `85` := (LONG `64` < 0이면 `ff`, 아니면 0), A1/A2 := `69f02`/`6a210`, BYTE `7f` ≥ 7이면 `6a51e`/`6a82c`. `2be0a`: D0.B := (BYTE `15` bit 0 ? `ff` : 0), D1.B := BYTE `85` ^ D0.B, 0이 아니면 A1 := A2(`2be1c`). `2be1e`: 애니메이션. `2be28`: LONG `64` := 0, 설치 `2be36`.
- **`2be36`**(미끄러져 멈춤): BYTE `15` bit 7 = 0 → `2c212`. 입력: bit 2 → BYTE `85` ≥ 0(부호)이면 `2bbb6`, 아니면 `2bbdc`. bit 3 → BYTE `85` < 0이면 `2bb7e`, 아니면 `2bba0`. `2be74`: BYTE `7f` ≥ 5 → `2beaa`. 아니면 bit 7 → `2c96a`, bit 1 → `2bfcc`, bit 5 → `2c1ae`, bit 6이면 `BSR 2b532`, C Set → `2bef6`; → `2bece`. `2beaa`: bit 1 = 0 → `2c0fc`, bit 7 → `2c96a`, bit 5 → `2c6cc`, bit 6이면 `BSR 2b608`.
  - `2bece`: BYTE `82` := BYTE `7e`, (새 ^ 옛) bit 7 = 1 → `2baf4`. `2bee0`: `BSR 2c71a`, `BSR 2b418`, C Set → 설치 `2baf4`(`2beec`). `2bef2`: `BRA 2c562`.
- **`2bef6`**(사격 자세 진입): BYTE `7f` := 0, BYTE `82` := BYTE `7e`, BYTE `81` := `ff`, 애니메이션 `6c906`, 설치 `2bf1e`.
- **`2bf1e`**: BYTE `15` bit 7 = 0 → `2c212`. 입력. BYTE `81` ≠ 0 → 입력 속도(`2bf3c`) → `2bf80`. BYTE `81` = 0 → bit 1 → `2bfcc`, bit 3 → `2bba0`, bit 2 → `2bbdc`, 아니면 LONG `64` := 0.
  - `2bf80`: bit 7 → `2c96a`, bit 5 → `2c1ae`, bit 6이면 `BSR 2b532`, C Set → `2bef6`. `2bfa0`: `BSR 2c71a`, `BSR 2b418`, C Set → 설치 `2baf4`. `2bfb2`: BYTE `82` ≠ 0 이고 BYTE `7e` = 0이면 설치 `2baf4`. `BRA 2c562`.
- **`2bfcc`**(웅크림 진입): 소리 `1a5f`(`3af8`), BYTE `82` := BYTE `7e`, 애니메이션 `6556a`, 설치 `2bff2`.
- **`2bff2`**: BYTE `7e` ≠ BYTE `82`이면 BYTE `82` := `7e`, 애니메이션 `6556a`. `2c012`: BYTE `15` bit 7 = 0 → `2c212`. 입력, 입력 속도, LONG `64` := D7. bit 7 → `2c96a`, bit 5 → `2c6cc`, bit 1 = 0 → `2c0fc`, bit 6이면 `BSR 2b608`. `2c06c`: `BSR 2c71a`, `BSR 2b418`, C Set → WORD `92` := 0, 설치 `2c088`. `BRA 2c562`.
- **`2c088`**: 애니메이션 `662c2`, 설치 `2c09e`. `2c09e`: BYTE `15` bit 7 = 0 → `2c212`. 입력: bit 3 → `2bb7e`, bit 2 → `2bbb6`, bit 1 = 0 → `2c0fc`, bit 7 → `2c96a`, bit 5 → `2c6cc`, bit 6이면 `BSR 2b608`. `2c0e8`: LONG `64` := 0, `BSR 2c71a`, `BSR 2b418`(C 무시), `BRA 2c562`.

## 분기 출구 상태 `2c96a..2ca68`(30)

- **`2c96a`**: 소리 `1ac8`. `2c974`: LONG `98` := `2c7a6`(N28 경로 목록), 애니메이션 `68b02`. `2c98c`: `4d4b4`(D0.W = WORD `88`, D1.B = 1). `2c99a`: LONG `64` := 0, 설치 `2c9a8`.
- **`2c9a8`**: A0 := LONG `98`, A0 = 0(32 bit) → `2c9d6`. `2c9b4`: BYTE `14` := BYTE `1a`, D1.W := WORD `(A0)+`, `ffff`면 `2c9c4`: A0 += sext(WORD `(A0)`), D1.W := WORD `(A0)+`. `2c9c8`: LONG `98` := A0, D0.B := BYTE `14`, `JSR 8d34`(B3a).
- **`2c9d6`**: D0 := `c0000`, BYTE `15` bit 0 → `NEG.L D0`(`2c9e6`). `2c9e8`: D0 −= LONG `64`, `ASR.L #5,D0`, LONG `64` += D0, `BSR 2c760`(N28). `2c9f6`: `BSR 2b418`(C 무시). `2c9fa`: WORD `8e` := `8000`, BYTE `61` bit 0 → `2ca56`. `2ca0a`: A0 := `2c8f2`, `JSR 4ae4a`(N08).
- **표**(`2ca14` `2ca1c`, 정적으로 한정): `2ca14 CMPI.W #9,D0; BCC.W 2ca48`. `2ca1c ADD.W D0,D0; ADD.W D0,D0; JMP 2ca24(PC,D0.W)` — `2ca14`를 거치면 D0.W ∈ `0..8`이라 slot 9개 `2ca24..2ca44`(각 `BRA.W`)로만 간다. 표 전사: slot 0 `2ca48`, 1 `2ca56`, 2 `2ca56`, 3~8 `2ca48`. `2ca1c`에 직접 들어가면 원본 그대로 PC = `2ca24` + sext((4·D0.W) & `ffff`)이고 상한 검사는 없다(F1 결정 3; 착지 PC는 dispatcher가 판정, 범위 안 내부 PC면 이 단위 오류).
- **`2ca48`**: A0 := `2b6de`, `JSR 1ab02`(U05). `2ca52`: C Clear → `2ca64 BRA 2c8ca`(N28 공유 꼬리), C Set → `2ca56`: A0 := `2c910`, `JSR 4ae4a`. `2ca60`: `BRA 2ca68`(N28).
- [I] `4ae4a`는 A0 상자 표(`2c8f2` `2c910`)로 충돌 index를 D0에 돌려준다. slot 1·2만 `2ca56`(다른 상자 판정)으로 간다.

## 경계·routing 밖 출구

- [F] routing 밖 실행 PC: 없음. `28ae` 자식 값 `2db06`(약 16 block [I])은 자료다. 자식 실행은 이후 pass다.
- [F] routing된 출구·callee: B3a `2c0fc` `2c1ae` `2c212` `2c562` `2c6cc` `2c71a` `2b532` `2b608` `8d34`, N28 `2b418` `2c760` `2c8ca` `2ca68`, `28ae` `3af8` `49be0` `49f8c` `4ae4a` `4d4b4` `1ab02`. 이 단위에는 `JMP 2a00` 삭제 출구가 없다.

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`). V1 기반 world: seed 116/117 frame 2의 자연 N28 node(B3a spec과 같은 `BASE_CALLBACKS`)에 선언 편집(레지스터, node field, 포인터 field `78` `94` `98` `9e`, PC).
- 포인터 field는 자연 값 또는 실제 기록(`9e` = `2b3d0`, `98` = `2c7a6`/`2c7fa` 등)을 선언한다.
- 사슬(chain) fixture: 소비자 8개를 실제 생산자로 들어간다(`2b532` → `2bb66` `2bd06` `2bea2` `2bf9c`, `2b418` → `2bee8` `2bfa8` `2c074`, `1ab02` → `2ca52`).
- node fixture: 설치 값(`2baf4` `2bb1c` `2bc70` `2be36` `2bf1e` `2bff2` `2c088` `2c09e` `2c9a8`)과 분기 진입(`2bef6` `2bfcc` `2c96a`)을 node callback으로 들어가 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- B3a node·chain fixture는 B3b PC에서 더 이상 멈추지 않고 이 단위를 지나간다(B3a spec은 routing을 파싱하므로 바꾸지 않고 다시 돌려 일치를 확인한다).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(두 범위의 모든 짝수 PC, `engine/tests` `tools/unit_fixture_specs` `tools/*.py`): B3b PC를 쓰는 기존 시험은 B3a 시험·spec의 stop/후속(`2bef6` `2bfcc` `2c96a`, 설치 값 `2baf4`)뿐이다. stop은 routing 판정보다 먼저라 그대로 통과한다. "routing 밖" rollback 기대로 B3b PC를 쓰는 곳은 없다.
- [I] 계산 PC로 B3b 범위에 착지하는 숨은 탐침은 구현 뒤 `make test`와 V1 재실행으로 찾는다(B3a의 B1c `2b5fe` 선례). 찾으면 아래 결정 4대로 옮기고 목록을 이 절에 더한다.
- [I] 자연 경로를 바꾸지 않으므로 D1 구동기(Skip), controller `Execute`(`--declare game`), 실제 IRQ 비교는 54,400/54,400 그대로여야 한다(회귀로 확인).

## B3c 후보(이 계약에서 구현하지 않음)

- [F] scratch `closure.py`(on-demand 정적 closure, routing된 PC에서 멈춤):

| 진입 | block | 명령 | 범위 | routing된 출구 |
| --- | --- | --- | --- | --- |
| `28ae` 자식 `2d7be`(B3a `2b548`) | 20 | 57 | `2d7be..2d8b8` | `2a00` `8ebe` `43e34` `49f8c` `49fc6` |
| `28ae` 자식 `2d916`(B3a `2ba50`) | 14 | 51 | `2d916..2d9dc` | `2a00` `8ebe` `1bf80` `1d198` `43e34` `491c4` `49290` `49f8c` `49fc6` |
| `28ae` 자식 `2db06`(B3b `2bdbe`) | 16 | 49 | `2db06..2dbda` | `288c` `2a00` `8ebe` `43e08` `43e34` `49f8c` `49fc6` |
| callee `1c114`(B3a `2b636`) | 21 | 63 | `1c114..1c1ba` `2291a..2296a` | `289e` `2986` `491b6` `4c2fa` |
| 합계 | **71** | 220 | | 간접 분기 0, 새 자식 0 |

## 결정 (결정 2는 메인이 접기로 해결; 번호는 초안 그대로)

1. **범위.** B3a 계약 메인 결정 1의 B3b 207 block에서 접힌 `2bd58`을 뺀 206 block을 하나로 구현한다(작업자 권고·구현).
2. **`2bd58 BMI`의 N. [해결: 메인, 접기]** 선행이 둘이라 N04 `ab1a6` / N09 `af7b0` / N15 `71c86` 선례대로 BMI를 각 선행에 접는다. 선행마다 자기 N(`2bd48`: MOVE.L의 D0 bit 31, `2bd56`: NEG.L 결과 bit 31)으로 `2bd76`/`2bd5c`를 고른다. 직접 진입 `2bd58`은 내부 PC 오류다. 작업자 초안의 재계산안(`2bd58`을 시작으로 두고 D0 bit 31 사용)은 폐기했다.
3. **carry 보존 목록.** 소비자 8개만 넣는다(B2c·B3a 꼴).
4. **숨은 탐침 이전.** 구현 뒤 기존 시험이 계산 PC로 B3b 범위에 착지하면 B3a 결정 5와 같이 기대 문자열만 이 단위 오류로 바꾸고 실패 PC를 stop으로 확인한다(RAM `10fexx`로 옮길 수 없는 경우). 옮길 수 있으면 RAM 탐침으로 옮긴다.
5. **표 `2ca1c` 직접 진입.** 상한 검사 없이 원본 계산(F1 결정 3)을 따른다.

## 미확인

- [U] BYTE `7e` `7f` `81` `82` `85` `9c` `9d`, BYTE `61` bit 4·5, WORD `8e`의 의미(입력·속도 감쇠·방향 기록으로 추정).
- [U] `4ae4a` 상자 표 `2c8f2` `2c910`과 `1ab02` 자료 `2b6de`의 의미.
- [U] `2db06` 자식과 `2c96a` 상태의 화면상 동작 이름.
- [U] 400 frame 밖·응답 `00`·controller 생략 해제 시의 자연 도달(`2ba3e` 설치 조건 `4d2d4` Set).

## 구현·검증 기록(작업자, 메인 접기 결정 뒤 최종 실행)

- 파일: `engine/src/animation_machine_objects_b3b.cpp`(case label 206 = scratch `starts206.txt`와 집합 일치; `2bd58`은 `2bd48` / `2bd56`에 접힘), `engine/tests/animation_machine_objects_b3b_test.cpp`(단위 시험, 생성 구역 + 수작성 규칙: `2bd58` 직접 진입 오류 × 들어오는 C 3가지, `2bd56` 접힌 BMI 4행), `tools/generate_animation_machine_objects_b3b_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음), `tools/unit_fixture_specs/b3b.py`(V1 spec). 공유 수정은 "공통 규칙"의 다섯 곳뿐이다. 다른 단위의 시험·spec은 고치지 않았다(무효 탐침 없음).
- [F] `make -j3 all test`: 종료 0, 경고 0, Assert 줄 0, Python 310개 통과. B3b 시험 줄: `733 fixtures (558 single-block, 127 path, 14 producer chain, 16 declared C, 18 checked error (4 with a later failing PC), 30 kept C), 206 blocks, 3764 calls, 43277 checks`. 내부 PC 693개(`2bd58` 포함) 정확한 오류.
- [F] UBSan(-O1 -fsanitize=undefined -fno-sanitize-recover): 통과, 같은 B3b 줄.
- [F] 변이 30/30 검출(기존 28개 중 `2bd58-n-inverted`를 접기용 3개로 교체: `2bd48-fold-swap`, `2bd56-fold-swap`, `2bd56-n-before-neg`).
- [F] 실제 ROM 차분(Unicorn 대 C++, 8개 program_rom, 5 batch × 1,500 = 7,500 case): 불일치 0, native 홀수 주소 0, Unknown-C 진입 0, 덮은 시작 s1 205/206(`2bf60` 미추첨) s2 206 s3 205/206(`2c038`) f4 206 f5 206. 의도적 차이 `2986` caller-X: s1 66, s2 48, s3 65, f4 93, f5 73(B3b 경로가 N28 `2ca68`/`2c8ca` 뒤 `2986` 실패에 닿음, buffer_cue 결정 1).
- [F] V1 b3b(두 번 실행, `[(name, digest)]` 같음): 1,360/1,360(match 641, 오류 709, 음성 10), 시작 206/206, 누락 후속 없음, carry oracle ok(Unknown/Clear/Set = 625/8/8). V1 B3a spec 재실행 1,468/1,468(match 550, 오류 908, 음성 10; carry 525/14/11).
- [F] frame 회귀(scratch `frames/`): D1 driver, controller `--declare game`, IRQ 모두 종료 0, frame 54,400/54,400 일치, 자연 seed 136 완료, deterministic / negative_ok true. B3a scratch 보고와 시간·소스 해시 필드만 다르다.
- [U] 400 frame 밖, 응답 `00`, controller 생략 해제 시의 자연 도달은 미확인(위 미확인 절).

## block 목록

[F] scratch `starts.txt`(SHA256 `23d489ae6f5f5955089d51b896637c083ed5273d3080cb49d9245326e023def1`)와 같다.

- **`2baf4..2c0fc`(176, 접기 뒤)**: `2baf4 2bb06 2bb16 2bb1c 2bb26 2bb30 2bb3a 2bb42 2bb4a 2bb52 2bb5a 2bb62 2bb66 2bb6a 2bb76 2bb7a 2bb7e 2bb96 2bb9a 2bba0 2bbb2 2bbb6 2bbd2 2bbd6 2bbdc 2bbf2 2bbf6 2bc06 2bc10 2bc20 2bc2a 2bc3a 2bc44 2bc54 2bc5a 2bc64 2bc70 2bc7a 2bc84 2bc8e 2bc94 2bc9c 2bca6 2bcac 2bcb4 2bcbc 2bcc0 2bcc8 2bcd0 2bcd4 2bcd8 2bce2 2bcea 2bcf2 2bcfa 2bd02 2bd06 2bd0a 2bd0e 2bd16 2bd1e 2bd26 2bd2e 2bd32 2bd36 2bd48 2bd56 2bd5c 2bd6c 2bd72 2bd76 2bd86 2bd8c 2bd96 2bd9a 2bda4 2bdaa 2bdb4 2bdbe 2bdd2 2bdd6 2bde0 2bdfe 2be0a 2be1c 2be1e 2be28 2be36 2be40 2be4a 2be54 2be5c 2be60 2be68 2be70 2be74 2be7e 2be86 2be8e 2be96 2be9e 2bea2 2bea6 2beaa 2beb2 2beba 2bec2 2beca 2bece 2bee0 2bee4 2bee8 2beec 2bef2 2bef6 2bf18 2bf1e 2bf28 2bf32 2bf3c 2bf4c 2bf4e 2bf56 2bf58 2bf60 2bf68 2bf70 2bf78 2bf80 2bf88 2bf90 2bf98 2bf9c 2bfa0 2bfa4 2bfa8 2bfac 2bfb2 2bfba 2bfc2 2bfc8 2bfcc 2bfd6 2bfec 2bff2 2bffe 2c012 2c01c 2c026 2c038 2c03a 2c042 2c044 2c050 2c058 2c060 2c068 2c06c 2c070 2c074 2c078 2c084 2c088 2c098 2c09e 2c0a8 2c0b2 2c0bc 2c0c4 2c0cc 2c0d4 2c0dc 2c0e4 2c0e8 2c0f0 2c0f4 2c0f8`
- **`2c96a..2ca68`(30)**: `2c96a 2c974 2c98c 2c99a 2c9a8 2c9b4 2c9c4 2c9c8 2c9d6 2c9e6 2c9e8 2c9f6 2c9fa 2ca0a 2ca14 2ca1c 2ca24 2ca28 2ca2c 2ca30 2ca34 2ca38 2ca3c 2ca40 2ca44 2ca48 2ca52 2ca56 2ca60 2ca64`
