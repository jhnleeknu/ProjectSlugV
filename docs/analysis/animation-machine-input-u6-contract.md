# `480bc` 프레임 helper 묶음 U6: 입력 `49b0c`·입력 callback 계약

**상태: 메인 리뷰를 거쳐 확정(아래 메인 결정). 구현·검증 기록이 아니다.** 범위 근거는 `animation-machine-480bc-scope.md`의 U6, 진입 경계는 확정된 U1 계약(`animation-machine-frame-helpers-u1-contract.md`)의 `480c6` JSR `49b0c`(복귀 LONG `480cc`)다. Claude Opus 5.5 / high 분석 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, fixed CPU 주소=file offset)을 capstone M68000으로 디코드하고 기존 관측 산출물을 읽기 전용으로 재생해 작성했다. U1~U5 실행부는 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `018d0b2`, WIP)의 `engine/src`를 읽기 전용으로 참조했다. [F]=원본 바이트 또는 기록된 산출물에서 확인한 사실, [I]=추론, [U]=미확인. 명령 단위 정답은 원본 바이트 자체다. 같은 루틴들의 typed host 재구성(`engine/src/stage_input*.cpp`, 문서 `stage-input.md`·`stage-input-callbacks.md`·`stage-input-loop.md`·`stage-frame-followup.md`·`player-record-capture.md`)은 machine 실행부가 아니며 교차 확인 자료로만 쓴다.

메인 결정(Claude Opus 5.5, 원본 대조 리뷰 후): (1) U6a·U6b·U6c 전체(block 시작 151)를 하나의 core 단위로 구현한다(기존 host가 지원하는 19 target을 machine에서도 유지; 분할보다 통합 주기가 적다). (2) `JSR (A1)` 대상은 U2~U5와 같은 계산 PC 정책을 따른다. 상위 BYTE가 0이 아닌 대상은 24bit로 접지 않고 checked 오류로 거부한다(실제 하드웨어와 다를 수 있는 유일한 지점이며, 잘못된 결과 대신 오류를 낸다). (3) `4d7f0` TRAP #15는 U1 `4939c`처럼 실행부 없는 경계다. (4) 이전 block flag로 시작하는 `49dd4`·`49e8a`는 앞 block에 접고, 분기 대상이자 fall-through인 `49f4a`(SNE 3명령)는 두 선행 block에 복제하며 `49f4a` 직접 진입은 거부한다(machine 상태에 Z를 추가하지 않는다). (5) `49ab0`·`4cf7e..4df60` ROM 자료는 물리 `program_rom_000000.ms5d` window로만 읽는다.

## 메인 결정 필요 항목

1. **분할과 미설치 callback 포함 여부**: [F] block 시작은 U6a 34, U6b 70(TRAP 경계 1 포함), U6c 47, 합계 151(아래 "구현 범위"). [F] U6c 대상 `49d88 49e38 49e9c 49eba 49ef0 49f2c`는 fixed/banked 전 8 MiB 원시 인코딩 검색에서 설치 경로를 찾지 못했다(아래 "callback 대상 집합").
   - 선택 A(**작업자 권고**): 2단계. U6a(core+null/marker 경로+단일 block callback 3개)를 먼저, 그다음 U6b와 U6c를 한 단위로 구현한다. 근거: 기존 host API(`step_stage_input_loop`)가 19개 대상을 지원·검증했으므로 machine이 지원 범위를 줄이지 않는다. U6c는 직선 코드가 대부분이고 `49de6`을 공유한다. 비용: 47 block과 아래 결정 4의 flag 접기.
   - 선택 B: U6a, U6b만 구현하고 U6c는 계산 PC 정책(결정 2)으로 `unsupported animation machine PC` 거부. 설치 경로가 없다는 [I]에 기댄다.
   - 선택 C: U6a+U6b+U6c를 한 번에(151 block). U2(215) 규모보다 작다.
2. **`JSR (A1)`(`49b2c`/`49b82`) 계산 PC 정책**: [F] 대상은 RAM LONG `10d734`/`10d738`(live A5 기준 `5734`/`5738(a5)`)이며 범위 검사가 없다. 비영이고 `289e` marker 검사(C=1)를 통과할 때만 호출된다.
   - 선택 A(**작업자 권고**): U2~U5와 같은 계산 PC. return LONG `49b2e`/`49b84`를 live stack에 push하고 PC=LONG 값. 지원 block 시작이면 실행, 홀수면 기존 홀수 PC 오류, 그 밖은 `unsupported animation machine PC`와 전체 rollback, 전용 오류 없음. **상위 BYTE가 0이 아닌 LONG**(예 `01049e34`)은 24-bit로 접지 않고 그대로 비교해 거부한다. [I] 실제 68000은 하위 24-bit로 fetch하므로 이 경우만 원본과 다르다. 자연 관측 값은 모두 null이다.
   - 선택 B: PC를 `&ffffff`로 접어 실행하고 push LONG은 원본대로 `49b2e`를 쓴다. 모든 실행부의 PC 비교 규약에 예외가 생긴다.
3. **TRAP #15 `4d7f0`**(`1da60`→`4d7a6`, record+`27` BYTE=0): 선택 A(**작업자 권고**)는 U1의 `4939c`와 같이 라우팅하지 않는 경계로 둔다. stop=`4d7f0`이면 그 직전 상태로 멈추고, 아니면 `unsupported animation machine PC`와 전체 rollback이다. 선택 B는 전용 오류 문자열을 둔다. [F] 기존 host API는 같은 경로를 구조화된 오류로 거부한다.
4. **앞 block의 N/Z를 소비하는 block 시작(모두 U6c)**: [F] `49dd4`(BMI, `49dcc` TST.W 뒤 BEQ의 fall-through), `49e8a`(BMI, `49e84` TST.W 뒤 BEQ의 fall-through)는 U2 `19c7e` 선례처럼 앞 block에 묶는다. [F] `49f4a`(SNE D2)는 `49f3e`의 BRA 대상이자 `49f46`의 fall-through이고, 두 앞 block의 TST.B Z를 소비한다. 선택 A(**작업자 권고**)는 `49f4a..49f52`(SNE.B D2, EOR.B D2,D1, BEQ)를 두 앞 block에 같은 의미로 복제하고 `49f4a` 직접 진입은 거부하는 것이다. 선택 B는 machine 상태에 Z를 추가하는 것으로, 공용 상태가 바뀌므로 권고하지 않는다.
5. **ROM 자료 창**: [F] 작업 트리 `program_bus.cpp`의 `rom_unit`은 legacy kind1 창과 physical 창이 겹치면 `partial or ambiguous legacy/physical program bus ROM unit`으로 실패한다. machine 검증기는 physical 8창(`extracted/runtime/program_rom/program_rom_*.ms5d`)을 쓴다. 선택 A(**작업자 권고**)는 U6가 `49ab0..49ab4`와 `4cf64..4df60`을 physical 창 `program_rom_000000.ms5d`로만 읽는 것이다. 기존 `stage_input/default_masks.ms5d`·`player_record_lookup.ms5d`는 host API 전용으로 두고 machine에 함께 넘기지 않는다.
6. **단일 block callback을 U6a에 넣는지**: 선택 A(**작업자 권고**)는 `49e34`(MOVEQ 0,D7; RTS), `1d8cc`(RTS), `e73f2`(MOVE.W `10de24`,D7; RTS)를 U6a에 넣는 것이다. 그러면 `49b2c→callback→49b2e→49afe` 경로를 U6a 단독으로 검증할 수 있다. 선택 B는 U6a를 core 31 block만으로 둔다. 그 경우 `49b2c` 이후 경로는 U6b까지 검증하지 못한다.

## 원본 바이트 근거

[F] 아래 코드 범위 합계 1,288바이트(368 명령, TRAP 1 포함, 미해독 0, 범위 안 빈틈 없음)와 자료 4바이트를 위 ROM에서 직접 추출했다(scratch `u6/bytes.md`, `u6/leaders6.py`).

| CPU 범위 | 단위 | 바이트 수 | 명령 수 | 원본 바이트 |
| --- | --- | --- | --- | --- |
| `49ab4..49bca` | U6a | 278 | 79 | `7e001e000207000f1c0774041a1c1800c805b8056600000c05c7c8016700000405c652020c02000865e2594c142c0002c42c000167000012080600066700000a08870005088600054e753c2900020246fff0bf46cc474e757e007c00226d5734b2fc00006700002041f900100cb84eb90000289e6400000c4e9143ed57264ebaffca60000022102dccaa122dccab49f90010f01c0c2d000280126700000649faff5c6100ff5c43ed5726610000547e007c00226d5738b2fc00006700002041f900100da84eb90000289e6400000c4e9143ed572c4ebaff7460000022102dccb0122dccb149f90010f0200c2d000280126700000649faff066100ff0643ed572c30290004337cffff0004ce40cc403347000232864e75` |
| `49e34..49e38` | U6a | 4 | 2 | `7e004e75` |
| `1d8cc..1d8ce` | U6a | 2 | 1 | `4e75` |
| `e73f2..e73f8` | U6a | 6 | 2 | `3e2d5e244e75` |
| `49c20..49c38` | U6b | 24 | 8 | `02400001e54843ed573443f1000022884e75307c000060e8` |
| `49c66..49c6c` | U6b | 6 | 2 | `41fa01cc60b4` |
| `49de6..49e34` | U6b | 78 | 22 | `7e00302800786600000c32390010d73c6000000832390010d73e2428004294ad53a22628004a96ad53aa4842484394416700fe4e9641b5436b00fe464a426b00000808c700024e7508c700034e75` |
| `49f66..49f8c` | U6b | 38 | 8 | `7000b1fc00100cb866000006102dccaab1fc00100da866000006102dccb049fafb2a6000fb2a` |
| `1bec0..1bee4` | U6b | 36 | 9 | `082800070015670000100828000700a7660000067e004e754eb900049f660247000f4e75` |
| `1d5ac..1d5c4` | U6b | 24 | 6 | `4eb90004836e6500000c302800784eb900049c327e004e75` |
| `1d5e2..1d5fc` | U6b | 26 | 7 | `0828000700156600003e7e004a6e003a6b0000063e3c00084e75` |
| `1d61a..1d63a` | U6b | 32 | 8 | `082800070015660000067e004e75302800784eb900049c324eb900049f664e75` |
| `1d664..1d698` | U6b | 52 | 16 | `7e0032280042926d53a2926800ae67b44a416a00000a0047000860000006004700043428004a946d53a2946800aeb5416b924e75` |
| `1d6c2..1d6fa` | U6b | 56 | 16 | `7e0032280046926d53a6926800ae6700ff564a416a00000a0047000160000006004700023428004e946d53a6946800aeb5416b00ff324e75` |
| `1da60..1daba` | U6b | 90 | 24 | `7e0032280042926d53a2926800ae670000284a416a00000a0047000860000006004700043428004a946d53a2946800aeb5416b0000044e75302800784eb90004d7a64a0067000012302800784eb900049c324eb900049f664e75` |
| `4836e..48384` | U6b | 22 | 6 | `082d0002568367000008023c00fe4e75003c00014e75` |
| `4d7a6..4d81c` | U6b | 118 | 36 | `4a006600000e49ed5cba41ed8cb86000000a49ed5ce641ed8da84eb90000289e640000084a5466000014303c000072007400760078007aff7c004e757000102c00270c400000660000044e4f122c0025142c0026362c001c3a2c00201c2c002a3800024400ffc8fc001049faf752d8c4382c000a4e75` |
| `49d88..49de6` | U6c | 94 | 31 | `242800422628004a94ad53a296ad53aa48424843302800786600000c32390010d73c6000000832390010d73e94419641b5436a0000103f022f086100fe6e205f341f44427e004a42670000126b00000a08c700026000000608c700034e75` |
| `49e38..49f66` | U6c | 302 | 83 | `7e00342800423628004a946d53a2966d53aa302800786600000c32390010d73c6000000832390010d73e94416700000a9641b5436a0000160828000700156700000c7e0041fa00ae6000fd9e4a42670000126b00000a08c700026000000608c700034e756100ff4848e7800030070240000c660000087e0008c700054cdf00014e754200b1f900100cb867000006103c0001012d57326600001a01ed57326100ff0e48e780003007004000204cdf00014e756100fefa4e754200b1f900100cb867000006103c0001012d57326700000a3028007842874e7548e780006100fed04cdf000234070242000c6600000603ed57324e757e0008280000001556c1302800786600000a4a2d5740600000064a2d574156c2b501670000144a026600000a08c700036000000608c700024e75` |
| `49ab0..49ab4`(자료, 기본 mask) | 자료 | 4 | — | `10204080` |

[F] 단위 합계: U6a 290바이트/84 명령, U6b 602/170(`4d7f0` TRAP 포함), U6c 396/114. 참고로 기존 `289e..28ae`(readiness 실행부, 바이트 `0c900000270e67000006003c00014e75`)와 자료 창 `4cf64..4df60`(4092바이트, SHA256 `a6ff769be292399534dc547ca3c43af55f33f5c047758ab44487d23cf0f6f899`)을 함께 쓴다. `49ab0..49ab4`의 SHA256은 `e80b549e486ab5a754fffde6b415bce417ecf2e3c62a989b3eeea3c9a80e8de6`이다.

## callback 대상 집합과 완전성

[F] 방법: scratch `u6/scan.py`·`scan2.py`로 8 MiB 전체의 짝수 offset에서 다음을 원시 인코딩으로 찾았다. JSR/JMP abs.L(`4eb9`/`4ef9`)과 LEA/MOVEA/PEA/MOVE #imm abs.L, fixed 1 MiB 안의 JSR/JMP/LEA/PEA (d16,PC), BRA/BSR/Bcc(byte·word)로 `49ab4..49f8c` 안을 가리키는 것. LONG 리터럴(`00049c20`, 각 callback 주소, `0010d734`/`0010d738`)도 찾았다. A5 변위 `5734`/`5736`/`5738`/`573a`를 쓰는 명령도 찾았다. 기존 `tools/inventory_stage_input_callbacks.py`의 20 후보(fixed, 49c20 abs와 PC 상대만)는 이 결과의 부분집합이다.

- [F] slot 쓰기 경로는 setter `49c20`(`MOVE.L A0,(A1)`, A1=`10d734`+(D0.W&1)<<2)과 초기화 `49a8e`(`475ec` JSR.L에서 호출)의 `CLR.L 5734/5738(a5)`뿐이다. [F] `49a8e`는 `10d726`/`10d728`/`10d72a`와 `10d72c`/`10d72e`/`10d730` WORD도 0으로 만든다. 따라서 초기화 직후 첫 `49bb4`의 일회성 mask는 0이다. `0010d734`/`0010d738` 리터럴은 physical `5585c2`/`5585d2`의 주소 목록 자료 안에만 있다([I] 디버그 감시 표, 코드 아님).
- [F] `49c20` 호출과 그 직전 A0 정의:
  - `1bee4` LEA `1bec0`이 두 slot에 설치한다(`1beea` JSR, `1bef2` JMP).
  - `1d5a0`→`1d5ac`, `1d5d6`→`1d5e2`, `1d60e`→`1d61a`, `1d658`→`1d664`, `1d6b6`→`1d6c2`, `1d8c0`→`1d8cc`, `1da2e`→`1da60`, `e7406`→`e73f2`. 모두 바로 앞이 LEA (d16,PC),A0다.
  - 내부 경로: `49c32`(A0=0), `49c66`(A0=`49e34`), `49e7c`(A0=`49f2c`, `49e38` callback 안).
  - setter: `49cba`(`49d88`), `49cd8`(`49de6`), `49d02`(`49e38`), `49d2c`(`49e9c`), `49d5c`(`49eba`), `49d80`(`49ef0`).
- [F] setter 진입 호출: `49cc2`(→`49de6`)는 `d6576 d6582 d6ab8 d6ad6`에서 호출된다. `49c66`(→`49e34`)은 `307c4 307cc bf9c6 bf9ce d5f7e d5f86 d6ac2 d6ae0 d6b80 d6bd0 d6c24 dceec`과 callback `49de6` 안에서 호출된다. `49c32`(해제)는 `47a0e 47a16 d60ec d60f4 dcf0a 1d5ba 1d62c 1daac 49dc2`에서 호출된다. **`49ca8 49ce0 49d0a 49d34 49d64` setter에는 호출 인코딩이 하나도 없다.**
- 설치가 확인된 대상(11, U6a/U6b): `49e34 49de6 1bec0 1d5ac 1d5e2 1d61a 1d664 1d6c2 1d8cc 1da60 e73f2`.
- 설치 경로를 찾지 못한 대상(6, U6c): `49d88 49e38 49e9c 49eba 49ef0`과 `49e38`만 설치하는 `49f2c`. [I] 사용되지 않는 코드일 가능성이 높다.
- 기존 host API가 callback 진입으로 받는 `49f66`·`1d628`은 설치 대상이 아니다. 둘은 각각 call/branch 대상이라 U6b block 시작에 포함되므로, 결정 2 선택 A에서 slot에 들어 있으면 실행된다.
- [I] 완전성 확신도: 직접 인코딩(abs.L·PC 상대·branch) 기준으로는 높다. [U] 다음 경우는 배제하지 못한다. 다른 base register(A6 등)로 `10d734`를 만드는 쓰기, 상대 offset jump 표나 계산 JSR로 setter에 들어가는 경로, 압축·복사된 코드, 홀수 정렬 데이터 안의 우연 일치.

## 실행 의미(A5=`108000` 기준 절대 주소)

[F] 모든 `d16(A5)` 접근은 live A5로 계산한다(U2~U5와 같음). A5=`108000`이면 다음과 같다.

- `5726..5730`→`10d726..10d730`, `5732`→`10d732`, `5734`/`5738`→`10d734`/`10d738`, `5740`/`5741`→`10d740`/`10d741`.
- `53a2`/`53a6`/`53aa`→`10d3a2`/`10d3a6`/`10d3aa`, `5683`→`10d683`, `5cba`/`5ce6`→`10dcba`/`10dce6`, `5e24`→`10de24`.
- `−7348`/`−7258`→`100cb8`/`100da8`(`4d7a6`만), `−3356`/`−3355`/`−3350`/`−334f`→`104caa`/`104cab`/`104cb0`/`104cb1`, `−7fee`→`100012`.

절대 주소 접근은 `100cb8`/`100da8`(`49b1c`/`49b72` LEA, `49ebc`/`49ef2` CMPA.L 메모리, `49f68`/`49f76` CMPA.L 즉시값), `10f01c`/`10f020`(LEA), `10d73c`/`10d73e`(WORD 읽기)뿐이다.

공통 폭 규칙은 U2~U5와 같다.
- MOVE.B/AND.B/EOR.B는 하위 BYTE만, MOVE.W/AND.W/EOR.W/SUB.W/ANDI.W/ORI.W는 하위 WORD만 바꾼다.
- MOVEQ·MOVE.L·SUB.L·CLR.L은 LONG 전체를 쓰고, SWAP은 두 WORD를 교환한다.
- CMPA.W #0은 An LONG 전체가 0인지 검사한다. CMPA.L은 32-bit 비교다.
- Dn 대상 BSET/BCLR/BTST는 bit 번호 mod 32, 메모리 대상은 mod 8이다.
- Scc.B는 하위 BYTE만 `ff`/`00`으로 쓰고 flag를 바꾸지 않는다. MOVEM.L은 flag를 바꾸지 않는다.
- BMI/BPL은 N만 본다.
- MULU.W는 D4 LONG 전체를 16×16 무부호 곱으로 쓴다. ADDA.W는 부호확장한다.

[F] U6 범위에 X 소비 명령(ADDX/SUBX/NEGX/ROXL/ROXR/ABCD/SBCD/NBCD)은 없다. `49ab2`의 `4080`(NEGX)은 자료 `49ab0..49ab4` 안이며 코드가 아니다.

1. [F] **`49b0c`**(U1 `480c6` JSR, 복귀 LONG `480cc`, 유일 호출자): 첫 플레이어부터 처리한다.
   - MOVEQ 0,D7; MOVEQ 0,D6; A1=LONG `10d734`; CMPA.W #0,A1이 같으면 `49b3a`.
   - 비null `49b1c`: A0=`100cb8`; JSR `289e`(기존 readiness, 복귀 `49b28`).
   - `49b28` BCC `49b36`(**carry 소비**): C=0, 즉 LONG (A0)=`270e` marker면 callback과 `49afe`를 건너뛴다.
   - C=1 `49b2c`: JSR (A1)(**계산 PC**, 결정 2), 복귀 `49b2e`.
   - `49b2e`: A1=`10d726`; JSR `49afe`(복귀 `49b36`). `49b36`: BRA `49b5a`.
   - null `49b3a`: D0.B=BYTE `104caa`; D1.B=BYTE `104cab`; A4=`10f01c`; CMPI.B #2,BYTE `100012`가 같지 않으면 `49b52` A4=`49ab0`(PC 상대, ROM 기본 mask). `49b56` BSR `49ab4`(복귀 `49b5a`).
   - `49b5a`: A1=`10d726`; BSR `49bb4`(복귀 `49b62`).
   - `49b62`: 둘째 플레이어를 같은 형태로 처리한다. 차이는 slot LONG `10d738`을 **이 시점 live RAM에서** 읽는 것, A0=`100da8`, 입력 `104cb0`/`104cb1`, 사용자 mask `10f020`, 결과 `10d72c`다. callback 복귀 PC는 `49b84`, 두 경로 합류는 `49bb0`이다.
   - `49bb0` A1=`10d72c` 뒤 `49bb4`로 **fall-through**하며, 그 RTS가 `480cc`로 돌아간다.
   - [F] callback 경로는 D0/D1/A4를 설정하지 않는다. callback은 진입 D0/D1(첫 slot은 U1 진입 시점 값, 둘째는 첫 처리 뒤 값), A0=객체, A1=callback 주소, live A6, D6=D7=0을 받는다.
2. [F] **`49ab4`**(BSR `49b56`/`49bac`, 그리고 `49f66`의 BRA tail): mask 4개로 held와 edge를 만든다.
   - 초기화: MOVEQ 0,D7; D7.B=D0.B; ANDI.B #`f`,D7; D6.B=D7.B(**D6 상위 24-bit 보존**); MOVEQ 4,D2.
   - 루프 `49ac0`: D5.B=BYTE (A4)+; D4.B=D0.B AND D5.B. D4.B=D5.B이면(mask 0도 충족) BSET D2,D7을 하고, 이어 D4.B AND=D1.B가 비영이면 BSET D2,D6을 한다.
   - `49ad6`: ADDQ.B #1,D2; CMPI.B #8,D2; BCS `49ac0`(같은 block 안 C 소비). 따라서 bit 4..7을 처리한다.
   - `49ade`: SUBQ.W #4,A4(A4 복귀); D2.B=BYTE 2(A4) AND BYTE 1(A4). 0이면 RTS. 아니면 BTST #6,D6이 1일 때 BCLR #5,D7과 BCLR #5,D6을 한다. RTS.
   - [F] 기본 mask `10 20 40 80`은 `20 AND 40`=0이라 bit5 제거 경로를 타지 않는다. D6 하위 nibble은 항상 D7 하위 nibble과 같다.
3. [F] **`49afe`**(JSR `49b32`/`49b88`): D6.W=WORD 2(A1)(이전 held, 상위 보존); ANDI.W #`fff0`,D6; EOR.W D7,D6; AND.W D7,D6; RTS. [I] 새로 눌린 button bit를 만들고, 방향 nibble은 held이면 항상 새 입력으로 친다.
4. [F] **`49bb4`**(BSR `49b5e`와 `49bb0` fall-through, 두 번 실행되고 RTS도 두 번): D0.W=WORD 4(A1)(일회성 mask); WORD `ffff`→4(A1); AND.W D0,D7; AND.W D0,D6; WORD D7→2(A1); WORD D6→(A1); RTS. [F] 쓰기 순서는 4(A1)→2(A1)→(A1)로, 기존 host 관측(`stage-input.md`)과 일치한다.
5. [F] **slot helper**:
   - `49c20`: ANDI.W #1,D0; LSL.W #2,D0(상위 보존); A1=`10d734`; A1=A1+sext(D0.W); LONG A0→(A1); RTS. A1이 slot 주소로 바뀐다.
   - `49c32`: MOVEA.W #0,A0(A0 LONG 0); BRA `49c20`.
   - `49c66`: A0=`49e34`(LEA PC); BRA `49c20`.
6. [F] **단일 block callback**(U6a): `49e34`는 MOVEQ 0,D7; RTS. `1d8cc`는 RTS(D7=0 유지). `e73f2`는 D7.W=WORD `10de24`(상위 WORD 0 유지); RTS.
7. [F] **`49de6`**(U6b):
   - MOVEQ 0,D7; D0.W=WORD 78(A0). 0이면 D1.W=WORD `10d73c`, 아니면 WORD `10d73e`.
   - D2=LONG 42(A0)−LONG `10d3a2`; D3=LONG 4a(A0)−LONG `10d3aa`; SWAP D2; SWAP D3.
   - SUB.W D1,D2가 0이면 `49c66`으로 tail. 아니면 SUB.W D1,D3; EOR.W D2,D3; BMI `49c66`(tail).
   - TST.W D2: 음수면 BSET #3,D7, 아니면 BSET #2,D7; RTS.
   - [F] tail에서는 slot (D0.W&1)에 `49e34`를 설치하고, `49c20`의 RTS가 callback 호출자로 돌아간다. 이때 D7=0, A0=`49e34`, A1=slot 주소다. [F] D0.W는 객체 +78 WORD이므로 `100cb8` 처리 중에도 그 WORD가 홀수면 **둘째 slot**을 바꾼다.
8. [F] **`1bec0`**: BTST #7,15(A0)=1이고 BTST #7,a7(A0)=0이면 MOVEQ 0,D7; RTS. 그 외 `1bed8`: JSR `49f66`(복귀 `1bede`); ANDI.W #`f`,D7; RTS.
9. [F] **`49f66`**: MOVEQ 0,D0. A0=**즉시값** `100cb8`이면 D0.B=`104caa`, A0=`100da8`이면 D0.B=`104cb0`. A4=`49ab0`; BRA `49ab4`. [F] D1과 D6은 설정하지 않는다. callback 경로에서는 `100012`와 무관하게 기본 mask를 쓰며, edge 계산에 남아 있던 D1.B가 들어간다. 다만 그 D6 하위 WORD는 뒤의 `49afe`가 다시 쓴다.
10. [F] **`1d5ac`**: JSR `4836e`(복귀 `1d5b2`). `1d5b2` BCS `1d5c0`(**carry 소비**). C=0이면 D0.W=WORD 78(A0); JSR `49c32`(복귀 `1d5c0`). `1d5c0`: MOVEQ 0,D7; RTS.
    - `4836e`: BTST #2,BYTE `10d683`. 0이면 `4837e` ORI #1,CCR(known Set); RTS. 1이면 `48378` ANDI #`fe`,CCR(known Clear); RTS.
11. [F] **`1d5e2`**: BTST #7,15(A0)=1이면 `1d628`. 아니면 MOVEQ 0,D7; TST.W 3a(**A6**)가 음수가 아니면 D7.W=8; RTS. [F] 자연 `49b0c` 진입 A6=`100820`(stage_frame 64 frame 경계 기록).
12. [F] **`1d61a`**: BTST #7,15(A0)=0이면 MOVEQ 0,D7; RTS, 1이면 `1d628`.
    - `1d628`: D0.W=WORD 78(A0); JSR `49c32`(복귀 `1d632`, **A0=0이 된다**); JSR `49f66`(복귀 `1d638`, A0=0이므로 D0=0); RTS.
13. [F] **`1d664`**: MOVEQ 0,D7; D1.W=WORD 42(A0)−WORD `10d3a2`−WORD ae(A0). 0이면 `1d628`(BEQ.B). TST.W D1이 음수가 아니면 ORI.W #4,D7, 음수면 ORI.W #8,D7. 이어 D2.W=WORD 4a(A0)−WORD `10d3a2`−WORD ae(A0)(이전 좌표도 같은 camera X); EOR.W D2,D1이 음수면 `1d628`; RTS.
    - **`1d6c2`**: 같은 형태로 46/4e(A0)와 `10d3a6`을 쓰고 ORI.W #1(음수)/#2(양수)를 한다.
14. [F] **`1da60`**: `1d664`와 같은 X 검사다. 현재 차분 0이나 교차면 `1da98`로 간다.
    - `1da98`: D0.W=WORD 78(A0); JSR `4d7a6`(복귀 `1daa2`). TST.B D0이 0이면 RTS.
    - 아니면 D0.W=WORD 78(**반환 A0**); JSR `49c32`(복귀 `1dab2`); JSR `49f66`(복귀 `1dab8`, A0=0); RTS.
15. [F] **`4d7a6`**: TST.B D0이 0이면 A4=`10dcba`, A0=`100cb8`, 아니면 A4=`10dce6`, A0=`100da8`(A5 상대). JSR `289e`(복귀 `4d7c6`).
    - `4d7c6` BCC `4d7d0`(**carry 소비**). C=1이면 TST.W (A4)가 0이 아닐 때 `4d7e2`.
    - `4d7d0`: D0.W=0(MOVE.W, **상위 보존**); MOVEQ 0으로 D1~D4=0, D5=−1, D6=0; RTS.
    - `4d7e2`: MOVEQ 0,D0; D0.B=BYTE 27(A4). D0.W=0이면 `4d7f0` **TRAP #15**(결정 3).
    - `4d7f2`: D1.B=25(A4); D2.B=26(A4); D3.W=1c(A4); D5.W=20(A4); D6.B=2a(A4); D4.W=D0.W; ANDI.W #`ff`,D4; MULU.W #`10`,D4(LONG); A4=`4cf64`(PC 상대)+sext(D4.W); D4.W=WORD a(A4); RTS.
    - [F] index는 1..255(0은 TRAP)이므로 ROM 읽기 범위는 `4cf7e..4df60`이다.
16. [F] **U6c**(설치 경로 미확인):
    - `49d88`: D2/D3=LONG 42/4a(A0)−LONG `10d3a2`/`10d3aa`; SWAP; 목표 D1.W는 `49de6`과 같다. SUB.W D1,D2; SUB.W D1,D3; EOR.W D2,D3이 음수면 다음을 한다.
      - `49dbe`: MOVE.W D2,-(A7); MOVE.L A0,-(A7); BSR `49c32`; A0=pop LONG; D2.W=pop WORD(live stack); NEG.W D2.
      - `49dcc`: MOVEQ 0,D7. D2.W가 0이면 RTS, 음수면 bit3, 양수면 bit2를 세우고 RTS.
    - `49e38`: WORD 좌표 42/4a(A0)−WORD `10d3a2`/`10d3aa`. 도달하거나 교차했고 BTST #7,15(A0)=1이면 MOVEQ 0,D7; A0=`49f2c`; BRA `49c20`. 그 외에는 D2.W 부호에 따라 bit3/bit2/없음.
    - `49e9c`: BSR `49de6`; MOVEM.L D0,-(A7); D0.W=D7.W; ANDI.W #`c`,D0이 0이면 MOVEQ 0,D7과 BSET #5,D7; MOVEM.L (A7)+,D0; RTS.
    - `49eba`: CLR.B D0. CMPA.L **LONG `100cb8`의 값**,A0이 다르면 D0.B=1. BTST D0,BYTE `10d732`(mod 8)가 1이면 `49eea` BSR `49de6`; RTS. 0이면 BSET D0,`10d732`; BSR `49de6`; MOVEM.L D0,-(A7); D0.W=D7.W; ORI.W #`20`,D0; MOVEM.L (A7)+,D0(OR 결과는 버려진다); RTS.
    - `49ef0`: 같은 메모리 비교로 D0.B를 정한다. bit=1이면 D0.W=WORD 78(A0); CLR.L D7; RTS. bit=0이면 MOVEM.L D0,-(A7); BSR `49de6`; MOVEM.L (A7)+,**D1**; D2.W=D7.W AND `c`가 0이면 BSET D1,`10d732`(mod 8); RTS.
    - `49f2c`: MOVEQ 0,D7; BTST #0,15(A0); SNE D1. D0.W=WORD 78(A0)이 0이면 TST.B `10d740`, 아니면 TST.B `10d741`. `49f4a` SNE D2; EOR.B D2,D1이 0이면 RTS. 아니면 D2.B가 0일 때 bit3, 비영일 때 bit2를 세우고 RTS.

[F] U6 쓰기 대상은 RAM(`10d726..10d731` WORD, slot LONG `10d734`/`10d738`, U6c의 `10d732` BYTE)과 live stack뿐이다. port·PVC·bank 쓰기는 없다. 읽기는 RAM, 객체 필드, fixed ROM `49ab0..49ab4`와 `4cf7e..4df60`이며 banked 읽기는 없다. [F] `100012`는 읽기(CMPI.B)만 하고 U6는 쓰지 않는다. 홀수 주소 WORD/LONG 접근(A0/A1/A6/A7)은 기존 checked 오류와 전체 rollback이다.

[F] Stack 깊이(`49b0c` 진입 A7 기준 추가 사용 최대):
- core: 4바이트(JSR `289e`/callback/`49ab4`/`49bb4`).
- 설치 확인 callback: 12바이트(`49b2c` 4 + `1da98` JSR `4d7a6` 4 + `4d7c0` JSR `289e` 4).
- U6c: 14바이트(`49b2c` 4 + `49dbe` push 6 + BSR `49c32` 4).

Push/pop은 live stack이며, `49dc6`/`49dc8`·`49eb4`·`49f18`은 저장 위치에서 다시 읽는다.

## 구현 범위와 규약

- [I] 새 실행부 파일 제안: `engine/src/animation_machine_input.cpp`(함수 `animation_input_block`).
  - U6a 라우팅: `49ab4..49bca`, `49e34`, `1d8cc`, `e73f2`.
  - U6b 라우팅: `49c20..49c38`, `49c66`, `49de6..49e34`, `49f66..49f8c`, `1bec0..1bee4`, `1d5ac..1d5c4`, `1d5e2..1d5fc`, `1d61a..1d63a`, `1d664..1d698`, `1d6c2..1d6fa`, `1da60..1daba`, `4836e..48384`, `4d7a6..4d7f0`, `4d7f2..4d81c`. **`4d7f0`은 제외**(결정 3).
  - U6c 라우팅: `49d88..49de6`, `49e38..49f66`.
  - [F] 작업 트리 라우팅과 겹치지 않는다. 가장 가까운 기존 범위는 interpreter `49f8c..4a46c`(U6 `49f66..49f8c` 끝과 맞닿음), interpreter `1dc84`/`1dc8a`, exit `48398..483a8`, readiness `289e..28ae`·`4847c..`, frame_helpers `4d9d6..4da06`, palette_bind `e7bf4..e7c10`, card_child `e7c16..`이다.
  - 초기화·setter·조회 루틴 `49a8e 49bca 49be0 49bf2 49c38 49c56 49c6c 49ca8 49cc2 49ce0 49d0a 49d34 49d64`은 U6 closure에서 도달하지 않으므로 라우팅하지 않는다.
- [F] U6가 부르는 기존 실행부는 `289e`(readiness, `49b22`/`49b78`/`4d7c0` JSR, known C 반환) 하나다(작업 트리 `animation_machine_readiness.cpp` 49행 case). U1 `480c6`의 `am_call(c,0x49b0c,0x480cc)`(`animation_machine_frame_helpers.cpp` 65행)은 그대로 둔다.
- **Block 시작 PC (151개)**: 루틴 진입, 분기 대상, 조건분기 fall-through, 호출 복귀, 호출 진입, 설치 callback 진입을 모두 넣는다. 일반 규칙으로 154개를 계산했고, 결정 4의 `49dd4`·`49e8a`·`49f4a` 3개를 뺐다(scratch `u6/leaders6.py`, `split.txt`). 목록 밖 PC 직접 진입은 거부한다.
  - U6a 34: `1d8cc` `49ab4` `49ac0` `49acc` `49ad4` `49ad6` `49ade` `49aec` `49af4` `49afc` `49afe` `49b0c` `49b1c` `49b28` `49b2c` `49b2e` `49b36` `49b3a` `49b52` `49b56` `49b5a` `49b62` `49b72` `49b7e` `49b82` `49b84` `49b8c` `49b90` `49ba8` `49bac` `49bb0` `49bb4` `49e34` `e73f2`
  - U6b 70(경계 `4d7f0` 포함): `1bec0` `1beca` `1bed4` `1bed8` `1bede` `1d5ac` `1d5b2` `1d5b6` `1d5c0` `1d5e2` `1d5ec` `1d5f6` `1d5fa` `1d61a` `1d624` `1d628` `1d632` `1d638` `1d664` `1d674` `1d67a` `1d682` `1d686` `1d696` `1d6c2` `1d6d4` `1d6da` `1d6e2` `1d6e6` `1d6f8` `1da60` `1da72` `1da78` `1da80` `1da84` `1da96` `1da98` `1daa2` `1daa8` `1dab2` `1dab8` `4836e` `48378` `4837e` `49c20` `49c32` `49c66` `49de6` `49df0` `49dfa` `49e00` `49e1a` `49e22` `49e28` `49e2e` `49f66` `49f72` `49f76` `49f80` `49f84` `4d7a6` `4d7ac` `4d7b8` `4d7c0` `4d7c6` `4d7ca` `4d7d0` `4d7e2` `4d7f0` `4d7f2`
  - U6c 47: `49d88` `49da4` `49dae` `49db4` `49dbe` `49dc6` `49dcc` `49dd8` `49de0` `49de4` `49e38` `49e52` `49e5c` `49e62` `49e68` `49e70` `49e7a` `49e84` `49e8e` `49e96` `49e9a` `49e9c` `49ea0` `49eae` `49eb4` `49eba` `49ec6` `49eca` `49ed2` `49eda` `49eea` `49eee` `49ef0` `49efc` `49f00` `49f08` `49f10` `49f18` `49f26` `49f2a` `49f2c` `49f3e` `49f46` `49f52` `49f58` `49f60` `49f64`
  - [F] 범위 문서의 근사 "core ~31 + callback ~132"는 core 31과 일치한다. callback 쪽 차이는 집계 대상(설치 확인 여부, `49c38` 등 setter 포함 여부)의 차이다.
- **묶인 분기·접힌 PC (54개, 직접 진입 거부)**:
  - U6a 9: `49ac8` `49ad0` `49adc` `49ae8` `49af0` `49b18` `49b4e` `49b6e` `49ba4`
  - U6b 25: `1bec6` `1bed0` `1d5e8` `1d5f2` `1d620` `1d672` `1d676` `1d694` `1d6d0` `1d6d6` `1d6f4` `1da6e` `1da74` `1da92` `1daa4` `48374` `49dec` `49e16` `49e1e` `49e24` `49f6e` `49f7c` `4d7a8` `4d7cc` `4d7ec`
  - U6c 20: `49da0` `49dba` `49dd0` `49dd4` `49e4e` `49e64` `49e6c` `49e76` `49e86` `49e8a` `49eaa` `49ec2` `49ece` `49ef8` `49f04` `49f22` `49f3a` `49f4a` `49f4e` `49f54`
- **Carry 소비 block (4개)**: `49b28`·`49b7e`(`289e` C), `4d7c6`(`289e` C), `1d5b2`(`4836e` C). 진입 C가 Unknown이면 checked 오류와 전체 rollback이다(제안 문자열 `input caller requires known carry`).
- **Known carry 생산**:
  - [F] 기존 `289e`가 known C를 반환한다(`28a8` ORI=Set, `28ac` 경로=CMPI.L 같음 Clear).
  - [F] 신규 `48378`(ANDI #`fe`,CCR → Clear)·`4837e`(ORI #1,CCR → Set) block이 RTS까지 그 C를 운반한다.
  - [F] `49ad6`(ADDQ/CMPI→BCS)는 block 안에서 C를 만들고 소비한다.
  - [F] U6 routine(`49b0c`, callback, `49c20`, `49f66`/`49ab4`)이 반환하는 C를 소비하는 호출자는 없다(`480cc` JSR, `49b2e` LEA, `1d5c0` MOVEQ, `1bede` ANDI.W, `49dc6` MOVEA, `49f18` MOVEM 뒤 MOVE.W).
- **Carry 보존(FLOW_ONLY) block (66개)**: 기존 규약대로 전 명령이 LEA/MOVEA/PEA/JSR/JMP/BSR/BRA/RTS/MOVEM/NOP/BTST/BSET/BCLR/조건분기인 block이다.
  - U6a 21: `1d8cc` `49ad4` `49aec` `49af4` `49afc` `49b1c` `49b28` `49b2c` `49b2e` `49b36` `49b52` `49b56` `49b5a` `49b72` `49b7e` `49b82` `49b84` `49b8c` `49ba8` `49bac` `49bb0`
  - U6b 25: `1bec0` `1beca` `1bed8` `1d5ac` `1d5b2` `1d5e2` `1d5fa` `1d61a` `1d632` `1d638` `1d696` `1d6f8` `1da96` `1dab2` `1dab8` `4836e` `49c32` `49c66` `49e28` `49e2e` `49f84` `4d7ac` `4d7b8` `4d7c0` `4d7c6`
  - U6c 20: `49dd8` `49de0` `49de4` `49e70` `49e8e` `49e96` `49e9a` `49e9c` `49eb4` `49eca` `49ed2` `49eea` `49eee` `49f00` `49f10` `49f26` `49f2a` `49f58` `49f60` `49f64`
  - 그 밖은 Unknown이다. [I] `48378`·`4837e`는 ANDI/ORI CCR이므로 FLOW_ONLY가 아니라 known 생산 block으로 따로 구현한다(U1 `493b6` 선례).
- **경계·stop**:
  - [F] 새 경계는 `4d7f0`(TRAP, 결정 3)뿐이다. U6a만 구현한 동안에는 `JSR (A1)` 대상 중 U6a 밖 PC가 실행부 없는 PC가 되어 stop 또는 rollback이다.
  - U6 구현 후에는 U1의 `49b0c` 경계가 일반 block 시작이 된다.
  - stop을 도달하는 block 시작 PC로 주면 그 PC 실행 직전 상태로 멈춘다.
  - 단독 검증 stop: `49b0c` 진입은 `480cc`(U1 block 시작, RTS 직후 상태), callback 직접 진입은 `49b2e`/`49b84`를 쓴다.
  - 도달하지 않는 stop은 실행부 없는 PC에서 `unsupported animation machine PC`와 전체 rollback이다(U1~U5와 같음).
- [F] 기존 회귀 중 `49b0c`를 "실행부 없음" 경계로 기대하는 곳이 있다. U6 구현 시 다른 실행부 없는 PC(`4aa88` 등)로 옮겨야 한다.
  - 작업 트리 `engine/tests/animation_machine_frame_helpers_test.cpp`: 56~63행 edge `{0x480c6,0x49b0c,0x480cc}`, 232행 `{0x480c6,0x49b0c,0x49b0c}`, 282행 outside 목록의 `0x49b0c`.
  - 작업 트리 `engine/tests/animation_machine_screen_test.cpp` 69행 `state(0x49b0c)` 거부 기대.
- **계산 PC 정책(결정 2)**: `JSR (A1)`의 대상에만 적용한다. U6 안의 다른 분기는 모두 고정 대상이다.
- 루프: `49ac0..49ade` 4회 고정 루프만 있다. 무한 루프 가능성은 없다.

## 시작 상태(관측 산출물 재생, 읽기 전용)

[F] 방법: scratch `u6/nat.py`가 기록된 PC 열을 읽어 `49b0c`..`480cc` 구간을 분류했다. 대상은 `artifacts/stage_entry_body/native_*.trace.json.gz`(152)와 `artifacts/stage_frame/verification.json`(SHA `47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5`, 96)이다. `u6/` 보조 스크립트는 stage_frame `host_writes`와 경계 레지스터 기록을 집계했다. Unicorn 재실행은 하지 않았다(PC 열과 기록 RAM 쓰기로 충분).

- [F] `49b0c` 호출자는 `480c6` 하나다(8 MiB 원시 검색). scene_frame_execution(594)과 scene_general_initialization(221) seed는 `1a73c`/`1a5a4`에서 시작하므로 `49b0c`에 도달하지 않는다.
- [F] stage_entry_body는 142/152, stage_frame은 64/96 frame이 `49b0c`에 들어가며, 모두 `480cc`로 돌아왔다.
  - 206 frame 전부 **두 slot null**이다(`49b18→49b3a`, `49b6e→49b90`). `100012`≠2이므로 기본 mask(`49b52`/`49ba8` 실행)를 쓴다.
  - 실행된 U6 block 시작은 16개다: `49ab4 49ac0 49ad6 49ade 49afc 49b0c 49b3a 49b52 49b56 49b5a 49b62 49b90 49ba8 49bac 49bb0 49bb4`.
  - 미실행 U6a 18개: `1d8cc 49acc 49ad4 49aec 49af4 49afe 49b1c 49b28 49b2c 49b2e 49b36 49b72 49b7e 49b82 49b84 49b8c 49e34 e73f2`.
  - [I] `49acc`가 미실행이므로 입력 BYTE `104caa`/`104cb0`의 bit 4..7은 모두 0이었다.
- [F] 두 trace 집합 어디에도 slot(`10d734..10d73b`) 쓰기 기록이 없고, `49c20`/`49c32`/`47a0e`도 실행되지 않았다.
  - stage_frame 31 case는 host write로 slot LONG 0, 객체 `100cb8`/`100da8` LONG `270e`(1 case는 0)를 둔다. `100012`는 `00`(14)/`01`(2)이다.
- [F] stage_frame `49b0c` 경계 기록은 A6=`100820`, A7=`1feff8`이다(64/64). stage_entry_body의 A6는 [U].
- [F] 자연 seed에서 callback을 실행하는 경우는 없다. U6b/U6c는 자연 `480bc` seed로 도달하지 않는다.
- [F] 선언 진입 자료(재사용 후보, host API용):
  - `artifacts/stage_input_loop/observation.json`은 3,229 조건이고 그중 `49b0c` 1,142 조건이다. dynamic call은 두 slot 각각 19 대상(설치 확인 11 + U6c 6 + `49f66`·`1d628`)이다. 분기 비율은 `49b18` 127/1015, `49b28` 125/2(marker skip), `49b4e` 762/253(사용자 mask), `49b7e` 128/2, `4d7c6`/`4d7cc`/`4d7ec`이다.
  - `artifacts/stage_input_callback/observation.json`은 2,943 조건이다.
  - [F] 두 관측 모두 명령 PC 목록이 아니라 명령 수만 기록하므로 block coverage는 machine 검증에서 다시 재야 한다. [I] fixture 생성기(`tools/observe_stage_input_loop.py`의 `build_cases`/`fixture`)를 machine 선언 진입에 재사용할 수 있다.
- [I] 자연 연결: U1 `480c6` → `49b0c`(U6a) → `480cc` → `4aa88`(U7 경계). U1~U6a 결합 뒤에는 stage_entry_body·stage_frame 자연 frame을 `4aa88` 경계까지 비교할 수 있다.

## 검증 조건(최소)

- 자연(결합, U1~U5 구현 위): stage_entry_body 142·stage_frame 64 frame을 `480bc`에서 `4aa88` stop까지 원본과 비교한다. split/continuous로 한다.
- 자연(U6a 단독): 같은 206 frame을 원본으로 PC=`49b0c`에서 캡처한 상태에서 `480cc` stop까지 비교한다.
- 선언 진입(native fixture, `49b0c` 진입과 복귀 LONG `480cc`):
  - stage_input_loop 1,142 조건을 재생한다. U6a 단계에서는 U6a 밖 callback 대상 조건이 그 대상 PC stop 또는 unsupported rollback이어야 한다.
  - 사용자 mask(`100012`=2)를 넣는다. 영 mask, 중복·겹침 mask(`1(A4)&2(A4)`≠0이면서 D6 bit6 1/0), all-ones를 포함한다.
  - 일회성 mask `ffff`/0/부분, marker skip, 두 slot 조합을 넣는다.
  - 첫 callback이 둘째 slot을 해제·설치하는 경우를 넣는다(`1d5ac`+`10d683` bit2, `49de6` 도달에서 객체 +78 WORD 홀수).
- callback 직접 진입(stop `49b2e`): 설치 확인 11 대상 전부를 넣는다(U6c는 결정 1에 따름).
  - `1d5e2`의 A6+3a 부호.
  - `1da60`→`4d7a6`의 inactive marker, (A4) WORD 0, index 1..255(`4cf64` 창), index 0 TRAP(stop `4d7f0` 일치 또는 rollback).
  - `49eba`/`49ef0` 메모리 LONG 비교와 `49f66` 즉시값 비교(A0=0 포함), `49e9c`/`49ef0` MOVEM 저장·복원.
- 계산 PC(결정 2): slot이 홀수, RAM 주소, 상위 BYTE 비영, 다른 실행부 block 시작(예 `49e34`가 아닌 기존 block)인 경우와 block 중간을 넣는다.
- 경계·오류:
  - Unknown carry로 `49b28 49b7e 1d5b2 4d7c6` 직접 진입하면 오류여야 한다.
  - 묶인·접힌 분기와 내부 PC 직접 진입은 거부해야 한다(`49dd4 49e8a 49f4a` 포함).
  - 홀수 A0/A1/A6/A7 접근 오류 rollback, zero-step, 비도달 stop rollback을 넣는다.
  - U1 회귀의 `49b0c` 기대값과 screen 회귀 69행을 갱신한다.
- 비교 항목은 기존과 같다: full 64KiB RAM/16R/PC/A7/carry 분류/PVC-device/bank/ordered ports(U6는 0개)/external reads/status, 입력·산출물 SHA, ROM stat 불변. C 판정은 원본 opcode 분류로 하고 Unicorn hook에서 SR을 읽지 않는다(U3~U5와 같음).

## 필요한 ROM·MS5D 자료 창

- [F] fixed ROM `49ab0..49ab4`(`10204080`). 기존 kind1 `extracted/runtime/stage_input/default_masks.ms5d`(CPU `49ab0`, payload 4)가 있으며 host API가 쓴다.
- [F] fixed ROM `4cf64..4df60`(4092바이트, 실제 읽기는 `4cf7e..4df60`의 WORD). 기존 kind1 `extracted/runtime/player_record_lookup.ms5d`(ID `player-record-lookup:0004cf64`)가 있다. 기존 `game_records.ms5d` 320바이트 prefix와 겹친다.
- [F] 두 창 모두 physical `extracted/runtime/program_rom/program_rom_000000.ms5d` 범위 안이다. machine은 결정 5에 따라 physical 창으로 읽는다.
- [F] 주소만 싣고 읽지 않는 PC 상대 상수는 `49e34`(`49c66`), `49f2c`(`49e7c`), `49ab0`(`49b52`/`49ba8`/`49f84`, 이후 읽음), `4cf64`(`4d810`)다. banked 자료는 없다.
- [I] machine 검증기는 physical ROM을 직접 읽으므로 위 kind1 창은 게임 런타임 납품 범위의 확인용이다.

## 미확인·범위 밖

1. 메인 결정 1~6.
2. [U] U6c 대상과 setter `49ca8 49ce0 49d0a 49d34 49d64`의 실제 사용 여부. 간접 설치 경로가 있는지(완전성 절).
3. [U] 자연 플레이에서 slot이 비null이 되는 문맥(`d6576` 등 설치 호출 위치의 게임 상황)과 그때의 A6·D0/D1·객체 +78 WORD 값.
4. [U] 입력 RAM `104caa/ab/b0/b1`의 생산자와 의미([I] 현재 held·새 눌림 BYTE), `100012` 값 2의 의미([I] 사용자 버튼 배치 사용), `10f01c..10f023`의 생산자.
5. [U] TRAP #15 처리기(vector)와 그 의도. `4d7a6` index 0의 자연 발생 여부.
6. [U] `10d732` bit, `10d740/741`, `10de24`, 객체 +15 bit0/7, +a7 bit7, +ae, +78의 게임 의미(이 문서의 명칭은 [I]).
7. [U] slot LONG 상위 BYTE가 비영인 값의 자연 발생 여부(결정 2).
8. [I] U7(`4aa88`·`e8a48`)과 전체 `480bc` frame 통합, 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이·전체 Goal은 범위 밖이다.

작업자 scratch: 세션 scratchpad `u6/`(`md.py`, `scan.py`, `scan2.py`, `leaders6.py`, `leaders6_{a,b,bu,all}.json`, `L_*.txt`, `split.txt`, `bytes.md`, `nat.py`, 저장소 밖).
