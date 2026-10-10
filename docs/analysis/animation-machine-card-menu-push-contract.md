# 카드 자식의 메뉴 push(`a29c`→`a0a0`→`38e8`/`386e`)와 renderer 설정(`c2a8`→`a2b8`) 계약

Baseline `bfbfe60`, branch `codex/animation-machine-card-menu-push`. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 확정했다. 구현·원본 동등성 완료 보고가 아니다. 기존 host API(`init_menu`, `menu_stack`, `menu_frame`)는 바꾸지 않으며 이번 실행부는 live RAM/A7 stack 위의 animation machine 경로다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `a29c..a2be` | `2b7c00003650ff161b7c0000ff1a23fc00107f0e00107f0e6000fdea2b48ff164e75` |
| `a0a0..a1e2` | `2f2dff124bf900108000246dff0e2b4aff1295fc00000010b5fc00107e0e640000044e752b4aff0e48e7c080157c00ff0009157c00ff000a157c0000000b157c0000000c43faff22d5fc00000010b5fc00107f0e6400000e2b4aff126100fa5a6100fd184cdf0103246dff0e2b4aff122488154000091541000a157c00000007157c00000008157c0000000f157c0003000d157c00ff000e15680004000b15680005000c157c00000006264870002053b0fc0000670000084eb9000038e83f00d6fc00102053b0fcffff6700002cb0fc000067000018b0fcfffe670000104eb9000038e8b057630000043e80522a0006d6fc000a205360ce2652302b000e0240000e6600000870026000000470005440d05fb02a000b630000061540000b102a00065440b02a000c630000061540000c157c000000041b7c0001ff1b2b5fff124e75` |
| `386e..38e8` | `14180c02005c670000044e7514180c02006e6700003c0c020072670000400c020063670000240c0200706700000c0c02006c6700002c4e75024100ff1e180207000fe14f824760b80241ff00121860b052430c437500650000044e4f300360a076001618eb4bd618064370000c437500650000044e4f30036086` |
| `38e8..3902` | `3f3c000061804a026700000c52576100ff764a0260f2301f4e75` |
| `c2a8..c2c8` | `41f9000e84c84eb90000a2b82cbc0000c2ba4eb90000a3704a00660000044e75` |
| `c188..c1c4` (데이터) | `0000000000000000bf2c0000000000000000be60000000000000fffffffe0000000000000000be9a0000c1c400000000bea00000bf940000ffffffff` |

`c188` 해석(사실, 실행 경로가 읽는 부분만): `+0` LONG 제목 포인터 0, `+4`/`+5` BYTE 최소 폭/높이 0/0, `+e` WORD 0(플래그), `+10`부터 10바이트 항목 `{LONG 문자열, LONG callback, WORD}`: `be60`("DATA SAVE ?  ", callback 0), `fffffffe`(구분자), `be9a`(" YES ", callback `c1c4`), `bea0`(" NO ", callback `bf94`), 종료 `ffffffff`. 문자열에는 `\`(5c) escape가 없다.

## 실행 의미(사실)

1. 진입: 카드 자식 `c2a2` JSR `a29c` 복귀 `c2a8`(리뷰0233에서 stop 경계였던 지점). 이 시점 A0=`c188`(LONG 76(A6)), D0.W=4, D1.W=4, A5=live(디스패처가 `108000`으로 둔 값).
2. `a29c` LONG `3650`→-ea(A5), BYTE 0→-e6(A5), LONG `107f0e`→`107f0e`(절대), BRA `a0a0`. A5는 live 값을 쓴다.
3. `a0a0` MOVE.L -ee(A5),-(A7)(**이전 A5 기준**, live push) 다음 LEA `108000`,A5. 이하 -xx(A5)는 `107f..`. A2=LONG -f2(`107f0e`); -ee←A2; SUBA.L #10,A2; CMPA.L #`107e0e`,A2; BCC `a0c4`(unsigned A2≥`107e0e`). 아니면 `a0c2` RTS가 앞서 push한 LONG(이전 -ee 값)을 PC로 pop한다(원본 그대로, 보정하지 않음).
4. `a0c4` -f2←A2; MOVEM.L D0-D1/A0,-(A7)(12바이트 live push); BYTE ff→9(A2), ff→a(A2), 0→b(A2), 0→c(A2); LEA `a008`,A1; ADDA.L #10,A2; CMPA.L #`107f0e`,A2; BCC `a104`. 아니면(중첩 메뉴) `a0f8` -ee←A2, BSR `9b58`(복귀 `a100`), 이후 BSR `9e1a`. `9b58`/`9e1a`는 이번 범위 밖 경계다. `a29c` 경유에서는 -f2가 `107f0e`로 초기화되므로 항상 `a104`로 간다.
5. `a104` MOVEM.L (A7)+,D0-D1/A0; A2=-f2; -ee←A2; LONG A0→(A2); BYTE D0→9(A2), D1→a(A2); 0→7(A2), 0→8(A2), 0→f(A2), 3→d(A2), ff→e(A2); BYTE 4(A0)→b(A2), 5(A0)→c(A2); 0→6(A2); A3=A0; MOVEQ 0,D0; A0=LONG (A3); CMPA.W #0,A0(부호확장 32bit 비교)가 0이면 `a15e`, 아니면 `a158` JSR `38e8` 복귀 `a15e`.
6. `a15e` MOVE.W D0,-(A7)(최대 폭 WORD); ADDA.W #10,A3; A0=LONG (A3). `a166` 루프: A0==`ffffffff`(CMPA.W #ffff)면 `a198`; A0==0 또는 `fffffffe`면 `a18c`; 아니면 `a17e` JSR `38e8` 복귀 `a184`; `a184` CMP.W (A7),D0, BLS `a18c`(unsigned D0.W≤(A7)이면 유지), 아니면 `a18a` (A7)←D0.W. `a18c` ADDQ.B #1,6(A2); ADDA.W #a,A3; A0=LONG (A3); BRA `a166`. 구분자·null 항목도 6(A2)를 센다.
7. `a198` A3=LONG (A2); D0.W=WORD e(A3) AND e; 0이면 `a1a6` MOVEQ 2,D0 → `a1ae`, 아니면 `a1ac` MOVEQ 0,D0. `a1ae` ADDQ.W #2,D0; ADD.W (A7)+,D0; CMP.B b(A2),D0, BLS `a1be`(unsigned BYTE D0≤b), 아니면 `a1ba` b(A2)←D0.B. `a1be` MOVE.B 6(A2),D0(하위 BYTE만 교체), ADDQ.W #2,D0, CMP.B c(A2),D0, BLS `a1d0`, 아니면 `a1cc` c(A2)←D0.B. `a1d0` BYTE 0→4(A2), BYTE 1→-e5(A5)=`107f1b`, MOVE.L (A7)+,-ee(A5)(3에서 push한 이전 -ee 복원), RTS(→`c2a8`).
8. `38e8` WORD 0 push; BSR `386e` 복귀 `38ee`; `38ee` TST.B D2, BEQ `38fe`; `38f4` ADDQ.W #1,(A7), BSR `386e` 복귀 `38fa`; `38fa` TST.B D2, BRA `38f0`(=BEQ `38fe` 재검사); `38fe` MOVE.W (A7)+,D0, RTS. 즉 escape를 제외한 문자 수를 D0.W로 반환한다(D0 상위 WORD 보존).
9. `386e` MOVE.B (A0)+,D2; `5c`가 아니면 `3878` RTS. `387a` 다음 BYTE: `6e`(`n`)→`38be` ADDQ.W #1,D3, CMPI.W #7500,D3, BCS `38ca`, 아니면 `38c8` TRAP #f; `72`(`r`)→`38ca` D0.W←D3, BRA `386e`; `63`(`c`)→`38b6` D1.W&=ff00, D1.B←다음 BYTE, BRA `386e`; `70`(`p`)→`38a6` D1.W&=ff, D7.B←다음 BYTE AND f, D7.W<<=8(결과 D7.W=nibble<<8, D7 bit16-31 보존), D1.W|=D7.W, BRA `386e`; `6c`(`l`)→`38ce` D3=0(32bit), D3.B←다음 BYTE, D3.W<<=5, D3.B+=다음 BYTE(BYTE 덧셈), D3.W+=7000, CMPI.W #7500,D3, BCS `38e4` D0.W←D3, BRA `386e`, 아니면 `38e2` TRAP #f; 그 밖이면 `38a4` RTS(D2=그 BYTE, 0이 아니면 문자로 셈). 모든 문자열 BYTE는 실제 접근 시점의 live bus(fixed ROM, RAM, 현재 bank)로 읽는다.
10. `c2a8` LEA `e84c8`,A0; JSR `a2b8` 복귀 `c2b4`; `a2b8` LONG A0→-ea(A5)(live A5, `a0a0` 뒤 `108000`), `a2bc` RTS; `c2b4` LONG `c2ba`→(A6); `c2ba` JSR `a370` 복귀 `c2c0`. `a370` 메뉴 프레임은 이번 범위 밖이며 stop 경계다.

## 구현 범위와 규약

- 새 실행부 파일 `engine/src/animation_machine_card_menu.cpp`(함수 `animation_card_menu_block`): `a29c`, `a0a0..a1e0`, `386e..38e4`, `38e8..38fe`, `a2b8`/`a2bc`, `c2a8`/`c2b4`/`c2ba`. 기존 실행부(디스패처, card child 등)를 가리지 않는다. 기존 AnimationMachineContext/am_* helper만 쓴다.
- Block 시작 PC(native split checkpoint로 노출, 이 목록 밖의 내부 PC 직접 진입은 거부):
  `a29c`, `a0a0`, `a0c2`, `a0c4`, `a0f8`, `a104`, `a158`, `a15e`, `a166`, `a17e`, `a184`, `a18a`, `a18c`, `a198`, `a1a6`, `a1ac`, `a1ae`, `a1ba`, `a1be`, `a1cc`, `a1d0`, `386e`, `3878`, `387a`, `38a4`, `38a6`, `38b6`, `38be`, `38ca`, `38ce`, `38e4`, `38e8`, `38ee`, `38f4`, `38fa`, `38fe`, `c2a8`, `a2b8`, `a2bc`, `c2b4`, `c2ba`.
- 묶음(Z/N/C 생산자와 소비 분기를 한 block): `a0b8`+`a0be`, `a0ee`+`a0f4`, `a150`+`a154`, `a166..a17a`의 세 CMPA/BEQ, `a184`+`a186`, `a19e`+`a1a2`, `a1b2`+`a1b6`, `a1c4`+`a1c8`, `386e`의 CMPI/BEQ, `387a`의 다섯 CMPI/BEQ, `38c0`+`38c4`, `38da`+`38de`, `38ee`+`38f0`, `38fa`+`38fc`→`38f0`. 묶인 분기 PC(`a0be`,`a0f4`,`a154`,`a16a`,`a172`,`a17a`,`a186`,`a1a2`,`a1b6`,`a1c8`,`3874`,`3880`,`38c4`,`38de`,`38f0`,`38fc`) 직접 진입은 거부한다.
- 경계(실행부 없음): `9b58`(중첩 push), `38c8`/`38e2`(TRAP #f), `a370`. stop을 그 PC로 주면 그 직전 상태(JSR/BSR이면 return이 stack에 남은 상태)로 멈추고, 다른 stop이면 checked 오류 `unsupported animation machine PC`와 전체 rollback이다.
- Carry: 전체가 FLOW_ONLY(LEA/MOVEA/PEA/JSR/JMP/BSR/BRA/RTS/MOVEM/조건분기/BTST류)인 block만 C를 보존한다: `a0c2`, `a158`, `a17e`, `3878`, `38a4`, `c2a8`, `a2bc`, `c2ba`. ADDA/SUBA는 실제 68000에서 CCR을 바꾸지 않지만 기존 검증기 source 분류(FLOW_ONLY에 없음)와 일치시키기 위해 보수적으로 Unknown으로 둔다. 나머지 block은 Unknown. 원본 opcode 분류이며 native C 측정이 아니다.
- 모든 descriptor·문자열·스택 읽기는 실제 접근 시점의 live bus로 하고 미리 decode하지 않는다. 바이트/워드 폭, unsigned 비교(BCC/BLS), CMPA.W 부호확장, MOVE.B의 하위 BYTE만 교체를 명시적으로 구현한다.
- 프레임 연결: 이번 실행은 카드 자식 `c290` 프레임 안에서 이어지므로 host 변경 없이 `a29c` stop 출력에서 `a370` stop까지 진행한다. `a370` 이후 프레임은 범위 밖이다.
- 리소스 형식(MS5D v1 kind3)·loader/bus·기존 host 메뉴 API는 바꾸지 않는다. ROM·추출물은 수정하거나 Git에 추가하지 않는다.

## 검증 조건(최소)

- 연결: card_child 관측의 `a29c` stop 출력(A7에 `c2a8` 위 `2ac2`)에서 host 변경 없이 `a370` stop까지. split checkpoint 전부와 continuous.
- 경계(선언된 초기 변경은 레지스터 또는 RAM fixture로 기록):
  - RAM descriptor(A0 변경): 제목 문자열 있음, `e`에 비트(AND e≠0 → D0=0), 4/5가 계산값보다 큼/작음, BYTE wrap(폭 합이 ff 초과), null 항목(0)과 구분자, 항목 0개.
  - RAM 문자열의 escape `\n`,`\r`,`\c`,`\p`,`\l`, 알 수 없는 escape(`\x`), D3=74ff에서 `\n`→`38c8` TRAP 경계, `\l`이 7500 이상→`38e2`.
  - 문자열·descriptor를 banked 영역(`200000+`)에 두는 현재 bank 읽기 1건 이상.
  - 진입 A5≠`108000`(a29c의 -ea/-e6 쓰기와 a0a0의 -ee 읽기가 이전 A5 기준), A5가 ROM 영역이면 write device 오류 rollback.
  - `a0a0` 직접 진입 overflow(-f2=`107e14` 등): `a0c2` RTS가 push된 이전 -ee를 PC로 pop(값을 `a370`으로 두면 stop `a370` 성공), 중첩(-f2=`107efe`)→`9b58` stop.
  - 홀수 descriptor/A2/A7 오류 rollback, 묶인 분기 PC와 내부 PC 직접 진입 거부, `a370`/`9b58`/`38c8` 이외 stop rollback.
- 비교 항목은 기존과 같다(full 64KiB RAM/16R/PC/A7/carry 분류/PVC-device/bank/ordered ports/external reads/status, 입력·산출물 SHA, ROM stat 불변).
- 기존 회귀: card_child 검증기·unit의 `a29c` unsupported 경계는 아직 실행부가 없는 `a370`으로 옮긴다. `a29c` 정상 stop은 유지한다.

## 미확인·범위 밖

`a370` 메뉴 프레임(입력·커서·그리기 `9b58`/`9e1a`/`9d3a`/`a018`/`3918`/`3650`/`e84c8`), callback `c1c4`/`bf94`와 BIOS 재호출, `c2c8` 이후 페이드·부모 62=ff·`2a00`, TRAP #f 처리, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
