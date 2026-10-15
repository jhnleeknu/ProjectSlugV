# F6c IRQ sprite writer family A(`f226..11792`)·B(`13b46..16092`) 계약 초안

**구현 전 계약 초안 — 메인 결정 전**

범위 근거는 F6 범위 문서(`animation-machine-irq-f6-scope.md`)의 4절 F6c 행이다. 형식과 결정은 F5 H4(`animation-machine-frame-head-h4-contract.md`, 역방향 head writer `11792..13b46`)와 H8(`animation-machine-frame-head-h8-contract.md`, 정방향 head writer `ce62..f226`) 계약을 따른다.

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 두 범위 모두 fixed이므로 CPU 주소와 file offset이 같다. 짝수 PC는 기존 routing에 없다. 이웃은 다음과 같다.
- `f226` 앞: H8 `ce62..f226`
- `11792`: H4 시작
- `13b46` 앞: H4 끝
- `16092`: F6a clear run(`16092..166bc`)

[F]·[I]·[U] 표기는 범위 문서와 같다. scratch `clos2.py` `units.py` `cmpfam.py` `edits.py`로 계산했다.

## 요약

- [F] **두 family.** IRQ `16cfa`(F6a)가 BYTE `108d3c` bit7을 반전하고 방향을 고른다.
  - 원래 bit7이 1이었으면 `16d26` 경로로 가서 표 A `f226`(정방향 순회)를 쓴다.
  - 원래 0이었으면 `16dde` 경로로 가서 표 B `13b46`(역방향 순회)를 쓴다.
  - 진입은 `16d80 JSR (A3,D7.W)`(A3 = `f226`)와 `16e3c JSR (A3,D7.W)`(A3 = `13b46`)이다. `D7.W` = ((WORD `4(A2)` ≠ `ffff` ? 4 : 0) | `D1.B`) × 4이고, `D1` = WORD `6(A2)`의 bit2를 지운 값이다(H1 결정 5와 같은 식).
- [F] **block 시작.**
  - A: 624개(표 8 + routine 8개 76–78개씩). 목록 SHA256 `81029d4d9dab58cef7e73c45469ae5f061c2dcdc05d4b12cb5d3834c178fd381`.
  - B: 616개(표 8 + routine 75–77개씩). 목록 SHA256 `ccfe82248baf2fd17774a8da0e2865064e1b1ffe3f786ea1556f567f8dd908d5`.
  - Duff 진입은 family마다 128개(routine 4–7 각 32)다.
    - A: `1065c` `10bae` `11112` `1167a` + 8·j(j = 0..31), SHA256 `1487c88d15fcaf87f20e6de4e2a4b8a4be1b9e6ae63032b3cb9bab4aa4aaeb3e`.
    - B: `14f6a` `154b8` `15a18` `15f7c` + 8·j, SHA256 `d10a59d9f24bd78cece9ffcdeb42bc9de308e56160d9d6f842b09a783817b0e0`.
  - 합계는 1,240 + 256 = 1,496이다.
- [F] **template.**
  - capstone 명령 열(4자리 이상 즉값·주소는 `$X`로 정규화)을 `difflib`로 비교했다. family A routine k = H8 routine k + 편집 3–4곳, family B routine k = H4 routine k + 같은 편집 3–4곳이다. A와 B의 차이는 H8과 H4의 차이(방향 편집 6–7곳, H8 계약)와 같은 종류다.
  - 편집 내용은 다음과 같다(routine 0 기준, A `f2b0..f2bc` `f2ec` `f300..f312`).
    1. 삽입: `LSL.W #7,D6; MOVE.W 8(A2),D4; ANDI.W #imm,D4; ADD.W D4,D6; OR.B D7,D6`
       - routine 4–7은 대신 `MOVEQ #0,D2; MOVE.B 5(A2),D2; ADDQ.W #1,D2; MULS.W D2,D3; …; MULU.W D2,D3; ADDI.W #ff,D3; LSR.W #8,D3; OR.B D3,D6`이다(크기 배율).
       - routine 2·3은 삽입이 둘로 나뉜다.
    2. 비교 대상 교체: H8 `CMP.W 6(A4),D6` → A `CMP.W 2(A4),D6`
    3. 삽입: `MOVE.L #imm,D2; MOVE.L D6,D0; ADD.W D2,D0; SWAP D0; MOVE.L D0,(A6); CMP.W 6(A4),D6; BMI.B`. VRAM에 한 건을 더 쓰고 분기가 하나 는다.
  - [I] 이 편집 때문에 IRQ family는 head family의 실행부를 그대로 쓸 수 없다. 대신 같은 구조의 parametric 실행부(표·routine 시작·편집 위치 표)로 구현할 수 있다.
- [F] **자연 도달(범위 문서 5절, P1∪P2∪P2V, palette mirror 없음):** A 65/624, B 60/616이다. Duff 0/256, 표 항목은 일부다. [I] H8처럼 fixture 위주로 검증해야 한다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **실행부 수.**
   - 선택 1(권고): family마다 실행부 하나(`animation_irq_f6c_a_block`, `animation_irq_f6c_b_block`)를 둔다. H4·H8 관례이고 routing은 `f226..11792` 하나와 `13b46..16092` 하나다.
   - 선택 2: A·B를 방향 매개변수 실행부 하나로 묶는다.
   - 둘 다 template 증명(정규화 명령 열 동일성 + 편집 위치 표)을 단위 작업에서 다시 계산해 둔다. 증명이 깨지는 routine은 개별 block 구현으로 내린다.
2. **계산 점프는 live 대상으로 둔다(H4 결정 3과 같음).**
   - `16d80`/`16e3c`의 표 대상 `D1.B` ≥ 8이면 표 밖에 착지한다.
   - routine 안 BRA.W 표(`JMP d(PC,D0.W)`, routine마다 32항목)와 Duff(`JMP d(PC,D3.W)`)의 목표 = 기준 + sext(`D0.W`/`D3.W`)다.
   - 목표가 이 family의 block 시작이면 실행하고, 내부 PC면 `unsupported animation irq f6c PC`, 범위 밖이면 그 PC의 routing에 맡긴다.
   - [F] routine 4(`10226`)의 Duff 선행은 `SUBQ.B #1,D7; ANDI.B #1f,D7; ADD.B D7,D7`(`102d8..102de`)이고, `D3` = `D7.B` × 4다. 즉 0..`f8`, 8 간격 32 진입으로 H4와 같다. [U] 나머지 7 routine × 2 family의 같은 확인.
3. **port.** VRAM 쓰기는 `A6 = 3c0000`에 대한 `MOVE.L Dn,(A6)` 한 건 = `VideoPortWrite` 크기 4 한 건이다(D1 관례). PVC는 `am_write`로 쓴다(routine 머리의 `MOVE.W D7,-7ff0(A5)` + `2ffff2` 쓰기). `MULS.W`/`MULU.W`는 16×16→32 명시 계산이고, C++ 부호 있는 overflow에 기대지 않는다.
4. **무효화 탐침.** 범위 안 PC를 "routing 밖" 탐침으로 쓰는 기존 시험·검증기를 단위 작업에서 검색한다. H1 시험의 writer 표 대상 행(`ce62`/`11792` 계열)과는 겹치지 않는다.

## block 시작 목록

[F] 표 항목은 `BRA.W`(4바이트)다. 각 routine 줄은 그 routine 범위 안의 모든 정적 시작이며, routine 안 BRA.W 표 32항목과 그 대상 32개를 포함한다. Duff 진입은 위 요약의 식으로 정한다(정적 leader에 포함되지 않음).

- A 표 `f226`(8): `f226` `f22a` `f22e` `f232` `f236` `f23a` `f23e` `f242`
- A routine 0 `f246..f636`(77): f246 f29e f2a0 f2cc f2d8 f2da f2ea f2ec f2f4 f300 f314 f358 f35c f360 f364 f368 f36c f370 f374 f378 f37c f380 f384 f388 f38c f390 f394 f398 f39c f3a0 f3a4 f3a8 f3ac f3b0 f3b4 f3b8 f3bc f3c0 f3c4 f3c8 f3cc f3d0 f3d4 f3d8 f3ea f3fc f40e f420 f432 f444 f456 f468 f47a f48c f49e f4b0 f4c2 f4d4 f4e6 f4f8 f50a f51c f52e f540 f552 f564 f576 f588 f59a f5ac f5be f5d0 f5e2 f5f4 f606 f626 f630
- A routine 1 `f636..fa28`(76): f636 f68e f690 f6be f6ca f6cc f6dc f6e4 f6f2 f706 f74a f74e f752 f756 f75a f75e f762 f766 f76a f76e f772 f776 f77a f77e f782 f786 f78a f78e f792 f796 f79a f79e f7a2 f7a6 f7aa f7ae f7b2 f7b6 f7ba f7be f7c2 f7c6 f7ca f7dc f7ee f800 f812 f824 f836 f848 f85a f86c f87e f890 f8a2 f8b4 f8c6 f8d8 f8ea f8fc f90e f920 f932 f944 f956 f968 f97a f98c f99e f9b0 f9c2 f9d4 f9e6 f9f8 fa18 fa22
- A routine 2 `fa28..fe26`(77): fa28 fa80 fa82 fab8 fac4 fac6 fad6 fad8 fae0 faec fb00 fb48 fb4c fb50 fb54 fb58 fb5c fb60 fb64 fb68 fb6c fb70 fb74 fb78 fb7c fb80 fb84 fb88 fb8c fb90 fb94 fb98 fb9c fba0 fba4 fba8 fbac fbb0 fbb4 fbb8 fbbc fbc0 fbc4 fbc8 fbda fbec fbfe fc10 fc22 fc34 fc46 fc58 fc6a fc7c fc8e fca0 fcb2 fcc4 fcd6 fce8 fcfa fd0c fd1e fd30 fd42 fd54 fd66 fd78 fd8a fd9c fdae fdc0 fdd2 fde4 fdf6 fe16 fe20
- A routine 3 `fe26..10226`(76): fe26 fe7e fe80 feb8 fec4 fec6 fed6 fede feec ff00 ff48 ff4c ff50 ff54 ff58 ff5c ff60 ff64 ff68 ff6c ff70 ff74 ff78 ff7c ff80 ff84 ff88 ff8c ff90 ff94 ff98 ff9c ffa0 ffa4 ffa8 ffac ffb0 ffb4 ffb8 ffbc ffc0 ffc4 ffc8 ffda ffec fffe 10010 10022 10034 10046 10058 1006a 1007c 1008e 100a0 100b2 100c4 100d6 100e8 100fa 1010c 1011e 10130 10142 10154 10166 10178 1018a 1019c 101ae 101c0 101d2 101e4 101f6 10216 10220
- A routine 4 `10226..10774`(78): 10226 1027e 10280 102d8 102e4 102e6 102f6 10302 1030a 10312 1031e 10332 1037a 1037e 10382 10386 1038a 1038e 10392 10396 1039a 1039e 103a2 103a6 103aa 103ae 103b2 103b6 103ba 103be 103c2 103c6 103ca 103ce 103d2 103d6 103da 103de 103e2 103e6 103ea 103ee 103f2 103f6 103fa 1040c 1041e 10430 10442 10454 10466 10478 1048a 1049c 104ae 104c0 104d2 104e4 104f6 10508 1051a 1052c 1053e 10550 10562 10574 10586 10598 105aa 105bc 105ce 105e0 105f2 10604 10616 10628 10764 1076e
- A routine 5 `10774..10cc6`(77): 10774 107cc 107ce 1082a 10836 10838 10848 10850 10858 10870 10884 108cc 108d0 108d4 108d8 108dc 108e0 108e4 108e8 108ec 108f0 108f4 108f8 108fc 10900 10904 10908 1090c 10910 10914 10918 1091c 10920 10924 10928 1092c 10930 10934 10938 1093c 10940 10944 10948 1094c 1095e 10970 10982 10994 109a6 109b8 109ca 109dc 109ee 10a00 10a12 10a24 10a36 10a48 10a5a 10a6c 10a7e 10a90 10aa2 10ab4 10ac6 10ad8 10aea 10afc 10b0e 10b20 10b32 10b44 10b56 10b68 10b7a 10cb6 10cc0
- A routine 6 `10cc6..1122a`(78): 10cc6 10d1e 10d20 10d82 10d8e 10d90 10da0 10dac 10db4 10dbc 10dc8 10ddc 10e28 10e2c 10e30 10e34 10e38 10e3c 10e40 10e44 10e48 10e4c 10e50 10e54 10e58 10e5c 10e60 10e64 10e68 10e6c 10e70 10e74 10e78 10e7c 10e80 10e84 10e88 10e8c 10e90 10e94 10e98 10e9c 10ea0 10ea4 10ea8 10eba 10ecc 10ede 10ef0 10f02 10f14 10f26 10f38 10f4a 10f5c 10f6e 10f80 10f92 10fa4 10fb6 10fc8 10fda 10fec 10ffe 11010 11022 11034 11046 11058 1106a 1107c 1108e 110a0 110b2 110c4 110d6 1121a 11224
- A routine 7 `1122a..11792`(77): 1122a 11282 11284 112ea 112f6 112f8 11308 11310 11318 11330 11344 11390 11394 11398 1139c 113a0 113a4 113a8 113ac 113b0 113b4 113b8 113bc 113c0 113c4 113c8 113cc 113d0 113d4 113d8 113dc 113e0 113e4 113e8 113ec 113f0 113f4 113f8 113fc 11400 11404 11408 1140c 11410 11422 11434 11446 11458 1146a 1147c 1148e 114a0 114b2 114c4 114d6 114e8 114fa 1150c 1151e 11530 11542 11554 11566 11578 1158a 1159c 115ae 115c0 115d2 115e4 115f6 11608 1161a 1162c 1163e 11782 1178c
- A 합계 624
- B 표 `13b46`(8): `13b46` `13b4a` `13b4e` `13b52` `13b56` `13b5a` `13b5e` `13b62`
- B routine 0 `13b66..13f52`(76): 13b66 13bbe 13bc0 13bec 13bf8 13c08 13c0a 13c10 13c1c 13c32 13c76 13c7a 13c7e 13c82 13c86 13c8a 13c8e 13c92 13c96 13c9a 13c9e 13ca2 13ca6 13caa 13cae 13cb2 13cb6 13cba 13cbe 13cc2 13cc6 13cca 13cce 13cd2 13cd6 13cda 13cde 13ce2 13ce6 13cea 13cee 13cf2 13cf6 13d08 13d1a 13d2c 13d3e 13d50 13d62 13d74 13d86 13d98 13daa 13dbc 13dce 13de0 13df2 13e04 13e16 13e28 13e3a 13e4c 13e5e 13e70 13e82 13e94 13ea6 13eb8 13eca 13edc 13eee 13f00 13f12 13f24 13f42 13f4c
- B routine 1 `13f52..14340`(75): 13f52 13faa 13fac 13fda 13fe6 13ff6 13ffc 1400a 14020 14064 14068 1406c 14070 14074 14078 1407c 14080 14084 14088 1408c 14090 14094 14098 1409c 140a0 140a4 140a8 140ac 140b0 140b4 140b8 140bc 140c0 140c4 140c8 140cc 140d0 140d4 140d8 140dc 140e0 140e4 140f6 14108 1411a 1412c 1413e 14150 14162 14174 14186 14198 141aa 141bc 141ce 141e0 141f2 14204 14216 14228 1423a 1424c 1425e 14270 14282 14294 142a6 142b8 142ca 142dc 142ee 14300 14312 14330 1433a
- B routine 2 `14340..1473a`(76): 14340 14398 1439a 143d0 143dc 143ec 143ee 143f4 14400 14416 1445e 14462 14466 1446a 1446e 14472 14476 1447a 1447e 14482 14486 1448a 1448e 14492 14496 1449a 1449e 144a2 144a6 144aa 144ae 144b2 144b6 144ba 144be 144c2 144c6 144ca 144ce 144d2 144d6 144da 144de 144f0 14502 14514 14526 14538 1454a 1455c 1456e 14580 14592 145a4 145b6 145c8 145da 145ec 145fe 14610 14622 14634 14646 14658 1466a 1467c 1468e 146a0 146b2 146c4 146d6 146e8 146fa 1470c 1472a 14734
- B routine 3 `1473a..14b36`(75): 1473a 14792 14794 147cc 147d8 147e8 147ee 147fc 14812 1485a 1485e 14862 14866 1486a 1486e 14872 14876 1487a 1487e 14882 14886 1488a 1488e 14892 14896 1489a 1489e 148a2 148a6 148aa 148ae 148b2 148b6 148ba 148be 148c2 148c6 148ca 148ce 148d2 148d6 148da 148ec 148fe 14910 14922 14934 14946 14958 1496a 1497c 1498e 149a0 149b2 149c4 149d6 149e8 149fa 14a0c 14a1e 14a30 14a42 14a54 14a66 14a78 14a8a 14a9c 14aae 14ac0 14ad2 14ae4 14af6 14b08 14b26 14b30
- B routine 4 `14b36..15080`(77): 14b36 14b8e 14b90 14be8 14bf4 14c04 14c10 14c16 14c1e 14c2a 14c40 14c88 14c8c 14c90 14c94 14c98 14c9c 14ca0 14ca4 14ca8 14cac 14cb0 14cb4 14cb8 14cbc 14cc0 14cc4 14cc8 14ccc 14cd0 14cd4 14cd8 14cdc 14ce0 14ce4 14ce8 14cec 14cf0 14cf4 14cf8 14cfc 14d00 14d04 14d08 14d1a 14d2c 14d3e 14d50 14d62 14d74 14d86 14d98 14daa 14dbc 14dce 14de0 14df2 14e04 14e16 14e28 14e3a 14e4c 14e5e 14e70 14e82 14e94 14ea6 14eb8 14eca 14edc 14eee 14f00 14f12 14f24 14f36 15070 1507a
- B routine 5 `15080..155ce`(76): 15080 150d8 150da 15136 15142 15152 15158 15160 15178 1518e 151d6 151da 151de 151e2 151e6 151ea 151ee 151f2 151f6 151fa 151fe 15202 15206 1520a 1520e 15212 15216 1521a 1521e 15222 15226 1522a 1522e 15232 15236 1523a 1523e 15242 15246 1524a 1524e 15252 15256 15268 1527a 1528c 1529e 152b0 152c2 152d4 152e6 152f8 1530a 1531c 1532e 15340 15352 15364 15376 15388 1539a 153ac 153be 153d0 153e2 153f4 15406 15418 1542a 1543c 1544e 15460 15472 15484 155be 155c8
- B routine 6 `155ce..15b2e`(77): 155ce 15626 15628 1568a 15696 156a6 156b2 156b8 156c0 156cc 156e2 1572e 15732 15736 1573a 1573e 15742 15746 1574a 1574e 15752 15756 1575a 1575e 15762 15766 1576a 1576e 15772 15776 1577a 1577e 15782 15786 1578a 1578e 15792 15796 1579a 1579e 157a2 157a6 157aa 157ae 157c0 157d2 157e4 157f6 15808 1581a 1582c 1583e 15850 15862 15874 15886 15898 158aa 158bc 158ce 158e0 158f2 15904 15916 15928 1593a 1594c 1595e 15970 15982 15994 159a6 159b8 159ca 159dc 15b1e 15b28
- B routine 7 `15b2e..16092`(76): 15b2e 15b86 15b88 15bee 15bfa 15c0a 15c10 15c18 15c30 15c46 15c92 15c96 15c9a 15c9e 15ca2 15ca6 15caa 15cae 15cb2 15cb6 15cba 15cbe 15cc2 15cc6 15cca 15cce 15cd2 15cd6 15cda 15cde 15ce2 15ce6 15cea 15cee 15cf2 15cf6 15cfa 15cfe 15d02 15d06 15d0a 15d0e 15d12 15d24 15d36 15d48 15d5a 15d6c 15d7e 15d90 15da2 15db4 15dc6 15dd8 15dea 15dfc 15e0e 15e20 15e32 15e44 15e56 15e68 15e7a 15e8c 15e9e 15eb0 15ec2 15ed4 15ee6 15ef8 15f0a 15f1c 15f2e 15f40 16082 1608c
- B 합계 616

## carry

- [F] 소비 [U]. 단위 작업에서 `flow.py` 방식으로 분류한다. head family(H4·H8)에서는 소비 0이었다.
- [I] 편집 3의 `CMP.W`/`BMI.B`는 같은 block에서 flag를 만들고 읽는다. 표 대상 routine의 RTS 앞 C를 읽는 호출자(`16d84`/`16e40` `BRA`)는 없다.

## 시험 계획(fixture)

- H4·H8 시험 형식을 따른다. 시작 1,240 + Duff 256 전부, 표 밖 착지, 내부 PC 전수, 홀수 PC를 시험한다.
- 두 방향 각각의 sprite 높이 0..31(Duff 진입 32개), `MULS`/`MULU` 경계(`5(A2)` = 0, `ff`; `D6` 음수), 편집 3의 `BMI` 양쪽을 덮는다.
- fixture는 `16cfa` 경로(F6a) 상태에서 `108d3c` bit7 0/1로 두 family를 고른다.

## 검증 계획

1. 실제 ROM 차분: H4·H8 `real_*.py`와 같은 방식이다(무작위 work RAM + sprite 항목, 8 `program_rom_*.ms5d` bank). 비교 항목은 RAM, port, PVC, 레지스터, C다.
2. host-level oracle: `refresh_sprite_queue`(일반 사각형 지원 입력)의 RAM·VRAM port와 F6a+F6c 실행 결과를 비교한다(범위 문서 E8).
3. 자연 도달: F6-D native 인수(범위 문서 E10)에서 자연 IRQ가 지나는 routine·표 항목의 분포를 보고한다.

## 미확인

- [U] 편집 1 즉값(`ANDI.W #imm`)과 편집 3 즉값(`MOVE.L #imm,D2`)의 VRAM 의미(SCB 영역 추정 [I]).
- [U] routine별 Duff 범위 증명(routine 4만 확인).
- [U] head family와의 runtime 관계: 같은 frame에서 head(`16bba`)와 IRQ(`16cfa`)가 반대 방향을 쓰는 이유([I] 이중 buffer).
