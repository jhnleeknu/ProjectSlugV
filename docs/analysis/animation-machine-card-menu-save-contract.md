# 카드 메뉴 YES 선택: 카드 저장 `bd26`(BIOS 경계 3회)과 결과 하위 메뉴 push 계약

Baseline: 카드 메뉴 닫기 단위(리뷰0237) 통합 커밋. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 범위·경로를 확정했다. 명령 단위 정답은 원본 바이트다. 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `bd26..bd96` | `41edff1c43fafe627e146100fe863e3c00166100fe3a3b40ff322f0e13fc00040010fdc433fc02680010fdce13fc00000010fdd04eb900c0046813fc00030010fdc433fc02680010fdce13fc00000010fdd023fc00107f1c0010fdc833fc00180010fdcc4eb900c004682c5f60000078` |
| `bbb8..bbd4` | `2f0853476500001210d966f653476500000810fc000060f4205f4e75` |
| `bb74..bb8e` | `700012184881d041d04064000004464006403c5b534766ea4e75` |
| `be0c..be3a` | `2f0e13fc00000010fdc24eb900c0046e2c5f4bf9001080004a390010fdc666000008003c00014e75023c00fe4e75` |
| `9f36..9f78` | `246dff122652302b000e0240000e66000008700260000004700072007400d02a0009122a000a52005201142a0008d202205241e800103e02cefc000a207070004e75` |
| `a71a..a72c` | `4eb90000a0a0303c1adb4eb900003af84e75` |
| `a0f8..a104` | `2b4aff126100fa5a6100fd18` |
| `c1e6..c214` | `6100fb3e640000164eb900009f3641fa001e4eb90000a71a600000124eb900009f3641fa00284eb90000a71a4e75` |
| `bb8e..bba3` (데이터) | `4d4554414c20534c55472056332020202020202000` |
| `be84..be9a` (데이터) | `53415645204f4b2e2020004e4f20534156452e202000` |
| `c214..c250` (데이터) | `0000000000000000bf2c0000000000000000be840000bf940000ffffffff0000000000000000bf2c0000000000000000be8f0000bf940000ffffffff` |

데이터: `bb8e` "METAL SLUG V3       "(20자)+NUL. `be84` "SAVE OK.  ", `be8f` "NO SAVE.  ". `c214`/`c232` 결과 descriptor: 제목 0, +6 hook `bf2c`, 항목 1개 `{be84 또는 be8f, callback bf94, 0}`, 종료 `ffffffff`.

## 실행 경로(사실)

진입: 입력 단위 경로에서 커서가 YES(7=2)인 상태로 사건 3이 전달되면 `9b3e`→`c1c4`→`a73e`(D0≠0이라 효과음 없음)→`c1de` D0.W==3→`c1e6` BSR `bd26`(복귀 `c1ea`). 입력은 선언 fixture(위 입력 bit0로 커서 이동 후 bit4 선택)다.

1. `bd26` LEA -e4(A5),A0(=`107f1c`, live A5), LEA `bb8e`,A1, MOVEQ 14,D7, BSR `bbb8`(복귀 `bd34`). `bbb8` A0 push; 루프: SUBQ.W #1,D7, BCS 끝; MOVE.B (A1)+,(A0)+(Z는 옮긴 BYTE), BNE 반복; 이후 SUBQ.W/BCS 동안 BYTE 0 채우기; `bbd0` A0 pop, RTS. 20자 문자열은 D7 20회 복사 뒤 borrow로 끝난다(NUL 미복사).
2. `bd34` D7.W=16, BSR `bb74`(복귀 `bd3c`): D0=0(32bit); 루프 D7.W회: D1.B=(A0)+, EXT.W D1, ADD.W D1,D0, ADD.W D0,D0(C=WORD carry), carry 없으면 건너뛰고 있으면 NOT.W D0, ADDI.W #3c5b, SUBQ.W #1,D7, BNE. 대상은 `107f1c..107f31`(22바이트, 마지막 2바이트는 실행 시점 RAM 값).
3. `bd3c` WORD D0→-ce(A5)(`107f32`); A6 push; BYTE 4→`10fdc4`, WORD `0268`→`10fdce`, BYTE 0→`10fdd0`; JSR `c00468`(복귀 `bd60`) — BIOS 경계 1. `bd60` BYTE 3→`10fdc4`, WORD `0268`→`10fdce`, BYTE 0→`10fdd0`, LONG `107f1c`→`10fdc8`, WORD `0018`→`10fdcc`; JSR `c00468`(복귀 `bd90`) — BIOS 경계 2. `bd90` A6 pop; BRA `be0c`.
4. `be0c` A6 push; BYTE 0→`10fdc2`; JSR `c0046e`(복귀 `be1c`) — BIOS 경계 3. `be1c` A6 pop; LEA `108000`,A5; TST.B `10fdc6`; 0이면 `be2e` ORI CCR #1(known Set) RTS, 아니면 `be34` ANDI CCR #fe(known Clear) RTS(→`c1ea`).
5. `c1ea` BCC `c202`(known C 소비; Unknown이면 `card menu caller requires known carry`). Set이면 `c1ee` JSR `9f36`, A0=`c214`("SAVE OK."), JSR `a71a`, BRA `c212`; Clear면 `c202` JSR `9f36`, A0=`c232`("NO SAVE."), JSR `a71a`; `c212` RTS(→`9b3e` 호출자).
6. `9f36` A2=-ee; A3=(A2); D0.W=e(A3) AND e; 0이면 D0=2 아니면 0; D1=0, D2=0; ADD.B 9(A2),D0; D1.B=a(A2); ADDQ.B #1,D0; ADDQ.B #1,D1; D2.B=8(A2); ADD.B D2,D1; A0=(A2)+10; D7.W=D2; MULU.W #a,D7; A0=LONG (A0+D7.W 부호확장); RTS. 하위 메뉴 행·열(D0/D1)을 계산한다(A0은 호출자가 덮어씀).
7. `a71a` JSR `a0a0`(push 단위 실행부, 복귀 `a720`); `a720` D0.W=`1adb`, JSR `3af8`(복귀 `a72a`), RTS. 기존 메뉴(`107efe`)가 있으므로 `a0a0`은 새 프레임 `107eee`를 만들고 `a0c4` 뒤 `a0f8` -ee←`107efe`, BSR `9b58`(열림 단위 실행부, 복귀 `a100`); **`a100` BSR `9e1a`(복귀 `a104`)**; 이후 기존 `a104`.. 경로로 새 프레임을 채운다.

## 구현 범위와 규약

- 새 실행부 파일 `engine/src/animation_machine_card_menu_save.cpp`(함수 `animation_card_menu_save_block`): `bd26..bd92`, `bbb8..bbd2`, `bb74..bb8c`, `be0c..be38`, `9f36..9f76`, `a71a..a72a`.
- 기존 파일 보정: push 실행부(`animation_machine_card_menu.cpp`)에 `a100` case(BSR `9e1a`, 복귀 `a104`)를, 열림 실행부(`animation_machine_card_menu_open.cpp`)에 `c1ea` case(known C 소비)를 추가한다.
- Block 시작 PC: `9f36` `9f48` `9f4e` `9f50` `a100` `a71a` `a720` `a72a` `bb74` `bb76` `bb82` `bb84` `bb8c` `bbb8` `bbba` `bbc0` `bbc4` `bbca` `bbd0` `bd26` `bd34` `bd3c` `bd60` `bd90` `be0c` `be1c` `be2e` `be34` `c1ea`. 그 밖 내부 PC 직접 진입 거부(`unsupported animation card menu save PC`).
- 묶음: SUBQ.W+BCS(`bbba`,`bbc4`), MOVE.B+BNE(`bbc0`), ADD.W+BCC(`bb7c`), SUBQ.W+BNE(`bb88`), TST.B+BNE(`be24`), ANDI.W+BNE(`9f40`). `bbc0`의 Z는 옮긴 BYTE 값이다.
- BIOS 경계: `c00468`(두 번), `c0046e`는 실행하지 않는다. stop을 그 PC로 주면 JSR이 남긴 복귀(`bd60`/`bd90`/`be1c`)와 push된 A6가 stack에 있는 상태로 멈추고, 다른 stop이면 `unsupported animation machine PC`와 전체 rollback. BIOS 뒤 재개는 선언된 host 변경(PC=복귀, A7+=4, 필요하면 `10fdc6` BYTE)이며 carry Unknown이다. 카드 쓰기·BIOS 레지스터 효과는 미모델·미확인으로 기록한다.
- Carry: `be2e` known Set, `be34` known Clear(ORI/ANDI가 RTS와 같은 block). `c1ea`는 소비. FLOW_ONLY-only block만 보존(구현자가 원본 opcode로 계산해 보고). 그 밖 Unknown.
- 모든 읽기·쓰기는 live bus, 원본 순서·크기. EXT.W, ADD.W carry, NOT.W, MULU.W, MOVEA.L (A0,D7.W) 부호확장 인덱스를 명시 구현한다.

## 검증 조건(최소)

- 연결: 입력 단위 C++ 출력(열림 직후 첫 입력 프레임)에서 선언 입력으로 커서를 YES로 옮기고 다음 프레임에 선택(bit4)→`bd26`→BIOS 경계 1 stop→선언 재개→BIOS 경계 2 stop→선언 재개→`c0046e` stop→선언 재개(`10fdc6`=0과 ≠0 두 갈래)→`c1ea`→`9f36`→`a71a`→`a0a0` 중첩 push(`9b58`,`9e1a` 이전 메뉴 다시 그리기, 새 프레임 `107eee`)→`3af8 1adb`→`c212`→`a5c6`..→`2ac2` stop.
- 경계: `bbb8` D7=0/짧은 문자열(NUL 뒤 0 채움), `bb74`의 carry/NOT 경로를 바꾸는 RAM 바이트, `107f30/31` 값, 직접 진입 `be0c`의 `10fdc6` 0/1/80, Unknown carry로 `c1ea` 진입 오류, 중첩 stack 한계(-f2 근처), BIOS 이외 stop rollback, 홀수 A0/A2 오류 rollback, 내부 PC 거부.
- 비교 항목은 기존과 같다. 기존 회귀의 `bd26` unsupported 경계는 `c0046e`/`c00468` 등 실행부 없는 PC로 옮긴다.

## 미확인·범위 밖

BIOS `c00468`(명령 4/3)·`c0046e` 내부와 카드 기록 결과, `10fdc4`..`10fdd0`의 BIOS 의미, 하위 메뉴의 이후 프레임(열림·입력·`a698` 중첩 복귀·`a6da`), video port 화면 의미, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
