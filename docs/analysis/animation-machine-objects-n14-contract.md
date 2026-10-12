# 객체 callback F4 N14: `a5e80` 계열 객체(옛 U29+U28 일부) — stage event callback `a5e62` `a5e6c` `a5e76` `a5e80`, 설치 callback `a60c8` `a6a0c` `a6e7e`, `28ae` 자식 callback `a6dd4`, callback `be0c4`/`be110`, 공용 helper `4970a` `4972c` `4b702` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N14 행(191 block, `4970a..4976e` `4b702..4b70a` `a5cf6..a6172` `a6914..a6ac6` `a6dd4..a6eea` `a7256..a725c` `be0c4..be13c`, callback `a5e80` `a60c8` `a6dd4` `a6e7e` `be0c4` `be110`, 경계 callee 없음, bank 2, 미실행 설치 7(+150), 새 seed 30 31 / 30 31, 옛 U29 177·U28 14)과 메인 결정 1·2(이름 `objects-n14`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 단위 형식과 규약은 N12 계약(SHA256 `e0f432b4768d3fa7f62e65e899802427275df22bac00fca18c7bd65ded4cc0e9`)을 따른다. 메인 작업 지시: flag 재계산은 선행이 유일할 때만(아니면 각 선행에 접어 넣음), 범위 안 미참조 코드는 routing하지 않고 참조된 범위 안 진입은 넣는다, RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가), interpreter 명령 callback은 routing 판정에 맡긴다(`animation_machine_interpreter.cpp` 수정 없음).
- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback과 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 같은 flag를 쓰는 연속 Bcc(`a6a40 BEQ`+`a6a44 BLE`)는 앞 block에 묶는다. Unicorn TB 분할(`a5fe4` `a5fea` `a5ff8` `a5ffe` `a6002`)은 시작이 아니다.
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다. 범위 안 자료는 없다(범위 앞 자료 `a5cea..a5cf6`, `be0bc..be0c4`는 routing 밖).
- U01~N12 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`OR`/`NEG`/`EXT`/`LSL`/`ASR`/`ADD`/`SUB`는 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`ST`)과 Z만 바꾸는 `BTST`/`BSET`만인 block, callee C를 소비하는 Bcc block은 FLOW_ONLY다. 블록 경계를 건너는 N/Z 재계산은 선행이 유일할 때만 허용한다(N14에는 필요한 곳이 없다). checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N14 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 읽기 2곳(`200134` `2001dc`)은 live bus다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n14`(HEAD `6e3dc85` = N12까지 통합, `engine/src/animation_machine.cpp` SHA256 `f07b95b21d5b0d56aff79c146e4c348e53df2374e52c766d76b97f23c84ef850`, routing 규칙 69개, `engine/src/animation_machine_interpreter.cpp` SHA256 `3b91b9fae2a93a820c6de9b276bbb9b2cbe9b6bb859d607e7f977cc02095e540`)을 참조했다. N14 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N13(`59ea2..59f1a` `5a7c8..5ab6c` `5b220..5b4c6` `d3580..d3614` `d3ab8..d3b70` `dbfac..dbfb8`)과 범위·경계가 겹치지 않고 서로 부르지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n14/n14.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N14 = 196 block**, 코드 7 범위 2,094바이트, 448명령이다. routing 짝수 PC 1,047개 중 내부 PC 851개다. 범위 안의 모든 명령이 진입에서 정적으로 도달된다(미도달 명령 0). 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·SUBX/ADDX/MULx/DIVx·I/O port 쓰기·bank 변경·스택 직접 조작은 없다. 묶인 Bcc는 `a6a44 BLE`(앞 `a6a40 BEQ`와 같은 `CMP.W`) 하나다.
  - 재범위 N14 행의 191과 차이(+5): stage event 표의 형제 진입 `a5e62` `a5e6c` `a5e76`(+3, 결정 1)과 함수 경계 규칙 차이(재범위는 실행 TB 함수 본문만 셌다; 이 계약은 범위 안 정적 도달 전부를 센다).
- [F] 진입:
  - stage event callback(고정 ROM LONG 표, 같은 연속 표): `a5e80`(`e8e74`, 재범위 미연결 callback), `a5e76`(`e8e70`), `a5e62`(`e8e7c`), `a5e6c`(`e8e80`); `be0c4`(`e8fa0`).
  - 범위 안 설치 callback(결정 2): `a5e20`(`a5e1a`, fall-through), `a60c8`(`a60c2`), `a6a0c`(`a6a06`), `a6e7e`(`a6e78`), `be110`(`be10a`).
  - `28ae` 자식 callback: `a6dd4`(`a5f8c MOVEA.L #a6dd4,A0`+`a5f96 JSR 28ae`).
  - helper(JSR 대상): `4970a`(fixed ROM의 `JSR 4970a.L` 327곳 — 이 단위 5곳, 이미 routing된 N04 `ab052`·N07 `9c046` `9c074`·U18 `b7e28` 포함), `4972c`(`4970a JSR (PC)` + 범위 밖 9곳), `4b702`(`a6e54` + 범위 밖 23곳, 이미 routing된 U15 `af3ea` `af3f8` 포함).
  - 공용 꼬리·분기 대상: `a5cf6`(`a5e5e` `a616e` `a6ac2 BRA.W`, 범위 밖 8곳), `a5d18`(`a60dc` `a6a20 BNE.W`, 범위 밖 8곳), `a6914`(`a5fd8 BRA.W`), `a7256`(`a6e84 BCC.W`, 범위 밖 설치 값 `a6fa8` `a710a`).
- [F] **경계 callee(실행부 없음) 없음.** 나가는 호출은 모두 routing됨(아래 "의존·경계"). 단 `JSR 49f96`(`a6096` `a69ac`)은 interpreter 실행부에 그 진입 case가 없어 `unsupported animation interpreter PC`다(결정 7).
- [F] **범위 밖 설치 값(고아 설치, 노드 LONG에 저장만)**: `a6172` `a62cc` `a658e`(`a6148` `a6158` `a6168`), `a6ac6`(`a6ab2`), `a7036`(`a6ebc`). `28ae` 자식 대상 `d1d38`(N05) `7086a`(U14) `7487a`(미연결)는 자식 노드 LONG에 저장되는 자료다.
- [F] **carry**(아래 "carry" 절):
  - 소비 block **15개**: `a5d0c` `be130`(U05 `1ab02` 반환), `a5d56` `a5d8a` `a5dd6` `a5e46` `a5f9c`(fade_card `28ae` 반환), `a5da0` `a5dec` `a5fae`(`28ae` Clear 분기 또는 ORI Set), `a5ea4` `a5ee6`(U20 `497a6` 반환), `a60ce` `a6a12`(U01 `4b54e` 반환), `a6e84`(stage_event_ops `288c` 반환). 모두 FLOW_ONLY다.
  - known 생산 block **5개**(모두 Set, `ORI.B #1,CCR` 한 명령): `a5d64` `a5d9c` `a5de8` `a5e54` `a5faa`. `a5d9c` `a5de8` `a5faa`는 같은 함수 안 소비자 `a5da0` `a5dec` `a5fae`가 바로 읽는다(RTS 앞 생산이 아니다). `a5d64`는 다음 block `a5d68 CMPI`가, `a5e54`는 `JMP 2a00` 뒤 fade_card가 C를 덮어쓴다(결정 2).
  - FLOW_ONLY 74개(소비자 15 포함), Unknown 117개. 74 + 5 + 117 = 196.
- [F] 스택: JSR 복귀 LONG만 쓴다(`JSR (PC)` 2곳 `4970a` `49726` 포함).
- [F] 자료(모두 live bus): banked LONG `200134`(10곳: 노드 `22(A6)` 또는 자식 `a4(A6)` 노드 `22`), `2001dc`(`be0d6`). 그 LONG이 가리키는 기록의 LONG `a4` `4` `54` `2c` `7c` `20` `70` `48` `98` `6c`(애니메이션 목록 포인터, A1). work RAM: 노드 WORD `1e` `20` `42` `46` `54` `68` `76` `78` `7c` `7e` `80` `82` `84` `8e` `90` `94` `98`, LONG `(A6)` `c` `22` `36` `3a` `64` `9c` `a0` `a4`, BYTE `14` `15` `19` `5e` `60` `61` `9a` `9b` `a8`; `a4(A6)` 자식 노드 WORD `20`, LONG `22`; `28ae` 반환 A0 노드 WORD `76` `78` `7a` `7c` `7e`; `4970a` 인자 A0 노드 WORD `1e` `68`, BYTE `15`; 부모 `c(A6)` 노드 WORD `78` `7a`, BYTE `9b`; `491c4` 반환 A0의 BYTE `a8`; `26(A6)` 기준 WORD `6`(= 노드 `2c`).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng` `dyn_base`, TB 시작 기준; scratch `n14reach.py`): RNG 400 frame과 base 120 frame 모두 seed 30 31이 frame 0 `be0c4`부터 N14에 들어온다(TB 시작 80개). seed 6 7 12 13 76 77 98 99 104 105(RNG; base는 6 7)는 `4970a`/`4972c` helper만 지난다(9개). 196 시작 중 77개가 TB 시작으로 나타난다. 실행되지 않는 시작은 `a5d18` 파괴 경로, `a5e62`~`a5e80`의 대부분, `a6914`/`a6a0c` 경로 등이다(목록은 scratch).
- [F] 기준 측정(이 작업 트리 base `6e3dc85`의 `git archive` 사본, scratch 출력 `ms5-scratch/n14/fp/base_*`): 아래 "작업자 검증 기록".

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **stage event 형제 진입 `a5e62` `a5e6c` `a5e76` 포함(+3 block).** [F] 세 진입은 `a5e80`과 같은 연속 stage event LONG 표(`e8e70` `e8e74` `e8e7c` `e8e80`)가 가리키고 `MOVE.B #1/#2,9a(A6); BRA.W a5e86`으로 `a5e80` 본문에 합류한다. "범위 안 참조된 진입은 넣는다"(N12 결정 1 `53ad0` 선례)에 따라 넣는다. 400 frame 안에 실행되지 않는다. 빼면 193 block이고 세 PC는 내부 PC(`unsupported animation objects n14 PC`)가 된다.
2. **`ORI.B #1,CCR` 5 block을 모두 known Set 생산으로 둔다.** [F] `JSR 4970a` 뒤의 `ORI.B #1,CCR`은 원본에서 항상 C = 1을 만든다. `a5d9c` `a5de8` `a5faa`는 바로 뒤 소비자(`a5da0` `a5dec` `a5fae`)가 읽으므로 Set이어야 한다. `a5d64`(뒤 `a5d68 CMPI.B`가 덮음)와 `a5e54`(뒤 `a5e58 JMP 2a00`, fade_card `2a00`이 덮음)는 소비자가 없지만 같은 명령이라 같은 분류(Set, 정확한 원본 값)로 둔다(N07 `9c04c`/`9c07a` 선례; U18 `b7e2e`는 Unknown으로 둔 선례가 있다). Unknown으로 바꾸면 두 block만 carry 보존 목록과 무관하게 Unknown이 되고 결과 상태는 C 외에 같다.
3. **`4970a`/`4972c`/`4b702`의 반환 C는 Unknown.** [F] `4970a`는 `49214`(N05)로 끝나고 `4b702`는 `ORI.B #80,60(A6)`(C = 0)로 끝난다. 고정 ROM의 `JSR 4970a.L` 327곳·`JSR 4b702.L` 24곳·`JSR 4972c.L` 9곳 복귀점 첫 명령(scratch `retscan.py`; `LEA`/`MOVEA`/`BTST`/`BSET`/`ST`는 건너뜀)은 모두 C를 덮어쓰거나(`ORI.B #1,CCR` 287곳, `MOVE`/`TST`/`ADDQ`/`SUBQ`/`CLR` 등) 다른 JSR/RTS/BRA로 넘긴다. Bcc/Scc/ADDX 같은 직접 C 소비자는 없다. 따라서 known 생산으로 두지 않는다(실제 ROM 소비자가 없어 native 분기 확인이 불가능하다). `RTS`/`JSR` 뒤로 넘기는 13곳(예: `31a7a` `60bb6` `87904`)은 미연결 코드라 그 단위에서 다시 본다.
4. **block 수 196(재범위 191과 +5).** 결정 1의 +3과 함수 경계 규칙 차이. 범위 밖 설치 값(`a6172` `a62cc` `a658e` `a6ac6` `a7036`)과 그 사슬(`a6172..a6914`, `a6ac6..a6dd4`, `a6eea..a7256`, `a725c..`)은 고아 설치(재범위 결정 3)로 남긴다.
5. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n14.cpp`의 `animation_objects_n14_block`. 오류는 `unsupported animation objects n14 PC`(내부 PC), `objects n14 caller requires known carry`(소비 15 block). 메인 지시와 같다.
6. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`에서 N14 범위 PC를 쓰는 곳은 경계 stop 검사뿐이다: N04 test(`ab04e` → `4970a`), N07 test(`9c03a-c2` `9c06c-c2` `9c03e` `9c070` → `4970a`), U18 test(`b7e20-c2-*` `b7e24` → `4970a`), U15 test(`af3ea` `af3f8` → `4b702`). 모두 stop만 확인하고(`f.stop==want && final pc==want`) rollback을 기대하지 않으므로 그대로 유효하다. N09 test의 `0x1b069a5e808bb21e`는 digest 값의 일부다.
7. **interpreter 두 번째 진입 `49f96`(공유 실행부 1 case 추가 필요).** [F] `a6096`/`a69ac`는 자식 노드의 애니메이션을 `JSR 49f96.L`(A0 = 자식 + `26`, A1 = 목록, D0.W = `100`)로 초기화한다. `49f96`은 `49f8c`(`LEA 26(A6),A0; MOVE.B #0,18(A6)`) 바로 뒤의 두 번째 진입으로, 원본은 `MOVE.W #0,-7ff0(A5)`; bank port 정리; `CMPA.L #108000,A5; BEQ`(아니면 TRAP); `MOVE.L A1,(A0); MOVE.W #0,4(A0); MOVE.W D0,6(A0); RTS`다. routing은 범위(`49f8c..4a46c`)로 interpreter 실행부에 보내지만 `animation_machine_interpreter.cpp`에는 `49f96` case가 없어 `unsupported animation interpreter PC`(checked 오류, rollback)다. 이 단위는 지시대로 interpreter 파일을 고치지 않았다. [F] seed 30 31(RNG·base)은 frame 1 `a5e80`→`a6096`에서 `49f96`을 실행하므로(재범위 scratch 재생 TB), 이 case 없이는 30 31이 완주하지 못한다(아래 "작업자 검증 기록"). 권고: interpreter에 `case 0x49f96`(위 원본 순서; 끝 C Clear, `49f8c`와 같은 `MOVE.W D0,6(A0)`)을 더한다. scratch 패치 `ms5-scratch/n14/interp_49f96.patch`와 그 패치를 얹은 scratch 트리의 검증 결과를 함께 기록했다. [U] seed 38 39 116 117도 다른 미연결 코드에서 `49f96`을 부른다.

## 원본 바이트 근거

[F] 코드 7 범위 합계 2,094바이트. 범위 순서로 이어 붙인 SHA256 `40e51b3645fa72f3e8a957f4238ef393719d3ffe1840407f24565a39dab142e4`.

| CPU 범위 | 바이트 | SHA256 | 시작 | 내용 |
| --- | --- | --- | --- | --- |
| `4970a..4976e` | 100 | `ce0b43a1e8275b48d08ed4129fb3267f610ed43d963ecb9637262de8fff8c51b` | 14 | helper `4970a` `4972c` |
| `4b702..4b70a` | 8 | `bd0643cedfeb5ca10e0271566c7c44879407378b465d215655c574c06c611a93` | 1 | helper `4b702` |
| `a5cf6..a6172` | 1,148 | `0c09bb6a05584b594c34ae1b47aec17d7776f2057514415d8cae8ea966631809` | 109 | 꼬리 `a5cf6`, 파괴 `a5d18`, 진입 `a5e62`~`a5e80`, 설치 `a5e20` `a60c8` |
| `a6914..a6ac6` | 434 | `3ba16f81139271cf38a7968cd6d7549f32019790cf7016da3bb254055c4bc1d2` | 38 | `78 = 4` 초기화 `a6914`, 설치 `a6a0c` |
| `a6dd4..a6eea` | 278 | `ef0607357bcbc1e9512b3f6ce11e275dc61e8b6719746230fdc8de31743bcdac` | 24 | 자식 `a6dd4`, 설치 `a6e7e` |
| `a7256..a725c` | 6 | `2738adf81304c5fbbc9eedf6248d6b2d7cfa132bc35dfb5e458d0bbd9e12d3f9` | 1 | `JMP 2a00` |
| `be0c4..be13c` | 120 | `338c1d32e3b531924ae65ec02a66f204b44e621bb1d0a44f4d300e1f5b9e434e` | 9 | callback `be0c4`, 설치 `be110` |

- [F] 범위 밖 이웃(모두 미연결, `unsupported animation machine PC`): `49708`(앞 함수 끝), `4976e..`(다음 함수), `4b6f4..4b702`(다른 helper), `4b70a..`, `a5cea..a5cf6`(사각형 자료 `ffe0 fff0 0040 0040` + `0302 0304`, `a5d02 LEA a5cea(PC)`가 `1ab02`에 넘김), `a6172..a6914`(고아 설치 사슬), `a6ac6..a6dd4`(고아 설치 `a6ac6` 사슬), `a6eea..a7256`(고아 설치 `a7036` 등), `a725c..`, `be0bc..be0c4`(사각형 자료 `ffe0 ffd0 0040 0060`, `be126`이 `1ab02`에 넘김), `be13c..`.
- [F] 범위 밖 → N14 참조(scratch `n14xref.py`, 고정 ROM 전수): `4970a`(`JSR.L` 327곳), `4972c`(`JSR.L` 9곳), `4b702`(`JSR.L` 23곳), `a5cf6`(`BRA.W` 8곳), `a5d18`(`BNE.W` 8곳), `a5fdc`(`a690a`·`a6578` `MOVE.L #a5fdc,(A6)`; 범위 안 `a5fd4 BNE.W`의 대상), `a7256`(`MOVE.L #a7256,(A6)` 2곳), stage event 표 `e8e70`~`e8e80` `e8fa0`. 모두 block 시작으로 간다. 내부 PC와 같은 값은 자료 LONG·명령 operand의 우연 일치다(`a5f41` `a5f66` `a6000` `a6090` `a60bc` `a60c6` `a60de` `a60f0` `a60f2` `a6a00` `a6a18` `a6a7e` `a6e00` `be0ec`; 예: `a5f90`은 `MOVEA.L #a6dd4`의 operand, `be154`는 `JSR c6a96`의 operand).

## block 목록과 실행 의미

[F] 196 block. 각 줄은 block 안 명령 전체다(capstone 표기, 즉치·주소 16진). "(→x)"는 fall-through다. 태그: "C 소비"(Unknown이면 checked 오류), "Set 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호확장한다(`-6(a0)` = A0 − 6). `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVE.W #0,D0`·`CLR.W D0`은 하위 WORD만). `MOVEQ`는 LONG 전체를 쓴다. `EXT.L`은 하위 WORD 부호확장, `LSL.L #8`은 32-bit 왼쪽 shift, `NEG.L`/`NEG.W`/`ADD.L`/`SUB.L`/`SUBI.W`/`ADDI.W`/`SUBQ.W`는 원래 폭의 2의 보수, `ASR.L #2`/`#3`은 부호 bit 채움 산술 shift다. 비교 분기: `BLE`/`BGE`(부호 있는 비교; `CMP.L x,D0`은 D0 − x), `BPL`/`BMI`(결과 최상위 bit), `BEQ`/`BNE`(결과 0 여부; `SUBQ.W #1,8e(A6); BNE`는 감소 결과), `BCC`(C = 0), `BCS`(C = 1). `MOVE.W d0,d0`(`a6e24`)은 값을 바꾸지 않는다. `CMP.W 84(A6),D0`(`a6ab8`)의 결과 flag는 쓰이지 않지만 WORD 읽기는 한다.

**자식 배치 helper `4970a`(`4972c` 호출, N05 `49214`로 꼬리) 7**
- `4970a`: `JSR 4972c(pc)` — FLOW
- `4970e`: `BTST.B #0, 15(a0); BEQ.W 4971a` (→`49718`) — FLOW
- `49718`: `NEG.W d0` (→`4971a`)
- `4971a`: `BTST.B #1, 15(a0); BEQ.W 49726` (→`49724`) — FLOW
- `49724`: `NEG.W d1` (→`49726`)
- `49726`: `JSR 49214(pc)` — FLOW
- `4972a`: `RTS` — FLOW

**자식 표시 복사 helper `4972c` 7**
- `4972c`: `MOVE.W 1e(a6), d2; MOVE.W d2, 1e(a0); MOVE.W 68(a6), d2; MOVE.W d2, 68(a0); BTST.B #0, 15(a6); BEQ.W 4974c` (→`49746`)
- `49746`: `BSET.B #0, 15(a0)` (→`4974c`) — FLOW
- `4974c`: `BTST.B #1, 15(a6); BEQ.W 4975c` (→`49756`) — FLOW
- `49756`: `BSET.B #1, 15(a0)` (→`4975c`) — FLOW
- `4975c`: `BTST.B #2, 15(a6); BEQ.W 4976c` (→`49766`) — FLOW
- `49766`: `BSET.B #2, 15(a0)` (→`4976c`) — FLOW
- `4976c`: `RTS` — FLOW

**helper `4b702` 1**
- `4b702`: `ORI.B #80, 60(a6); RTS`

**공용 꼬리 `a5cf6`(`1ab02` 화면 밖 판정) 6**
- `a5cf6`: `TST.W 90(a6); BEQ.W a5d02` (→`a5cfe`)
- `a5cfe`: `SUBQ.W #1, 90(a6)` (→`a5d02`)
- `a5d02`: `LEA.L a5cea(pc), a0; JSR 1ab02.l` — FLOW
- `a5d0c`: `BCC.W a5d16` (→`a5d10`) — C 소비
- `a5d10`: `JMP 2a00.l` — FLOW
- `a5d16`: `RTS` — FLOW

**파괴 경로 `a5d18`(설치 `a5e20`) 30**
- `a5d18`: `BSET.B #3, 15(a6); LEA.L 26(a6), a0; MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L a4(a1), a1; JSR 49f8c.l`
- `a5d46`: `MOVEA.L #d1d38, a0; MOVE.W #1e, d0; JSR 28ae.l`
- `a5d56`: `BCC.W a5d68` (→`a5d5a`) — C 소비
- `a5d5a`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `a5d64`: `ORI.B #1, ccr` (→`a5d68`) — Set 생산
- `a5d68`: `CMPI.B #1, 9a(a6); BNE.W a5e0e` (→`a5d72`)
- `a5d72`: `TST.W 7e(a6); BNE.W a5dc6` (→`a5d7a`)
- `a5d7a`: `MOVEA.L #7086a, a0; MOVE.W #14, d0; JSR 28ae.l`
- `a5d8a`: `BCC.W a5da0` (→`a5d8e`) — C 소비
- `a5d8e`: `MOVE.W #0, d0; MOVE.W #20, d1; JSR 4970a.l`
- `a5d9c`: `ORI.B #1, ccr` (→`a5da0`) — Set 생산
- `a5da0`: `BCC.W a5dc2` (→`a5da4`) — C 소비
- `a5da4`: `MOVE.W #0, 76(a0); MOVE.W #78, 78(a0); MOVE.W #b4, 7a(a0); MOVE.W #0, 7c(a0); MOVE.W #0, 7e(a0)` (→`a5dc2`)
- `a5dc2`: `BRA.W a5e0e` — FLOW
- `a5dc6`: `MOVEA.L #7487a, a0; MOVE.W #14, d0; JSR 28ae.l`
- `a5dd6`: `BCC.W a5dec` (→`a5dda`) — C 소비
- `a5dda`: `MOVE.W #0, d0; MOVE.W #20, d1; JSR 4970a.l`
- `a5de8`: `ORI.B #1, ccr` (→`a5dec`) — Set 생산
- `a5dec`: `BCC.W a5e0e` (→`a5df0`) — C 소비
- `a5df0`: `MOVE.W #0, 76(a0); MOVE.W #0, 78(a0); MOVE.W #0, 7a(a0); MOVE.W #0, 7c(a0); MOVE.W #1, 7e(a0)` (→`a5e0e`)
- `a5e0e`: `MOVE.B #0, 9a(a6); MOVE.B #2, 9b(a6); MOVE.L #a5e20, (a6)` (→`a5e20`)
- `a5e20`: `JSR 4be2c.l` — FLOW
- `a5e26`: `JSR 49fc6.l` — FLOW
- `a5e2c`: `BTST.B #7, 15(a6); BEQ.W a5e5e` (→`a5e36`) — FLOW
- `a5e36`: `MOVEA.L #d1d38, a0; MOVE.W #1e, d0; JSR 28ae.l`
- `a5e46`: `BCC.W a5e58` (→`a5e4a`) — C 소비
- `a5e4a`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `a5e54`: `ORI.B #1, ccr` (→`a5e58`) — Set 생산
- `a5e58`: `JMP 2a00.l` — FLOW
- `a5e5e`: `BRA.W a5cf6` — FLOW

**stage event callback `a5e62` `a5e6c` `a5e76` `a5e80`과 초기화 본문(설치 `a60c8`) 50**
- `a5e62`: `MOVE.B #1, 9a(a6); BRA.W a5e86`
- `a5e6c`: `MOVE.B #2, 9a(a6); BRA.W a5e86`
- `a5e76`: `MOVE.B #1, 9a(a6); BRA.W a5e86`
- `a5e80`: `MOVE.B #2, 9a(a6)` (→`a5e86`)
- `a5e86`: `CMPI.B #1, 9a(a6); BNE.W a5ed2` (→`a5e90`)
- `a5e90`: `MOVE.W #c7f, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `a5e9e`: `JSR 497a6.l` — FLOW
- `a5ea4`: `BCC.W a5eba` (→`a5ea8`) — C 소비
- `a5ea8`: `MOVE.W #c4d, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `a5eb6`: `BRA.W a5ec8` — FLOW
- `a5eba`: `MOVE.W #c49, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `a5ec8`: `MOVE.B 19(a6), 14(a6); BRA.W a5f10`
- `a5ed2`: `MOVE.W #c7f, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `a5ee0`: `JSR 497a6.l` — FLOW
- `a5ee6`: `BCC.W a5efc` (→`a5eea`) — C 소비
- `a5eea`: `MOVE.W #c54, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `a5ef8`: `BRA.W a5f0a` — FLOW
- `a5efc`: `MOVE.W #c4e, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `a5f0a`: `MOVE.B 19(a6), 14(a6)` (→`a5f10`)
- `a5f10`: `MOVE.W #c83, d0; JSR 4a496.l`
- `a5f1a`: `BSET.B #6, 15(a6); MOVE.W #8800, 68(a6); MOVE.W #8800, 1e(a6); MOVE.W #32, 54(a6); MOVE.W 7c(a6), 8e(a6); CMPI.W #3, 78(a6); BNE.W a5f4c` (→`a5f42`)
- `a5f42`: `MOVE.W #5a, 90(a6); BRA.W a5f52`
- `a5f4c`: `MOVE.W #32, 90(a6)` (→`a5f52`)
- `a5f52`: `MOVE.L #0, 36(a6); MOVE.L #0, 3a(a6); MOVE.W 80(a6), d0; BNE.W a5f76` (→`a5f6a`)
- `a5f6a`: `MOVE.L #30000, 9c(a6); BRA.W a5f7e`
- `a5f76`: `EXT.L d0; LSL.L #8, d0; MOVE.L d0, 9c(a6)` (→`a5f7e`)
- `a5f7e`: `TST.W 76(a6); BNE.W a5f8c` (→`a5f86`)
- `a5f86`: `BSET.B #0, 15(a6)` (→`a5f8c`) — FLOW
- `a5f8c`: `MOVEA.L #a6dd4, a0; MOVE.W #a, d0; JSR 28ae.l`
- `a5f9c`: `BCC.W a5fae` (→`a5fa0`) — C 소비
- `a5fa0`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `a5faa`: `ORI.B #1, ccr` (→`a5fae`) — Set 생산
- `a5fae`: `BCS.W a5fb8` (→`a5fb2`) — C 소비
- `a5fb2`: `JMP 2a00.l` — FLOW
- `a5fb8`: `MOVE.L a0, a4(a6); MOVE.B #1, 9b(a6); TST.W 76(a6); BEQ.W a5fce` (→`a5fca`)
- `a5fca`: `NEG.L 9c(a6)` (→`a5fce`)
- `a5fce`: `CMPI.W #4, 78(a6); BNE.W a5fdc` (→`a5fd8`)
- `a5fd8`: `BRA.W a6914` — FLOW
- `a5fdc`: `MOVE.L #4000, 36(a6); BTST.B #0, 15(a6); BNE.W a5ff2` (→`a5fee`)
- `a5fee`: `NEG.L 36(a6)` (→`a5ff2`)
- `a5ff2`: `MOVE.W #0, 98(a6); MOVE.W #6, 94(a6); MOVE.B 9a(a6), d0; BNE.W a6032` (→`a6006`)
- `a6006`: `LEA.L 26(a6), a0; MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 4(a1), a1; JSR 49f8c.l`
- `a602e`: `BRA.W a608e` — FLOW
- `a6032`: `CMPI.B #1, d0; BNE.W a6066` (→`a603a`)
- `a603a`: `LEA.L 26(a6), a0; MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 54(a1), a1; JSR 49f8c.l`
- `a6062`: `BRA.W a608e` — FLOW
- `a6066`: `LEA.L 26(a6), a0; MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 2c(a1), a1; JSR 49f8c.l`
- `a608e`: `TST.B 9b(a6); BEQ.W a60c2` (→`a6096`)
- `a6096`: `MOVEA.L a4(a6), a4; LEA.L 26(a4), a0; MOVE.W #cb, -6(a0); MOVE.L 200134.l, -4(a0); MOVE.W #100, d0; LEA.L 26(a4), a0; MOVEA.L 22(a6), a1; MOVEA.L 7c(a1), a1; JSR 49f96.l`
- `a60c2`: `MOVE.L #a60c8, (a6)` (→`a60c8`)

**설치 callback `a60c8`(수평 이동 상태) 23**
- `a60c8`: `JSR 4b54e.l` — FLOW
- `a60ce`: `BCC.W a60d6` (→`a60d2`) — C 소비
- `a60d2`: `CLR.B 5e(a6)` (→`a60d6`)
- `a60d6`: `BTST.B #7, 61(a6); BNE.W a5d18` (→`a60e0`) — FLOW
- `a60e0`: `MOVE.L 36(a6), d0; BTST.B #0, 15(a6); BNE.W a6100` (→`a60ee`)
- `a60ee`: `CMP.L 9c(a6), d0; BLE.W a60fc` (→`a60f6`)
- `a60f6`: `ASR.L #3, d0; ADD.L d0, 36(a6)` (→`a60fc`)
- `a60fc`: `BRA.W a610e` — FLOW
- `a6100`: `CMP.L 9c(a6), d0; BGE.W a610e` (→`a6108`)
- `a6108`: `ASR.L #3, d0; ADD.L d0, 36(a6)` (→`a610e`)
- `a610e`: `JSR 43ea4.l` — FLOW
- `a6114`: `JSR 49fc6.l` — FLOW
- `a611a`: `TST.W 8e(a6); BEQ.W a6136` (→`a6122`)
- `a6122`: `SUBQ.W #1, 8e(a6); BNE.W a6136` (→`a612a`)
- `a612a`: `MOVE.B #0, 9b(a6); MOVE.W #0, 90(a6)` (→`a6136`)
- `a6136`: `TST.W 90(a6); BNE.W a616e` (→`a613e`)
- `a613e`: `CMPI.W #0, 78(a6); BNE.W a614e` (→`a6148`)
- `a6148`: `MOVE.L #a6172, (a6)` (→`a614e`)
- `a614e`: `CMPI.W #1, 78(a6); BNE.W a615e` (→`a6158`)
- `a6158`: `MOVE.L #a62cc, (a6)` (→`a615e`)
- `a615e`: `CMPI.W #3, 78(a6); BNE.W a616e` (→`a6168`)
- `a6168`: `MOVE.L #a658e, (a6)` (→`a616e`)
- `a616e`: `BRA.W a5cf6` — FLOW

**`78 = 4` 초기화 `a6914`(설치 `a6a0c`) 13**
- `a6914`: `MOVE.B 9a(a6), d0; BNE.W a6948` (→`a691c`)
- `a691c`: `LEA.L 26(a6), a0; MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 20(a1), a1; JSR 49f8c.l`
- `a6944`: `BRA.W a69a4` — FLOW
- `a6948`: `CMPI.B #1, d0; BNE.W a697c` (→`a6950`)
- `a6950`: `LEA.L 26(a6), a0; MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 70(a1), a1; JSR 49f8c.l`
- `a6978`: `BRA.W a69a4` — FLOW
- `a697c`: `LEA.L 26(a6), a0; MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 48(a1), a1; JSR 49f8c.l`
- `a69a4`: `TST.B 9b(a6); BEQ.W a69d8` (→`a69ac`)
- `a69ac`: `MOVEA.L a4(a6), a4; LEA.L 26(a4), a0; MOVE.W #cb, -6(a0); MOVE.L 200134.l, -4(a0); MOVE.W #100, d0; LEA.L 26(a4), a0; MOVEA.L 22(a6), a1; MOVEA.L 98(a1), a1; JSR 49f96.l`
- `a69d8`: `CLR.L 36(a6); MOVE.L #fffff000, 3a(a6); MOVE.L 9c(a6), a0(a6); MOVE.L #1000, 36(a6); TST.L 9c(a6); BPL.W a6a02` (→`a69fa`)
- `a69fa`: `NEG.L 36(a6); BRA.W a6a06`
- `a6a02`: `NEG.L a0(a6)` (→`a6a06`)
- `a6a06`: `MOVE.L #a6a0c, (a6)` (→`a6a0c`)

**설치 callback `a6a0c`(수직 이동 상태) 25**
- `a6a0c`: `JSR 4b54e.l` — FLOW
- `a6a12`: `BCC.W a6a1a` (→`a6a16`) — C 소비
- `a6a16`: `CLR.B 5e(a6)` (→`a6a1a`)
- `a6a1a`: `BTST.B #7, 61(a6); BNE.W a5d18` (→`a6a24`) — FLOW
- `a6a24`: `MOVE.L 3a(a6), d0; CMP.L a0(a6), d0; BLE.W a6a36` (→`a6a30`)
- `a6a30`: `ASR.L #3, d0; ADD.L d0, 3a(a6)` (→`a6a36`)
- `a6a36`: `CLR.B d2; MOVE.W 42(a6), d0; CMP.W 84(a6), d0; BEQ.W a6a60; BLE.W a6a56` (→`a6a48`)
- `a6a48`: `TST.L 9c(a6); BPL.W a6a52` (→`a6a50`)
- `a6a50`: `ST.B d2` (→`a6a52`) — FLOW
- `a6a52`: `BRA.W a6a60` — FLOW
- `a6a56`: `TST.L 9c(a6); BMI.W a6a60` (→`a6a5e`)
- `a6a5e`: `ST.B d2` (→`a6a60`) — FLOW
- `a6a60`: `TST.B d2; BNE.W a6a74` (→`a6a66`)
- `a6a66`: `MOVE.L 36(a6), d0; ASR.L #2, d0; SUB.L d0, 36(a6); BRA.W a6a9c`
- `a6a74`: `MOVE.L 36(a6), d0; MOVE.L 9c(a6), d1; BPL.W a6a90` (→`a6a80`)
- `a6a80`: `CMP.L d1, d0; BLE.W a6a8c` (→`a6a86`)
- `a6a86`: `ASR.L #3, d0; ADD.L d0, 36(a6)` (→`a6a8c`)
- `a6a8c`: `BRA.W a6a9c` — FLOW
- `a6a90`: `CMP.L d1, d0; BGE.W a6a9c` (→`a6a96`)
- `a6a96`: `ASR.L #3, d0; ADD.L d0, 36(a6)` (→`a6a9c`)
- `a6a9c`: `JSR 43ea4.l` — FLOW
- `a6aa2`: `MOVE.W 46(a6), d0; SUBI.W #100, d0; CMP.W 82(a6), d0; BGE.W a6ab8` (→`a6ab2`)
- `a6ab2`: `MOVE.L #a6ac6, (a6)` (→`a6ab8`)
- `a6ab8`: `CMP.W 84(a6), d0; JSR 49fc6.l`
- `a6ac2`: `BRA.W a5cf6` — FLOW

**`28ae` 자식 callback `a6dd4`(설치 `a6e7e`) 10**
- `a6dd4`: `BSET.B #6, 15(a6); MOVE.W #e001, 68(a6); MOVE.W #e001, 1e(a6); MOVEQ #0, d0; MOVEQ #0, d1; JSR 49290.l`
- `a6df0`: `MOVE.W #4c, d0; MOVE.W #1f, d1; MOVE.B #0, d2; JSR c6a96.l`
- `a6e02`: `BSET.B #3, 15(a6); LEA.L cad88.l, a0; JSR 490ba.l` — FLOW
- `a6e14`: `MOVE.W d0, 54(a6); LEA.L cadea.l, a0; JSR 490ba.l`
- `a6e24`: `MOVE.W d0, d0; EXT.L d0; LSL.L #8, d0; BTST.B #0, 15(a6); BNE.W a6e36` (→`a6e34`)
- `a6e34`: `NEG.L d0` (→`a6e36`)
- `a6e36`: `MOVEA.L c(a6), a0; CMPI.W #4, 78(a0); BNE.W a6e46` (→`a6e44`)
- `a6e44`: `NEG.L d0` (→`a6e46`)
- `a6e46`: `MOVE.L d0, 64(a6); MOVEQ #0, d0; MOVE.L d0, 36(a6); MOVE.L d0, 3a(a6); JSR 4b702.l`
- `a6e5a`: `MOVEA.L c(a6), a0; MOVE.W 7a(a0), d0; ADDI.W #100, d0; MOVE.W d0, 82(a6); MOVE.W #cb, 20(a6); MOVE.L 200134.l, 22(a6); MOVE.L #a6e7e, (a6)` (→`a6e7e`)

**설치 callback `a6e7e` 14**
- `a6e7e`: `JSR 288c.l` — FLOW
- `a6e84`: `BCC.W a7256` (→`a6e88`) — C 소비
- `a6e88`: `JSR 491c4.l` — FLOW
- `a6e8e`: `MOVE.B a8(a0), a8(a6); JSR 43e34.l`
- `a6e9a`: `JSR 492c8.l` — FLOW
- `a6ea0`: `JSR 49fc6.l` — FLOW
- `a6ea6`: `MOVEA.L c(a6), a0; TST.B 9b(a0); BNE.W a6ed8` (→`a6eb2`)
- `a6eb2`: `MOVE.W #182a, d0; JSR 3af8.l`
- `a6ebc`: `MOVE.L #a7036, (a6); MOVE.W #0, d0; MOVE.W #ffe0, d1; JSR 49290.l`
- `a6ed0`: `JSR 49274.l` — FLOW
- `a6ed6`: `RTS` — FLOW
- `a6ed8`: `CMPI.B #2, 9b(a0); BNE.W a6ee8` (→`a6ee2`)
- `a6ee2`: `JMP 2a00.l` — FLOW
- `a6ee8`: `RTS` — FLOW

**삭제 꼬리 `a7256` 1**
- `a7256`: `JMP 2a00.l` — FLOW

**callback `be0c4`(설치 `be110`) 9**
- `be0c4`: `MOVE.W #76, d0; MOVE.W #1b, d1; MOVE.B #0, d2; JSR c6a96.l`
- `be0d6`: `MOVE.W #8838, 68(a6); MOVE.W #8838, 1e(a6); LEA.L 26(a6), a0; MOVE.W #21b, 20(a6); MOVE.L 2001dc.l, 22(a6); MOVE.W #100, d0; LEA.L 26(a6), a0; MOVEA.L 22(a6), a1; MOVEA.L 6c(a1), a1; JSR 49f8c.l`
- `be10a`: `MOVE.L #be110, (a6)` (→`be110`)
- `be110`: `JSR 43e34.l` — FLOW
- `be116`: `LEA.L 26(a6), a0; MOVE.W #80, 6(a0); JSR 49fc6.l`
- `be126`: `LEA.L be0bc(pc), a0; JSR 1ab02.l` — FLOW
- `be130`: `BCC.W be13a` (→`be134`) — C 소비
- `be134`: `JMP 2a00.l` — FLOW
- `be13a`: `RTS` — FLOW

## carry

- [F] **소비 15 block.** Unknown C로 들어오면 `objects n14 caller requires known carry`(상태 보존)다. 모두 `BCC.W`/`BCS.W` 한 명령이다.
  - `a5d0c BCC.W a5d16`, `be130 BCC.W be13a`: U05 `1ab02`(사각형 화면 판정)의 C. Clear → RTS, Set → `JMP 2a00`.
  - `a5d56 BCC.W a5d68`, `a5d8a BCC.W a5da0`, `a5dd6 BCC.W a5dec`, `a5e46 BCC.W a5e58`, `a5f9c BCC.W a5fae`: fade_card `28ae`의 C. Clear → 분기 대상, Set → `JSR 4970a` 뒤 `ORI.B #1,CCR`.
  - `a5da0 BCC.W a5dc2`, `a5dec BCC.W a5e0e`: 선행 2개(`28ae` Clear로 온 `a5d8a`/`a5dd6`의 분기, Set 생산 `a5d9c`/`a5de8`). Clear → 분기 대상, Set → 자식 WORD 기록(`a5da4`/`a5df0`).
  - `a5fae BCS.W a5fb8`: 선행 `a5f9c`(Clear 분기)와 `a5faa`(Set). Set → `a5fb8`, Clear → `a5fb2 JMP 2a00`.
  - `a5ea4 BCC.W a5eba`, `a5ee6 BCC.W a5efc`: U20 `497a6`(`497a6` Clear·`497b0` Set)의 C.
  - `a60ce BCC.W a60d6`, `a6a12 BCC.W a6a1a`: U01 `4b54e`의 C. Clear → 분기, Set → `CLR.B 5e(A6)`.
  - `a6e84 BCC.W a7256`: stage_event_ops `288c`(부모 `c(A6)`가 0이면 Set, 부모 callback LONG이 `270e`이면 Clear, 아니면 Set)의 C. Clear → `a7256 JMP 2a00`, Set → `a6e88`.
- [F] **known 생산 5 block**(Set): `a5d64` `a5d9c` `a5de8` `a5e54` `a5faa`(`ORI.B #1,CCR`). 결정 2.
- [F] **FLOW_ONLY 74 block**(C 보존): JSR/JMP/BRA/RTS block, `LEA`+`JSR`(`a5d02` `a6e02` `be126`), BTST/BSET(Z만)+Bcc·ST block, 소비 15개. 목록: `4970a 4970e 4971a 49726 4972a 49746 4974c 49756 4975c 49766 4976c a5d02 a5d0c a5d10 a5d16 a5d56 a5d8a a5da0 a5dc2 a5dd6 a5dec a5e20 a5e26 a5e2c a5e46 a5e58 a5e5e a5e9e a5ea4 a5eb6 a5ee0 a5ee6 a5ef8 a5f86 a5f9c a5fae a5fb2 a5fd8 a602e a6062 a60c8 a60ce a60d6 a60fc a610e a6114 a616e a6944 a6978 a6a0c a6a12 a6a1a a6a50 a6a52 a6a5e a6a8c a6a9c a6ac2 a6e02 a6e7e a6e84 a6e88 a6e9a a6ea0 a6ed0 a6ed6 a6ee2 a6ee8 a7256 be110 be126 be130 be134 be13a`.
- [F] **Unknown 117 block**: 그 밖 `MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`ADD`/`ADDI`/`SUBI`/`SUBQ`/`NEG`/`EXT`/`LSL`/`ASR`/`ORI` 포함 block, `MOVE.L #imm,(A6)` 설치 block, `MOVEA.L #imm,A0`+`MOVE.W`+`JSR 28ae` 자식 block, 애니메이션 block(`MOVE.L 200134.l,22(A6)` 등), `4b702 ORI.B #80,60(A6); RTS`(결정 3), `49718`/`49724 NEG.W`.
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 Bcc로 시작하는 곳은 위 C 소비 15곳뿐이다).

## 구현 범위와 규약

- routing 7 범위(위 표). 짝수 PC 1,047개 중 block 시작 196, 내부 851. 내부 PC 직접 진입은 `unsupported animation objects n14 PC`다. 범위 이웃은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수·부호 채움으로 명시 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 FLOW_ONLY 74개를 넣는다. Set 생산 5개는 실행 뒤 known Set을 둔다.
- 제어 이동은 모두 정적이다. 설치 값(`MOVE.L #imm,(A6)`)은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `28ae` 자식 대상(A0)도 자료다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다.
- 스택: JSR 복귀 LONG만. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] banked window(live bus; 현재 PVC bank):
  - LONG `200134` → 노드 `22(A6)`(`a5d18` `a6006` `a603a` `a6066` `a691c` `a6950` `a697c` `a6e5a`) 또는 `a4(A6)` 자식 노드의 `22`(`a6096` `a69ac`, `-4(A0)`, A0 = 자식 + `26`). 이어서 `22(A6)` 기록의 LONG(오프셋 `a4` `4` `54` `2c` `20` `70` `48`, 자식용 `7c` `98`)을 A1(애니메이션 목록)로 읽는다.
  - LONG `2001dc` → `22(A6)`(`be0d6`), 그 기록의 LONG `6c` → A1.
- [F] 주소만 넘기는 고정 ROM 자료: 사각형 `a5cea`(`a5d02`) `be0bc`(`be126`)(A0, `1ab02`), `490ba` 표 `cad88` `cadea`(A0), `28ae` 자식 대상 `d1d38` `7086a` `7487a` `a6dd4`(A0, D0.W = `1e` `14` `14` `a`).
- [F] 상수 쓰기: `20(A6)` = `cb`(`a5d18` 등) / `21b`(`be0d6`), `68`/`1e` = `8800`(`a5f1a`) `e001`(`a6dd4`) `8838`(`be0d6`), `54` = `32`, `90` = `5a`/`32`, `9b` = `2`/`1`/`0`, `9a` = `0`/`1`/`2`, `98` = 0, `94` = 6, `36` = `4000`(±) / `1000`(±), `3a` = 0 / `fffff000`, `9c` = `30000` 또는 `ext(80.W) << 8`(`76 ≠ 0`이면 부호 반전), `82` = 부모 `7a` + `100`, `64` = `ext(490ba 결과.W) << 8`(`15` bit 0과 부모 `78 = 4`에 따라 부호 반전), `28ae` 반환 노드 `76 78 7a 7c 7e` = `0 78 b4 0 0`(`a5da4`) / `0 0 0 0 1`(`a5df0`), `26(A6)+6` = `80`(`be116`). 소리 `8ebe` D0 = `c7f` `c4d` `c49` `c54` `c4e`(D1.B = 0), `3af8` D0 = `182a`, `4a496` D0 = `c83`, `c6a96` D0/D1/D2.B = `4c`/`1f`/0(`a6df0`), `76`/`1b`/0(`be0c4`), `49290` D0/D1 = 0/0(`a6dd4`), 0/`ffe0`(`a6ebc`), `4970a` D0/D1 = 0/0 또는 0/`20`.
- [F] `4970a`: `4972c`가 노드 A6의 WORD `1e` `68`을 자식 A0에 복사하고 A6 `15` bit 0~2가 서 있으면 A0 `15`의 같은 bit를 세운다(지우지 않음). 이어서 A0 `15` bit 0/1이 서 있으면 `D0.W`/`D1.W`를 `NEG.W`하고 `49214`(N05)로 JSR 후 RTS. [I] `49214`는 자식 위치를 부모 위치 + (D0, D1)로 둔다(N05 계약 범위).
- [I] 게임 의미: `a5e80` 계열은 좌우(`78` = 0/1/3) 또는 상하(`78` = 4, `a6914`)로 움직이는 객체다. `9a`(1/2)는 소리·외형 변형, `a4(A6)`은 `28ae` 자식 `a6dd4`(같은 외형을 따라가는 부품; 부모 `9b`가 0이 아니면 `a6ed8`에서 `9b = 2`일 때 삭제)다. `61` bit 7은 파괴 표시(`a5d18`: 폭발 자식 `d1d38`, 잔해 `7086a`/`7487a`, `a5e20` 상태에서 `15` bit 7이면 삭제)로 보인다. `be0c4`는 화면 밖(`1ab02`)이 되면 삭제되는 정지 장식 객체로 보인다. 확인하지 않았다.

## 의존·경계

- [F] N14 → 기존(모두 routing됨): U05 `1ab02`(C 반환) `c6a96`, stage_event_ops `288c`(C 반환), fade_card `28ae`(C 반환) `2a00`(JMP), sound `3af8`, cleanup `43e34`, U04 `43ea4`, U12 `490ba` `492c8`, U17 `491c4`, N05 `49214`, U08 `49274` `49290`, U20 `497a6`(C 반환), interpreter `49f8c` `49fc6`(그리고 `49f96`: routing 범위 안이지만 진입 case 없음, 결정 7), U14 `4a496`, U01 `4b54e`(C 반환), U18 `4be2c`, U02 `8ebe`.
- [F] 실행부 없는 경계 없음(`49f96`은 결정 7). 단위 test의 stop은 다른 단위 진입(`28ae` `49214` `49f96` 등 callee 진입)에서 멈춘다. rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N14: stage event 표(`e8e70`~`e8e80`, `e8fa0`), `JSR 4970a`(N04 `ab052`, N07 `9c046` `9c074`, U18 `b7e28` 및 미연결 다수), `JSR 4b702`(U15 `af3ea` `af3f8` 및 미연결 다수). 이 단위 뒤 그 호출은 N14 실행부로 이어진다. 범위 밖 미연결 설치 사슬(`a6172..a6914` 등)이 `a5cf6` `a5d18` `a5fdc` `a7256`로 들어온다(그 사슬은 고아 설치로 남는다).
- [F] N13과 경계·범위가 겹치지 않는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 196 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, Set 생산 5개, 그 밖 Unknown), zero-step, 내부 851 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 소비 15곳의 Unknown carry 오류. bank LONG은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`28ae`, `1ab02`, `497a6`, `4b54e`, `288c`)를 따라 들어간 fixture로 native 분기를 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(callback, 설치 상태, 실제 bank LONG·기록, 소비자 native 분기).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, complete +2(30 31) 기대(재범위 행).

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n14.cpp`(SHA256 `f792313dd7dd2d7cbcdd7b58e3d77762c3cefe991d44d50c99635bf01adfd69b`), 새 `engine/tests/animation_machine_objects_n14_test.cpp`(SHA256 `a321d08bdd734c471e989ce899535baf683aa4337fc6fcffdb9b2bf6a44e55f5`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 7 범위, carry 보존 case group 1개 74 PC; SHA256 `9ca7b6df778821b1a456282043194fadb3cde511f3286a75e757e0ae14e59aa7`), `engine/src/animation_machine_internal.h`(선언 1줄), `Makefile`(source list·test target·run line), `tools/verify_animation_machine.py`(SOURCES). `animation_machine_interpreter.cpp`는 고치지 않았다(결정 7).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0. 새 test: `animation machine objects n14: 612 fixtures (24 checked errors, 104 kept C), 196 blocks, 2668 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0. 기존 N04·N07·U15·U18 test(경계 `4970a`/`4b702` stop 검사)는 그대로 통과했다.
- [F] typed fixture(scratch `gen/gen.py`, Unicorn + 합성 물리 바이트 `a5cea` `be0bc`(사각형) `200134` `2001dc`(bank LONG → work RAM 기록)): 196 시작 모두 fixture 진입 또는 경로로 덮임. 실제 생산자 추종 fixture: `28ae`(`a5d46` `a5d7a` `a5dc6` `a5f8c`, 성공/실패; `4970a`→`49214`→`43e38`까지 따라가 ORI Set 뒤 소비자 `a5da0` `a5dec` `a5fae`의 native 분기), `1ab02`(`a5cf6` `be126`, 안/밖·반전), `497a6`(`a5e9e` `a5ee0`), `4b54e`(`a60c8` `a6a0c`, `5e`·`61` 조합), `288c`(`a6e7e`, 부모 0 / `270e` / 그 밖). block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류, Unknown C는 소비 15곳에서 정확한 오류, zero-step 196×3, 내부 851 PC 정확한 오류, 홀수 PC, RAM rollback 탐침 `10fe10` `10fe20` `10fe30`·RTS 복귀 `10fe40`, 범위 앞 자료 `a5cea` `a5cee` `be0bc` `be0c0`은 routing 밖. 돌연변이 5개(부호 비교 2, ORI Set, `ASR`, `15` bit 번호)가 모두 test를 실패시켰다(scratch `mut/`).
- [F] 실제 ROM 차분(`realrom/real14.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건): 불일치 0/0/0, 시작 도달 196/196(세 seed 모두). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `a5d0c` 751, `a5d56` 250, `a5d8a` 64, `a5da0` 70, `a5dd6` 80, `a5dec` 88, `a5e46` 11, `a5ea4` 95, `a5ee6` 140, `a5f9c` 236, `a5fae` 245, `a60ce` 299, `a6a12` 256, `a6e84` 256, `be130` 108. 결정 7 차이(native는 `49f96`을 지나고 C++는 `unsupported animation interpreter PC`): 23/22/16건(모두 `any` 진입 `a602e` `a6062` `a608e` `a6096` `a6944` `a6978` `a69a4` `a69ac`). 같은 입력을 `interp_49f96.patch`를 얹은 scratch 트리로 돌리면 불일치 0, 결정 7 차이 0이다(`runp_*.log`).
- [F] 기준(`6e3dc85` `git archive` 사본 `ms5-scratch/n14/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 13,448·node 110,480, 불일치 0, 자연 완주 123(seed 30 31은 frame 0 `be0c4` 첫 미연결). N14 뒤(이 작업 트리): 일치 pass 13,450·node 110,502, 불일치 0, 회귀 0, 자연 완주 123. 바뀐 seed는 30 31뿐이다(frame 0 `be0c4` → frame 1 `a5e80` 노드의 `JSR 49f96`에서 `unsupported animation interpreter PC`, 상태 보존). 결과 SHA256 `0120630091a05faf44f06c9ffb97e339c02d20556e35a97d3f79fd39c385f690`.
- [F] RNG 초기화 400 frame 차분: 기준 complete 114, 일치 pass 45,600·node 338,201, 불일치 0(verification.json SHA256 `9b5b0af0b5ab6bc437ba678634e8540a65e98850d2b8388ec913834396085e8a`). N14 뒤(이 작업 트리): complete 114, 일치 pass 45,602·node 338,223, 불일치 0, 회귀 0, `other` 2(seed 30 31, 위와 같은 `49f96` 오류; 도구 종료 코드 1), 그 밖 분류 변화 0(SHA256 `fa36b2ae896e26bf7dc778c471c7e44bef5606c213dd173f9e131732f3b40216`).
- [F] 결정 7 패치(`interp_49f96.patch`, SHA256 `496cdb808e88713230e0f7f583f4c899f312b27fa6b72d951603327c0a5fc4c0`)를 얹은 scratch 트리(`ms5-scratch/n14/patchtree`, 그 밖 파일은 이 작업 트리와 같음): base 일치 pass 13,688·node 113,100, 불일치 0, 회귀 0, 자연 완주 **125**(+30 31, 120 frame 완주; SHA256 `0d9c5a8f3d4707f4d1f3f5c52af8c7e3279a39a6dd8ffd48ac5db77652c487fc`). RNG complete **116**(+30 31, 각 400 frame), 일치 pass 46,400·node 344,181, 불일치 0, `other` 0, 도구 종료 코드 0(SHA256 `a1f886affae28d9fadab5a43ce3dc11f40ce7ceb07271aa9dd7f91cf9b3a32b8`). 재범위 N14 행의 기대(118/127은 N13 포함 누적)와 같은 +2다.
- [F] ROM SHA256·mtime 작업 전후 같음(`29112a94…`, `1791291625`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] 범위 밖 설치 사슬 `a6172` `a62cc` `a658e` `a6ac6` `a7036`과 자식 `7487a`의 동작은 해당 단위(고아 설치 정리)에서 정한다.
3. [U] `a5e62` `a5e6c` `a5e76`을 쓰는 stage event는 400 frame 자연 기록에 없다.
4. [U] `4970a`를 `RTS`/`JSR`로 넘기는 미연결 호출자 13곳의 상위 소비자(결정 3)는 그 단위에서 확인한다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n14/`(`n14.py` block·범위 계산, `n14stat.py` 범위 SHA·짝수 PC, `n14cls.py` carry 분류, `n14fmt.py` block 목록, `n14xref.py` 범위 밖 참조, `refs14.py`, `retscan.py` 복귀점 C 소비 검사, `n14reach.py` 자연 도달, `gen/` typed fixture 생성·test 조립, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스·RNG 차분; 저장소 밖).

- (메인) 결정 7 채택: 인터프리터에 `49f8c`의 두 번째 진입점 `case 0x49f96`을 메인이 병합 커밋에서 추가했다(원본 `49f96 MOVE.W #0,-7ff0(A5)`부터 같은 본문, `LEA 26(A6),A0`와 `MOVE.B #0,18(A6)` 생략, 끝에서 C Clear).
