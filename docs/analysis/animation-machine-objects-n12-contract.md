# 객체 callback F4 N12: `53050` 계열 객체(옛 U26) — 부모 callback `53050`·`53102`·`53122`·`531c2`·`5327a`, 자식 callback `539f8` `53b70` `53c42` `53d14` `53e70`, interpreter 명령 callback `52e78` `53ad0`, 공용 꼬리 `52e9c` `52f9c` `539e4` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N12 행(155 block, `52e4a..532a0` `539e4..53ee0`, callback `53050` `53102` `53122` `531c2` `5327a` `539f8` `53a62` `53b70` `53bd2` `53c42` `53ca4` `53d14` `53d6c` `53e70` `53ed2`, 경계 callee `482fa` `d3802`, bank 2, 미실행 설치 12(+42), 새 seed 46 47 / 46 47, 옛 U26 155)과 메인 결정 1·2(이름 `objects-n12`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 단위 형식과 규약은 N09 계약(SHA256 `0ff994e110ef3146cdafaea6aa59be074a024cf487cc43542dbc2e4a5ecee140`)과 N08 계약(SHA256 `6014ec8f40fc2cd776f4faa38e214dbd09e6aa9e8717a0bee47df1342e21182d`; RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로 확인), N04 계약 결정 5a(interpreter 명령 callback 허용 목록 1줄 추가)를 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)`/`MOVE.L #imm,7c(A6)` 설치 callback과 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 같은 flag를 쓰는 연속 Bcc(`531d4 BGT`+`531d8 BLT`)는 앞 block에 묶는다. Unicorn TB 분할(예: bank 읽기 뒤 `52fea` `52ff2`, `531d8`)은 시작이 아니다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 실행부 없는 경계다. 범위 안 자료(표)는 routing하지 않는다.
- U01~N10 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`OR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`ST`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block, callee C를 소비하는 Bcc block은 FLOW_ONLY다. `ADDQ An`은 Unknown이다. 블록 경계를 건너는 N/Z 재계산은 선행이 유일할 때만 허용한다(N12에는 필요한 곳이 없다). checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N12 코드와 고정 표는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기 2곳(`200188` `200370`)은 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n12`(HEAD `2dd58fd` = N10까지 통합, `engine/src/animation_machine.cpp` SHA256 `97e95ffdbd75fa3dc19c56ba28e22c1fc57bde59f6d1b300c0e841735f4cf122`, routing 규칙 67개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97fdde53a818555817108c9be69e053773168501858641890b62787649b56cbf`)을 참조했다. N12 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N11(`aee30..af06c` `dbf80..dbf9a` `eb24e..eb3e2` `eb586..eb626` `eb74a..eb766`)과 범위·경계가 겹치지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n12/n12.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N12 = 212 block**, 코드 5 범위 2,302바이트, 477명령이다. routing 짝수 PC 1,151개 중 내부 PC 939개다. 범위 안의 모든 명령이 진입에서 정적으로 도달된다(미도달 명령 0). 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·SUBX/ADDX/MULx/DIVx·I/O port 쓰기·bank 변경은 없다. 묶인 Bcc는 `531d8 BLT`(앞 `531d4 BGT`와 같은 `CMP.W`) 하나다.
  - 재범위 N12 행의 155와 차이(+57): 범위 안 설치 callback 본문(재범위 "미실행 설치 12(+42)" 중 범위 안 것: `52f4a` `52f80` `52f96` 사슬과 `52e9c` 사망 꼬리, `53222` 이동 상태, 자식 상태 `53bf6` `53c0a` `53cc8` `53cdc` `53dba` `53dd8` `53dec` `53e2e` 등; 결정 2), 그리고 interpreter 명령 callback `53ad0` 11 block(결정 1). [I] 재범위는 400 frame 안에 실행되는 함수 본문만 셌다.
  - 범위 안 자료 3곳은 routing하지 않는다: `52e64..52e78`(WORD 표 10개, `52e52`가 읽음), `531a2..531c2`(BYTE 표 4×4 `531a2` + LONG 설치 값 표 `531b2` 4개), `53b50..53b70`(LONG 자식 callback 표 `53b50` 2개 + LONG 애니메이션 목록 표 `53b58` 6개).
- [F] 진입:
  - node callback(재범위 미연결 callback): 부모 `53050`(stage event 표 LONG `e903c`), `53102`(`530f6 MOVE.L #53102,7c(A6)` → `531e8 MOVE.L 7c(A6),(A6)`), `53122`(`5311c`, fall-through), `531c2`(`5323e` `53296`; 범위 밖 `53362` `53678` `53796` `538b8 BRA.W`), `5327a`(`53274`, fall-through); 자식 `539f8` `53b70` `53c42` `53d14` `53e70`(`53050`의 `28ae` 자식), `53a62`(`53a5c`), `53bd2`(`53bcc`), `53ca4`(`53c9e`), `53d6c`(`53d66`), `53ed2`(`53ecc`).
  - 범위 안 설치·자식 callback(결정 2): `52f4a`(`52f44`), `52f96`(`52f76`), `52f80`(`52ed4`의 `28ae` 자식), `5310c`(범위 밖 `535fa` `5370e` `539dc`의 설치 값; `53102 JSR 3af8`의 복귀점과 같은 시작), `53222`(`5321c`), `53a44`(`53ac2`), `53ab2`(`53aac`), `53bcc`(`53c34`), `53bf6`(`53bdc`), `53c0a`(`53bec`), `53c20`(`53c1a`), `53c9e`(`53d06`), `53cc8`(`53cae`), `53cdc`(`53cbe`), `53cf2`(`53cec`), `53d66`(`53e16` `53e58`), `53dba`(`53d96`), `53dd8`(`53da6`), `53dec`(`53d76`), `53e02`(`53dfc`), `53e2e`(`53d86`), `53e44`(`53e3e`).
  - interpreter 명령 callback(고정 ROM LONG 표 `4a500`; interpreter `callback()`이 live 대상 `JSR (A1)`로 부른다): `52e78`(표 `4a5c0` = 명령 `30`, 자연 기록에서 실행됨), `53ad0`(표 `4a5c4` = 명령 `31`, 400 frame 안에 실행되지 않음; 결정 1).
  - helper(JSR/BSR 대상): `52e4a`(`5302c` `5323a` `53292 BSR.W`), `52fe4`(`53050 BSR.B`), `5317c`(`5312c JSR (PC)`), 공용 꼬리 `52e9c`(Bcc 12곳, 범위 밖 8곳 포함), `52f9c`(BRA/BCC 17곳, 범위 밖 9곳 포함), `539e4`(`53a8a` `53bf2` `53cc4` `53edc BRA.W`).
- [F] **경계 callee(실행부 없음)**: `482fa`(`52ece`), `d3802`(`52ea6` `52eee` `52f04`; A1 = `549bc` `549e0` `549ce`, 반환 A0을 뒤 block이 쓴다), `4833e`(`52f88`). 범위 밖 설치·자식 값 `5366a` `538aa` `53354` `53788`(표 `531b2`, `5316a MOVE.L D7,(A6)`), `53fa0` `5420c`(표 `53b50`, `53ae8 JSR 28ae`의 A0), `54082`(`53b36 JSR 28ae`의 A0)는 노드 LONG에 저장만 한다.
- [F] **나가는 호출(routing됨)**: cleanup `2a0a` `43e34` `8ff4` `2a24`(JMP), area_clear `4b6ec`, U08 `49274` `49290`, fade_card `28ae`(C 반환) `2a00`(JMP), U02 `8ebe`, interpreter `49f8c` `49fc6`(C 반환), U04 `43ea4`, U01 `4b54e`, U12 `490ba`, sound `3af8`, stage_area `49a58`, frame_helpers `49392`(C 반환), U14 `4a496` `16ef0`, N04 `4a46c`, N05 `49214`.
- [F] **carry**(아래 "carry" 절):
  - 소비 block **12개**: `53130`(`5317c` 반환), `53184` `5318e`(`SCS.B`, `49392` 반환), `53232` `5328a` `53abe` `53c2c` `53cfe` `53e0e` `53e50`(`49fc6` 반환), `53aee` `53b3c`(`28ae` 반환). `53184` `5318e`는 C를 읽은 뒤 `MOVEQ`/`OR.B`가 C를 지우므로 끝 C는 Unknown이다(그 C를 읽는 소비자가 없다). 나머지 10개는 FLOW_ONLY다.
  - known 생산 block **2개**: Set `53196`(`ORI.B #1,CCR; RTS`), Clear `5319c`(`ANDI.B #fe,CCR; RTS`). 둘 다 `5317c`의 반환 C이고 유일한 호출자 `5312c`의 복귀점 `53130 BCC`가 읽는다.
  - FLOW_ONLY 76개(소비자 10 포함), Unknown 134개(소비자 2 포함). 76 + 2 + 134 = 212.
- [F] 스택: `53ad0`의 `MOVE.W D0,-(A7)`·`MOVE.W D1,-(A7)`(WORD 2개), `53af2` `53b40`의 `MOVE.W (A7),D1`·`MOVE.W 2(A7),D0`(읽기만), `53b4c ADDQ.W #4,A7`(주소 레지스터 전체 +4), JSR/BSR 복귀 LONG.
- [F] 자료(모두 live bus): 고정 ROM 표 `52e64`+sext(`2·94(A6)`.W) WORD, `531a2`+sext(`4·D0.W`)+sext((`49a58` 결과 & 3)) BYTE, `531b2`+sext(`4·D0.W`) LONG, `53b58`+sext(`4·D0.W`) LONG(D0 = 부모 BYTE `9b`), `53b50`+sext(`4·D7.W`) LONG(D7 = 명령 인자 WORD). 원본은 index를 검사하지 않는다(아래 "자료"). banked LONG `200188`(5곳), `200370`(+ 그 LONG이 가리키는 주소 + 4의 LONG). work RAM: 노드 WORD `20` `46` `54` `68` `1e` `76` `78` `90` `94` `96` `98`, LONG `(A6)` `c` `22` `2e` `32` `36` `3a` `56` `7c` `80` `84` `88`, BYTE `15` `5e` `61` `9a` `9b` `9c` `9d` `9e` `9f` `a0` `a1`; 부모 노드 `c(A6)`의 BYTE `98` `9a` `9b` `9c`; `22(A6)` 기록의 LONG `90`; `28ae`·`d3802` 반환 A0 노드의 WORD `68` `1e` `76`, BYTE `9e` `a2`; A5 BYTE `5d44`; interpreter 인자 A0의 WORD 2개(`52e78`) / 3개(`53ad0`).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng` `dyn_base`, TB 시작 기준): RNG 400 frame과 base 120 frame 모두 seed 46 47만 N12에 들어온다(frame 0 `53050`부터). 212 시작 중 101개가 TB 시작으로 나타난다(TB 분할 `52fea` `52ff2` `52ff8` `52ffc` `53000` `531d8` 6개는 시작이 아니다). 실행 경로는 `53050`→`531c2`(`94` < `96` → `53248`→`5327a` 이동)·`53122`(`5317c`/`49392`→`5319c` Clear)·자식 5개(`53ed2`, `53a62`→`53a8a`, `53bd2`, `53ca4`, `53d6c`)와 interpreter 명령 `52e78`이다. 경계 `482fa` `d3802` `4833e`, 사망 꼬리 `52e9c`, `53ad0`은 실행되지 않는다.
- [F] 기준 측정(이 작업 트리 base `2dd58fd`의 `git archive` 사본, scratch 출력 `ms5-scratch/n12/fp/base_*`): base 일치 pass 12,968·node 102,054, 불일치 0, 자연 완주 119(seed 46 47은 frame 0 `53050` 첫 미연결). RNG 400: 일치 pass 40,842·node 297,783, 불일치 0, complete 102, `other` 6(seed 18 19 96 97 102 103, frame 7 `af71a` 계열 interpreter의 `unsupported animation callback target`; N12와 무관한 기존 상태, 도구 종료 코드 1).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **`53ad0`(interpreter 명령 `31`, 11 block) 포함.** [F] `53ad0`은 범위 안에서 N12 진입으로는 도달하지 않지만 interpreter 명령 callback 표 LONG `4a5c4`(routing된 interpreter가 쓰는 표, `52e78`의 다음 칸)가 가리키는 진입이다. "참조 없는 코드"가 아니므로 넣는다(N09 `b051a` 제외 선례는 참조자가 미연결 코드였다). 400 frame 안에 실행되지 않는다. 빼면 routing `539e4..53b50` 대신 `539e4..53ad0`, 201 block이고 허용 목록에도 `53ad0`을 넣지 않는다.
2. **interpreter `callback()` 허용 목록에 `52e78` `53ad0` 추가(공유 실행부 1줄; N04 결정 5a 선례).** [F] 기존 허용 목록(`3679e` `2b3e8` `2b3fa` `47672` `eb752` `eb766`) 밖 대상은 `unsupported animation callback target`이다. seed 46 47은 `53050` 계열 script가 명령 `30`으로 `52e78`을 부르므로(자연 기록 TB `52e78`), 넣지 않으면 N12 routing 뒤에도 이 오류(`cpp-error-other`)로 멈춘다. 그 밖 대상은 기존 오류 그대로다.
3. **block 수 212(재범위 155와 +57).** 범위 안 설치·자식 callback 본문을 결정 2대로 넣고(+46, 400 frame 안에 실행되지 않는 상태 포함), `53ad0`(+11)을 넣는다. 범위 밖 설치 값(`5366a` `538aa` `53354` `53788` `53fa0` `5420c` `54082`)과 그 사슬(`532a0..539e4` 등)은 고아 설치(재범위 결정 3)로 남긴다.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n12.cpp`의 `animation_objects_n12_block`. 오류는 `unsupported animation objects n12 PC`(내부 PC), `objects n12 caller requires known carry`(소비 12 block). 메인 지시와 같다.
5. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`에서 N12 범위 PC를 경계·rollback 기대로 쓰는 곳은 없다(scratch grep; 몇몇 test 표의 `52f08` `5320f` `53c6a0bb…` 등은 자료 값 일부). 기존 RNG/base 도구가 seed 46 47의 첫 미연결 `53050`을 기대 값으로 고정하지 않는다.

## 원본 바이트 근거

[F] 코드 5 범위 합계 2,302바이트. 범위 순서로 이어 붙인 SHA256 `f25803c89fe5ffb6732e19f07412242decf01e00045448a914c5f442728d3b56`.

| CPU 범위 | 바이트 | SHA256 | 시작 | 내용 |
| --- | --- | --- | --- | --- |
| `52e4a..52e64` | 26 | `4128cd48777379785333e704baba1d8f1fdef212aaf159a57b9eae1481ae8aec` | 2 | helper `52e4a` |
| `52e78..531a2` | 810 | `da8aafd70d030dcd798fdfd02c54a64243c85aef18f507173b9620de3d3fb8d2` | 69 | `52e78`, 꼬리 `52e9c` `52f9c`, 설치 `52f4a` `52f80` `52f96`, helper `52fe4`, callback `53050` `53102` `53122`, helper `5317c` |
| `531c2..532a0` | 222 | `4b6972ba2e956a7afd29bd4c109c110f8a5c1762bdaf3b632b78c03d4168e1d8` | 25 | callback `531c2` `5327a`, 설치 `53222` |
| `539e4..53b50` | 364 | `5899c6db884989d281fe140cf701bc1d14e144d4389c4418d8dd7b96550d695f` | 32 | 꼬리 `539e4`, 자식 `539f8` 계열, `53ad0` |
| `53b70..53ee0` | 880 | `5fd162d4a38f19c3e8ef9dff263a6351ba83b208e54361e59f3d49c6d2277f24` | 84 | 자식 `53b70` `53c42` `53d14` `53e70` 계열 |

- [F] 범위 안 자료(routing 밖): `52e64..52e78` = `01a4 0168 012c 00f0 00b4 0078 003c 0000 ffc4 ff88`, `531a2..531c2` = BYTE `01 01 01 00 02 02 02 03 03 03 03 00 00 00 00 01` + LONG `5366a` `538aa` `53354` `53788`, `53b50..53b70` = LONG `53fa0` `5420c` + LONG `549f2` `54a40` `54a8e` `54adc` `54b2a` `54b78`.
- [F] 범위 밖 이웃: `52e48`(앞 함수의 자료 끝, 미연결), `532a0..539e4`(0 채움 자료와 범위 밖 설치 사슬 `532xx`~`539e0`, 미연결; 고아 설치), `53ee0..`(다음 객체 함수, 미연결). 모두 `unsupported animation machine PC`다.
- [F] 범위 밖 → N12 참조(scratch `n12xref.py`, 고정 ROM 전수): `e903c`(LONG `53050`), `4a5c0`/`4a5c4`(LONG `52e78`/`53ad0`), `535fa` `5370e` `539dc`(`MOVE.L #5310c,(A6)`), `536d2`~`539ca` 8곳(`BNE.W 52e9c`), `53372`~`538c8` 9곳(`BRA.W 52f9c`), `53362` `53678` `53796` `538b8`(`BRA.W 531c2`). 모두 block 시작으로 간다. 내부 PC를 가리키는 참조는 없다(우연히 범위 값과 같은 자료 LONG·명령 operand 13곳은 코드 참조가 아니다).

## block 목록과 실행 의미

[F] 212 block. 각 줄은 block 안 명령 전체다(capstone 표기, 즉치·주소 16진). "(→x)"는 fall-through다. 태그: "C 소비"(Unknown이면 checked 오류), "Clear/Set 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호확장한다. `(PC,Dn.W)`/`(An,Dn.W)` index는 `Dn.W` 부호확장이다. `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVE.W #0,D0`은 하위 WORD만). `MOVEQ`는 LONG 전체를 쓴다. `SWAP`은 상·하위 WORD를 바꾼다. `NEG.L`/`ADD.L`/`SUB.L`은 32-bit 2의 보수, `ASR.L #5`는 부호 bit 채움 산술 shift다. 비교 분기: `BCC`(무부호 ≥), `BGT`/`BLT`(부호 있는 WORD 비교), `BPL`(결과 최상위 bit 0), `BEQ`/`BNE`(결과 0 여부). `BSET.B #n,d(A6); BNE`는 바꾸기 전 bit가 1이면 분기한다.

**부모 위치 helper `52e4a` 2**
- `52e4a`: `MOVEQ #0, d0; MOVE.W 94(a6), d0; ADD.W d0, d0; MOVE.W 52e64(pc, d0.w), d0; SWAP d0; MOVE.L d0, 32(a6); JSR 43e34.l`
- `52e62`: `RTS` — FLOW

**interpreter 명령 callback `52e78` 4**
- `52e78`: `MOVE.W (a0)+, d0; MOVE.B d0, 9c(a6); MOVEQ #0, d0; MOVE.W (a0), d0; SWAP d0; BTST.B #0, 15(a6); BEQ.W 52e90` (→`52e8e`)
- `52e8e`: `NEG.L d0` (→`52e90`)
- `52e90`: `ADD.L d0, 32(a6); JSR 43e34.l`
- `52e9a`: `RTS` — FLOW

**공용 사망 꼬리 `52e9c`(자식 `52f80` 설치) 12**
- `52e9c`: `JSR 2a0a.l` — FLOW
- `52ea2`: `LEA.L 549bc(pc), a1; JSR d3802.l` — FLOW
- `52eac`: `MOVE.W #e0ed, 68(a0); MOVE.W #e0ed, 1e(a0); JSR 4b6ec.l`
- `52ebe`: `JSR 49274.l` — FLOW
- `52ec4`: `BCLR.B #2, 9d(a6); ST.B 5d44(a5); JSR 482fa.l` — FLOW
- `52ed4`: `MOVEA.L #52f80, a0; MOVE.W #0, d0; JSR 28ae.l`
- `52ee4`: `MOVE.W #3c, 76(a0); LEA.L 549e0(pc), a1; JSR d3802.l`
- `52ef4`: `MOVE.W #e0ed, 68(a0); MOVE.W #e0ed, 1e(a0); LEA.L 549ce(pc), a1; JSR d3802.l`
- `52f0a`: `MOVE.W #e0ec, 68(a0); MOVE.W #e0ec, 1e(a0); JSR 8ff4.l`
- `52f1c`: `MOVE.W #d28, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `52f2a`: `MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 90(a1), a1; JSR 49f8c.l`
- `52f40`: `CLR.L 36(a6); MOVE.L #52f4a, (a6)` (→`52f4a`)

**설치 callback `52f4a` 6**
- `52f4a`: `JSR 4b6ec.l` — FLOW
- `52f50`: `MOVE.L #ffff0000, d1; SUB.L 3a(a6), d1; ASR.L #5, d1; ADD.L d1, 3a(a6); JSR 43ea4.l`
- `52f66`: `JSR 49fc6.l` — FLOW
- `52f6c`: `CMPI.W #a0, 46(a6); BGT.W 52f7c` (→`52f76`)
- `52f76`: `MOVE.L #52f96, (a6)` (→`52f7c`)
- `52f7c`: `BRA.W 52f9c` — FLOW

**`28ae` 자식 `52f80` 4**
- `52f80`: `SUBQ.W #1, 76(a6); BPL.W 52f94` (→`52f88`)
- `52f88`: `JSR 4833e.l` — FLOW
- `52f8e`: `JMP 2a00.l` — FLOW
- `52f94`: `RTS` — FLOW

**설치 callback `52f96` 1**
- `52f96`: `JMP 2a24.l` — FLOW

**공용 꼬리 `52f9c` 9**
- `52f9c`: `MOVE.W 54(a6), d0; CMP.W 78(a6), d0; BCC.W 52fb6` (→`52fa8`)
- `52fa8`: `BSET.B #1, 9d(a6); BNE.W 52fb6` (→`52fb2`) — FLOW
- `52fb2`: `ST.B 9f(a6)` (→`52fb6`) — FLOW
- `52fb6`: `BTST.B #0, 9d(a6); BNE.W 52fe2` (→`52fc0`) — FLOW
- `52fc0`: `BTST.B #7, 61(a6); BEQ.W 52fd8` (→`52fca`) — FLOW
- `52fca`: `MOVE.L #0, 56(a6); BSET.B #0, 9d(a6)` (→`52fd8`)
- `52fd8`: `JSR 4b54e.l` — FLOW
- `52fde`: `CLR.B 5e(a6)` (→`52fe2`)
- `52fe2`: `RTS` — FLOW

**초기화 helper `52fe4` 4**
- `52fe4`: `MOVE.W #173, 20(a6); MOVE.L 200188.l, 22(a6); MOVEA.L 200370.l, a0; MOVEA.L 4(a0), a0; MOVE.L a0, 56(a6); LEA.L 55a82.l, a0; JSR 490ba.l`
- `5300c`: `MOVE.W d0, 54(a6); LEA.L 55acc.l, a0; JSR 490ba.l`
- `5301c`: `MOVE.W d0, 78(a6); MOVE.W #0, 98(a6); MOVE.W #0, 94(a6); BSR.W 52e4a`
- `53030`: `MOVE.L #1280000, 2e(a6); ST.B 9a(a6); MOVE.B #ff, 9b(a6); MOVE.W #ffff, 90(a6); MOVE.B #a, a1(a6); RTS`

**부모 callback `53050` 10**
- `53050`: `BSR.B 52fe4` — FLOW
- `53052`: `MOVE.W #d25, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `53060`: `MOVE.W #922, d0; JSR 4a496.l`
- `5306a`: `BSET.B #6, 15(a6); MOVE.W #800, 68(a6); MOVE.W #800, 1e(a6); JSR 16ef0.l`
- `53082`: `MOVEA.L #53e70, a0; MOVE.W #0, d0; JSR 28ae.l`
- `53092`: `MOVEA.L #539f8, a0; MOVE.W #0, d0; JSR 28ae.l`
- `530a2`: `MOVEA.L #53b70, a0; MOVE.W #0, d0; JSR 28ae.l`
- `530b2`: `MOVE.B #0, 9e(a0); MOVE.L a0, 84(a6); MOVEA.L #53c42, a0; MOVE.W #0, d0; JSR 28ae.l`
- `530cc`: `MOVE.B #0, 9e(a0); MOVE.L a0, 80(a6); MOVEA.L #53d14, a0; MOVE.W #0, d0; JSR 28ae.l`
- `530e6`: `MOVE.B #0, 9e(a0); MOVE.L a0, 88(a6); MOVE.W #2, 96(a6); MOVE.L #53102, 7c(a6); BRA.W 531c2`

**callback `53102`/`53122`(설치) 14**
- `53102`: `MOVE.W #19d4, d0; JSR 3af8.l`
- `5310c`: `MOVEA.L #54e12, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `5311c`: `MOVE.L #53122, (a6)` (→`53122`)
- `53122`: `BTST.B #0, 9d(a6); BNE.W 52e9c` (→`5312c`) — FLOW
- `5312c`: `JSR 5317c(pc)` — FLOW
- `53130`: `BCC.W 5316c` (→`53134`) — C 소비
- `53134`: `MOVE.W 90(a6), d0; CMPI.W #ffff, d0; BNE.W 53148` (→`53140`)
- `53140`: `MOVE.W #0, d0; BRA.W 5315e`
- `53148`: `ADD.W d0, d0; ADD.W d0, d0; LEA.L 531a2(pc, d0.w), a0; JSR 49a58.l`
- `53156`: `ANDI.W #3, d0; MOVE.B (a0, d0.w), d0` (→`5315e`)
- `5315e`: `MOVE.W d0, 90(a6); ADD.W d0, d0; ADD.W d0, d0; MOVE.L 531b2(pc, d0.w), d7; MOVE.L d7, (a6)` (→`5316c`)
- `5316c`: `JSR 43e34.l` — FLOW
- `53172`: `JSR 49fc6.l` — FLOW
- `53178`: `BRA.W 52f9c` — FLOW

**C 반환 helper `5317c` 5**
- `5317c`: `MOVEQ #0, d0; JSR 49392.l`
- `53184`: `SCS.B d7; MOVEQ #1, d0; JSR 49392.l` — C 소비 (끝 C Unknown)
- `5318e`: `SCS.B d0; OR.B d7, d0; BEQ.W 5319c` (→`53196`) — C 소비 (끝 C Unknown)
- `53196`: `ORI.B #1, ccr; RTS` — Set 생산
- `5319c`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**callback `531c2`/`5327a`(설치)와 이동 상태 `53222` 25**
- `531c2`: `BTST.B #0, 9d(a6); BNE.W 52e9c` (→`531cc`) — FLOW
- `531cc`: `MOVE.W 94(a6), d0; CMP.W 96(a6), d0; BGT.W 531f0; BLT.W 53248` (→`531dc`)
- `531dc`: `JSR 43e34.l` — FLOW
- `531e2`: `JSR 49fc6.l` — FLOW
- `531e8`: `MOVE.L 7c(a6), (a6); BRA.W 52f9c`
- `531f0`: `TST.B 9f(a6); BNE.W 5320c` (→`531f8`)
- `531f8`: `MOVEA.L #551ea, a1; MOVE.W #140, d0; JSR 49f8c.l`
- `53208`: `BRA.W 5321c` — FLOW
- `5320c`: `MOVEA.L #551ea, a1; MOVE.W #200, d0; JSR 49f8c.l`
- `5321c`: `MOVE.L #53222, (a6)` (→`53222`)
- `53222`: `BTST.B #0, 9d(a6); BNE.W 52e9c` (→`5322c`) — FLOW
- `5322c`: `JSR 49fc6.l` — FLOW
- `53232`: `BCC.W 52f9c` (→`53236`) — C 소비
- `53236`: `SUBQ.W #1, 94(a6); BSR.W 52e4a`
- `5323e`: `MOVE.L #531c2, (a6); BRA.W 52f9c`
- `53248`: `TST.B 9f(a6); BNE.W 53264` (→`53250`)
- `53250`: `MOVEA.L #54ed8, a1; MOVE.W #140, d0; JSR 49f8c.l`
- `53260`: `BRA.W 53274` — FLOW
- `53264`: `MOVEA.L #54ed8, a1; MOVE.W #1c0, d0; JSR 49f8c.l`
- `53274`: `MOVE.L #5327a, (a6)` (→`5327a`)
- `5327a`: `BTST.B #0, 9d(a6); BNE.W 52e9c` (→`53284`) — FLOW
- `53284`: `JSR 49fc6.l` — FLOW
- `5328a`: `BCC.W 52f9c` (→`5328e`) — C 소비
- `5328e`: `ADDQ.W #1, 94(a6); BSR.W 52e4a`
- `53296`: `MOVE.L #531c2, (a6); BRA.W 52f9c`

**자식 공용 꼬리 `539e4` 4**
- `539e4`: `JSR 43e34.l` — FLOW
- `539ea`: `JSR 49fc6.l` — FLOW
- `539f0`: `JSR 4a46c.l` — FLOW
- `539f6`: `RTS` — FLOW

**자식 callback `539f8`(설치 `53a44` `53a62` `53ab2`) 17**
- `539f8`: `MOVE.W #173, 20(a6); MOVE.L 200188.l, 22(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `53a14`: `MOVE.W #d25, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `53a22`: `MOVE.W #922, d0; JSR 4a496.l`
- `53a2c`: `BSET.B #6, 15(a6); MOVE.W #803, 68(a6); MOVE.W #803, 1e(a6); JSR 16ef0.l`
- `53a44`: `MOVEA.L #54bc6, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53a54`: `MOVEA.L c(a6), a0; ST.B 9a(a0); MOVE.L #53a62, (a6)` (→`53a62`)
- `53a62`: `MOVEA.L c(a6), a0; MOVE.B 98(a0), d0; ANDI.B #1f, d0; MOVE.B d0, 9c(a6); MOVEQ #0, d0; MOVE.B 9b(a0), d0; CMPI.B #ff, d0; BEQ.W 53a8a` (→`53a80`)
- `53a80`: `MOVE.B #ff, 9b(a0); BRA.W 53a8e`
- `53a8a`: `BRA.W 539e4` — FLOW
- `53a8e`: `LEA.L 53b58(pc), a1; ADD.W d0, d0; ADD.W d0, d0; MOVEA.L (a1, d0.w), a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53aa4`: `MOVEA.L c(a6), a0; CLR.B 9a(a0); MOVE.L #53ab2, (a6)` (→`53ab2`)
- `53ab2`: `JSR 43e34.l` — FLOW
- `53ab8`: `JSR 49fc6.l` — FLOW
- `53abe`: `BCC.W 53ac8` (→`53ac2`) — C 소비
- `53ac2`: `MOVE.L #53a44, (a6)` (→`53ac8`)
- `53ac8`: `JSR 4a46c.l` — FLOW
- `53ace`: `RTS` — FLOW

**interpreter 명령 callback `53ad0` 11**
- `53ad0`: `MOVE.W (a0)+, d7; MOVE.W (a0)+, d0; MOVE.W (a0)+, d1; MOVE.W d0, -(a7); MOVE.W d1, -(a7); ADD.W d7, d7; ADD.W d7, d7; MOVE.L 53b50(pc, d7.w), d7; MOVEA.L d7, a0; MOVE.W #a, d0; JSR 28ae.l`
- `53aee`: `BCC.W 53b2c` (→`53af2`) — C 소비
- `53af2`: `ADDQ.B #1, a0(a6); MOVE.W (a7), d1; MOVE.W 2(a7), d0; JSR 49214.l`
- `53b02`: `CLR.B a2(a0); TST.B a1(a6); BNE.W 53b28` (→`53b0e`)
- `53b0e`: `MOVE.B #ff, a2(a0); LEA.L 55a38.l, a0; JSR 490ba.l`
- `53b20`: `MOVE.B d0, a1(a6); BRA.W 53b2c`
- `53b28`: `SUBQ.B #1, a1(a6)` (→`53b2c`)
- `53b2c`: `MOVEA.L #54082, a0; MOVE.W #1e, d0; JSR 28ae.l`
- `53b3c`: `BCC.W 53b4c` (→`53b40`) — C 소비
- `53b40`: `MOVE.W (a7), d1; MOVE.W 2(a7), d0; JSR 49214.l`
- `53b4c`: `ADDQ.W #4, a7; RTS`

**자식 callback `53b70`(설치 `53bcc` `53bd2` `53bf6` `53c0a` `53c20`) 21**
- `53b70`: `MOVE.W #173, 20(a6); MOVE.L 200188.l, 22(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `53b8c`: `MOVE.W #d25, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `53b9a`: `MOVE.W #922, d0; JSR 4a496.l`
- `53ba4`: `BSET.B #6, 15(a6); MOVE.W #804, 68(a6); MOVE.W #804, 1e(a6); JSR 16ef0.l`
- `53bbc`: `MOVEA.L #554fc, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53bcc`: `MOVE.L #53bd2, (a6)` (→`53bd2`)
- `53bd2`: `CMPI.B #1, 9e(a6); BNE.W 53be2` (→`53bdc`)
- `53bdc`: `MOVE.L #53bf6, (a6)` (→`53be2`)
- `53be2`: `CMPI.B #2, 9e(a6); BNE.W 53bf2` (→`53bec`)
- `53bec`: `MOVE.L #53c0a, (a6)` (→`53bf2`)
- `53bf2`: `BRA.W 539e4` — FLOW
- `53bf6`: `MOVEA.L #55506, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53c06`: `BRA.W 53c1a` — FLOW
- `53c0a`: `MOVEA.L #555ac, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53c1a`: `MOVE.L #53c20, (a6)` (→`53c20`)
- `53c20`: `JSR 43e34.l` — FLOW
- `53c26`: `JSR 49fc6.l` — FLOW
- `53c2c`: `BCC.W 53c3a` (→`53c30`) — C 소비
- `53c30`: `CLR.B 9e(a6); MOVE.L #53bcc, (a6)` (→`53c3a`)
- `53c3a`: `JSR 4a46c.l` — FLOW
- `53c40`: `RTS` — FLOW

**자식 callback `53c42`(설치 `53c9e` `53ca4` `53cc8` `53cdc` `53cf2`) 21**
- `53c42`: `MOVE.W #173, 20(a6); MOVE.L 200188.l, 22(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `53c5e`: `MOVE.W #d25, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `53c6c`: `MOVE.W #922, d0; JSR 4a496.l`
- `53c76`: `BSET.B #6, 15(a6); MOVE.W #801, 68(a6); MOVE.W #801, 1e(a6); JSR 16ef0.l`
- `53c8e`: `MOVEA.L #55652, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53c9e`: `MOVE.L #53ca4, (a6)` (→`53ca4`)
- `53ca4`: `CMPI.B #1, 9e(a6); BNE.W 53cb4` (→`53cae`)
- `53cae`: `MOVE.L #53cc8, (a6)` (→`53cb4`)
- `53cb4`: `CMPI.B #2, 9e(a6); BNE.W 53cc4` (→`53cbe`)
- `53cbe`: `MOVE.L #53cdc, (a6)` (→`53cc4`)
- `53cc4`: `BRA.W 539e4` — FLOW
- `53cc8`: `MOVEA.L #55662, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53cd8`: `BRA.W 53cec` — FLOW
- `53cdc`: `MOVEA.L #556d2, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53cec`: `MOVE.L #53cf2, (a6)` (→`53cf2`)
- `53cf2`: `JSR 43e34.l` — FLOW
- `53cf8`: `JSR 49fc6.l` — FLOW
- `53cfe`: `BCC.W 53d0c` (→`53d02`) — C 소비
- `53d02`: `CLR.B 9e(a6); MOVE.L #53c9e, (a6)` (→`53d0c`)
- `53d0c`: `JSR 4a46c.l` — FLOW
- `53d12`: `RTS` — FLOW

**자식 callback `53d14`(설치 `53d66` `53d6c` `53dba` `53dd8` `53dec` `53e02` `53e2e` `53e44`) 35**
- `53d14`: `MOVE.W #173, 20(a6); MOVE.L 200188.l, 22(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `53d30`: `MOVE.W #d29, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `53d3e`: `BSET.B #6, 15(a6); MOVE.W #802, 68(a6); MOVE.W #802, 1e(a6); JSR 16ef0.l`
- `53d56`: `MOVEA.L #55732, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53d66`: `MOVE.L #53d6c, (a6)` (→`53d6c`)
- `53d6c`: `CMPI.B #3, 9e(a6); BNE.W 53d7c` (→`53d76`)
- `53d76`: `MOVE.L #53dec, (a6)` (→`53d7c`)
- `53d7c`: `CMPI.B #4, 9e(a6); BNE.W 53d8c` (→`53d86`)
- `53d86`: `MOVE.L #53e2e, (a6)` (→`53d8c`)
- `53d8c`: `CMPI.B #5, 9e(a6); BNE.W 53d9c` (→`53d96`)
- `53d96`: `MOVE.L #53dba, (a6)` (→`53d9c`)
- `53d9c`: `CMPI.B #6, 9e(a6); BNE.W 53dac` (→`53da6`)
- `53da6`: `MOVE.L #53dd8, (a6)` (→`53dac`)
- `53dac`: `JSR 43e34.l` — FLOW
- `53db2`: `JSR 49fc6.l` — FLOW
- `53db8`: `RTS` — FLOW
- `53dba`: `MOVE.W #188d, d0; JSR 3af8.l`
- `53dc4`: `MOVEA.L #557c6, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53dd4`: `BRA.W 53dfc` — FLOW
- `53dd8`: `MOVEA.L #55854, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53de8`: `BRA.W 53dfc` — FLOW
- `53dec`: `MOVEA.L #5573c, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53dfc`: `MOVE.L #53e02, (a6)` (→`53e02`)
- `53e02`: `JSR 43e34.l` — FLOW
- `53e08`: `JSR 49fc6.l` — FLOW
- `53e0e`: `BCC.W 53e2c` (→`53e12`) — C 소비
- `53e12`: `CLR.B 9e(a6); MOVE.L #53d66, (a6); MOVEA.L #55798, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53e2c`: `RTS` — FLOW
- `53e2e`: `MOVEA.L #558e2, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53e3e`: `MOVE.L #53e44, (a6)` (→`53e44`)
- `53e44`: `JSR 43e34.l` — FLOW
- `53e4a`: `JSR 49fc6.l` — FLOW
- `53e50`: `BCC.W 53e6e` (→`53e54`) — C 소비
- `53e54`: `CLR.B 9e(a6); MOVE.L #53d66, (a6); MOVEA.L #55732, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53e6e`: `RTS` — FLOW

**자식 callback `53e70`(설치 `53ed2`) 7**
- `53e70`: `MOVE.W #173, 20(a6); MOVE.L 200188.l, 22(a6); MOVE.W #0, d0; MOVE.W #0, d1; JSR 49290.l`
- `53e8c`: `MOVE.W #d25, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `53e9a`: `MOVE.W #922, d0; JSR 4a496.l`
- `53ea4`: `BSET.B #6, 15(a6); MOVE.W #805, 68(a6); MOVE.W #805, 1e(a6); JSR 16ef0.l`
- `53ebc`: `MOVEA.L #54ccc, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `53ecc`: `MOVE.L #53ed2, (a6)` (→`53ed2`)
- `53ed2`: `MOVEA.L c(a6), a0; MOVE.B 9c(a0), 9c(a6); BRA.W 539e4`


## carry

- [F] **소비 12 block.** Unknown C로 들어오면 `objects n12 caller requires known carry`(상태 보존)다.
  - `53130 BCC.W 5316c`: `5317c`가 돌려준 C(아래 생산 2개). Clear → `5316c`, Set → `53134`.
  - `53184 SCS.B D7`: `49392`(frame_helpers, `4939e` Clear / `493b6` Set)가 돌려준 C로 `D7.B` = `ff`(Set)/`00`(Clear). 이어서 `MOVEQ #1,D0`이 C를 지우고 `JSR 49392`로 간다. 끝 C는 Unknown으로 둔다(이 C를 읽는 소비자가 없다; `49392`가 새로 만든다).
  - `5318e SCS.B D0; OR.B D7,D0; BEQ.W 5319c`: `49392` C로 `D0.B`, `OR.B`로 둘을 합쳐 0이면 `5319c`, 아니면 `53196`. 끝 C는 Unknown(다음 block이 새로 만든다).
  - `53232` `5328a` `53abe` `53c2c` `53cfe` `53e0e` `53e50 BCC.W`: interpreter `49fc6`의 C. Clear → 분기 대상, Set → fall-through.
  - `53aee` `53b3c BCC.W`: fade_card `28ae`의 C. Clear → 분기 대상(`53b2c`/`53b4c`), Set → fall-through(`53af2`/`53b40`).
- [F] **known 생산 2 block.** `53196 ORI.B #1,CCR; RTS`(Set), `5319c ANDI.B #fe,CCR; RTS`(Clear). [F] `5317c`의 유일한 호출자는 `5312c JSR 5317c(PC)`이고 복귀점 `53130`이 바로 `BCC`로 읽는다. 단위 test와 실제 ROM 차분은 이 C를 `53130`의 native 분기 결과로 확인한다(Unicorn SR로 단정하지 않는다). [I] `5317c`는 두 선수(`49392` D0 = 0/1)의 BYTE `568e(A5)` bit 중 하나라도 서 있으면 Set을 돌려준다(선수 참여 여부로 보임).
- [F] **FLOW_ONLY 76 block**(C 보존): JSR/BSR/BRA/JMP/RTS block, `LEA`+`JSR` `52ea2`, BTST/BSET/BCLR(Z만)+Bcc·ST block `52ec4` `52fa8` `52fb2` `52fb6` `52fc0` `53122` `531c2` `53222` `5327a`, 소비 BCC 10개. 목록: `52e62 52e9a 52e9c 52ea2 52ebe 52ec4 52f4a 52f66 52f7c 52f88 52f8e 52f94 52f96 52fa8 52fb2 52fb6 52fc0 52fd8 52fe2 53050 53122 5312c 53130 5316c 53172 53178 531c2 531dc 531e2 53208 53222 5322c 53232 53260 5327a 53284 5328a 539e4 539ea 539f0 539f6 53a8a 53ab2 53ab8 53abe 53ac8 53ace 53aee 53b3c 53bf2 53c06 53c20 53c26 53c2c 53c3a 53c40 53cc4 53cd8 53cf2 53cf8 53cfe 53d0c 53d12 53dac 53db2 53db8 53dd4 53de8 53e02 53e08 53e0e 53e2c 53e44 53e4a 53e50 53e6e`.
- [F] **Unknown 134 block**: 그 밖 `MOVE`/`MOVEQ`/`MOVEA`+`MOVE`/`CLR`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDQ`/`SUB`/`SUBQ`/`NEG`/`ASR`/`ANDI`/`SWAP`/`OR`+Bcc block, `MOVE.L #imm,(A6)` 설치 block, `MOVE.L 7c(A6),(A6)`, `MOVEA.L #imm,A0`+`MOVE.W`+`JSR 28ae` 자식 block, 애니메이션 `MOVEA.L #imm,A1`+`MOVE.W`+`JSR 49f8c` block, `ADDQ.W #4,A7; RTS`(`53b4c`), 소비 뒤 C를 지우는 `53184` `5318e`.
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 Bcc로 시작하는 곳은 위 C 소비 10곳뿐이다).

## 구현 범위와 규약

- routing 5 범위(위 표). 짝수 PC 1,151개 중 block 시작 212, 내부 939. 내부 PC 직접 진입은 `unsupported animation objects n12 PC`다. 범위 이웃과 범위 안 자료는 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. `NEG`/`SUB`/`ADD`/`ASR`는 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다(`BGT`/`BLT`는 부호 있는 WORD 비교, `52f6c`의 `CMPI.W #a0,46(A6); BGT`는 sext(`46`) > `a0`).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 FLOW_ONLY 76개와 `53184` `5318e`를 넣는다(78개). `53184` `5318e`는 실행 뒤 C를 Unknown으로 둔다. `53196` `5319c`는 known Set/Clear를 둔다.
- 제어 이동은 모두 정적이다. 설치 값(`MOVE.L #imm,(A6)`, `MOVE.L 7c(A6),(A6)`, `MOVE.L D7,(A6)`)은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `28ae` 자식 대상(A0)도 자료다. 경계 callee로 가는 `JSR`은 복귀 LONG을 쌓고 PC를 경계로 둔다. 다음 dispatch에서 실행부가 없으므로 stop이면 멈추고 아니면 `unsupported animation machine PC`로 rollback한다.
- interpreter 명령 callback `52e78` `53ad0`은 interpreter `callback()`이 `am_call`로 들어온다(A0 = 명령 인자 주소, 복귀 `4a354`/`4a43e`). 허용 목록에 두 PC를 더한다(결정 2).
- 스택: JSR/BSR 복귀 LONG, `53ad0`의 WORD push 2개(`A7` −2씩, D0 먼저), `(A7)`/`2(A7)` 읽기, `53b4c ADDQ.W #4,A7`(`A7` + 4). work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] 고정 ROM 표(원본은 index 범위를 검사하지 않는다; C++는 주소를 고정하지 않고 live bus로 읽는다):
  - `52e4a`: `D0 = 0`, `D0.W = 94(A6)`, `ADD.W` → index sext(`2·94`.W); WORD `52e64`+index를 `D0.W`로, `SWAP` → `D0 = WORD << 16`, `32(A6)`에 LONG. [I] `94` = 0~9(이동 칸 번호; `531cc`에서 `96`과 비교, `53236`/`5328e`에서 ±1)이면 `01a4`…`ff88`(y 위치 표).
  - `53148`/`53156`: `D0.W = 90(A6)`(`ffff`가 아니면) ×4 → A0 = `531a2`+sext; `49a58`(난수) 결과 `D0.W & 3`을 index로 BYTE 하나 → `D0.B`. `90 = ffff`면 `D0.W = 0`. `5315e`: `90(A6) = D0.W`, LONG `531b2`+sext(`4·D0.W`) → `D7` → `(A6)`. [I] 상태 `90` = 0~3과 난수 2 bit로 다음 상태(표 `531a2` 4×4)를 고르고 상태별 callback `5366a` `538aa` `53354` `53788`을 설치한다.
  - `53a8e`: `D0` = 부모 BYTE `9b`(0~`fe`; `ff`면 `539e4`), ×4 → LONG `53b58`+sext → A1(애니메이션 목록, `49f8c`). 원본 표는 6칸이다.
  - `53ad0`: `D7.W` = 인자 첫 WORD ×4 → LONG `53b50`+sext → A0(`28ae` 자식 callback). 원본 표는 2칸이다.
- [F] banked window(live bus; bank 기준 `200000`/`300000` 등 현재 PVC bank): LONG `200188` → `22(A6)`(`52fe4` `539f8` `53b70` `53c42` `53d14` `53e70`), LONG `200370` → A0, 그 A0 + 4의 LONG → A0 → `56(A6)`(`52fe4`).
- [F] 주소만 넘기는 고정 ROM 자료: 애니메이션 목록 `54e12` `551ea` `54ed8` `54bc6` `554fc` `55506` `555ac` `55652` `55662` `556d2` `55732` `557c6` `55854` `5573c` `55798` `558e2` `54ccc`(A1, `49f8c`), `490ba` 표 `55a82` `55acc` `55a38`(A0), 경계 `d3802` 인자 `549bc` `549e0` `549ce`(A1).
- [F] 상수 쓰기: `20(A6)` = `173`, `68`/`1e` = `800`(부모) `803` `804` `801` `802` `805`(자식), `e0ed`/`e0ec`(`d3802` 반환 노드), `2e` = `1280000`, `90` = `ffff`, `96` = 2, `a1` = `a`, `9b` = `ff`, `76(A0)` = `3c`(`52f80` 자식). 소리 `8ebe` D0 = `d25`/`d28`/`d29`, `3af8` D0 = `19d4`/`188d`, `4a496` D0 = `922`.
- [I] 게임 의미: `53050`은 위·아래로 움직이는 부모 객체(5 자식 부품 `539f8` `53b70` `53c42` `53d14` `53e70`, 각자 `9e` 상태로 애니메이션 전환)다. `9d` bit 0은 파괴 표시(`52fb6`·`53122` 등 → `52e9c` 사망 처리: 폭발 `d3802` 3개, 소리 `d28`, 점수 `482fa`, 잔해 자식 `52f80`)이고 `54`/`78` 비교(`52f9c`)는 피해 누적으로 보인다. 확인하지 않았다.

## 의존·경계

- [F] N12 → 기존(모두 routing됨): 위 "나가는 호출". C를 돌려받아 소비하는 callee: `49392` `49fc6` `28ae`, 내부 `5317c`.
- [F] 실행부 없는 경계: `482fa`(`52ec4`), `d3802`(`52ea2` `52ee4` `52ef4`), `4833e`(`52f88`). 단위 test는 이 PC의 stop 성립만 확인한다(F4 시험 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N12: stage event 표(`e903c`, `53050`), interpreter 명령 callback 표(`52e78` `53ad0`). 범위 밖 미연결 설치 사슬(`532a0..539e4`)이 `52e9c` `52f9c` `531c2` `5310c`로 들어온다(그 사슬은 고아 설치로 남는다).
- [F] N11과 경계·범위가 겹치지 않는다. N12는 N11 PC를 부르지 않는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 212 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 2개, 소비 뒤 Unknown 2개, 그 밖 Unknown), zero-step, 내부 939 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 경계 `482fa` `d3802` `4833e`는 stop만, 소비 12곳의 Unknown carry 오류. 고정 ROM 표·bank LONG은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. `5317c` 생산 C는 실제 소비자 `53130`의 native 분기로 확인한다(`5312c`에서 `49392`를 따라 들어감).
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(callback, 설치 상태, interpreter 명령 진입, 실제 표·bank LONG, 소비자 native 분기).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, complete +2(46 47) 기대(재범위 행).

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n12.cpp`(SHA256 `8f771e17364ed66deb8b8c532200b15dfc7d330f069dbdc7011e4006a2be07c9`), 새 `engine/tests/animation_machine_objects_n12_test.cpp`(SHA256 `82e16fbf149c917c232ed058349a3fce499ca07e4738afb1ae35409fc3f2ef5e`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 5 범위, carry 보존 case group 1개 78 PC), `engine/src/animation_machine_internal.h`(선언 1줄), `engine/src/animation_machine_interpreter.cpp`(허용 목록에 `52e78` `53ad0`, 결정 2), `Makefile`(source 목록·test target·실행 줄), `tools/verify_animation_machine.py`(SOURCES). 공개 header 변경 없음. 무효화 탐침 없음(결정 5).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0. 새 test: `animation machine objects n12: 548 fixtures (19 checked errors, 132 kept C), 212 blocks, 2787 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen.py`, Unicorn + 합성 물리 바이트 `52e64` `531a2` `531b2` `53b50` `53b58`, 표 밖 index 탐침 `56e64` `4ee64` `571a2` `571b2` `57b50` `53f50`, bank LONG `200188` `200370`): 212 시작 모두 fixture 진입 또는 경로로 덮임. block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류, Unknown C는 소비 12곳에서 정확한 오류, zero-step 212×3, 내부 939 PC 정확한 오류, 홀수 PC, RAM rollback 탐침 `10fe10` `10fe20` `10fe30` `10fe40`, routing 밖 자료 `52e48` `52e64` `52e76` `531a2` `531c0` `53b50` `53b6e`, 경계 `482fa` `d3802` `4833e` stop만. 실제 생산자 사슬 10건(`5312c`에서 frame_helpers `49392`를 따라 `5317c` → `53196`/`5319c` → RTS → 실제 소비자 `53130`)에서 native 분기가 계약과 같다(568e bit 0/1 모두 0 → Clear → `5316c`, 하나라도 1 → Set → `53134`). 돌연변이 확인: `52f6c` 부호 비교를 무부호로, `5319c` C 반전, `52f50` `ASR` 부호 채움 누락, `5318e` 끝 C Unknown 누락, `53af2` D0/D1 맞바꿈이 모두 test에서 실패했다.
- [F] 실제 ROM 차분(`realrom/real12.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건): 불일치 0/0/0. 시작 도달 211/212/212(seed 1은 `53dd8` 미도달, 2·3에서 도달). native stop: STOP, 경계 `d3802`(176/194/176) `482fa` `4833e`, U02 미연결 `8ec8`, `2a00`/`2a24`. 실제 생산자 뒤 소비자 native 분기 비교: seed 1 기준 `53130` 72, `53184` 76, `5318e` 84, `53232` 27, `5328a` 21, `53abe` 31, `53aee` 67, `53b3c` 84, `53c2c` 34, `53cfe` 45, `53e0e` 58, `53e50` 39건. 실제 bank LONG `200188`/`200370`과 실제 표, interpreter(`49f8c`/`49fc6`) script, `28ae`, `49392`, `490ba`, `49214`를 실제로 거친다. 의도한 차이: native 주소 레지스터가 홀수인 interpreter 목록(임의 `9b`로 표 `53b58` 밖 LONG을 읽은 경우; 68000 address error를 Unicorn이 흉내 내지 않음)에서 C++ checked 오류 `unsupported animation command or dispatch alignment` 0/1/1건. 하네스 주: native stop 판정은 다른 실행부 block 안의 직선 후속 PC(`e90d0` 등, 단일 PC routing `e90ca`의 내부)를 dispatch 지점으로 보지 않는다. `2986` caller-X 차이 0건, port 쓰기 비교 포함.
- [F] 기준(`2dd58fd` `git archive` 사본 `ms5-scratch/n12/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 12,968·node 102,054, 불일치 0, 자연 완주 119. N12 뒤: 일치 pass 13,208·node 104,470, 불일치 0, 회귀 0, 자연 완주 **121**(+46 47; frame 0 `53050` 첫 미연결 → 120 frame 완주).
- [F] RNG 초기화 400 frame 차분: 기준 complete 102, 일치 pass 40,842·node 297,783, 불일치 0. N12 뒤 complete **104**(+46 47, 각 400 frame), 일치 pass 41,642·node 303,559, 불일치 0, 회귀 0, 그 밖 seed 분류·pass·node 변화 0. `other` 6(seed 18 19 96 97 102 103, frame 7 `af71a` 계열 interpreter의 `unsupported animation callback target`)은 기준과 같다(도구 종료 코드 1도 기준과 같음; N12와 무관). verification.json SHA256 기준 `76fba9ec70e45c235fc6a286bd5f99af30f75a5ae2fb3a24267a35738918517e`, N12 뒤 `5c81f9e57aa278e6ad352074680d692c56f0f311214b3bfa671699026581ae81`.
- [F] ROM SHA256·mtime 작업 전후 같음.

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] 고정 ROM 표 index의 실제 범위(`94` `90` `9b` 인자 WORD). 원본은 검사하지 않으므로 C++도 검사하지 않고 live bus로 읽는다.
3. [U] 범위 밖 설치 사슬 `5366a` `538aa` `53354` `53788`(그리고 그 사슬이 쓰는 `532a0..539e4`), 자식 `53fa0` `5420c` `54082`, 경계 `482fa` `d3802` `4833e`의 동작은 해당 단위 계약에서 정한다.
4. [U] `53ad0`을 부르는 interpreter script(명령 `31`)는 400 frame 자연 기록에 없다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n12/`(`n12.py` block·범위 계산, `n12stat.py` 범위 SHA·짝수 PC, `n12cls.py` carry 분류, `n12fmt.py` block 목록, `n12xref.py` 범위 밖 참조, `refs12.py`, `gen/` typed fixture 생성·test 조립, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스·RNG 차분, `mut/` 돌연변이 확인; 저장소 밖).
