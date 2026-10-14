# F5 frame head H8: 정방향 sprite writer family(표 `ce62..ce82`, routine 8개 `ce82..f226`) 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`)의 §1 sprite writer 행과 §4 H8~H11 행이다: 정방향 writer 표 `ce62..ce82`(BRA.W, k=0..7, `ce62+4k`), routine `ce82..f224`(H8 `ce82..d250` `d250..d620`, H9 `d620..ddc6`, H10/H11 + Duff 진입 `e1ba` `e6ce` `ebea` `f10a`, 각 32개). 메인 결정(범위 문서 머리)이 구속한다. 특히 "반복 family(…sprite writer 16종, Duff 진입)는 PC를 매개변수로 받는 executor 하나로 구현해도 된다. 단위 상한은 고유 코드 기준으로 세되, 시험은 모든 진입 PC를 덮어야 한다." H1 계약(`animation-machine-frame-head-h1-contract.md`) 결정 5(writer 표 JSR은 live 대상, 표·표 밖 착지 routing은 H4/H8 계약이 정함)의 정방향 쪽을 이 문서가 닫는다. 역방향 쪽은 H4 계약(`animation-machine-frame-head-h4-contract.md`)이 닫았고, 이 문서의 형식·결정 번호는 H4 계약을 따른다.

작업 지시(요약): 먼저 8개 정방향 routine이 하나의 template인지, 그리고 H4 역방향 template와 어떤 관계인지 원본 바이트로 증명한다. Duff·cell 표 계산 JMP마다 `D7.B` 범위를 H4처럼 증명한다. 하나의 template이면 family 전체(H8~H11)를 executor 하나(`animation_machine_frame_head_h8.cpp`)로 구현하고, 아니면 표 + 첫 routine만 구현한다. 정방향 경로는 자연 실행되지 않으므로(BYTE `108d3c` bit7) fixture 전용이다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. 범위는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기준 작업 트리 `metalslug-h8`(branch `codex/f5-h8-wip`, base `b7b72d3` = F4 N35까지 + F5 H1·H3·H4 + external-read queue). 범위 `ce62..f226`의 짝수 PC는 기존 routing에 없다. 이웃 `ce60`(F4 U04 `ce02..ce62`의 `RTS`)은 routing 안이고, `f226`(다른 writer 표 `f226..`, 범위 밖)은 routing 밖이다. [F]=원본 바이트·기록 산출물·작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. scratch(저장소 밖) `ms5-scratch/h8/`: `h8tmpl.py`(정렬 diff), `h8fwdrev.py`(정방향 = 역방향 + 방향 편집 6개 증명), `h8dec.py`(정적 leader, `starts.txt` SHA256 `cd79780894b251887620a7e12cd473cb0346e0aec5f472d448e55f7ba6e1f000`), `h8ana.py`(D7.B 범위·carry), `h8roles.py`(역할 표·구조 검사), `h8xref.py`(외부 참조).

## 요약

- [F] **8개 정방향 routine은 H4와 같은 3개 flag(H, V, S) template이다.** k = 표 slot 번호(0..7)일 때 H = k bit 0, V = k bit 1, S = k bit 2이다. 정방향 routine 사이의 정렬 diff는 H4 역방향 사이의 diff와 같은 삽입점·같은 편집 수다(0→1 3, 0→2 1, 0→3 4, 4→5 4, 4→6 2, 4→7 6, 0→4 7, 1→5·2→6·3→7 6/7/6). cell(18바이트)·Duff 항목(8바이트)·BRA.W 표 항목은 8개 routine에서 바이트 단위로 같고 H4의 것과도 같다.
- [F] **정방향 routine k = 역방향 routine k + 고정 방향 편집 6개**(flag와 무관, 8개 모두 같은 자리; `h8fwdrev.py`). 아래 "방향 편집" 표. 분기 목표 불일치는 편집된 명령(`test`, `finish`)을 가리키는 분기뿐이고 역할이 1:1로 대응한다.
- [F] **정적 block 시작 736개** = 표 slot 8 + routine 0..7 각 75·74·75·74·108·107·108·107(H4와 같은 수). BRA.W 표 항목 256, cell 256, Duff 진입 128. 범위 안 명령 3,954개 중 3,946개에 도달한다. **도달하지 않는 명령 8개**는 각 routine `step` 바로 앞의 `ADDQ.W #1,D6`(`cf06` `d2d6` `d6a4` `da78` `de5a` `e36e` `e87e` `ed9e`)이다(결정 6).
- [F] **진입:** 외부 code 참조는 H1 `16c42`(`LEA ce62.l,A3`) → `16c48 JSR (A3,D7.W)`(복귀 `16c4c`) 하나다(`h8xref.py`; 그 밖의 일치는 명령 operand 절반 또는 자료 LONG `0000d800` 등이다 [I]). 복귀점 `16c4c BRA 16c04` → `16c04 CMPA`가 C를 다시 만든다.
- [F] **계산 점프 12개는 모두 정적으로 제한된다.** routine마다 cell 표 `JMP d(PC,D0.W)` 하나, S routine마다 Duff `JMP d(PC,D3.W)` 하나. routine 진입부터의 모든 CFG 경로에서 JMP 시점 `D7.B` ∈ {0, 2, …, 62}(`h8ana.py`). 범위 문서 §7 항목 4를 정방향 8곳에서 확인했다.
- [F] **carry:** 소비 block 0, known 생산 0, FLOW_ONLY 264(표 slot 8 + BRA.W 표 항목 256), Unknown 472. X 소비 명령은 없다. `BPL`은 N만 읽는다.
- [F] **I/O:** H4와 같다(VRAM `MOVE.L Dn,(A6)`, PVC `2ffff2`/`2ffff0` WORD 쓰기, bank window `200004` LONG 읽기). device 읽기·대기·TRAP·BIOS·callee는 없다.
- [F] **자연 실행 0.** H1 `16be4 TST.B d3c(A5); BPL.W 16c6a`가 BYTE `108d3c` bit7 = 0이면 역방향 경로(`16c6a`)로 간다. 이 bit를 바꾸는 code는 IRQ 쪽 `16cfa`의 `BCHG`뿐이라(범위 문서 §1) 선언 모델의 자연 H에서는 정방향 writer가 실행되지 않는다. 시험·차분은 선언 fixture와 "자연 상태 + bit7 선언 설정"으로만 한다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **family 전체를 이 단위에서 구현(H8~H11 통합), H4와 별도 실행부.** [F] template 증명이 성립하므로 표 `ce62..ce82`, routine 8개(`ce82..f226`)·Duff 128개를 executor 하나(`animation_frame_head_h8_block`)로 구현한다. routing은 범위 하나 `ce62..f226`이다. 범위 문서 §4의 H9~H11 행은 이 단위에 흡수된다. 정방향 끝은 `f224`가 아니라 `f226`이다(routine 7의 `RTS`가 `f224`).
   - 제안: H4 실행부(`animation_machine_frame_head_h4.cpp`)는 고치지 않고 같은 구조의 별도 파일을 둔다. 방향 편집 6개는 flag가 아니라 family 전체에 고정이고, H4를 방향 매개변수로 바꾸면 기존 실행부·시험·검증 기록을 다시 열어야 한다. 대가는 약 200줄의 구조 중복이다. 두 파일의 차이는 방향 편집 6개 자리로 한정한다(검증 기록에서 diff로 확인).
2. **writer 표 JSR(`16c48`)의 표 밖 착지(H1 결정 5).** [F] `16c30..16c40`: `D7.W` = (((WORD `4(A2)` ≠ `ffff`) ? 4 : 0) | `D1.B`) × 4이고 `D1.B`는 `BCLR #2` 뒤 임의 BYTE이므로 목표는 `ce62 + 4m`, m = 0..255(`ce62..d25e`)다. m ≤ 7은 표 slot이다. m = 8..255 중 55개는 routine 0의 block 시작에 닿고(`ce82` m 8, `ceda` 30, `cefa` 38, `cf1a` 46, `cf22` 48, `cf2e` 51, cell 표 항목 32개 m 68..99, cell 시작 `cff2 + 36i` 등, `d24a` 250), 나머지는 routine 0 내부 또는 routine 1 머리 내부(`d252..d25e`; `d250`은 4 정렬이 아니라 닿지 않는다)다. 제안: H4 결정 2와 같이 **live 대상**으로 둔다. 착지 PC가 이 단위의 block 시작이면 그 block을 실행하고, 내부 PC면 `unsupported animation frame head h8 PC`(checked, 전체 rollback)이다(F1 결정 3).
3. **계산 점프는 live 대상으로 표현하되 정적 범위를 증명한다(H4 결정 3과 같음).** 자연 경로에서는 목표가 표 항목 32개·Duff 진입 32개 중 하나다. block 단위 직접 진입에서는 C++가 `PC := 표 기준 + sext(D0.W)`(Duff `+ sext(D3.W)`)로 두고 다음 step의 routing에 맡긴다(범위 밖 목표는 그 PC의 routing; `f226` 이후·`ce60` 이전은 다른 단위 또는 `unsupported animation machine PC`).
4. **VRAM 쓰기 표현(H4 결정 4와 같음).** (A6 & `ffffff`) = `3c0000`이면 `VideoPortWrite`{`3c0000`, 4, 값} 1건, 아니면 `am_write(A6, 4, 값)`. H1 `16bee`가 A6 = `3c0000`을 세운다.
5. **bank 선택 6·7(H4 결정 5와 같음).** n = 6은 다음 `200004` 읽기에서 `reached program bank physical span outside ROM`(checked), n = 7은 기준 `100000`으로 정상 실행.
6. **도달하지 않는 `ADDQ.W #1,D6` 8개.** [F] 각 routine에서 `height`의 `BRA.W test` 바로 뒤, `step` 바로 앞 2바이트(`step − 2`)에 있다. 이 PC로 가는 분기·fall-through·계산 목표·외부 참조가 없다(`h8dec.py` 도달 분석, `h8xref.py`). 그래서 block 시작이 아니고 내부 PC로 둔다: 직접 진입은 `unsupported animation frame head h8 PC`다. [I] 역방향 `column` 머리의 `SUBQ.W #1,D6`을 정방향에서 열 꼬리의 `ADDQ`로 옮길 때 남은 흔적으로 보인다(실행 의미에는 영향 없음).
7. **무효화 탐침.** [F] 처음 정적 검색은 놓쳤으나 전체 `make test`에서 확인했다: 엔진 시험 6개가 `deac`(H8 내부)·`ce62`/`ce64`(H8 표)를 "routing 밖" 탐침으로 썼다. 제안(적용함): 기대 문자열은 두고 탐침 값만 work RAM `10fe44`/`10fe50`/`10fe52`로 바꾼다. Python 검증기 11개의 `deac` 탐침은 고치지 않고 무효화 목록으로 둔다(검증 기록). H1 시험의 정방향 표 대상 행(`16bc8-n1` stop `ce72`, `16c30-0-ffff` stop `ce62` 등)은 stop PC로만 쓰므로 그대로 통과했다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_frame_head_h8.cpp`의 `animation_frame_head_h8_block`. 오류: `unsupported animation frame head h8 PC`(범위 안 내부 PC·표 영역 비정렬 PC·결정 6). carry 소비자가 없으므로 carry 오류 문자열은 없다. 그 밖의 오류는 기존 공용 helper 문자열이다.

## 원본 바이트 근거

[F] family `ce62..f226` 9,156바이트, SHA256 `de8f2f7bd1495cffd888334d89e0ded228fd0f3e852755e41fc9daf793e75b48`.

| 범위 | k | flag | 바이트 | SHA256(앞 16) | block |
| --- | --- | --- | --- | --- | --- |
| `ce62..ce82`(표) | - | - | 32 | `86a9a970650c52f2` | 8 |
| `ce82..d250` | 0 | - | 974 | `8af354579c5b947c` | 75 |
| `d250..d620` | 1 | H | 976 | `f635e5d334f898f1` | 74 |
| `d620..d9f2` | 2 | V | 978 | `995bcb2a8b7acafb` | 75 |
| `d9f2..ddc6` | 3 | H V | 980 | `e60a712fcbbf77dd` | 74 |
| `ddc6..e2d6` | 4 | S | 1,296 | `4538fb4379c1deb5` | 108 |
| `e2d6..e7ea` | 5 | H S | 1,300 | `1a3bd033cfb9d543` | 107 |
| `e7ea..ed06` | 6 | V S | 1,308 | `579a7717a77409e5` | 108 |
| `ed06..f226` | 7 | H V S | 1,312 | `427c4e5dbc0b2564` | 107 |

- [F] 표 slot `ce62+4k` = `BRA.W` routine k(`6000xxxx`, 바이트 `6000001e 600003e8 600007b4 60000b82 60000f52 6000145e 6000196e 60001e86`).
- [F] 각 routine은 같은 k의 역방향 routine보다 2바이트 길다(삽입 `ADDQ.W` 2개 − 삭제 `SUBQ.W` 1개). cell 18바이트 `3a1b da43 b305 3805 2c84 d882 301b 2c80 d082`, Duff 항목 8바이트 `2c84 d882 2c80 d082`, cell 표 항목 `6000xxxx`는 H4와 같다(`h8roles.py`가 8개 routine 모두에서 바이트 비교).

## template 증명

[F] 방법은 H4와 같다(`h8tmpl.py`): routine을 명령 열로 디코드하고 분기 operand 목표를 지운 텍스트로 `SequenceMatcher` 정렬을 한 뒤, 같다고 정렬된 명령의 분기 목표가 정렬 대응으로 옮겨지는지 확인했다.

### 정방향 routine 사이(flag H/V/S)

[F] 차이는 H4 template 증명 표와 같은 삽입·교체뿐이다(주소는 정방향).

| flag | 자리 | 원본 차이(정방향 예) |
| --- | --- | --- |
| H | outer, `MOVE.W (A3)+,D7` 뒤 | `NEG.W D5` 삽입(`d2b4`) |
| H | 열 전진 | 비 H: `test` 앞 별도 `advance` block(`cf18 ADD.W D4,D5`, S `de6c..de76`). H: 같은 계산을 `SUB`로 `clip` 머리에(`d2f0 SUB.W D4,D5`, S `e390..e39a`) |
| H·S | outer, `MOVE.B D5,D4` 뒤 | `SUB.B D3,D4` 삽입(`e34e`) |
| V | column, `LSL.W #6,D0` 뒤 | `ADD.B D7,D0; NEG.L D2` 삽입(`d6f2`) |
| V·S | Duff 머리, `MOVE.B D7,D3` 뒤 | `SWAP D0; ADD.W D3,D0; ADDQ.W #4,D0; SWAP D0` 삽입(`ebd0`) |
| S | outer, test 뒤 scale, column 둘째 쓰기, 마지막 cell 뒤 Duff | H4 표의 S 행과 같다(`de2a..de3e`, `de80`, `deaa`, `e19c..e2b6`) |

- [F] 편집 수: 0→1 3, 0→2 1, 0→3 4, 4→5 4, 4→6 2, 4→7 6(H4와 같음). 분기 목표 불일치는 advance 재배치로 생기는 재진입 목표(비 H `advance` ↔ H `test`) 한 종류뿐이다.

### 정방향 k ↔ 역방향 k(방향 편집, `h8fwdrev.py`)

[F] 8개 k 모두 정확히 아래 6개 편집뿐이고(순서·내용 assert), 분기 목표 불일치(k마다 3~4개)는 모두 편집된 `test`/`finish`를 가리키는 분기이며 역할이 같다(역방향 `test` → 정방향 `test`, `finish` → `finish`).

| # | 역할 자리 | 역방향(H4) | 정방향(H8) |
| --- | --- | --- | --- |
| 1 | `head` 끝부분 | `MOVE.W 6(A4),D6` | `MOVE.W 4(A4),D6` |
| 2 | `step` 바로 앞(도달 불가, 결정 6) | – | `ADDQ.W #1,D6` |
| 3 | `test` | `CMP.W 4(A4),D6; BLE.W finish` | `CMP.W 6(A4),D6; BPL.W finish` |
| 4 | `column` 첫 명령 | `SUBQ.W #1,D6` | – |
| 5 | 열 꼬리(비 S 마지막 cell, S Duff 꼬리) `MOVEM.L (A7)+,D3-D5` 뒤 | – | `ADDQ.W #1,D6` |
| 6 | `finish` | `MOVE.W D6,6(A4)` | `MOVE.W D6,4(A4)` |

- [I] 의미: 역방향은 sprite 번호를 `6(A4)`(현재)에서 아래로 할당하며 하한 `4(A4)`에서 멈추고, 정방향은 `4(A4)`(현재)에서 위로 할당하며 상한 `6(A4)`에서 멈춘다. H1 `16bf8`/`16c00`이 정방향 진입 전에 `4(A4)` := `(A4)`를 세운다(역방향은 `16c76`/`16c80`이 `6(A4)` := `2(A4)`). 실행 의미는 아래 명령 의미만 따른다.
- [F] 역할 구조 검사(`h8roles.py`): 각 routine의 block 시작 = {역할 block 12~14개} ∪ {표 32} ∪ {cell 32} ∪ {Duff 32(S)}이고 남는 시작이 없다. 역할별 마지막 분기(대상·fall-through)는 H4와 같고 `test`만 `BPL.W finish`다. `head`의 `4(A4)` 읽기, `test`의 `CMP.W 6(A4)`, `column`에 `D6` 감소 없음, 열 꼬리의 `MOVEM` → `ADDQ.W #1,D6` → `SUBI.W #100,D7`, `finish` `MOVE.W D6,4(A4); RTS`를 routine마다 assert했다.

## block 목록(736)

역할 표(시작 PC). `advance`는 비 H만, `scale`·`duff`는 S만 있다(없으면 –).

| k | head | swap7 | outer | height | step | advance | test | scale | clip | column | table | cells | duff | next | finish | end |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `ce82` | `ceda` | `cedc` | `cefa` | `cf08` | `cf18` | `cf1a` | – | `cf22` | `cf2e` | `cf72` | `cff2` | – | `d240` | `d24a` | `d250` |
| 1 | `d250` | `d2a8` | `d2aa` | `d2ca` | `d2d8` | – | `d2e8` | – | `d2f0` | `d2fe` | `d342` | `d3c2` | – | `d610` | `d61a` | `d620` |
| 2 | `d620` | `d678` | `d67a` | `d698` | `d6a6` | `d6b6` | `d6b8` | – | `d6c0` | `d6cc` | `d714` | `d794` | – | `d9e2` | `d9ec` | `d9f2` |
| 3 | `d9f2` | `da4a` | `da4c` | `da6c` | `da7a` | – | `da8a` | – | `da92` | `daa0` | `dae8` | `db68` | – | `ddb6` | `ddc0` | `ddc6` |
| 4 | `ddc6` | `de1e` | `de20` | `de4e` | `de5c` | `de6c` | `de78` | `de80` | `de88` | `de94` | `dedc` | `df5c` | `e1be` | `e2c6` | `e2d0` | `e2d6` |
| 5 | `e2d6` | `e32e` | `e330` | `e362` | `e370` | – | `e380` | `e388` | `e390` | `e3a8` | `e3f0` | `e470` | `e6d2` | `e7da` | `e7e4` | `e7ea` |
| 6 | `e7ea` | `e842` | `e844` | `e872` | `e880` | `e890` | `e89c` | `e8a4` | `e8ac` | `e8b8` | `e904` | `e984` | `ebee` | `ecf6` | `ed00` | `ed06` |
| 7 | `ed06` | `ed5e` | `ed60` | `ed92` | `eda0` | – | `edb0` | `edb8` | `edc0` | `edd8` | `ee24` | `eea4` | `f10e` | `f216` | `f220` | `f226` |

- 표 slot: `ce62 + 4k`(k = 0..7) → routine k `head`. 8 block, FLOW.
- cell 표 항목: `table + 4i`(i = 0..31) = `BRA.W cells + 18 × (31 − i)`. FLOW.
- cell: `cells + 18j`(j = 0..31). j = 31은 cell + 꼬리(비 S: `MOVEM.L (A7)+,D3-D5; ADDQ.W #1,D6; SUBI.W #100,D7; BCC.W 재진입`(fall `next`); S: Duff 머리 + `JMP`).
- Duff 진입(S): `duff + 8j`(j = 0..31). j = 31은 꼬리(`SWAP D3; MOVEM.L (A7)+,D3-D5; ADDQ.W #1,D6; SUBI.W #100,D7; BCC.W 재진입`, fall `next`). 범위 문서의 Duff JMP 위치 `e1ba` `e6ce` `ebea` `f10a`는 각 routine `cells + 18×31` block의 마지막 명령이고 진입 기준은 그 다음 주소(`e1be` `e6d2` `ebee` `f10e`)다.
- 재진입 = 비 H: `advance`, H: `test`.
- 내부(도달 불가, 결정 6): `step − 2` 8개.

## 실행 의미(template, flag H/V/S)

표기는 H4 계약과 같다. H4 계약 "실행 의미"의 각 항목을 그대로 따르되 다음 4곳만 다르다(방향 편집 1·3·4·5·6; 편집 2는 도달 불가).

- `head`: … `D6.W` = WORD **`4(A4)`**; `D7.W` = WORD(A3), A3 += 2; `D7.W` −= `100`; 빌림이면 `finish`, 아니면 `swap7`. (그 앞은 H4와 같다: `D2` = 0, LONG `8(A2)`, `D7.W` = `D2.W` & 7, WORD push `D0.W`, `-7ff0(A5)`, PVC `2ffff2`/`2ffff0`, WORD pop, `LSR.L #1`, `& 3fc`, A3 = `200004`, 2단 포인터, `LSR.L #8`, `& 3ffc`.)
- `test`: `D6.W` − WORD **`6(A4)`**(WORD 차, mod 2^16)의 bit 15가 0이면(`BPL`, N clear; overflow는 보지 않는다) `finish`, 아니면 S `scale`, 비 S `clip`.
- `column`: **`D6` 감소 없이** `D0.W` = `D6.W` + `8401`; `SWAP D0`; `D0.W` = `D5.W`; `D0.W` += `D0.W`; `video(D0)`. 이후(`MOVEQ #-1,D0`/S 값, `8001`, `video`, `D2` = `00020000`, `D0.W` = ((`D6.W` + 1) << 6), [V], `D1`, `D0`, `MOVEM.L D3-D5,-(A7)`, `D3`, `D4`, `JMP`)는 H4와 같다.
- 열 꼬리(비 S 마지막 cell j = 31, S Duff j = 31): `D3`, `D4`, `D5` = LONG pop ×3(S는 그 앞에 `SWAP D3`) 뒤 **`D6.W` += 1**; `D7.W` −= `100`; 빌림이면 `next`, 아니면 재진입.
- `finish`: WORD **`4(A4)`** = `D6.W`; RTS(자연 복귀 `16c4c`).
- 그 밖(`swap7`, `outer`, `height`, `step`, `advance`, `scale`, `clip`, cell 표 항목, cell j < 31, S Duff 머리, Duff j < 31, `next`)은 H4 계약의 정의와 같다.

## Duff·cell 표 진입 범위 증명(범위 문서 §7 항목 4)

- [F] `h8ana.py`(H4 `h4ana.py`와 같은 모델; 정방향 추가 명령 `ADDQ.W #1,D6`은 `D7`을 쓰지 않는다): routine마다 진입 `head`에서 CFG(분기·fall-through·계산 목표 32개)를 따라 `D7.B` 값 집합을 고정점까지 전파했다. `D7`을 쓰는 명령은 H4와 같은 집합이고 모르는 writer는 없다.
- [F] 결과: 12개 JMP(`cf6e` `d33e` `d710` `dae4` `ded8` `e1ba` `e3ec` `e6ce` `e900` `ebea` `ee20` `f10a`) 모두에서 `D7.B` ∈ {0, 2, …, 62}(정확히 32값).
- [F] 색인 레지스터: cell JMP에서 `D0` writer는 `MOVEQ #0,D0` 뒤 `MOVE.W D6,D0; ADDQ.W #1; LSL.W #6;` [V `ADD.B D7,D0`] `SWAP D0; MOVE.B D7,D0; ADD.W D0,D0`뿐 → `D0.W` = 2 × `D7.B` → 목표 `table + 4i`. Duff JMP에서 `D3`은 `SWAP D3; CLR.W D3; MOVE.B D7,D3; ADD.W D3,D3; ADD.W D3,D3`뿐 → `D3.W` = 4 × `D7.B` → 목표 `duff + 8j`.

## carry

- [F] **소비 0, known 생산 0.** 모든 Bcc(`BCS`/`BCC`/`BPL`/`BMI`)는 같은 block의 `SUBI`/`CMP`/`CMPI`/`ADD`가 만든 flag를 읽는다(`h8ana.py`: 첫 flag 읽기 앞에 flag 생산이 없는 block 0). `finish`의 `MOVE.W; RTS`가 C를 지우지만 복귀점 `16c4c`(H1 FLOW) 다음 `16c04 CMPA`가 다시 만든다. 외부 호출자는 `16c48` 하나다.
- [F] **FLOW_ONLY 264 block**(C 보존): 표 slot 8(`ce62..ce7e`)과 routine마다 cell 표 항목 32. carry 보존 목록(`carry_preserving_pc`)에 주석 붙은 case group 하나로 넣는다.
- [F] **Unknown 472 block**: 나머지(`ADDQ.W #1,D6`도 C를 만든다).

## 경계·I/O·스택

- [F] **경계:** callee·TRAP·BIOS·대기가 없다. 나가는 길은 `finish`의 RTS(자연 `16c4c`, H1)와 결정 2·3의 live 목표뿐이다. 단위 시험은 다른 단위 PC를 "routing 밖" 탐침으로 쓰지 않고, rollback 탐침은 work RAM PC `10fe00..10fefe`를 쓴다. H1 블록(`16be4`/`16c04` 진입, `16c4c` 복귀)은 실행 경로·stop으로만 쓴다.
- [F] **읽기:** sprite 항목 LONG `8(A2)`·WORD `2(A2)`·BYTE `4(A2)` `5(A2)`, WORD `4(A4)` `6(A4)`, bank window LONG, 둘째 포인터 LONG, frame 자료 WORD(A3)+(live bus), stack.
- [F] **쓰기:** WORD `-7ff0(A5)`, PVC `2ffff2`·`2ffff0`, VRAM `video()`(결정 4), WORD `4(A4)`, stack(WORD push/pop `D0`, `MOVEM.L` 12바이트).

## 구현 범위와 규약

- routing: `ce62..f226` 하나(짝수 PC 4,578개, 시작 736, 내부 3,842 = 3,834 + 도달 불가 `ADDQ` 8). 내부 PC 직접 진입과 표 영역(`ce62..ce82`)의 4바이트 비정렬 PC는 `unsupported animation frame head h8 PC`다.
- executor: 정방향 routine 8개의 역할 PC 표(위 표를 C++ 상수 표로 옮겨 적음)와 flag로 매개변수화한 함수 하나. H4 실행부와 같은 구조이고 방향 편집 자리만 다르다(결정 1). 반복 block(cell, Duff 항목)은 block 실행 한 번이 cell 하나(또는 Duff 항목 하나)다.
- 공유 최소 수정: `animation_machine.cpp` routing `else if` 하나(마지막 `else return am_error` 앞)와 carry 보존 case group 하나(264 PC, `// BTST/BEQ changes only Z` 앞), `animation_machine_internal.h` 선언 하나(끝), `Makefile`(source 목록·test target·실행 줄), `tools/verify_animation_machine.py` SOURCES. 기존 실행부(H1·H4 포함)는 고치지 않는다. public header는 바꾸지 않는다.

## 시험 계획

- 단위 시험 `engine/tests/animation_machine_frame_head_h8_test.cpp`(`run_animation_machine`만): scratch Unicorn 생성 fixture(PvcMachine, 원본 code + H4와 같은 형식의 합성 물리 바이트; 2단 포인터·frame 자료·sprite 항목은 work RAM).
  - 시작 736개 전부: block 표(시작 × 들어오는 C clear/set/unknown: native 후속·digest·port 수·C 분류), zero-step(736 × C 3), 내부 PC 3,842 전수(정확한 오류, 도달 불가 `ADDQ` 8 포함), 범위 양끝 홀수, RAM rollback 탐침 `10fexx`.
  - 전체 routine fixture: k = 0..7 × 줄 수 1..32(cell 표 32항목·Duff 32항목 전부), 여러 열·part, x clip, `test` 조기 종료와 `BPL` 경계(차 = 0, 차의 bit 15 = 1인 큰 양수 차 `7fff`/`8000` 등 부호 비교와 다른 경우), S 배율, H/V, bank 1·5·7, bank window 자료, A6 = RAM.
  - H1 연결: `16be4`(bit7 = 1, `4(A4)` := `(A4)` 초기화 포함) 또는 `16c04`에서 시작 → `16c48 JSR (A3,D7.W)` → routine → RTS `16c4c` → ring 끝 → `16c4e` → `16ce6 RTS`(k 0..7).
  - successor/carry × 3, 결정 2 표 밖 착지(block 시작 = 실행, 내부 = h8 오류), 결정 3 비정상 `D7.B`, 결정 5 bank 6 오류·bank 7, checked 오류(홀수 포인터, ROM 바이트 없음, A6 device, 스택 device).
- 돌연변이 검사(routine별 매개변수: 역할 PC·flag·stride·방향 편집 6곳), UBSan, 실제 ROM 차분(Unicorn vs C++ + 8 `program_rom_*.ms5d`, 모든 시작): 자연 정방향 진입이 없으므로 **입력은 자연 F5 관측의 H 시작 상태(pass-end dump)에서 BYTE `108d3c` bit7을 선언으로 세운 뒤** native H를 실행해 H1 `16c48`이 정방향 표에 들어가는 순간의 상태로 만든다. 같은 상태로 H 시작부터 첫 routing 밖 경계까지 native vs C++(H1 + H8 연쇄)도 비교한다. native 관측기의 `path-sprite-forward` fixture(seed 0 frame 6~7, bit7 선언)도 대조한다. base frame pass·RNG 400 무변화(기준 `b7b72d3`: complete 134, 불일치 0).

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다. 작업 트리 `metalslug-h8`(base `b7b72d3`), scratch `ms5-scratch/h8/`.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_frame_head_h8.cpp` `013fde06f019a87e`, `engine/tests/animation_machine_frame_head_h8_test.cpp` `2e46b4aa5d82d2fa`(생성 표 `gen/tables_h8.inc` `2905b7865f9de1df`). 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나 `ce62..f226`, carry 보존 case group 하나 264 PC; `562af4d8043bb651`), `engine/src/animation_machine_internal.h`(선언 하나; `c4c6d312e0319e15`), `Makefile`(source 목록·test target·실행 줄; `7ca62c954c1516a9`), `tools/verify_animation_machine.py` SOURCES(`633e365defca2806`). H4 실행부·public header는 바꾸지 않았다.
- [F] 실행부는 H4 실행부와 같은 구조이고, 이름을 맞춘 diff(scratch `h8norm.cpp`)의 차이는 주석·역할 표·표 기준 외에 방향 편집 자리 5곳(`head` `4(A4)`, `test` `CMP.W 6(A4)`/`BPL`, `column` 감소 삭제, 열 꼬리 `ADDQ.W #1,D6`(helper `fh8_pop_d3_d5_next_number`), `finish` `4(A4)`)뿐이다. 편집 2(도달 불가 `ADDQ`)는 block 시작이 아니므로 코드가 없다(내부 오류).
- [F] **결정 7 정정(무효화 탐침 6곳, 엔진 시험은 값만 교체):** 전체 `make test`에서 다음 시험이 work RAM 밖 "routing 밖" 탐침 `deac`(이제 H8 routine 4 `column` 내부 → `unsupported animation frame head h8 PC`)와 `ce62`/`ce64`(H8 표)를 썼다. 기대 문자열은 그대로 두고 탐침 값만 work RAM `10fe44`/`10fe50`/`10fe52`로 바꿨다: `animation_machine_callers_test.cpp`(`450557e1c7f5637a`), `_activation_test.cpp`(`19159898eaa6e46e`), `_readiness_test.cpp`(`848cbaba3579d983`), `_screen_test.cpp`(`c37ee732dd03b893`), `_cleanup_test.cpp`(`e3ef5bcd303bbc7e`), `_objects_u04_test.cpp`(`outside[]`의 `ce62`,`ce64`; `e561614684b46dde`). **Python 검증기(수정하지 않음, 무효화 목록):** 반환 LONG/PC `deac`를 "unsupported animation machine PC" 기대로 쓰는 `tools/verify_animation_machine.py`(245·246행), `_activation.py`(139), `_cleanup.py`(292), `_hud.py`(259·268·275), `_exit.py`(285·288·292·296), `_readiness.py`(124), `_map_transfer.py`(304), `_palette_bind.py`(314), `_scene.py`(292·295·298), `_screen.py`(257), `_transition.py`(290·302). 다시 실행하면 이 행들은 h8 내부 오류를 낼 것으로 본다 [I, 실행하지 않음].
- [F] `make -j3 all test`(동시 3 process 상한, 탐침 교체 뒤): exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log` 경고 0 + `make_all2.log`), `tools/tests` unittest 257개 OK. H8 test 출력: `animation machine frame head h8: 582 fixtures (23 checked errors, 20 kept C), 736 blocks, 13566 calls`.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, 전체 source, scratch `build_test.sh ubsan`): H8 test 통과, runtime error 0.
- [F] 단위 시험(`run_animation_machine`만; scratch `gen/gen_h8.py` Unicorn PvcMachine 생성): fixture 582(성공 559, checked 오류 23). fixture가 시작 736개를 모두 지난다(k 0..7 × 줄 수 1..32, 여러 part·열, x clip, 조기 종료, `BPL` 경계 4종 `7fff/8001` `8000/7fff` `0010/9000` `0000/8000`(부호·무부호 비교와 결과가 다른 경우), 번호 WORD 순환 `fffe→0002`(상위 WORD 보존), 줄 수 byte `00 21 41 ff`, clip 경계, S 배율 6×3, bank 1·5·7, window 자료, A6 = RAM, H1 연결 9개(`16bcc`/`16bd6` → bit7 → `16bec` → `16c48` → routine → `16c4c` → `16c4e` → `16ce6` RTS; ring 2항목·`d46` 범위 포함), 결정 2 착지 `ce82`, 결정 3 비정상 `D7.B`(cell 0 착지, Duff → `next` 착지)). block 표 736 × C 3, zero-step 736 × C 3, 내부 PC 3,842 전수(정확한 `unsupported animation frame head h8 PC`), 도달 불가 `ADDQ` 8 × C 3, 홀수 PC 5, RAM rollback 탐침 3 + 반환 LONG `10fe40` 2행. successor/carry × 3: split 행 각각을 3곳에서 끊어 C 3가지 모두 원래 행과 같다. checked 오류 23: bank 6, bank 2 합성 없음, cell ROM 읽기, 홀수 표·frame·A2·A4, A6 device·홀수, push·pop device, finish A4 device, 내부 착지 7(`16c30` → `ce8e`, cell 표 홀수 `D7.B`, Duff 중간·꼬리 내부·다음 routine 내부, 도달 불가 `ADDQ` k 0·7), rollback 2.
- [F] 돌연변이 검사(scratch `mut/mut_h8.py`, scratch 사본만 변형, 119개 + identity 통과): 116개를 잡았다. 방향 편집 돌연변이 7개(열 감소 복원, 꼬리 `ADDQ` 삭제·BYTE·LONG, S 꼬리만 삭제, 도달 불가 `ADDQ`를 시작으로, step에 증가 추가)와 `test` 4종(BMI·부호 GE·무부호 GE·GT)을 모두 잡았다(`ADDQ` LONG은 처음 살아남아 번호 순환 fixture를 더해 잡혔다). 살아남은 3개는 H4와 같은 동치 돌연변이(Duff 머리 `CLR.W D4`·`CLR.W D0`, Duff 꼬리 `SWAP D3`)다.
- [F] 실제 ROM 차분(scratch `realrom/real_h8.py` + `batch_h8`, Unicorn PvcMachine vs C++ + 8 `program_rom_*.ms5d`): **자연 정방향 진입이 없으므로** 자연 F5 관측 seed 24개의 pass-end dump(H 시작 상태)에 BYTE `108d3c` bit7 := 1을 선언하고 native H를 돌려 `16c48`이 정방향 표에 들어가는 순간 638개를 pool로 모았다(slot `ce62` 487 · `ce66` 77 · `ce72` 46 · `ce76` 28). case 종류는 H4와 같다(표 slot 진입·n번째 leader snapshot과 `D7.B` 교란·임의 시작·cell 표/Duff 강제 256). seed 1·3·4 × 1,500 case 불일치 0/0/0, 매 seed 시작 736/736, 비교 port 307,684/280,002/320,040. 기대 checked 오류: h8 내부 착지 72/54/53, bank 6 10/12/15, 홀수 주소 37/35/41. native가 멈추지 않은 case 건너뜀 106/77/105. C++ stop C는 모두 Unknown. seed 2는 native 쪽 Unicorn이 TCG 코드 생성 중 abort(`tcg_out_st`, 무작위 상태 case)로 끝나 결과가 없다(C++와 무관; seed 4로 대체).
- [F] native F5 관측 대조(scratch `realrom/nat_h8.py` + 큐 판 `batch_h8q`, `observation.json` SHA256 `4fe4f796…` 읽기 전용): (1) 자연 seed 137개의 pass-end dump 4,975개: 원래 digest = 기록 `h.start` 4,975/4,975, bit7 선언 뒤 H 시작부터 첫 routing 밖 PC까지 native vs C++(선언 external-read 큐 = native가 읽은 열, 소진 확인) 불일치 0. (2) 관측기 typed fixture `path-sprite-forward`(seed 0, frame 6 host write `108d3c |= 80`)의 frame 6·7: 시작 digest 일치, native 전체 H 재실행이 기록 `h.end`·port digest·대기 목록을 2/2 재현, 구간 차분 불일치 0. 합계 4,977 구간, **첫 경계는 모두 `31d6`(H2)**(H1 → H8 → H1 → H3 `5728` 통과). 구간 안 `16bd0` 선언 해제 1,545회. H8 시작 208개 실행, 표 slot 진입 `ce62` 7,439 · `ce72` 2,846 · `ce66` 1,869 · `ce76` 1,572 · `ce6a` 180(k = 0, 4, 1, 5, 2).
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `b7b72d3` pass 14,650·node 126,740 일치·불일치 0 → H8 뒤 `diff_results.json` 바이트 동일(SHA256 `c44c3039…`).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 134·pass 53,602·node 403,729·불일치 0(`verification.json` SHA256 `d3882c20…`) → H8 뒤 같은 totals(`bcf7065c…`; 차이는 source SHA 항목). 새 완주 0, 잃은 seed 0(정방향 경로는 자연 frame에서 실행되지 않는다).
- [U] 남은 미확인: 도달 불가 `ADDQ.W #1,D6` 8개의 유래([I] 편집 흔적). 표 밖 착지(`D1.B` ≥ 8)와 비정상 `D7.B`는 관측에 없다. 역할 의미(SCB 번호·배율·번호 증가 방향)의 해석은 [I]이다. 정방향 경로의 자연 발생(IRQ `16cfa` `BCHG`)은 IRQ 단위(F6) 전에는 확인할 수 없다.
