# 객체 callback F4 N34: 경사 이동 함수 `4c3de`(본문 `4c810`)와 helper `4c410` `4c44c` `4c4bc` `4c660` `4c6a4` `4c72a`, leaf `4c408` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N34 행(213 block, 누적 5,352, 범위 `4c3de..4c6f0` `4c810..4cf52`, 진입 표기 없음, 경계 `4c6f0` `4c72a`, bank 0, 미실행 설치 0, 옛 U39 143 + U46 62)과 N33 계약(`animation-machine-objects-n33-contract.md`, SHA256 `9b15f2e9a117e2aedc1789dfb8cddd6fc2b60158864a4cc27c946fde28b8318c`; `46bfc`는 N34만 부르고 `4b8e8` `4bfc8`은 공유 callee)이다. 단위 형식과 규약은 N33·N32a/b·N31 계약을 따른다. 메인 작업 지시:
- 진입(호출자·설치자)은 직접 찾는다. block 시작은 `MOVE.L #imm,(A6)` 설치 callback, DBRA 대상, JSR 복귀점을 포함한 정적 디코드로 정하고 자료는 routing하지 않는다. 표는 전부 옮긴다. 다른 단위 범위 안은 routing하지 않는다(`engine/src/animation_machine.cpp` 확인).
- closure가 약 230 block보다 훨씬 크면 a/b 분할을 제안하고 a만 구현한다.
- seed 116 117은 기준(`e7c6972`)에서 frame 0 node 7 N35 `4cf52`에서 멈춘다. N34가 그 경로에 있는지와 다음 멈춤 위치를 보고한다.
- N35(`4c6f0..4c72a` `4cf52..4cf64` `4d8d8..4d900` `4da4a..4da74` `ea680..ea69c`)와 u08b 두 번째 진입 `4bc58`은 병렬 작업자 몫이다. routing·수정하지 않고 stop만 쓴다.
- 탐침 이동·두 번째 진입 patch는 scratch patch 파일과 결정으로 보고한다.
- 메인 결정(작업 중 전달): 소유 단위 없는 `4c72a..4c7a4`가 N34(`4ca9c` `4ccf0 BSR`)에서만 불리면 N34에 넣는다. 정적 디코드로 확인해 넣었다(결정 4).

- 결정 관례(N31~N33과 같음): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, 범위 밖에서 참조하는 범위 안 진입(설치 값·`28ae` 자식 값·BRA/JMP/JSR 대상))로 정한다. Unicorn TB 분할은 시작이 아니다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다. flag를 함께 읽는 연속 Bcc는 한 block으로 묶는다.
- U01~N33 수용 관례: `MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDQ`/`ADDI`/`SUB`/`SUBI`/`AND`/`ANDI`/`OR`/`ORI`/`EOR`/`NOT`/`NEG`/`SWAP`/`ASR`/`LSL`/`LSR`/`MULS`/`Scc` 없는 산술 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`BSET`/`BCLR`/`Scc`)만인 block은 FLOW_ONLY다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N34 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기는 없다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n34`(HEAD `e7c6972` = N01~N33, F5 H1, H3, 외부 읽기 queue 통합, `engine/src/animation_machine.cpp` SHA256 `6043293e064d770ef7538371620c6e77765718476f00917a8f538683a4fddfcd`, routing 규칙 93개, `engine/src/animation_machine_objects_u08b.cpp` SHA256 `2eaa138c170340b55b81f0b1e9635b011a9ebe1d28a15d158e44edcecd8f1afc`, `..._u08.cpp` `98066f720e8ce780ea1c249b662a6c92c055ae5a21374143b3154e94525ccb94`, `..._u09.cpp` `c88e29ea1570db5b794697c14a56e6fefe71d94e35372e465cda15c875652ba8`, `..._n33.cpp` `5f3763afa464e2ceda82e986c01e4c29a425592abf4957530ea05fafd6f28dd1`)을 참조했다. N34 세 범위의 짝수 PC는 모두 기존 routing에 없다(scratch `n34.py`가 PC마다 확인). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n34/n34.py`(정적 디코드)와 `cls34.py`(분류)가 원본 opcode에서 독립 계산했다(`starts.txt` SHA256 `7683553f2e213fa93d62ccea13299963b8eb9b7191e0ea5619b2e79244a74472`).

## 요약

- [F] **N34 = 220 block**(3 routing 범위, 코드 2,766바이트, 733 명령 중 729 도달, 짝수 PC 1,383, 내부 1,163). 진입 2개(`4c3de` `4c408`)에서 분기·fall-through·JSR/BSR 복귀점을 끝까지 따라간 정적 closure다. 230 미만이라 나누지 않는다. `4c3f6..4c408`(4 명령, 18바이트)은 어디에서도 참조하지 않는 죽은 진입 조각이라 내부 PC다(결정 2). 범위 안 설치 callback·`28ae` 자식·DBRA·TRAP·계산 점프·레지스터 간접 제어 이동이 없다.
- [F] 진입(범위 밖에서 들어옴):
  - `4c3de`(N28 `2c76e JSR`; `2c760`에서 A0 = LONG `94(A6)`, BYTE `15` bit 7이 1일 때): LONG `5c8e(A5)` ← A0(이하 기록 R), `JSR 4bc44`(u08b), BYTE `549f(A5)` = `5cb4(A5)` = `ff`, `BRA.W 4c810`(본문). 본문의 RTS가 N28 `2c774`(`MOVE.W D0,8c(A6)`)로 돌아간다.
  - `4c408`(범위 밖 `2c24a JSR`; `2c246 MOVEA.L 94(A6),A0` 뒤, routing 밖 고아 함수 영역): `78.W(A0)` = `80`, RTS.
- [F] 본문 `4c810`(R = LONG `5c8e(A5)`, A6 = 노드):
  1. BYTE `549d` = 0, `D0`~`D3`/A0 ← LONG `2e`/`32`/`36`/`3a`/`3e(A6)`, A1 = A5+`538e`, `JSR 43eb8`(U08), `2e`~`3e(A6)` ← `D0`~`D3`/A1. A0 = R. BYTE `9b(R)` ≠ 0이면 `98.W(R)` ← `54a4.W(A5)`.
  2. `BSR 4c44c`·`4c4bc`·`4c660`, BYTE `9b(R)` = `ff`, `9c(R)` = 0, A0 = R, `BSR 4c6a4`.
  3. LONG `5c92` `5c96` `5c9c` `5ca0`·WORD `5c9a` = 0, WORD `54a2`를 스택에 넣고 `ffff`로, `7a.W(R)` = `7c.W(R)` = 0, LONG `5cb6` = `ffffffff`, WORD `54a4` = `00ff`.
  4. 첫 번째 축(`8e`/`92`, 결과 `7a`/`80`): 노드 `2e`/`32` → R `8e`/`92` 차를 `D2`/`D3`로 `JSR 469d8`(U09, A0 = A5+`538e`), `JSR 46bfc`(N33), 좌표계 보정(`4c8b2` 꼴: A2 ← A1, A1 ← A0, A0 = A5+`538e`, `D0`/`D1` += `14`/`18(A1)` − `14`/`18(A0)`, A0 = R). `D6` bit 1이면 `7a.W` |= `4000`·LONG `5cb6` = A2, bit 10이면 BYTE `9b` = 0. 역방향(`8e` → `2e`) 한 번 더(`D6` &= 2, bit 1이면 `7a.W` |= `8000`·`5cb6` = A2). BYTE `76` = `e0`이고 `7e`|`7c` bit 0 = 0이고 (`5cb4` = 0 또는 LONG `64` ≥ 0)이면 중점 경로(`9c` = `ff`, `D2`/`D3` = `2e`/`32`와 `8e`/`92`의 산술 평균), 아니면 `D2`/`D3` = `2e`/`32` − `5cac`/`5cb0`(BYTE `9a` ≥ 0이면 `5ca4`/`5ca8`(9a > 0이면 2배)를 더 뺌) + `36`/`3a(A6)`. 목표를 스택에 넣고 `JSR 469d8`·`46bfc`·보정, `D6` bit 0이면 `5cb6` = A1, `8e`/`92` ← `D0`/`D1`(bit 4·`5cb4`·`99` 모두 0 아니면 노드 `2e`/`32`), `D7.W` −= `4000` → `80.W(R)`, `7a.W` |= `D6.W`, 목표를 꺼내 `D0`/`D1` −= 목표, `BSR 4c6f0`(N35). `D0`|`D1` ≠ 0, `7a` bit 2 = 0, `9a` ≥ 0이면 `D0`/`D1` = `5cac`/`5cb0` − (`D2`/`D3` − `2e`/`32`), `BSR 4c72a`(helper), `5c9c`/`5ca0` += `D2`/`D3`.
  5. 두 번째 축(`86`/`8a`, 결과 `7c`/`82`): 4와 대칭(부호 반대: `5cac`/`5cb0`·`5ca4`/`5ca8`를 더함, `9a` ≤ 0 조건, 중점 조건 `76` = `20`·`64` ≤ 0, `5cb6` 갱신 조건에 `TST.W`/`TST.L 5cb6`·`76.W` 부호 검사 추가). 끝은 `5c9c`/`5ca0` −= `D2`/`D3`.
  6. WORD `54a2` 복원. `5cb4` ≠ 0이고 LONG `64` = 0이면 |`5c92`|+|`5c96`| < `10000`(무부호)일 때 둘을 0, `5c9a.W` + `100`이 `200` 이하(무부호 WORD)이면 `5c9c`/`5ca0`을 0.
  7. `D0`~`D3` ← `2e`~`3a(A6)`, `D2`/`D3` += `5c92`+`5c9c`/`5c96`+`5ca0`, BYTE `78(R)` 양수면 `5ca4`/`5ca8`를 빼고 음수면 더함, `D3` −= `96.W(R)` << 16, A0 = `10d38e`, BYTE `549f` ≠ 0이면 `JSR 4b8e8`(N33), 아니면 `JSR 4bb22`(u08b).
  8. `D0`~`D3` 저장, `JSR 469d8`(A0 = A5+`538e`), A0 = R, `D6` &= `10`(`AND.W D5,D6`), `D6` ≠ 0이고 BYTE `99` ≠ 0이면 BYTE `549d` = `ff`, `D6` bit 0이면 `84.W` = `D7.W`(결정 3: 이 지점에서 `D6`은 0 또는 `10`이라 실제로는 건너뜀), `D0`~`D3` 복원, `D6.W`를 스택에 넣고 `JSR 469d8`, A1 = 결과 A0, A0 = R, `D6` bit 0이면 `84.W` = `D7.W`, `D6.W` |= 꺼낸 WORD → `7e.W(R)`, BYTE `84` −= `40`.
  9. `5cb4` ≠ 0이고 `D6` bit 2이면 LONG `64` ≥ 0 → `7c.W` |= `8000`, ≤ 0 → `7a.W` |= `8000`. `D6.W` = (`D6` & `fffb`) | `7a` | `7c`. `5cb4` ≠ 0이고 `64` ≠ 0이면 양수는 BYTE `76` ≠ `20`, 음수는 `76` ≠ `e0`일 때 bit 2를 지운다. BYTE `9c` = 0이고 `D6` & `c000` ≠ 0이면 `D6` |= 1.
  10. `7e` bit 0 = 0이고 LONG `5cb6` ≠ `ffffffff`(`CMPA.W #ffff`)이면 `D0`/`D1` += `14`/`18(A1)` − `14`/`18(A2)`, A1 = A2(= `5cb6`). `D2` = `36(A6)` + `14`−`1c`(A5+`538e`) − `14`+`1c`(A1), `D3` = `3a(A6)` + `18`−`20`(A5+`538e`) − `18`+`20`(A1), `2e`~`3e(A6)` ← `D0`~`D3`/A1.
  11. `96.W(R)`: `5cb4` = 0 또는 `D6` bit 0이면 0, 아니면 BYTE `9c` = 0이고 `96` < 4(무부호)일 때 +1·`D6` |= 1.
  12. `BSR 4bf16`(u08b), A0 = R, `78.W` += `5c9a.W`, `BSR 4c660`, BYTE `76` += BYTE `78`, `D0.W` = `76.W`, RTS.
- [F] helper:
  - `4c410`(`D0`/`D1` → `D7`): `D0` &= `c005`가 0이면 `D7` = 2. 아니면 `D7` = (`D1` bit 0) + (`D0` bit 0)이고, `D0` bit 0이 0일 때만 `(D0 & c000 ≠ 0) xor (D1 bit 0)`을 더한다(`SNE`·`EOR.B`).
  - `4c44c`: `7a`/`7e` → `D7` → `D6`, `7c`/`7e` → `D7`. BYTE 비교(`CMP.B D6,D7`): 같으면 그대로, `D7−D6` 음수면 `78.W` += `a0`, 양수면 `78.W` −= `a0`. `7e` bit 0이면 `D0.W` = `84.W` − `76.W`; 0이면 `78.W` = 0, 양수면 `78.W` = min(`78.W`, `D0`), 음수면 max(부호 WORD 비교).
  - `4c4bc`: BYTE `9a` ← BYTE `78`. `5cb4` = 0이면 RTS. `D2` = `D3` = BYTE `76`(0 확장). LONG `64` ≠ 0이면 음수는 `D0` = `7a.W`, 양수는 `D0` = `7c.W`로 `D0` & `8005` = 1이면 `D2.B` = BYTE `80`·`9a` = `ff`(음수) 또는 `82`·`1`(양수), 아니면 `D0` bit 15 = 0이고 반대쪽(`7c`/`7a`) bit 0이면 `82`·`1`(음수) 또는 `80`·`ff`(양수); `D0` bit 14면 `D3.W` = `D2.W`, (`D0`|`7e`) bit 2면 음수는 `D3.B` = `e0`·`9a` = 1(`MOVE.B`), 양수는 `D3.W` = `20`·`9a` = `ff`(`MOVE.W`); `7e` & `11` = `11`이고 BYTE `99` ≠ 0이면 `9a` = 0·`D2` = `D3` = BYTE `84`·노드 `2e`/`32`를 `8e`/`92`(음수) 또는 `86`/`8a`(양수)에 복사. `4c60e`: `D2.W` *= 2, `D0` = `D1` = LONG `64` 산술 >> 8, `D0` = `MULS.W 4419e[D2]`, `D1` = `MULS.W 4411e[D2]` → LONG `36`/`3a(A6)`. `D3.B` −= BYTE `76`이 0이 아니면 `D3.W` <<= 8, `D0.W` = `64.W`(음수 아니면 `NOT.W`), `D0.W` += 9에서 WORD 자리올림이 있으면 `D3.W` = `ASR.W` (`D0` mod 64), `D3.W`가 음수가 아니면 +1, `78.W` += `D3.W`.
  - `4c660`: BYTE `78`이 0이면 RTS. 양수: `76`+`78`−`20`(BYTE)이 부호 비교로 `20` 초과이면 `78` −= 초과분·BYTE `79` = `80`. 음수: `76`+`78`이 `e0`(−32) 미만이면 같은 보정.
  - `4c72a`(`4ca9c` `4ccf0 BSR`): `D0`/`D1`을 각각 `LSL.L #2`(결과 음수면 `ADDI.L #ffff`), `SWAP` 두 번, `JSR 44602`(경계). 복귀 `4c74c`: A0 = R, `D0.B` −= BYTE `76`, `D0.W` = (`D0.W` << 8) − `80` + BYTE `79`, WORD `5c9a(A5)` −= `D0.W`, `D1` = (`78.W` − `D0.W`) >> 8(무부호), `D0` = BYTE `76`, `D1.B` += `D0.B`, `D0.B` += BYTE `78`, 둘 다 ×2(WORD), `D2.W` = `4419e[D1]` − `4419e[D0]`, `D3.W` = `4411e[D1]` − `4411e[D0]`, `MULS.W #1800`, RTS.
  - `4c6a4`: `D0`~`D3.W` = `1800`, `D7` = BYTE `76` × 2, `D0` = `MULS 4419e[D7]`, `D1` = `MULS 4411e[D7]` → LONG `5cac`/`5cb0`, `D7.W` = (`D7.W` >> 1) + BYTE `78`(BYTE 덧셈) × 2, `D2` = `MULS 4419e[D7]` − `D0`, `D3` = `MULS 4411e[D7]` − `D1` → LONG `5ca4`/`5ca8`, RTS.
- [F] **고정 ROM 자료 읽기**: WORD 표 `4419e`와 `4411e`(`MULS.W (A1,Dn.W)`/`(A2,Dn.W)` 6곳 `4c624` `4c628` `4c6c2` `4c6c6` `4c6da` `4c6de`, `MOVE.W`/`SUB.W (A1,Dn.W)`/`(A2,Dn.W)` 4곳 `4c78a` `4c78e` `4c792` `4c796`). 색인은 항상 `0..1fe`(BYTE를 0 확장한 뒤 ×2, `4c6d4` `4c780` `4c782`는 `ADD.B`라 다시 BYTE, `4c778 LSR.W #8`의 상위 WORD는 `MOVEQ #0`)라 읽는 범위는 `4411e..4431e`와 `4419e..4439e`, 즉 `4411e..4439e`(U17·U02와 같은 표) 안이다. live bus(`am_read`)로 읽는다.
- [F] **다른 실행부로 가는 callee**: `4bc44` `4bb22` `4bf16`(u08b), `43eb8`(U08), `469d8`(U09), `46bfc` `4b8e8`(N33), `4c6f0`(`4ca68` `4ccb8 BSR`; N35 범위 — 기준 `e7c6972`에는 실행부가 없어 경계 stop). **경계(실행부 없음)**: `44602`(`4c746 JSR`; N19·N25와 같은 경계). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **carry**: 소비 0, known 생산 0, FLOW_ONLY 27, Unknown 193(27 + 193 = 220). N 재계산 1(`4c49c`, 아래 "carry").
- [F] X·DIVx·TRAP·I/O port 쓰기·bank 읽기/변경이 없다. `MULS.W` 8개(표 6 + `#1800` 2, 16 × 16 부호 곱, 32 bit 결과). 가변 이동 `ASR.W D0,D3`(`4c650`) 1개(개수 = `D0` mod 64, 16 이상이면 부호 bit로 채움). 스택: JSR/BSR 복귀 LONG, WORD push/pop `4c85a`/`4ccfc`(`54a2`)·`4cde6`/`4ce0a`(`D6`), LONG push/pop `4c9d0`/`4ca54`·`4cc10`/`4cca4`(목표 `D2` `D3`), `MOVEM.L D0-D3,-(A7)`/`(A7)+`(`4cdae`/`4cde6`).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준): seed 116 117만 N34 PC를 실행한다. 첫 실행은 frame 1 node 7(callback `2b96c`(N28), `2c76e JSR 4c3de`)이다. 실행 TB(모두 N34 block 시작, 220 중 92): `4c3de` `4c3e6`, `4c410..4c44c`(5), `4c44c..4c4bc`(7), `4c4bc` `4c4ca` `4c60e` `4c65e`, `4c660` `4c6a2` `4c6a4`, 본문 `4c810..4cf52`(71). `4c4da..4c5f6`(LONG `64` ≠ 0 경로), `4c408`, `4c66c..4c696`, `4caa0`/`4ccf4` 뒤(`4c72a` 경로) 등은 자연 400 frame에서 실행되지 않는다. `4c6f0`(N35)은 자연 실행되고 `4c72a..4c7a4`·`44602`는 되지 않는다.
- [F] 기준(`e7c6972`)에서 seed 116 117은 frame 0 node 7(callback `4cf52`, N35)에서 멈춘다. N34는 그 뒤 frame 1 node 7부터의 경로에 있다(아래 "작업자 검증 기록").

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 앞 `4c390..4c3de`(소유자 없음)를 넣지 않는다.** [F] `4c390`(범위 밖 `2c1f2` `2c2c2` `2c516` `2c754 JSR`), `4c3a2`(N28 `2c79a JSR`), `4c3ba`(참조 없음), `4c3cc`(범위 밖 `2c728 JSR`)는 `4c3de`와 같은 꼴의 진입 조각(`MOVE.L A0,5c8e(A5)`, `JSR 4bce0`(N33) 또는 `JSR 4bc44`(u08b), BYTE `549f`·`5cb4` 설정, `BRA.W 4c810`)이다. N34 호출 그래프 밖(N34 쪽에서 부르지 않음)이고 재범위 N34 행에 없으며 seed 116 117이 자연 400 frame에서 실행하지 않는다(N28 결정 2: `4c3a2`는 자연 미실행). 규칙대로 routing하지 않는다. [I] 권고: N35 뒤 정리 단위(고아 `2bb..2c760` 함수들과 함께)에서 4 조각(각 2 block)을 N34 본문 진입으로 넣는다. 바이트 `4c390..4c3de` SHA256 `097bca7cb60fc8a49c2bf33bdd89b5d07d0ede8d7d41bc97955d916c47283db8`.
2. **죽은 조각 `4c3f6..4c408`.** [F] `4c3f6 MOVE.L A0,5c8e(A5); JSR 4bc44(PC); MOVE.B #ff,5cb4(A5); BRA.W 4c810`을 참조하는 분기·JSR·LONG이 fixed ROM 전체에 없다(scratch `xref34.py`). 재범위 범위(`4c3de..4c6f0`) 안이라 routing 범위에는 두되 block 시작이 아니므로 내부 PC(`unsupported animation objects n34 PC`)다(N33 `3b2d8`과 같은 처리). [U] 계산 점프·RAM 설치로 들어오는지는 정적으로 확인하지 못했다(자연 400 frame에서는 실행되지 않음).
3. **`4cde2`(정적으로만 도달).** [F] `4cdc4 AND.W D5,D6`(`D5` = `10`)이 `D6`을 0 또는 `10`으로 만들므로 `4cdd8 MOVE.W #1,D5; AND.W D6,D5; BEQ.W 4cde6`은 늘 분기하고 `4cde2 MOVE.W D7,84(A0)`는 실행될 수 없다. 원본 그대로 block으로 두고(분기 대상 fall-through) 구현한다. 고정 fixture는 `4cde2`에서 직접 시작한다.
4. **`4c72a..4c7a4`를 N34에 넣음(메인 결정 반영).** [F] `4c72a..4c7a4`(122바이트, SHA256 `958079955eb7a88de812985d8f45d14e89941c3c674304962e3d6a020c0b1bc0`)는 재범위 N34 행이 경계로 두고 N35 행에도 없다. fixed ROM 전체의 분기·JSR·LONG 참조는 N34 `4ca9c` `4ccf0 BSR`뿐이다(`4c741` 홀수, `4c74c`의 LONG `4ab84`는 `EXG` opcode 우연 일치). 6 block(`4c72a` `4c730` `4c736` `4c73c` `4c742` `4c74c`)을 helper로 넣었다. 새 경계는 `44602`(routing 밖)다. 자연 400 frame에서는 실행되지 않는다(`4ca88`/`4ccdc` TB 없음).
5. **재범위 수치와 다른 점(213 → 220).** [F] 재범위 N34 행은 진입을 적지 않았다. 이 계약은 범위 밖 `2c24a`가 부르는 `4c408`을 진입으로 더하고 JSR/BSR 복귀점을 모두 시작으로 나누며, 결정 4의 `4c72a..4c7a4` 6 block을 더한다(214 + 6). [U] 재범위 leader 집합(`rescope/build.pkl`)과의 집합 비교는 하지 않았다(N32·N33 결정 2와 같은 차이로 추정).
6. **N33 결정 목록 중 N34 관련.** [F] N33 결정 3: `46bfc`는 N34(`4c8ac` `4c90e` `4c9f8` `4cacc` `4cb3e` `4cc38`)만 부른다 — N34는 stop/호출만 한다. `4b8e8`은 N34 `4cd9e`가 부른다(N33 실행부). N33 결정 5(`4bc58`)는 N34와 무관하다(N34는 `4bc44` 블록 시작으로만 들어간다). N33 탐침 이동(결정 4)이 바꾼 test에는 N34 PC가 없다.
7. **기존 test의 N34 PC(탐침 이동 필요 없음).** [F] 기존 test·실행부에서 N34 범위 PC는 N28 `2c76e`의 경계 stop `4c3de`(`animation_machine_objects_n28_test.cpp`의 stop 기대)뿐이고 rollback 탐침·"routing 밖" 탐침으로 쓰는 곳이 없다(아래 검증 기록의 `grep`). N28 test는 `4c3de`에서 멈추는 stop만 쓰므로 그대로 통과한다. 탐침 patch는 만들지 않는다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n34.cpp`의 `animation_objects_n34_block`. 오류는 `unsupported animation objects n34 PC`(내부 PC). 소비자가 없으므로 carry 오류 문자열은 두지 않는다.
9. **`2986` caller-X 제한 해당 없음.** [F] N34는 `2986`을 부르지 않는다.

## 원본 바이트 근거

[F] N34 코드 3 범위 합계 2,766바이트(짝수 PC 1,383개, 시작 220, 내부 1,163). 범위 순서로 이어 붙인 SHA256 `956e5334c80e88431664d43320ca4442b340d25b5d80f9b22aaa910d4df82178`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `4c3de..4c6f0` | 786 | `3db2d6dda4d7b98b2cb616a7713ebd7425fad045df815f33ce90f492a639fd64` | 73 |
| `4c72a..4c7a4` | 122 | `958079955eb7a88de812985d8f45d14e89941c3c674304962e3d6a020c0b1bc0` | 6 |
| `4c810..4cf52` | 1858 | `de6349c79d8eb18013a3fc8d5bb0d3459d95017f1572c0e26ce8a233195dec07` | 141 |

- [F] 범위 이웃: `4c3dc`(routing 밖, 결정 1의 `4c3cc` 조각 끝) / `4c6f0`(N35 범위); `4c728`(N35 범위) / `4c7a4`(N33); `4c80e`(N33 `4c7a4..4c810`의 RTS) / `4cf52`(N35 범위).
- [F] 우연 일치(실행 진입 아님; scratch `xref34.py`): `4c540`(LONG `46f6a` `47180`; U09 `46f6c`/`47182 EXG`의 opcode `c540`), `4c74c`(LONG `4ab84`; `EXG` opcode — 결정 4의 block 시작이지만 이 LONG은 참조가 아님), `4cccc`(LONG 7곳: `77a8a` `78e0e` `b7426`의 `MOVE.L #4cccc,…` 즉시값과 `2f938` `2f970` `d56aa` `d56e2` 자료 — 고정소수 속도 값), `4ce40`(LONG `49bbc`, 자료), 홀수 `4c5c5` `4c741` `4c945` `4cd91` `4cdc5`.
- [F] 범위 안 자료는 없다. 읽는 고정 ROM 표 `4411e..4439e`(640바이트, SHA256 `398e75bfcd95d3a2b4dc255a0f93006fbc9368eb5869caaf578c8e649a6fdf83`)는 N34 범위 밖이고 routing하지 않는다(U02·U17이 이미 같은 표를 live bus로 읽음).

## carry

- [F] **FLOW_ONLY 27**(진입 C를 그대로 둔다; `carry_preserving_pc` 목록에 넣음): `BSR`/`JSR`/`BRA`/`RTS`/`LEA`/`MOVEM`/`BTST`/Bcc만인 block — `4c44a` `4c488` `4c49c` `4c4ac` `4c4ba` `4c576` `4c65e` `4c686` `4c6a2` `4c83c` `4c840` `4c844` `4c8ac` `4c90e` `4c9ee` `4c9f8` `4cacc` `4cb3e` `4cc2e` `4cc38` `4cd9e` `4cda4` `4cda8` `4cdae` `4ce1e` `4ce70` `4cf30`.
- [F] **소비 0**: callee가 돌려준 C를 읽는 block이 없다. 모든 `BCC`/`BCS`/`BHI`(`4c648` `4cd24` `4cd38` `4cf1e`)는 같은 block 안의 `ADDI`/`CMPI`가 만든 C를 읽는다. 진입 C를 읽는 block도 없다.
- [F] **N 재계산 1**: `4c49c BMI.W 4c4ae`는 block 첫 명령으로 `4c48e SUB.W 76(A0),D0`의 N을 읽는다. 선행자는 `4c492 BNE.W 4c49c` 하나다(`4c496` block은 RTS로 끝나 fall-through가 없음). 결과가 `D0.W`에 있으므로 N = `D0` bit 15로 정확히 다시 계산한다. block은 C를 바꾸지 않아 FLOW_ONLY다.
- [F] **known 생산 0**: 마지막 `4cf44 MOVE.W 76(A0),D0; RTS`는 C = 0을 남기지만 소비자가 없다(N28 `2c774 MOVE.W`가 덮음). Unknown으로 둔다.
- [F] **Unknown 187**: 나머지.
- [F] 부호 비교(V 포함): `BGE`/`BLE` after `CMP.W 78(A0),D0`(`4c4a0` `4c4ae`)은 부호 WORD 비교, `BLE` after `SUBI.B #20`(`4c66c`)·`BGE` after `SUBI.B #e0`(`4c688`)은 부호 BYTE 비교(`d1 ≤ 20`, `d1 ≥ −20`), `BLT`/`BGE`/`BGT`/`BLE` after `TST`/`MOVE`(V = 0)는 N·Z만 본다. `BHI` after `CMPI.W #200`과 `BCC` after `CMPI.L #10000`/`CMPI.W #4`는 무부호, `BCC` after `ADDI.W #9,D0`(`4c648`)은 WORD 덧셈 자리올림이다.

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "N 재계산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)과 `(An,Dn.W)` 색인은 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. `MOVEQ`는 LONG 전체를 쓴다. `CMP`/`TST`와 그 Bcc는 같은 block 안에 있다. `BTST #n,Dn`은 bit n mod 32. `CMPA.W #ffff,A2`는 부호 확장 `ffffffff`와 LONG 비교. `MOVEM.L D0-D3,-(A7)`은 D0이 가장 낮은 주소, `MOVEM.L (A7)+`는 D0부터 읽는다. `MOVEM.L 2e(A6),D0-D3/A0`·`MOVEM.L D0-D3/A1,2e(A6)`은 레지스터 순서로 오름차순 주소다. `MULS.W`는 대상 레지스터 하위 WORD와 원본 WORD를 부호 16 bit로 곱해 32 bit 전체를 쓴다. `BPL` after `LSL.L #2`(`4c72a` `4c736`)는 같은 block 안의 결과 bit 31을 본다.

**진입 `4c3de`(N28 `2c76e JSR`) 2**
- `4c3de`: `MOVE.L a0, 5c8e(a5); JSR 4bc44(pc)`
- `4c3e6`: `MOVE.B #ff, 549f(a5); MOVE.B #ff, 5cb4(a5); BRA.W 4c810`

**leaf `4c408`(범위 밖 `2c24a JSR`) 1**
- `4c408`: `MOVE.W #80, 78(a0); RTS `

**helper `4c410`(`4c44c` `4c456` `BSR.B`): 경사 방향 판정 D7 9**
- `4c410`: `ANDI.W #c005, d0; BNE.W 4c41c` (→`4c418`)
- `4c418`: `MOVEQ #2, d7; RTS `
- `4c41c`: `MOVEQ #0, d7; ANDI.W #1, d1; BEQ.W 4c428` (→`4c426`)
- `4c426`: `ADDQ.W #1, d7` (→`4c428`)
- `4c428`: `MOVE.W #1, d2; AND.W d0, d2; BEQ.W 4c436` (→`4c432`)
- `4c432`: `ADDQ.W #1, d7; RTS `
- `4c436`: `ANDI.W #c000, d0; SNE.B d2; ANDI.W #1, d1; SNE.B d3; EOR.B d2, d3; BEQ.W 4c44a` (→`4c448`)
- `4c448`: `ADDQ.W #1, d7` (→`4c44a`)
- `4c44a`: `RTS ` — FLOW

**helper `4c44c`(`4c83c BSR`): `78.W` 기울기 보정 16**
- `4c44c`: `MOVE.W 7a(a0), d0; MOVE.W 7e(a0), d1; BSR.B 4c410`
- `4c456`: `MOVE.W d7, d6; MOVE.W 7c(a0), d0; MOVE.W 7e(a0), d1; BSR.B 4c410`
- `4c462`: `CMP.B d6, d7; BEQ.W 4c47c; BMI.W 4c476` (→`4c46c`)
- `4c46c`: `SUBI.W #a0, 78(a0); BRA.W 4c47c`
- `4c476`: `ADDI.W #a0, 78(a0)` (→`4c47c`)
- `4c47c`: `MOVE.W 7e(a0), d5; ANDI.W #1, d5; BNE.W 4c48a` (→`4c488`)
- `4c488`: `RTS ` — FLOW
- `4c48a`: `MOVE.W 84(a0), d0; SUB.W 76(a0), d0; BNE.W 4c49c` (→`4c496`)
- `4c496`: `MOVE.W d0, 78(a0); RTS `
- `4c49c`: `BMI.W 4c4ae` (→`4c4a0`) — N 재계산, FLOW
- `4c4a0`: `CMP.W 78(a0), d0; BGE.W 4c4ac` (→`4c4a8`)
- `4c4a8`: `MOVE.W d0, 78(a0)` (→`4c4ac`)
- `4c4ac`: `RTS ` — FLOW
- `4c4ae`: `CMP.W 78(a0), d0; BLE.W 4c4ba` (→`4c4b6`)
- `4c4b6`: `MOVE.W d0, 78(a0)` (→`4c4ba`)
- `4c4ba`: `RTS ` — FLOW

**helper `4c4bc`(`4c840 BSR`): 속도 분해 `36`/`3a`와 `78.W` 회전 37**
- `4c4bc`: `MOVE.B 78(a0), 9a(a0); TST.B 5cb4(a5); BEQ.W 4c65e` (→`4c4ca`)
- `4c4ca`: `MOVEQ #0, d2; MOVE.B 76(a0), d2; MOVE.W d2, d3; TST.L 64(a6); BEQ.W 4c60e` (→`4c4da`)
- `4c4da`: `TST.L 64(a6); BPL.W 4c57a` (→`4c4e2`)
- `4c4e2`: `MOVE.W 7a(a0), d0; MOVE.W #8005, d1; AND.W d0, d1; CMPI.W #1, d1; BNE.W 4c502` (→`4c4f4`)
- `4c4f4`: `MOVE.B 80(a0), d2; MOVE.B #ff, 9a(a0); BRA.W 4c522`
- `4c502`: `MOVE.W #8000, d1; AND.W d0, d1; BNE.W 4c522` (→`4c50c`)
- `4c50c`: `MOVE.W #1, d1; AND.W 7c(a0), d1; BEQ.W 4c522` (→`4c518`)
- `4c518`: `MOVE.B 82(a0), d2; MOVE.B #1, 9a(a0)` (→`4c522`)
- `4c522`: `MOVE.W #4000, d1; AND.W d0, d1; BEQ.W 4c52e` (→`4c52c`)
- `4c52c`: `MOVE.W d2, d3` (→`4c52e`)
- `4c52e`: `MOVE.W d0, d1; OR.W 7e(a0), d1; ANDI.W #4, d1; BEQ.W 4c546` (→`4c53c`)
- `4c53c`: `MOVE.B #e0, d3; MOVE.B #1, 9a(a0)` (→`4c546`)
- `4c546`: `MOVE.W #11, d1; AND.W 7e(a0), d1; CMPI.W #11, d1; BNE.W 4c576` (→`4c556`)
- `4c556`: `TST.B 99(a0); BEQ.W 4c576` (→`4c55e`)
- `4c55e`: `MOVE.B #0, 9a(a0); MOVE.B 84(a0), d2; MOVE.W d2, d3; MOVE.L 2e(a6), 8e(a0); MOVE.L 32(a6), 92(a0)` (→`4c576`)
- `4c576`: `BRA.W 4c60e` — FLOW
- `4c57a`: `MOVE.W 7c(a0), d0; MOVE.W #8005, d1; AND.W d0, d1; CMPI.W #1, d1; BNE.W 4c59a` (→`4c58c`)
- `4c58c`: `MOVE.B 82(a0), d2; MOVE.B #1, 9a(a0); BRA.W 4c5ba`
- `4c59a`: `MOVE.W #8000, d1; AND.W d0, d1; BNE.W 4c5ba` (→`4c5a4`)
- `4c5a4`: `MOVE.W #1, d1; AND.W 7a(a0), d1; BEQ.W 4c5ba` (→`4c5b0`)
- `4c5b0`: `MOVE.B 80(a0), d2; MOVE.B #ff, 9a(a0)` (→`4c5ba`)
- `4c5ba`: `MOVE.W #4000, d1; AND.W d0, d1; BEQ.W 4c5c6` (→`4c5c4`)
- `4c5c4`: `MOVE.W d2, d3` (→`4c5c6`)
- `4c5c6`: `MOVE.W d0, d1; OR.W 7e(a0), d1; ANDI.W #4, d1; BEQ.W 4c5de` (→`4c5d4`)
- `4c5d4`: `MOVE.W #20, d3; MOVE.B #ff, 9a(a0)` (→`4c5de`)
- `4c5de`: `MOVE.W #11, d1; AND.W 7e(a0), d1; CMPI.W #11, d1; BNE.W 4c60e` (→`4c5ee`)
- `4c5ee`: `TST.B 99(a0); BEQ.W 4c60e` (→`4c5f6`)
- `4c5f6`: `MOVE.B #0, 9a(a0); MOVE.B 84(a0), d2; MOVE.W d2, d3; MOVE.L 2e(a6), 86(a0); MOVE.L 32(a6), 8a(a0)` (→`4c60e`)
- `4c60e`: `ADD.W d2, d2; MOVE.L 64(a6), d0; ASR.L #8, d0; MOVE.L d0, d1; LEA.L 4419e.l, a1; LEA.L 4411e.l, a2; MULS.W (a1, d2.w), d0; MULS.W (a2, d2.w), d1; MOVE.L d0, 36(a6); MOVE.L d1, 3a(a6); SUB.B 76(a0), d3; BEQ.W 4c65e` (→`4c63c`)
- `4c63c`: `LSL.W #8, d3; MOVE.W 64(a6), d0; BMI.W 4c648` (→`4c646`)
- `4c646`: `NOT.W d0` (→`4c648`)
- `4c648`: `ADDI.W #9, d0; BCC.W 4c652` (→`4c650`)
- `4c650`: `ASR.W d0, d3` (→`4c652`)
- `4c652`: `TST.W d3; BMI.W 4c65a` (→`4c658`)
- `4c658`: `ADDQ.W #1, d3` (→`4c65a`)
- `4c65a`: `ADD.W d3, 78(a0)` (→`4c65e`)
- `4c65e`: `RTS ` — FLOW

**helper `4c660`(`4c844` `4cf40 BSR`): `78.B` 제한 7**
- `4c660`: `MOVE.B 78(a0), d0; BEQ.W 4c6a2; BMI.W 4c688` (→`4c66c`)
- `4c66c`: `MOVE.B 76(a0), d1; ADD.B d0, d1; SUBI.B #20, d1; BLE.W 4c686` (→`4c67a`)
- `4c67a`: `SUB.B d1, d0; MOVE.B d0, 78(a0); MOVE.B #80, 79(a0)` (→`4c686`)
- `4c686`: `RTS ` — FLOW
- `4c688`: `MOVE.B 76(a0), d1; ADD.B d0, d1; SUBI.B #e0, d1; BGE.W 4c6a2` (→`4c696`)
- `4c696`: `SUB.B d1, d0; MOVE.B d0, 78(a0); MOVE.B #80, 79(a0)` (→`4c6a2`)
- `4c6a2`: `RTS ` — FLOW

**helper `4c6a4`(`4c848 BSR`): `5ca4`~`5cb0` 벡터 1**
- `4c6a4`: `MOVE.W #1800, d0; MOVE.W d0, d1; MOVE.W d0, d2; MOVE.W d0, d3; MOVEQ #0, d7; MOVE.B 76(a0), d7; ADD.W d7, d7; LEA.L 4419e.l, a1; LEA.L 4411e.l, a2; MULS.W (a1, d7.w), d0; MULS.W (a2, d7.w), d1; MOVE.L d0, 5cac(a5); MOVE.L d1, 5cb0(a5); LSR.W #1, d7; ADD.B 78(a0), d7; ADD.W d7, d7; MULS.W (a1, d7.w), d2; MULS.W (a2, d7.w), d3; SUB.L d0, d2; SUB.L d1, d3; MOVE.L d2, 5ca4(a5); MOVE.L d3, 5ca8(a5); RTS `

**helper `4c72a`(`4ca9c` `4ccf0 BSR`; 결정 4): `44602` 뒤 `5c9a`·`D2`/`D3` 6**
- `4c72a`: `LSL.L #2, d0; BPL.W 4c736` (→`4c730`)
- `4c730`: `ADDI.L #ffff, d0` (→`4c736`)
- `4c736`: `LSL.L #2, d1; BPL.W 4c742` (→`4c73c`)
- `4c73c`: `ADDI.L #ffff, d1` (→`4c742`)
- `4c742`: `SWAP d0; SWAP d1; JSR 44602.l`
- `4c74c`: `MOVEA.L 5c8e(a5), a0; SUB.B 76(a0), d0; LSL.W #8, d0; SUBI.W #80, d0; MOVEQ #0, d1; MOVE.B 79(a0), d1; ADD.W d1, d0; SUB.W d0, 5c9a(a5); LEA.L 4419e.l, a1; LEA.L 4411e.l, a2; MOVE.W 78(a0), d1; SUB.W d0, d1; LSR.W #8, d1; MOVEQ #0, d0; MOVE.B 76(a0), d0; ADD.B d0, d1; ADD.B 78(a0), d0; ADD.W d0, d0; ADD.W d1, d1; MOVE.W (a1, d1.w), d2; MOVE.W (a2, d1.w), d3; SUB.W (a1, d0.w), d2; SUB.W (a2, d0.w), d3; MULS.W #1800, d2; MULS.W #1800, d3; RTS `

**본문 `4c810`(`4c3e6 BRA.W`) 앞부분 8**
- `4c810`: `CLR.B 549d(a5); MOVEM.L 2e(a6), d0-d3/a0; LEA.L 538e(a5), a1; JSR 43eb8.l`
- `4c824`: `MOVEM.L d0-d3/a1, 2e(a6); MOVEA.L 5c8e(a5), a0; TST.B 9b(a0); BEQ.W 4c83c` (→`4c836`)
- `4c836`: `MOVE.W 54a4(a5), 98(a0)` (→`4c83c`)
- `4c83c`: `BSR.W 4c44c` — FLOW
- `4c840`: `BSR.W 4c4bc` — FLOW
- `4c844`: `BSR.W 4c660` — FLOW
- `4c848`: `MOVE.B #ff, 9b(a0); CLR.B 9c(a0); MOVEA.L 5c8e(a5), a0; BSR.W 4c6a4`
- `4c85a`: `CLR.L 5c92(a5); CLR.L 5c96(a5); CLR.W 5c9a(a5); CLR.L 5c9c(a5); CLR.L 5ca0(a5); MOVE.W 54a2(a5), -(a7); MOVE.W #ffff, 54a2(a5); CLR.W 7a(a0); CLR.W 7c(a0); MOVE.L #ffffffff, 5cb6(a5); MOVE.W #ff, 54a4(a5); MOVE.L 2e(a6), d0; MOVE.L 32(a6), d1; MOVE.L 8e(a0), d2; MOVE.L 92(a0), d3; SUB.L d0, d2; SUB.L d1, d3; LEA.L 538e(a5), a0; JSR 469d8.l`

**본문: 첫 번째 축(`8e`/`92`, `7a`/`80`) 탐색 35**
- `4c8ac`: `JSR 46bfc.l` — FLOW
- `4c8b2`: `MOVEA.L a1, a2; MOVEA.L a0, a1; LEA.L 538e(a5), a0; ADD.L 14(a1), d0; ADD.L 18(a1), d1; SUB.L 14(a0), d0; SUB.L 18(a0), d1; MOVEA.L 5c8e(a5), a0; MOVE.W #2, d5; AND.W d6, d5; BEQ.W 4c8e2` (→`4c8d8`)
- `4c8d8`: `ORI.W #4000, 7a(a0); MOVE.L a2, 5cb6(a5)` (→`4c8e2`)
- `4c8e2`: `MOVE.W #400, d5; AND.W d6, d5; BEQ.W 4c8f0` (→`4c8ec`)
- `4c8ec`: `CLR.B 9b(a0)` (→`4c8f0`)
- `4c8f0`: `MOVE.L 8e(a0), d0; MOVE.L 92(a0), d1; MOVE.L 2e(a6), d2; MOVE.L 32(a6), d3; SUB.L d0, d2; SUB.L d1, d3; LEA.L 538e(a5), a0; JSR 469d8.l`
- `4c90e`: `JSR 46bfc.l` — FLOW
- `4c914`: `MOVEA.L a1, a2; MOVEA.L a0, a1; LEA.L 538e(a5), a0; ADD.L 14(a1), d0; ADD.L 18(a1), d1; SUB.L 14(a0), d0; SUB.L 18(a0), d1; MOVEA.L 5c8e(a5), a0; ANDI.W #2, d6; BEQ.W 4c992` (→`4c938`)
- `4c938`: `ORI.W #8000, 7a(a0); MOVE.L a2, 5cb6(a5); CMPI.B #e0, 76(a0); BNE.W 4c992` (→`4c94c`)
- `4c94c`: `MOVE.W 7e(a0), d0; OR.W 7c(a0), d0; ANDI.W #1, d0; BNE.W 4c992` (→`4c95c`)
- `4c95c`: `TST.B 5cb4(a5); BEQ.W 4c96c` (→`4c964`)
- `4c964`: `TST.L 64(a6); BLT.W 4c992` (→`4c96c`)
- `4c96c`: `MOVE.B #ff, 9c(a0); MOVE.L 2e(a6), d0; MOVE.L 32(a6), d1; MOVE.L 8e(a0), d2; MOVE.L 92(a0), d3; SUB.L d0, d2; SUB.L d1, d3; ASR.L #1, d2; ASR.L #1, d3; ADD.L d0, d2; ADD.L d1, d3; BRA.W 4c9d0`
- `4c992`: `MOVE.L 8e(a0), d0; MOVE.L 92(a0), d1; MOVE.L 2e(a6), d2; MOVE.L 32(a6), d3; SUB.L 5cac(a5), d2; SUB.L 5cb0(a5), d3; MOVE.B 9a(a0), d6; BLT.W 4c9c8` (→`4c9b2`)
- `4c9b2`: `MOVE.L 5ca4(a5), d4; MOVE.L 5ca8(a5), d5; TST.B d6; BLE.W 4c9c4` (→`4c9c0`)
- `4c9c0`: `ADD.L d4, d4; ADD.L d5, d5` (→`4c9c4`)
- `4c9c4`: `SUB.L d4, d2; SUB.L d5, d3` (→`4c9c8`)
- `4c9c8`: `ADD.L 36(a6), d2; ADD.L 3a(a6), d3` (→`4c9d0`)
- `4c9d0`: `MOVE.L d2, -(a7); MOVE.L d3, -(a7); SUB.L d0, d2; SUB.L d1, d3; TST.B 5cb4(a5); BEQ.W 4c9ee` (→`4c9e0`)
- `4c9e0`: `TST.L 64(a6); BGE.W 4c9ee` (→`4c9e8`)
- `4c9e8`: `MOVE.W 98(a0), 54a4(a5)` (→`4c9ee`)
- `4c9ee`: `LEA.L 538e(a5), a0; JSR 469d8.l` — FLOW
- `4c9f8`: `JSR 46bfc.l` — FLOW
- `4c9fe`: `MOVEA.L a1, a2; MOVEA.L a0, a1; LEA.L 538e(a5), a0; ADD.L 14(a1), d0; ADD.L 18(a1), d1; SUB.L 14(a0), d0; SUB.L 18(a0), d1; MOVEA.L 5c8e(a5), a0; BTST.B #0, d6; BEQ.W 4ca26` (→`4ca22`)
- `4ca22`: `MOVE.L a1, 5cb6(a5)` (→`4ca26`)
- `4ca26`: `MOVE.L d0, 8e(a0); MOVE.L d1, 92(a0); MOVE.W #10, d5; AND.W d6, d5; BEQ.W 4ca54` (→`4ca38`)
- `4ca38`: `TST.B 5cb4(a5); BEQ.W 4ca54` (→`4ca40`)
- `4ca40`: `TST.B 99(a0); BEQ.W 4ca54` (→`4ca48`)
- `4ca48`: `MOVE.L 2e(a6), 8e(a0); MOVE.L 32(a6), 92(a0)` (→`4ca54`)
- `4ca54`: `SUBI.W #4000, d7; MOVE.W d7, 80(a0); OR.W d6, 7a(a0); MOVE.L (a7)+, d3; MOVE.L (a7)+, d2; SUB.L d2, d0; SUB.L d3, d1; BSR.W 4c6f0`
- `4ca6c`: `MOVE.L d0, d7; OR.L d1, d7; BEQ.W 4caa8` (→`4ca74`)
- `4ca74`: `MOVE.W #4, d6; AND.W 7a(a0), d6; BNE.W 4caa8` (→`4ca80`)
- `4ca80`: `TST.B 9a(a0); BLT.W 4caa8` (→`4ca88`)
- `4ca88`: `MOVE.L 5cac(a5), d0; MOVE.L 5cb0(a5), d1; SUB.L 2e(a6), d2; SUB.L 32(a6), d3; SUB.L d2, d0; SUB.L d3, d1; BSR.W 4c72a`
- `4caa0`: `ADD.L d2, 5c9c(a5); ADD.L d3, 5ca0(a5)` (→`4caa8`)

**본문: 두 번째 축(`86`/`8a`, `7c`/`82`) 탐색 43**
- `4caa8`: `MOVE.W #ff, 54a4(a5); MOVE.L 2e(a6), d0; MOVE.L 32(a6), d1; MOVE.L 86(a0), d2; MOVE.L 8a(a0), d3; SUB.L d0, d2; SUB.L d1, d3; LEA.L 538e(a5), a0; JSR 469d8.l`
- `4cacc`: `JSR 46bfc.l` — FLOW
- `4cad2`: `MOVEA.L a1, a2; MOVEA.L a0, a1; LEA.L 538e(a5), a0; ADD.L 14(a1), d0; ADD.L 18(a1), d1; SUB.L 14(a0), d0; SUB.L 18(a0), d1; MOVEA.L 5c8e(a5), a0; MOVE.W #2, d5; AND.W d6, d5; BEQ.W 4cb12` (→`4caf8`)
- `4caf8`: `MOVE.W #4000, 7c(a0); TST.W 5cb6(a5); BMI.B 4cb0e` (→`4cb04`)
- `4cb04`: `CMPI.W #0, 76(a0); BLT.W 4cb12` (→`4cb0e`)
- `4cb0e`: `MOVE.L a2, 5cb6(a5)` (→`4cb12`)
- `4cb12`: `MOVE.W #400, d5; AND.W d6, d5; BEQ.W 4cb20` (→`4cb1c`)
- `4cb1c`: `CLR.B 9b(a0)` (→`4cb20`)
- `4cb20`: `MOVE.L 86(a0), d0; MOVE.L 8a(a0), d1; MOVE.L 2e(a6), d2; MOVE.L 32(a6), d3; SUB.L d0, d2; SUB.L d1, d3; LEA.L 538e(a5), a0; JSR 469d8.l`
- `4cb3e`: `JSR 46bfc.l` — FLOW
- `4cb44`: `MOVEA.L a1, a2; MOVEA.L a0, a1; LEA.L 538e(a5), a0; ADD.L 14(a1), d0; ADD.L 18(a1), d1; SUB.L 14(a0), d0; SUB.L 18(a0), d1; MOVEA.L 5c8e(a5), a0; ANDI.W #2, d6; BEQ.W 4cbd2` (→`4cb68`)
- `4cb68`: `ORI.W #8000, 7c(a0); TST.L 5cb6(a5); BMI.B 4cb7e` (→`4cb74`)
- `4cb74`: `CMPI.W #0, 76(a0); BLT.W 4cb82` (→`4cb7e`)
- `4cb7e`: `MOVE.L a2, 5cb6(a5)` (→`4cb82`)
- `4cb82`: `CMPI.B #20, 76(a0); BNE.W 4cbd2` (→`4cb8c`)
- `4cb8c`: `MOVE.W 7e(a0), d0; OR.W 7a(a0), d0; ANDI.W #1, d0; BNE.W 4cbd2` (→`4cb9c`)
- `4cb9c`: `TST.B 5cb4(a5); BEQ.W 4cbac` (→`4cba4`)
- `4cba4`: `TST.L 64(a6); BGT.W 4cbd2` (→`4cbac`)
- `4cbac`: `MOVE.B #ff, 9c(a0); MOVE.L 2e(a6), d0; MOVE.L 32(a6), d1; MOVE.L 86(a0), d2; MOVE.L 8a(a0), d3; SUB.L d0, d2; SUB.L d1, d3; ASR.L #1, d3; ASR.L #1, d2; ADD.L d0, d2; ADD.L d1, d3; BRA.W 4cc10`
- `4cbd2`: `MOVE.L 86(a0), d0; MOVE.L 8a(a0), d1; MOVE.L 2e(a6), d2; MOVE.L 32(a6), d3; ADD.L 5cac(a5), d2; ADD.L 5cb0(a5), d3; MOVE.B 9a(a0), d6; BGT.W 4cc08` (→`4cbf2`)
- `4cbf2`: `MOVE.L 5ca4(a5), d4; MOVE.L 5ca8(a5), d5; TST.B d6; BGE.W 4cc04` (→`4cc00`)
- `4cc00`: `ADD.L d4, d4; ADD.L d5, d5` (→`4cc04`)
- `4cc04`: `ADD.L d4, d2; ADD.L d5, d3` (→`4cc08`)
- `4cc08`: `ADD.L 36(a6), d2; ADD.L 3a(a6), d3` (→`4cc10`)
- `4cc10`: `MOVE.L d2, -(a7); MOVE.L d3, -(a7); SUB.L d0, d2; SUB.L d1, d3; TST.B 5cb4(a5); BEQ.W 4cc2e` (→`4cc20`)
- `4cc20`: `TST.L 64(a6); BLE.W 4cc2e` (→`4cc28`)
- `4cc28`: `MOVE.W 98(a0), 54a4(a5)` (→`4cc2e`)
- `4cc2e`: `LEA.L 538e(a5), a0; JSR 469d8.l` — FLOW
- `4cc38`: `JSR 46bfc.l` — FLOW
- `4cc3e`: `MOVEA.L a1, a2; MOVEA.L a0, a1; LEA.L 538e(a5), a0; ADD.L 14(a1), d0; ADD.L 18(a1), d1; SUB.L 14(a0), d0; SUB.L 18(a0), d1; MOVEA.L 5c8e(a5), a0; BTST.B #0, d6; BEQ.W 4cc76` (→`4cc62`)
- `4cc62`: `TST.L 5cb6(a5); BMI.B 4cc72` (→`4cc68`)
- `4cc68`: `CMPI.W #0, 76(a0); BLT.W 4cc76` (→`4cc72`)
- `4cc72`: `MOVE.L a1, 5cb6(a5)` (→`4cc76`)
- `4cc76`: `MOVE.L d0, 86(a0); MOVE.L d1, 8a(a0); MOVE.W #10, d5; AND.W d6, d5; BEQ.W 4cca4` (→`4cc88`)
- `4cc88`: `TST.B 5cb4(a5); BEQ.W 4cca4` (→`4cc90`)
- `4cc90`: `TST.B 99(a0); BEQ.W 4cca4` (→`4cc98`)
- `4cc98`: `MOVE.L 2e(a6), 86(a0); MOVE.L 32(a6), 8a(a0)` (→`4cca4`)
- `4cca4`: `SUBI.W #4000, d7; MOVE.W d7, 82(a0); OR.W d6, 7c(a0); MOVE.L (a7)+, d3; MOVE.L (a7)+, d2; SUB.L d2, d0; SUB.L d3, d1; BSR.W 4c6f0`
- `4ccbc`: `MOVE.L d0, d7; OR.L d1, d7; BEQ.W 4ccfc` (→`4ccc4`)
- `4ccc4`: `MOVE.W #4, d6; AND.W 7c(a0), d6; BNE.W 4ccfc` (→`4ccd0`)
- `4ccd0`: `MOVEQ #0, d0; MOVEQ #0, d1; TST.B 9a(a0); BGT.W 4ccfc` (→`4ccdc`)
- `4ccdc`: `MOVE.L 5cac(a5), d0; MOVE.L 5cb0(a5), d1; SUB.L 2e(a6), d2; SUB.L 32(a6), d3; ADD.L d2, d0; ADD.L d3, d1; BSR.W 4c72a`
- `4ccf4`: `SUB.L d2, 5c9c(a5); SUB.L d3, 5ca0(a5)` (→`4ccfc`)

**본문: 누적 보정과 충돌 판정(`4b8e8`/`4bb22`) 17**
- `4ccfc`: `MOVE.W (a7)+, 54a2(a5); TST.B 5cb4(a5); BEQ.W 4cd50` (→`4cd08`)
- `4cd08`: `TST.L 64(a6); BNE.W 4cd50` (→`4cd10`)
- `4cd10`: `MOVE.L 5c92(a5), d0; BPL.W 4cd1a` (→`4cd18`)
- `4cd18`: `NEG.L d0` (→`4cd1a`)
- `4cd1a`: `MOVE.L 5c96(a5), d1; BPL.W 4cd24` (→`4cd22`)
- `4cd22`: `NEG.L d1` (→`4cd24`)
- `4cd24`: `ADD.L d0, d1; CMPI.L #10000, d1; BCC.W 4cd38` (→`4cd30`)
- `4cd30`: `CLR.L 5c92(a5); CLR.L 5c96(a5)` (→`4cd38`)
- `4cd38`: `MOVE.W 5c9a(a5), d0; ADDI.W #100, d0; CMPI.W #200, d0; BHI.W 4cd50` (→`4cd48`)
- `4cd48`: `CLR.L 5c9c(a5); CLR.L 5ca0(a5)` (→`4cd50`)
- `4cd50`: `MOVEM.L 2e(a6), d0-d3; ADD.L 5c92(a5), d2; ADD.L 5c96(a5), d3; ADD.L 5c9c(a5), d2; ADD.L 5ca0(a5), d3; TST.B 78(a0); BEQ.W 4cd86; BMI.W 4cd7e` (→`4cd72`)
- `4cd72`: `SUB.L 5ca4(a5), d2; SUB.L 5ca8(a5), d3; BRA.W 4cd86`
- `4cd7e`: `ADD.L 5ca4(a5), d2; ADD.L 5ca8(a5), d3` (→`4cd86`)
- `4cd86`: `MOVEQ #0, d7; MOVE.W 96(a0), d7; SWAP d7; SUB.L d7, d3; LEA.L 10d38e.l, a0; TST.B 549f(a5); BEQ.W 4cda8` (→`4cd9e`)
- `4cd9e`: `JSR 4b8e8.l` — FLOW
- `4cda4`: `BRA.W 4cdae` — FLOW
- `4cda8`: `JSR 4bb22.l` — FLOW

**본문: 바닥 판정 결과 기록과 끝 38**
- `4cdae`: `MOVEM.L d0-d3, -(a7); LEA.L 538e(a5), a0; JSR 469d8.l` — FLOW
- `4cdbc`: `MOVEA.L 5c8e(a5), a0; MOVE.W #10, d5; AND.W d5, d6; BEQ.W 4cdd8` (→`4cdca`)
- `4cdca`: `TST.B 99(a0); BEQ.W 4cdd8` (→`4cdd2`)
- `4cdd2`: `MOVE.B #ff, 549d(a5)` (→`4cdd8`)
- `4cdd8`: `MOVE.W #1, d5; AND.W d6, d5; BEQ.W 4cde6` (→`4cde2`)
- `4cde2`: `MOVE.W d7, 84(a0)` (→`4cde6`)
- `4cde6`: `MOVEM.L (a7)+, d0-d3; LEA.L 538e(a5), a0; MOVE.W d6, -(a7); JSR 469d8.l`
- `4cdf6`: `MOVEA.L a0, a1; MOVEA.L 5c8e(a5), a0; MOVE.W #1, d5; AND.W d6, d5; BEQ.W 4ce0a` (→`4ce06`)
- `4ce06`: `MOVE.W d7, 84(a0)` (→`4ce0a`)
- `4ce0a`: `OR.W (a7)+, d6; MOVE.W d6, 7e(a0); SUBI.B #40, 84(a0); TST.B 5cb4(a5); BEQ.W 4ce42` (→`4ce1e`)
- `4ce1e`: `BTST.B #2, d6; BEQ.W 4ce42` (→`4ce26`) — FLOW
- `4ce26`: `TST.L 64(a6); BLT.W 4ce34` (→`4ce2e`)
- `4ce2e`: `ORI.W #8000, 7c(a0)` (→`4ce34`)
- `4ce34`: `TST.L 64(a6); BGT.W 4ce42` (→`4ce3c`)
- `4ce3c`: `ORI.W #8000, 7a(a0)` (→`4ce42`)
- `4ce42`: `ANDI.W #fffb, d6; OR.W 7a(a0), d6; OR.W 7c(a0), d6; TST.B 5cb4(a5); BEQ.W 4ce82` (→`4ce56`)
- `4ce56`: `TST.L 64(a6); BEQ.W 4ce82; BMI.W 4ce74` (→`4ce62`)
- `4ce62`: `CMPI.B #20, 76(a0); BEQ.W 4ce70` (→`4ce6c`)
- `4ce6c`: `ANDI.W #fffb, d6` (→`4ce70`)
- `4ce70`: `BRA.W 4ce82` — FLOW
- `4ce74`: `CMPI.B #e0, 76(a0); BEQ.W 4ce82` (→`4ce7e`)
- `4ce7e`: `ANDI.W #fffb, d6` (→`4ce82`)
- `4ce82`: `TST.B 9c(a0); BNE.W 4ce98` (→`4ce8a`)
- `4ce8a`: `MOVE.W #c000, d5; AND.W d6, d5; BEQ.W 4ce98` (→`4ce94`)
- `4ce94`: `ORI.W #1, d6` (→`4ce98`)
- `4ce98`: `MOVE.W #1, d5; AND.W 7e(a0), d5; BNE.W 4cec2` (→`4cea4`)
- `4cea4`: `MOVEA.L 5cb6(a5), a2; CMPA.W #ffff, a2; BEQ.W 4cec2` (→`4ceb0`)
- `4ceb0`: `ADD.L 14(a1), d0; ADD.L 18(a1), d1; SUB.L 14(a2), d0; SUB.L 18(a2), d1; MOVEA.L a2, a1` (→`4cec2`)
- `4cec2`: `MOVE.L 36(a6), d2; MOVE.L 3a(a6), d3; LEA.L 538e(a5), a2; ADD.L 14(a2), d2; SUB.L 1c(a2), d2; ADD.L 18(a2), d3; SUB.L 20(a2), d3; SUB.L 14(a1), d2; ADD.L 1c(a1), d2; SUB.L 18(a1), d3; ADD.L 20(a1), d3; MOVEM.L d0-d3/a1, 2e(a6); TST.B 5cb4(a5); BNE.W 4cf04` (→`4cefc`)
- `4cefc`: `CLR.W 96(a0); BRA.W 4cf30`
- `4cf04`: `MOVE.W #1, d5; AND.W d6, d5; BEQ.W 4cf16` (→`4cf0e`)
- `4cf0e`: `CLR.W 96(a0); BRA.W 4cf30`
- `4cf16`: `TST.B 9c(a0); BNE.W 4cf30` (→`4cf1e`)
- `4cf1e`: `CMPI.W #4, 96(a0); BCC.W 4cf30` (→`4cf28`)
- `4cf28`: `ADDQ.W #1, 96(a0); ORI.W #1, d6` (→`4cf30`)
- `4cf30`: `BSR.W 4bf16` — FLOW
- `4cf34`: `MOVEA.L 5c8e(a5), a0; MOVE.W 5c9a(a5), d0; ADD.W d0, 78(a0); BSR.W 4c660`
- `4cf44`: `MOVE.B 78(a0), d0; ADD.B d0, 76(a0); MOVE.W 76(a0), d0; RTS `

## 작업자 검증 기록 (scratch, 커밋하지 않음)

Claude Opus 5.5 / high 작업자, 작업 트리 `/Users/start/Workspce/metalslug-n34`(기준 `e7c6972`), scratch `/Users/start/Workspce/ms5-scratch/n34/`. ROM SHA256 `29112a94…860f`·mtime `1791291625`·크기 8,388,608 불변.

- 산출(SHA256 앞 16자리): `engine/src/animation_machine_objects_n34.cpp` `3fd03fb50301ad3f`, `engine/tests/animation_machine_objects_n34_test.cpp` `95e7385ea77e9d13`, `engine/src/animation_machine.cpp` `949afcc61f5cbdd2`(routing `else if` 1개 + carry 목록 group 1개), `engine/src/animation_machine_internal.h` `fe199cacefd3a7dc`(선언 1줄), `Makefile` `9f819897e54f1988`(source·test target·run 줄), `tools/verify_animation_machine.py` `a0d980f9683df0c3`(SOURCES). 탐침 이동·두 번째 진입 patch 없음(결정 7).
- scratch: `n34.py` `be7edfe366b075e8`, `cls34.py` `e4828c887ac37494`, `unitdef_final.py` `a9a84012acfa4c37`, `starts.txt` `71750ef238ccfa64`, 생성기 `gen/gen34.py` `e2a5e24238f2b188`(= `fw_head.py` + `build34.py` + `fw_tail.py`), `gen/tables_n34.inc` `c60cdea80d0f06b8`, key facts `gen/mkfacts34.py` `203a93f1b75e284b`(손 계산·합성 표 공식에서 독립 계산), `gen/assemble34.py` `f6f14952c0394e22`, 실제 ROM 차등 `realrom/real34.py` `eb5e634b7ba23354`(+ `n34_part.py` `63bbaf407d946963`), 돌연변이 `mut/mut34.py` `0eb19f8bd442c61a`, 공유 편집 재적용 `apply_shared.py` `06f4f80f24a48e7b`.
- [F] `make -j3 all test`: exit 0, warning 0, `Assert` 줄 0(`make_all.log`).
- [F] N34 test(run_animation_machine만): fixture 392(checked 오류 13, kept C 15), block 220 × C 3(소비자 없음: FLOW 27은 진입 C 유지, 나머지는 Unknown, C에 따라 후속·상태가 바뀌지 않음), zero-step 220 × 3, 내부 PC 1,163 전부 `unsupported animation objects n34 PC`(죽은 `4c3f6..4c408` 포함), 홀수 PC 6, RAM 탐침 rollback(`10fe60` `10fe70` `10fe80` `10fea4` `10feb4`, RTS 복귀 `10fe90` 8건), 경계·callee stop 9 PC(`4bc44` `4bb22` `4bf16` `43eb8` `469d8` `46bfc` `4b8e8` `4c6f0` `44602`). 생성기: Unicorn 고정 ROM + 합성 표 `4411e..4439e`(ROM 자료 아님), 모든 data 읽기 검사, 220 시작 전부와 조건 분기 결과 전부(343 edge)를 fixture trace가 덮음. `4c49c`는 SR.N을 `D0` bit 15와 맞춘 상태로 생성.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`): N34 test 통과, runtime error 0(`ubsan.log`).
- [F] 돌연변이 68개 중 66개 검출(`mut/mut.log`). 살아남은 2개는 등가 돌연변이다: `m18`(`4c4ae BLE`→`BLT`: 같을 때 `78.W`에 같은 값을 씀), `m27`(`4c60e ASR.L #8`→`LSR`: 뒤의 `MULS.W`가 하위 WORD(= 원래 bit 8..23)만 읽음). 첫 실행의 생존자(`4c66c`/`4c688` 부호 BYTE 경계 `80`/`e0`, `4c53c`/`4c5d4` `D3` 상위 BYTE, `TST.W 5cb6` bit 15, `5cb6` 하위 WORD `ffff`, `4cba4` 0, `4c74c` `ADD.B` 넘침)는 typed fixture를 더해 모두 검출했다.
- [F] 실제 ROM 차등(8개 `program_rom_*.ms5d`, bank 200000/300000, Unicorn vs C++, 다른 단위 callee는 각 C++ 실행부로): seed 1·2·3 각 6,000 case, 220 시작 전부 도달, 불일치 seed 1: 0, seed 3: 0, seed 2: 1. 그 1건(`any` 진입 `4caa0`)은 의도된 차이다: 무작위 지형 RAM에서 U08 `447be`·U09 `47288` 탐색 고리가 30,032번 돌아 native는 2,989,464 명령 뒤 `4c6f0`에서 멈추지만 C++는 block 한도 1,000,000을 넘어 `animation machine block budget exceeded`(checked 오류, 상태 보존)를 낸다(N34 밖, `in_s2.bin` 기록 5459에서 재현). native 미정지 skip은 seed마다 약 1,030(대부분 끝 RTS가 무작위 스택 LONG을 꺼냄). native stop: `4c6f0` 약 2,650, `44602` 약 530, `ff000` 약 2,800(seed마다).
- [F] 기준 frame pass(`verify_animation_machine_scheduler_f4.py` 복사본, OUT scratch): 기준 `e7c6972` 14,648 pass / 126,694 node 일치 → N34 14,648 / 126,694, 불일치 0.
- [F] RNG 400 frame(`verify_animation_machine_scheduler_rng_f4.py` 복사본): 기준 `e7c6972` 134 완주 / 53,600 pass / 403,683 node / 불일치 0(JSON SHA256 `10385a3154d32e49…`) → N34 134 완주 / 53,600 / 403,683 / 불일치 0, checks 모두 참(JSON SHA256 `9ae773e09205e59c…`). 이 기준에서 seed 116 117은 frame 0 node 7 N35 `4cf52`에서 그대로 멈춘다(N34 경로는 그 뒤 frame 1 node 7).
- [F] **병합 시험(연속 줄 HEAD `b7b72d3` = N35·u08b `4bc58` 병합 뒤)**: `git archive b7b72d3`를 scratch `merge/`에 풀고 N34 새 파일 3개 복사 + `apply_shared.py`로 공유 편집(Makefile·routing·carry 목록·선언·SOURCES)을 다시 적용했다(자동 patch는 N35 인접 줄 때문에 충돌). `make -j3 all test` exit 0, warning 0, `Assert` 0(N34·N35 test 포함). frame pass 14,888 pass / 131,718 node 일치(N35 단독 14,650 / 126,740), 불일치 0. RNG 400: **136 완주**(seed 116 117 400 frame 완주), 54,400 pass / 412,067 node(N35 단독 53,602 / 403,729), 불일치 0, checks 모두 참, 변형 6 완주(JSON SHA256 `9803cc939423f84c…`). 남은 비완주는 기준과 같은 cpp-error-at-native-end 6건(141 포함)이다.
