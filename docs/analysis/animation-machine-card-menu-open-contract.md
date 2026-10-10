# 카드 메뉴 첫 프레임들(`a370` 열림 애니메이션→`a5ea` 첫 전체 그리기·callback) 계약

Baseline: 메뉴 push 단위(리뷰0234) 통합 커밋. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 범위·경로를 확정했다. 아래 명령 의미 요약은 폭·부호·경로 결정의 근거이며, 명령 단위 정답은 원본 바이트 자체다. 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `a370..a3e2` | `4bf900108000247c00107f0e94fc0010b5edff0e6500004a2f0a2b4aff12b5edff0e67000024082a0000000f6700001a102a0004670000126100ff144a2a000466000006610003242652286b000ab8fc0000670000044e94245f94fc001060b0246dff0eb5fc00107f0e6500000670ff4e75` |
| `a3e2..a406` | `2b4aff12102dff1b0c000001670001e20c0000026700026a0c0000006700000670ff4e75` |
| `a5d2..a662` | `2b4aff121e2a0004be2a000c6400000a6100fd6470004e751b7c0000ff1b246dff12156a000700086100f52a4aab000466000018102a00075200b02a00066500000470001540000760d8226dff166100f5366100f7f4246dff122652d6fc00100c93ffffffff660000044e4f156a00070008303c00066100f4f4246dff12156a00070008303c00006100f4e270004e75` |
| `a348..a370` | `43fafcbe6100f80a7000102a000ced48d16a0004102a000ce148b06a000464000006354000044e75` |
| `a216..a280` | `246dff121f2a0007102a0007082a0001000f660000125200b02a00066500000470006000000c530064000006d02a000615400007154000084ebaf8d6202b000467c620130c80fffffffe67bc43fafda4155f00086100face156a000700086100fac4157c0000000e4e75` |
| `9b26..9b58` | `246dff122652d6fc00107000102a0008c0fc000ad6c04e753f0061e4301f206b0004322b0008b0fc0000670000044ed04e75` |
| `9b58..9bbc` | `246dff121e2a0004660000044e752652303c0001c06b000e670000086600031e4e75b5edff0e6600000a303c0b0060000006303c6b0048404240102a0009eb48d02a000a06407000360061000474650000144840103c00f423c0003c0000484006400020` |
| `9bbc..9cd4` | `1c2a000b0c060002630000206100044e650000144840103c00f023c0003c0000484006400020530660da61000430650000144840103c00f523c0003c00004840064000200c07000263000068524330036100040a650000144840103c00f223c0003c00004840064000201c2a000b0c06000263000020610003e4650000144840103c006023c0003c0000484006400020530660da610003c6650000144840103c00f323c0003c00004840064000205307609252433003610003a4650000144840103c00f623c0003c00004840064000201c2a000b0c060002630000206100037e650000144840103c00f123c0003c0000484006400020530660da61000360650000144840103c00f723c0003c000048400640002052434e75` |
| `9cd4..9d3a` | `61000342650000144840303c0bf823c0003c000048400640002053070c070002650000206100031e650000144840303c0bf923c0003c0000484006400020534760da0c0700016600001c610002f8650000144840303c0bfa23c0003c00004840064000204e75` |
| `9d3a..9e1a` | `123c0001d22a0008b22a0004650000044e754240102a0009eb48d02a000a0640700006400020d00126523e2b000e0247000ed6fc00107200122a0008c2fc000ad6c12053b0fcfffe660000167e001e2a000b5547650000066100ff40600000704a07660000584840102a0008b02a00076700000a303c00ff60000006303c031348406100025a6500000c484023c0003c0000484006400020610002446500001a48401e2a0008be2a000766000004520023c0003c0000484006400020b0fc00006700000c6100017c4eb900003918303c000548e700706100fd2c4cdf0e004e75` |
| `9e1a..9e94` | `246dff124a2a0004660000044e7526522053b0fc0000670000464eb9000038e84400d02a000be200d02a0009024000ffeb48d02a000a064070002053b0fc00006700001cb5edff0e6600000a323c010360000006323c06034eb9000039187000b02a000664000012154000086100feb2102a0008520060e84e75` |
| `9f7c..9fc4` | `b5edff0e670000141e2a0007be2a000867000008323c06034e752f0b2652322b000e265f0241000e0c41000266000014122a0007b22a000867000008323c0b034e75323c00034e75` |
| `a008..a080` | `6100000e650000082f2dff164e754e7548e707c03e00044770003c07ea4e0247001f207900107f12227900107f0e90fc0010b3c86200002e08280000000f6600001e1a069a280009ba28000b640000101a079a28000aba2800046500001290fc001060ce4cdf03e0023c00fe4e754cdf03e0003c00014e75` |
| `3918..392c` | `36006100ff520c020000660000044e754e9160ee` |
| `3650..3670` | `48403001e908e948100223c0003c000048400640002033fc8200003c00004e75` |
| `e84c8..e84d6` | `0c010010640000084ef900003650` |
| `c1c4..c214` | `4eb90000a73e0c4000066600000e3d7c012c007e4ef90000a2160c4000036600002e6100fb3e640000164eb900009f3641fa001e4eb90000a71a600000124eb900009f3641fa00284eb90000a71a4e75` |
| `bf94..bfbe` | `4eb90000a73e0c400006660000083d7c001e007e0c4000036600000e1d7c00ff00804ef90000a70a4e75` |
| `a73e..a75a` | `3f003f010c4000006600000c303c1a6c4eb900003af8321f301f4e75` |
| `c2c0..c2c8` | `4a00660000044e75` |

## 실행 경로(사실)

자연 연결: push 단위의 `a370` stop(같은 프레임, `c2ba` JSR, stack에 `c2c0` 위 `2ac2`)에서 `a370`을 실행한다. 이후 프레임은 직전 실제 출력(stop `2ac2`, A6=카드 자식)에서 PC=`2ab8`만 바꾸는 선언 재진입이며 자식 (A6)=`c2ba`이므로 `2abe`→`2ac0` JSR `c2ba`→JSR `a370`. 부모·다른 객체 프레임은 생략한 fixture다.

1. `a370` A5=`108000`; A2=`107f0e`-10; 루프 `a380` CMPA.L -f2(A5),A2, BCS `a3d0`(unsigned A2<-f2). 아니면 A2 push, -ee←A2; A2==-f2면 `a3b8`; 아니면 BTST #0,f(A2)·BYTE 4(A2) 검사 후 `a3a8` BSR `a2be`(범위 밖 경계)/`a3b4` BSR `a6da`(경계). `a3b8` A3=LONG (A2), A4=LONG a(A3), CMPA.W #0이면 건너뛰고 아니면 `a3c6` JSR (A4)(hook). `a3c8` A2 pop, -10, BRA `a380`. 메뉴 1개(`107efe`)에서는 1회 돌고 `c188+a`=0이므로 hook 없음.
2. `a3d0` A2=-f2; A2≥`107f0e`(unsigned)면 `a3de` MOVEQ -1,D0 RTS. 아니면 `a3e2` -ee←A2, D0.B=-e5(A5): 1→`a5d2`, 2→`a662`(경계), 0→`a406`(입력 경로, 경계), 그 밖→`a402` MOVEQ -1 RTS.
3. `a5d2` -ee←A2; D7.B=4(A2) CMP.B c(A2), BCC `a5ea`(unsigned 4≥c). 아니면 `a5e2` BSR `a348` 후 `a5e6` MOVEQ 0,D0 RTS.
4. `a348` LEA `a008`,A1; BSR `9b58`; `a350` D0=0, D0.B=c(A2), LSL.W #6, ADD.W D0,**WORD** 4(A2)(바이트 5 포함, 원래 메모리 값 그대로); D0.B=c(A2), LSL.W #8; CMP.W 4(A2),D0, BCC `a36e`(unsigned D0≥WORD), 아니면 `a36a` WORD 4(A2)←D0; RTS. push 직후 5(A2)는 기록되지 않은 잔여값이므로 프레임 수는 그 값에 의존한다(native connected chain에서는 `0088`→`0208`→`0388`→`0508`→`0688`→clamp `0600`).
5. `9b58` A2=-ee; D7.B=4(A2), 0이면 RTS; A3=(A2); WORD e(A3) AND 1이 0이 아니면 `9e94`(경계). A2==-f2면 D0.W=`0b00` 아니면 `6b00`; SWAP; CLR.W; D0.B=9(A2); LSL.W #5; ADD.B a(A2)(BYTE); ADDI.W #7000; D3.W=D0. 이후 상단 모서리 f4, 상단 테두리 f0×(b-2)(D6.B 루프, CMPI.B #2/BLS unsigned), f5, 행 루프(D7.B>2 동안: D3+1→D0, f2, 내부 60×(b-2), f3, SUBQ.B D7), 하단 f6, f1×(b-2), f7, D3+1. 각 타일은 BSR `a018`; BCS면 건너뜀; 아니면 SWAP, D0.B(또는 `9cd4` 경로의 D0.W)←타일, LONG D0→`3c0000`, SWAP, ADDI.W #20(`a332`류는 ADDI.L). `3c0000` LONG 쓰기는 기존 video port 기록 규약을 따른다.
6. `a018` MOVEM.L D5-D7/A0-A1 push; D7.W=D0-7000; D6=D7>>5(LSR.W); D7&=1f; A0=LONG `107f12`, A1=LONG `107f0e`; A0-=10; 루프: A1>A0(unsigned, BHI)면 `a06c` pop, ANDI CCR #fe(known Clear), RTS. 아니면 BTST #0,f(A0)≠0 또는 (D6.B-9(A0)) ≥ b(A0)(unsigned BYTE) 또는 (D7.B-a(A0)) ≥ 4(A0)이면 A0-=10 반복; 둘 다 안이면 `a076` pop, ORI CCR #1(known Set), RTS. 즉 현재 메뉴 위(더 최근) 프레임이 가리는 셀이면 C=1.
7. 호출자의 `BCS`(BSR `a018` 복귀 PC `9ba6` `9bcc` `9bea` `9c10` `9c36` `9c54` `9c76` `9c9c` `9cba` `9cd8` `9cfc` `9d22` `9dc0` `9dd6`, `a008`의 `a00c`)는 `a018`이 남긴 known C를 소비한다. C++에서 그 block 진입 C가 Unknown이면 checked 오류 `card menu caller requires known carry`(기존 cleanup/readiness 규약과 같은 형식).
8. `a008` BSR `a018`; C=1이면 `a016` RTS; 아니면 `a010` LONG -ea(A5) push 후 RTS(=renderer로 간접 점프, renderer의 RTS는 `a008` 호출자에게 돌아감).
9. `a5ea` BYTE 0→-e5; A2=-ee; 루프 `a5f4` 8(A2)←7(A2); BSR `9b26`(A3=LONG(A2)+10+8(A2).B×a, MULU.W); TST.L 4(A3)(callback)≠0이면 `a61c`; 아니면 7(A2)+1(BYTE), 6(A2) 이상(unsigned)이면 0, 7(A2)←D0, 반복. `c188`에서는 7=2(YES). `a61c` A1=LONG -ea(A5)(=`e84c8`); BSR `9b58`; BSR `9e1a`; A2=-ee; A3=(A2)+10; LONG (A3)==`ffffffff`면 `a63c` TRAP #f(경계); `a63e` 8←7, D0.W=6, BSR `9b3e`; `a64c` A2=-ee, 8←7, D0.W=0, BSR `9b3e`; `a65e` MOVEQ 0,D0 RTS(→`c2c0`).
10. `9e1a` A2=-ee; 4(A2)=0이면 RTS; 제목 A0=LONG (A3=(A2))≠0이면 JSR `38e8`(기존 실행부) 폭으로 가운데 위치(NEG.B, ADD.B b, ASR.B #1(부호 산술), ADD.B 9, ANDI.W ff, LSL.W #5, ADD.B a, ADDI.W 7000), A0 재로드, D1=A2==-f2?`0103`:`0603`, JSR `3918`. `9e78` 항목 루프 D0.B=0..6(A2)-1: 8(A2)←D0, BSR `9d3a`.
11. `9d3a` D1.B=1+8(A2); D1≥4(A2)(unsigned BYTE)이면 RTS(보이지 않는 행). 아니면 위치 D0.W=(9<<5)+a+7000+20+D1(BYTE ADD); A3=(A2); D7.W=e(A3) AND e; A3+=10+8×a; A0=LONG(A3). A0==`fffffffe`(CMPA.W)면 D7=b-2(SUBQ.W, borrow면 건너뜀) `9cd4` 구분선(bf8/bf9…/bfa, WORD 타일) 후 `9e08`. D7≠0면 커서 열 생략. 아니면 커서 칸: 8==7이면 타일 `0313` 아니면 `00ff`(첫 칸), 둘째 칸 BYTE+1(선택 시). A0≠0이면 `9f7c`(D1 팔레트 선택: A2≠-f2 이고 7≠8이면 `0603`; 아니면 descriptor e AND e==2 이고 7≠8이면 `0b03`, 그 밖 `0003`) 후 JSR `3918`. `9e08` D0.W=5; MOVEM A1-A3 push; BSR `9b3e`; pop; RTS.
12. `3918` D3.W=D0; 루프: BSR `386e`(기존); CMPI.B #0,D2 BNE `3928` 아니면 RTS; `3928` JSR (A1); `392a` BRA `391a`. A1=`a008`(열림 프레임) 또는 `e84c8`(`a61c` 프레임).
13. `e84c8` CMPI.B #10,D1, BCC `e84d6`(경계, 범위 밖). 아니면 JMP `3650`. `3650` SWAP D0; D0.W=D1; LSL.B #4; LSL.W #4; MOVE.B D2,D0; LONG D0→`3c0000`; SWAP; ADDI.W #20; WORD `8200`→`3c0000`; RTS.
14. `9b3e` D0.W push; BSR `9b26`; pop; A0=LONG 4(A3), D1.W=WORD 8(A3); A0==0(CMPA.W)면 RTS; 아니면 `9b54` JMP (A0)(callback은 RTS로 `9b3e` 호출자에게 돌아감). Callback의 A6는 live A6(카드 자식).
15. `c1c4`(YES): JSR `a73e`; D0.W==6이면 WORD `012c`→7e(A6), JMP `a216`; ==3이면 `c1e6` BSR `bd26`(BIOS 카드, 경계); 그 밖 RTS. `bf94`(NO): JSR `a73e`; ==6이면 WORD `001e`→7e(A6)(그리고 계속 비교); ==3이면 BYTE ff→80(A6), JMP `a70a`(경계); RTS.
16. `a73e` D0.W push, D1.W push; D0.W==0이면 D0.W=`1a6c`, JSR `3af8`(기존 sound 실행부); D1, D0 pop; RTS.
17. `a216` A2=-ee; BYTE 7(A2) push(WORD 칸, 68000 A7 BYTE push는 A7을 2 감소시키고 새 A7(짝수) 주소에 BYTE를 저장, pop은 A7 주소 BYTE를 읽고 2 증가); D0.B=7; 루프: BTST #1,f(A2)=0이면 +1(6 이상이면 0) 아니면 -1(borrow면 +6(A2)); 7,8←D0; JSR `9b26`; LONG 4(A3)==0 또는 LONG (A3)==`fffffffe`면 반복; `a262` A1=`a008`; 8(A2)←pop BYTE; BSR `9d3a`(이전 커서 행 다시 그리기); 8←7; BSR `9d3a`; BYTE 0→e(A2); RTS. `c1c4`의 JMP로 들어왔으므로 RTS는 `a64c`로 간다.

## 구현 범위와 규약

- 보정(리뷰 중 메인 확인): 1항의 `c2c0` TST.B D0/BNE `c2c8`, `c2c6` RTS를 실행 범위에 넣는다(`a5ea` 프레임이 `2ac2`에 도달하려면 필요). `c2c8`은 경계.

- 새 실행부 파일 `engine/src/animation_machine_card_menu_open.cpp`(함수 `animation_card_menu_open_block`): 위 표의 범위. 기존 `386e`/`38e8`(push 단위), `3af8`(sound), 디스패처·card child 실행부를 호출 경로로 쓰고 가리지 않는다.
- Block 시작 PC: 아래 목록 전부(분기 대상, 조건분기 fallthrough, 호출 복귀 주소, 호출 진입). 목록 밖 내부 PC 직접 진입은 거부한다.

`3650` `3918` `391a` `391e` `3926` `3928` `392a` `9b26` `9b3e` `9b42` `9b54` `9b56` `9b58` `9b64` `9b66` `9b78` `9b7a` `9b82` `9b8a` `9b8e` `9ba6` `9baa` `9bbc` `9bc0` `9bc8` `9bcc` `9bd0` `9be2` `9be6` `9bea` `9bee` `9c00` `9c08` `9c10` `9c14` `9c26` `9c2a` `9c32` `9c36` `9c3a` `9c4c` `9c50` `9c54` `9c58` `9c6a` `9c6e` `9c76` `9c7a` `9c8c` `9c90` `9c98` `9c9c` `9ca0` `9cb2` `9cb6` `9cba` `9cbe` `9cd0` `9cd4` `9cd8` `9cdc` `9cee` `9cf0` `9cf8` `9cfc` `9d00` `9d12` `9d16` `9d1e` `9d22` `9d26` `9d38` `9d3a` `9d4a` `9d4c` `9d86` `9d92` `9d96` `9d9a` `9da0` `9dae` `9db6` `9dba` `9dc0` `9dc4` `9dce` `9dd6` `9dda` `9de8` `9dea` `9df2` `9df6` `9dfe` `9e02` `9e08` `9e14` `9e1a` `9e26` `9e28` `9e34` `9e3a` `9e5e` `9e66` `9e6e` `9e72` `9e78` `9e7a` `9e82` `9e8a` `9e92` `9f7c` `9f84` `9f90` `9f96` `9fac` `9fb8` `9fbe` `a008` `a00c` `a010` `a016` `a018` `a03a` `a040` `a04a` `a058` `a066` `a06c` `a076` `a216` `a21e` `a22c` `a236` `a238` `a23c` `a242` `a246` `a252` `a258` `a262` `a26e` `a278` `a348` `a350` `a36a` `a36e` `a370` `a380` `a388` `a396` `a3a0` `a3a8` `a3ac` `a3b4` `a3b8` `a3c6` `a3c8` `a3d0` `a3de` `a3e2` `a3f2` `a3fa` `a402` `a5d2` `a5e2` `a5e6` `a5ea` `a5f4` `a5fe` `a606` `a614` `a616` `a61c` `a624` `a628` `a63e` `a64c` `a65e` `a73e` `a74a` `a754` `bf94` `bf9a` `bfa2` `bfa8` `bfb0` `bfbc` `c1c4` `c1ca` `c1d2` `c1de` `c1e6` `c1ee` `c1f4` `c1fe` `c202` `c208` `c212` `e84c8` `e84d0` `c2c0` `c2c6`

  (분기·복귀 리더 186개와 `a018` 호출자 BCS 복귀 PC 14개(위 7항, `a00c`는 186개에 이미 포함) = 200개, 여기에 아래 `c2c0`/`c2c6` 2개를 더해 202개. `c1ee`..`c208`은 `bd26` 경계 뒤라 이번 자연 경로에서 도달하지 않는다. 블록 경계 계산 스크립트는 메인 scratchpad의 capstone 분석이며 구현자는 원본 바이트로 재확인한다.)
- 같은 block 안에서 Z/N/C 생산자와 조건분기를 묶는다(위 목록에 없는 조건분기 PC는 직접 진입 거부). 예외: 7항의 `a018` 호출자 BCS는 별도 block이며 modeled carry를 소비한다.
- 경계(실행부 없음): `c2c8`(D0≠0 뒤 페이드, 다음 범위), `9e94` `9f36` `a2be` `a406` `a662` `a6da` `a70a` `a71a` `bd26` `e84d6` `a63c`(TRAP). stop을 그 PC로 주면 직전 상태로 멈추고, 다른 stop이면 checked 오류 `unsupported animation machine PC`와 전체 rollback.
- Carry: `a06c`는 known Clear, `a076`는 known Set을 남긴다. 전체가 FLOW_ONLY(LEA/MOVEA/PEA/JSR/JMP/BSR/BRA/RTS/MOVEM/NOP/BTST/BSET/BCLR/BCHG/조건분기)인 block만 C를 보존하고 그 밖은 Unknown. 구현자는 보존 block 목록을 원본 opcode로 계산해 보고한다(메인 리뷰 대상). `a06c`/`a076`의 MOVEM 뒤 CCR 명령은 같은 block이며 결과는 known이다.
- 프레임 재진입은 선언된 PC=`2ab8` 변경뿐이다. 자연 scheduler·IRQ·VBlank가 아니다.
- 모든 descriptor·문자열·메뉴 프레임·stack 읽기는 실제 접근 시점 live bus로 한다. BYTE/WORD 폭, unsigned 비교, ASR.B 산술, MULU.W, SUBQ.W borrow, BYTE push(A7-2)를 명시적으로 구현한다.
- 리소스 형식·loader/bus·기존 host 메뉴 API는 바꾸지 않는다. ROM·추출물은 수정하거나 Git에 추가하지 않는다.

## 검증 조건(최소)

- 연결: push 단위 C++ `a370` stop 출력에서 열림 프레임(같은 프레임 + 재진입)들을 거쳐 `a5ea` 프레임의 `a65e` RTS→`c2c0` TST/RTS→`2ac2` stop까지. 각 프레임 split/continuous, 직전 실제 C++ 출력 재개.
- 경계: 5(A2) 잔여 BYTE 변경(프레임 수 변화), c(A2)/b(A2) 변경(작은 상자, b≤2), 가리는 상위 메뉴 프레임이 있을 때 `a018` C=1 경로(-f2와 상위 프레임 fixture, `a3b8`/hook 경로 포함), hook A4≠0(경계 PC로 stop), 제목 있음, 구분자·null 항목, 모든 항목 callback 0(무한 루프가 아니라 항목 1개 이상에 callback이 있어야 종료하므로 그 경우는 budget 오류가 아니라 fixture로 피함을 기록), `e84c8` D1≥10 경계, `-e5`=0/2/기타, -f2≥`107f0e` RTS ff, D0=3 callback으로 `bd26`/`a70a` 경계, `9e94`(e bit0) 경계, `a63c` TRAP 경계, Unknown carry로 BCS 진입 오류, 묶인 분기·내부 PC 거부, 홀수 A2/A3/A0 오류 rollback.
- 비교 항목은 기존과 같다(full 64KiB RAM/16R/PC/A7/carry 분류/PVC-device/bank/ordered ports(video LONG/WORD 순서 포함)/external reads/status, 입력·산출물 SHA, ROM stat 불변).
- 기존 회귀의 `a370` unsupported 경계는 아직 실행부가 없는 PC(`a406` 등)로 옮긴다.

## 미확인·범위 밖

`a406` 입력 프레임과 이후 cursor/선택, `a662` 닫기, `a2be`/`a6da`/`9e94`/`9f36`/`a70a`/`a71a`, `e84d6` 가나 renderer 본문, `bd26` BIOS 카드 처리, TRAP #f, video port의 실제 화면 의미(타일 번호·팔레트 해석), 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
