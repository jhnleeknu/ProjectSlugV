# 객체 callback F4 U06: script 객체 `e73f8`·선택 객체 `e7792` 계열·bank 목록 객체 `eb7b6`·C3 `49be0` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U06 행과 그 "메인 결정"이다. 단위 형식과 규약은 U01 계약(`animation-machine-objects-u01-contract.md`, SHA256 `5f4a42b5f3095b24374ce129d91e67bffadb537033651fe0cb1d75fbfea36b3b`)과 U05 계약(`animation-machine-objects-u05-contract.md`, SHA256 `77fd4062f3935d0e8b2989ad65bed395f43fa7bd37f33309c7a29fa9f512dafc`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee는 실행부 없는 경계(`unsupported animation machine PC`)다.
- 결정 7(변경): 메인 결정: guard 제거. 근거 `animation-machine-pvc-banks.md`와 `observe_animation_machine_pvc_banks.py`의 native 관측(`artifacts/animation_machine_pvc_banks_native/observation.json` SHA256 `613bd4648d7ed3035620ad1949e1be4c94e4e866635a788a423df6c9650a65fe`): bank 4/5(`400000`/`500000`)는 ROM 8 MiB 안이며 93 entry 전부 정상 포인터 표와 0 종결 목록을 읽고, 시드 58·59는 120 frame을 완주한다. PVC 쓰기 4곳(`eba5c` `eba62` `eba8c` `eba94`)은 공용 PVC 모델(`am_write`→`pvc_effects`→`bank_base`)을 거치는 평범한 WORD 쓰기이며 쓰기 시점 검사가 없다. 어떤 bank도 쓰기에서 오류가 아니고, 8 MiB 밖(`bank_base+offset+size>800000`)을 읽는 순간은 공용 program bus의 `reached program bank physical span outside ROM`, 홀수 목록 주소는 `program bus requires even WORD/LONG address`다. 오류 문자열 `objects u06 PVC bank outside model`은 삭제한다.
- U01/U05 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다(U06에는 없음). `MOVE.x`는 C를 지운다(필요한 소비자가 있을 때만 known 생산으로 둔다). `ADDQ`/`ADDA` An block은 Unknown이다. `JSR (An…)`은 live 주소를 routing으로 보내고 generic 오류를 쓴다. checked 오류는 경계에서 낸다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U06의 코드와 fixed 자료는 `<100000`에 있으므로 CPU 주소와 file offset이 같다. banked window 자료(`200004`)는 아래 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u06`(HEAD `9f2996a`, U01+U02+U03+U05 WIP, `engine/src/animation_machine.cpp` SHA256 `ea9490e2fdb44c49e0cfa87db59bcb23e2615067345fe739e91a29f63c32dad0`)을 참조했다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u06/u06.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U06은 함수 17개(진입 `49be0` `e73f8`(+설치 callback `e7426`) `e74b6` `e74da` `e74f2` `e7546` `e7792`(+`e77ac`) `e77e4` `e780a` `e7830` `e7850` `e788c`(+`e78a8`, `e78d8`(+`e78f4`)) `eb7b6`(+`eb81e`) `eba3e`)의 **block 시작 135개**다. 코드 6 범위, 1,350바이트, 320명령이며 미해독·TRAP·묶인 분기·PC 상대 점프 표는 없다. routing 짝수 PC는 675개, 내부 PC는 540개다.
- [F] **범위 문서 133과의 차이(+2)**: 설치 callback 진입 `e78f4`(`e78ee MOVE.L #e78f4,(A6)`)와 `eb81e`(`eb818 MOVE.L #eb81e,(A6)`)를 block 시작으로 센다(U05 `b971a`와 같은 관례). 범위 스크립트는 자연 재생에서 callback으로 관측된 진입만 함수로 나눴고 이 둘은 관측되지 않아 fall-through로 묶였다. 나머지 133개는 범위 스크립트 본문 집합(`f4scope/plan.py` `blocks(units[5].fns)`)과 같다.
- [F] 경계(실행부 없음) callee 5개: `3ed2`(`e743a`), `e7562`(`e7462` `e7478` `e7486` BSR), `eb9ba`(`eb846` `eb85a`), `eb9e4`(`eb86e` `eb888`), `101c`(`eb980` `eb992`). 범위 문서 "경계 callee 5"와 같다.
- [F] 간접 `e74ac JSR (A0,D0.W)`: script 명령 처리기. 대상은 live `A0+sext(D0.W)`를 routing으로 보낸다. ROM script `e7570..e7752`의 처리기는 `e74f2` `e74b6` `e7546`(U06), `e74f8`(U06 밖, 점프 표 `e7504` 2 entry), `e7562`(U06 밖 경계)다. U06 밖 대상은 `unsupported animation machine PC`다.
- [F] 기존 실행부로 나가는 출구: input `8da2..8e48`(`8da2`), `49c20`, `4836e`(known C), sprite `16ed2` `16ea4`, U02 `8ebe`, `8ff4`, interpreter `49f8c` `49fc6`(known C), F3a `43e34`, transition `35a2`, `3918`(그 안의 `JSR (A1)`=`e84c8`), U05 `c6a96`.
- [F] **PVC bank guard.** `eba3e`는 `80(A6)` LONG의 하위 3bit `n`으로 `2ffff2`에 `(n+1)<<12`를 쓴다(bank base `200000+n*100000`). ROM 표 `eba9e`의 93 entry는 모두 `n`=2(36개) 또는 3(57개)이다(bank base `400000`/`500000`). native 관측 모델(`tools/observe_animation_machine_scheduler.py`)은 base `200000`/`300000`만 두고 그 밖은 쓰기 직후 `invalid-memory-access`(kind `bank`)로 멈춘다(seed 58·59 frame 0, `eba5c`, base `400000`). 기존 C++ PVC 모델(`am_write`→`pvc_effects`)은 같은 쓰기를 오류 없이 받아 `bank_base`=`400000`로 바꾸고, program bus는 physical `400004`가 ROM 8 MiB 안이라 읽기도 성공한다. 결정 7에 따라 U06의 PVC 쓰기 4곳은 쓰기 결과 base가 `200000`/`300000`이 아니면 쓰기 전에 checked 오류 `objects u06 PVC bank outside model`을 낸다(아래 결정 2). **[폐기: 마지막 문장과 결정 2의 guard는 결정 7(변경)으로 제거됐다. native 모델도 `observe_animation_machine_pvc_banks.py`의 `PvcMachine`이 모든 bank를 두므로 위 `invalid-memory-access`는 스케줄러 Machine 한정이다.]**
- [F] 자연 seed(F2 프레임 패스 기본 120 frame, `f4scope/dyn`): 108·109가 `e73f8` `e7792` `e77e4` `e780a` `e7830` `e7850`(frame 0) 뒤 `e7426` `e77ac` `e78a8`을 매 frame 실행하고, 58·59가 frame 0에 `eb7b6`을 실행해 `eba5c`에서 native guard로 멈춘다. TB 시작 기준 58 block이 자연 도달한다. U06 뒤 완주 seed는 52→56(새 58 59 108 109)이 되어야 한다(U04 미병합 기준; 범위 문서의 58은 U04의 24·25 포함). **[변경: 58·59는 guard 정지가 아니라 120 frame 완주 일치이며(pvc-banks 관측), 완주 seed는 52→56.]**
- [F] `49be0..49bf2`는 input U6 실행부 범위(`49ab4..49bca`, `49c20..49c38`, `49c66..49c6c`, `49d88..49f8c`)와 겹치지 않는다. 사이의 `49bca..49be0`(함수 `49bca`)과 `49bf2..49c20`(함수 `49bf2`+WORD 표 `49c00`)은 어느 실행부에도 없다. input 계약은 `49be0`을 "U6 closure 밖, routing하지 않음"으로 적었다(`animation-machine-input-u6-contract.md` 161행). `e73f8`은 input 범위 `e73f2..e73f8`의 바로 뒤다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 정정(133→135).** 설치 callback 진입 `e78f4` `eb81e`를 block 시작으로 센다(권고, U05 `b971a` 관례). 범위 문서는 고치지 않는다.
2. **PVC bank guard의 C++ 형태.** **[폐기 — 결정 7(변경)]** 이 항목이 권고하던 쓰기 전 base 검사와 `objects u06 PVC bank outside model`은 구현하지 않는다. U06 helper `ou6_pvc`는 `am_write(c,address,2,value&65535U)`뿐이며 공용 `am_write`/`pvc_effects`는 바꾸지 않는다. 8 MiB 밖의 banked 읽기는 공용 program bus 오류가 그대로 낸다. (원 권고 기록: 권고: U06 실행부 안의 helper가 `2ffff0`/`2ffff2` WORD 쓰기 4곳(`eba5c` `eba62` `eba8c` `eba94`)마다 MAME 식(`base=100000+((ff8>>8)|(ff…)
3. **간접 `e74ac`.** 권고: `JSR (A0,D0.W)`는 live `A0+sext(D0.W)`로 복귀 LONG `e74b0`을 쌓고 PC를 옮긴다. 대상 검사는 routing에 맡긴다(홀수면 `unaligned animation machine PC`, routing 밖이면 `unsupported animation machine PC`). `e74f8` `e7562`는 U06에서 구현하지 않는다(`e74f8`은 기록 지평 120 frame 안에서 실행되지 않았고, `e7562`는 경계 callee).
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u06.cpp`의 `animation_objects_u06_block`. 오류는 `unsupported animation objects u06 PC`, `objects u06 caller requires known carry`(메인 지시와 같음). PVC 전용 문자열은 없다(결정 7 변경).

## 원본 바이트 근거

[F] 코드 6 범위 합계 1,350바이트. 범위 순서로 이어 붙인 SHA256 `6ef5a9a9f5b19dbf6d96cdd1267ceaf4dae5e065ace15d59f9e30844f4bda698`(바이트 전체는 scratch `u06.py B` 출력과 ROM에서 재생성).

| CPU 범위 | 내용 |
| --- | --- |
| `49be0..49bf2` | C3 `49be0`(입력 slot 선택) |
| `e73f8..e74f8` | callback `e73f8`/`e7426`, script 처리기 `e74b6` `e74da` `e74f2` |
| `e7546..e7562` | script 처리기 `e7546` |
| `e7792..e7946` | callback `e7792`/`e77ac`, `e77e4` `e780a` `e7830` `e7850`, `e788c`/`e78a8`, `e78d8`/`e78f4` |
| `eb7b6..eb9ba` | callback `eb7b6`/`eb81e` |
| `eba3e..eba9e` | bank 목록 길이 `eba3e` |

- [F] 범위 밖 이웃: `49bca`·`49bf2`(다른 함수), `e73f2..e73f8`(input 실행부), `e74f8..e7546`(script 처리기 `e74f8`와 점프 표), `e7562..e7570`(경계 `e7562`), `e7570..e7792`(script 자료와 LONG 표 `e7752`), `e7946`(다른 callback), `eb9ba..eba3e`(경계 `eb9ba` `eb9e4`), `eba9e`(표).
- [F] 자료(모두 live bus로 읽는다):
  - script `e7570..e7752`(`e7410 MOVE.L #e7570,76(A6)`): (지속 WORD, 처리기 offset WORD, 처리기별 인자 WORD)의 열. 끝 `e774e`는 지속 `ffff`, 처리기 `e7562`다. fixed ROM.
  - `e7392`/`e73c2` LONG 표 12개씩(`e74da`가 `-8000(A5)`=BYTE `100000`이 3이면 `e7392`, 아니면 `e73c2`; `e74be MOVEA.L (A1,D0.W)`의 index는 script 인자 `0..2c`). fixed ROM.
  - `e7752` LONG 표 16개(`e77b4`, index `4*(WORD AND f)`). fixed ROM.
  - `eba9e` 표: 8바이트 entry(LONG `80(A6)`, WORD `84(A6)`, WORD `86(A6)`), LONG 0이 끝(`ebd86`). 93 entry. `eb7b6`이 개수를 세고(`D0`=93) `eba12`가 `7c(A6)×8`로 고른다. fixed ROM.
  - `e6ed2`(`8da2` 인자), `e7a70` `e7a5c` `e7a46`(`49f8c` 인자 `A1`): U06은 주소만 넘긴다.
  - banked: `eba6e LEA 200004.L,A1; MOVEA.L (A1,D2.W),A1`(D2.W=`((80(A6) AND ffff)>>3)<<2`, 0..`7ffc`)과 그 LONG 목록(`eba7c TST.L (A1)`, LONG 0까지). 새로 고른 live bank로 읽는다.
- [F] I/O: PVC WORD 쓰기 4곳 `eba5c MOVE.W D1,2ffff2.L`, `eba62 MOVE.W #0,2ffff0.L`, `eba8c MOVE.W #1000,2ffff2.L`, `eba94 MOVE.W #0,2ffff0.L`. 각각 port 이벤트 1건(size 2)이다. RAM WORD `-7ff0(A5)`(`100010`)에 bank 번호를 두고 끝에 0으로 되돌린다.

## block 목록과 실행 의미

[F] 135 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)·`(An,Dn.W)`는 부호확장한다. `MOVE.B`/`MOVE.W`/`.B`·`.W` 연산은 나머지 bit를 보존한다. `-xxxx(A5)`는 `A5`(자연 `108000`) 기준이다.

**C3 `49be0` 3**
- `49be0`: `TST.B D0; BNE 49bec`
- `49be6`: `LEA 5726(A5),A0; RTS`
- `49bec`: `LEA 572c(A5),A0; RTS`

**callback `e73f8`(+`e7426`)와 script 처리기 33**
- `e73f8`: `LEA e6ed2(PC),A0; JSR 8da2`
- `e7402`: `MOVE.B #0,D0; LEA e73f2(PC),A0; JSR 49c20`
- `e7410`: `CLR.W 5e24(A5); MOVE.L #e7570,76(A6); CLR.W 7a(A6); MOVE.L #e7426,(A6)` (→`e7426`)
- `e7426`: `JSR 4836e` (callback 진입)
- `e742c`: `BCS e748a` (carry 소비; `4836e` 반환 C)
- `e7430`: `MOVEQ #-1,D0; TST.B 7d82(A5); BEQ e7440`
- `e743a`: `JSR 3ed2` (경계 callee)
- `e7440`: `MOVEQ #0,D7; BTST #0,D0; BEQ e744e`
- `e744a`: `OR.B -3355(A5),D7` (→`e744e`)
- `e744e`: `BTST #1,D0; BEQ e745a`
- `e7456`: `OR.B -334f(A5),D7` (→`e745a`)
- `e745a`: `ANDI.B #30,D7; BEQ e7466`
- `e7462`: `BSR e7562` (경계 callee)
- `e7466`: `TST.B 7d82(A5); BNE e748a`
- `e746e`: `CMPI.B #1,7db6(A5); BNE e747c`
- `e7478`: `BSR e7562` (경계)
- `e747c`: `CMPI.B #1,7db7(A5); BNE e748a`
- `e7486`: `BSR e7562` (경계)
- `e748a`: `TST.W 7a(A6); BEQ e74a2`
- `e7492`: `CMPI.W #ffff,7a(A6); BEQ e74a0`
- `e749c`: `SUBQ.W #1,7a(A6)` (→`e74a0`)
- `e74a0`: `RTS`
- `e74a2`: `MOVEA.L 76(A6),A0; MOVE.W (A0)+,7a(A6); MOVE.W (A0)+,D0; JSR (A0,D0.W)` (간접, 결정 3)
- `e74b0`: `MOVE.L A0,76(A6); BRA e748a`
- `e74b6`: `MOVE.W (A0)+,D0; MOVE.L A0,-(A7); BSR e74da`
- `e74be`: `MOVEA.L (A1,D0.W),A0; LEA e84c8.L,A1; MOVE.W #70a6,D0; MOVE.W #800,D1; JSR 3918`
- `e74d6`: `MOVEA.L (A7)+,A0; RTS`
- `e74da`: `MOVE.B -8000(A5),D1; LEA e7392(PC),A1; CMPI.B #3,D1; BNE e74ec`
- `e74ea`: `RTS`
- `e74ec`: `LEA e73c2(PC),A1; RTS`
- `e74f2`: `MOVE.W (A0)+,5e24(A5); RTS`
- `e7546`: `MOVE.L A0,-(A7); MOVE.W #70a5,D0; MOVE.W #320,D1; MOVE.W #1f,D2; MOVE.W #6,D3; JSR 35a2`
- `e755e`: `MOVEA.L (A7)+,A0; RTS`

**선택 객체 `e7792` 계열 40**
- `e7792`: `JSR 16ed2`
- `e7798`: `MOVE.W #2b1,D0; MOVE.B #0,D1; JSR 8ebe`
- `e77a6`: `MOVE.L #e77ac,(A6)` (→`e77ac`)
- `e77ac`: `MOVEQ #0,D0; JSR 49be0` (callback 진입)
- `e77b4`: `MOVE.W (A0),D0; ANDI.W #f,D0; LEA e7752(PC),A1; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A1; MOVE.W #100,D0; JSR 49f8c`
- `e77d0`: `MOVE.W #ea,20(A6); JSR 43e34`
- `e77dc`: `JSR 49fc6`
- `e77e2`: `RTS`
- `e77e4`: `MOVE.W #2ae,D0; MOVE.B #0,D1; JSR 8ebe`
- `e77f2`: `MOVE.W #90,76(A6); MOVE.W #10,76(A6); MOVE.L #0,78(A6); BRA e786c`
- `e780a`: `MOVE.W #2af,D0; MOVE.B #0,D1; JSR 8ebe`
- `e7818`: `MOVE.W #a0,76(A6); MOVE.W #20,76(A6); MOVE.L #800,78(A6); BRA e786c`
- `e7830`: `MOVE.W #2b0,D0; MOVE.B #0,D1; JSR 8ebe`
- `e783e`: `MOVE.W #40,76(A6); MOVE.L #1000,78(A6); BRA e786c`
- `e7850`: `MOVE.W #2b2,D0; MOVE.B #0,D1; JSR 8ebe`
- `e785e`: `MOVE.W #80,76(A6); MOVE.L #1800,78(A6)` (→`e786c`)
- `e786c`: `JSR 16ed2`
- `e7872`: `MOVE.W #ea,20(A6); MOVEA.L #e7a70,A1; MOVE.W #100,D0; JSR 49f8c`
- `e7888`: `BRA e78a2`
- `e788c`: `MOVE.W #ea,20(A6); MOVEA.L #e7a5c,A1; MOVE.W #100,D0; JSR 49f8c` (`e792e`가 설치하는 callback 진입)
- `e78a2`: `MOVE.L #e78a8,(A6)` (→`e78a8`)
- `e78a8`: `JSR 43e34` (callback 진입)
- `e78ae`: `MOVEQ #0,D0; JSR 49be0`
- `e78b6`: `MOVE.W (A0),D0; AND.W 76(A6),D0; BNE e78d8`
- `e78c0`: `JSR 49fc6`
- `e78c6`: `MOVEQ #0,D0; MOVE.L 78(A6),D7; ADDI.W #ea,D7; JSR 16ea4`
- `e78d6`: `RTS`
- `e78d8`: `MOVE.W #ea,20(A6); MOVEA.L #e7a46,A1; MOVE.W #100,D0; JSR 49f8c` (`e790a`가 설치하는 callback 진입)
- `e78ee`: `MOVE.L #e78f4,(A6)` (→`e78f4`)
- `e78f4`: `JSR 43e34` (callback 진입, 범위 문서 밖 +1)
- `e78fa`: `MOVEQ #0,D0; JSR 49be0`
- `e7902`: `AND.W 76(A6),D0; BEQ e7910`
- `e790a`: `MOVE.L #e78d8,(A6)` (→`e7910`)
- `e7910`: `JSR 49fc6`
- `e7916`: `BCC e7934` (carry 소비; `49fc6` 반환 C)
- `e791a`: `MOVEQ #0,D0; JSR 49be0`
- `e7922`: `MOVE.W 2(A0),D0; AND.W 76(A6),D0; BNE e7934`
- `e792e`: `MOVE.L #e788c,(A6)` (→`e7934`)
- `e7934`: `MOVEQ #0,D0; MOVE.L 78(A6),D7; ADDI.W #ea,D7; JSR 16ea4`
- `e7944`: `RTS`

**bank 목록 객체 `eb7b6`(+`eb81e`) 56**
- `eb7b6`: `MOVEQ #0,D0; LEA eba9e(PC),A0` (→`eb7bc`)
- `eb7bc`: `ADDQ.W #1,D0; ADDQ.L #8,A0; TST.L (A0); BNE eb7bc`
- `eb7c4`: `MOVE.W D0,78(A6); MOVE.W #0,7c(A6); MOVE.W #0,7e(A6); MOVE.W #0,88(A6); MOVE.B #2,8a(A6); MOVE.W #8,D0; MOVE.W #0,D1; MOVE.B #0,D2; JSR c6a96`
- `eb7f2`: `LEA eba9e(PC),A0; MOVE.L (A0),80(A6); MOVE.W 4(A0),84(A6); MOVE.W 6(A0),86(A6); JSR eba3e(PC)`
- `eb80a`: `MOVE.W 84(A6),D0; MOVE.B #0,D1; JSR 8ebe`
- `eb818`: `MOVE.L #eb81e,(A6)` (→`eb81e`)
- `eb81e`: `MOVE.B #90,567e(A5); MOVE.B #ff,567f(A5); TST.W 76(A6); BNE eb83a` (callback 진입, 범위 문서 밖 +1)
- `eb832`: `MOVE.B -3346(A5),D0; BRA eb83e`
- `eb83a`: `MOVE.B -3340(A5),D0` (→`eb83e`)
- `eb83e`: `BTST #4,D0; BEQ eb852`
- `eb846`: `ADDQ.W #1,7e(A6); JSR eb9ba(PC)` (경계)
- `eb84e`: `BRA eb89a`
- `eb852`: `BTST #5,D0; BEQ eb866`
- `eb85a`: `SUBQ.W #1,7e(A6); JSR eb9ba(PC)` (경계)
- `eb862`: `BRA eb89a`
- `eb866`: `BTST #6,D0; BEQ eb880`
- `eb86e`: `MOVE.W #0,7e(A6); ADDQ.W #1,7c(A6); JSR eb9e4(PC)` (경계)
- `eb87c`: `BRA eb89a`
- `eb880`: `BTST #7,D0; BEQ eb89a`
- `eb888`: `MOVE.W #0,7e(A6); SUBQ.W #1,7c(A6); JSR eb9e4(PC)` (경계)
- `eb896`: `BRA eb89a`
- `eb89a`: `TST.W 76(A6); BNE eb8aa`
- `eb8a2`: `MOVE.B -3342(A5),D0; BRA eb8ae`
- `eb8aa`: `MOVE.B -3348(A5),D0` (→`eb8ae`)
- `eb8ae`: `BTST #0,D0; BEQ eb8ba`
- `eb8b6`: `ADDQ.W #1,46(A6)` (→`eb8ba`)
- `eb8ba`: `BTST #1,D0; BEQ eb8c6`
- `eb8c2`: `SUBQ.W #1,46(A6)` (→`eb8c6`)
- `eb8c6`: `BTST #3,D0; BEQ eb8d2`
- `eb8ce`: `ADDQ.W #1,42(A6)` (→`eb8d2`)
- `eb8d2`: `BTST #2,D0; BEQ eb8de`
- `eb8da`: `SUBQ.W #1,42(A6)` (→`eb8de`)
- `eb8de`: `TST.W 76(A6); BNE eb8ee`
- `eb8e6`: `MOVE.B -3340(A5),D0; BRA eb8f2`
- `eb8ee`: `MOVE.B -3346(A5),D0` (→`eb8f2`)
- `eb8f2`: `BTST #4,D0; BEQ eb92c`
- `eb8fa`: `ADDQ.W #1,88(A6); MOVE.W 86(A6),D0; CMP.W 88(A6),D0; BCC eb910` (block 안 C: `D0.W` ≥ `88(A6)` 무부호이면 분기)
- `eb90a`: `MOVE.W #0,88(A6)` (→`eb910`)
- `eb910`: `JSR 8ff4`
- `eb916`: `MOVE.W 84(A6),D0; ADD.W 88(A6),D0; MOVE.B #0,D1; JSR 8ebe`
- `eb928`: `BRA eb95a`
- `eb92c`: `BTST #5,D0; BEQ eb95a`
- `eb934`: `SUBQ.W #1,88(A6); BCC eb942` (block 안 C: 이전 값 0일 때만 borrow)
- `eb93c`: `MOVE.W 86(A6),88(A6)` (→`eb942`)
- `eb942`: `JSR 8ff4`
- `eb948`: `MOVE.W 84(A6),D0; ADD.W 88(A6),D0; MOVE.B #0,D1; JSR 8ebe`
- `eb95a`: `TST.W 76(A6); BNE eb96a`
- `eb962`: `MOVE.B -3341(A5),D0; BRA eb96e`
- `eb96a`: `MOVE.B -3347(A5),D0` (→`eb96e`)
- `eb96e`: `BTST #6,D0; BEQ eb9a0`
- `eb976`: `CMPI.B #1,8a(A6); BNE eb992`
- `eb980`: `MOVE.B #2,D0; MOVE.B D0,8a(A6); JSR 101c` (경계)
- `eb98e`: `BRA eb9a0`
- `eb992`: `MOVE.B #1,D0; MOVE.B D0,8a(A6); JSR 101c` (경계)
- `eb9a0`: `MOVEQ #0,D0; MOVE.L 80(A6),D7; MOVE.W 7e(A6),D0; LSL.L #8,D0; LSL.L #3,D0; ADD.L D0,D7; MOVEQ #0,D0; JSR 16ea4`
- `eb9b8`: `RTS`

**bank 목록 길이 `eba3e` 3**
- `eba3e`: `MOVE.L 80(A6),D1; MOVE.L D1,D2; ANDI.W #7,D1; LSR.W #3,D2; LSL.W #2,D2; MOVEQ #0,D3; MOVE.W D0,-(A7); MOVE.W D1,D0; MOVE.W D1,-7ff0(A5); ADDQ.W #1,D1; LSL.W #8,D1; LSL.W #4,D1; MOVE.W D1,2ffff2.L; MOVE.W #0,2ffff0.L; MOVE.W D0,D1; MOVE.W (A7)+,D0; LEA 200004.L,A1; MOVEA.L (A1,D2.W),A1` (→`eba78`. PVC 쓰기 2곳, banked 읽기)
- `eba78`: `ADDQ.W #1,D3; ADDQ.L #4,A1; TST.L (A1); BNE eba78`
- `eba80`: `SUBQ.W #1,D3; MOVE.W D3,7a(A6); MOVE.W #0,-7ff0(A5); MOVE.W #1000,2ffff2.L; MOVE.W #0,2ffff0.L; RTS` (PVC 쓰기 2곳)

## 구현 범위와 규약

- routing 6 범위: `49be0..49bf2`, `e73f8..e74f8`, `e7546..e7562`, `e7792..e7946`, `eb7b6..eb9ba`, `eba3e..eba9e`. 짝수 PC 675개 중 block 시작 135, 내부 540. 내부 PC 직접 진입은 `unsupported animation objects u06 PC`다. 경계(`3ed2` `e7562` `eb9ba` `eb9e4` `101c`), 간접 대상 `e74f8`, 범위 이웃은 routing 밖이므로 `unsupported animation machine PC`(stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- **carry 소비 block 2개**: `e742c`(BCS, `4836e`: input 실행부 `48378` Clear/`4837e` Set), `e7916`(BCC, `49fc6`: interpreter 실행부 known C). Unknown이면 `objects u06 caller requires known carry`.
- **known carry 생산 block 0개.** [F] `49be0`의 `TST.B`는 C를 지우지만, ROM의 `JSR 49be0` 39곳 바로 뒤 명령에 C 소비 Bcc는 없다(`MOVE.W` 31, `TST.W` 4, `MOVE.L` 2, `CLR.L` 1, `AND.W` 1). `eba3e`(2곳), `e74da`(1곳)의 호출 뒤도 C 소비가 없다. U06 callback의 반환 C는 scheduler가 쓰지 않는다(F2 소비자 없음).
- **FLOW_ONLY 47개**(C 보존): `49be6` `49bec` `e74ec`(LEA+RTS), `e73f8`(LEA PC+JSR), `e7426` `e743a` `e7792` `e77dc` `e786c` `e78a8` `e78c0` `e78f4` `e7910` `eb910` `eb942`(JSR), `e7462` `e7478` `e7486`(BSR), `e742c` `e7916`(소비 Bcc), `e744e` `eb83e` `eb852` `eb866` `eb880` `eb8ae` `eb8ba` `eb8c6` `eb8d2` `eb8f2` `eb92c` `eb96e`(Dn `BTST`+`BEQ`, Z만), `e7888` `eb84e` `eb862` `eb87c` `eb896` `eb928` `eb98e`(BRA), `e74a0` `e74ea` `e77e2` `e78d6` `e7944` `eb9b8`(RTS), `e74d6` `e755e`(`MOVEA.L (A7)+,A0`+RTS). 그 밖(MOVE/MOVEQ/MOVEA+MOVE 혼합/CLR/TST/CMP/CMPI/AND/ANDI/OR/ADD/ADDI/ADDQ/SUBQ/LSL/LSR, `ADDQ.L` An block `eb7bc` `eba78`, PVC block)은 Unknown이다.
- **block 안 C**: `eb8fa`(`CMP.W` 무부호), `eb934`(`SUBQ.W` borrow)는 같은 block의 결과로 분기하며 caller C와 무관하다. block 끝 C는 Unknown이다.
- 간접: `e74a2`는 `A0`을 WORD 두 번 읽은 뒤의 `A0`(+4)에 `sext(D0.W)`를 더한 대상으로 `JSR`한다(복귀 `e74b0`). `e74b0`은 처리기가 전진시킨 `A0`을 `76(A6)`에 저장한다. 처리기 `e74b6`은 `A0`을 stack에 저장해 `e74d6`에서 되돌린다(인자 WORD 1개 소비). `e74f2`는 인자 WORD 1개를 `5e24(A5)`에 쓴다. `e7546`은 인자를 소비하지 않는다.
- 반복: `eb7bc`(표 `eba9e`, LONG 0까지 8씩)와 `eba78`(bank 목록, LONG 0까지 4씩)은 원본대로 두고 block budget(1,000,000)만 한계다. `e748a`↔`e74b0`는 script의 지속 0 명령이 이어지는 동안 한 호출 안에서 반복한다.
- PVC(결정 7 변경): 쓰기 4곳은 `am_write`로 쓴다(port 이벤트·`pvc_effects`·live `bank_base` 갱신). 쓰기 시점 base 검사는 없다. `eba6e`의 banked 읽기와 `eba78`의 목록 읽기는 새 live bank로 읽고, 8 MiB 밖이면 공용 program bus 오류다.
- 스택: `e74b6` `e7546`의 `MOVE.L A0,-(A7)`(LONG), `eba3e`의 `MOVE.W D0,-(A7)`/`MOVE.W (A7)+,D0`(WORD), JSR/BSR 복귀 LONG. 홀수 A7·work RAM 밖 쓰기는 기존 checked 오류다.
- I/O: RAM d16(A6) `20` `42` `46` `76` `78` `7a` `7c` `7e` `80` `84` `86` `88` `8a`, node LONG `(A6)`(callback 설치), d16(A5) `5e24` `567e` `567f` `5726`/`572c`(주소만) `7d82` `7db6` `7db7` `-8000` `-7ff0` `-3355` `-334f` `-3348` `-3347` `-3346` `-3342` `-3341` `-3340`. port 쓰기는 PVC 4곳뿐이다(callee 몫 제외).
- 회귀 탐침: [F] `engine/tests/animation_machine_input_test.cpp`의 outside 탐침 `0xe73f8`은 U06 block 시작이 된다. 아무 분석 문서에도 없는 미연결 `0x5f200`으로 바꾼다. 같은 파일 690행 `{0xe73f2,0xe73f8}`은 input routing 범위(끝 미포함)라 바꾸지 않는다.

## 자연 시작 상태(읽기 전용 기록)

[F] F4 범위 scratch 재생(`f4scope/dyn`, 142 seed)에서 U06 block에 닿는 callback: `e73f8` `e7792` `e77e4` `e780a` `e7830` `e7850` 각 2(108·109 frame 0), `e7426` 162, `e77ac` 162, `e78a8` 648(108·109), `eb7b6` 2(58·59). TB 시작 기준으로 135 block 중 58개가 자연 도달한다. 미도달 77개(fixture 필요): `49bec` `e743a` `e744e` `e745a` `e7462` `e7478` `e7486` `e74a0` `e74ea` `e788c` `e78d8` `e78ee` `e78f4` `e78fa` `e7902` `e790a` `e7910` `e7916` `e791a` `e7922` `e792e` `e7934` `e7944`, `eb80a`부터 `eb9b8`까지의 `eb7b6` 계열 52개, `eba78` `eba80`(TB 경계 때문에 fall-through block 일부는 실제로 실행돼도 미도달로 셈).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 135 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), 소비 block의 Unknown 오류, zero-step, 내부 540 PC 정확한 오류, 홀수 PC, 경계·간접 대상 오류, bank 4/5/9(ff9 bit15)의 실제 실행, 8 MiB 밖 bank(`800000`)와 홀수 목록 시작의 공용 program bus 오류(상태 보존). 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, 합성 physical 자료: script·`e7392`/`e73c2`/`e7752`/`eba9e` 표, bank 2/3/4/5/1의 banked 목록(physical `200004` `300004` `400004` `500004` `100004`))로 비교한다.
- 실제 ROM 차분: `e73f8`·`e7426`(script)·`e7792` 계열·`eb7b6`(guard)·`49be0`을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`): U01+U02+U03+U05 기준 일치 pass 9,296개가 모두 그대로 일치하고, 완주 seed가 52→56(새 58 59 108 109; 58·59는 pvc-banks native 120 frame 일치)이어야 한다.

## 미확인·범위 밖

1. [I] `e73f8`은 script(`e7570`)로 시간에 따라 `5e24(A5)` WORD(input `e73f2`가 `D7`로 돌려주는 값)와 화면 글자(`3918`/`e84c8`)·전환(`35a2`)을 바꾸는 연출 객체, `e7792` 계열은 입력 slot(`49be0`, `5726`/`572c(A5)`)의 bit(`76(A6)`)로 상태를 바꾸는 선택 표시 객체, `eb7b6`은 입력으로 bank 목록(`eba9e`)을 넘겨 보는 객체로 보인다([I] 디버그 viewer 후보). 게임 의미는 미확인이다.
2. [U] `e74f8`(script 처리기, 점프 표 `e7504`→`e750c`/`e7534`)과 script 끝의 `e7562`(지속 `ffff`)는 기록 지평 밖에서 실행될 수 있다. U06에서는 generic 경계다.
3. [U] native 모델이 bank 4/5를 두지 않는 이유는 관측 도구 설계(실행 window `200000..2fe000`만 복사)이며, 원본 하드웨어에서 bank 4/5 선택이 정상 동작인지는 이 계약에서 정하지 않는다(결정 7 변경: guard 제거. pvc-banks 관측에서 bank 4/5 읽기가 정상 형태임이 확인됐으며 목록이 가리키는 자료의 의미는 [U]).
4. [U] `eb9ba` `eb9e4` `101c` `3ed2` `e7562`는 U06 밖이다.

작업자 scratch: 세션 scratchpad `f4u06/`(`u06.py` block·범위·SHA 계산, `dis_u06.py`, `reach.py`, `callers.py`, `script.py`; 저장소 밖).
