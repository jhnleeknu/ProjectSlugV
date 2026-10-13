# 객체 callback F4 N22(첫 부분 N22a): `3d228` stage event callback 계열 — `3df44` 자식 생성(`41fe6` `3e0f6`), `3d280`/`3d32c` 상태, N23이 부르는 `1bf02` `1bfb4`, code pointer `3d3de` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N22 행(211 block, `1bf02..1c012` `3d228..3d526` `3d7e8..3d8de` `3da72..3e250` `41fe6..420be`, callback `3d228` `3d280` `3d32c` `3e0f6` `3e1ce` `41fe6`, 경계 18(`3d8de`~`4da50`), 간접 `3e1b6`, 표 `3d8a4`:9, bank 2, 미실행 설치 9(+142), 새 seed 없음(N23 seed 38 39의 전제))과 메인 결정 1·2(이름 `objects-n22`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 단위 형식과 규약은 N21 계약(`animation-machine-objects-n21-contract.md`, SHA256 `eb4a38831a3ca58fee36a764c18bab57f4f8256c6e0b2ada13912659c9a2943c`)을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 분기를 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 설치·진입은 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. 기존 실행부의 두 번째 진입 누락은 scratch patch와 결정으로 보고한다. DIV 0 제수는 단위 checked 오류(N22a에는 DIV가 없다).
- 계산 점프 표는 정적으로 묶고 전부 전사한다(못 하면 F1 결정 3).
- 설치·표 포함 뒤 ~220 block을 넘으면 나누고, N23 seed가 쓰는 부분을 먼저 구현한다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치·`MOVEA.L #imm,A0`+`JSR 28ae` 자식, 참조된 code pointer)로 정한다. Unicorn TB 분할은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N21 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDI`/`ANDI`/`SUBQ`/`NEG`/`EXT`/`LSR`/`AND`/`CLR` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`BTST`/`BSET`/`BCLR`/`Scc`/`ST`)만인 block과 callee C를 소비하는 Bcc/Scc block은 FLOW_ONLY다. `ORI`/`ANDI` CCR은 known Set/Clear 생산이다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N22 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기(`2001a0` `2000b8`)는 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n22`(HEAD `10b3c2d` = N21까지 통합, `engine/src/animation_machine.cpp` SHA256 `36cb03c8e257208e0685cdb93a071867920bba256320f2dc2e1612c8ee506da0`, routing 규칙 78개, `engine/src/animation_machine_interpreter.cpp` SHA256 `bd2bffb36ccf99cc18fe141949335e6ef1e07f7255cb1f137e387d0451ebac05`)을 참조했다. 재범위 N22 행 5 범위의 짝수 PC와 N22a 범위 양옆 PC는 기존 routing에 없다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n22/n22.py`(정적 디코드)와 `n22split.py`(분할)가 원본 opcode에서 독립 계산했다(`startsA.txt`, `startsB.txt`).

## 요약

- [F] **재범위 N22 행의 정적 closure는 304 block**이다(진입 6 + 참조 code pointer 3 + LONG 표 대상 2에서 분기·설치·`28ae` 자식·BRA.W 표 `3d8a4` 9 entry를 끝까지 따라감; 범위 안 미참조 코드 제외). 재범위 211은 400 frame 안에 실행되는 함수 본문만 센 값이고, 미실행 설치 사슬(+142 추정)과 미실행 내부 callee(`3dcac` `3dcda` `3dd0e` `3dd30` `3dde4` `3de54` `3defa` `3df30` `3e0a8`, 재범위의 "경계 18" 중 9)는 빠져 있었다. 220을 넘으므로 메인 지시대로 나눈다(결정 1).
  - **N22a(이 계약, 151 block)** = 자연 seed(38 39 116 117)가 실행하는 함수(`1bf02` `1bfb4` `3d228`→`3df44`/`3de06`, 설치 `3d280` `3d32c` `3d3b2` `3d2b4`, `3dcf2`/`3dd6a`, `3de46`, 공유 꼬리 `3dbba`/`3dc24`, `3db62`, `28ae` 자식 `41fe6` `3e0f6`→`3e1c2`/`3e1ce`/`3e17a`/`3e130`, LONG 표 대상 `3e1ec`→`3e214`, code pointer `3d3de` `3e1e2` `3e22a`)의 정적 본문 전체. 코드 14 범위 1,756바이트, 396명령.
  - **N22b(다음 단위, 153 block)** = 나머지: 설치 값 `3d3f0`의 사슬(`3d41a` `3d470` `3d4e2`, `3d498` 계열), 범위 밖에서 설치되는 `3d7e8`(`3d7e2`)·`3da72`(`3da6c`)와 그 사슬(`3d880`, BRA.W 표 `3d8a4`, `3dad0`, `28ae` 자식 `3db68`→`3dba2`, `3dbbe`), 미실행 내부 callee 9개. 12 범위 `3d3f0..3d526` `3d7e8..3d8de` `3da72..3db62` `3db68..3dbba` `3dbbe..3dc24` `3dcac..3dcf2` `3dd0e..3dd42` `3dde4..3de06` `3de54..3def2` `3defa..3df1a` `3df1e..3df44` `3e03e..3e0aa`(짝수 PC 736).
- [F] N22a 진입:
  - stage event callback(고정 ROM LONG 표): `3d228`(`e8ce8` `e9058`).
  - `28ae` 자식 callback(`MOVEA.L #imm,A0; JSR 28ae`): `41fe6`(`3df82` `3dfd2`; 범위 밖 `2b738` `2b77a` `2b820` `2b862` `3194e` `33b7e` `40aba`도 LONG 참조), `3e0f6`(`3e028`).
  - N23 범위에서 부르는 진입: `1bf02`(`4d2d4`/`4d2e4 LEA 1bf02.l,A1` → `4d38a JSR (A1)`), `1bfb4`(`4d766 JSR 1bfb4.l`).
  - 범위 안 설치(결정 3): `3d280`(`3d22c`), `3d32c`(`3d326`, fall-through), `3d3b2`(`3d3ac`, fall-through), `3d2b4`(`3d3be`), `3db62`(`3d3d4`; 분기 대상이기도 함), `3e1ce`(`3e1c8`, fall-through), `3e214`(`3e20e`, fall-through).
  - 참조된 code pointer: `3d3de`(`3d310 LEA 3d3de(PC),A0` → `4da50`이 자식 `4db42`의 LONG `7a`에 저장 → N23 `4dbb0 JSR (A1)`), `3e1e2`·`3e22a`(`3e1dc`/`3e222 LEA x(PC),A0; BRA 3e17a` → `3e1b6 JMP (A0)`의 계속 주소), `3e1c2`·`3e1ec`(LONG 표 `3e1ba`의 entry 0·1, `3e1a0 MOVEA.L 3e1ba(PC,D0.W),A0` → `JMP (A0)`).
  - 범위 밖 참조가 있는 시작은 위 진입뿐이다(scratch `n22xref.py`; 고정 ROM 절대 LONG, `Bcc`/`BRA`/`BSR`, `JSR`/`JMP`/`LEA`/`PEA d16(PC)` 전수 검사. `3d32e` `3d35c` `3d3e2` `3dadc` `3de47` `3df00` `3e000` `3e082` `3e188` `3e20c` `3e240` `42000` 등의 겉보기 참조는 자료·명령 확장어·다른 코드의 우연 일치다; `3d35c`는 `3cf1a`의 자료 `6000 0440`이다).
- [F] **경계(실행부 없음, 현재 routing 밖)**: N23 `484b4`(`1bf04`) `4d2d4`(`3d346`) `4d508`(`3d374`) `4d766`(`3dc58`), N35 범위 `4da50`(`3d314`), N22b `3dcac`(`3d354`) `3defa`(`3dc76`). `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee**: `288c`(stage_event_ops), `289e`(readiness), `28ae` `2a00`(fade_card), `8ebe`(U02), `8ff4` `43e04` `43e34`(cleanup), `ce02` `43ea4`(U04), `1aa7e` `4b54e`(U01), `1ab02`(U05), `491c4`(U17), `49290`(U08), `496c2`(U11), `49f8c` `49f96` `49fc6` `49fca`(interpreter), `4b82e`(N03), `4d81c`(stage_area). **`49fca`는 interpreter routing 범위(`49f8c..4a46c`) 안이지만 실행부에 case가 없다**(결정 2).
- [F] **범위 밖 설치 값(노드 LONG에 저장만)**: `3d3f0`(`3d37a`, N22b), `3d982`(`3dc36`, `3d8de..3da72` 다른 미연결 함수), `420be`(`420b6`, N23). 실행 PC가 아니다.
- [F] **carry**(아래 "carry" 절): 소비 block 16개, known 생산 6개(`ORI` Set 4, `TST.B` Clear 1, `LSR.B` 계산 1), FLOW_ONLY 69개(소비 16 포함), Unknown 76개. 69 + 6 + 76 = 151.
- [F] 스택: JSR/BSR 복귀 LONG, `1bf02 MOVE.L A0,-(A7)`/`1bf5c`·`1bf66 MOVEA.L (A7)+,A0`, `3dd02 SCS.B -(A7)`/`3dd08 MOVE.B (A7)+,D0`, `3dd6a MOVE.W 1e(A6),-(A7); MOVE.B 14(A6),-(A7)`/`3ddd0 MOVE.B (A7)+,14(A6); MOVE.W (A7)+,1e(A6)`(BYTE는 A7 ±2, 상위 BYTE 주소).
- [F] 미해독·PC 상대 BRA.W 점프 표(N22a 안)·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx·I/O port 쓰기·bank 변경은 없다. 레지스터 간접 점프는 `3e1b6 JMP (A0)` 하나다(live target).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n22seen.py`): RNG 기록에서 seed 38 39 116 117, base 기록에서 116 117만 N22 범위 PC를 실행한다(N22b PC는 0). callback 실행 수(RNG, seed 38): `3d228` 1, `3d280` 1, `3d32c` 84, `3e0f6` 1, `3e1ce` 85, `41fe6` 2(116 117은 `3d32c` 80, `3e1ce` 81, `41fe6` 5).
- [F] **기준(`10b3c2d`)에서 이 seed들은 N22에 닿기 전에 멈춘다**: 38 39는 frame 0 callback `7086a` 안의 N23 `c3a7c`, 116 117은 frame 0 `38ba0`(N31). 따라서 N22a만으로는 frame pass 차분의 자연 경로가 바뀌지 않는다(새 완주 seed 없음; 재범위 "새 seed - / -"와 같다). 자연 상태는 따로 잡아 비교한다(검증 기록).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **N22 = N22a(151) + N22b(153) 분할, 이번 구현은 N22a.** [F] 재범위 N22 행을 메인 결정 2(범위 안 설치 포함)와 결정 3 관례로 정적 디코드하면 304 block이다. 메인 지시("~220을 넘으면 나누고 N23 seed가 쓰는 부분을 먼저")대로 자연 seed가 실행하는 함수 본문 전체를 N22a로 둔다. 분할 규칙: 위 N22a 진입에서 분기·fall-through·범위 안 설치·`28ae` 자식·code pointer를 따라가되, 자연 seed가 실행하지 않는 함수 진입(`3dcac` `3dcda` `3dd0e` `3dd30` `3dde4` `3de54` `3defa` `3df30` `3e0a8` `3e03e` `3d7e8` `3da72`)과 설치 값 `3d3f0`에서 멈춘다. N22b 코드가 N22a 범위 안 PC로 점프하는 곳은 모두 N22a block 시작이다(`3dbba` `3dc24` `3db62` `3dcf2` `3de06` `3de46` `3e130` 등; scratch 검사에서 N22a 범위 안의 추가 시작 0). 이름은 U20/U20b·U15/U15b 관례대로 N22a를 `objects-n22`(파일·함수·오류 문자열 그대로), 다음 부분을 `objects-n22b`로 권고한다.
2. **interpreter `49fca` 두 번째 진입 누락.** [F] `3ddaa`가 `LEA 8a(A6),A0; JSR 49fca.l`로 interpreter `49fc6`(`LEA 26(A6),A0`; `49fca`부터 bank 0 쓰기 3개 → `(A0)` 애니메이션 block 실행)의 두 번째 진입을 부른다(호출자 A0 = `A6+8a`). `49fca`는 interpreter routing 범위 안이지만 `animation_interpreter_block`에 `case 0x49fca`가 없어 `unsupported animation interpreter PC`(interpreter `default`)가 난다. 자연 seed 38 39 116 117이 `3dcf2`→`3dd6a`→`49fca`를 매 frame 실행한다(`3ddc0` TB 시작 기록). 이 단위는 interpreter를 고치지 않는다. scratch patch `ms5-scratch/n22/patch/interpreter-49fca.patch`(`case 0x49fca:`를 `0x49f96`과 같은 꼴로: A0 = 호출자 값, 나머지는 `49fc6` 본문과 같음)를 제안한다. [I] 메인이 받아들이면 interpreter 소유 단위의 계약 갱신이 필요하다.
3. **LONG 표 `3e1ba` + `JMP (A0)`(live target).** [F] `3e1a0`은 `MOVE.B D0,9d(A6); ADD.W D0,D0; ADD.W D0,D0; MOVEA.L 3e1ba(PC,D0.W),A0`로 code pointer LONG을 읽고 `3e1b6 JMP (A0)`로 간다. 색인 `D0.B`는 부모 노드 BYTE `9d`(`MOVEQ #0` 뒤 `MOVE.B`, `BMI` 제외로 0..`7f`)라 정적 상한은 128 entry지만 표 자료는 2 LONG(`3e1c2` `3e1ec`)뿐이고 그 뒤는 코드 바이트다. BRA.W 점프 표가 아니라 자료 LONG 읽기 + 레지스터 간접 점프이므로 전사하지 않고 live bus 읽기와 live target routing(`JMP (A0)` → A0)으로 둔다. 범위 안의 두 LONG 대상만 block 시작이다. 색인 2 이상은 코드 바이트를 주소로 읽어 그 주소의 routing 결과(대개 `unsupported animation machine PC` 또는 `unaligned animation machine PC`)가 된다. [I] 원본도 부모 `9d` ≤ 1을 전제로 한다(`3e192`의 bit 표 `3e1b8` = `01 02`). 메인이 BRA.W 표와 같은 "전사" 규칙을 요구하면 F1 결정 3 대상이다.
4. **known C 생산.** [F] `1bf5c` `3d3ea` `3df96` `3dfe6`(`ORI.B #1,CCR`) Set, `3d3de`(`TST.B` 뒤 `BEQ`; 두 출구 모두 C = 0) Clear, `3dd08`(`MOVE.B (A7)+,D0; LSR.B #1,D0; RTS`) 계산 C = 꺼낸 BYTE의 bit 0(`3dd02 SCS.B`가 넣은 `49fc6`의 C). 실제 ROM 소비자: `3d3de`/`3d3ea` → N23 `4dbb2 BCS.W 4dbd6`, `3dd08` → `3d3ba BCC.W 3d3c4`(N22a)·`3d478`(N22b). `1bf5c`의 소비자는 ROM에 없다(`4d38a JSR (A1)` 뒤 `TST.B D0`). `3df96`/`3dfe6`의 C는 `3dfc0`/`3e010`(`MOVE`)이 지운다. [F] native 확인: 생산 block 진입, 복귀 LONG = 실제 소비자(`4dbb2` 또는 `3d3ba`)로 두고 native 분기 결과로 C를 확인했다(검증 기록). `1bf66 MOVEQ #ff`·`1c00a MOVEQ`·`3ddd0 SNE+LSR`는 소비자가 없어 Unknown이다(`4d38c TST.B`, `4d77a ADD.B`, `3dd08 MOVE.B`가 덮음).
5. **seed 38 39는 N23 말고 `4da50`도 필요.** [F] 재범위 표는 38 39의 필요 단위를 "N03 N04 N22 N23"으로 적었지만 seed 38 실행 TB에 `4da50` `4da66`(재범위 N35 `4da4a..4da74`)가 있다(`3d314 JSR 4da50`). N23만 더해서는 38 39가 `4da50`에서 멈춘다. [I] N23 작업 때 `4da4a..4da74`(진입 `4da4a` `4da50`)를 N23에 옮기거나 N35를 먼저 하길 권고한다.
6. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n22.cpp`의 `animation_objects_n22_block`. 오류는 `unsupported animation objects n22 PC`(내부 PC), `objects n22 caller requires known carry`(소비 16 block). 메인 지시와 같다.
7. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`의 16진 토큰 중 N22a 범위 짝수 PC와 같은 것은 자료값뿐이다(`u08b` 레지스터 `0x3e022`, `n07`/`u10`/`u15b` 값 `0x1c000`, `u11` 레지스터 `0x1bf24`, `tools/pack_animation_fields.py` `CALLER = 0x3d2e2`(분석 주석 값)). 경계·rollback 탐침으로 쓰는 곳은 없다.
8. **범위 안 미참조 코드.** [F] N22a hull 안의 `1bf6c..1bfb4`(함수 `1bf6c` `1bf80` `1bf94`; 범위 밖 LONG 참조 `2f792` `2d92e` `4ea20` 등은 다른 단위 몫)와 `3d234..3d280`(`3d234` `3d270`)은 N22a 진입에서 닿지 않아 routing하지 않는다(메인 지시). `3dd42..3dd6a`(LONG 표, N22b `3dd30`이 읽음), `3def2..3defa`(N22b `3de54`의 자료), `3e1b8..3e1c2`(bit 표 + LONG 표)는 자료다.

## 원본 바이트 근거

[F] N22a 코드 14 범위 합계 1,756바이트(짝수 PC 878개, 시작 151, 내부 727). 범위 순서로 이어 붙인 SHA256 `00fb168a6700c25504df3e47c863a2ab28c50fa98433ac1c2970d87b9fba0110`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `1bf02..1bf6c` | 106 | `4f76e4f3795412b20e24ffd884d32143f0fa8a546e8a549a986a42062df39317` | 13 |
| `1bfb4..1c012` | 94 | `d461408792ed688a738d370d9705647a7cc0b9ae36c30870128de76e503c5a19` | 12 |
| `3d228..3d234` | 12 | `27ebbdd97d3121482a984870b86992ed0535908de66ab14083b741a809b56918` | 2 |
| `3d280..3d3f0` | 368 | `eded7f4021b7afc2e6b19bf40f393f98f7612db937e9d084246679e7bd87ef38` | 35 |
| `3db62..3db68` | 6 | `2738adf81304c5fbbc9eedf6248d6b2d7cfa132bc35dfb5e458d0bbd9e12d3f9` | 1 |
| `3dbba..3dbbe` | 4 | `1c6e82c19328d0037519fc7b60c5ec861ce36b667a354ad1c919b97115a6b5f1` | 1 |
| `3dc24..3dcac` | 136 | `6d6eeab6c29c871031bdcf8e12c514a87ffc58fe3f99d9e005b5da19cdb14096` | 15 |
| `3dcf2..3dd0e` | 28 | `a5f365aa08a650ef8f134ba4b201de0927dd89029c68ed7f6704e08c72af3f52` | 4 |
| `3dd6a..3dde4` | 122 | `329913515f5566b8f681f3c81b246ed2b418f2650acbda83a5c5a8c829b1cd59` | 7 |
| `3de06..3de54` | 78 | `640e39eceeef282830a1e7b942b800658cf1e04f9ddd4440faf4f2bca5d2881b` | 8 |
| `3df44..3e03e` | 250 | `206f9ad903c7b7845c367b971953e9be85e0bf007261a8f49970d8e517b7b3c5` | 11 |
| `3e0f6..3e1b8` | 194 | `f74c384a4c22efc1b6fbd9d8cb8b402fdaf62c88337d00e6958f7ff56af9a7cc` | 12 |
| `3e1c2..3e250` | 142 | `a590365d616b5c69e1f64cb3e5b713203c44fc71f08529198baa20fda4d9b168` | 19 |
| `41fe6..420be` | 216 | `a14b2bfc477b488425a40eb8938eb873af7ac1cbfcd986debfd6a80c2fee10ca` | 11 |

- [F] 범위 이웃: `1bf02` 앞(`1bef8..1bf02` BYTE 표 `01`×9 `00`), `1bf6c..1bfb4`(미참조 함수 셋, 결정 8), `1c012..`(다른 함수), `3d234..3d280`(미참조 함수 둘), `3d3f0..3d526`·`3da72..3db62`·`3db68..3dbba`·`3dbbe..3dc24`·`3dcac..3dcf2`·`3dd0e..3dd6a`·`3dde4..3de06`·`3de54..3df44`·`3e03e..3e0f6`(N22b, 자료 `3dd42..3dd6a` `3def2..3defa`, 미참조 `3df1a` `3e0aa..3e0f6` 포함), `3e1b8..3e1c2`(자료: bit 표 `01 02`, LONG `0003e1c2` `0003e1ec`), `420be..`(N23).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "Set/Clear 생산", "계산 C 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)·`(An,Dn.W)`는 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVE.W #x,D0`·`ANDI.W #1,D0`·`ADD.W D0,D0`·`NEG.W D0`·`ADDI.W #12,D1`·`ANDI.W #ff,D1`·`EXT.W`는 하위 WORD만, `MOVE.B`·`SNE.B`·`SCS.B`·`LSR.B`는 하위 BYTE만; `MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`는 LONG 전체). `LEA 0.w,A0`은 A0 = 0이다. 모든 비교·`TST`와 그 Bcc는 같은 block 안에 있다.


**`1bf02`(N23 `4d36e`의 `JSR (A1)` 대상, A1 = `1bf02`를 `4d2d4`/`4d2e4`가 넘김) 13**
- `1bf02`: `MOVE.L a0, -(a7); JSR 484b4.l`
- `1bf0a`: `BCC.W 1bf66` (→`1bf0e`) — C 소비
- `1bf0e`: `TST.B d0; BNE.W 1bf1e` (→`1bf14`)
- `1bf14`: `LEA.L 100cb8.l, a0; BRA.W 1bf24` — FLOW
- `1bf1e`: `LEA.L 100da8.l, a0` (→`1bf24`) — FLOW
- `1bf24`: `JSR 289e.l` — FLOW
- `1bf2a`: `BCC.W 1bf66` (→`1bf2e`) — C 소비
- `1bf2e`: `BTST.B #7, 61(a0); BNE.W 1bf66` (→`1bf38`) — FLOW
- `1bf38`: `LEA.L 1bef8(pc), a1; MOVEQ #0, d0; MOVE.B 9f(a0), d0; TST.B (a1, d0.w); BEQ.W 1bf66` (→`1bf4a`)
- `1bf4a`: `TST.L 3a(a0); BPL.W 1bf66` (→`1bf52`)
- `1bf52`: `BTST.B #7, 15(a0); BNE.W 1bf66` (→`1bf5c`) — FLOW
- `1bf5c`: `MOVEQ #0, d0; MOVEA.L (a7)+, a0; ORI.B #1, ccr; RTS ` — Set 생산
- `1bf66`: `MOVEA.L (a7)+, a0; MOVEQ #ff, d0; RTS `

**`1bfb4`(N23 `4d766 JSR 1bfb4.l`) 12**
- `1bfb4`: `ANDI.W #1, d0; BNE.W 1bfc6` (→`1bfbc`)
- `1bfbc`: `LEA.L 100cb8.l, a0; BRA.W 1bfcc` — FLOW
- `1bfc6`: `LEA.L 100da8.l, a0` (→`1bfcc`) — FLOW
- `1bfcc`: `JSR 289e.l` — FLOW
- `1bfd2`: `BCC.W 1c00a` (→`1bfd6`) — C 소비
- `1bfd6`: `BTST.B #7, 61(a0); BNE.W 1c00a` (→`1bfe0`) — FLOW
- `1bfe0`: `TST.W 90(a0); SNE.B d1; BTST.B #0, a8(a0); BEQ.W 1bff2` (→`1bff0`)
- `1bff0`: `MOVEQ #ff, d1` (→`1bff2`)
- `1bff2`: `MOVEQ #0, d3; BTST.B #2, a7(a0); SNE.B d2; BEQ.W 1c008` (→`1c000`)
- `1c000`: `BTST.B #6, a8(a0); SNE.B d3` (→`1c008`) — FLOW
- `1c008`: `RTS ` — FLOW
- `1c00a`: `MOVEQ #0, d1; MOVEQ #0, d2; MOVEQ #0, d3; RTS `

**stage event callback `3d228`(고정 ROM LONG `e8ce8` `e9058`; 설치 `3d280` → `3d2b4`/`3d32c`/`3d3b2`, 공유 꼬리 `3dbba`→`3dc24`) 34**
- `3d228`: `JSR 3df44(pc)` — FLOW
- `3d22c`: `MOVE.L #3d280, (a6); RTS `
- `3d280`: `MOVE.W #0, 68(a6); MOVE.W #0, 1e(a6); LEA.L 0.w, a0; JSR 4b82e.l`
- `3d296`: `MOVE.B #0, 9d(a6); JSR 3de06(pc)`
- `3d2a0`: `MOVE.B 1b(a6), 14(a6); MOVE.L #0, 80(a6); JSR 496c2.l`
- `3d2b4`: `TST.B a1(a6); BNE.W 3d388` (→`3d2bc`)
- `3d2bc`: `MOVE.W #0, 86(a6); MOVE.B #0, a0(a6); MOVE.B #0, a1(a6); MOVEA.L #3e754, a1; MOVE.W #100, d0; LEA.L 8a(a6), a0; JSR 49f96.l`
- `3d2e2`: `MOVEA.L #3e808, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3d2f2`: `BCLR.B #3, 15(a6); MOVE.L #0, 56(a6); MOVEQ #0, d0; MOVEQ #40, d1; BTST.B #0, 15(a6); BEQ.W 3d310` (→`3d30e`)
- `3d30e`: `NEG.W d0` (→`3d310`)
- `3d310`: `LEA.L 3d3de(pc), a0; JSR 4da50.l` — FLOW
- `3d31a`: `MOVE.B #0, 78(a6); MOVE.B #0, b3(a6); MOVE.L #3d32c, (a6)` (→`3d32c`)
- `3d32c`: `LEA.L 3f6f0.l, a0; JSR 1aa7e.l` — FLOW
- `3d338`: `BCS.W 3db62` (→`3d33c`) — C 소비
- `3d33c`: `JSR 3de46(pc)` — FLOW
- `3d340`: `LEA.L 3f708.l, a0; JSR 4d2d4.l` — FLOW
- `3d34c`: `BCC.W 3d380` (→`3d350`) — C 소비
- `3d350`: `MOVE.W d0, 84(a6); JSR 3dcac(pc)`
- `3d358`: `BCC.W 3d380` (→`3d35c`) — C 소비
- `3d35c`: `MOVE.W d0, 86(a6); MOVE.W 84(a6), d0; MOVE.B #12, d1; MOVE.B a5(a6), d2; MOVE.B a6(a6), d3; MOVE.W 54(a6), d4; JSR 4d508.l`
- `3d37a`: `MOVE.L #3d3f0, (a6)` (→`3d380`)
- `3d380`: `JSR 3dcf2(pc)` — FLOW
- `3d384`: `BRA.W 3dbba` — FLOW
- `3d388`: `MOVEA.L #3e754, a1; MOVE.W #100, d0; LEA.L 8a(a6), a0; JSR 49f96.l`
- `3d39c`: `MOVEA.L #3e92e, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3d3ac`: `MOVE.L #3d3b2, (a6)` (→`3d3b2`)
- `3d3b2`: `JSR 3de46(pc)` — FLOW
- `3d3b6`: `JSR 3dcf2(pc)` — FLOW
- `3d3ba`: `BCC.W 3d3c4` (→`3d3be`) — C 소비
- `3d3be`: `MOVE.L #3d2b4, (a6)` (→`3d3c4`)
- `3d3c4`: `LEA.L 3f6f0.l, a0; JSR 1ab02.l` — FLOW
- `3d3d0`: `BCC.W 3d3da` (→`3d3d4`) — C 소비
- `3d3d4`: `MOVE.L #3db62, (a6)` (→`3d3da`)
- `3d3da`: `BRA.W 3dbba` — FLOW

**code pointer `3d3de`(`3d310 LEA 3d3de(PC),A0; JSR 4da50`(N35 범위) → N23 자식 `4db42`의 LONG `7a`, N23 `4dbb0 JSR (A1)`) 3**
- `3d3de`: `MOVEA.L c(a6), a0; TST.B b1(a0); BEQ.W 3d3ee` (→`3d3ea`) — Clear 생산
- `3d3ea`: `ORI.B #1, ccr` (→`3d3ee`) — Set 생산
- `3d3ee`: `RTS ` — FLOW

**`3db62`(`3d338 BCS`·`3e038 BCC` 대상, `3d3d4` 설치 값) / 공유 꼬리 `3dbba` `3dc24..3dcac` 17**
- `3db62`: `JMP 2a00.l` — FLOW
- `3dbba`: `BRA.W 3dc24` — FLOW
- `3dc24`: `JSR 4b54e.l` — FLOW
- `3dc2a`: `BTST.B #7, 61(a6); SNE.B d0; BEQ.W 3dc3c` (→`3dc36`) — FLOW
- `3dc36`: `MOVE.L #3d982, (a6)` (→`3dc3c`)
- `3dc3c`: `AND.B d0, 5e(a6)` (→`3dc40`)
- `3dc40`: `BCLR.B #6, 61(a6); TST.W 88(a6); BEQ.W 3dc58` (→`3dc4e`)
- `3dc4e`: `SUBQ.W #1, 88(a6); BSET.B #6, 61(a6)` (→`3dc58`)
- `3dc58`: `JSR 4d766.l` — FLOW
- `3dc5e`: `BCC.W 3dc68` (→`3dc62`) — C 소비
- `3dc62`: `BSET.B #6, 61(a6)` (→`3dc68`) — FLOW
- `3dc68`: `TST.L 80(a6); BEQ.W 3dc84` (→`3dc70`)
- `3dc70`: `MOVE.B 1a(a6), 14(a6); JSR 3defa(pc)`
- `3dc7a`: `BSET.B #6, 61(a6); BRA.W 3dca4` — FLOW
- `3dc84`: `MOVE.B 1b(a6), 14(a6); MOVE.W 88(a6), d0; ANDI.W #1, d0; BEQ.W 3dca4` (→`3dc96`)
- `3dc96`: `MOVE.B 19(a6), 14(a6); ST.B 94(a6); ST.B 98(a6)` (→`3dca4`)
- `3dca4`: `MOVE.B #ff, 9f(a6); RTS `

**내부 함수 `3dcf2`(`JSR 3dcf2(PC)`) 4 / `3dd6a`(`3dd04 BSR`) 7 / `3de06` 6 / `3de46` 2**
- `3dcf2`: `MOVE.W 1e(a6), d0; JSR ce02.l`
- `3dcfc`: `JSR 49fc6.l` — FLOW
- `3dd02`: `SCS.B -(a7); BSR.W 3dd6a` — C 소비
- `3dd08`: `MOVE.B (a7)+, d0; LSR.B #1, d0; RTS ` — 계산 C 생산
- `3dd6a`: `MOVE.W 1e(a6), -(a7); MOVE.B 14(a6), -(a7); MOVEQ #0, d1; MOVE.B b0(a6), d1; ADD.W d1, 46(a6); ADDI.W #12, d1; ANDI.W #ff, d1; MOVE.W #ee00, d0; MOVE.B d1, d0; MOVE.W d0, 96(a6); MOVE.W #1200, d0; MOVE.B d1, d0; MOVE.W d0, 92(a6); MOVE.B 14(a6), d0; CMP.B 1b(a6), d0; BNE.W 3ddaa` (→`3dda4`)
- `3dda4`: `MOVE.B 1c(a6), 14(a6)` (→`3ddaa`)
- `3ddaa`: `MOVE.W #2, 1e(a6); BCLR.B #0, 9b(a6); LEA.L 8a(a6), a0; JSR 49fca.l`
- `3ddc0`: `BCC.W 3ddca` (→`3ddc4`) — C 소비
- `3ddc4`: `BSET.B #0, 9b(a6)` (→`3ddca`) — FLOW
- `3ddca`: `JSR 43e34.l` — FLOW
- `3ddd0`: `MOVE.B (a7)+, 14(a6); MOVE.W (a7)+, 1e(a6); BTST.B #0, 9b(a6); SNE.B d0; LSR.B #1, d0; RTS `
- `3de06`: `JSR 8ff4.l` — FLOW
- `3de0c`: `MOVE.W #e18, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3de1a`: `MOVE.W #e0e, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3de28`: `MOVE.W #e0e, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3de36`: `MOVE.W #e0f, d0; MOVE.B #1, d1; JSR 8ebe.l`
- `3de44`: `RTS ` — FLOW
- `3de46`: `MOVE.L 64(a6), 36(a6); JSR 43ea4.l`
- `3de52`: `RTS ` — FLOW

**내부 함수 `3df44`(`3d228 JSR`; `28ae` 자식 `41fe6` 둘, `3e0f6` 하나) 11**
- `3df44`: `MOVE.W #1a3, 20(a6); MOVE.L 2001a0.l, 22(a6); JSR 3de06(pc)`
- `3df56`: `MOVE.B 1b(a6), 14(a6); BSET.B #6, 15(a6); MOVE.W #2, 68(a6); MOVE.W #2, 1e(a6); MOVEQ #12, d1; JSR 4d81c.l`
- `3df76`: `MOVE.B d1, a5(a6); MOVE.B d2, a6(a6); MOVE.W d3, 54(a6); MOVEA.L #41fe6, a0; MOVE.W #a, d0; JSR 28ae.l`
- `3df92`: `BCC.W 3dfc0` (→`3df96`) — C 소비
- `3df96`: `LEA.L 96(a6), a1; MOVE.L a1, 76(a0); MOVE.B #12, 7a(a0); MOVE.B #4, 7b(a0); MOVE.B #0, 7c(a0); MOVE.B #0, 7d(a0); MOVE.B #0, 7e(a0); ORI.B #1, ccr` (→`3dfc0`) — Set 생산
- `3dfc0`: `BSET.B #6, 15(a0); MOVE.W #6, 68(a0); MOVE.W #6, 1e(a0); MOVEA.L #41fe6, a0; MOVE.W #a, d0; JSR 28ae.l`
- `3dfe2`: `BCC.W 3e010` (→`3dfe6`) — C 소비
- `3dfe6`: `LEA.L 92(a6), a1; MOVE.L a1, 76(a0); MOVE.B #13, 7a(a0); MOVE.B #4, 7b(a0); MOVE.B #2, 7c(a0); MOVE.B #0, 7d(a0); MOVE.B #0, 7e(a0); ORI.B #1, ccr` (→`3e010`) — Set 생산
- `3e010`: `BSET.B #6, 15(a0); MOVE.W #6, 68(a0); MOVE.W #6, 1e(a0); MOVE.B #0, 9a(a6); MOVEA.L #3e0f6, a0; MOVE.W #a, d0; JSR 28ae.l`
- `3e038`: `BCC.W 3db62` (→`3e03c`) — C 소비
- `3e03c`: `RTS ` — FLOW

**`28ae` 자식 callback `3e0f6`(설치 `3e1ce` `3e214`; 내부 `3e130`, `3e17a`→`JMP (A0)`; LONG 표 `3e1ba` 대상 `3e1c2` `3e1ec`; 계속 주소 `3e1e2` `3e22a`) 31**
- `3e0f6`: `MOVE.W #1a3, 20(a6); MOVE.L 2001a0.l, 22(a6); BSET.B #6, 15(a6); MOVE.W #5, 68(a6); MOVE.W #5, 1e(a6); MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `3e120`: `MOVE.B #0, 9d(a6); MOVE.W #ffff, 86(a6); BRA.W 3e1c2`
- `3e130`: `JSR 491c4.l` — FLOW
- `3e136`: `MOVE.B b0(a0), b0(a6); MOVE.B 60(a0), 60(a6); MOVE.W 84(a0), 84(a6); MOVE.W 86(a0), d0; CMP.W 86(a6), d0; BEQ.W 3e178` (→`3e154`)
- `3e154`: `MOVE.W d0, 86(a6); JSR 8ff4.l`
- `3e15e`: `MOVE.W 86(a6), d0; LEA.L 3fc6e.l, a0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; MOVE.B #0, d1; JSR 8ebe.l`
- `3e178`: `RTS ` — FLOW
- `3e17a`: `MOVEQ #0, d0; MOVEQ #0, d1; MOVEA.L c(a6), a1; MOVE.B 9d(a1), d0; BMI.W 3e1b6` (→`3e18a`)
- `3e18a`: `MOVE.B 9d(a6), d1; BMI.W 3e1a0` (→`3e192`)
- `3e192`: `LEA.L 3e1b8(pc), a1; MOVE.B (a1, d1.w), d2; BTST.L d0, d2; BNE.W 3e1b6` (→`3e1a0`)
- `3e1a0`: `MOVE.B d0, 9d(a6); ADD.W d0, d0; ADD.W d0, d0; MOVEA.L 3e1ba(pc, d0.w), a0; MOVEA.L c(a6), a1; MOVE.B #ff, 9d(a1)` (→`3e1b6`)
- `3e1b6`: `JMP (a0)` — FLOW
- `3e1c2`: `MOVE.B #0, 9d(a6); MOVE.L #3e1ce, (a6)` (→`3e1ce`)
- `3e1ce`: `JSR 288c.l` — FLOW
- `3e1d4`: `BCC.W 3e24a` (→`3e1d8`) — C 소비
- `3e1d8`: `JSR 3e130(pc)` — FLOW
- `3e1dc`: `LEA.L 3e1e2(pc), a0; BRA.B 3e17a` — FLOW
- `3e1e2`: `JSR 43e34.l` — FLOW
- `3e1e8`: `BRA.W 3e248` — FLOW
- `3e1ec`: `MOVE.B #1, 9d(a6); LEA.L 3fc86.l, a1; MOVE.W 86(a6), d0; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `3e20e`: `MOVE.L #3e214, (a6)` (→`3e214`)
- `3e214`: `JSR 288c.l` — FLOW
- `3e21a`: `BCC.W 3e24a` (→`3e21e`) — C 소비
- `3e21e`: `JSR 3e130(pc)` — FLOW
- `3e222`: `LEA.L 3e22a(pc), a0; BRA.W 3e17a` — FLOW
- `3e22a`: `MOVEQ #0, d0; MOVEQ #0, d1; MOVE.B b0(a6), d1; JSR 49290.l`
- `3e238`: `JSR 43e34.l` — FLOW
- `3e23e`: `JSR 49fc6.l` — FLOW
- `3e244`: `BRA.W 3e248` — FLOW
- `3e248`: `RTS ` — FLOW
- `3e24a`: `JMP 2a00.l` — FLOW

**`28ae` 자식 callback `41fe6`(`3df82`/`3dfd2` 등 `MOVEA.L #41fe6,A0; JSR 28ae`) 11**
- `41fe6`: `MOVE.W #12a, 20(a6); MOVE.L 2000b8.l, 22(a6); MOVEA.L c(a6), a0; LEA.L 2e(a0), a1; MOVEA.L 76(a6), a0; MOVE.B (a0)+, d0; MOVE.B (a0)+, d1; CLR.B (a0); EXT.W d0; EXT.W d1; JSR 43e04.l`
- `42010`: `MOVEQ #0, d0; MOVE.B 7a(a6), d0; ADD.W d0, d0; LEA.L 41e4c(pc), a0; MOVE.W (a0, d0.w), 86(a6); MOVEA.L 76(a6), a0; MOVE.B #ff, 3(a0); MOVEQ #0, d0; MOVE.B 7a(a6), d0; LEA.L 41eca(pc), a0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; MOVE.B #0, d1; JSR 8ebe.l`
- `42046`: `MOVEQ #0, d0; MOVE.B 7a(a6), d0; LEA.L 41ef4(pc), a0; ADD.W d0, d0; MOVE.W (a0, d0.w), d0; MOVE.B #0, d1; JSR 8ebe.l`
- `42060`: `MOVE.B 19(a6), 14(a6); MOVEQ #0, d0; MOVE.B 7a(a6), d0; ADD.W d0, d0; ADD.W d0, d0; LEA.L 41f92(pc), a0; MOVE.L (a0, d0.w), 96(a6); TST.B 7b(a6); BNE.W 42088` (→`42082`)
- `42082`: `MOVE.B #2, 7b(a6)` (→`42088`)
- `42088`: `TST.B 7d(a6); BNE.W 42096` (→`42090`)
- `42090`: `MOVE.B #5, 7d(a6)` (→`42096`)
- `42096`: `MOVE.W 1e(a6), d0; CMPI.W #ffff, d0; BEQ.W 420a6` (→`420a2`)
- `420a2`: `MOVE.W d0, 94(a6)` (→`420a6`)
- `420a6`: `MOVEA.L #4264a, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `420b6`: `MOVE.L #420be, (a6); RTS `

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다):
  - `1bf02`: A0을 LONG으로 push, `JSR 484b4`(N23; C 생산). `1bf0a`: Clear → `1bf66`. `1bf0e`: `D0.B` ≠ 0이면 A0 = `100da8`, 아니면 `100cb8`(player 기록). `1bf24 JSR 289e`(readiness: `CMPI.L #270e,(A0)` 같음 → Clear, 아니면 Set). `1bf2a`: Clear → `1bf66`. `1bf2e`: BYTE `61(A0)` bit 7 = 1 → `1bf66`. `1bf38`: A1 = `1bef8`, `D0` = 0, `D0.B` = BYTE `9f(A0)`, BYTE `1bef8 + D0.W`(고정 ROM 자료, live bus) = 0이면 `1bf66`. `1bf4a`: LONG `3a(A0)` ≥ 0(`BPL`)이면 `1bf66`. `1bf52`: BYTE `15(A0)` bit 7 = 1 → `1bf66`. `1bf5c`: `D0` = 0, A0 = pop LONG, C = 1, RTS. `1bf66`: A0 = pop LONG, `D0` = `ffffffff`, RTS.
  - `1bfb4`: `D0.W` &= 1; ≠ 0이면 A0 = `100da8`, 아니면 `100cb8`; `JSR 289e`; Clear → `1c00a`(`D1` = `D2` = `D3` = 0, RTS). `1bfd6`: BYTE `61(A0)` bit 7 = 1 → `1c00a`. `1bfe0`: `D1.B` = (WORD `90(A0)` ≠ 0 ? `ff` : 0); BYTE `a8(A0)` bit 0 = 1이면 `D1` = `ffffffff`(`1bff0 MOVEQ`). `1bff2`: `D3` = 0, `D2.B` = (BYTE `a7(A0)` bit 2 ? `ff` : 0); bit 2 = 1이면 `D3.B` = (BYTE `a8(A0)` bit 6 ? `ff` : 0)(`1c000`). RTS.
  - `3d228`: `JSR 3df44` 뒤 `(A6)` = `3d280`, RTS. `3df44`: `20.W` = `1a3`, LONG `22` = bank LONG `2001a0`, `JSR 3de06`(`JSR 8ff4`, `8ebe`를 `D0.W`/`D1.B` = `e18`/1, `e0e`/1, `e0e`/1, `e0f`/1로 네 번). `3df56`: BYTE `14` = BYTE `1b`, BYTE `15` bit 6 = 1, `68.W` = `1e.W` = 2, `D1` = `12`, `JSR 4d81c`(stage_area). `3df76`: BYTE `a5` = `D1.B`, BYTE `a6` = `D2.B`, `54.W` = `D3.W`, `28ae`(A0 = `41fe6`, `D0.W` = `a`). `3df92`: Clear(자리 없음; A0 = `A5-7168` 더미 노드) → `3dfc0`; Set → `3df96`: 자식 LONG `76` = A6 + `96`, BYTE `7a`/`7b`/`7c`/`7d`/`7e` = `12`/4/0/0/0, C = 1. `3dfc0`: 자식 BYTE `15` bit 6 = 1, `68.W` = `1e.W` = 6, 두 번째 `28ae`(`41fe6`); `3dfe6`: LONG `76` = A6 + `92`, BYTE `7a..7e` = `13`/4/2/0/0, C = 1. `3e010`: 자식 BYTE `15` bit 6, `68.W` = `1e.W` = 6, BYTE `9a(A6)` = 0, 세 번째 `28ae`(`3e0f6`). `3e038`: Clear → `3db62`(`JMP 2a00`), Set → RTS.
  - `3d280`(설치): `68.W` = `1e.W` = 0, A0 = 0, `JSR 4b82e`; BYTE `9d` = 0, `JSR 3de06`; BYTE `14` = BYTE `1b`, LONG `80` = 0, `JSR 496c2`. `3d2b4`: BYTE `a1` ≠ 0이면 `3d388`. `3d2bc`: `86.W` = 0, BYTE `a0` = `a1` = 0, `49f96`(A0 = A6 + `8a`, A1 = `3e754`, `D0.W` = `100`), `49f8c`(A1 = `3e808`). `3d2f2`: BYTE `15` bit 3 = 0, LONG `56` = 0, `D0` = 0, `D1` = `40`, BYTE `15` bit 0 = 1이면 `D0.W` = -`D0.W`(`3d30e`). `3d310`: A0 = `3d3de`, `JSR 4da50`(경계). `3d31a`: BYTE `78` = `b3` = 0, `(A6)` = `3d32c`, fall-through.
  - `3d32c`(설치): `1aa7e`(A0 = `3f6f0`; U01 화면 판정 C); Set → `3db62`(`JMP 2a00`). `3d33c JSR 3de46`(LONG `36` = LONG `64`, `JSR 43ea4`). `3d340`: `4d2d4`(A0 = `3f708`; 경계); Clear → `3d380`. `3d350`: `84.W` = `D0.W`, `JSR 3dcac`(N22b 경계); Clear → `3d380`. `3d35c`: `86.W` = `D0.W`, `D0.W` = `84.W`, `D1.B` = `12`, `D2.B` = BYTE `a5`, `D3.B` = BYTE `a6`, `D4.W` = `54.W`, `JSR 4d508`(경계); `3d37a`: `(A6)` = `3d3f0`(N22b 설치 값). `3d380 JSR 3dcf2` 뒤 `BRA 3dbba` → `3dc24`.
  - `3d388`(BYTE `a1` ≠ 0): `49f96`(A1 = `3e754`), `49f8c`(A1 = `3e92e`), `(A6)` = `3d3b2`, fall-through. `3d3b2`(설치): `JSR 3de46`, `JSR 3dcf2`; `3d3ba`: Set(`3dcf2`의 C)이면 `(A6)` = `3d2b4`(`3d3be`). `3d3c4`: `1ab02`(A0 = `3f6f0`; U05); Set이면 `(A6)` = `3db62`(`3d3d4`). `BRA 3dbba`.
  - `3d3de`(code pointer): A0 = LONG `c(A6)`(부모), BYTE `b1(A0)` = 0이면 C = 0으로 RTS, 아니면 C = 1(`3d3ea ORI`)로 RTS.
  - 공유 꼬리 `3dc24`: `JSR 4b54e`; `3dc2a`: `D0.B` = (BYTE `61` bit 7 ? `ff` : 0), bit 7 = 1이면 `(A6)` = `3d982`(`3dc36`, 범위 밖 설치 값). `3dc3c`: BYTE `5e` &= `D0.B`. `3dc40`: BYTE `61` bit 6 = 0; `88.W` ≠ 0이면 `88.W` -= 1(16 bit), BYTE `61` bit 6 = 1(`3dc4e`). `3dc58`: `JSR 4d766`(경계); Set이면 BYTE `61` bit 6 = 1(`3dc62`). `3dc68`: LONG `80` ≠ 0이면 BYTE `14` = BYTE `1a`, `JSR 3defa`(N22b 경계), BYTE `61` bit 6 = 1(`3dc7a`); 아니면 BYTE `14` = BYTE `1b`, `D0.W` = `88.W` & 1; ≠ 0이면 BYTE `14` = BYTE `19`, BYTE `94` = BYTE `98` = `ff`(`3dc96`). `3dca4`: BYTE `9f` = `ff`, RTS.
  - `3dcf2`: `D0.W` = `1e.W`, `JSR ce02`(U04), `JSR 49fc6`(interpreter, C 생산). `3dd02`: `SCS.B -(A7)`(A7 -= 2, BYTE (A7) = C ? `ff` : 0), `BSR 3dd6a`. `3dd08`: `D0.B` = pop BYTE(A7 += 2), C = 그 BYTE의 bit 0, `D0.B` = BYTE >> 1, RTS.
  - `3dd6a`: push `1e.W`(WORD), push BYTE `14`(A7 -= 2); `D1` = BYTE `b0`(0 확장); `46.W` += `D1.W`(16 bit, 읽고 씀); `D1.W` = (`D1.W` + `12`) & `ff`; `D0.W` = `ee00`, `D0.B` = `D1.B`, `96.W` = `D0.W`; `D0.W` = `1200`, `D0.B` = `D1.B`, `92.W` = `D0.W`; `D0.B` = BYTE `14`; BYTE `14` = BYTE `1b`이면 BYTE `14` = BYTE `1c`(`3dda4`). `3ddaa`: `1e.W` = 2, BYTE `9b` bit 0 = 0, A0 = A6 + `8a`, `JSR 49fca`(interpreter 두 번째 진입, 결정 2); `3ddc0`: Set이면 BYTE `9b` bit 0 = 1(`3ddc4`). `3ddca JSR 43e34`. `3ddd0`: BYTE `14` = pop BYTE, `1e.W` = pop WORD, `D0.B` = (BYTE `9b` bit 0 ? `ff` : 0), `LSR.B #1`(`D0.B` = `7f` 또는 0; C는 Unknown로 둔다), RTS.
  - `3e0f6`(`28ae` 자식): `20.W` = `1a3`, LONG `22` = bank LONG `2001a0`, BYTE `15` bit 6 = 1, `68.W` = `1e.W` = 5, `D0` = `D1` = 0, `JSR 49290`(U08). `3e120`: BYTE `9d` = 0, `86.W` = `ffff`, `BRA 3e1c2`. `3e1c2`: BYTE `9d` = 0, `(A6)` = `3e1ce`, fall-through. `3e1ce`(설치): `JSR 288c`(stage_event_ops: 부모 없음 → Set, 부모 LONG = `270e` → Clear, 아니면 Set); Clear → `3e24a`(`JMP 2a00`). `3e1d8 JSR 3e130`. `3e1dc`: A0 = `3e1e2`, `BRA 3e17a`.
  - `3e130`: `JSR 491c4`(U17; A0 = 대상 노드). `3e136`: BYTE `b0` = BYTE `b0(A0)`, BYTE `60` = BYTE `60(A0)`, `84.W` = `84.W(A0)`, `D0.W` = `86.W(A0)`; `D0.W` = `86.W(A6)`이면 RTS. `3e154`: `86.W` = `D0.W`, `JSR 8ff4`; `3e15e`: `D0.W` = `86.W`, A0 = `3fc6e`, `D0.W` = 2·`D0.W`(16 bit), `D0.W` = WORD(`3fc6e` + sext(`D0.W`))(고정 ROM 자료), `D1.B` = 0, `JSR 8ebe`. RTS.
  - `3e17a`: `D0` = `D1` = 0, A1 = LONG `c(A6)`(부모), `D0.B` = BYTE `9d(A1)`; 음수(`BMI`)면 `JMP (A0)`(호출자가 준 계속 주소). `3e18a`: `D1.B` = BYTE `9d(A6)`; 음수면 `3e1a0`. `3e192`: A1 = `3e1b8`, `D2.B` = BYTE(`3e1b8` + `D1.W`)(고정 ROM 자료), `D2`의 bit (`D0` & 31)(`BTST.L`, 32 bit 전체) = 1이면 `JMP (A0)`. `3e1a0`: BYTE `9d(A6)` = `D0.B`, `D0.W` = 4·`D0.W`(16 bit), A0 = LONG(`3e1ba` + sext(`D0.W`))(고정 ROM 자료), A1 = LONG `c(A6)`, BYTE `9d(A1)` = `ff`. `3e1b6`: PC = A0(live target; 결정 3).
  - `3e1e2`(계속): `JSR 43e34`, RTS(`3e248`). `3e1ec`(표 entry 1): BYTE `9d` = 1, A1 = `3fc86`, `D0.W` = 4·`86.W`(16 bit), A1 = LONG(`3fc86` + sext(`D0.W`))(고정 ROM 자료), `D0.W` = `100`, `JSR 49f8c`; `(A6)` = `3e214`, fall-through. `3e214`(설치): `JSR 288c`; Clear → `JMP 2a00`; `JSR 3e130`; A0 = `3e22a`, `BRA 3e17a`. `3e22a`(계속): `D0` = 0, `D1` = BYTE `b0`(0 확장), `JSR 49290`, `JSR 43e34`, `JSR 49fc6`, RTS.
  - `41fe6`(`28ae` 자식): `20.W` = `12a`, LONG `22` = bank LONG `2000b8`, A0 = LONG `c(A6)`(부모), A1 = A0 + `2e`, A0 = LONG `76(A6)`, `D0.B` = BYTE (A0)+, `D1.B` = BYTE (A0)+, BYTE (A0) = 0, `D0.W` = sext(`D0.B`), `D1.W` = sext(`D1.B`), `JSR 43e04`(cleanup). `42010`: `D0` = BYTE `7a`(0 확장), `86.W` = WORD(`41e4c` + 2·`D0`); A0 = LONG `76`, BYTE `3(A0)` = `ff`; `D0` = BYTE `7a`, A0 = `41eca`, `D0.W` = WORD(`41eca` + 2·`D0`), `D1.B` = 0, `JSR 8ebe`. `42046`: 같은 꼴로 표 `41ef4`, `JSR 8ebe`. `42060`: BYTE `14` = BYTE `19`, LONG `96` = LONG(`41f92` + 4·BYTE `7a`); BYTE `7b` = 0이면 2, BYTE `7d` = 0이면 5; `D0.W` = `1e.W`, ≠ `ffff`이면 `94.W` = `D0.W`. `420a6`: A1 = `4264a`, `D0.W` = `100`, `JSR 49f8c`; `420b6`: `(A6)` = `420be`(N23 설치 값), RTS. (고정 ROM 표 `41e4c` `41eca` `41ef4` `41f92`는 BYTE 색인 0..`ff`로 live bus 읽기.)

## carry

- [F] **소비 16 block**(FLOW_ONLY). Unknown C로 들어오면 `objects n22 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS·SCS는 fall-through/0; Set이면 반대.
  - `1bf0a BCC.W 1bf66`: N23 `484b4`(`ORI`/`ANDI` CCR; 현재 경계).
  - `1bf2a BCC.W 1bf66`, `1bfd2 BCC.W 1c00a`: readiness `289e`(`CMPI.L #270e,(A0)` 같음 → Clear, `28a8 ORI` → Set).
  - `3d338 BCS.W 3db62`: U01 `1aa7e`(`1aaf6 ANDI` Clear, `1aafc ORI` Set).
  - `3d34c BCC.W 3d380`: N23 `4d2d4`(경계). `3d358 BCC.W 3d380`: N22b `3dcac` → `JMP 4d418`(경계)의 C. `3dc5e BCC.W 3dc68`: N23 `4d766`(경계).
  - `3d3ba BCC.W 3d3c4`: N22a `3dcf2`(→ `3dd08` 계산 C).
  - `3d3d0 BCC.W 3d3da`: U05 `1ab02`(`1ab7a ANDI` Clear, `1aafc ORI` Set).
  - `3dd02 SCS.B -(A7); BSR 3dd6a`: interpreter `49fc6`의 C(BYTE `ff`/0을 push).
  - `3ddc0 BCC.W 3ddca`: interpreter `49fca`(결정 2)의 C.
  - `3df92 BCC.W 3dfc0`, `3dfe2 BCC.W 3e010`, `3e038 BCC.W 3db62`: fade_card `28ae`(`2908 ORI` Set = 자식 생성, `290e ANDI` Clear = 자리 없음/A0 = 0).
  - `3e1d4 BCC.W 3e24a`, `3e21a BCC.W 3e24a`: stage_event_ops `288c`(`2898 ORI` Set, `289e` 계산, `28a8 ORI` Set).
- [F] **known 생산 6 block**: `1bf5c`(Set, RTS 앞), `3d3de`(Clear; `3d3ee` RTS로), `3d3ea`(Set; `3d3ee` RTS로), `3df96`(Set; `3dfc0`이 덮음), `3dfe6`(Set; `3e010`이 덮음), `3dd08`(계산: 꺼낸 BYTE bit 0; RTS 앞). 소비자 확인은 결정 4.
- [F] **FLOW_ONLY 69 block**(C 보존): JSR/BSR/JMP/BRA/RTS block, `LEA`+`JSR`/`BRA`(`1bf14` `1bf1e` `1bfbc` `1bfc6` `3d310` `3d32c` `3d340` `3d3c4` `3e1dc` `3e222`), `BTST`(+`BNE`/`BEQ`)·`BSET`·`SNE` block(`1bf2e` `1bf52` `1bfd6` `1c000` `3dc2a` `3dc62` `3dc7a` `3ddc4`), `JMP (A0)`(`3e1b6`), 소비 16개. 목록: `1bf0a` `1bf14` `1bf1e` `1bf24` `1bf2a` `1bf2e` `1bf52` `1bfbc` `1bfc6` `1bfcc` `1bfd2` `1bfd6` `1c000` `1c008` `3d228` `3d310` `3d32c` `3d338` `3d33c` `3d340` `3d34c` `3d358` `3d380` `3d384` `3d3b2` `3d3b6` `3d3ba` `3d3c4` `3d3d0` `3d3da` `3d3ee` `3db62` `3dbba` `3dc24` `3dc2a` `3dc58` `3dc5e` `3dc62` `3dc7a` `3dcfc` `3dd02` `3ddc0` `3ddc4` `3ddca` `3de06` `3de44` `3de52` `3df92` `3dfe2` `3e038` `3e03c` `3e130` `3e178` `3e1b6` `3e1ce` `3e1d4` `3e1d8` `3e1dc` `3e1e2` `3e1e8` `3e214` `3e21a` `3e21e` `3e222` `3e238` `3e23e` `3e244` `3e248` `3e24a`.
- [F] **carry 보존 목록 69 PC** = FLOW_ONLY 69. 생산 6 block은 보존 목록에 넣지 않고 block 안에서 C를 정한다.
- [F] **Unknown 76 block**: 나머지(`MOVE`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDI`/`ANDI`/`AND`/`SUBQ`/`NEG`/`EXT`/`CLR`/`LSR` 포함 block, 설치 block, 애니메이션 block).
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 flag 읽기로 시작하는 곳은 위 C 소비 16곳뿐이고 모두 JSR/BSR 복귀점이다; 선행은 callee 하나).

## 구현 범위와 규약

- routing 14 범위(위 표). 짝수 PC 878개 중 block 시작 151, 내부 727. 내부 PC 직접 진입은 `unsupported animation objects n22 PC`다. 범위 이웃(N22b·미참조 코드·자료)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 69 PC를 넣는다.
- 제어 이동: `3e1b6 JMP (A0)`만 live target이다(PC = A0; 홀수면 `unaligned animation machine PC`, routing 밖이면 `unsupported animation machine PC`). 나머지는 정적이다. 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`3d31a`→`3d32c`, `3d3ac`→`3d3b2`, `3e1c2`→`3e1ce`, `3e20e`→`3e214`).
- 스택: 요약의 push/pop만. BYTE push/pop은 A7 ±2(`push_program_stack`/`pop_program_stack` 규약)다. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank): LONG `2001a0`(id `20.W` = `1a3`; `3df44` `3e0f6` → LONG `22`), LONG `2000b8`(id `12a`; `41fe6` → LONG `22`).
- [F] 고정 ROM 자료(live bus 읽기): BYTE 표 `1bef8`(`01`×9 `00`; 색인 BYTE `9f(A0)`), WORD 표 `3fc6e`(색인 2·`86.W`), LONG 표 `3fc86`(색인 4·`86.W`), bit 표 `3e1b8`(`01 02`; 색인 BYTE `9d(A6)` 0..`7f`), LONG 표 `3e1ba`(`3e1c2` `3e1ec`; 색인 4·BYTE 부모 `9d`), WORD 표 `41e4c` `41eca` `41ef4`·LONG 표 `41f92`(색인 BYTE `7a`). 원본은 색인을 검사하지 않고 C++도 검사하지 않는다(표 밖 색인은 이웃 바이트를 읽는다).
- [F] 주소만 넘기는 고정 ROM 자료: 사각형 `3f6f0`(`1aa7e` `1ab02`; `ffe0 0000 0040 0040`), `3f708`(`4d2d4`; `fff0 0008 0030 0010`), 애니메이션 목록 `3e754` `3e808` `3e92e` `4264a`, `8ebe` 인자 WORD.
- [F] work RAM:
  - 노드 A6: BYTE `14` `15` `19` `1a` `1b` `1c` `5e` `60` `61` `78` `7a` `7b` `7d` `94` `98` `9a` `9b` `9d` `9f` `a0` `a1` `a5` `a6` `b0` `b3`; WORD `1e` `20` `46` `54` `68` `84` `86` `88` `92` `94` `96`; LONG `(A6)`(설치) `c`(부모) `22` `36` `56` `64` `76`(자식: 부모 WORD 포인터) `80` `96`.
  - 부모 노드 `c(A6)`: BYTE `9d`(`3e17a`·`3e1a0` 씀), `b1`(`3d3de`); `41fe6` A1 = 부모 + `2e`.
  - `1bf02`/`1bfb4`의 player 기록 `100cb8`/`100da8`: LONG `(A0)`(`289e`), BYTE `15` `61` `9f` `a7` `a8`, WORD `90`, LONG `3a`.
  - `28ae` 자식(`3df96` `3dfc0` `3dfe6` `3e010`): BYTE `15` `7a..7e`, WORD `1e` `68`, LONG `76`. 자리 없음이면 A0 = `100e98`(A5 - `7168`, 더미 노드)에 쓴다.
  - `491c4`가 돌려준 A0 노드(`3e136`): BYTE `60` `b0`, WORD `84` `86`.
  - `41fe6`의 LONG `76`이 가리키는 BYTE 3개(+0 +1 읽기, +2 = 0, `42010`에서 +3 = `ff`).
- [F] 상수 인자: `8ebe` `D0.W`/`D1.B` = `e18`/1, `e0e`/1, `e0e`/1, `e0f`/1(`3de06`), `3fc6e`·`41eca`·`41ef4` 표 값/0; `4d81c` `D1` = `12`; `28ae` `D0.W` = `a`; `49290` `D0`/`D1` = 0/0(`3e0f6`), 0/BYTE `b0`(`3e22a`); `49f8c`/`49f96` `D0.W` = `100`.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256): `engine/src/animation_machine_objects_n22.cpp` `fbe5422a15fc309e41a1aea2033cf9286b17a4b80b38eee298c145e3e4408c20`, `engine/tests/animation_machine_objects_n22_test.cpp` `371a96c6d70ee1f70c1e59e10c3a4af1f4fbae2119b795d90f3e147cf3845d26`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나; `a8ff43d8…`), `engine/src/animation_machine_internal.h`(선언 하나; `956357a1…`), `Makefile`(source 목록·test target·실행 줄; `4c7c2698…`), `tools/verify_animation_machine.py` SOURCES(`a6e28fbb…`).
- [F] 실행부 case 집합 = `startsA.txt`(151, scratch 비교 일치). 내부 PC 727개는 모두 `unsupported animation objects n22 PC`, 소비 16 block은 Unknown C에서 `objects n22 caller requires known carry`(상태 보존)다.
- [F] `make -j4 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all2.log`). N22 test 출력: `animation machine objects n22: 460 fixtures (34 checked errors, 134 kept C), 151 blocks, 2139 calls`.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N22 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만): 460 fixture(성공 426, checked 오류 34), 151 시작 모두 Unicorn fixture로 덮음, block 표(151 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 16은 Unknown에서 거부), zero-step 151 × 3, 내부 PC 727 전수, 홀수 PC(범위 양끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`, 범위 옆 자료 `1bef8` `3dd42` `3def2` `3e1b8` `3e1ba` `3e1be`, 경계 stop 29개(다른 단위 진입·N23/N35/N22b 경계는 stop만). "real" 행은 `289e` `288c` `1aa7e` `1ab02` `28ae`를 native로 따라가 실제 소비자 분기와 비교했다. RTS 앞 생산은 실제 ROM 소비자를 복귀 LONG으로 두고 native 분기로 확인했다: `1bf5c` → `4dbb2` Set(→`4dbd6`), `3d3de` b1 = 0 → Clear(→`4dbb6`), b1 = 1/`80` → Set, `3dd08` BYTE `0`/`fe`/`80` → Clear(`3d3ba`→`3d3c4`), `ff`/`1`/`7f` → Set(→`3d3be`).
- [F] 돌연변이 검사(scratch `mut/mut22.py`, 실행부 한 줄씩 12개: 소비 분기 뒤바꿈, `3dd08` bit, `BTST.L` mask, `EXT.W`, `ADD.W`, `3d3de` C, 표 색인 배수, `SUBQ.W`, `SNE` 폭, `SCS` 값, `CMPI.W` 폭, BYTE 표 색인): 12/12를 test가 잡았다(`CMPI.W #ffff` 폭 돌연변이를 잡으려고 `42096` fixture 5개를 더했다).
- [F] 실제 ROM 차분(scratch `realrom/real22.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM, native는 STOP·`2a00`·`2a24`·C++ routing 밖 첫 PC·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤):
  - 기준 interpreter(`49fca`는 JSR로 들어갈 때 선언 stop): 3 seed × 1,500 case, 불일치 0, 시작 151/151(seed 3은 150; `1bf0a` 미도달). 실제 생산자 뒤 소비자 native 분기 비교 `1bf2a` `1bfd2` `3d338` `3d3d0` `3dd02` `3df92` `3dfe2` `3e038` `3e1d4` `3e21a`. clean stop이 없는 native case는 건너뜀(seed별 232/226/246).
  - `49fca` scratch patch(결정 2) 적용 batch: 3 × 1,500 case, 불일치 0, 시작 151/151, 소비자 `3d3ba`(`3dd08` 계산 C) 222회·`3ddc0`(`49fca` C) 562회 추가 비교.
  - patch + interpreter 따라가기(`FOLLOW_ANIM`): 2 × 1,000 case, 불일치 0.
  - native 홀수 주소·Unknown C 진입 소비 거부·`2986` X 한계 해당 0.
- [F] 자연 상태 차분(scratch `natural/natural22.py`·`compare22.py`, RNG 초기화+응답 `80` 400 frame 선언 모델을 seed 38 39 116 117로 다시 돌림; pass 끝이 native seed 파일과 모두 같음): N22 callback 진입(`3d228` `3d280` `3d32c` `3e0f6` `3e1ce` `41fe6`), N23이 부르는 `1bf02` `1bfb4` `3d3de`, 경계 복귀점 `1bf0a` `3d34c` `3dc5e`(C는 native 분기로 정함) `3d31a`의 상태 4,464개를 잡아 선언 host 변경(복귀 LONG = STOP; `1bf0a`는 저장 A0 때문에 그대로) 뒤 native와 C++를 비교했다. 기준 interpreter(선언 stop `49fca`/`49f8c`/`49f96`)와 patch+따라가기 모두 **불일치 0**(`cmp_unpatched.log` SHA256 `278f9701…`, `cmp_patched.log` SHA256 `6f730360…`). patch 쪽에서 `3d34c` 332개가 `3d380`→`3dcf2`→`49fc6`→`3dd02`→`3dd6a`→`49fca`→`3ddc0`→`3ddd0`→`3dd08`→`3dbba`→`3dc24`→`4d766`까지 자연 경로로 일치했다.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `10b3c2d` 일치 pass 14,408·node 122,462, 불일치 0 → N22a 뒤 같음(불일치 0, seed별 분류 줄 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 130·pass 52,000·node 389,711·불일치 0 → N22a 뒤 같음(complete 130, 미완 seed·분류·첫 미연결 callback 동일: 32 33 `dcf56`, 38 39 `7086a`(N23 `c3a7c`), 116 117 `38ba0`, 136~140 `deadbeef`, 141). **새 완주 seed 없음, 회귀 없음**(재범위 "새 seed - / -"와 같다).
- [U] 남은 미확인: N22a 범위 PC는 400 frame 자연 frame pass에서 아직 실행되지 않는다(38 39는 N23 `c3a7c`, 116 117은 N31 `38ba0`에서 먼저 멈춤). N23(+`4da50`, 결정 5)과 interpreter `49fca`(결정 2) 뒤에 seed 38 39가 frame pass로 N22a를 지난다.
