# 카드 메뉴 닫기(`a662`/`a2be`/`9e94`)와 카드 자식·부모 종료(`c2c8`→`2a00`) 계약

Baseline: 카드 메뉴 입력 단위(리뷰0236) 통합 커밋. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 범위·경로를 확정했다. 명령 단위 정답은 원본 바이트이며 아래 요약은 폭·부호·경로 근거다. 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `a662..a70a` | `2b4aff121e2a00040c0700006300000a6100fc4a70004e754ebaf81806ad00000010ff0e246dff0eb5fc00107f0e6500000670ff4e751b7c0000ff1b2b4aff12156a00070008303c00072f0a4ebaf48e245fb5edff0e660000142b4aff12156a00070008303c00004ebaf472246dff126100000670004e752f0a247c00107f0e94fc001043faf920b5d7650000182b4aff126100f4626100f720246dff1294fc001060e4245f4e75` |
| `a2be..a348` | `7000102a0006ed48322a0004924064000008d041323c000035410004024100ffd240e0493f0143fafd226100f86e303c00ff48404240102a0009eb48d02a000a06407000d02a00040c570000670000383f00246dff121e2a000b0c0700006700001e4ebafcf66500000c484023c0003c00004840068000000020530760dc301f5240535760c2544f4e75` |
| `9e94..9ee6` | `247900107f127000102a0009eb48d02a000a0640700036001e2a00040c0700006700002e4840303c00ff1c2a000b0c0600006700001223c0003c0000068000200000530660e8484052433003530760cc4e75` |
| `c2c8..c2fa` | `70e172e174e176144eb900008c163d43007e2cbc0000c2e0536e007e66000012206e000c117c00ff00624ef900002a004e75` |

## 실행 경로(사실)

진입: 입력 단위 끝에서 `a1ee`가 -e5=2를 둔 뒤 다음 자식 재진입(선언 PC=`2ab8`)→`c2ba` JSR `a370`→`a3e2` -e5=2→`a662`.

1. `a662` -ee←A2(-f2 프레임); D7.B=4(A2); CMPI.B #0,D7, BLS `a67a`(D7=0). 아니면 `a672` BSR `a2be`, `a676` MOVEQ 0,D0 RTS(→`c2c0`, D0=0이므로 `c2c6` RTS).
2. `a2be` 축소: D0=0, D0.B=6(A2)(항목 수), LSL.W #6; D1.W=WORD 4(A2)(바이트 5 포함); SUB.W D0,D1, BCC `a2d6`; borrow면 `a2d0` ADD.W D1,D0, D1.W=0. `a2d6` WORD 4(A2)←D1; ANDI.W #ff,D1; ADD.W D0,D1; LSR.W #8,D1; D1.W push(지울 행 수); LEA `a008`,A1; BSR `9b58`(새 높이로 상자 다시 그리기, 열림 단위 실행부). `a2ec` D0.W=ff, SWAP, CLR.W, D0.B=9(A2), LSL.W #5, ADD.B a(A2), ADDI.W #7000, ADD.B 4(A2)(BYTE). `a306` 루프: CMPI.W #0,(A7) BEQ `a344`; D0.W push; A2=-ee; D7.B=b(A2); `a318` CMPI.B #0,D7 BEQ `a33c`; `a320` JSR `a018`(복귀 `a324`), `a324` BCS `a332`(known C 소비); `a328` SWAP, LONG D0→`3c0000`, SWAP; `a332` ADDI.L #20,D0(32bit); SUBQ.B #1,D7; BRA `a318`. `a33c` D0.W pop, ADDQ.W #1, SUBQ.W #1,(A7), BRA `a306`. `a344` ADDQ.W #2,A7, RTS.
3. `a67a` JSR `9e94`(복귀 `a67e`): A2=LONG `107f12`; 위치 D3; D7.B=4(A2) 행마다 b(A2) 칸에 LONG (위치<<16)|`00ff` 쓰기(`ADDI.L #200000`으로 상위 WORD 위치 +20), 행마다 D3+1. 4(A2)=0이면 바로 RTS. `a67e` ADDI.L #10,-f2(A5)(LONG RMW); A2=-f2; A2≥`107f0e`(unsigned)면 `a694` MOVEQ -1,D0 RTS(→`c2c0` D0.B≠0→`c2c8`). 아니면 `a698` 중첩 복귀 경로(-e5=0, 9b3e D0=7, a6da 재그리기)이며 이번 자연 경로에서는 경계로 둔다.
4. `c2c8` MOVEQ e1→D0/D1/D2, MOVEQ 14→D3, JSR `8c16`(기존 페이드, 복귀 `c2d6`); `c2d6` WORD D3→7e(A6); LONG `c2e0`→(A6); `c2e0` SUBQ.W #1,7e(A6), BNE `c2f8` RTS(Z 소비, 같은 block). 0이면 `c2e8` A0=LONG c(A6)(부모), BYTE ff→62(A0), JMP `2a00`(기존: `299c` cleanup, A7←`104ca4`, BRA `2ac2`).
5. 부모 `480ac` 프레임(기존 실행부): 62≠0이면 `480b6` JMP `2a00`.

## 구현 범위와 규약

- 새 실행부 파일 `engine/src/animation_machine_card_menu_close.cpp`(함수 `animation_card_menu_close_block`). 범위: `a662..a6d8`(단 `a698` 이후 중첩 경로는 경계), `a2be..a346`, `9e94..9ee4`, `c2c8..c2f8`. 기존 `9b58`/`a018`/`a008`(열림 단위), `8c16`, `2a00`/`299c`, 디스패처를 호출 경로로 쓴다.
- Block 시작 PC: `9e94` `9eb0` `9eb8` `9ec2` `9eca` `9eda` `9ee4` `a2be` `a2d0` `a2d6` `a2ec` `a306` `a30e` `a318` `a320` `a324` `a328` `a332` `a33c` `a344` `a662` `a672` `a676` `a67a` `a67e` `a694` `c2c8` `c2d6` `c2e0` `c2e8` `c2f8`. `a324`는 `a018` 복귀 BCS로 modeled carry를 소비하며 Unknown이면 `card menu caller requires known carry`. 그 밖 내부 PC 직접 진입 거부(`unsupported animation card menu close PC`).
- 경계(실행부 없음): `a698`(중첩 메뉴 복귀). stop을 그 PC로 주면 멈추고, 다른 stop이면 `unsupported animation machine PC`와 전체 rollback.
- Carry: FLOW_ONLY-only block만 보존(구현자가 원본 opcode로 계산해 보고), `a324`는 소비. 그 밖 Unknown.
- WORD 4(A2) RMW·ADDI.L 메모리 RMW·ADDI.L D0 32bit·LSR.W·BYTE ADD를 명시 구현한다. video port 기록은 기존 규약.
- 프레임 재진입은 선언 PC=`2ab8` 변경뿐이다. 부모·자식 순서: 자식 `2a00` 뒤 `2ac2`에서 stop하고, 부모 프레임은 기존 fade_card 검증과 같은 선언 재진입(A6=부모)으로 실행한다.

## 검증 조건(최소)

- 연결: 입력 단위 C++ 마지막 출력(-e5=2)에서 재진입: 닫기 프레임(높이 `0600`→`0480`→`0300`→`0180`→`0000`, 각 프레임 상자 재그리기와 행 지우기 포트 순서), 높이 0 프레임(`9e94`, -f2←`107f0e`, D0=ff, `c2c8` 페이드, 7e=14), 7e 타이머 프레임들, 0 도달 프레임(부모 62=ff, `2a00` 자식 제거→`2ac2`), 부모 `480ac` 프레임에서 `2a00` 부모 제거→`2ac2` stop.
- 경계: 6(A2)·바이트 5 변경에 따른 borrow 경로(`a2d0`), b=0(빈 행 루프), 가린 칸(a018 C=1, 상위 프레임 fixture), 중첩 stack(-f2+10<`107f0e`→`a698` stop), 7e=1/0 진입, 부모 포인터 c(A6) 변경·홀수, 홀수 A2 오류 rollback, 내부 PC 거부, Unknown carry로 `a324` 진입 오류.
- 비교 항목은 기존과 같다. 기존 회귀의 `a662`/`c2c8` unsupported 경계는 아직 실행부 없는 PC(`a698` 등)로 옮긴다.

## 미확인·범위 밖

`a698` 중첩 메뉴 복귀·`a6da`, `bd26` BIOS 카드 저장 경로(YES 선택), 부모·자식 제거 뒤 다음 객체·장면, video port 화면 의미, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
