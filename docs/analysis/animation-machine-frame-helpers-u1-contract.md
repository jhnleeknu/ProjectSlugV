# `480bc` 프레임 helper 묶음 U1: 호출 shell과 가벼운 helper 계약

Baseline: 카드 메뉴 연결 통합 이후. 범위 근거는 `animation-machine-480bc-scope.md`. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 확정했다. 명령 단위 정답은 원본 바이트다. 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `480bc..480f2` | `4ebaf5844eb90001a73c4eb900049b0c4eb90004aa884eb9000b4a2a4eb90006f1c24eb90004701e4eb9000e8a484eb90002efa64e75` |
| `47642..47672` | `422d568e41ed8cb870006100000841ed8da870014eb90000289e640000120828000700616600000801ed568e4e754e75` |
| `6f1c2..6f1c4` | `4e75` |
| `2efa6..2efdc` | `122d54914a2d549056c01b405491670000144a016600000c303c1d284eb900003af84e754a016700000c303c1d284eb900003c444e75` |
| `3c44..3c7c` | `3f0041edcd82322dcd8ab26dcd8c6700001643f01000544102410006b05166000004425160e470146100fe5a10176100fe54301f6000fe4e` |
| `b4a2a..b4ab0` | `3b7c80005d4870004eb9000493926400002470004eb90001c028b2fc0000670000144c91000fd0680042d268004648ad000f5d483b7c80005d5070014eb9000493926400002470014eb90001c028b2fc0000670000144c91000fd0680042d268004648ad000f5d5041ed5d584a1067000004531054484a1067000004531054484ebafd724e75` |
| `49392..493bc` | `bbfc00108000670000044e4f41ed8cb8024000016700000641ed8da8012d568e67000006003c00014e75` |
| `1c028..1c052` | `3f004eb90004d9d6301fb0fc0000670000044e7541ed8cb8024000016700000641ed8da8226800564e75` |
| `4d9d6..4da08` | `49ed5cba4a006700000649ed5ce64a546600000a207c000000004e75200e302c00066600000630404e752040226c00084e75` |
| `b481e..b4850` | `302d800e024000016600000e43ed5d5c45ed5d986000000a43ed5d9845ed5dd47000b5c96700000a3280d2fc000a60f24e75` |
| `4701e..4706c` | `41ed5646700020c020c020c020c020c020c020c020c020c03b7c0007567c41ed561a3028002a6700000e53403140002a4eb900043e384a6800266b0000066100fef441e8ffd4536d567c64d64e75` |
| `46f52..4701e` | `226800263028001c322800203428001436280018b0426f000004c540b2436f000004c7414c9900f05247e74ce74de74ee74fdc44de45d044d245d446d6473e2d567c7c001c11e51e0206000357466400000e464643ed56690fe151cefffc383cffa03a3c01ffb0456e00006094446d00005a90446c0000047000b2456f0000043205383c00803a3c01ffb2456e00003c96446d00003692446c0000047200b6456f0000043605ea48ea4a9440ea49ea4b964143ed5646d2c00fd951cafffc43ed5656d2c10fd951cbfffc4e75` |

## 실행 의미(사실, A5=`108000` 기준 절대 주소)

1. `480bc` JSR `47642`(복귀 `480c0`), JSR `1a73c`(복귀 `480c6`), JSR `49b0c`, JSR `4aa88`, JSR `b4a2a`, JSR `6f1c2`, JSR `4701e`, JSR `e8a48`, JSR `2efa6`, `480f0` RTS. 이번 단위에서 `1a73c`·`49b0c`·`4aa88`·`e8a48`은 실행부가 없는 경계이므로 `480bc` 자연 실행은 `1a73c` stop까지다. 나머지 helper는 직접 진입 조건으로 검증한다(선언된 복귀 LONG을 stack에 둔 fixture).
2. `47642` BYTE 0→`10d68e`; A0=`100cb8`, D0=0, BSR `47656`(복귀 `47650`); A0=`100da8`, D0=1, `47656`으로 fall-through. `47656` JSR `289e`(기존, 복귀 `4765c`) 뒤 BCC `47670` RTS(known C 소비); C=1이면 BTST #7,61(A0)≠0이면 RTS, 아니면 BSET D0(mod 8),`10d68e` 후 RTS. 같은 `47656` 본문이 BSR과 fall-through로 두 번 실행되어 RTS가 두 번 일어난다.
3. `6f1c2` RTS만.
4. `2efa6` D1.B=BYTE `10d491`; TST.B `10d490`; SNE D0; BYTE D0→`10d491`; Z(=SNE 결과가 아니라 MOVE.B D0의 결과 BYTE)가 0이면 `2efca`, 아니면 이전 D1.B≠0이면 RTS, 0이면 D0.W=`1d28`, JSR `3af8`(기존). `2efca` 이전 D1.B=0이면 RTS, 아니면 D0.W=`1d28`, JSR `3c44`.
5. `3c44` D0.W push; A0=`104d82`; D1.W=WORD `104d8a`; 루프: D1==WORD `104d8c`면 끝; A1=A0+D1.W(부호확장); D1=(D1+2)&6; WORD (A1)==D0.W면 CLR.W (A1); 반복. 끝에서 MOVEQ 14,D0, BSR `3ac8`(기존); D0.B=BYTE (A7)(push한 WORD의 상위 BYTE, live stack 읽기); BSR `3ac8`; D0.W pop; BRA `3ac8`(그 RTS가 `3c44` 호출자로 돌아감).
6. `b4a2a` WORD `8000`→`10dd48`; D0=0, JSR `49392`(복귀 `b4a38`), BCC `b4a5e`; C=1이면 D0=0, JSR `1c028`(복귀 `b4a44`), CMPA.W #0,A1 같으면 `b4a5e`, 아니면 MOVEM.W (A1),D0-D3(부호확장 LONG), D0.W+=42(A0), D1.W+=46(A0), MOVEM.W D0-D3→`10dd48`. 같은 순서로 D0=1, `10dd50`. `b4a92` A0=`10dd58`: BYTE≠0이면 SUBQ.B, A0+=2, 다시 한 번, A0+=2; JSR `b481e`(복귀 `b4aae`); RTS.
7. `49392` CMPA.L #`108000`,A5 다르면 `4939c` TRAP #f(경계, 실행하지 않음). 같으면 A0=`100cb8`; D0.W AND 1≠0이면 A0=`100da8`; BTST D0(mod 32 아님: 메모리 피연산자이므로 mod 8),`10d68e`; 0이면 RTS(Z만 바뀜, C는 ANDI.W가 지운 Clear), 아니면 ORI CCR #1(known Set) RTS. 즉 `493a2` ANDI.W #1,D0가 C=0을 만들고 `493ae` BTST는 C를 바꾸지 않는다.
8. `1c028` D0.W push; JSR `4d9d6`(복귀 `1c030`); D0.W pop; CMPA.W #0,A0≠0이면 RTS; 아니면 A0=`100cb8`(D0 AND 1이면 `100da8`), A1=LONG 56(A0), RTS. `4d9d6` A4=`10dcba`(D0.B≠0이면 `10dce6`); TST.W (A4)=0이면 A0=0 RTS; 아니면 D0.L=A6, D0.W=WORD 6(A4), 0이면 A0=D0.W 부호확장(=0) RTS, 아니면 A0=D0.L(A6 상위 WORD|WORD), A1=LONG 8(A4), RTS.
9. `b481e` D0.W=WORD -7ff2(A5)=`10000e` AND 1; 0이면 A1=`10dd5c`, A2=`10dd98`; 아니면 A1=`10dd98`, A2=`10ddd4`; D0=0; A1≠A2인 동안 WORD 0→(A1), A1+=a. RTS.
10. `4701e` `10d646`부터 LONG 0 9개(36바이트); WORD 7→`10d67c`; A0=`10d61a`; 루프: D0.W=2a(A0)≠0이면 SUBQ.W, 2a(A0)←D0, JSR `43e38`(기존, 복귀 `47054`); TST.W 26(A0) 음수가 아니면 BSR `46f52`(복귀 `47060`); A0-=2c; SUBQ.W #1,`10d67c`, BCC 반복(이전 WORD가 0이 아니면). 8회.
11. `46f52` A1=LONG 26(A0)(rect 자료); D0..D3=WORD 1c,20,14,18(A0); 부호 비교로 정렬(BLE/EXG); MOVEM.W (A1)+,D4-D7; D7+1; 각 LSL.W #3; D6+=D4, D7+=D5; D0+=D4, D1+=D5, D2+=D6, D3+=D7; D7=WORD `10d67c`; D6=BYTE (A1) ROL.B #2 AND 3, SUBQ.W #3, borrow면 NOT.W D6 후 A1=`10d669`에서 BSET D7,-(A1) DBRA; 이후 X 범위(`ffa0`/`1ff`, BGT/BLT 부호)(원본은 X 단계에서 `46fcc` CMP.W D5,D1 / `46fd2` MOVE.W D5,D1로 D1을 자르고 D2는 자르지 않는다. 따라서 X bin이 16바이트 X 배열을 넘어 Y 배열까지 쓸 수 있다. 원본 버그 여부 미확인)와 Y 범위(`0080`/`1ff`)로 잘라 LSR.W #5 bin을 `10d646`·`10d656` BYTE 배열에 BSET D7 DBRA. 범위 밖이면 RTS.

## 구현 범위와 규약

- 새 실행부 파일 `engine/src/animation_machine_frame_helpers.cpp`(함수 `animation_frame_helpers_block`): 위 표의 범위 전부.
- Block 시작 PC는 분기 대상·조건분기 fallthrough·호출 복귀·호출 진입 전부와 `289e`/`49392` 복귀 BCC(known C 소비). 구현자가 원본 opcode로 목록을 계산해 보고하고 메인이 리뷰한다. 묶음 규칙은 기존과 같다(Z/N/V/C 생산자와 소비 분기는 같은 block; BSR 복귀 BCC/BCS는 modeled carry 소비, Unknown이면 `frame helper caller requires known carry`).
- 경계(실행부 없음): `1a73c`, `49b0c`, `4aa88`, `e8a48`, `4939c`(TRAP #f). stop을 그 PC로 주면 멈추고 다른 stop이면 `unsupported animation machine PC`와 전체 rollback.
- Carry: `49392` 반환은 known(Set: ORI 경로, Clear: `493a2` ANDI.W가 지우고 BTST·BEQ·RTS만 지나는 경로). FLOW_ONLY-only block만 보존. 그 밖 Unknown.
- BTST/BSET Dn,메모리의 bit 번호는 mod 8, 레지스터 피연산자는 mod 32. MOVEM.W 로드는 부호확장. DBRA는 WORD 감소·-1 종료. EXG, ROL.B, NOT.W, 부호 비교(BLE/BGT/BLT/BGE)를 명시 구현한다.
- `3c44`의 MOVE.B (A7)은 live stack BYTE 읽기다.
- 시작 상태: 카드 체인 RAM은 `480bc` 시점에 의사난수이므로 쓰지 않는다. `artifacts/stage_frame`·`artifacts/stage_entry_body`의 일관된 seed(입력 RAM·register)를 선언 fixture로 사용하고 출처 SHA를 기록한다.

## 검증 조건(최소)

- 자연: stage seed에서 `480bc` 진입→`47642`(두 player 객체, `289e` 결과와 61 bit7 조합)→`1a73c` stop.
- 직접 진입(선언 복귀 LONG): `b4a2a`(두 player의 `49392` Set/Clear, `1c028` A1 null/비null, `4d9d6` A4 두 갈래와 6(A4) 0/비0, `10dd58` BYTE 0/비0, `10000e` bit0 두 갈래), `4701e`(2a 타이머 0/비0으로 `43e38` 호출, 26 음수/비음수, `46f52` 범위 안/밖·DBRA 횟수·ROL 경로), `2efa6`(`10d490`/`10d491` 네 조합, `3af8`·`3c44` 경로), `3c44`(ring 일치/불일치, 빈 ring), `6f1c2`.
- 경계: A5≠`108000`→`4939c` TRAP stop, 비경계 stop rollback, 홀수 A0/A1/A4/A7 오류 rollback, 내부 PC 거부, Unknown carry로 BCC 진입 오류, zero-step.
- 비교 항목은 기존과 같다.

## 미확인·범위 밖

`1a73c`·`49b0c`·`4aa88`·`e8a48` 본문(U2~U7), TRAP #15의 의도, `10d68e`·`10dd48..`·`10d646..` 배열의 게임 의미, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
