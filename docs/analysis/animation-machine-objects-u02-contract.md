# 객체 callback F4 U02: 문자열 커서 `3950`/`396e`/`3a70`·C1 `8ebe`·C5 `443d2`·결과 callback `e5120` 계열 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U02 행과 그 "메인 결정"이다. 형식과 관례는 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)을 그대로 따른다. 적용하는 메인 결정은 다음과 같다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다. 앞 조건분기와 같은 비교의 flag를 쓰는 바로 뒤 `Bcc`는 앞 block에 묶는다(U01 관례).
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- 결정 6: `TRAP #f`는 실행부 없는 checked 경계다(stop이면 직전 상태로 멈춤, 아니면 rollback).

구조와 규약(묶인 분기, carry 보존 목록, 소비 block, 내부 PC 거부, ROM window)은 F1a·F1b·F1c·F3·U01 계약을 따른다. 실행 규약(프레임 패스)은 F2 계약(`animation-machine-scheduler-shell-f2-contract.md`)과 같다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U02의 코드와 자료는 모두 fixed `<100000`에 있으므로 CPU 주소와 file offset이 같다. 기존 실행부와 routing은 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `4b36ff8`, U01 WIP)을 참조했다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u02/u02.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같다.

## 요약

- [F] U02는 **block 시작 133개 + TRAP 경계 3개(`39c6`, `3a0c`, `8ec8`)**다. 코드 10 범위, 1,584바이트, 395명령이며 미해독은 없다. routing 짝수 PC는 792개, 내부 PC는 659개다.
- [F] **범위 문서 140과의 차이(−7)**:
  - −6: `8fe0` `8fe4` `8fe8` `8fec` `8fee` `8ff2`는 `8fdc` 직선 block 안의 Unicorn TB 분할 인공물이다(결정 3, 범위 문서 "측정 방법"이 이미 지적).
  - −3: TRAP 자리 `39c6`·`3a0c`·`8ec8`은 block이 아니라 경계다(F3b·U01 관례).
  - −1: `e50fc BNE`는 앞 `e50f8 BCS`의 fall-through이며 같은 `CMP.L (A0),D2`의 Z를 소비한다. `e50f4`에 묶는다.
  - +3: `e51e6`(`e51e0`이 설치), `e523c`(`e5236`이 설치), `e525a`(`e5254`가 설치)는 `MOVE.L #imm,(A6)` callback 진입이다. 범위 스크립트는 본문 안 fall-through라 leader로 세지 않았다.
- [F] 함수(진입) 12개: 문자열 커서 `3950`(기록 설정), `396e`(한 단계, C 반환), `3a70`(`104cd6` 기록으로 문자열 전체), C1 palette slot 참조 `8ebe`, C5 `443d2`(sin/cos 곱), 결과 비교 `e5086`, node callback `e5120`(설치 callback `e5168` `e5196` `e51ac` `e51d0` `e51e6` `e523c` `e525a`), 자식 callback `e5614`(+`e5626`), `e5680`(+`e56a0`), `e5724`(+`e5794`), `e579c`·`e57a4`(공통 `e57a8`, +`e57f0`).
- [F] 경계(실행부 없음): callee `36ba` `3902`(`8ebe`의 debug 출력 경로), `383e` `37e2`(`396e`의 `%` 서식 경로), `48256`(`e5286`), `e6496`(`e50c4`). TRAP `39c6` `3a0c` `8ec8`. `8eca RTS`(TRAP 뒤, 도달 불가)와 debug 문자열 `8f6c..8f84`는 routing 밖이다. `e51f0`/`e5200`이 만드는 자식 `e5324`는 U02 밖이다(`28ae`의 자료일 뿐 U02 안에서 실행되지 않는다).
- [F] 계산된 호출(간접) 3곳: `3a10` `3a36` `3a66 JSR (A1)`. 아래 "계산된 호출 정책".
- [F] 기존 실행부로 나가는 출구: card_menu `386e`, card_menu_open `3650`·`e84c8`(간접 대상), palette_bind `8da2`, U01 `48296`, fade_card `28ae`·`2a00`, sound `3af8`, interpreter `49f8c`·`49fc6`, F3a `43e34`.
- [F] 자연 seed(F2 프레임 패스, 기본 120 frame): 90·91·118~126(11개)의 첫 미연결 callback `e5120`이 U02로 연결된다. 이 seed들은 frame 29에 `e5680`→`3950`/`396e`→`3a0e JSR (A1)`=`e84c8`→`e84cc BCC e84d6`(D1.B≥`10`)으로 U03 범위 `e84d6`에 닿는다. 따라서 U02만으로 새 완주 seed는 없다(39 유지, 범위 문서 예상과 같음).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(140→133).** 위 요약의 −6/−3/−1/+3을 채택한다(권고). 범위 문서는 고치지 않는다.
2. **계산된 호출 `JSR (A1)` 정책(권고).** 대상은 live A1(32비트) 그대로이고, 표를 두지 않고 routing이 실행부를 고른다. 홀수 대상은 기존 `unaligned animation machine PC`, 실행부 없는 대상은 `unsupported animation machine PC`이며 둘 다 run 전체 rollback이다(복귀 LONG push는 rollback에 포함). 새 오류 문자열은 만들지 않는다.
   - [F] 근거: fixed ROM에서 `3950`/`3a70`을 부르는 정적 호출자 11곳(`eec` `9730` `987a` `b70c` `e52ac` `e52d0` `e52f0` `e531e` `e563e` `e5660` `e5694`)은 호출 직전 `LEA` 로 A1을 `e84c8`(10곳) 또는 `3650`(`eec`, 1곳)으로 둔다. 둘 다 기존 card_menu_open 실행부 진입이다. U02 안의 호출자(`e5626` `e5644` `e5680`)는 모두 `e84c8`이다.
   - [F] `e84c8`은 `CMPI.B #10,D1; BCC e84d6`이고 `e84d6`은 U03 범위다. U02 단독에서는 경계가 된다.
   - [I] card_menu_open의 `3928 JSR (A1)`은 자체 오류(`animation card menu open odd jump target`)를 두지만, U02는 지시된 오류 문자열 두 개만 쓰므로 홀수 대상도 공통 dispatcher 오류로 둔다. 둘 다 checked 오류이고 상태 보존은 같다.
3. **`ADDQ.W An` block의 carry.** [F] 68000에서 `ADDQ` to An은 CCR을 바꾸지 않는다. U01 관례(`4b570 ADDQ.W #1,A2` block Unknown)를 따라 `39ae`(`ADDQ.W #1,A0; BRA`)와 `8f68`(`ADDQ.W #2,A7`)은 Unknown으로 둔다(보수적. 소비자 없음).
4. **`8ebe`의 A5 변경.** [F] `8ecc LEA 108000.L,A5`는 호출자의 A5를 `108000`으로 덮어쓴다. 원본대로 둔다(자연 상태에서는 이미 `108000`).

## 원본 바이트 근거

[F] 코드 10 범위 합계 1,584바이트. 이어 붙인 SHA256 `e3a74ec0b5dfd9c6af6d506662160cb8b21daf4475cf3d8be167e20956ec22ca`.

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `3950..39c6` | `274800062749000a274a000e36803740000237410004377c000000164e75206b0006226b000a3013322b0004362b00026100feec0c02000066000008003c00014e75374300023741000436800c0200256600006c14100c0200256600000852486000005c0c02003057c36100fe820c47000066000004` |
| `39c8..3a0c` | `1418246b000e3c2b0016be466600000e377c000000162748000660924a0666000010205a274a000e2748001260000006206b00120c0200736700001c0c02007867000048` |
| `3a0e..3a82` | `30134e91368027480006023c00fe4e75526b00163013342b00023f076100fe4237410004374300024e913e1f2748001236800c1000006600000637470016023c00fe4e75382b00165244374400166100fd84301341fafbec4e913680023c00fe4e7547f900104cd66100fed86100fef264fa4e75` |
| `8ebe..8ec8` | `0c2e0004001d65000006` |
| `8ecc..8f6c` | `4bf90010800043edcd9208010000660000343e00024700ffe94f58473c317002bc476700002045f16000b06a000a6600000c082a0000000f6700008e3c2a0002bc4766e23e3c10003c31700245f16000bc47660000641d7c00ff0014083900020010f000670000383200024101ff3f01e248064001003f0041fa00264eb900003902204f76ff78024eb9000036ba544f204f76ff78034eb9000036ba544f4e75` |
| `8f84..8ff4` | `3540000a3540000c08c100071541000f0c6affff000867000006526a0008320030063801024400ffe94c584449f14000b06c0002670000223412362a00023382300033832002362c00023380300035430002348439400002e8487400142e001d1d8020191d40001452021d42001d4e75` |
| `443d2..443ea` | `74001401e0802200d44241fafdc0c1f02000c3f020804e75` |
| `e5086..e5292` | `303cffff3200342e007c41f90010fdb60c30000020006700007441f90010de1443f90010de1c4a6e007c6700000e41f90010de1c43f90010de1448e700c04eb9000e649653404cdf03000c41000a6400003c74014a6e007c67000004740045f90010fdb60c3200002000670000202411b49065000018660000104a6e007c6700000c524160000006524052410c41000a65000006303c03e74e7541fafe7c4eb900008da24eb900048296207c000e5724303c00004eb9000028ae3d7c0001007c6100ff3e3d4000843d7c0000007c6100ff303d4000823d7c001e007a2cbc000e5168536e007a670000044e75303c1a8c4eb900003af8207c000e5680303c00004eb9000028ae422e00622cbc000e51964a2e0062660000044e753d7c001e007a2cbc000e51ac536e007a670000044e75207c000e5614303c00004eb9000028ae422e00622cbc000e51d04a2e0062660000044e753d7c000f007a2cbc000e51e6536e007a670000044e75207c000e5324303c00004eb9000028ae2f08207c000e5324303c00004eb9000028ae7000720124390010de14b4b90010de1c64000004c1413140007c225f3341007c422e00622cbc000e523c0c2e00020062670000044e753d7c0014007a3d7c19c000862cbc000e525a0c6e19cf00866c000010526e0086302e00864eb900003af8536e007a670000044e75303c19c04eb900003af84eb9000482564ef900002a00` |
| `e5614..e56c0` | `3d7c0004002e3d7c000f00322cbc000e5626302e002eeb48d06e00320640700041faf9c643f9000e84c84eb900003a70536e0032302e002eeb48d06e00320640700041faf98043f9000e84c84eb900003a700c6e0005003266000010206e000c50e800624ef900002a004e75303c708f41faf95243f9000e84c847f90010ddfa4eb9000039502cbc000e56a047f90010ddfa4eb90000396e64000010206e000c50e800624ef900002a004e75` |
| `e5724..e583c` | `207c000e579c303c00004eb9000028ae317c0000007e207c000e57a4303c00004eb9000028ae08e800000015317c4000007e207c000e579c303c00004eb9000028ae08e800000015317c8000007e207c000e57a4303c00004eb9000028ae317cc000007e3d7c4000007e2cbc000e5794046e0100007e4e75303c000060000006303c00013d7c022b002043fa008cd040d04022710000303c01004eb900049f8c303c035f123c00004eb900008ebe42ae002e2d7c0180000000323d7c000000683d7c0000001e2cbc000e57f04eb900043e34206e000c3228007ed26e007e6b000036e0493f01203c0000ffff4eb9000443d2e0491d410012321f203c000088004eb9000443d2e088064000a03d40002e4eb900049fc64e75` |

- [F] 범위에서 뺀 바이트: TRAP `39c6`(`4e4f`), `3a0c`(`4e4f`), `8ec8`(`4e4f`)와 그 뒤 `8eca RTS`(`4e75`, 도달 불가); `8f6c..8f84` debug 문자열(`\c` `\p` `\l` 제어 코드 + 반각 가타카나 `ﾊﾟﾚｯﾄ ｵｰﾊﾞｰ`, [I] "palette over"); `e5292..e5614`(다른 함수 `e5292` `e52b2` `e52d6` `e52f6`와 자식 `e5324`), `e56c0..e5724`(BCD 변환 `e56c0`, U02 밖), `e583c..`(자료).
- [F] 자료(모두 physical window로만 읽음, F1 결정 6):
  - `4419e` WORD 표(`443dc LEA 4419e(PC),A0`): `(A0,D2.W)`와 `-80(A0,D2.W)`, D2=2×D1.B(0..`1fe`)이므로 읽는 범위는 `4411e..4439e`다. [I] 256 단계 sin 표와 그 1/4 주기 앞(cos).
  - `e583c` LONG 2개(`e57ae LEA e583c(PC),A1`): `000e5844` `000e5850`. `49f8c`(interpreter)에 넘기는 script 포인터다.
  - 문자열 `e4ffc` `e4fd8`(`e5626`/`e5644`/`e5680`의 A0), palette_bind 인자 `e4f9e`(`e5120`의 A0). 이 바이트는 `386e`(card_menu)·`3650`/`e84c8`(card_menu_open)과 `3a38 CMPI.B #0,(A0)`·`39a4`·`39c8`이 읽는다. [F] `e4fd8`·`e4ffc`에는 `%`(`25`)가 없다(자연 경로는 `39a4..3a68` 서식 분기를 쓰지 않는다).
  - `3a62 LEA 3650(PC),A0`는 주소만 A0에 둔다.

## block 목록과 실행 의미

[F] 133 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 live 레지스터를 쓰고 index `(An,Dn.W)`는 부호확장한다. MOVE.B/MOVE.W Dn·ADD.W·SUB.W·LSR.W·LSL.W 등은 나머지 bit를 보존한다.

**문자열 커서 `3950`/`396e`/`3a70` 31**
- `3950`: `MOVE.L A0,6(A3); MOVE.L A1,a(A3); MOVE.L A2,e(A3); MOVE.W D0,(A3); MOVE.W D0,2(A3); MOVE.W D1,4(A3); MOVE.W #0,16(A3); RTS`
- `396e`: `MOVEA.L 6(A3),A0; MOVEA.L a(A3),A1` (→`3976`)
- `3976`: `MOVE.W (A3),D0; MOVE.W 4(A3),D1; MOVE.W 2(A3),D3; BSR 386e` (card_menu 실행부)
- `3984`: `CMPI.B #0,D2; BNE 3992`
- `398c`: `ORI.B #1,CCR; RTS` (C=Set 생산: 문자열 끝)
- `3992`: `MOVE.W D3,2(A3); MOVE.W D1,4(A3); MOVE.W D0,(A3); CMPI.B #25,D2; BNE 3a0e`
- `39a4`: `MOVE.B (A0),D2; CMPI.B #25,D2; BNE 39b4`
- `39ae`: `ADDQ.W #1,A0; BRA 3a0e` (`%%`)
- `39b4`: `CMPI.B #30,D2; SEQ D3; BSR 383e` (경계 callee)
- `39be`: `CMPI.W #0,D7; BNE 39c8` (0이면 TRAP `39c6`)
- `39c8`: `MOVE.B (A0)+,D2; MOVEA.L e(A3),A2; MOVE.W 16(A3),D6; CMP.W D6,D7; BNE 39e4`
- `39d8`: `MOVE.W #0,16(A3); MOVE.L A0,6(A3); BRA 3976`
- `39e4`: `TST.B D6; BNE 39f8`
- `39ea`: `MOVEA.L (A2)+,A0; MOVE.L A2,e(A3); MOVE.L A0,12(A3); BRA 39fc`
- `39f8`: `MOVEA.L 12(A3),A0` (→`39fc`)
- `39fc`: `CMPI.B #73,D2; BEQ 3a1e`
- `3a04`: `CMPI.B #78,D2; BEQ 3a52` (아니면 TRAP `3a0c`)
- `3a0e`: `MOVE.W (A3),D0; JSR (A1)` (계산된 호출)
- `3a12`: `MOVE.W D0,(A3); MOVE.L A0,6(A3); ANDI.B #fe,CCR; RTS` (C=Clear 생산)
- `3a1e`: `ADDQ.W #1,16(A3); MOVE.W (A3),D0; MOVE.W 2(A3),D2; MOVE.W D7,-(A7); BSR 386e`
- `3a2e`: `MOVE.W D1,4(A3); MOVE.W D3,2(A3); JSR (A1)` (계산된 호출)
- `3a38`: `MOVE.W (A7)+,D7; MOVE.L A0,12(A3); MOVE.W D0,(A3); CMPI.B #0,(A0); BNE 3a4c`
- `3a48`: `MOVE.W D7,16(A3)` (→`3a4c`)
- `3a4c`: `ANDI.B #fe,CCR; RTS` (Clear 생산)
- `3a52`: `MOVE.W 16(A3),D4; ADDQ.W #1,D4; MOVE.W D4,16(A3); BSR 37e2` (경계 callee)
- `3a60`: `MOVE.W (A3),D0; LEA 3650(PC),A0; JSR (A1)` (계산된 호출)
- `3a68`: `MOVE.W D0,(A3); ANDI.B #fe,CCR; RTS` (Clear 생산)
- `3a70`: `LEA 104cd6.L,A3; BSR 3950`
- `3a7a`: `BSR 396e`
- `3a7e`: `BCC 3a7a` (carry 소비; `396e` 반환 C)
- `3a80`: `RTS`

**C1 palette slot 참조 `8ebe` 19**
- `8ebe`: `CMPI.B #4,1d(A6); BCS 8ecc` (무부호. 실패 시 TRAP `8ec8`)
- `8ecc`: `LEA 108000.L,A5; LEA -326e(A5),A1; BTST #0,D1; BNE 8f10` (A1=`104d92`. BTST Dn은 bit 0)
- `8ede`: `MOVE.W D0,D7; ANDI.W #ff,D7; LSL.W #4,D7; ADDQ.W #4,D7; MOVE.W 2(A1,D7.W),D6; CMP.W D7,D6; BEQ 8f10` (bucket head=`A1+16×key.B+4`)
- `8ef2`: `LEA (A1,D6.W),A2; CMP.W a(A2),D0; BNE 8f08`
- `8efe`: `BTST #0,f(A2); BEQ 8f94`
- `8f08`: `MOVE.W 2(A2),D6; CMP.W D7,D6; BNE 8ef2` (원형 목록 순회, 상한 없음)
- `8f10`: `MOVE.W #1000,D7; MOVE.W 2(A1,D7.W),D6; LEA (A1,D6.W),A2; CMP.W D7,D6; BNE 8f84` (빈 목록 head `A1+1000`)
- `8f22`: `MOVE.B #ff,14(A6); BTST #2,10f000.L; BEQ 8f6a` (slot 부족)
- `8f34`: `MOVE.W D0,D1; ANDI.W #1ff,D1; MOVE.W D1,-(A7); LSR.W #1,D0; ADDI.W #100,D0; MOVE.W D0,-(A7); LEA 8f6c(PC),A0; JSR 3902` (경계 callee)
- `8f4e`: `MOVEA.L A7,A0; MOVEQ #-1,D3; MOVEQ #2,D4; JSR 36ba` (경계 callee)
- `8f5a`: `ADDQ.W #2,A7; MOVEA.L A7,A0; MOVEQ #-1,D3; MOVEQ #3,D4; JSR 36ba` (경계 callee)
- `8f68`: `ADDQ.W #2,A7` (→`8f6a`)
- `8f6a`: `RTS`
- `8f84`: `MOVE.W D0,a(A2); MOVE.W D0,c(A2); BSET #7,D1; MOVE.B D1,f(A2)` (→`8f94`. BSET Dn은 bit 7)
- `8f94`: `CMPI.W #ffff,8(A2); BEQ 8fa2`
- `8f9e`: `ADDQ.W #1,8(A2)` (→`8fa2`. 참조 수)
- `8fa2`: `MOVE.W D0,D1; MOVE.W D6,D0; MOVE.W D1,D4; ANDI.W #ff,D4; LSL.W #4,D4; ADDQ.W #4,D4; LEA (A1,D4.W),A4; CMP.W 2(A4),D0; BEQ 8fdc`
- `8fbc`: `MOVE.W (A2),D2; MOVE.W 2(A2),D3; MOVE.W D2,(A1,D3.W); MOVE.W D3,2(A1,D2.W); MOVE.W 2(A4),D3; MOVE.W D0,(A1,D3.W); MOVE.W D3,2(A2); MOVE.W D4,(A2); MOVE.W D0,2(A4)` (→`8fdc`. 양방향 목록에서 떼어 bucket head 뒤에 넣음)
- `8fdc`: `LSR.W #4,D0; MOVEQ #0,D2; MOVE.B 1d(A6),D2; MOVE.B D0,19(A6,D2.W); MOVE.B D0,14(A6); ADDQ.B #1,D2; MOVE.B D2,1d(A6); RTS` (`8fe0..8ff2`는 이 block 안)

**C5 `443d2` 1**
- `443d2`: `MOVEQ #0,D2; MOVE.B D1,D2; ASR.L #8,D0; MOVE.L D0,D1; ADD.W D2,D2; LEA 4419e(PC),A0; MULS.W (A0,D2.W),D0; MULS.W -80(A0,D2.W),D1; RTS` (MULS: 부호 16×16→32)

**결과 비교 `e5086` 15**
- `e5086`: `MOVE.W #ffff,D0; MOVE.W D0,D1; MOVE.W 7c(A6),D2; LEA 10fdb6.L,A0; CMPI.B #0,(A0,D2.W); BEQ e5112`
- `e50a0`: `LEA 10de14.L,A0; LEA 10de1c.L,A1; TST.W 7c(A6); BEQ e50c0`
- `e50b4`: `LEA 10de1c.L,A0; LEA 10de14.L,A1` (→`e50c0`)
- `e50c0`: `MOVEM.L A0-A1,-(A7); JSR e6496` (경계 callee)
- `e50ca`: `SUBQ.W #1,D0; MOVEM.L (A7)+,A0-A1; CMPI.W #a,D1; BCC e5112` (무부호)
- `e50d8`: `MOVEQ #1,D2; TST.W 7c(A6); BEQ e50e4`
- `e50e2`: `MOVEQ #0,D2` (→`e50e4`)
- `e50e4`: `LEA 10fdb6.L,A2; CMPI.B #0,(A2,D2.W); BEQ e5112`
- `e50f4`: `MOVE.L (A1),D2; CMP.L (A0),D2; BCS e5112; BNE e510e` (묶음: `e50fc`. 무부호 LONG)
- `e5100`: `TST.W 7c(A6); BEQ e5112`
- `e5108`: `ADDQ.W #1,D1; BRA e5112`
- `e510e`: `ADDQ.W #1,D0; ADDQ.W #1,D1` (→`e5112`)
- `e5112`: `CMPI.W #a,D1; BCS e511e` (무부호)
- `e511a`: `MOVE.W #3e7,D0` (→`e511e`)
- `e511e`: `RTS`

**node callback `e5120`(+`e5168` `e5196` `e51ac` `e51d0` `e51e6` `e523c` `e525a`) 38**
- `e5120`: `LEA e4f9e(PC),A0; JSR 8da2` (palette_bind)
- `e512a`: `JSR 48296` (U01)
- `e5130`: `MOVEA.L #e5724,A0; MOVE.W #0,D0; JSR 28ae` (자식 `e5724`)
- `e5140`: `MOVE.W #1,7c(A6); BSR e5086`
- `e514a`: `MOVE.W D0,84(A6); MOVE.W #0,7c(A6); BSR e5086`
- `e5158`: `MOVE.W D0,82(A6); MOVE.W #1e,7a(A6); MOVE.L #e5168,(A6)` (→`e5168`)
- `e5168`: `SUBQ.W #1,7a(A6); BEQ e5172` (callback 진입)
- `e5170`: `RTS`
- `e5172`: `MOVE.W #1a8c,D0; JSR 3af8`
- `e517c`: `MOVEA.L #e5680,A0; MOVE.W #0,D0; JSR 28ae` (자식 `e5680`)
- `e518c`: `CLR.B 62(A6); MOVE.L #e5196,(A6)` (→`e5196`)
- `e5196`: `TST.B 62(A6); BNE e51a0` (callback 진입. 자식이 `62`를 세움)
- `e519e`: `RTS`
- `e51a0`: `MOVE.W #1e,7a(A6); MOVE.L #e51ac,(A6)` (→`e51ac`)
- `e51ac`: `SUBQ.W #1,7a(A6); BEQ e51b6` (callback 진입)
- `e51b4`: `RTS`
- `e51b6`: `MOVEA.L #e5614,A0; MOVE.W #0,D0; JSR 28ae` (자식 `e5614`)
- `e51c6`: `CLR.B 62(A6); MOVE.L #e51d0,(A6)` (→`e51d0`)
- `e51d0`: `TST.B 62(A6); BNE e51da` (callback 진입)
- `e51d8`: `RTS`
- `e51da`: `MOVE.W #f,7a(A6); MOVE.L #e51e6,(A6)` (→`e51e6`)
- `e51e6`: `SUBQ.W #1,7a(A6); BEQ e51f0` (callback 진입)
- `e51ee`: `RTS`
- `e51f0`: `MOVEA.L #e5324,A0; MOVE.W #0,D0; JSR 28ae` (자식 `e5324`, U02 밖)
- `e5200`: `MOVE.L A0,-(A7); MOVEA.L #e5324,A0; MOVE.W #0,D0; JSR 28ae`
- `e5212`: `MOVEQ #0,D0; MOVEQ #1,D1; MOVE.L 10de14.L,D2; CMP.L 10de1c.L,D2; BCC e5228` (무부호)
- `e5226`: `EXG D0,D1` (→`e5228`)
- `e5228`: `MOVE.W D0,7c(A0); MOVEA.L (A7)+,A1; MOVE.W D1,7c(A1); CLR.B 62(A6); MOVE.L #e523c,(A6)` (→`e523c`)
- `e523c`: `CMPI.B #2,62(A6); BEQ e5248` (callback 진입)
- `e5246`: `RTS`
- `e5248`: `MOVE.W #14,7a(A6); MOVE.W #19c0,86(A6); MOVE.L #e525a,(A6)` (→`e525a`)
- `e525a`: `CMPI.W #19cf,86(A6); BGE e5272` (callback 진입. 부호)
- `e5264`: `ADDQ.W #1,86(A6); MOVE.W 86(A6),D0; JSR 3af8`
- `e5272`: `SUBQ.W #1,7a(A6); BEQ e527c`
- `e527a`: `RTS`
- `e527c`: `MOVE.W #19c0,D0; JSR 3af8`
- `e5286`: `JSR 48256` (경계 callee)
- `e528c`: `JMP 2a00` (자기 삭제)

**자식 callback `e5614`(+`e5626`) 6**
- `e5614`: `MOVE.W #4,2e(A6); MOVE.W #f,32(A6); MOVE.L #e5626,(A6)` (→`e5626`)
- `e5626`: `MOVE.W 2e(A6),D0; LSL.W #5,D0; ADD.W 32(A6),D0; ADDI.W #7000,D0; LEA e4ffc(PC),A0; LEA e84c8.L,A1; JSR 3a70` (callback 진입)
- `e5644`: `SUBQ.W #1,32(A6); MOVE.W 2e(A6),D0; LSL.W #5,D0; ADD.W 32(A6),D0; ADDI.W #7000,D0; LEA e4fd8(PC),A0; LEA e84c8.L,A1; JSR 3a70`
- `e5666`: `CMPI.W #5,32(A6); BNE e567e`
- `e5670`: `MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00` (부모 신호 후 자기 삭제)
- `e567e`: `RTS`

**자식 callback `e5680`(+`e56a0`) 6**
- `e5680`: `MOVE.W #708f,D0; LEA e4fd8(PC),A0; LEA e84c8.L,A1; LEA 10ddfa.L,A3; JSR 3950`
- `e569a`: `MOVE.L #e56a0,(A6)` (→`e56a0`)
- `e56a0`: `LEA 10ddfa.L,A3; JSR 396e` (callback 진입)
- `e56ac`: `BCC e56be` (carry 소비; `396e` 반환 C)
- `e56b0`: `MOVEA.L c(A6),A0; ST.B 62(A0); JMP 2a00`
- `e56be`: `RTS`

**자식 callback `e5724`(+`e5794`), `e579c`·`e57a4`(+`e57f0`) 17**
- `e5724`: `MOVEA.L #e579c,A0; MOVE.W #0,D0; JSR 28ae`
- `e5734`: `MOVE.W #0,7e(A0); MOVEA.L #e57a4,A0; MOVE.W #0,D0; JSR 28ae`
- `e574a`: `BSET #0,15(A0); MOVE.W #4000,7e(A0); MOVEA.L #e579c,A0; MOVE.W #0,D0; JSR 28ae`
- `e5766`: `BSET #0,15(A0); MOVE.W #8000,7e(A0); MOVEA.L #e57a4,A0; MOVE.W #0,D0; JSR 28ae`
- `e5782`: `MOVE.W #c000,7e(A0); MOVE.W #4000,7e(A6); MOVE.L #e5794,(A6)` (→`e5794`)
- `e5794`: `SUBI.W #100,7e(A6); RTS` (callback 진입)
- `e579c`: `MOVE.W #0,D0; BRA e57a8` (자식 callback 진입)
- `e57a4`: `MOVE.W #1,D0` (자식 callback 진입, →`e57a8`)
- `e57a8`: `MOVE.W #22b,20(A6); LEA e583c(PC),A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c` (interpreter)
- `e57c4`: `MOVE.W #35f,D0; MOVE.B #0,D1; JSR 8ebe`
- `e57d2`: `CLR.L 2e(A6); MOVE.L #1800000,32(A6); MOVE.W #0,68(A6); MOVE.W #0,1e(A6); MOVE.L #e57f0,(A6)` (→`e57f0`)
- `e57f0`: `JSR 43e34` (callback 진입, F3a)
- `e57f6`: `MOVEA.L c(A6),A0; MOVE.W 7e(A0),D1; ADD.W 7e(A6),D1; BMI e583a` (N=합 WORD bit15)
- `e5806`: `LSR.W #8,D1; MOVE.W D1,-(A7); MOVE.L #ffff,D0; JSR 443d2`
- `e5816`: `LSR.W #8,D1; MOVE.B D1,12(A6); MOVE.W (A7)+,D1; MOVE.L #8800,D0; JSR 443d2`
- `e582a`: `LSR.L #8,D0; ADDI.W #a0,D0; MOVE.W D0,2e(A6); JSR 49fc6` (interpreter)
- `e583a`: `RTS`

## 구현 범위와 규약

- routing 10 범위(위 표). 짝수 PC 792개 중 block 시작 133, 내부 659(묶인 PC `e50fc` 포함). 내부 PC 직접 진입은 `unsupported animation objects u02 PC`다. TRAP·`8eca`·문자열 바이트는 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤)다.
- **carry 소비 block 2개**: `3a7e`(`396e`), `e56ac`(`396e`). Unknown이면 `objects u02 caller requires known carry`.
- **known carry 생산 block 4개**: Set `398c`, Clear `3a12` `3a4c` `3a68`(모두 ORI/ANDI CCR 뒤 RTS까지 같은 block). `396e`의 모든 반환이 이 넷 중 하나다(경계 callee·TRAP 경로는 반환하지 않음).
- **FLOW_ONLY 32개**(C 보존): `396e` `39f8`(MOVEA), `3a70` `3a7a`(LEA/BSR), `3a7e`, `3a80`, `8ecc`(LEA·BTST Dn), `8efe`(BTST 메모리), `8f6a`, `e50b4`(LEA), `e50c0`(MOVEM·JSR), `e511e`, `e5120` `e512a`, `e5170` `e519e` `e51b4` `e51d8` `e51ee` `e5246` `e527a`(RTS), `e5226`(EXG), `e5286` `e528c`, `e5670` `e56b0`(MOVEA·ST·JMP), `e567e` `e56a0` `e56ac` `e56be`, `e57f0` `e583a`. 그 밖(MOVE/MOVEQ/CLR/TST/CMP/CMPI/ADD/ADDQ/ADDI/SUBQ/SUBI/LSL/LSR/ASR/MULS/ANDI/SEQ/EXT, `ADDQ.W An` block `39ae` `8f68`, BSET+MOVE block)은 Unknown이다(기존 관례).
- [F] **반환 C 소비자 조사**: fixed ROM의 `JSR/BSR` 호출자 중 바로 뒤에서 C를 쓰는 곳은 `396e`의 두 곳(`3a7e` `e56ac`)뿐이다. `8ebe`(610곳), `443d2`(89곳), `3a70`(10곳), `3950`(2곳), `e5086`(2곳)의 호출자는 C를 쓰지 않는다. 따라서 MOVE로 끝나는 반환(`8fdc` 등)을 known Clear로 둘 필요가 없다.
- 부호 비교: `BGE`(`e525a` CMPI.W)는 부호 WORD 비교, `BCS`/`BCC`(`8ebe` `e50ca` `e5112` `e5212` `e50f4`)는 무부호, `BMI`(`e57f6`)는 ADD.W 결과 bit15다.
- 반복: `8ef2..8f08` bucket 순회, `3976..39d8` 문자열 순회, `3a7a..3a7e` 반복은 원본대로 두고 block budget(1,000,000)만 한계다.
- 스택: `3a1e`/`3a38`(WORD push/pop D7), `8f34`(WORD 2개 push, `8f5a`/`8f68`에서 `ADDQ.W #2,A7`), `e50c0`/`e50ca`(MOVEM.L A0-A1: push A1 다음 A0, pop A0 다음 A1), `e5200`/`e5228`(LONG A0), `e5806`/`e5816`(WORD D1)은 모두 work RAM 스택이다.
- 홀수 주소 WORD/LONG 접근과 work RAM 밖 쓰기는 기존 checked 오류(원본은 주소 오류·ROM 쓰기)다. port 쓰기는 U02 자체에 없다(callee 몫).
- I/O: RAM 절대 주소 `104cd6`(문자열 기록), `104d92..`(palette slot 표, `A5-326e`), `10f000`(BTST bit2, [I] debug flag), `10fdb6`(BYTE 2개), `10de14`·`10de1c`(LONG), `10ddfa`(문자열 기록). d16(A6) `14` `19..` `1d` `2e` `32` `62` `68` `7a` `7c` `7e` `82` `84` `86`, `c(A6)`=부모 node.
- 회귀 탐침: [F] 기존 `engine/tests`·`tools/*animation_machine*`에서 U02 범위 안 PC를 "outside" 탐침으로 쓰는 곳은 없다(검색한 일치는 자료 값 `0x39de` `0x8f9f` `0x8ec3`, 관측 도구의 범위 끝 `0x8ebe`뿐이다). 교체할 탐침이 없으므로 다음 빈 탐침 `5f040+`는 쓰지 않는다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, F2 프레임 패스 Unicorn, 142 seed)에서 U02 callback node 실행: `e5120` 11, `e5168` 319, `e5196` 198, `e51ac` 319, `e51d0` 55, `e5614` 11, `e5626` 55, `e5680` 11, `e56a0` 187, `e5724` 11, `e5794` 891, `e579c` 22, `e57a4` 22, `e57f0` 3,564. 모두 seed 90·91·118~126이다. TB 포함 기준으로 133 block 중 75개가 자연 도달한다. 미도달(fixture 필요) 58개: `3976`(TB 안) `39a4` `39ae` `39b4` `39be` `39c8` `39d8` `39e4` `39ea` `39f8` `39fc` `3a04` `3a1e` `3a2e` `3a38` `3a48` `3a4c` `3a52` `3a60` `3a68` `8f22` `8f34` `8f4e` `8f5a` `8f68` `8f6a` `8fa2` `e50a0` `e50b4` `e50c0` `e50ca` `e50d8` `e50e2` `e50e4` `e50f4` `e5100` `e5108` `e510e` `e511e` `e51da` `e51e6` `e51ee` `e51f0` `e5200` `e5212` `e5226` `e5228` `e523c` `e5246` `e5248` `e525a` `e5264` `e5272` `e527a` `e527c` `e5286` `e528c` `e5670`.
- [I] `e5086`의 `e50a0` 이후가 자연에 없는 것은 seed의 `10fdb6` slot flag가 0이기 때문이다(D0=D1=`ffff`→`3e7`).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 133 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 block 값, 그 밖 Unknown), 소비 block의 Unknown 오류, zero-step, 내부 659 PC 정확한 오류, TRAP 3개 stop·rollback, 홀수 PC, 경계 callee 6개 오류, 계산된 호출의 홀수·미연결 대상 오류. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, 합성 ROM 자료)로 비교한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`): 이전에 일치하던 pass(U01 뒤 7,736)가 모두 그대로 일치하고, 완주 seed는 39로 유지된다. 90·91·118~126은 frame 0~28이 새로 일치하고 frame 29의 `e5680` node에서 U03 경계 `e84d6`으로 rollback되어야 한다.

## 미확인·범위 밖

1. [I] `3950`/`396e`/`3a70`은 화면 문자열 출력 커서(`%s`·`%x` 서식, `\` 제어 코드는 `386e`), `8ebe`는 palette slot 참조 계수(256 bucket 해시 + 빈 목록, 부족 시 debug "palette over"), `443d2`는 각도 D1.B의 sin/cos 곱, `e5086`은 두 LONG 점수 비교로 순위를 내는 함수, `e5120` 계열은 결과 화면 연출로 보인다. 게임 의미는 미확인이다.
2. [U] `383e`(10진 수 해석), `37e2`(자리 출력), `36ba`, `3902`, `48256`, `e6496`과 자식 `e5324`는 U02 밖이다.
3. [U] `4419e` 표와 `e583c` 표의 의미(값은 ROM에 있고 읽기는 bus가 막는다). `e84c8`의 `D1.B≥10` 경로(`e84d6`)는 U03이다.

작업자 scratch: 세션 scratchpad `f4u02/`(`u02.py` block·범위·SHA 계산, `reach.py`, `callers.txt`; 저장소 밖).
