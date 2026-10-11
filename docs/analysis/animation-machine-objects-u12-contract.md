# 객체 callback F4 U12: 공유 core 조각(`1abda`, 지형 탐색 `46d72`, 수학 `49098`/`490ba`/`492ae`/`492c8`, 이동 `4c0ac`)과 `70418`/`70054` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U12 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`), U04 계약(`animation-machine-objects-u04-contract.md`, SHA256 `9c61f228b57bdb3a3b239b3342d437aeaba2d22169caeae3ad9d772d1f405397`, 결정 2 flag 재계산), U10 계약(`animation-machine-objects-u10-contract.md`, SHA256 `2b3c1f73213c12bb8f3b5512968210e99d1986a04b90321ce48e99c0fa98147c`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다. 결정 6: `TRAP #f`는 실행부 없는 checked 경계다.
- U01~U10 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U12에는 없음). `MOVE.x`/`MOVEQ`/`TST`/`CMP`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`, Z만 바꾸는 `BTST`/`BSET`/`BCLR`)만인 block은 FLOW_ONLY다. `ADDQ`/`SUBQ`/`ADDA` An block은 Unknown이다. 앞 predecessor가 하나뿐일 때 flag를 정확히 재계산한다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U12의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u12`(HEAD `58898ef`, U01~U10 + U08a/U08b + cleanup `43e04` WIP, `engine/src/animation_machine.cpp` SHA256 `4df62add779f5ca9641815dd63fcb0835d450a229cf16f6fd8edec9e5ed2cc4c`, routing 규칙 45개)을 참조했다. U11은 다른 작업 트리(`metalslug-u11`)에서 구현 중이며 그 범위(`448ca..449dc` `45176..452fa` `46efe..472b8` `49370..497ea` 외 3)의 PC는 여기서 경계로 둔다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u12/u12.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] U12는 **block 시작 162개 + TRAP 경계 3개(`4910c` `4913e` `49174`)**다. 함수 진입 9개(`1abda` `46d72` `49098` `490ba` `492ae` `492c8` `4c0ac` `70418` `70054`; `70054`는 `70548 BRA`와 외부 `72e8a`/`735a4 BRA.W`로 들어온다). 코드 10 범위, 1,652바이트, 433명령이며 미해독·PC 상대 점프 표·레지스터 간접 점프·설치 callback·묶인 Bcc·SUBX/ADDX/DIVx는 없다(MULU 2: `70432` `70452`). routing 짝수 PC는 826개, 내부 PC는 664개다.
- [F] **범위 문서 170(함수 본문 합 171)과의 차이(−9)**:
  - −4: `449ae` `449be` `449c6` `449ca`. 범위 문서 이후 U08a(`4483a` 표 대상 `447be..44ade`)가 이미 routing한다. 다시 routing하지 않는다.
  - −2: `452ea` `45310`. U11의 `45176` `JMP d(PC,D7.W)` 표(`4517a..452fa`, 96 슬롯) 슬롯과 그 대상이다(U11 범위). U12에서는 `46e08`/`46e6a BSR 45176`의 경계로만 나타난다.
  - −3: TRAP `4910c` `4913e` `49174`는 block이 아니라 경계다(F3b·U01 관례).
- [F] **경계 callee(실행부 없음) 9개**: 범위 문서의 7개 `4bc04` `4c1de` `4c29a` `4c2cc`(C 반환) `6feb4` `70036` `ea5f0`(범위 문서 U13)과 U11의 `45176`(`46e08` `46e6a`) `49370`(`70054`). TRAP 3개는 routing 밖이다.
- [F] 기존 실행부로 나가는 호출: readiness `289e`(C 반환), cleanup `43e34`·`8ff4`, U08 `447be`, U08a `4483a`(표 진입), U08b `461ec`·`4bc44`, U09 `469a0`·`469ae`, stage_area RNG `49a58`, stage_event_ops `49a84`, U05 `c6a96`.
- [F] **flag**: known carry 생산 block 4개(`1abda` `1abec` `46eda` `46ee6`), C 소비 block 4개(`490a4` `490b0` SCS, `4c0c6` `70502` BCC), RTS를 넘는 N 소비 2개(`70198 BPL`, `701cc SMI`; `49a58`의 `SUB.W D0,(A3)` 결과, 아래 결정 4).
- [F] I/O: `49140`·`49196`가 `MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L`(PVC bank 0 선택, 기존 `am_zero_bank`와 같은 세 쓰기)을 한다. 그 밖 port 쓰기 없음.
- [F] 자연 도달(F4 범위 scratch 재생 `f4scope/dyn`, TB 기준): base 162 중 60 block(seed 52개), RNG 초기화+응답 `80` 변형 117 block. 범위 안 TB 시작은 모두 정적 시작이다(TB 인공 진입 0).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(170→162).** 위 −9를 적용한다(권고). U08a 표 대상과 U11 표는 다시 routing하지 않는다.
2. **경계 callee 9개.** 범위 문서 7개와 U11 `45176` `49370`을 실행부 없는 경계로 둔다(권고). U11 병합 뒤에는 `45176`/`49370`이 실행된다. U12 routing은 이 PC들을 포함하지 않으므로 U11과 충돌이 없다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u12.cpp`의 `animation_objects_u12_block`. 오류는 `unsupported animation objects u12 PC`, `objects u12 caller requires known carry`(메인 지시와 같음).
4. **RTS를 넘는 N(`70198` `701cc`).** [F] 두 block은 `JSR 49a58.L`(`70192` `701c6`)의 복귀점이고 predecessor는 `49a58`의 `49a80 SUB.W D0,(A3); RTS` 하나뿐이다. N은 그 결과 WORD의 bit 15이며 `RTS`·복귀 뒤에도 `A3`와 그 WORD는 바뀌지 않는다. 권고: 두 block이 live `A3`의 WORD를 다시 읽어 N을 정확히 재계산한다(U04 결정 2와 같은 방식). 직접 진입하는 test fixture는 같은 전제(N = WORD (A3) bit 15)로 만든다. `A3`가 홀수이거나 읽을 수 없으면 기존 checked 읽기 오류다.
5. **`1abda`의 C.** [F] 외부 호출자 14곳 중 8곳(`ea5d6` `ea5e6` `ea5f6` `ea606` `ea686` `ea6b8` `eaa82` `eaac6`)이 반환 C를 소비한다. `1abea RTS`는 `CMPI.W #ffff,D1`(같지 않음)의 C=Set을, `1abec`는 `ANDI.B #fe,CCR`의 Clear를 돌려준다. 권고: `1abda`가 CMPI의 정확한 C(`D1.W <u ffff`)를 만들고 `1abea`는 FLOW_ONLY로 둔다.
6. **`46d72`의 C.** [F] 호출자 4곳(`4c0c6` U12, `4c128` `4c182` `4c2e8` 다른 단위)이 모두 C를 소비한다. `46eda`(`MOVE.W 54aa(A5),D5`가 C를 지움)가 Clear, `46ee6 ORI.B #1,CCR`가 Set을 만들고 `46eea RTS`가 넘긴다.
7. **`490a4`/`490b0` SCS.** [F] 두 block은 `JSR 289e.L`(readiness, known C) 복귀점에서 C를 `Scc`로 소비한다. `490a4`는 CCR을 바꾸지 않으므로(SCS/LEA/JSR) 들어온 C를 그대로 둔다(FLOW_ONLY). `490b0`은 `ADD.B`로 C를 바꾸므로 끝에서 Unknown이다(`490ba`의 `490be MOVE.L`이 받는다; `49098`의 외부 호출자는 `490bc` 하나).
8. **ROM 표 읽기.** [F] `490be LEA 48f98(PC),A1` 뒤 `MOVE.B (A1,D0.W),D0`(`490f0`)와 `MOVE.B (A1,D5.W),D5`(`49176`)는 fixed ROM `48f98..49098`(256 BYTE, [I] index의 1 bit 수 표)을 읽는다. index는 `AND`/BYTE 확장으로 0..ff에 묶인다(`490f0`: `D0.W = D5.W AND (2^(n)−1)`, n=1..8; `49176`: `D5.W` = `MOVE.B (A0)+` 뒤 `MOVEQ #0` 위 BYTE). 권고: live bus(`am_read`)로 읽고 test에는 합성 표를 쓴다(ROM 자료를 test에 넣지 않음). 호출자 A0 자료(`c8750` `c868e` `c85cc` 등 fixed ROM 또는 RAM)도 live bus로 읽는다.
9. **무효화 탐침.** [F] `engine/tests`에서 `492c8`을 rollback·outside 탐침으로 쓰는 곳 3곳: U08 test `interior()` outside, U08b test `BOUNDARIES`(그 PC에서 멈춘 fixture를 STOP으로 다시 실행해 rollback 기대)와 `interior()` outside. 권고 교체(어느 `docs/analysis` 파일에도 없는 `5fa00` 이후 PC): U08 `0x5fa10`, U08b BOUNDARIES `0x5fa14`(stop으로 쓰이지 않음), U08b outside `0x5fa18`. U10 test의 `492c8`은 stop 성공만 확인하므로 그대로 둔다.

## 원본 바이트 근거

[F] 코드 10 범위 합계 1,652바이트. 범위 순서로 이어 붙인 SHA256 `ec6b65c9a3235c4e74ac792e285b20f64d020328f99daad1a6bf2d044eac54bd`.

| CPU 범위 | 바이트 | SHA256 |
| --- | --- | --- |
| `1abda..1abfa` | 32 | `d6620268e286f96200b8cd62dea7c72b90c926440706ee878be76f6e27768815` |
| `46d72..46eec` | 378 | `e774a6f07a2008e895df79a36cdb885a3ead034967a35ff0edc962537e2f0689` |
| `49098..4910c` | 116 | `d08d23f69067f712f4c6f5cd42e9104485c10ce7a7bc11e23e9801e8e7e04903` |
| `4911a..4913e` | 36 | `30b5fc0d25f706119e28d877cae481029c29147963de59991ab4265129016ded` |
| `49140..49174` | 52 | `9166da1339a508b5edc5daa6b4d3a2d72ee229d8e4ce8d88909e911afbe28348` |
| `49176..491b6` | 64 | `7100a271723f275226af05c7188672c7a63906f2648a84b5dfc2a8cfb4a6e757` |
| `492ae..492d0` | 34 | `e44fd0f344f49978e6c170e348f4d3a9e463507c4dd404fcd5ada5f355eba792` |
| `4c0ac..4c0ea` | 62 | `f25f07f09224a57796fa8f73a52d047b5fa65c887f81dfe4ab4e782eab69f1fa` |
| `70054..7028e` | 570 | `48513e8e10e872e0cd1774a40dab6304bb6ccb05477c1fba9de1520fb8518022` |
| `70418..7054c` | 308 | `7293c9ba70339e469114bd14fc1a6dbf34b6902c57908df596e458432c853a07` |

- [F] 범위에서 뺀 바이트: TRAP `4910c`(`4e4f`)+문자열 `4910e..4911a`(`DIFF EZRR OR` 류 ASCII 뒤 `00`), TRAP `4913e`(`4e4f`), TRAP `49174`(`4e4f`). 범위 이웃: `1abfa`(다른 함수), `46eec..46ef4`(다른 본문; cleanup `46ef4`), `48f98..49098`(BYTE 표, 자료), `491b6`(범위 문서 U23), `492d0`(범위 문서 U20), `4c0ea`(다른 함수), `70036..70054`(경계 함수 `70036`), `7028e..70418`(다른 함수), `7054c`(다른 함수).
- [F] 자료:
  - fixed ROM: BYTE 표 `48f98..49098`(256개, 값 0..8, index 0의 값 0). 호출자 A0 자료(U12 안의 호출자는 `c8750` `c868e` `c85cc`): BYTE 유형 `(A0)`, BYTE mask `1(A0)`, 그 뒤 WORD/BYTE 표.
  - work RAM `A5`: WORD `542e` `5430`(`1abda`), LONG `54d0` `54d4`(MOVEM A0) `54d8` `54ba`/`54be`(MOVEM D0-D1), WORD `54aa` `54ae` `54b0` `54b2` `54dc`, BYTE `54b4`, BYTE `7d8b`(=`10fd8b`) `-7fee`(=`100012`), WORD `-7ff0`(=`100010`, 쓰기, `am_zero_bank`), 노드 `-7348`(`100cb8`) `-7258`(`100da8`)의 LONG `0`(`289e`) WORD `42`.
  - 노드 d16(A6): BYTE `15` `61` `6a` `6e` `82` `83` `86`, WORD `1e` `42` `46` `68` `6e` `76` `78` `7a` `7c` `7e` `8e` `90` `9a` `9c`, LONG `2e`..`3e`(MOVEM D0-D3/A0, 읽기 D0-D1), `3e`(MOVEA).
  - 탐색 노드 d16(A0/A1): LONG `14` `18`.
  - 스택: `46db6 SUBQ.W #4,A7`로 지역 LONG `(A7)`을 두고 `46eba ADDQ.W #4,A7`로 푼다. `490ba MOVE.L A0,-(A7)`/`490be MOVE.L (A7)+,D6`, `70158`의 WORD push 2개/`7016a` pop 2개.
- [F] I/O: PVC `2ffff2`(WORD `1000`)·`2ffff0`(WORD `0`)와 WORD `-7ff0(A5)`(=0) 쓰기(`49140` `49196`, 같은 순서). 그 밖 port 쓰기·bank 변경 없음.

## block 목록과 실행 의미

[F] 162 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `MOVE.B`/`MOVE.W` Dn·`ADD.W`/`SUB.W`/`AND.W`/`ANDI.W`/`SUBQ.W`/`NEG.W`/`LSR.W`/`LSL.W`/`ASR.W`/`ADDQ.B`/`SUBQ.B`/`ANDI.B`/`NEG.B`/`ADD.B`/`AND.B`/`SWAP`는 나머지 bit를 보존하고 `MOVEQ`/`MOVE.L`/`NEG.L`/`ADD.L`/`SUB.L`/`LSR.L`/`MULU.W`은 LONG 전체를 쓴다. `MOVEA.W #0,A0`은 부호확장한다. `BSET.B Dn,Dm`은 bit 번호 `Dn mod 32`의 LONG bit다. 같은 block 안 `CMP`/`CMPI` 뒤 `BCC`/`BCS`는 무부호 비교, `BPL`/`BMI`/`SPL`/`SMI`는 결과 부호다. 단독 `BCC` block은 앞 JSR callee가 돌려준 C를 소비한다.

**`1abda` 3**
- `1abda`: `MOVE.W 542e(A5),D0; MOVE.W 5430(A5),D1; CMPI.W #ffff,D1; BEQ.W 1abec` (함수 진입; C 생산: CMPI.W #ffff 결과(같지 않으면 Set))
- `1abea`: `RTS`
- `1abec`: `MOVE.W #210,D0; MOVE.W #20c,D1; ANDI.B #fe,ccr; RTS` (C 생산: Clear)

**지형 탐색 `46d72` 35**
- `46d72`: `MOVEM.L A0,54d4(A5); MOVE.L #160,54d8(A5); MOVEQ #0,D2; CMPA.W #0,A0; BSR.W 469a0` (함수 진입; U09)
- `46d8a`: `NEG.L D3; MOVE.L D3,54d0(A5); MOVE.W #0,54aa(A5); MOVE.L #fff80000,D3; CMPA.W #0,A0; BEQ.W 46dac`
- `46da4`: `ADD.L 14(A0),D0; ADD.L 18(A0),D1` (→`46dac`)
- `46dac`: `MOVEM.L D0-D1,54ba(A5); BSR.W 469ae` (U09)
- `46db6`: `SUBQ.W #4,A7; CMPA.W #0,A1; BEQ.W 46eba`
- `46dc0`: `MOVEA.L A1,A0; SUB.L 14(A0),D0; SUB.L 18(A0),D1; MOVE.L #0,(A7); SWAP D0; SWAP D1; BSR.W 447be` (U08)
- `46dd8`: `MOVE.W D7,54ae(A5); CMPI.W #178,D7; BEQ.B 46dea`
- `46de2`: `CMPI.W #17c,D7; BNE.W 46df4`
- `46dea`: `MOVE.W #160,D7; ORI.W #400,54aa(A5)` (→`46df4`)
- `46df4`: `MOVE.W D7,54b0(A5); MOVE.W D6,54b2(A5); CLR.B 54b4(A5); SWAP D0; SWAP D1; BSR.W 4483a` (U08a 표)
- `46e08`: `BSR.W 45176` (U11 경계)
- `46e0c`: `TST.L D6; BPL.W 46e84`
- `46e12`: `SUB.L D3,(A7); SWAP D0; SWAP D1; SUBQ.W #8,D1; BSR.W 447be` (U08)
- `46e1e`: `MOVE.W D6,54b2(A5); MOVE.W 54ae(A5),D4; MOVE.W D7,54ae(A5); CMPI.W #174,D4; BNE.W 46e3e`
- `46e32`: `CMPI.W #174,D7; BNE.W 46e3e`
- `46e3a`: `MOVE.W #160,D7` (→`46e3e`)
- `46e3e`: `CMPI.W #178,D7; BEQ.B 46e4c`
- `46e44`: `CMPI.W #17c,D7; BNE.W 46e56`
- `46e4c`: `MOVE.W #160,D7; ORI.W #400,54aa(A5)` (→`46e56`)
- `46e56`: `MOVE.W D7,54b0(A5); SWAP D0; SWAP D1; CMPI.W #160,D7; BEQ.W 46e78`
- `46e66`: `BSR.W 4483a` (U08a 표)
- `46e6a`: `BSR.W 45176` (U11 경계)
- `46e6e`: `CMPI.L #80000000,D6; BNE.W 46e84`
- `46e78`: `MOVE.L (A7),D4; CMP.L 54d0(A5),D4; BCS.B 46e12`
- `46e80`: `BRA.W 46ea8`
- `46e84`: `ADD.L (A7),D6; CMP.L 54d0(A5),D6; BCC.W 46ea8`
- `46e8e`: `ORI.W #1,54aa(A5); MOVE.L D6,54d0(A5); MOVE.L D7,54d8(A5); MOVEM.L A0,54d4(A5); MOVE.W 54b2(A5),54dc(A5)` (→`46ea8`)
- `46ea8`: `MOVEM.L 54ba(A5),D0-D1; BSR.W 469ae` (U09)
- `46eb2`: `CMPA.W #0,A1; BNE.W 46dc0`
- `46eba`: `ADDQ.W #4,A7; MOVEA.L 54d4(A5),A0; CMPA.W #0,A0; BEQ.W 46ed0`
- `46ec8`: `SUB.L 14(A0),D0; SUB.L 18(A0),D1` (→`46ed0`)
- `46ed0`: `MOVE.L 54d8(A5),D7; MOVE.W D7,D5; BSR.W 461ec` (U08b)
- `46eda`: `MOVE.L 54d0(A5),D6; MOVE.W 54aa(A5),D5; BEQ.W 46eea` (C 생산: Clear(MOVE))
- `46ee6`: `ORI.B #1,ccr` (→`46eea`) (C 생산: Set)
- `46eea`: `RTS`

**`49098` 3**
- `49098`: `MOVEQ #0,D7; LEA.L -7348(A5),A0; JSR 289e.L` (함수 진입; readiness, C 반환)
- `490a4`: `SCS.B D0; LEA.L -7258(A5),A0; JSR 289e.L` (readiness, C 반환; carry 소비: 289e 반환 C)
- `490b0`: `SCS.B D1; AND.B D0,D1; NEG.B D1; ADD.B D1,D7; RTS` (carry 소비: 289e 반환 C)

**`490ba` 13**
- `490ba`: `MOVE.L A0,-(A7); BSR.B 49098` (함수 진입)
- `490be`: `MOVE.L (A7)+,D6; MOVEA.L D6,A0; LEA.L 48f98(PC),A1; MOVE.B (A0)+,D6; MOVEQ #0,D5; MOVE.B (A0)+,D5; MOVE.B 7d8b(A5),D1; CMPI.B #2,-7fee(A5); BEQ.W 490dc`
- `490da`: `MOVEQ #3,D1` (→`490dc`)
- `490dc`: `CMPI.B #7,D1; BCS.W 490f0`
- `490e4`: `CMPI.W #2,D7; BCS.W 490f0`
- `490ec`: `MOVE.B #1,D7` (→`490f0`)
- `490f0`: `MOVEQ #0,D2; ANDI.B #7,D1; ADDQ.B #1,D1; BSET.B D1,D2; SUBQ.W #1,D2; MOVE.W D5,D0; AND.W D2,D0; MOVE.B (A1,D0.w),D0; CMPI.B #1,D0; BCC.W 4911a` (아니면 TRAP `4910c`)
- `4911a`: `SUBQ.B #1,D0; ADD.W D0,D0; ADD.W D7,D0; CMPI.B #2,D6; BEQ.W 49160`
- `49128`: `ADD.W D0,D0; ADD.W D0,D0; MOVE.W D0,D1; ADD.W D0,D0; ADD.W D1,D0; MOVE.B 6a(A6),D1; CMPI.W #c,D1; BCS.W 49140` (아니면 TRAP `4913e`)
- `49140`: `ADD.W D1,D1; ADD.W D1,D0; ADDA.W D0,A0; MOVE.W (A0),D0; MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS`
- `49160`: `ADD.W D0,D0; MOVE.W D0,D1; ADD.W D0,D0; ADD.W D1,D0; MOVE.B 6a(A6),D1; CMPI.W #c,D1; BCS.W 49176` (아니면 TRAP `49174`)
- `49176`: `ADD.W D1,D0; MOVE.B (A0,D0.w),D0; LSL.W #4,D0; MOVE.B (A1,D5.w),D5; ADD.W D5,D5; MOVE.W D5,D1; ADD.W D5,D5; ADD.W D1,D5; ADD.W D5,D5; ADD.W D5,D0; ADDA.W D0,A0; JSR 49a58.L` (stage_area RNG)
- `49196`: `ANDI.W #e,D0; MOVE.W (A0,D0.w),D0; MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS`

**`492ae`/`492c8` 5**
- `492ae`: `MOVE.W 68(A6),D0; MOVE.W D0,D7; ANDI.W #f000,D7; CMPI.W #8000,D7; BNE.W 492c6` (함수 진입)
- `492c0`: `MOVE.W 46(A6),D1; SUB.W D1,D0` (→`492c6`)
- `492c6`: `RTS`
- `492c8`: `BSR.B 492ae` (함수 진입)
- `492ca`: `MOVE.W D0,1e(A6); RTS`

**`4c0ac` 6**
- `4c0ac`: `JSR 4bc44(PC)` (함수 진입; U08b)
- `4c0b0`: `MOVEM.L 2e(A6),D0-D1; MOVEA.L 3e(A6),A0; MOVE.L #ff000000,D3; JSR 46d72.L`
- `4c0c6`: `BCC.W 4c0d2` (carry 소비: 46d72 반환 C)
- `4c0ca`: `SUB.L D6,D1; BSET.B #7,15(A6)` (→`4c0d2`)
- `4c0d2`: `LSR.L #8,D7; MOVE.W D7,6e(A6); MOVEQ #0,D2; MOVEQ #0,D3; MOVEM.L D0-D3/A0,2e(A6); JSR 43e34.L` (cleanup)
- `4c0e8`: `RTS`

**`70054` 63**
- `70054`: `JSR 49370.L` (함수 진입(외부 BRA 72e8a/735a4); U11 경계)
- `7005a`: `TST.B D0; BNE.W 7006e`
- `70060`: `MOVE.B #ff,86(A6); MOVEA.W #0,A0; BRA.W 7010c`
- `7006e`: `CMPI.B #1,D0; BNE.W 70084`
- `70076`: `MOVE.B #0,86(A6); LEA.L -7348(A5),A0; BRA.W 700ea`
- `70084`: `CMPI.B #2,D0; BNE.W 7009a`
- `7008c`: `MOVE.B #1,86(A6); LEA.L -7258(A5),A0; BRA.W 700ea`
- `7009a`: `LEA.L -7348(A5),A0; LEA.L -7258(A5),A1; MOVE.W 42(A0),D0; MOVE.W 42(A1),D1; MOVE.W 42(A6),D2; SUB.W D2,D0; BPL.W 700b6`
- `700b4`: `NEG.W D0` (→`700b6`)
- `700b6`: `SUB.W D2,D1; BPL.W 700be`
- `700bc`: `NEG.W D1` (→`700be`)
- `700be`: `TST.B 86(A6); BNE.W 700ce`
- `700c6`: `LSR.W #2,D0; LSL.W #4,D1; BRA.W 700d2`
- `700ce`: `LSL.W #4,D0; LSR.W #2,D1` (→`700d2`)
- `700d2`: `ADD.W D1,D0; JSR 49a84.L` (stage_event_ops RNG)
- `700da`: `MOVEQ #0,D7; CMP.W D0,D1; BCC.W 700e6`
- `700e2`: `MOVEA.L A1,A0; MOVEQ #1,D7` (→`700e6`)
- `700e6`: `MOVE.B D7,86(A6)` (→`700ea`)
- `700ea`: `CLR.B 82(A6); MOVE.W 42(A0),D0; CMP.W 42(A6),D0; SPL.B D0; BTST.B #0,15(A6); SNE.B D1; EOR.B D0,D1; BMI.W 7010c`
- `70106`: `BSET.B #0,82(A6)` (→`7010c`)
- `7010c`: `MOVE.W 78(A6),D0; BEQ.W 7011a`
- `70114`: `SUBQ.W #1,D0; MOVE.W D0,78(A6)` (→`7011a`)
- `7011a`: `LEA.L c8750.L,A0; JSR 490ba.L`
- `70126`: `MOVE.W D0,D1; JSR 49a58.L` (stage_area RNG)
- `7012e`: `MOVE.W D0,D7; ANDI.W #ff,D0; CMP.W D1,D0; BCC.W 70172`
- `7013a`: `LSR.W #8,D7; CMP.W D1,D7; BCC.W 70172`
- `70142`: `BSET.B #1,82(A6); MOVE.W #30,D0; BTST.B #0,15(A6); BNE.W 70158`
- `70156`: `NEG.W D0` (→`70158`)
- `70158`: `ADD.W 42(A6),D0; MOVE.W 46(A6),D1; MOVE.W D0,-(A7); MOVE.W D1,-(A7); JSR 4bc04.L` (경계)
- `7016a`: `MOVE.W (A7)+,D3; MOVE.W (A7)+,D2; BSR.W 70036` (경계)
- `70172`: `MOVE.W 76(A6),D0; BEQ.W 701b8`
- `7017a`: `CMPI.W #1,D0; BNE.W 70192`
- `70182`: `BSET.B #4,61(A6); BSET.B #5,61(A6); BRA.W 701b8`
- `70192`: `JSR 49a58.L` (stage_area RNG)
- `70198`: `BPL.W 701ac` (N 소비: 49a58의 `SUB.W D0,(A3)` 결과, live (A3) WORD bit 15로 재계산)
- `7019c`: `BCLR.B #5,61(A6); BSET.B #4,61(A6); BRA.W 701b8`
- `701ac`: `BSET.B #5,61(A6); BCLR.B #4,61(A6)` (→`701b8`)
- `701b8`: `MOVE.W 7c(A6),D0; BEQ.W 701c6`
- `701c0`: `SUBQ.W #1,D0; MOVE.W D0,7c(A6)` (→`701c6`)
- `701c6`: `JSR 49a58.L` (stage_area RNG)
- `701cc`: `SMI.B 83(A6); BCLR.B #3,82(A6); MOVE.W 42(A6),D0; SUBI.W #20,D0; CMPI.W #100,D0; BCC.W 701f8` (N 소비: 49a58의 `SUB.W D0,(A3)` 결과, live (A3) WORD bit 15로 재계산)
- `701e6`: `MOVE.W 46(A6),D0; SUBI.W #20,D0; CMPI.W #c0,D0; BSET.B #3,82(A6)` (→`701f8`)
- `701f8`: `MOVE.W 9a(A6),D7; BEQ.W 7020c`
- `70200`: `ASR.W #6,D7; BNE.W 70208`
- `70206`: `MOVEQ #1,D7` (→`70208`)
- `70208`: `SUB.W D7,9a(A6)` (→`7020c`)
- `7020c`: `MOVEQ #0,D0; MOVE.W #20,D1; MOVE.W #10,D2; MOVE.W #24,D3; BTST.B #0,15(A6); BNE.W 70226`
- `70224`: `NEG.W D2` (→`70226`)
- `70226`: `JSR 4c29a.L` (경계)
- `7022c`: `BTST.B #3,D6; BEQ.W 7023e`
- `70234`: `BSET.B #1,82(A6); BRA.W 7025a`
- `7023e`: `BTST.B #6,D6; BEQ.W 7024c`
- `70246`: `BSET.B #4,82(A6)` (→`7024c`)
- `7024c`: `BTST.B #2,D6; BEQ.W 7025a`
- `70254`: `BSET.B #5,82(A6)` (→`7025a`)
- `7025a`: `MOVE.W #8,D0; BTST.B #0,15(A6); BNE.W 7026a`
- `70268`: `NEG.W D0` (→`7026a`)
- `7026a`: `JSR 4c1de.L` (경계)
- `70270`: `BTST.B #2,D6; BEQ.W 7027e`
- `70278`: `BSET.B #2,82(A6)` (→`7027e`)
- `7027e`: `BTST.B #0,D6; BNE.W 7028c`
- `70286`: `BSET.B #7,82(A6)` (→`7028c`)
- `7028c`: `RTS`

**`70418` 34**
- `70418`: `JSR ea5f0.L` (함수 진입; 경계(U13))
- `7041e`: `LEA.L c868e.L,A0; JSR 490ba.L`
- `7042a`: `MOVE.W 78(A6),D1; BEQ.W 70434`
- `70432`: `MULU.W D1,D0` (→`70434`)
- `70434`: `LSR.L #8,D0; MOVE.W D0,78(A6); LEA.L c85cc.L,A0; JSR 490ba.L`
- `70446`: `MOVE.W 7a(A6),D1; BNE.W 70452`
- `7044e`: `MOVE.W #1e,D1` (→`70452`)
- `70452`: `MULU.W D1,D0; LSR.L #8,D0; MOVE.W D0,7a(A6); JSR 49a58.L` (stage_area RNG)
- `70460`: `ANDI.W #7,D0; ADD.W D0,7a(A6); TST.W 7c(A6); BNE.W 70476`
- `70470`: `MOVE.W #5a,7c(A6)` (→`70476`)
- `70476`: `JSR 8ff4.L` (cleanup)
- `7047c`: `TST.W 9c(A6); BNE.W 7049a`
- `70484`: `MOVE.W #33,D0; MOVE.W #3,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `70496`: `BRA.W 704ac`
- `7049a`: `MOVE.W #34,D0; MOVE.W #3,D1; MOVE.B #0,D2; JSR c6a96.L` (U05)
- `704ac`: `MOVE.W #8820,68(A6); MOVE.W #8820,1e(A6); MOVE.W 7e(A6),D0; BEQ.W 704fa`
- `704c0`: `CMPI.W #e,D0; BEQ.W 704fa`
- `704c8`: `CMPI.W #f,D0; BEQ.W 704fa`
- `704d0`: `CMPI.W #3,D0; BEQ.W 704fa`
- `704d8`: `CMPI.W #6,D0; BEQ.W 704fa`
- `704e0`: `CMPI.W #8,D0; BEQ.W 704fa`
- `704e8`: `CMPI.W #a,D0; BEQ.W 704fa`
- `704f0`: `JSR 4c0ac.L`
- `704f6`: `BRA.W 70512`
- `704fa`: `MOVEQ #ff,D0; JSR 4c2cc.L` (경계, C 반환)
- `70502`: `BCC.W 7050c` (carry 소비: 4c2cc 반환 C)
- `70506`: `BSET.B #7,15(A6)` (→`7050c`)
- `7050c`: `SWAP D7; MOVE.B D7,6e(A6)` (→`70512`)
- `70512`: `JSR 43e34.L` (cleanup)
- `70518`: `CMPI.W #A0,42(A6); BPL.W 70528`
- `70522`: `BSET.B #0,15(A6)` (→`70528`)
- `70528`: `MOVE.W 42(A6),D0; SUBI.W #A0,D0; ASR.W #2,D0; ADDI.W #A0,D0; MOVE.W D0,8e(A6); JSR 49a58.L` (stage_area RNG)
- `70540`: `MOVE.W D0,90(A6); BSR.W 6feb4` (경계)
- `70548`: `BRA.W 70054`

(각 묶음 줄의 수는 그 묶음의 block 수다: 3+35+3+13+5+6+63+34=162.)

## 구현 범위와 규약

- routing 10 범위(위 표). 짝수 PC 826개 중 block 시작 162, 내부 664. 내부 PC 직접 진입은 `unsupported animation objects u12 PC`다. TRAP·문자열 바이트, 경계 callee 9개와 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 4개**: `490a4` `490b0`(`SCS`, `289e` 반환 C; readiness `289e`의 CMPI/ORI CCR), `4c0c6`(`46d72` 반환 C), `70502`(경계 `4c2cc` 반환 C; 경계가 실행되기 전에는 선언 C로만 진입). Unknown이면 `objects u12 caller requires known carry`.
- **known carry 생산 block 4개**: `1abda`(CMPI의 C: `D1.W`≠`ffff`이면 Set, 같으면 Clear), `1abec`(ANDI CCR Clear), `46eda`(MOVE Clear), `46ee6`(ORI CCR Set).
- **FLOW_ONLY 47개**(C 보존, 소비 `490a4` `4c0c6` `70502`와 N 소비 `70198` 포함): `1abea` `46dac` `46e08` `46e66` `46e6a` `46e80` `46ea8` `46eea` `490a4` `492c6` `492c8` `4c0ac` `4c0c6` `4c0e8` `70054` `70106` `7011a` `70182` `70192` `70198` `7019c` `701ac` `701c6` `70226` `7022c` `70234` `7023e` `70246` `7024c` `70254` `7026a` `70270` `70278` `7027e` `70286` `7028c` `70418` `7041e` `70476` `70496` `704f0` `704f6` `70502` `70506` `70512` `70522` `70548`. `490b0`은 C를 소비하고 끝에서 Unknown이다(carry 보존 목록에는 있으나 FLOW_ONLY는 아니다). 그 밖 110개(MOVE/MOVEQ/CLR/TST/CMP/CMPA/CMPI/ADD/SUB/ADDI/SUBI/ANDI/AND/ORI/EOR/NEG/SWAP/LSL/LSR/ASR/MULU/Scc+MOVE block, SUBQ/ADDQ An block `46db6` `46eba`, ADDA block `49140` `49176`, 스택 MOVE block)은 Unknown이다.
- 반환 Z·N: RTS를 넘는 flag 소비는 위 C 4개와 N 2개(결정 4)뿐이다. 그 밖 소비는 같은 block의 flag 생산 뒤다.
- 루프: `46d72` 탐색 루프(`46dc0`→…→`46ea8 BSR 469ae`→`46eb2 BNE 46dc0`, U09 목록이 0을 돌려주면 끝)와 그 안 `46e78 BCS 46e12`(지역 LONG `(A7)`이 `54d0` 아래인 동안 `D3`만큼 빼며 반복). 상한은 호출자 자료(목록 길이, `54d0`)에 달려 있고 실행부 block 상한(1,000,000)이 유한성을 보장한다.
- I/O: `49140`/`49196`의 PVC 쓰기는 기존 `am_write`(port 기록, `pvc_effects`, bank 갱신)로 한다. 홀수 주소 WORD/LONG, work RAM 밖 쓰기, 미해결 ROM·bank 읽기는 기존 checked 오류다.

## 의존

- [F] U12 → U11: `46e08`/`46e6a BSR 45176`, `70054 JSR 49370`. U11 병합 전에는 경계에서 멈춘다.
- [F] U12 → U08/U08a/U08b/U09: `447be`(`46dc0` `46e12`), `4483a`(`46df4` `46e66`), `461ec`(`46ed0`), `4bc44`(`4c0ac`), `469a0`(`46d72`), `469ae`(`46dac` `46ea8`).
- [F] 다른 단위 → U12: U08b `4bf98 JSR 492c8`, U10 `492c8` 7곳(그 경계가 실행부로 바뀐다), `4c0ac` 외부 호출자 83곳, `490ba` 외부 호출자 348곳, `1abda` 14곳(범위 문서 U13/U18의 `ea5..` 등), `46d72` 3곳(`4c128` `4c182` `4c2e8`).
- [I] 자연 frame pass에서 `46d72`는 `45176`(U11)에서, `70054`는 `49370`(U11)에서, `70418`은 `ea5f0`에서 바로 멈춘다. 그래서 U12만으로 새 완주 seed는 기대하지 않는다(범위 문서와 같음). U10 `bb206` 등의 `492c8`은 U12로 실행된다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 162 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 block 값, 그 밖 Unknown), 소비 block 4개의 Unknown 오류, zero-step, 내부 664 PC 정확한 오류, 홀수 PC. TRAP 3개와 경계 callee 9개는 그 PC에서 stop이 성공하는 것만 확인하고, rollback·`unsupported animation machine PC` 확인은 F4 단위 밖 미연결 PC(`5f6xx..5ffxx`)로만 한다(메인의 F4 단위 test 경계 관례). 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력과 합성 fixed 표 `48f98..49098`; ROM 자료는 test에 넣지 않음)로 비교한다.
- 실제 ROM 차분: 각 함수 진입과 경계 사이 구간을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`, seed 58·59는 `animation_machine_pvc_banks_native`)과 RNG 초기화 400 frame 차분(`verify_animation_machine_frame_pass_rng.py`): 기준(`58898ef`) 일치 수가 모두 그대로 일치해야 한다. 기준: F2 일치 pass 10,016·node 75,072(142 seed, 불일치 0), RNG 일치 pass 22,000·node 146,944(불일치 0, 분류 "cpp-error-other" 15 seed `0 1 20 21 42 43 127~135`).

## 미확인·범위 밖

1. [I] `46d72`는 A0 노드 기준 위치(`D0`/`D1`, 16.16)에서 U09 목록(`469a0`/`469ae`)의 노드마다 상대 좌표로 지형(`447be` `4483a` `45176`)을 찾고 가장 가까운 거리(`54d0`)와 그 지형 값(`54d8` `54b2`→`54dc`)을 고르는 탐색으로 보인다. `174` `178` `17c` `160`은 지형 code로 보이나 의미는 미확인이다.
2. [I] `49098`은 두 player 노드(`100cb8` `100da8`)가 모두 활성(`289e` C=Set이면 비활성 아님)이면 `D7`=1을 돌려준다. `490ba`는 난이도 BYTE `10fd8b`(BYTE `100012`≠2이면 3)와 그 `D7`로 호출자 표에서 값을 고른다(`48f98`은 1 bit 수 표). 게임 의미는 미확인이다.
3. [I] `70418`/`70054`는 RNG·난이도 표로 타이머(`78` `7a` `7c`)를 정하고 player를 고르고(`49370`) 방향 bit(`82` `15` `61`)를 갱신하는 적 AI 갱신으로 보인다. 미확인이다.
4. [U] 경계 callee 9개와 그 C 반환 의미는 U12 밖이다.
5. [U] `701e6`의 `CMPI.W #c0,D0` 결과는 쓰이지 않는다(뒤 `BSET`은 Z만 바꾸고 다음 block이 `MOVE`로 덮는다). 원본 그대로 옮긴다.

작업자 scratch: 세션 scratchpad `f4u12/`(`u12.py` block·범위·SHA 계산, `classify.py` carry 분류, `doclist.py` 목록, `dis_u12.py`, `reach.py`, `refs.py`, `nextins.py`; 저장소 밖).
