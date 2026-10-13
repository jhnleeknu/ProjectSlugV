# 객체 callback F4 N32b: 함수 `39cda` 본문 중 `39b72` 이상 — 상태 `39b72`/`39b80` `39cb0` `39cda`(함수 진입) `39db4` `39eb2`, 설치 callback `39bb2` `39cda` `39e24` `39ef4`, BRA.W 표 `39e76`:9 `39f4a`:9 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N32 행과 N32a 계약(`animation-machine-objects-n32-contract.md`, SHA256 `372504afc664b44d6f563f941ac297216483af78ef69d03309e3f20cf4ada61d`, 결정 1: N32b = `39b72..39f9c` `3a34c..3a4a4` 162 block, 표 `39e76`:9 `39f4a`:9, BYTE 표 `39ca6..39cb0`는 자료), N31 계약(`animation-machine-objects-n31-contract.md`, SHA256 `afe778f95178a0f1e3a0f3d468f23a33c5eae9ec6133c69c1e8a5a3f5ad15fe2`, 결정 1: `3a34c..3a4a4`는 N31 소유, 이미 routing)이다. 메인 작업 지시:
- N32b = `39b72..39f9c`(자료 `39ca6..39cb0` 제외). `3a34c..3a4a4`는 N31 몫이므로 routing하지 않는다(메인 결정, 구속). N32b의 `BRA.W 3a350`/`3a41c`와 설치 값 `3a2f4`는 N31 실행부(이미 block 시작)로 간다.
- N32a가 나가는 `39b72` `39db4` `39eb2`를 block 시작으로 둔다. N32b가 N32a로 들어가는 `39076` `39156` `395dc` `395f8` `3976a` `398be`는 이미 N32a 시작이다(두 번째 진입 patch 없음).
- 별도 파일 `engine/src/animation_machine_objects_n32b.cpp`, 오류 문자열 `unsupported animation objects n32b PC`(내부 PC)와 `objects n32b caller requires known carry`(소비자가 있으므로 둠).
- 병행 N33 작업자 범위(`3a1e0..3a2f4` `3a5d2..` `3b118..` `3b542..` `4c3de..` 등)는 routing하지 않고 stop 전용 경계로 둔다.
- 범위 안 PC를 "routing 밖" 탐침으로 쓰는 기존 test는 RAM `10fe00..10fefe`로 옮긴다(해당 없음, 결정 9).

- 결정 관례(N30·N32a와 같음): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, 범위 밖에서 참조하는 범위 안 진입, 계산 점프 표 slot)로 정한다. Unicorn TB 분할은 시작이 아니다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N32a 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMPI`/`CMPA`/`CLR`/`ANDI`/`ADD`/`ADDI`/`SUB`/`NEG`/`ASR` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). `ORI #1,CCR`은 known Set 생산이다(N31·N30 관례). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`JMP`/`BRA`/Bcc/`BTST`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N32b 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n32b`(base `c5181b6` = N01~N31, N32a, F5 H1 통합; `engine/src/animation_machine.cpp` SHA256 `4337007826e7d6dc41dd3381162124ca0ca028f7b7eb04fc85e4dc36454e94d3`, routing 규칙 90개, `engine/src/animation_machine_objects_n32.cpp` SHA256 `e0c8d0df1663fe539f69d9a2c9251360ea43d95f16f2e9e29cdbd417ef618b9e`, `engine/src/animation_machine_objects_n31.cpp` SHA256 `887e18348061b56e6dea93bc3ef9dfebecb2d691c37cd55991d9693c5b69a2d4`)을 참조했다. `39b72..39f9c`의 짝수 PC는 모두 기존 routing 밖이고 양끝 이웃 `39b70` `39f9c`도 routing 밖이다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n32b/n32b.py`(정적 디코드, SHA256 `085a9e0883990e03fbc2759e0d4f531189ca31fe78600c176e7a94393924e625`; `starts.txt` SHA256 `d6c7cf4ca13e5c18fa1722459c0ab6ccde9207f5f4987747ea6389a9b1fdc7c8`)와 `cls32b.py`(분류, SHA256 `613be5f06a6cd95d8997ad0909a3e3a41424a5a22adeaf1b06602733874e7977`)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N32b = 125 block**(2 routing 범위 `39b72..39ca6` `39cb0..39f9c`, 코드 1,056바이트, 238 명령 전부 도달, 짝수 PC 528, 내부 403). 진입 4개(`39cda`(함수 진입·설치 값), N32a에서 들어오는 `39b72` `39db4` `39eb2`)에서 분기·fall-through·JSR 복귀점·범위 안 설치·BRA.W 표 2개를 끝까지 따라갔다. DBRA·TRAP·`JMP (An)`·RTS는 없다. 자료 `39ca6..39cb0`(BYTE 표 10, `39c74`가 읽음)은 routing하지 않는다.
- [F] N32a 계약의 N32b 162 block = 이 125 + N31이 가져간 `3a34c..3a4a4` 공유 꼬리 37 block(N31 계약 "공유 꼬리 `3a34c` / `3a350` / `3a3e8` / `3a41c` 37"). N32a가 N32b에만 있다고 적은 시작 5개(`39bb2` `39cb0` `39cba` `39e24` `39ef4`)는 모두 이 125 안에 있다.
- [F] 진입·참조(ROM 전체 `xref32b.py`): `39b72`(N32a `39108` `396aa`, 범위 밖 `38f94` `39b1c`, N32b `39d30`), `39db4`(N32a `39030` `390aa` `39666` `397b0`, 범위 밖 `38f26` `39ad8`, N32b `39bcc` `39cec`), `39eb2`(N32a `3918c`, 범위 밖 `391fa` `392ee` `39466` `3956c`). 설치 LONG `39bb2`(`39bae`), `39cb0`(`39c5e`), `39cda`(`39cd6`), `39e24`(`39e20`), `39ef4`(`39ef0`) 외에 범위 안을 가리키는 바깥 참조는 없다. `39e54`의 `6000 003a`(`ADDI.L #ffff6000`의 확장어)가 `39e90`을 가리키는 것은 우연 일치다(명령 중간).
- [F] **범위 안 설치 callback 5개**: `39bb2`(`39bac`, fall-through), `39cb0`(`39c5c`, 설치 뒤 `39c62`로), `39cda`(`39cd4`, fall-through), `39e24`(`39e1e`, fall-through), `39ef4`(`39eee`, fall-through).
- [F] **N32b → N32a 진입**: `39076`(`39c34` `39d54 BCS`), `39156`(`39bde` `39cfe`), `395dc`(`39c3c` `39d5c`), `395f8`(`39c44` `39d64`), `3976a`(`39be6` `39d06`), `398be`(`39bb8` `39ce0 BEQ`). 모두 N32a block 시작이다(patch 없음).
- [F] **N31 실행부로 가는 곳**: `BRA.W 3a350`(`39ca2` `39db0`), `BRA.W 3a41c`(`39eae` `39f98`), 설치 값 `3a2f4`(`39e44`). `3a350` `3a41c`는 N31 block 시작이다(patch 없음).
- [F] **경계(실행부 없음, routing 밖)**: callee `3a4be`(`39dc2` `39ec0`), `3a4da`(`39c2c` `39d4c`; C 반환), `3a5be`(`39c4c` `39d6c` `39ef8`; A0 = LONG `82`), `3a5d2`(`39b8a` `39dd0` `39ece`; N33), `3b282`(`39e58` `39f18`; N33), `3b288`(`39c50` `39d70`; N33), `3b302`(`39b78` `39b86` `39cb6` `39dcc` `39eca`; N33, A0 = 애니메이션 목록), `3b334`(`39c54` `39d74` `39e5c` `39f1c`; N33, C 반환), `3b424`(`39bbc` `39ce4`; N33, D0 반환), `d0fec`(`39e0a`); 분기 출구 `39f9c`(표 slot `39e7e` `39e82`의 `BRA.W`; 재범위 어느 단위에도 없음), `3a242`(`39f94 BRA.W`; N33 범위 `3a1e0..3a2f4`). 재범위 N32 bound 21개 중 N32b가 닿는 12개와 같다. 모두 `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee**: `3af8`(sound; `39db8` `39eb6`), `4ae4a`(N08; `39c04`(`3b756`) `39c6e`(`3b774`) `39ddc`(`3b792`) `39e64`(`3b7b0`) `39d24`(`3b756`) `39f38`(`3b80a`) `39f8e`(`3b828`)), `28ae`(자식 생성; `39c8a`(A0 = `3b1ae`) `39d98`(A0 = `3acd6`), D0.W = `1e`), `4970a`(`39c98` `39da6`, D0.W = D1.W = 0), `1ab02`(U05; `39e3a` `39f76`, A0 = `3b736`), `3c44`(`39f84`, D0.W = `1ac8`).
- [F] **범위 밖 설치 값·자식 값(실행 PC가 아님)**: 설치 `38e92`(`39d7c`; N32a 결정 7, 어느 단위에도 없음), `3a2f4`(`39e44`; N31), `39f9c`(`39ea8`; 어느 단위에도 없음). `28ae` 자식 callback `3b1ae`(N33 범위 `3b118..3b424`)와 `3acd6`(어느 단위에도 없음)은 A0로 넘기는 자료다.
- [F] **carry**(아래 "carry" 절): 소비 8 block(모두 FLOW), known 생산 2개(`39c9e` `39dac` `ORI #1,CCR` Set; 결정 2), FLOW_ONLY 80개(소비 8 포함), Unknown 43개. 80 + 2 + 43 = 125.
- [F] 고정 ROM 자료 읽기 1곳: `39c74 MOVE.B 39ca6(PC,D0.W),D1`(BYTE 표 `39ca6`, 색인 = `D0.W` 부호 확장, 범위 검사 없음; 결정 3). PC 상대 계산 점프 2곳: `39e76` `39f4a`(`CMPI.W #9,D0; BCC.W`로 0..8 제한, slot 9개 전부 전사; 결정 4). X·DIVx/MULx·TRAP·I/O port 쓰기·bank 변경·banked 읽기가 없다. N/Z 재계산이 없다(모든 비교와 그 Bcc가 한 block 안에 있다).
- [F] 스택: JSR 복귀 LONG, `MOVE.L D0,-(A7)`(LONG push; `39bfe` `39d1e` `JSR 4ae4a` 앞, `39c1e` `39d3e` `JSR 3a4da` 앞)과 `MOVEM.L (A7)+,D0`(LONG pop; `39c0a` `39c30` `39d2a` `39d50`). 같은 함수 안 짝이다(N32a 결정 6과 같음).
- [F] 자연 도달(재범위 scratch `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen32b.py`): RNG·base 두 기록 모두 **N32b 범위 PC는 한 번도 실행되지 않는다**. [I] 새 완주 seed는 없다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위: N32b 125 block, `3a34c..3a4a4` 제외.** [F] N31 결정(구속)대로 `3a34c..3a4a4`는 N31이 이미 routing했다. N32b routing은 `39b72..39ca6` `39cb0..39f9c` 두 범위다(자료 `39ca6..39cb0` 제외).
   - 대안: 없음(메인 지시).
2. **`39c9e` `39dac` `ORI.B #1,CCR`: known Set 생산.** [F] 두 block은 `JSR 4970a`의 복귀점이고 C = 1을 둔 뒤 `39ca2`/`39db0 BRA.W 3a350`(FLOW)으로 N31 `3a350`(FLOW, `BTST`+`BEQ`)에 들어간다. 그 뒤 `3a35a`(`MOVEQ`)·`3a376`(`ADDQ.B`)이 C를 덮으므로 **이 C를 읽는 소비자는 없다**. 원본 의미가 정확한 상수(Set)이므로 N31 `38d50`·N30의 `ORI` 관례대로 known Set 생산으로 둔다(관찰 차이는 `39ca2`/`3a350`에서 멈출 때의 C뿐).
   - 대안: 소비자가 없으므로 Unknown으로 둔다(실행 결과는 같고 stop 상태의 C만 다르다).
3. **`39c74` BYTE 표 읽기: 범위 검사 없이 live bus.** [F] `39c6a LEA 3b774(PC),A0; JSR 4ae4a.l` 뒤 `39c74 MOVE.B 39ca6(PC,D0.W),D1; BEQ.W 39ca2`. 확장어 `0030`(d8 = `30`, 색인 `D0.W`), PC = `39c76`이라 주소 = `39ca6` + 부호 확장 `D0.W`다. 원본에는 색인 검사가 없다. 실행부는 원본대로 `39ca6 + sext(D0.W)`(`31ca6..41ca5`, 모두 고정 ROM)를 live bus BYTE로 읽고 `D1.B`만 바꾼다. [F] ROM 표 10바이트 `00 01 01 00 01 00 00 00 01 00`(SHA256 `23274c63…095d`). [I] `4ae4a`가 `3b774` 목록에서 0..9를 돌려주는 것으로 보이나 [U] 확인하지 않았다(색인 제한을 실행부에 넣지 않음).
4. **BRA.W 표 `39e76`:9 `39f4a`:9: 전부 전사, 직접 진입은 F1 결정 3.** [F] `39e6a CMPI.W #9,D0; BCC.W 39e9e`(무부호 ≥ 9면 표를 건너뜀), `39e72 ADD.W D0,D0; ADD.W D0,D0; JMP 39e7a(PC,D0.W)`. slot(`39e7a` + 4k, k = 0..8): k = 1, 2(`39e7e` `39e82`) → `BRA.W 39f9c`(경계), 나머지 7개 → `BRA.W 39e9e`. `39f3e CMPI.W #9,D0; BCC.W 39f72`, `39f46 ... JMP 39f4e(PC,D0.W)`: k = 1, 2(`39f52` `39f56`) → `BRA.W 39f80`, 나머지 7개 → `BRA.W 39f72`. 18 slot 모두 block 시작이다. `39e72`/`39f46`은 조건분기 fall-through 시작이라 직접 진입하면 `D0.W`가 9 이상일 수 있다. 실행부는 N30 `336de`와 같이 검사 없이 `D0.W` = `(D0.W × 4) mod 10000`(16 bit, 상위 WORD 보존), PC = 표 base + 부호 확장 `D0.W`로 둔다(명령 중간 착지는 해당 실행부의 checked 오류 또는 routing 밖 오류; F1 결정 3).
5. **경계 callee C 소비 8 block.** [F] `39c58` `39d78`(`BCC.W`)는 `JSR 3b334`(N33)의 C, `39c30` `39d50`(`MOVEM.L (A7)+,D0; BCS.W`)은 `JSR 3a4da`(미배정)의 C를 읽는다(실행부 없음 → typed fixture의 선언 C로만 실행). `39c90` `39d9e`(`BCC.W`)는 `JSR 28ae`(실행부 있음: `2908 ORI` Set = 자식 생성, `290e ANDI` Clear = 실패), `39e40` `39f7c`(`BCC.W`)는 `JSR 1ab02`(U05: `1aafc ORI` Set, `1ab7a ANDI` Clear)의 C를 읽는다. Unknown C면 `objects n32b caller requires known carry`(상태 보존)다. 실제 생산자 뒤 소비자는 native 분기로 확인한다(Unicorn SR을 생산자 사실로 쓰지 않음).
6. **`MOVEM.L D0-D1,36(A6)`(`39e10`).** [F] 레지스터→메모리 `MOVEM`은 CCR을 바꾸지 않고 낮은 주소부터 `D0`(LONG `36`), `D1`(LONG `3a`) 순으로 쓴다. 같은 block의 `MOVE.L #3b68a,7e(A6)`·설치가 C를 바꾸므로 block은 Unknown이다.
7. **출구 `39f9c`·`3a242`와 설치 값 `39f9c`.** [F] `39f9c..3a1e0`은 재범위 어느 단위에도 없다(N32 범위 끝이 `39f9c`). `3a242`는 N33 범위 `3a1e0..3a2f4` 안이다(병행 N33 작업자가 시작으로 둬야 함; N32b 쪽 patch는 필요 없음). 둘 다 stop 전용 경계이고 test는 rollback 기대에 쓰지 않는다. [I] `39f9c`는 고아 정리 단계 몫이다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n32b.cpp`의 `animation_objects_n32b_block`. 오류는 `unsupported animation objects n32b PC`(내부 PC 403개), `objects n32b caller requires known carry`(소비 8 block).
9. **무효화 탐침 없음(탐침 이동 없음).** [F] `engine/tests`·`engine/src`·`tools/*.py`에서 `39b72..39f9c` 값은 N32a test의 stop PC `39b72` `39db4` `39eb2`(stop 전용; block 표 후속 PC 포함), `animation_machine_objects_u20_test.cpp` 레지스터 값 `0x39dde`, `animation_machine_objects_n04_test.cpp` 레지스터 값 `0x39f08`뿐이다. "routing 밖" 탐침이나 rollback 기대로 쓰는 곳은 없다.
10. **`2986` caller-X 제한 해당 없음.** [F] N32b는 `2986`을 부르지 않는다.

## 원본 바이트 근거

[F] N32b 코드 2 범위 합계 1,056바이트(짝수 PC 528개, 시작 125, 내부 403). 범위 순서로 이어 붙인 SHA256 `e8110fcaf0b28d387ba99890c2d41dd62cfc1f6bfd09951a4c09d103bd7c4a59`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `39b72..39ca6` | 308 | `cd47c2e0c91e3e404f9e17c9235eaf81a65f49b78f1f2c0a9b7164cdfcf5ea3c` | 34 |
| `39cb0..39f9c` | 748 | `6bbd412d17d11ed40e2b5852b0729adcb06f45e17a80716320290e5dff8e3678` | 91 |
| (자료) `39ca6..39cb0` | 10 | `23274c6361bbc4ff6919800c34cc16762e3f54c6de99e8458a75a28338ba095d` | - |

- [F] 범위 이웃: `39b72` 앞 `39a76..39b72`(N32a 결정 7의 설치 대상 코드 `39a76` `39ab6`; 어느 단위에도 없음), `39f9c..3a1e0`(결정 7), `3a1e0..3a2f4`(N33).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "FLOW"(C 보존), "Set 생산". 태그 없는 block은 Unknown이다. d16(An)은 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. 비교·`TST`·`BTST`와 그 Bcc는 같은 block 안에 있다.

**`39b72` / `39b80`(`39b72`: N32a `39108` `396aa` 등 `BNE`; `39b80`: `39c10 BNE`; 애니메이션 `3b936`/`3b93c`, `3a5d2`, 필드 초기화, 설치 callback `39bb2`(fall-through): BYTE `15` bit 7 → `398be`, 입력 `3b424`, BYTE `ac` → `39c48`, 입력 bit 7/1/5 → `39db4`/`39156`/`3976a`, `4ae4a`(`3b756`) → `39b80`, `3a4da` C → `39076`, bit 2/3 → `395dc`/`395f8`, partner `3a5be` `3b288` `3b334` C → 설치 `39cb0`, BYTE `98` → `4ae4a`(`3b774`) + BYTE 표 `39ca6` → `28ae`(`3b1ae`) C → `4970a` + ORI, 끝 `BRA 3a350`) 34**
- `39b72`: `MOVEA.L #3b936, a0; JSR 3b302(pc)` — FLOW
- `39b7c`: `BRA.W 39b8a` — FLOW
- `39b80`: `MOVEA.L #3b93c, a0; JSR 3b302(pc)` — FLOW
- `39b8a`: `JSR 3a5d2(pc)` — FLOW
- `39b8e`: `CLR.L 64(a6); MOVE.B #0, 9f(a6); ANDI.B #ef, 9d(a6); ANDI.B #ef, 9e(a6); CLR.B 98(a6); CLR.B ac(a6); MOVE.L #39bb2, (a6)` (→`39bb2`)
- `39bb2`: `BTST.B #7, 15(a6); BEQ.W 398be` (→`39bbc`) — FLOW
- `39bbc`: `JSR 3b424(pc)` — FLOW
- `39bc0`: `TST.B ac(a6); BEQ.W 39c48` (→`39bc8`)
- `39bc8`: `BTST.B #7, d0; BNE.W 39db4` (→`39bd0`) — FLOW
- `39bd0`: `BTST.B #1, d0; BEQ.W 39be2` (→`39bd8`) — FLOW
- `39bd8`: `BTST.B #7, 15(a6); BNE.W 39156` (→`39be2`) — FLOW
- `39be2`: `BTST.B #5, d0; BNE.W 3976a` (→`39bea`) — FLOW
- `39bea`: `BTST.B #2, 94(a6); BNE.W 39c14` (→`39bf4`) — FLOW
- `39bf4`: `BTST.B #4, 9d(a6); BEQ.W 39c14` (→`39bfe`) — FLOW
- `39bfe`: `MOVE.L d0, -(a7); LEA.L 3b756(pc), a0; JSR 4ae4a.l`
- `39c0a`: `TST.W d0; MOVEM.L (a7)+, d0; BNE.W 39b80` (→`39c14`)
- `39c14`: `BTST.B #6, 9d(a6); BEQ.W 39c38` (→`39c1e`) — FLOW
- `39c1e`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `39c30`: `MOVEM.L (a7)+, d0; BCS.W 39076` (→`39c38`) — C 소비, FLOW
- `39c38`: `BTST.B #2, d0; BNE.W 395dc` (→`39c40`) — FLOW
- `39c40`: `BTST.B #3, d0; BNE.W 395f8` (→`39c48`) — FLOW
- `39c48`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `39c50`: `JSR 3b288(pc)` — FLOW
- `39c54`: `JSR 3b334(pc)` — FLOW
- `39c58`: `BCC.W 39c62` (→`39c5c`) — C 소비, FLOW
- `39c5c`: `MOVE.L #39cb0, (a6)` (→`39c62`)
- `39c62`: `TST.B 98(a6); BEQ.W 39ca2` (→`39c6a`)
- `39c6a`: `LEA.L 3b774(pc), a0; JSR 4ae4a.l` — FLOW
- `39c74`: `MOVE.B 39ca6(pc, d0.w), d1; BEQ.W 39ca2` (→`39c7c`)
- `39c7c`: `CLR.B 98(a6); MOVEA.L #3b1ae, a0; MOVE.W #1e, d0; JSR 28ae.l`
- `39c90`: `BCC.W 39ca2` (→`39c94`) — C 소비, FLOW
- `39c94`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `39c9e`: `ORI.B #1, ccr` (→`39ca2`) — Set 생산
- `39ca2`: `BRA.W 3a350` — FLOW

**설치 callback `39cb0`(`39c5c`; 애니메이션 `3b942`, 필드 초기화, 설치 callback `39cda`(fall-through) = 함수 진입: `39b72` 계열과 같은 입력 검사(`4ae4a` → `39b72`), partner `3a5be` `3b288` `3b334` C → 설치 `38e92`(범위 밖 값), BYTE `ac` → `28ae`(`3acd6`) C → `4970a` + ORI, 끝 `BRA 3a350`) 28**
- `39cb0`: `MOVEA.L #3b942, a0; JSR 3b302(pc)` — FLOW
- `39cba`: `MOVE.B #0, 95(a6); CLR.L 64(a6); ANDI.B #8f, 9d(a6); ANDI.B #8f, 9e(a6); CLR.B ac(a6); MOVE.L #39cda, (a6)` (→`39cda`)
- `39cda`: `BTST.B #7, 15(a6); BEQ.W 398be` (→`39ce4`) — FLOW
- `39ce4`: `JSR 3b424(pc)` — FLOW
- `39ce8`: `BTST.B #7, d0; BNE.W 39db4` (→`39cf0`) — FLOW
- `39cf0`: `BTST.B #1, d0; BEQ.W 39d02` (→`39cf8`) — FLOW
- `39cf8`: `BTST.B #7, 15(a6); BNE.W 39156` (→`39d02`) — FLOW
- `39d02`: `BTST.B #5, d0; BNE.W 3976a` (→`39d0a`) — FLOW
- `39d0a`: `BTST.B #2, 94(a6); BNE.W 39d34` (→`39d14`) — FLOW
- `39d14`: `BTST.B #4, 9d(a6); BEQ.W 39d34` (→`39d1e`) — FLOW
- `39d1e`: `MOVE.L d0, -(a7); LEA.L 3b756(pc), a0; JSR 4ae4a.l`
- `39d2a`: `TST.W d0; MOVEM.L (a7)+, d0; BNE.W 39b72` (→`39d34`)
- `39d34`: `BTST.B #6, 9d(a6); BEQ.W 39d58` (→`39d3e`) — FLOW
- `39d3e`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `39d50`: `MOVEM.L (a7)+, d0; BCS.W 39076` (→`39d58`) — C 소비, FLOW
- `39d58`: `BTST.B #2, d0; BNE.W 395dc` (→`39d60`) — FLOW
- `39d60`: `BTST.B #3, d0; BNE.W 395f8` (→`39d68`) — FLOW
- `39d68`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `39d70`: `JSR 3b288(pc)` — FLOW
- `39d74`: `JSR 3b334(pc)` — FLOW
- `39d78`: `BCC.W 39d82` (→`39d7c`) — C 소비, FLOW
- `39d7c`: `MOVE.L #38e92, (a6)` (→`39d82`)
- `39d82`: `TST.B ac(a6); BEQ.W 39db0` (→`39d8a`)
- `39d8a`: `CLR.B ac(a6); MOVEA.L #3acd6, a0; MOVE.W #1e, d0; JSR 28ae.l`
- `39d9e`: `BCC.W 39db0` (→`39da2`) — C 소비, FLOW
- `39da2`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `39dac`: `ORI.B #1, ccr` (→`39db0`) — Set 생산
- `39db0`: `BRA.W 3a350` — FLOW

**`39db4`(N32a `39030` `390aa` `39666` `397b0`, N32b `39bcc` `39cec`, 범위 밖 `38f26` `39ad8 BNE`; 소리 `1ac8`, `3a4be`(`D1.B` = 1), 애니메이션 `3b960`, `3a5d2`, BYTE `9f` = 0, `4ae4a`(`3b792`) A0 → WORD 차 `42`/`46` 또는 상수 `30`/0, `d0fec`, LONG `36`/`3a`, LONG `7e` = `3b68a`, 설치 callback `39e24`(fall-through): WORD `3a` 부호 → BYTE `a4` = `7f` / `1ab02`(`3b736`) C → 설치 `3a2f4` + BYTE `a4` = 0, LONG `3a` += `ffff6000`, `3b282` `3b334`, `4ae4a`(`3b7b0`) → 표 `39e76` → `39f9c` / BYTE `15` bit 5 → 설치 `39f9c`, 끝 `BRA 3a41c`) 33**
- `39db4`: `MOVE.W #1ac8, d0; JSR 3af8.l`
- `39dbe`: `MOVE.B #1, d1; JSR 3a4be(pc)`
- `39dc6`: `MOVEA.L #3b960, a0; JSR 3b302(pc)` — FLOW
- `39dd0`: `JSR 3a5d2(pc)` — FLOW
- `39dd4`: `CLR.B 9f(a6); LEA.L 3b792(pc), a0; JSR 4ae4a.l`
- `39de2`: `CMPA.W #0, a0; BEQ.W 39dfe` (→`39dea`)
- `39dea`: `MOVE.W 42(a0), d0; SUB.W 42(a6), d0; MOVE.W 46(a0), d1; SUB.W 46(a6), d1; BRA.W 39e02`
- `39dfe`: `MOVEQ #30, d0; MOVEQ #0, d1` (→`39e02`)
- `39e02`: `MOVE.L #ffff6000, d2; MOVEQ #23, d3; JSR d0fec.l`
- `39e10`: `MOVEM.L d0-d1, 36(a6); MOVE.L #3b68a, 7e(a6); MOVE.L #39e24, (a6)` (→`39e24`)
- `39e24`: `TST.W 3a(a6); BLE.W 39e36` (→`39e2c`)
- `39e2c`: `MOVE.B #7f, a4(a6); BRA.W 39e50`
- `39e36`: `LEA.L 3b736(pc), a0; JSR 1ab02.l` — FLOW
- `39e40`: `BCC.W 39e4a` (→`39e44`) — C 소비, FLOW
- `39e44`: `MOVE.L #3a2f4, (a6)` (→`39e4a`)
- `39e4a`: `MOVE.B #0, a4(a6)` (→`39e50`)
- `39e50`: `ADDI.L #ffff6000, 3a(a6); JSR 3b282(pc)`
- `39e5c`: `JSR 3b334(pc)` — FLOW
- `39e60`: `LEA.L 3b7b0(pc), a0; JSR 4ae4a.l` — FLOW
- `39e6a`: `CMPI.W #9, d0; BCC.W 39e9e` (→`39e72`)
- `39e72`: `ADD.W d0, d0; ADD.W d0, d0; JMP 39e7a(pc, d0.w)`
- `39e7a` `39e86` `39e8a` `39e8e` `39e92` `39e96` `39e9a`: `BRA.W 39e9e` — FLOW(slot k = 0, 3..8)
- `39e7e` `39e82`: `BRA.W 39f9c` — FLOW(slot k = 1, 2; 경계)
- `39e9e`: `BTST.B #5, 15(a6); BEQ.W 39eae` (→`39ea8`) — FLOW
- `39ea8`: `MOVE.L #39f9c, (a6)` (→`39eae`)
- `39eae`: `BRA.W 3a41c` — FLOW

**`39eb2`(N32a `3918c`, 범위 밖 `391fa` `392ee` `39466` `3956c BNE`; 소리 `1ac8`, `3a4be`(`D1.B` = 1), 애니메이션 `3b8fa`, `3a5d2`, BYTE `95` = 5, `9f` = `11`, LONG `7e` = `3b68a`, `36` = 0, 설치 callback `39ef4`(fall-through): partner `3a5be`, LONG `36` 지수 접근(`c0000`, BYTE `15` bit 0 부호, `ASR.L #5`), `3b282` `3b334`, BYTE `15` bit 7·`61` bit 0 → `4ae4a`(`3b80a`) → 표 `39f4a` → `1ab02`(`3b736`) C → `BRA 3a41c` / 소리 `3c44`(`1ac8`), `4ae4a`(`3b828`), 끝 `BRA 3a242`) 30**
- `39eb2`: `MOVE.W #1ac8, d0; JSR 3af8.l`
- `39ebc`: `MOVE.B #1, d1; JSR 3a4be(pc)`
- `39ec4`: `MOVEA.L #3b8fa, a0; JSR 3b302(pc)` — FLOW
- `39ece`: `JSR 3a5d2(pc)` — FLOW
- `39ed2`: `MOVE.B #5, 95(a6); MOVE.B #11, 9f(a6); MOVE.L #3b68a, 7e(a6); MOVE.L #0, 36(a6); MOVE.L #39ef4, (a6)` (→`39ef4`)
- `39ef4`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `39efc`: `MOVE.L #c0000, d0; BTST.B #0, 15(a6); BEQ.W 39f0e` (→`39f0c`)
- `39f0c`: `NEG.L d0` (→`39f0e`)
- `39f0e`: `SUB.L 36(a6), d0; ASR.L #5, d0; ADD.L d0, 36(a6); JSR 3b282(pc)`
- `39f1c`: `JSR 3b334(pc)` — FLOW
- `39f20`: `BTST.B #7, 15(a6); BEQ.W 39f80` (→`39f2a`) — FLOW
- `39f2a`: `BTST.B #0, 61(a6); BNE.W 39f80` (→`39f34`) — FLOW
- `39f34`: `LEA.L 3b80a(pc), a0; JSR 4ae4a.l` — FLOW
- `39f3e`: `CMPI.W #9, d0; BCC.W 39f72` (→`39f46`)
- `39f46`: `ADD.W d0, d0; ADD.W d0, d0; JMP 39f4e(pc, d0.w)`
- `39f4e` `39f5a` `39f5e` `39f62` `39f66` `39f6a` `39f6e`: `BRA.W 39f72` — FLOW(slot k = 0, 3..8)
- `39f52` `39f56`: `BRA.W 39f80` — FLOW(slot k = 1, 2)
- `39f72`: `LEA.L 3b736(pc), a0; JSR 1ab02.l` — FLOW
- `39f7c`: `BCC.W 39f98` (→`39f80`) — C 소비, FLOW
- `39f80`: `MOVE.W #1ac8, d0; JSR 3c44.l`
- `39f8a`: `LEA.L 3b828(pc), a0; JSR 4ae4a.l` — FLOW
- `39f94`: `BRA.W 3a242` — FLOW(경계, N33)
- `39f98`: `BRA.W 3a41c` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다. "애니메이션 x"는 `MOVEA.L #x,A0; JSR 3b302(PC)`, "partner"는 `MOVEA.L 82(A6),A0; JSR 3a5be(PC)`, "소리 x"는 `MOVE.W #x,D0; JSR 3af8.l`, "push"는 `MOVE.L D0,-(A7)`(A7 −= 4), "pop"은 `MOVEM.L (A7)+,D0`(A7 += 4, `D0` = LONG, CCR 불변)이다):
  - `39b72`: 애니메이션 `3b936`, `39b7c`: `BRA 39b8a`. `39b80`: 애니메이션 `3b93c`. `39b8a`: `JSR 3a5d2`. `39b8e`: LONG `64` = 0, BYTE `9f` = 0, BYTE `9d` &= `ef`, BYTE `9e` &= `ef`, BYTE `98` = 0, BYTE `ac` = 0, `(A6)` = `39bb2`, fall-through.
  - `39bb2`: BYTE `15` bit 7 = 0이면 `398be`(N32a). `39bbc`: `JSR 3b424`. `39bc0`: BYTE `ac` = 0이면 `39c48`. `39bc8`: `D0` bit 7 → `39db4`. `39bd0`/`39bd8`: `D0` bit 1 = 1이고 BYTE `15` bit 7 = 1이면 `39156`(N32a). `39be2`: `D0` bit 5 → `3976a`(N32a). `39bea`: BYTE `94` bit 2 = 0이고(`39bf4`) BYTE `9d` bit 4 = 1이면 `39bfe`: push, A0 = `3b756`, `JSR 4ae4a`. `39c0a`: `D0.W` = 0 여부를 보고 pop; `D0.W` ≠ 0이었으면 `39b80`. `39c14`: BYTE `9d` bit 6 = 1이면 `39c1e`: push, BYTE `9d`/`9e` &= `bf`, `JSR 3a4da`. `39c30`: pop; Set이면 `39076`(N32a). `39c38`: `D0` bit 2 → `395dc`. `39c40`: `D0` bit 3 → `395f8`. `39c48`: partner. `39c50`: `JSR 3b288`. `39c54`: `JSR 3b334`. `39c58`: Set이면 `(A6)` = `39cb0`(`39c5c`). `39c62`: BYTE `98` = 0이면 `39ca2`. `39c6a`: A0 = `3b774`, `JSR 4ae4a`. `39c74`: `D1.B` = BYTE(`39ca6` + 부호 확장 `D0.W`); 0이면 `39ca2`. `39c7c`: BYTE `98` = 0, A0 = `3b1ae`, `D0.W` = `1e`, `JSR 28ae`. `39c90`: Clear면 `39ca2`. `39c94`: `D0.W` = 0, `D1.W` = 0, `JSR 4970a`. `39c9e`: C = 1. `39ca2`: `BRA 3a350`(N31).
  - `39cb0`: 애니메이션 `3b942`. `39cba`: BYTE `95` = 0, LONG `64` = 0, BYTE `9d` &= `8f`, BYTE `9e` &= `8f`, BYTE `ac` = 0, `(A6)` = `39cda`, fall-through. `39cda`..`39d64`: `39bb2`..`39c44`와 같은 검사(`39d2a`는 `D0.W` ≠ 0이면 `39b72`). `39d68`: partner. `39d70`: `JSR 3b288`. `39d74`: `JSR 3b334`. `39d78`: Set이면 `(A6)` = `38e92`(`39d7c`, 범위 밖 값). `39d82`: BYTE `ac` = 0이면 `39db0`. `39d8a`: BYTE `ac` = 0, A0 = `3acd6`, `D0.W` = `1e`, `JSR 28ae`. `39d9e`: Clear면 `39db0`. `39da2`: `D0.W` = `D1.W` = 0, `JSR 4970a`. `39dac`: C = 1. `39db0`: `BRA 3a350`.
  - `39db4`: 소리 `1ac8`. `39dbe`: `D1.B` = 1, `JSR 3a4be`. `39dc6`: 애니메이션 `3b960`. `39dd0`: `JSR 3a5d2`. `39dd4`: BYTE `9f` = 0, A0 = `3b792`, `JSR 4ae4a`. `39de2`: A0(32 bit) = 0이면 `39dfe`: `D0` = `30`, `D1` = 0(LONG). 아니면 `39dea`: `D0.W` = WORD `42(A0)` − WORD `42(A6)`, `D1.W` = WORD `46(A0)` − WORD `46(A6)`(16 bit, 읽기 순서 `42(A0)` `42(A6)` `46(A0)` `46(A6)`). `39e02`: `D2` = `ffff6000`, `D3` = `23`, `JSR d0fec`. `39e10`: LONG `36` = `D0`, LONG `3a` = `D1`, LONG `7e` = `3b68a`, `(A6)` = `39e24`, fall-through. `39e24`: WORD `3a` ≤ 0(부호 있음)이면 `39e36`: A0 = `3b736`, `JSR 1ab02` → `39e40`: Set이면 `(A6)` = `3a2f4`(`39e44`); `39e4a`: BYTE `a4` = 0. WORD `3a` > 0이면 `39e2c`: BYTE `a4` = `7f`. `39e50`: LONG `3a` += `ffff6000`(32 bit, 읽고 씀), `JSR 3b282`. `39e5c`: `JSR 3b334`. `39e60`: A0 = `3b7b0`, `JSR 4ae4a`. `39e6a`: 무부호 `D0.W` ≥ 9면 `39e9e`. `39e72`: 결정 4. `39e9e`: BYTE `15` bit 5 = 1이면 `(A6)` = `39f9c`(`39ea8`). `39eae`: `BRA 3a41c`(N31).
  - `39eb2`: 소리 `1ac8`. `39ebc`: `D1.B` = 1, `JSR 3a4be`. `39ec4`: 애니메이션 `3b8fa`. `39ece`: `JSR 3a5d2`. `39ed2`: BYTE `95` = 5, BYTE `9f` = `11`, LONG `7e` = `3b68a`, LONG `36` = 0, `(A6)` = `39ef4`, fall-through. `39ef4`: partner. `39efc`: `D0` = `c0000`; BYTE `15` bit 0 = 1이면 `39f0c`: `D0` = −`D0`(32 bit). `39f0e`: `D0` −= LONG `36`(32 bit), `D0` = 산술 오른쪽 5 bit(부호 확장), LONG `36` = LONG `36`(다시 읽음) + `D0`(32 bit), `JSR 3b282`. `39f1c`: `JSR 3b334`. `39f20`: BYTE `15` bit 7 = 0이거나(`39f2a`) BYTE `61` bit 0 = 1이면 `39f80`. `39f34`: A0 = `3b80a`, `JSR 4ae4a`. `39f3e`: 무부호 `D0.W` ≥ 9면 `39f72`. `39f46`: 결정 4. `39f72`: A0 = `3b736`, `JSR 1ab02`. `39f7c`: Clear면 `39f98`: `BRA 3a41c`. `39f80`: `D0.W` = `1ac8`, `JSR 3c44`. `39f8a`: A0 = `3b828`, `JSR 4ae4a`. `39f94`: `BRA 3a242`(경계).
- [I] 의미 추정(미확인): `39db4`는 뛰어오르기(LONG `36`/`3a` 속도, `3a` 중력 −`a000`), `39eb2`는 다른 공중 동작, `4ae4a`의 `3b7b0`/`3b80a` 목록은 0..8 입력 분류로 보인다. 실행부는 이 추정에 기대지 않는다.

## carry

- [F] **소비 8 block**(모두 FLOW). Unknown C로 들어오면 `objects n32b caller requires known carry`(상태 보존)다.
  - `BCC.W`(Clear면 분기 대상, Set이면 fall-through): `39c58 BCC.W 39c62`, `39d78 BCC.W 39d82`(경계 `3b334`의 C), `39c90 BCC.W 39ca2`, `39d9e BCC.W 39db0`(`28ae`의 C), `39e40 BCC.W 39e4a`, `39f7c BCC.W 39f98`(`1ab02`의 C).
  - `MOVEM.L (A7)+,D0; BCS.W`(pop 뒤 Set이면 분기 대상): `39c30 BCS.W 39076`, `39d50 BCS.W 39076`(경계 `3a4da`의 C).
- [F] **known 생산 2 block**: `39c9e` `39dac`(`ORI.B #1,CCR`, Set; 결정 2). 다른 `CLR`/`MOVE`/`ADD`/`SUB`/`NEG`/`ASR`/`CMPI`/`CMPA`/`TST` block의 C는 같은 block의 Bcc나 다음 소비자가 읽지 않는다(Unknown).
- [F] **FLOW_ONLY 80 block**(C 보존): `39b72` `39b7c` `39b80` `39b8a` `39bb2` `39bbc` `39bc8` `39bd0` `39bd8` `39be2` `39bea` `39bf4` `39c14` `39c30` `39c38` `39c40` `39c48` `39c50` `39c54` `39c58` `39c6a` `39c90` `39ca2` `39cb0` `39cda` `39ce4` `39ce8` `39cf0` `39cf8` `39d02` `39d0a` `39d14` `39d34` `39d50` `39d58` `39d60` `39d68` `39d70` `39d74` `39d78` `39d9e` `39db0` `39dc6` `39dd0` `39e36` `39e40` `39e5c` `39e60` `39e7a` `39e7e` `39e82` `39e86` `39e8a` `39e8e` `39e92` `39e96` `39e9a` `39e9e` `39eae` `39ec4` `39ece` `39ef4` `39f1c` `39f20` `39f2a` `39f34` `39f4e` `39f52` `39f56` `39f5a` `39f5e` `39f62` `39f66` `39f6a` `39f6e` `39f72` `39f7c` `39f8a` `39f94` `39f98`.
- [F] **carry 보존 목록 80 PC** = FLOW_ONLY 80(`carry_preserving_pc`의 주석 붙은 case group 하나).
- [F] **Unknown 43 block**: `39b8e` `39bc0` `39bfe` `39c0a` `39c1e` `39c5c` `39c62` `39c74` `39c7c` `39c94` `39cba` `39d1e` `39d2a` `39d3e` `39d7c` `39d82` `39d8a` `39da2` `39db4` `39dbe` `39dd4` `39de2` `39dea` `39dfe` `39e02` `39e10` `39e24` `39e2c` `39e44` `39e4a` `39e50` `39e6a` `39e72` `39ea8` `39eb2` `39ebc` `39ed2` `39efc` `39f0c` `39f0e` `39f3e` `39f46` `39f80`.
- [F] N32b에는 RTS가 없다. 모든 경로는 경계 callee·다른 실행부 호출, N32a 진입, `BRA 3a350`/`3a41c`(N31), `BRA 39f9c`/`3a242`(경계)에서 이 단위를 떠난다.

## 구현 범위와 규약

- routing 2 범위(위 표). 짝수 PC 528개 중 block 시작 125, 내부 403. 내부 PC 직접 진입은 `unsupported animation objects n32b PC`다. 자료 `39ca6..39cb0`와 범위 이웃(`39b70` 이하, `39f9c` 이상)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVE.L`·`MOVEQ`·`MOVEA`·`LEA`·`MOVEM.L`·`NEG.L`·`SUB.L`·`ASR.L`은 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow·음수 오른쪽 shift에 기대지 않는다(`ADDI.L #ffff6000`, `SUB.W`, `NEG.L`, `SUB.L`, `ASR.L #5`(bit 31 복제), `ADD.L`, `ADD.W D0,D0`). 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). `CLR`은 쓰기만 한다(기존 단위와 같음). `CMPA.W #0,A0`은 A0 32 bit 전체를 0과 비교한다.
- carry: 위 "carry" 절. `39c9e` `39dac`는 C = Set을 둔다.
- 제어 이동: 정적 + 표 2개(결정 4). 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`39bb2` `39cda` `39e24` `39ef4`). 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다.
- 스택: JSR 복귀 LONG, push/pop(LONG, `am_push`/`am_pop` 크기 4). work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 work RAM(노드·A0 대상)과 고정 ROM BYTE 표(`39c74`)이며 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] 고정 ROM 읽기: BYTE 표 `39ca6..39cb0`(`39c74`, 색인 `D0.W` 부호 확장, 결정 3). banked 읽기 없음. 주소만 넘기는 자료: 애니메이션 목록 `3b936` `3b93c` `3b942` `3b960` `3b8fa`(A0 → `3b302`), `4ae4a` 목록 `3b756` `3b774` `3b792` `3b7b0` `3b80a` `3b828`(A0), 사각형 `3b736`(A0 → `1ab02`), `28ae` 자식 callback `3b1ae` `3acd6`(A0), 소리 id `1ac8`(`D0.W` → `3af8`/`3c44`), LONG `7e` 값 `3b68a`, `d0fec` 인자 `D2` = `ffff6000`, `D3` = `23`.
- [F] work RAM 노드 A6: BYTE `15`(bit 0, 5, 7) `61`(bit 0) `94`(bit 2) `95` `98` `9d`(bit 4, 6) `9e` `9f` `a4` `ac`; WORD `3a`(상위 WORD, `TST.W`) `42` `46`; LONG `(A6)`(설치) `36` `3a` `64` `7e` `82`(partner 포인터, A0로만 넘김). `4ae4a`(`3b792`)가 돌려준 A0 노드의 WORD `42` `46`.
- [F] 상수 인자: `3a4be` `D1.B` = 1; `28ae` `D0.W` = `1e`; `4970a` `D0.W` = `D1.W` = 0.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_objects_n32b.cpp` `93e78f3160ec8881`, `engine/tests/animation_machine_objects_n32b_test.cpp` `8b8fb075fc4d331a`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나(2 범위), carry 보존 case group 하나(80 PC); `efac24a464c1f74e`), `engine/src/animation_machine_internal.h`(선언 하나; `b6bb4cf1ca5e5f87`), `Makefile`(source 목록·test target·실행 줄; `528f6d2ea7275003`), `tools/verify_animation_machine.py` SOURCES(`71268a44dd7ac64d`). N32a·N31 실행부와 `animation_machine_interpreter.cpp`는 바꾸지 않았다. 다른 단위의 두 번째 진입 patch는 필요 없다.
- [F] 실행부 case 집합 = scratch `starts.txt`(125). 내부 PC 403개는 모두 `unsupported animation objects n32b PC`, 소비 8 block은 Unknown C에서 `objects n32b caller requires known carry`(상태 보존)다.
- [F] `make -j3 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all2.log`). N32b test 출력: `animation machine objects n32b: 535 fixtures (31 checked errors, 44 kept C), 125 blocks, 1700 calls`. N32a(203)·N31(96)·N30(166) test는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N32b test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen32b.py` Unicorn 생성(표 SHA256 앞 16자리 `dcc1ee59b15e2c85`), `gen/assemble32b.py` 조립): 535 fixture(성공 504, checked 오류 31), 125 시작 모두 Unicorn fixture로 덮음, block 표(125 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 8은 Unknown에서 거부; 생산 `39c9e` `39dac` Set), zero-step 125 × 3, 내부 PC 403 전수, 자료 `39ca6..39cae` 5 PC(routing 밖 오류), 홀수 PC(범위 양끝 4), RAM rollback 탐침 `10fe60` `10fe70` `10fe80`, 경계·다른 단위 진입 stop 26개(stop만), 여러 block 뒤 스택 오류로 끝나는 rollback 행과 표 직접 진입의 명령 중간 착지 오류 행(`39e72`/`39f46`, `D0.W` = `a`). 합성 물리 바이트(ROM 자료 아님): BYTE 표 `39ca6..39cb0`(`00 01 00 02 00 7f 80 00 ff 00`), 사각형 `3b736`, `4ae4a` 목록 `3b756`과 `4a9ea..4a9ec`. 실제 생산자를 따라간 행: `28ae`(자식 생성 성공 Set / 실패 Clear → 소비자 `39c90` `39d9e`), `1ab02`(위치 6종 × BYTE `15` 4종 → `39e40` `39f7c`, Clear·Set 모두), `4970a` → ORI Set → `3a350`(C Set), `3af8` `3c44` `4ae4a`. 색인 범위 밖 `39c74`(`D0.W` = `a` `ffff` `8000` `7fff`)는 live bus의 `missing or ambiguous physical program bus ROM byte`다(검사 없음 확인).
- [F] 돌연변이 검사(scratch `mut/mut32b.py`, 실행부 44곳 + carry 목록 2곳 + routing 3곳, 49개): 48/49를 test가 잡았다(`mut/mut.log`, `mut_extra.log`; 처음 실행에서 살아남은 `m48`(자료 `39ca6..39cb0`까지 routing)은 자료 PC 검사를 더한 뒤 잡힘). 살아남은 `m37`(`39f0e`에서 LONG `36`을 다시 읽지 않고 첫 읽기 값 사용)은 같은 주소를 쓰기 없이 두 번 읽는 것이라 관찰 차이가 없는 동치 돌연변이다.
- [F] 실제 ROM 차분(scratch `realrom/real32b.py` SHA256 앞 16자리 `bb5bd4ba46a81f23`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM; native는 STOP·C++ routing 밖 첫 PC(N32b 경계 12개는 선언 stop으로 유지)·`2a00`·`2a24`·`49f8c`/`49f96`에서 멈춤; `3af8` `4ae4a`(실제 목록) `28ae` `4970a` `1ab02`(실제 `3b736`) `3c44`, N32a·N31 진입은 양쪽에서 실행): 3 seed × 1,500 case 불일치 0/0/0, 시작 124/125/125(합집합 125), native skip 5/9/3(`39c94`/`39da2`에 무작위 A0로 들어가 `4970a`가 깨끗이 멈추지 않음; `39c90` 1), port 0, 홀수 주소 0, Unknown C 진입 소비 거부 0, `2986` 0. 실제 생산자 뒤 소비자 native 분기 비교: seed 1 `39c90` 60 `39d9e` 52 `39e40` 66 `39f7c` 135(seed 2·3도 각 40~135회). 의도된 차이: 표 JMP block(`39e72`)에 `D0.W` ≥ 9로 직접 들어가 명령 중간에 착지한 4건(seed 1 2건, seed 3 2건; F1 결정 3, C++ checked 오류)을 따로 셌다.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `c5181b6` 일치 pass 14,648·node 126,688, 불일치 0 → N32b 뒤 같음(`diff_results.json` SHA256 앞 16자리 `ad8c6c0a8680d6e6`, 기준과 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 134·pass 53,600·node 403,677·불일치 0(`verification.json` `9f7116ab…`) → N32b 뒤 같은 수치·불일치 0(`d96faa6e…`; 차이는 기록된 `animation_machine.cpp` SHA(seed 116 117의 `current_router_sha256` 포함)와 새 원본 목록뿐). **새 완주 seed 없음**(예상과 같음), 잃은 seed 0.
- [F] 탐침 이동: 없음(결정 9). 이 test의 새 RAM 탐침은 `10fe60` `10fe70` `10fe80`이다.
- [U] 남은 미확인: N32b 범위는 자연 400 frame에서 실행되지 않아 frame pass 비교가 없다(실제 ROM 차분·fixture로만 덮음). 경계 `3b334`·`3a4da`의 C 생산과 `3b424`·`4ae4a`(`3b774`/`3b7b0`/`3b80a`)의 반환 범위는 그 단위가 정한다(결정 3·4). `39f9c..3a1e0`과 자식 callback `3acd6`은 어느 단위에도 없다(결정 7).
