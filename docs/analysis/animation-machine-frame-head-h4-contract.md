# F5 frame head H4: 역방향 sprite writer family(표 `11792..117b2`, routine 8개 `117b2..13b46`) 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`)의 §1 sprite writer 행과 §4 H4~H7 행이다: 역방향 writer 표 `11792..117b2`(BRA.W, k=0..7, `11792+4k`), routine `117b2..13b44`(H4 `117b2..11b7e` `11b7e..11f4c` 157 block, H5 `11f4c..126ee`, H6/H7 + Duff 진입 `12ae2` `12ff4` `1350e` `13a2c`, 각 32개). 메인 결정(범위 문서 머리)이 구속한다. 특히 "반복 family(…sprite writer 16종, Duff 진입)는 PC를 매개변수로 받는 executor 하나로 구현해도 된다. 단위 상한은 고유 코드 기준으로 세되, 시험은 모든 진입 PC를 덮어야 한다." H1 계약(`animation-machine-frame-head-h1-contract.md`)의 결정 5(writer 표 JSR은 live 대상, 표·표 밖 착지 routing은 H4/H8 계약이 정함)를 이 문서가 닫는다. 단위 형식은 H1·F4 계약(N26 등)을 따른다.

작업 지시(요약): 먼저 8개 역방향 routine(32항목 표·Duff 진입 포함)이 매개변수만 다른 같은 template인지 원본 바이트로 증명한다. 같으면 family 전체(H4~H7)를 매개변수 executor 하나로 이 단위에서 구현하고, 아니면 H4(표 + k=0,1)만 구현한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. 범위는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기준 작업 트리 `metalslug-h4`(branch `codex/f5-h4-wip`, base `0c89a1f` = F4 N32b + F5 H1 + external-read queue). 범위 `11792..13b46`의 짝수 PC는 기존 routing에 없고 이웃 `11790`(앞 family의 `RTS`)과 `13b46`(다른 writer 표 `13b46..`, 범위 밖)도 routing 밖이다. [F]=원본 바이트·기록 산출물·작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. scratch(저장소 밖) `ms5-scratch/h4/`: `h4tmpl.py`·`h4proof.py`(template 증명), `h4dec.py`(정적 leader, `starts.txt` SHA256 `9298ebb0e54b0ff6d2e614cb61b461540aead93d1a672c180d7dc161e14eea8c`), `h4ana.py`(D7.B 범위·carry), `h4roles.py`(역할 표·구조 검사), `h4xref.py`(외부 참조).

## 요약

- [F] **8개 routine은 3개 flag(H, V, S)를 매개변수로 하는 하나의 template이다.** k = 표 slot 번호(0..7)일 때 H = k bit 0, V = k bit 1, S = k bit 2이다. 정렬 diff(분기 대상 대응까지 확인)에서 차이는 아래 "template 증명"의 고정 삽입점 6곳뿐이고, 모든 조합(k=3 = H+V, k=7 = H+V+S 등)에서 같은 삽입이 같은 자리에 나타난다. cell(18바이트)·Duff 항목(8바이트)·BRA.W 표 항목은 8개 routine에서 바이트 단위로 같다. **따라서 family 전체(H4~H7)를 executor 하나로 이 단위에서 구현한다**(메인 결정 8). 고유 코드는 template 1개(역할 block 14종 + cell·Duff·표 항목 3종)다.
- [F] **정적 block 시작 736개** = 표 slot 8 + routine 0..7 각 75·74·75·74·108·107·108·107. 이 중 BRA.W 표 항목 256(routine당 32), cell 256(routine당 32), Duff 진입 128(S routine 4개 × 32)이다. 범위 문서의 수(writer 608 = 1,216/2, Duff 128 = 256/2, H4 157 = 8 + 75 + 74)와 같다. 범위 안 명령 3,946개를 모두 덮는다(미도달 0).
- [F] **진입:** 외부 code 참조는 H1 `16cb2`(`LEA 11792(PC),A3; JSR (A3,D7.W)`, 복귀 `16ccc`) 하나다(`h4xref.py`; 범위 안 PC와 같은 LONG 값이 fixed ROM 자료에 몇 곳 있으나 code 참조가 아니다 [I]). 그래서 RTS 앞 C의 외부 소비자도 `16ccc BRA 16c86` → `16c86 CMPA`로 없다.
- [F] **계산 점프 12개는 모두 정적으로 제한된다.** routine마다 `JMP d(PC,D0.W)`(cell BRA.W 표, D0.W = 2×D7.B) 하나, S routine마다 `JMP d(PC,D3.W)`(Duff, D3.W = 4×D7.B) 하나다. routine 진입부터의 모든 CFG 경로에서 JMP 시점 D7.B ∈ {0, 2, …, 62}이다(`h4ana.py` 집합 추상해석, 범위 문서 §7 항목 4를 8곳 모두 확인). 그래서 표 32항목·Duff 32항목이 정확한 목표 집합이고 전부 block 시작으로 옮겨 적는다.
- [F] **carry:** 소비 block 0, known 생산 0, FLOW_ONLY 264(표 slot 8 + BRA.W 표 항목 256), Unknown 472. 264 + 472 = 736. X 소비 명령(`ADDX`/`SUBX`/`ROXL` 등)은 없다.
- [F] **I/O:** VRAM `MOVE.L Dn,(A6)`(A6 = `3c0000`이면 size 4 port 1건) cell당 2건, column당 2건, Duff 항목당 2건. PVC `2ffff2`/`2ffff0` WORD 쓰기(head block, bank 선택)와 bank window `200004` LONG 읽기. device 읽기·대기·TRAP·BIOS·callee는 없다.
- [I] 자연 H의 H1 경계 `11792` 842 · `117a2` 651 · `11796` 107 · `117a6` 43(H1 차분, k = 0, 4, 1, 5)은 이 단위로 실행된다. 그 뒤 H는 H1 flush loop로 돌아가 다음 경계(`5728` H3 등)까지 간다(검증 기록에서 측정).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **family 전체를 이 단위에서 구현(H4~H7 통합).** [F] template 증명(아래)이 성립하므로 작업 지시대로 표 `11792..117b2`와 routine 8개(`117b2..13b46`)·Duff 128개를 executor 하나(`animation_frame_head_h4_block`)로 구현한다. 범위 문서 §4의 H5~H7 행은 이 단위에 흡수된다. routing은 하나의 범위 `11792..13b46`이다.
2. **writer 표 JSR(`16cb2`)의 표 밖 착지(H1 결정 5).** [F] `D7.W` = (((WORD `4(A2)` ≠ `ffff`) ? 4 : 0) | `D1.B`) × 4이고 `D1.B`는 bit 2만 지워진 임의 BYTE라 목표는 `11792 + 4m`, m = 0..255(`11792..11b8e`)다. m ≤ 7은 표 slot, m ≥ 8은 routine 0(일부 routine 1 머리) 안이다. 제안: H1처럼 **live 대상**으로 둔다. 착지 PC가 이 단위의 block 시작이면 그 block을 실행하고(예: m = 8 → `117b2`), 내부 PC면 `unsupported animation frame head h4 PC`(checked, 전체 rollback)이다. 이것은 F1 결정 3(중간 착지 = checked 오류)과 같다. [F] 자연 H에서는 m ∈ {0, 1, 4, 5}만 관측됐다(H1 차분).
3. **계산 점프는 live 대상으로 표현하되 정적 범위를 증명한다.** [F] 자연 경로(routine 진입에서 시작하는 모든 경로)에서는 목표가 표 항목 32개·Duff 진입 32개 중 하나다(아래 Duff 범위 증명). block 단위 직접 진입(시험 fixture, 결정 2의 표 밖 착지)에서는 `D7.B`가 임의일 수 있으므로 C++는 `PC := 표 기준 + sext(D0.W)`(Duff: `+ sext(D3.W)`)로 두고 다음 step의 routing에 맡긴다. 목표가 이 단위의 block 시작이면 실행, 내부 PC면 h4 내부 오류, 범위 밖이면 그 PC의 routing(다른 routine의 block일 수도 있다; `13b46` 이후는 `unsupported animation machine PC`)이다. 원본 CPU와 같은 결과다(홀수 목표는 생기지 않는다: D0.W·D3.W가 항상 짝수).
4. **VRAM 쓰기 표현(D7 관례).** [F] 쓰기는 모두 `MOVE.L Dn,(A6)`이다(cell `D4`·`D0`, column 2건, Duff `D4`·`D0`). (A6 & `ffffff`) = `3c0000`이면 원본 쓰기 1건 = `VideoPortWrite`{`3c0000`, 4, 값} 1건(hud·scheduler `4fd8c` 관례)이고, 아니면 `am_write(A6, 4, 값)`(RAM이면 RAM 쓰기, PVC면 PVC, 그 밖은 기존 checked 오류)이다. 자연 진입(H1 `16c6a`)은 A6 = `3c0000`이다.
5. **bank 선택 6·7.** [F] head block은 PVC `2ffff2` := ((LONG `8(A2)` & 7) + 1) << 12, 이어서 `2ffff0` := 0을 쓴다. 기존 PVC 모델(`pvc_effects`, 관측기 `pvc_bank_update`)에서 bank 기준은 쓰기마다 `100000 + ((ff8 >> 8) | (ff9 << 8))`로 다시 계산되고 쓰기 뒤 ff9 bit 15가 지워진다. 그래서 n = 0..5는 `200000 + n × 100000`, n = 6은 `800000`(8 MiB ROM 밖), n = 7은 `2ffff2` = `8000`(기준 `900000`, ff9 := 0) 뒤 `2ffff0` 쓰기에서 기준 `100000`(ROM 안)이 된다. n = 6이면 C++는 다음 `200004` 읽기에서 기존 program bus 오류 `reached program bank physical span outside ROM`(checked, rollback)을 낸다. native 관측기(PvcMachine)는 같은 읽기를 `bank-read-outside-rom` invalid로 멈추므로 실제 ROM 차분에서 이 case는 "기대 checked 오류"로 분류한다. n = 7은 정상 실행(physical `100004 + …`)이다. [I] 자연 관측의 bank 값은 검증 기록에 적는다.
6. **무효화 탐침.** [F] 기존 시험·검증기가 `11792..13b46`을 "routing 밖" rollback 탐침으로 쓰는지 검증 기록에서 확인하고, 있으면 work RAM PC `10fe00..10fefe`로 값만 바꾸거나(엔진 시험) 무효화 목록으로 보고한다(Python 검증기는 수정하지 않는다). H1 시험의 writer 표 대상 행은 stop PC로만 쓰므로 그대로 유효하다 [I].
7. **실행부 파일·오류 문자열.** `engine/src/animation_machine_frame_head_h4.cpp`의 `animation_frame_head_h4_block`. 오류: `unsupported animation frame head h4 PC`(범위 안 내부 PC·표 영역 비정렬 PC). carry 소비자가 없으므로 carry 오류 문자열은 없다. 그 밖의 오류는 기존 공용 helper 문자열(`am_read`/`am_write`/`am_push`/`am_pop`, program bus)이다.

## 원본 바이트 근거

[F] family `11792..13b46` 9,140바이트, SHA256 `3f048ebfeb6cdca23c003a4e827d8efa21e8fcd3de4a2a12bfa53ed2373187fa`.

| 범위 | k | flag | 바이트 | SHA256(앞 16) | block |
| --- | --- | --- | --- | --- | --- |
| `11792..117b2`(표) | - | - | 32 | `e1e7aa7216430bdf` | 8 |
| `117b2..11b7e` | 0 | - | 972 | `b0b65ff99b5a8aeb` | 75 |
| `11b7e..11f4c` | 1 | H | 974 | `79774d0caa978cc0` | 74 |
| `11f4c..1231c` | 2 | V | 976 | `f0f38d49c703668d` | 75 |
| `1231c..126ee` | 3 | H V | 978 | `780a491683310a97` | 74 |
| `126ee..12bfc` | 4 | S | 1,294 | `ea6e06ede34c86e2` | 108 |
| `12bfc..1310e` | 5 | H S | 1,298 | `306c8234abbccc9b` | 107 |
| `1310e..13628` | 6 | V S | 1,306 | `b8e0ecc3e4405483` | 108 |
| `13628..13b46` | 7 | H V S | 1,310 | `e2dc10d484211aad` | 107 |

- [F] 표 slot `11792+4k` = `BRA.W` routine k(`6000xxxx`).
- [F] 반복 단위 바이트: cell 18바이트 `3a1b da43 b305 3805 2c84 d882 301b 2c80 d082`(`MOVE.W (A3)+,D5; ADD.W D3,D5; EOR.B D1,D5; MOVE.W D5,D4; MOVE.L D4,(A6); ADD.L D2,D4; MOVE.W (A3)+,D0; MOVE.L D0,(A6); ADD.L D2,D0`), Duff 항목 8바이트 `2c84 d882 2c80 d082`(`MOVE.L D4,(A6); ADD.L D2,D4; MOVE.L D0,(A6); ADD.L D2,D0`), cell 표 항목 `6000xxxx`(BRA.W). 8개 routine 모두 cell 32개·표 32항목, S routine은 Duff 항목 31개 + 꼬리(`SWAP D3; MOVEM.L (A7)+,D3-D5; SUBI.W #100,D7; BCC.W`)가 같다.

## template 증명

[F] 방법(`h4proof.py`): 각 routine을 명령 열로 디코드하고 분기 operand의 목표 주소를 지운 텍스트로 `SequenceMatcher` 정렬을 한 뒤, 같다고 정렬된 명령의 분기 목표가 정렬 대응으로 서로 옮겨지는지 확인했다. 기준 routine 0(flag 없음)과 4(S)에 대한 차이는 다음뿐이다(주소는 routine 0/4 기준).

| flag | 자리 | 원본 차이 |
| --- | --- | --- |
| H | outer block, `MOVE.W (A3)+,D7` 뒤 | `NEG.W D5` 삽입 |
| H | 열 전진(advance) | 비 H: `test` 앞 별도 block(`11846 ADD.W D4,D5`, S: `12792 MOVE.W D4,D2; ADDI.W #100,D2; CLR.B D2; LSR.W #2,D2; ADD.W D2,D5`). H: 같은 계산을 `SUB`로 바꿔 `clip` block 머리에 둔다(`11c1c SUB.W D4,D5`, S: `12cb4 … SUB.W D2,D5`). 따라서 H에는 advance block이 없고 첫 열에도 전진이 적용된다 |
| H·S | outer, `MOVE.B D5,D4` 뒤 | `SUB.B D3,D4` 삽입 |
| V | column block, `LSL.W #6,D0` 뒤 | `ADD.B D7,D0; NEG.L D2` 삽입 |
| V·S | Duff 머리, `MOVE.B D7,D3` 뒤 | `SWAP D0; ADD.W D3,D0; ADDQ.W #4,D0; SWAP D0` 삽입 |
| S | outer | 비 S `LSL.W #6,D5`(… `MOVE.W #400,D4`) ↔ S `MOVEQ #0,D3; MOVE.B 4(A2),D3; ADDQ.W #1,D3; MULS.W D3,D5; LSL.W #4,D3; SUBI.W #100,D3; MOVE.B D5,D4; CLR.B D5; ASR.L #2,D5` |
| S | test 뒤 | `scale` block(`ANDI.W #ff,D4; ADD.W D3,D4; BMI.B step`) 삽입 |
| S | column 둘째 쓰기 | 비 S `MOVEQ #-1,D0` ↔ S `MOVE.W D4,D0; MOVE.B 5(A2),D0`(`SWAP D0` 뒤) |
| S | 마지막 cell 뒤 | 비 S `MOVEM.L (A7)+,D3-D5; SUBI.W #100,D7; BCC.W 재진입` ↔ S Duff 머리 + `JMP d(PC,D3.W)` + Duff 32 + 같은 꼬리 |

- [F] 정렬 결과: 0→1 편집 3, 0→2 편집 1, 0→3 편집 4, 4→5 편집 4, 4→6 편집 2, 4→7 편집 6, 1→5·2→6·3→7은 0→4와 같은 S 편집(H·V 문맥 형태). 분기 목표 불일치는 advance 재배치로 생기는 재진입 목표(비 H `advance` ↔ H `test`) 한 종류뿐이며 위 표에 반영했다.
- [F] 역할 구조 검사(`h4roles.py`): 각 routine의 block 시작 = {역할 block 12~14개} ∪ {표 32} ∪ {cell 32} ∪ {Duff 32(S)}이고 남는 시작이 없다. 역할별 마지막 분기(대상·fall-through)가 아래 역할 표와 같다.

## block 목록(736)

역할 표(시작 PC). `advance`는 비 H만, `scale`·`duff`는 S만 있다(없으면 –).

| k | head | swap7 | outer | height | step | advance | test | scale | clip | column | table | cells | duff | next | finish |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | `117b2` | `1180a` | `1180c` | `1182a` | `11836` | `11846` | `11848` | – | `11850` | `1185c` | `118a2` | `11922` | – | `11b6e` | `11b78` |
| 1 | `11b7e` | `11bd6` | `11bd8` | `11bf8` | `11c04` | – | `11c14` | – | `11c1c` | `11c2a` | `11c70` | `11cf0` | – | `11f3c` | `11f46` |
| 2 | `11f4c` | `11fa4` | `11fa6` | `11fc4` | `11fd0` | `11fe0` | `11fe2` | – | `11fea` | `11ff6` | `12040` | `120c0` | – | `1230c` | `12316` |
| 3 | `1231c` | `12374` | `12376` | `12396` | `123a2` | – | `123b2` | – | `123ba` | `123c8` | `12412` | `12492` | – | `126de` | `126e8` |
| 4 | `126ee` | `12746` | `12748` | `12776` | `12782` | `12792` | `1279e` | `127a6` | `127ae` | `127ba` | `12804` | `12884` | `12ae6` | `12bec` | `12bf6` |
| 5 | `12bfc` | `12c54` | `12c56` | `12c88` | `12c94` | – | `12ca4` | `12cac` | `12cb4` | `12ccc` | `12d16` | `12d96` | `12ff8` | `130fe` | `13108` |
| 6 | `1310e` | `13166` | `13168` | `13196` | `131a2` | `131b2` | `131be` | `131c6` | `131ce` | `131da` | `13228` | `132a8` | `13512` | `13618` | `13622` |
| 7 | `13628` | `13680` | `13682` | `136b4` | `136c0` | – | `136d0` | `136d8` | `136e0` | `136f8` | `13746` | `137c6` | `13a30` | `13b36` | `13b40` |

- 표 slot: `11792 + 4k`(k = 0..7) → routine k `head`. 8 block, FLOW.
- cell 표 항목: `table + 4i`(i = 0..31) = `BRA.W cells + 18 × (31 − i)`. FLOW.
- cell: `cells + 18j`(j = 0..31). j < 31은 cell 하나, j = 31은 cell + 꼬리(비 S: `MOVEM.L (A7)+,D3-D5; SUBI.W #100,D7; BCC.W 재진입`(fall `next`); S: Duff 머리 + `JMP`).
- Duff 진입(S): `duff + 8j`(j = 0..31). j < 31은 쓰기 2건, j = 31은 꼬리(`SWAP D3; MOVEM.L (A7)+,D3-D5; SUBI.W #100,D7; BCC.W 재진입`, fall `next`). 범위 문서의 Duff JMP 위치 `12ae2` `12ff4` `1350e` `13a2c`는 각 routine `cells + 18×31` block의 마지막 명령이고, 진입 기준은 그 다음 주소(`12ae6` `12ff8` `13512` `13a30`)다.
- 재진입 = 비 H: `advance`, H: `test`.

## 실행 의미(template, flag H/V/S)

표기: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVE.L`·`MOVEA`·`LEA`·`ADDA`·`MULS`·`ASR.L`·`LSR.L`·`ADD.L`·`NEG.L`·`SUBI.L`은 LONG 전체). `d16(An)`·`(An,Dn.W)`는 부호 확장이다. 비교·빌림은 폭별 부호 없는 계산, `BLE`는 부호 있는 WORD 비교, `BMI`는 결과 bit 15다. `video(v)`는 결정 4.

- `head`: `D2` = 0, `D2` = LONG `8(A2)`; `D7.W` = `D2.W` & 7; WORD push `D0.W`; `D0.W` = `D7.W`; WORD `-7ff0(A5)` = `D7.W`; `D7.W` = (((`D7.W` + 1) << 8) << 4)(WORD); PVC WORD `2ffff2` = `D7.W`, `2ffff0` = 0(bank 갱신); `D7.W` = `D0.W`; `D0.W` = WORD pop; `D2` = `D2` >> 1(논리 LONG); `D7.W` = `D2.W` & `3fc`; A3 = `200004`; A3 = LONG(A3 + sext(`D7.W`)); `D2` >>= 8(논리 LONG); `D7.W` = `D2.W` & `3ffc`; A3 = LONG(A3 + sext(`D7.W`)); `D6.W` = WORD `6(A4)`; `D7.W` = WORD(A3), A3 += 2; `D7.W` −= `100`; 빌림이면 `finish`, 아니면 `swap7`.
- `swap7`: `SWAP D7` → `outer`.
- `outer`: `SWAP D6`; `D5.W` = WORD(A3)+; `D6.W` = WORD(A3)+; `D6.W` = −`D6.W`; `D7.W` = WORD(A3)+; [H: `D5.W` = −`D5.W`]. 비 S: `D5.W` <<= 6; `D5.W` += WORD `2(A2)`; `D4.W` = `400`. S: `D3` = 0; `D3.B` = BYTE `4(A2)`; `D3.W` += 1; `D5` = sext(`D5.W`) × sext(`D3.W`)(32 bit `MULS.W`); `D3.W` <<= 4; `D3.W` −= `100`; `D4.B` = `D5.B`; [H: `D4.B` −= `D3.B`]; `D5.B` = 0; `D5` = `D5` >> 2(산술 LONG); `D5.W` += WORD `2(A2)`. 공통: `SWAP D6`; `D7.W` −= `100`; 빌림이면 `finish`, 아니면 `height`.
- `height`: `D7.B` = ((`D7.B` − 1) & `1f`) × 2(BYTE 연산 3개) → `test`.
- `step`: `D2` = 2; `D2.B` += `D7.B`; `D2.W` <<= 1; A3 += sext(`D2.W`); `D7.W` −= `100`; 빌림이면 `next`, 아니면 재진입.
- `advance`(비 H): 비 S `D5.W` += `D4.W`; S `D2.W` = `D4.W` + `100`, `D2.B` = 0, `D2.W` >>= 2(논리), `D5.W` += `D2.W`. → `test`.
- `test`: WORD `D6.W` ≤ WORD `4(A4)`(부호 있음)이면 `finish`, 아니면 S `scale`, 비 S `clip`.
- `scale`(S): `D4.W` &= `ff`; `D4.W` += `D3.W`; 결과 bit 15 = 1이면 `step`, 아니면 `clip`.
- `clip`: [H: advance와 같은 계산을 빼기로(비 S `D5.W` −= `D4.W`; S `D2.W` = (`D4.W` + `100`) & `ff00` >> 2, `D5.W` −= `D2.W`)]; `D2.W` = `D5.W` + `200`; `D2.W` ≥ `5000`(부호 없음)이면 `step`, 아니면 `column`.
- `column`: `D6.W` −= 1; `D0.W` = `D6.W` + `8401`; `SWAP D0`; `D0.W` = `D5.W`; `D0.W` += `D0.W`; `video(D0)`. 비 S: `D0` = `ffffffff`. 공통: `D0.W` = `D6.W` + `8001`; `SWAP D0`. S: `D0.W` = `D4.W`; `D0.B` = BYTE `5(A2)`. `video(D0)`. `D2` = `00020000`(`MOVEQ #2; SWAP`); `D0` = 0; `D0.W` = ((`D6.W` + 1) << 6)(WORD); [V: `D0.B` += `D7.B`; `D2` = −`D2`(LONG)]; `SWAP D1`; `D1.W` = `D0.W` + 1; `SWAP D1`; `SWAP D0`; `D0.B` = `D7.B`; `D0.W` += `D0.W`; LONG push `D5`, `D4`, `D3`(`MOVEM.L D3-D5,-(A7)`: A7 −= 12, LONG(A7) = `D3`, +4 = `D4`, +8 = `D5`); `D3.W` = `D1.W`; `D4` = `D1`; `D3.W` &= `ff00`; PC = `table` + sext(`D0.W`)(결정 3).
- cell 표 항목 i: `BRA.W` → `cells + 18 × (31 − i)`.
- cell j: `D5.W` = WORD(A3)+; `D5.W` += `D3.W`; `D5.B` ^= `D1.B`; `D4.W` = `D5.W`; `video(D4)`; `D4` += `D2`; `D0.W` = WORD(A3)+; `video(D0)`; `D0` += `D2`. j < 31 → 다음 cell. j = 31: 비 S → `D3`, `D4`, `D5` = LONG pop ×3(`MOVEM.L (A7)+`); `D7.W` −= `100`; 빌림이면 `next`, 아니면 재진입. S → Duff 머리: `D0.W` = 0; `D2` = `00020000`; `SWAP D3`; `D3.W` = 0; `D3.B` = `D7.B`; [V: `SWAP D0`; `D0.W` += `D3.W`; `D0.W` += 4; `SWAP D0`]; `D4` = `D0`; `D4.W` = 0; `D0` += `10000`; `D0.W` = `100`; `D3.W` += `D3.W` 두 번; PC = `duff` + sext(`D3.W`)(결정 3).
- Duff j < 31: `video(D4)`; `D4` += `D2`; `video(D0)`; `D0` += `D2` → `duff + 8(j+1)`. j = 31: `SWAP D3`; `D3`, `D4`, `D5` = LONG pop ×3; `D7.W` −= `100`; 빌림이면 `next`, 아니면 재진입.
- `next`: `D7` −= `01000000`(LONG); 빌림(`D7` < `01000000`)이면 `finish`, 아니면 `outer`.
- `finish`: WORD `6(A4)` = `D6.W`; RTS(자연 복귀 `16ccc`).
- [I] 의미(참고): A2는 H1이 고른 sprite 항목, A4는 화면 sprite 번호 범위(`4(A4)` 하한, `6(A4)` 현재 번호, 내림차순 할당), frame 자료는 bank의 2단 포인터 표(`200004`)로 찾는다. part 수(WORD 상위 byte), part마다 x·y·(열 수 << 8 | 줄 수 byte), 열마다 tile WORD 2개 × 줄 수. column은 SCB2/SCB3(`8001+n`/`8401+n`) 쓰기, cell은 SCB1(`(n+1) × 40`) tile 쌍, Duff는 S의 남은 줄을 tile 0/`100`으로 채운다. H/V는 좌우/상하 반전, S는 축소 배율(BYTE `4(A2)`, `5(A2)`)이다. 이 해석은 구현 근거가 아니며 실행 의미는 위 명령 의미만 따른다.

## Duff·cell 표 진입 범위 증명(범위 문서 §7 항목 4)

- [F] `h4ana.py`: routine마다 진입 `head`에서 CFG(분기·fall-through·계산 점프 목표 32개)를 따라 `D7.B`의 가능한 값 집합을 고정점까지 전파했다. `D7`을 쓰는 명령은 `MOVE.W`(전체 값), `ANDI.W #7`, `ADDQ.W #1`, `LSL.W #8`/`#4`, `ANDI.W #3fc`/`#3ffc`, `SWAP D7`(전체 값), `SUBI.W #100`(BYTE 불변), `SUBI.L #1000000`(BYTE 불변), `SUBQ.B #1`, `ANDI.B #1f`, `ADD.B D7,D7`뿐이고 모두 모델에 들어 있다(모르는 writer가 있으면 실패하도록 했다).
- [F] 결과: 12개 JMP(`1189e` `11c6c` `1203c` `1240e` `12800` `12ae2` `12d12` `12ff4` `13224` `1350e` `13742` `13a2c`) 모두에서 `D7.B` ∈ {0, 2, …, 62}(정확히 32값)다. 루프 재진입(`next` → `outer`)은 `MOVE.W (A3)+,D7` → `SUBQ.B`/`ANDI.B #1f`/`ADD.B`를 반드시 다시 지나고, 열 루프(`step`/마지막 cell/Duff 꼬리 → 재진입)는 `SUBI.W #100,D7`만 지나 BYTE를 바꾸지 않는다.
- [F] 색인 레지스터: cell JMP block에서 `D0`은 `MOVEQ #0,D0` 뒤 WORD/BYTE 연산만 받고(`MOVE.W D6,D0; ADDQ.W #1; LSL.W #6;` [V `ADD.B D7,D0`]) `SWAP D0`으로 상위 WORD 0이 하위로 온 뒤 `MOVE.B D7,D0; ADD.W D0,D0`이다 → `D0.W` = 2 × `D7.B` ∈ {0, 4, …, 124} → 목표 `table + 4i`, i = `D7.B`/2. Duff JMP에서 `D3`은 `SWAP D3; CLR.W D3; MOVE.B D7,D3; ADD.W D3,D3; ADD.W D3,D3`뿐이다 → `D3.W` = 4 × `D7.B` ∈ {0, 8, …, 248} → 목표 `duff + 8j`, j = `D7.B`/2(j = 31은 꼬리 block).
- [I] 따라서 cell은 i + 1개, Duff 쓰기는 31 − i쌍이 실행되어 한 열이 항상 32줄을 쓴다(S).

## carry

- [F] **소비 0, known 생산 0.** 모든 Bcc(`BCS`/`BCC`/`BLE`/`BMI`)는 같은 block의 `SUBI`/`CMP`/`CMPI`/`ADD`가 만든 flag를 읽는다(`h4ana.py`: 첫 flag 읽기 앞에 flag 생산이 없는 block 0). `finish`의 `MOVE.W; RTS`가 C를 지우지만 복귀점 `16ccc`(FLOW) 다음 `16c86 CMPA`가 다시 만든다. 외부 호출자는 `16cb2` 하나다. 그래서 carry 오류 문자열은 없다.
- [F] **FLOW_ONLY 264 block**(C 보존): 표 slot 8(`11792..117ae`)과 routine마다 cell 표 항목 32(`BRA.W`만). carry 보존 목록(`carry_preserving_pc`)에 주석 붙은 case group 하나로 넣는다.
- [F] **Unknown 472 block**: 나머지(`MOVE`/`MOVEQ`/`SWAP`/`ADD`/`SUB`/`CMP`/`AND`/`EOR`/`NEG`/`LSL`/`LSR`/`ASR`/`CLR`/`MULS`/`MOVE.L`-to-(A6) 등; `SWAP`도 C를 지운다).

## 경계·I/O·스택

- [F] **경계:** 이 단위에는 callee·TRAP·BIOS·대기가 없다. 나가는 길은 `finish`의 RTS(자연 `16ccc`, H1)와 결정 2·3의 live 목표뿐이다. 단위 시험은 다른 단위 PC를 "routing 밖" 탐침으로 쓰지 않고(F4 시험 경계 관례), rollback 탐침은 work RAM PC `10fe00..10fefe`를 쓴다. H1 블록(`16cb2` 진입, `16ccc` stop)은 실행 경로·stop으로만 쓴다.
- [F] **읽기:** sprite 항목 LONG `8(A2)`·WORD `2(A2)`·BYTE `4(A2)` `5(A2)`, WORD `4(A4)` `6(A4)`, bank window LONG `200004 + (… & 3fc)`(live PVC bank), 둘째 포인터 LONG, frame 자료 WORD(A3)+(fixed ROM, bank window, RAM 어디든 live bus), stack.
- [F] **쓰기:** WORD `-7ff0(A5)`(bank 사본), PVC `2ffff2`·`2ffff0`(`am_write`: PVC 기억·bank 공식·port 기록 각 1건), VRAM `video()`(결정 4), WORD `6(A4)`, stack(WORD push/pop `D0`, `MOVEM.L` 12바이트).
- [F] **스택:** head의 WORD push → pop(같은 block), column의 `MOVEM.L D3-D5,-(A7)`과 마지막 cell(비 S)·Duff 꼬리(S)의 `MOVEM.L (A7)+,D3-D5`, `finish` RTS. work RAM 밖 스택은 기존 checked 오류다.

## 구현 범위와 규약

- routing: `11792..13b46` 하나(짝수 PC 4,570개, 시작 736, 내부 3,834). 내부 PC 직접 진입과 표 영역(`11792..117b2`)의 4바이트 비정렬 PC는 `unsupported animation frame head h4 PC`다.
- executor: routine 8개의 역할 PC 표(위 표의 값을 C++ 상수 표로 옮겨 적음)와 flag로 매개변수화한 함수 하나. 반복 block(cell, Duff 항목)은 원본처럼 block 실행 한 번이 cell 하나(또는 Duff 항목 하나)다.
- 공유 최소 수정: `animation_machine.cpp` routing `else if` 하나(마지막 `else return am_error` 앞)와 carry 보존 case group 하나(264 PC, `// BTST/BEQ changes only Z` 앞), `animation_machine_internal.h` 선언 하나(끝), `Makefile`(source 목록·test target·실행 줄), `tools/verify_animation_machine.py` SOURCES. 기존 실행부는 고치지 않는다. public header는 바꾸지 않는다.

## 시험 계획

- 단위 시험 `engine/tests/animation_machine_frame_head_h4_test.cpp`(`run_animation_machine`만): scratch Unicorn 생성 fixture(PvcMachine, 원본 code + 합성 물리 바이트: bank window의 1단 포인터 표만 합성, 2단 포인터·frame 자료·sprite 항목은 work RAM). 
  - 시작 736개 전부: block 표(시작 × 들어오는 C clear/set: native 후속·digest·port 수·C 분류), zero-step(736 × C 3), 내부 PC 3,834 전수(정확한 오류), 범위 양끝 홀수·밖 PC.
  - 전체 routine fixture: k = 0..7 × 줄 수 1..32(cell 표 32항목·Duff 32항목 전부), 열 여러 개(재진입), part 여러 개(`next` → `outer`), x clip(`step`), `test` 조기 종료, S 배율·`scale` 음수, H/V, H1 `16cb2` 진입 → RTS `16ccc` → H1 flush loop 끝까지(연결).
  - successor/carry × 3, 결정 2 표 밖 착지(block 시작 = 실행, 내부 = h4 오류), 결정 3 계산 목표의 비정상 `D7.B`(홀수 → 내부 오류, ≥ 64 → 다른 routine block 또는 범위 밖), 결정 5 bank 6 오류·bank 7(기준 `100000`) 정상 실행, checked 오류(홀수 포인터, ROM 바이트 없음, A6 device, 스택 device), RAM rollback 탐침 `10fexx`.
- 돌연변이 검사(routine별 매개변수: flag 표·역할 PC·stride 포함), UBSan, 실제 ROM 차분(Unicorn vs C++ + 8 `program_rom_*.ms5d`, 모든 시작), native F5 관측 자연 H 차분(H1 + 이 단위, 어디서 멈추는지 보고; `5728`은 H3 경계로 남는다), base frame pass·RNG 400 무변화(기준 `0c89a1f`: frame pass 14,648 pass·node 126,688 일치·불일치 0, RNG complete 134·pass 53,600·node 403,677·불일치 0).

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다. 작업 트리 `metalslug-h4`(base `0c89a1f`), scratch `ms5-scratch/h4/`.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_frame_head_h4.cpp` `abd149d66e8270c7`, `engine/tests/animation_machine_frame_head_h4_test.cpp` `f7ca1602067a9688`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나 `11792..13b46`, carry 보존 case group 하나 264 PC; `d3ae5f5d5ac55da9`), `engine/src/animation_machine_internal.h`(선언 하나; `65d338f9afdbbc83`), `Makefile`(source 목록·test target·실행 줄; `0760ae6d415f62a0`), `tools/verify_animation_machine.py` SOURCES(`991f1522732a5cfe`). public header와 기존 실행부·시험은 바꾸지 않았다(결정 6: 무효화 탐침 없음, 아래).
- [F] 실행부 = 역할 표 8행(위 표와 같은 값) + flag. 시험이 계약 역할 표에서 계산한 시작 집합(736)과 FLOW 집합(264)이 scratch `starts.txt`·`flow.txt`와 같다.
- [F] `make -j3 all test`(동시 3 process 상한): exit 0, 경고 0, `Assert` 줄 0(scratch `make_all2.log`), `tools/tests` unittest 257개 OK. H4 test 출력: `animation machine frame head h4: 554 fixtures (20 checked errors, 20 kept C), 736 blocks, 13486 calls`. H1 test 등 기존 시험은 그대로 통과했다.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`, scratch `build_test.sh ubsan`): H4 test 통과, runtime error 0(`ubsan.log`).
- [F] 단위 시험(`run_animation_machine`만; scratch `gen/gen_h4.py` Unicorn PvcMachine 생성, 최종 `tables_h4.inc` SHA256 앞 16 `ed83c6cc77587327`): fixture 554(성공 534, checked 오류 20). 합성 물리 바이트는 bank window의 1단 포인터 표(bank 0·1·5·7 기준)와 bank 0 window 안 2단 표·frame뿐이며 생성기는 모든 bank 읽기가 합성 범위 안이고 fixed ROM 자료 읽기·장치 읽기가 0임을 확인했다.
  - full fixture가 시작 736개를 모두 지난다(k 0..7 × 줄 수 1..32 = cell 표·Duff 항목 전부, 여러 part·열, x clip, `test` 조기 종료·부호 있는 비교, 줄 수 byte `00 21 41 ff`, clip 경계 `D2.W` = `5000`/`4ffe`, S 배율 6종 × x 3종, bank 1·5·7, bank window 자료, A6 = RAM, H1 `16c86` → `16cb2` → routine → `16ccc` → `16cce` → `16ce6` RTS 연결 8개, 결정 2 착지 `117b2`, 결정 3 비정상 `D7.B`(cell 0 착지, Duff → `finish` 착지)).
  - block 표 736 × 들어오는 C 3가지(native 후속·digest·port 수·C 분류), zero-step 736 × C 3, 내부 PC 3,834 전수 × C 2가지(정확한 `unsupported animation frame head h4 PC`), 홀수 PC 5, RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 반환 LONG `10fe40` 2행(video port 포함 전체 rollback).
  - successor/carry × 3: split 행 70개 각각을 native trace의 첫 출현 block 시작 3곳에서 끊고 C++ 출력에서 다시 시작해 C 3가지 모두 원래 행과 같다(port 연결 포함). FLOW 행(표 slot 8 × C 2, 표 항목 2 × C 2)은 들어오는 C를 유지한다.
  - checked 오류 20: bank 6(`reached program bank physical span outside ROM`), bank 2 합성 없음·cell ROM 읽기(`missing or ambiguous physical program bus ROM byte`), 홀수 표·frame·A2·A4(`program bus requires even WORD/LONG address`), A6 device·A4 device(`unsupported animation machine write device`), A6 홀수(`invalid animation machine write size/alignment`), push device 2(`program bus write requires RAM mirror units`), pop device 2(`unsupported program bus device address`), 내부 착지 4(`16cb2` → `117be`, cell 표 홀수 `D7.B`, Duff 중간 `12bea`, 다음 routine 내부 `12bfe`), rollback 2(`unsupported animation machine PC`).
- [F] 돌연변이 검사(scratch `mut/mut_h4.py`, scratch 사본만 변형, 110개 + identity): 107/110을 시험이 잡았다. 첫 실행에서 살아남은 `height-mask`(`ANDI.B #1f` → `#3f`)와 `clip-limit`(`>=` → `>`)는 줄 수 byte·clip 경계 fixture를 더해 잡혔다. 잡힌 항목: routine별 매개변수(역할 PC 14종, H/V/S flag 7개, 표·cell·Duff 기준, stride 18/8, 항목 수 32, 표 slot 대응), 모든 분기 대상·조건, 비교 폭·부호(`BLE` 부호 있는 WORD), `MULS` 부호, `ASR.L`, BYTE/WORD 폭(`EOR.B`, `ADD.B`, `ADD.W`), port 크기·주소, PVC 쓰기 값·순서, 변위(`-7ff0` `4(A2)` `5(A2)` `4(A4)` `6(A4)`), index mask(`7` `3fc` `3ffc`), 이동 수, `MOVEM` 순서·개수, V `NEG.L`·`ADD.B`·Duff `ADDQ #4`, `next` 한계, 오류 문자열 2곳, carry group(빼기·더하기), routing 양끝. **살아남은 3개는 동치 돌연변이다(원본의 중복 명령):** Duff 머리의 `CLR.W D4`(`D0.W`가 같은 block 앞에서 `CLR.W D0`으로 이미 0이고 V 삽입은 상위 WORD만 바꾼다), `CLR.W D0`(그 뒤 `D0.W`는 `MOVE.W #100,D0`으로 덮이고 `D4.W`는 지워지며 `ADDI.L #10000`은 하위 WORD에서 올림이 없다), Duff 꼬리의 `SWAP D3`(바로 뒤 `MOVEM.L (A7)+,D3-D5`가 `D3` 전체를 덮는다). 실행부는 원본 명령을 그대로 따르므로 이 명령들도 남겨 둔다.
- [F] 실제 ROM 차분(scratch `realrom/real_h4.py`, Unicorn PvcMachine vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, 실제 frame 자료): 자연 F5 관측의 H 시작 상태에서 H1 `JSR (A3,D7.W)`가 표에 들어가는 순간 638개(seed 24개)를 pool로 모았다(자연 bank 선택 2: 194, 3: 444, A6 = `3c0000` 638/638). case 종류: 표 slot 진입(k 무작위, flip·배율·x·한계 필드 무작위, A6 = RAM 5%, bank 6/7 4%), native 실행 중 n번째 leader의 snapshot(`height`·column·Duff 머리에서 `D7.B` 교란), 시작 PC 무작위, cell 표·Duff 항목 강제(k × i 256개). 3 seed × 1,500 case 불일치 0/0/0, 매 seed 시작 736/736 진입, 비교 port 221,332/305,970/274,842건. 기대 checked 오류(native 분류 = C++ 문자열): 내부 착지 62/60/51, bank 6 9/15/13, 홀수 주소(Unicorn은 68000 address error를 내지 않음; C++는 정렬 오류) 37/29/37. native가 깨끗이 멈추지 않은 case(무작위 레지스터로 300만 명령 안에 끝나지 않음 등)는 건너뜀 86/100/82. C++ stop C는 모두 Unknown.
- [F] native F5 관측 차분(scratch `realrom/nat_h4.py`, `artifacts/animation_machine_frame_head_native/observation.json` SHA256 `4fe4f796…`, 읽기 전용): 자연 seed 136개의 pass-end dump 4,975개에서 (a) 시작 digest = 기록 `h.start` 4,975/4,975, (b) 선언 규약으로 H 전체 native 재실행이 기록 `h.end`·port digest·대기 목록을 4,975/4,975 재현, (c) H1 + H4 경계까지 native vs C++ 불일치 0. **H 구간이 처음 닿는 경계는 이제 모두 `5728`(H3) 4,975**다(H1만일 때 `5728` 3,332 + 역방향 writer 표 1,643). 자연 segment에서 실행된 H4 시작 208개, 표 slot 진입 `11792` 7,433 · `117a2` 2,844 · `11796` 1,864 · `117a6` 1,568 · `1179a` 180(k = 0, 4, 1, 5, 2). 구간 안의 `16bd0` 선언 해제 1,543회. C++ stop C는 모두 Unknown.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `0c89a1f` pass 14,648·node 126,688 일치, 불일치 0 → H4 뒤 `diff_results.json` 바이트 동일(SHA256 `ad8c6c0a…`).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 134·pass 53,600·node 403,677·불일치 0(`verification.json` SHA256 `d059ad2c…`) → H4 뒤 같은 값(`17709bc2…`; 차이는 `engine_source_sha256`의 `animation_machine.cpp`·새 파일 항목과 seed 2개 기록의 `current_router_sha256`뿐). 새 완주 0, 잃은 seed 0(frame head는 여전히 F2 pass의 stop이다).
- [F] 무효화 목록: 없음. 엔진 시험·Python 도구에서 `11792..13b46`을 "routing 밖" 탐침으로 쓰는 곳은 없다(검색; 값이 범위에 드는 상수는 레지스터 자료값이다). H1 시험의 writer 표 대상 stop 행(`11792..117ae`, 표 밖 착지 `11806` 등)은 stop PC로만 쓰므로 그대로 통과한다.
- [U] 남은 미확인: 정방향 family(`ce62`, H8~H11)는 별도 단위다(같은 template인지는 확인하지 않았다). 표 밖 착지(`D1.B` ≥ 8)와 비정상 `D7.B`는 자연 관측에 없다. 역할 의미(SCB 번호·배율)의 해석은 [I]이다.
