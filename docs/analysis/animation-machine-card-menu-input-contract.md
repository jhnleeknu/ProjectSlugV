# 카드 메뉴 입력 프레임(`a406`), 자동 선택 타이머 hook(`bf2c`)과 선택·닫기 시작 계약

Baseline: 메뉴 열림 단위(리뷰0235) 통합 커밋. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 범위·경로를 확정했다. 명령 단위 정답은 원본 바이트이며 아래 요약은 폭·부호·경로 근거다. 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `a406..a5d2` | `102a0004b02a000c6400000a6100ff3470004e7508aa0000000f6700000a2f0a4ebaf9f2245f2b4aff122652266b0006b6fc0000670000082f0a4e93245f2b4aff12156a000700080c2a00ff000e6700001c2f0a7000102a000e157c00ff000e6100f6d6245f2b4aff1260dc700072001b41ff1a082a0000000d67000006102dccba082a0001000d67000006122dccc00800000056c60801000056c702060001020700028e066700000a1b47ff1a600000b00800000156c60801000156c702060001020700028e066700000a1b47ff1a6000009c0800000256c60801000256c702060001020700028e066700000a1b47ff1a6000009c0800000356c60801000356c702060001020700028e066700000a1b47ff1a600000840800000556c60801000556c702060001020700028e066700000a1b47ff1a6000004e0800000456c60801000456c702060001020700028e066700000a1b47ff1a600000226000006a08ea0001000f6100fca86000003808aa0001000f6100fc9a6000002a157c0003000e60000020157c0004000e60000016157c0001000e6000000c157c0002000e600000020c2a00ff000e6700001c2f0a7000102a000e157c00ff000e6100f57a245f2b4aff1260dc70004e75` |
| `bf2c..bf94` | `302e007e6700001653403d40007e6600000c303c00034eb900009ff44a2e00806700000e4eb90000a70a700060000034700012390010fdb60c01000167080c010003660000060040000112390010fdb70c01000167080c01000366000006004000024ef900009fc4` |
| `9fc4..9fce` | `246dff121540000d4e75` |
| `9ff4..9ffe` | `246dff121540000e4e75` |
| `a70a..a71a` | `303c1a5b4eb900003af84ef90000a1ee` |
| `a1ee..a1fa` | `1b7c0002ff1b246dff0e4e75` |

## 실행 경로(사실)

진입: 열림 단위 뒤 자식 프레임 재진입(선언 PC=`2ab8`)→`c2ba` JSR `a370`→`a3e2`에서 -e5=0이면 `a406`. 열림 단위의 `a370`·`a3e2`·`9b3e`·`9e1a`·`a216`·`a348`·`3af8` 실행부를 그대로 쓴다.

1. `a406` D0.B=4(A2), CMP.B c(A2), BCC `a41a`(unsigned 4≥c). 아니면 `a412` BSR `a348`, `a416` MOVEQ 0,D0 RTS.
2. `a41a` BCLR #0,f(A2)(이전 bit0으로 Z), BEQ `a42c`; bit0이 1이었으면 `a424` A2 push, JSR `9e1a`(복귀 `a42a`), pop.
3. `a42c` -ee←A2; A3=LONG (A2); A3=LONG 6(A3)(descriptor 프레임 hook, `c188`은 `bf2c`); CMPA.W #0이면 `a444`, 아니면 `a43e` A2 push, JSR (A3)(복귀 `a442`), pop.
4. `bf2c` D0.W=7e(A6); 0이면 `bf48`; 아니면 SUBQ.W #1, 7e(A6)←D0, 결과≠0이면 `bf48`, 0이면 `bf3e` D0.W=3, JSR `9ff4`(복귀 `bf48`): A2=-ee, BYTE D0→e(A2), RTS. `bf48` TST.B 80(A6)≠0이면 `bf50` JSR `a70a`(복귀 `bf56`), `bf56` MOVEQ 0,D0, BRA `bf8e`. 아니면 `bf5c` MOVEQ 0,D0; BYTE `10fdb6`이 1 또는 3이면 D0|=1; BYTE `10fdb7`이 1 또는 3이면 D0|=2; `bf8e` JMP `9fc4`: A2=-ee, BYTE D0→d(A2), RTS(→`a442`).
5. `a444` -ee←A2; 8(A2)←7(A2); `a44e` 루프: e(A2)==ff면 `a472`; 아니면 A2 push, D0=0, D0.B=e(A2), e(A2)←ff, BSR `9b3e`(복귀 `a46a`), pop, -ee←A2, 반복. 대기 사건을 현재 커서 항목 callback에 D0로 전달한다.
6. `a472` D0=0, D1=0, BYTE D1(0)→-e6(A5); d(A2) bit0이면 D0.B=BYTE -3346(A5)=`104cba`, bit1이면 D1.B=BYTE -3340(A5)=`104cc0`. 이후 순서대로 bit 0,1,2,3,5,4에 대해 D6=SNE(D0 bit)&1, D7=SNE(D1 bit)&2, D7|=D6(OR.B, Z는 결과 BYTE); 0이 아니면 -e6(A5)←D7.B 후 각각 `a566`(bit0: BSET #1,f, BSR `a216` 역방향), `a574`(bit1: BCLR #1,f, BSR `a216` 정방향), `a596`(bit2: e←1), `a5a0`(bit3: e←2), `a58c`(bit5: e←4), `a582`(bit4: e←3). 모두 0이면 `a562` BRA `a5ce`.
7. `a5aa` e(A2)==ff까지 `a44e`와 같은 사건 전달 루프(`a5b4`..`a5cc`), `a5ce` MOVEQ 0,D0 RTS(→`c2c0`).
8. `c1c4`(YES)·`bf94`(NO)는 열림 단위 실행부: 사건 3이면 YES→`bd26`(BIOS 카드, 경계), NO→80(A6)=ff, JMP `a70a`. 사건 0이면 `a73e`가 효과음 `1a6c`.
9. `a70a` D0.W=`1a5b`, JSR `3af8`(복귀 `a714`), JMP `a1ee`: BYTE 2→-e5, A2=-f2, RTS. 다음 프레임은 `a3e2`에서 -e5=2→`a662`(닫기, 경계).

## 구현 범위와 규약

- 새 실행부 파일 `engine/src/animation_machine_card_menu_input.cpp`(함수 `animation_card_menu_input_block`). 범위는 위 표.
- Block 시작 PC: `9fc4` `9ff4` `a1ee` `a406` `a412` `a416` `a41a` `a424` `a42a` `a42c` `a43e` `a442` `a444` `a44e` `a458` `a46a` `a472` `a484` `a488` `a492` `a496` `a4b0` `a4b8` `a4d2` `a4da` `a4f4` `a4fc` `a516` `a51e` `a538` `a540` `a55a` `a562` `a566` `a570` `a574` `a57e` `a582` `a58c` `a596` `a5a0` `a5aa` `a5b4` `a5c6` `a5ce` `a70a` `a714` `bf2c` `bf34` `bf3e` `bf48` `bf50` `bf56` `bf5c` `bf6a` `bf72` `bf76` `bf82` `bf8a` `bf8e`(60개). 그 밖 내부 PC 직접 진입 거부(`unsupported animation card menu input PC`).
- 묶음: Z/C 생산자와 조건분기는 같은 block(`a41a` BCLR+BEQ, `a4aa` OR.B+BEQ 등). SNE는 BTST의 Z를 같은 block에서 소비한다.
- 경계(실행부 없음): `bd26`, `a662`, 그리고 hook가 `bf2c`가 아닌 descriptor의 hook 대상. stop을 그 PC로 주면 그 직전 상태로 멈추고, 다른 stop이면 `unsupported animation machine PC`와 전체 rollback.
- Carry: 전체가 FLOW_ONLY인 block만 보존(구현자가 원본 opcode로 계산해 보고). 그 밖 Unknown.
- 입력·카드 상태는 선언 fixture다: 프레임마다 `104cba`/`104cc0`(게임 입력 edge BYTE), `10fdb6`/`10fdb7`(BIOS 영역 BYTE) RAM write를 선언 host 변경으로 기록한다. 원래 입력 처리 루틴·BIOS가 그 값을 만든다고 주장하지 않는다.
- 프레임 재진입은 선언 PC=`2ab8` 변경뿐이다(자연 scheduler 아님).

## 검증 조건(최소)

- 연결: 열림 단위 C++ 마지막 출력(`2ac2`, 7e=`012c`, 커서 3, e=0)에서 재진입: 첫 입력 프레임(사건 0 전달→NO callback→효과음), 입력 없는 프레임 체인으로 7e 감소, 7e 1→0 프레임에서 e=3 → 같은 프레임 `a44e` 루프가 NO(`bf94`) 사건 3→80=ff→`a70a`→`3af8 1a5b`→`a1ee` -e5=2, 다음 재진입에서 `a662` stop. 대표 프레임 fresh split/continuous, 전체 300 프레임 내외 체인은 직전 실제 C++ 출력 재개.
- 입력 fixture: d(A2) bit 조합(`10fdb6`/`10fdb7` 0/1/2/3), 위/아래 커서 이동(정·역, wrap, 구분자 skip), 좌/우/bit5 사건 1/2/4, 커서 YES에서 선택(사건 3)→`bd26` stop, 동시 입력의 우선순위(bit0 먼저), P1/P2 합성 -e6 값(1/2/3).
- 경계: 7e=0 진입(감소 없음), 7e=1, 80(A6)≠0이면 hook에서 `a70a`, f bit0 설정 시 `a424` 재그리기, hook 0인 descriptor, 4<c(재성장 `a412`), 홀수 A2/A3 오류 rollback, 내부 PC 거부.
- 비교 항목은 기존과 같다. 기존 회귀의 `a406` unsupported 경계는 `a662` 등 아직 실행부 없는 PC로 옮긴다.

## 미확인·범위 밖

`a662` 닫기 애니메이션 이후, `bd26` BIOS 카드 저장, 원래 입력 루틴과 `10fdb6`/`10fdb7`의 실제 BIOS 의미, video port의 화면 의미, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
