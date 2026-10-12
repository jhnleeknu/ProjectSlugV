# 객체 callback F4 N09: `af4ee` 계열 객체 callback(`af4ee` `af582` `af6de` `af6ec` `af71a`), 범위 안 설치 callback `af630` `af676` `af698`, 범위 밖이 설치하는 `af92c` `afc16`, 공용 꼬리 `af96a`·`b057e`·`b059e`, helper `b0150`~`b0468` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N09 행(`af4ee..af80a` `af92c..af990` `afc16..afcbe` `b005e..b05be`, callback `af4ee` `af582` `af6de` `af6ec` `af71a`, 경계 callee `493bc` `4941e` `b0406`, X·DIV `b0336 DIVU.W`, 미실행 설치 8(+257))과 메인 결정 1·2(이름 `objects-n09`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 원 범위(`animation-machine-object-callbacks-f4-scope.md`, SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 R09·R10 행에 해당한다. 단위 형식과 규약은 N07 계약(SHA256 `cbbb8fbf769a9cad4b656ff71600a9ffdb85242a76c5c78c253a0fafe23a21d0`)과 N04 계약(SHA256 `80e41996735a39feeb7f89ddbb4e3267d993bc4a1431a214f2be4af2e05a31e3`, 결정 3 "predecessor가 둘인 Bcc는 각 predecessor에 묶는다")을 따른다. 같은 작업에서 N10(`c5896..c593e`)을 별도 계약 `animation-machine-objects-n10-contract.md`로 둔다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 실행부 없는 경계다. 범위 안이라도 단위 진입에서 도달하지 않고 참조도 없는 코드는 routing하지 않는다(N03/N05 선례).
- U01~N07 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`/`BCHG`만인 block, callee C를 소비하는 block은 FLOW_ONLY다. 블록 경계를 건너는 N/Z 재계산은 선행이 유일할 때만 허용하고, 선행이 둘 이상이면 Bcc를 각 선행 block에 묶는다(N04 `ab1a6` 선례). checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N09 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n09`(HEAD `de7108c` = N07까지 통합, `engine/src/animation_machine.cpp` SHA256 `a050463fca2b4eb8c6136b1349f468fba6d9b27845563fceab916fab7820b875`, routing 규칙 64개)을 참조했다. N09 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N08(`4945e..494c0` `4983e..49878` `4ae4a..4b50c`)과 겹치지 않는다. N08 진입 `4945e` `4983e` `4ae4a`는 N09가 호출하는 경계다(아래). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n09/n09.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N09 = 225 block**, 코드 9 범위 1,922바이트, 469명령이다. routing 짝수 PC 961개 중 내부 PC 736개다. 범위 안의 모든 명령이 진입에서 정적으로 도달된다(미도달 명령 0). 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 연속 Bcc·SUBX/ADDX/MULx·I/O port 쓰기·bank 변경·banked 자료 읽기는 없다. 나눗셈은 `b0336 DIVU.W #50,D0` 하나다(아래 "DIVU").
  - 재범위 N09 행의 205와 차이(+20): 범위 안 설치 callback `af630` `af676` `af698` 사슬 본문 `af630..af6dc` 20 block(재범위 결정 2; 재범위 "미실행 설치 8(+257)" 중 범위 안 3개), `b0406` 1 block(재범위가 경계 callee로 센 `b03ec BSR.W b0406`의 대상; `b0400 LEA`에서 fall-through하는 같은 함수 `b0352`의 명령 시작이라 block으로 넣는다, 결정 1), 그리고 두 predecessor에 묶은 `af7b0 BNE`(−1, 결정 3).
  - 재범위 범위 `b005e..b05be` 안에서 실제 routing은 `b005e..b0062` `b0150..b0206` `b0228..b0240` `b0260..b02c8` `b02ec..b04cc` `b057e..b05be`다. 빼는 것: U15 `b0062..b0106`, U16 `b0106..b0150` `b0206..b0228` `b02c8..b02ec`(다시 routing하지 않음), 참조 없는 `b0240..b0260`(`b0240 BSR.B b0228`로 시작하는 함수, 어떤 코드·LONG도 가리키지 않음), N09 진입에서 도달하지 않는 `b04cc..b057e`(`b04cc`는 참조 없음, `b051a`는 범위 밖 `afcfc` `afea2` `afee2` `aff0a` `aff52` `aff86`의 `JSR` 대상 = 범위 밖 설치 사슬의 helper).
  - `af4ee..af80a` 안에서 빼는 것 없음. `af80a..af812`는 `af7ea LEA af80a(PC),A1`로 경계 `4941e`에 넘기는 자료(`fffc fffc 0008 0008`)다. `af812..af92c`(설치 `af812` `af8a0` `af8cc` `af8f2` `af910`, TRAP `af856` 포함)와 `af990..afc16`(설치 `af990` `afbbe` 사슬), `afcbe..b005e`(설치 `afcbe` `afed8` 사슬)는 이 단위 밖 설치 사슬(고아, 재범위 결정 3)이다.
- [F] 진입:
  - 노드 callback `af4ee` `af582` `af6de` `af6ec` `af71a`(재범위 미연결 callback; `af6ec`는 U15 `af480 MOVE.L #af6ec,(A6)`이 설치, `af6de`는 routing 밖 `af0dc`, U15 `af4e6`, N09 `af6d4`가 설치).
  - 범위 안 `MOVE.L #imm,(A6)` 설치 callback: `af582`(`af57c`, fall-through), `af630`(`af61c`; 범위 밖 `afcea`도 설치), `af676`(`af780`), `af698`(`af692`, fall-through), `af6de`(`af6d4`), `af71a`(`af714`, fall-through), `af4ee`(`af752` `af78a` `af7b4` `af7d4`; U15 `af416`도 설치).
  - 범위 밖이 설치하는 callback 본문: `af92c`(`af926`, `af8cc` 사슬), `afc16`(`afc10`, `afbbe` 사슬). 재범위가 함수 `af92c` `afc16`으로 이 범위에 넣었다(N07 `9bf1e` 선례, 결정 2).
  - LONG 참조 진입 `b0260`(자료 LONG `4a704`, 앞 LONG `4b54000e` 다음; 재범위 "고아 동적 진입" 19개 중 하나, 자연 기록에서 실행됨). [I] 표 `4a704`를 쓰는 `JSR (A0)` 계열 호출의 대상이다. A0은 호출자가 준 WORD 표 주소다.
  - helper(JSR/BSR 대상): `b0150`(`b02ac`), `b01e4`(`b023e BRA.B`), `b0228`(`b0446`; 범위 밖 `b0240`), `b02ec`(`af734`), `b0326`(`af70c`), `b0352`(`af760`), `b0406`(`b03ec`), `b041c`(`af74a`), `b0468`(`af5ac`; 범위 밖 `afe66`).
  - 공용 꼬리 `af96a`(`af62c` `af6da` `af806` `af966`, 범위 밖 `af8c8` `af90c` `BRA.W`), `b057e`(`af98c`), `b005e`(`afcba`, 범위 밖 `afda2` `afe94` `aff4e` `b005a` `BRA.W`) → `b059e`.
- [F] **경계 callee(실행부 없음)**: `493bc`(`b0232`), `4941e`(`af7ee`, A1 = `af80a`), N08 `4945e`(`b01e4` `b0486`), `4983e`(`b0366`), `4ae4a`(`af958` `b0478`) — N08은 동시 진행이라 이 작업 트리에서는 routing 밖이다. 범위 밖 설치 대상 `af812` `af8cc` `af990` `afbbe` `afcbe` `afed8`은 노드 LONG에 저장만 한다.
- [F] **나가는 호출(routing됨)**: `4be34`(U18) `4be06`(U11) `4be2c`(U18) `4bfa4`(U17) `49f8c`(interpreter) `49fc6`(interpreter, C 반환) `49a58`(stage area RNG) `4c1de`(U15, C 반환) `b02c8`(U16 BSR) `b0206`(U16, C 반환) `496c2`(U11) `492d0`(U20a) `4b54e`(U01, C 반환) `8ff4`(cleanup) `443d2`(U02 계열) `49370`(U11) `490ba`(U11) `1ab02`(U05, C 반환) `1ab80`(N05, C 반환) `2a00`(JMP).
- [F] **carry**(아래 "carry" 절):
  - 소비 block **19개**: `af5b0`(`SCC.B 9b(A6)`, `b0468` 반환), `af64a`(U16 `b0206`), `af6a4` `af938` `afc92`(`49fc6`), `af738`(`b02ec`), `af74e`(`b041c`), `af764`(`b0352`), `af7f4`(경계 `4941e`), `af970`(`4b54e`), `afc78`(`4c1de`), `b01ea`(경계 N08 `4945e`), `b0238`(경계 `493bc`), `b02b0`(`b0150`), `b036c`(경계 N08 `4983e`), `b03f0`(`b0406`), `b044a`(`b0228`), `b058a`(`1ab02`), `b05aa`(`1ab80`).
  - known 생산 block **17개**: Clear `b01c8` `b01fa` `b0320` `b042e`(ANDI CCR), `b0358`(ANDI.B #7), `b03d8`(MOVE.B), `b041c`(TST.B) `b0468`(TST.W), `b047e`(CMPI.W #0 → 항상 C=0); Set `b01d6` `b01ee` `b031a` `b04b6`(ORI CCR); 계산값 `b0406` `b0412` `b0434` `b0462`(CMP/CMPI의 unsigned borrow 그대로).
  - N/Z 재계산 block 없음. 선행 2개 `af7a0`(`BTST.B #7,15(A6); BRA.W af7b0`)·`af7aa`(`BTST.B #1,61(A6)`, fall-through)의 공통 `af7b0 BNE.W af7ba`는 두 block에 각각 묶는다(결정 3). `af7b0`은 내부 PC다.
- [F] **DIVU**(`b0332` block): `EXT.L D0; LSL.L #8,D0; DIVU.W #50,D0; MOVE.W D0,2c(A6)`. 제수는 상수 `0050`이라 0으로 나누는 경우는 없다(검사 오류 불필요). 몫 `D0/0x50`(32-bit unsigned)이 `ffff`를 넘으면 overflow: V=1, `D0`는 바뀌지 않는다(N/Z는 뒤 `MOVE.W`가 덮어 무관, C는 0). 아니면 `D0 = (나머지 << 16) | 몫`. 이어서 `MOVE.W D0,2c(A6)`는 두 경우 모두 `D0`의 하위 WORD를 쓴다. [F] `D0.W`는 U11 `490ba`가 표 `cab3e`에서 돌려준 값이라 `ext(D0.W) << 8 >= 500000`(즉 `D0.W >= 5000` 또는 음수)이면 overflow다. DIVU는 X를 바꾸지 않는다(재범위 "X" 열 = 나눗셈 분류). 단위 안 SUBX/ADDX는 없다.
- [F] 스택: `af4fe MOVE.B D0,-(A7)` / `af520 MOVE.B (A7)+,D0`(BYTE ±2, `4be34` 호출을 사이에 둔다), `af71a MOVE.B 61(A6),-(A7)` / `af724 MOVE.B (A7)+,D0`, `b0150`의 LONG 3개 push(`3e` `32` `2e`) / `b01aa MOVEM.L (A7)+,D0-D2`(낮은 주소부터 D0=`2e`값, D1=`32`값, D2=`3e`값), `b0378 MOVE.B D0,-(A7)`·`b0386` `b0394` `b03a2 MOVE.W D0,-(A7)` / `b03b0 MOVE.W (A7)+` 3번(D2 D1 D0)·`b03d8 MOVE.B (A7)+,D7`, JSR/BSR 복귀 LONG.
- [F] 자료(모두 live bus): fixed ROM을 이 단위가 직접 읽지 않는다. 주소만 넘기는 fixed ROM 자료: `b0d88` `b0cdc` `b06c8`(`49f8c` 목록, A1), `b0660` `b067e`(경계 `4ae4a`, A0), `cab3e` `cabba` `cabd4` `cabee` `cac08`(`490ba` 표, A0), `b05de`(`1ab02`/`1ab80` 사각형, A0), `af80a`(경계 `4941e`, A1). work RAM: 노드 BYTE `15` `5e` `61` `63` `8c` `8d` `9a` `9b` `9c` `9d` `9e` `9f` `a0` `a1` `a3`, WORD `20` `2c` `42` `46` `8a` `8c` `8e` `96`, LONG `(A6)` `c` `2e` `32` `36` `3a` `3e` `64` `76` `7a` `7e`; 부모 노드 `c(A6)`의 BYTE `62`(`SUBQ.B #1`); 대상 노드 `76(A6)`의 WORD `42`; 고정 work RAM 객체 `100cb8` `100da8`의 WORD `42` `46`(`b0406`); `b0260` 호출자의 A0 WORD `(A0)`; A5 WORD `5404`.
- [F] 자연 도달(재범위 scratch 재생 `rescope/build.pkl`의 `N1R`/`N1B`, TB 시작 기준): RNG 초기화+응답 `80` 400 frame에서 seed 18 19 96 97 102 103만 N09에 들어온다(첫 frame 1: `af6de` `af6ec`; frame 2 `af71a`; frame 7 `b0260`/`b0150` 계열; frame 62 `af4ee`/`b0468`). 225 시작 중 110개가 TB 시작으로 나타난다(N10 포함 243 중). base 120 frame에서는 N09 PC를 실행하지 않는다. 자연 경로는 N08 `4945e` `4983e` `4ae4a`도 실행한다(같은 6 seed, frame 1부터). 따라서 [I] N09+N10만으로 이 6 seed는 완주하지 않고 첫 N08 경계에서 멈출 것으로 본다(검증에서 측정).
- [F] 기준 측정(이 작업 트리 base `de7108c`의 `git archive` 사본, scratch 출력 `ms5-scratch/n09/fp/base_*`): base 일치 pass 12,968·node 102,054, 불일치 0, 자연 완주 119. RNG 400: 일치 pass 40,800·node 297,077, 불일치 0, complete 102(SHA256 `d7b6e6c5b703da3a67d0871eaa3ee3e171f242d4e3a7cd8c0220816416861db1`). seed 18 19 96 97 102 103은 frame 0 N10 `c5896`이 첫 미연결 PC다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 225(재범위 205와 +20).** 범위 안 설치 callback `af630` `af676` `af698` 사슬 20 block을 넣고(재범위 결정 2, N04 선례), `b0406`을 block으로 넣고(+1), `af7b0`을 묶는다(−1). [F] `b0406`은 `b0400 LEA 100da8.L,A0`(6바이트) 바로 뒤 명령 시작이고 `b03ec BSR.W`의 대상이다. 같은 함수 `b0352` 본문이라 경계로 두면 `b0400`이 경계로 fall-through하는 꼴이 되어 본문이 끊긴다. 이 계약은 block으로 넣는다. 넣지 않으려면 `b0352` 함수 전체를 다음 단위로 미뤄야 한다.
2. **`af630..af6dc` 포함.** 자연 400 frame 안에 실행되지 않는다(재범위 "미실행 설치"). 결정 2를 따라 넣는다. 빼면 range를 `af4ee..af630` `af6de..af80a`로 나누고 205+1−1 = 205 block이 된다.
3. **`af7b0 BNE` 묶기.** `af7a0`(`BTST.B #7,15(A6); BRA.W af7b0`)과 `af7aa`(`BTST.B #1,61(A6)`, fall-through) 두 predecessor가 Z를 만든다. 유일 선행 규칙에 따라 재계산하지 않고 두 block에 묶는다. `af7a0`은 `BTST.B #7,15(A6); BRA.W af7b0; BNE.W af7ba`를, `af7aa`는 `BTST.B #1,61(A6); BNE.W af7ba`를 한 block으로 실행하고 `af7ba`/`af7b4`를 고른다. `af7b0` 직접 진입은 `unsupported animation objects n09 PC`다.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n09.cpp`의 `animation_objects_n09_block`. 오류는 `unsupported animation objects n09 PC`(내부 PC), `objects n09 caller requires known carry`(소비 19 block). 메인 지시와 같다.
5. **N08 경계.** `4945e` `4983e` `4ae4a`는 이 작업 트리에서 routing 밖이라 `unsupported animation machine PC`다. 단위 test는 그 PC에서 멈춤만 확인한다(F4 test 경계 관례). N08 병합 뒤 `b01ea` `b036c`의 C 생산자는 N08이다(N08 계약 확인 필요, [U]).
6. **DIVU overflow.** 원본이 overflow를 막지 않으므로(제수 상수, 몫 검사 없음) 68000 규칙대로 V만 세우고 `D0`를 그대로 둔다. 0 나누기는 생길 수 없어 checked 오류를 두지 않는다.
7. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`에서 N09 범위 PC를 경계·rollback 기대로 쓰는 곳은 없다(scratch grep, 아래 "의존·경계").

## 원본 바이트 근거

[F] 코드 9 범위 합계 1,922바이트. 범위 순서로 이어 붙인 SHA256 `33190dbc7921b591b61e838a26b060c3e9a53d74979c883f185a04cbbce47a50`.

| CPU 범위 | 바이트 | SHA256 | 시작 | 내용 |
| --- | --- | --- | --- | --- |
| `af4ee..af80a` | 796 | `cef4f5825f206180f08de84574dd8de7891e62878f95c3d0073ba849416ad978` | 83 | callback `af4ee` `af582` `af6de` `af6ec` `af71a`, 설치 `af630` `af676` `af698` |
| `af92c..af990` | 100 | `0202d43cb26d538436c0f7984bfcddbf2ed2665c731305177d71a7f430718d4e` | 14 | 설치 `af92c`, 공용 꼬리 `af96a` |
| `afc16..afcbe` | 168 | `a1bd3d998efaafb271645f75f122d17ab56d8ed5ad217e14b5c70e56f0bac562` | 22 | 설치 `afc16` |
| `b005e..b0062` | 4 | `2e6264a4d3b74ec0b35215ca6627d5b6a1d398aad8226b2973cff6f6369522e7` | 1 | `BRA.W b059e` |
| `b0150..b0206` | 182 | `a4bf82c78e1d222eda05ef24490395611c27a2765a09435cedc9fe64b15db344` | 17 | helper `b0150` `b01e4` |
| `b0228..b0240` | 24 | `1ea727de5d561fb25352f017a9e09dc79ee5734b0105c4dac6011845ecebf3df` | 5 | helper `b0228` |
| `b0260..b02c8` | 104 | `53d641aef531afc5e08869f41a7c4f2ee018b38d529192e94af21410934dd4a4` | 15 | `b0260` |
| `b02ec..b04cc` | 480 | `251cd706d6476bbcd134c7b89417836d0d829d0127b36074f3f7e297c63ecffa` | 60 | helper `b02ec` `b0326` `b0352` `b0406` `b041c` `b0468` |
| `b057e..b05be` | 64 | `a3d05ff8cc2d235e94470d439c6581de599a5b3614d0e23564a16867e0dc5f50` | 8 | 꼬리 `b057e` `b059e` |

## block 목록과 실행 의미

[F] 225 block. 각 줄은 block 안 명령 전체다(capstone 표기, 즉치·주소 16진). "(→x)"는 fall-through다. 태그: "C 소비"(FLOW_ONLY, Unknown이면 checked 오류), "Clear/Set 생산", "C 계산 생산"(CMP/CMPI의 unsigned borrow), "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. 부호 비교는 2의 보수로 명시 계산한다. `MOVE.B Dn,-(A7)`/`MOVE.B (A7)+,Dn`은 A7을 2 움직이고 BYTE는 A7 주소에 있다.
**callback `af4ee` 9**
- `af4ee`: `MOVE.B a1(a6),d0; LSL.B #1,d0; BTST.B #1,15(a6); BEQ.W af522` (→`af4fe`)
- `af4fe`: `ADDI.B #10,d0; BCHG.B #0,15(a6); MOVE.B d0,-(a7); MOVEQ #0,d0; MOVE.L d0,36(a6); MOVE.W #fff8,d0; SWAP d0; MOVE.L d0,3a(a6); JSR 4be34.l`
- `af520`: `MOVE.B (a7)+,d0` (→`af522`)
- `af522`: `MOVE.B d0,8c(a6); CLR.B 8d(a6); MOVEQ #0,d0; MOVE.L d0,36(a6); MOVE.L d0,3a(a6); MOVE.L #ffffb000,7e(a6); MOVE.W #163,20(a6); MOVEA.L #b0d88,a1; MOVE.W #100,d0; JSR 49f8c.l`
- `af552`: `JSR 49a58.l` — FLOW
- `af558`: `MOVE.W d0,d1; BEQ.W af56e` (→`af55e`)
- `af55e`: `ANDI.W #ff,d0; ADDI.W #100,d0; TST.W d1; BPL.W af56e` (→`af56c`)
- `af56c`: `NEG.W d0` (→`af56e`)
- `af56e`: `MOVE.W d0,8e(a6); BCLR.B #1,15(a6); ST.B 9b(a6); MOVE.L #af582,(a6)` (→`af582`)

**callback `af582`(설치) 17**
- `af582`: `MOVE.W 8e(a6),d0; ADD.W d0,8c(a6); ANDI.B #1f,8c(a6); MOVE.L 7e(a6),d0; ADD.L d0,3a(a6); JSR 4be34.l`
- `af59e`: `JSR 49fc6.l` — FLOW
- `af5a4`: `TST.B 9b(a6); BEQ.W af5b4` (→`af5ac`)
- `af5ac`: `JSR b0468(pc)` — FLOW
- `af5b0`: `SCC.B 9b(a6)` (→`af5b4`) — C 소비
- `af5b4`: `BTST.B #7,15(a6); BEQ.W af62c` (→`af5be`) — FLOW
- `af5be`: `JSR 49a58.l` — FLOW
- `af5c4`: `MOVE.W d0,d1; ANDI.W #1000,d1; SEQ.B d1; AND.B 9b(a6),d1; BEQ.W af608` (→`af5d4`)
- `af5d4`: `ANDI.W #1f0,d0; SUBI.W #100,d0; EXT.L d0; LSL.L #8,d0; MOVE.L d0,36(a6); MOVE.L 3a(a6),d0; ASR.L #2,d0; NEG.L d0; CMPI.L #20000,d0; BCC.W af5fc` (→`af5f6`)
- `af5f6`: `MOVE.L #20000,d0` (→`af5fc`)
- `af5fc`: `MOVE.L d0,3a(a6); SF.B 9b(a6); BRA.W af62c`
- `af608`: `TST.W d0; BPL.W af614` (→`af60e`)
- `af60e`: `BCHG.B #0,15(a6)` (→`af614`) — FLOW
- `af614`: `ANDI.B #3,d0; BEQ.W af626` (→`af61c`)
- `af61c`: `MOVE.L #af630,(a6); BRA.W af62c`
- `af626`: `MOVE.L #afbbe,(a6)` (→`af62c`)
- `af62c`: `BRA.W af96a` — FLOW

**설치 callback `af630`·`af676`·`af698` 20**
- `af630`: `MOVEQ #0,d0; JSR 4c1de.l`
- `af638`: `MOVE.W d7,d0; BSR.W b02c8`
- `af63e`: `MOVE.B d0,a1(a6); MOVE.B d0,a0(a6); JSR b0206(pc)`
- `af64a`: `BCC.W af65a` (→`af64e`) — C 소비
- `af64e`: `MOVEA.L 76(a6),a0; MOVE.W 42(a0),d0; BRA.W af65e`
- `af65a`: `MOVE.W #a0,d0` (→`af65e`)
- `af65e`: `CMP.W 42(a6),d0; SGT.B d0; BTST.B #0,15(a6); SNE.B d1; EOR.B d0,d1; BNE.W af676` (→`af672`)
- `af672`: `BRA.W af6de` — FLOW
- `af676`: `JSR 496c2.l` — FLOW
- `af67c`: `MOVE.W #163,20(a6); MOVEA.L #b0cdc,a1; MOVE.W #100,d0; JSR 49f8c.l`
- `af692`: `MOVE.L #af698,(a6)` (→`af698`)
- `af698`: `JSR 4be2c.l` — FLOW
- `af69e`: `JSR 49fc6.l` — FLOW
- `af6a4`: `BCC.W af6da` (→`af6a8`) — C 소비
- `af6a8`: `MOVEQ #5,d0; BTST.B #0,15(a6); BEQ.W af6b6` (→`af6b4`)
- `af6b4`: `NEG.W d0` (→`af6b6`)
- `af6b6`: `SWAP d0; MOVE.L d0,64(a6); JSR 4bfa4.l`
- `af6c2`: `JSR 492d0.l` — FLOW
- `af6c8`: `MOVE.B #4,a1(a6); MOVE.B #4,a0(a6); MOVE.L #af6de,(a6)` (→`af6da`)
- `af6da`: `BRA.W af96a` — FLOW

**callback `af6de`·`af6ec` 5**
- `af6de`: `BCLR.B #1,15(a6); SF.B 9f(a6); BRA.W af6f6` — FLOW
- `af6ec`: `BSET.B #1,15(a6); ST.B 9f(a6)` (→`af6f6`) — FLOW
- `af6f6`: `MOVE.W #163,20(a6); MOVEA.L #b06c8,a1; MOVE.W #100,d0; JSR 49f8c.l`
- `af70c`: `JSR b0326(pc)` — FLOW
- `af710`: `ST.B 9d(a6); MOVE.L #af71a,(a6)` (→`af71a`)

**callback `af71a`(설치) 32**
- `af71a`: `MOVE.B 61(a6),-(a7); JSR 4be06.l`
- `af724`: `MOVE.B (a7)+,d0; ANDI.B #2,d0; OR.B d0,61(a6); JSR 49fc6.l`
- `af734`: `JSR b02ec(pc)` — FLOW
- `af738`: `BCC.W af742` (→`af73c`) — C 소비
- `af73c`: `MOVE.L #af812,(a6)` (→`af742`)
- `af742`: `TST.B a3(a6); BNE.W af758` (→`af74a`)
- `af74a`: `JSR b041c(pc)` — FLOW
- `af74e`: `BCC.W af758` (→`af752`) — C 소비
- `af752`: `MOVE.L #af4ee,(a6)` (→`af758`)
- `af758`: `TST.B 9f(a6); BNE.W af76e` (→`af760`)
- `af760`: `JSR b0352(pc)` — FLOW
- `af764`: `BCC.W af76e` (→`af768`) — C 소비
- `af768`: `MOVE.L #af8cc,(a6)` (→`af76e`)
- `af76e`: `BTST.B #0,61(a6); BEQ.W af790` (→`af778`) — FLOW
- `af778`: `TST.B 9f(a6); BNE.W af78a` (→`af780`)
- `af780`: `MOVE.L #af676,(a6); BRA.W af790`
- `af78a`: `MOVE.L #af4ee,(a6)` (→`af790`)
- `af790`: `TST.B a3(a6); BNE.W af7be` (→`af798`)
- `af798`: `TST.B 9f(a6); BNE.W af7aa` (→`af7a0`)
- `af7a0`: `BTST.B #7,15(a6); BRA.W af7b0; BNE.W af7ba` (→`af7b4`) — FLOW
- `af7aa`: `BTST.B #1,61(a6); BNE.W af7ba` (→`af7b4`) — FLOW
- `af7b4`: `MOVE.L #af4ee,(a6)` (→`af7ba`)
- `af7ba`: `BRA.W af7da` — FLOW
- `af7be`: `TST.W 5404(a5); BEQ.W af7da` (→`af7c6`)
- `af7c6`: `JSR 49a58.l` — FLOW
- `af7cc`: `ANDI.W #f,d0; BNE.W af7da` (→`af7d4`)
- `af7d4`: `MOVE.L #af4ee,(a6)` (→`af7da`)
- `af7da`: `MOVE.B 9a(a6),d0; AND.B 9f(a6),d0; BEQ.W af806` (→`af7e6`)
- `af7e6`: `MOVEA.L c(a6),a0; LEA.L af80a(pc),a1; JSR 4941e.l` — FLOW
- `af7f4`: `BCS.W af806` (→`af7f8`) — C 소비
- `af7f8`: `MOVEA.L c(a6),a0; SUBQ.B #1,62(a0); JMP 2a00.l`
- `af806`: `BRA.W af96a` — FLOW

**설치 callback `af92c`(범위 밖 `af926` 설치) 8**
- `af92c`: `JSR 4be06.l` — FLOW
- `af932`: `JSR 49fc6.l` — FLOW
- `af938`: `BCC.W af94a` (→`af93c`) — C 소비
- `af93c`: `MOVEA.L c(a6),a0; SUBQ.B #1,62(a0); JMP 2a00.l`
- `af94a`: `TST.B 9c(a6); BEQ.W af966` (→`af952`)
- `af952`: `LEA.L b0660.l,a0; JSR 4ae4a.l` — FLOW
- `af95e`: `CMPI.W #0,d0; SEQ.B 9c(a6)` (→`af966`)
- `af966`: `BRA.W af96a` — FLOW

**공용 꼬리 `af96a` 6**
- `af96a`: `JSR 4b54e.l` — FLOW
- `af970`: `BCC.W af98c` (→`af974`) — C 소비
- `af974`: `BTST.B #7,61(a6); BEQ.W af988` (→`af97e`) — FLOW
- `af97e`: `MOVE.L #af990,(a6); BRA.W af98c`
- `af988`: `CLR.B 5e(a6)` (→`af98c`)
- `af98c`: `BRA.W b057e` — FLOW

**설치 callback `afc16`(범위 밖 `afc10` 설치) 22**
- `afc16`: `BTST.B #7,61(a6); BEQ.W afc32` (→`afc20`) — FLOW
- `afc20`: `TST.B 63(a6); BNE.W afc32` (→`afc28`)
- `afc28`: `JSR 8ff4.l` — FLOW
- `afc2e`: `ST.B 63(a6)` (→`afc32`) — FLOW
- `afc32`: `SUBQ.W #1,96(a6); BPL.W afc6c` (→`afc3a`)
- `afc3a`: `JSR 49a58.l` — FLOW
- `afc40`: `MOVE.W d0,d1; ANDI.W #ff,d0; ADDI.W #20,d0; TST.W d1; BPL.W afc52` (→`afc50`)
- `afc50`: `NEG.W d0` (→`afc52`)
- `afc52`: `EXT.L d0; LSL.L #8,d0; MOVE.L d0,64(a6); JSR 49a58.l`
- `afc60`: `ANDI.W #1f,d0; ADDI.W #a,d0; MOVE.W d0,96(a6)` (→`afc6c`)
- `afc6c`: `MOVE.W 64(a6),d0; ASL.W #1,d0; JSR 4c1de.l`
- `afc78`: `BCC.W afc86` (→`afc7c`) — C 소비
- `afc7c`: `JSR 4bfa4.l` — FLOW
- `afc82`: `BRA.W afc8c` — FLOW
- `afc86`: `JSR 4be06.l` — FLOW
- `afc8c`: `JSR 49fc6.l` — FLOW
- `afc92`: `BCC.W afcb0` (→`afc96`) — C 소비
- `afc96`: `BTST.B #7,61(a6); BEQ.W afcaa` (→`afca0`) — FLOW
- `afca0`: `MOVE.L #afed8,(a6); BRA.W afcb0`
- `afcaa`: `MOVE.L #afcbe,(a6)` (→`afcb0`)
- `afcb0`: `BTST.B #7,61(a6); BEQ.W af96a` (→`afcba`) — FLOW
- `afcba`: `BRA.W b005e` — FLOW

**`b005e` 1**
- `b005e`: `BRA.W b059e` — FLOW

**helper `b0150` 12**
- `b0150`: `MOVE.L 3e(a6),-(a7); MOVE.L 32(a6),-(a7); MOVE.L 2e(a6),-(a7); MOVE.L 7a(a6),d0; MOVE.B 9e(a6),d1; JSR 443d2.l`
- `b016a`: `NEG.L d1; MOVE.L d1,36(a6); MOVE.L d0,3a(a6); JSR 4be34.l`
- `b017a`: `BTST.B #1,61(a6); BNE.W b01aa` (→`b0184`) — FLOW
- `b0184`: `MOVE.L 7a(a6),d0; BPL.W b018e` (→`b018c`)
- `b018c`: `NEG.L d0` (→`b018e`)
- `b018e`: `MOVE.B 9e(a6),d1; JSR 443d2.l`
- `b0198`: `NEG.L d0; NEG.L d1; MOVE.L d0,36(a6); MOVE.L d1,3a(a6); JSR 4be34.l`
- `b01aa`: `MOVEM.L (a7)+,d0-d2; BTST.B #1,61(a6); BNE.W b01d6` (→`b01b8`) — FLOW
- `b01b8`: `MOVEM.L d0-d1,2e(a6); MOVE.L d2,3e(a6); JSR 4be06.l`
- `b01c8`: `BCLR.B #1,61(a6); ANDI.B #fe,ccr; BRA.W b01e2` — Clear 생산
- `b01d6`: `MOVE.W d4,d0; LSR.W #8,d0; MOVE.B d0,9e(a6); ORI.B #1,ccr` (→`b01e2`) — Set 생산
- `b01e2`: `RTS` — FLOW

**helper `b01e4` 5**
- `b01e4`: `JSR 4945e.l` — FLOW
- `b01ea`: `BCS.W b01fa` (→`b01ee`) — C 소비
- `b01ee`: `MOVE.L a0,76(a6); ORI.B #1,ccr; BRA.W b0204` — Set 생산
- `b01fa`: `MOVEQ #0,d0; MOVE.L d0,76(a6); ANDI.B #fe,ccr` (→`b0204`) — Clear 생산
- `b0204`: `RTS` — FLOW

**helper `b0228` 5**
- `b0228`: `MOVE.L 76(a6),d0; BEQ.W b023e` (→`b0230`)
- `b0230`: `MOVEA.L d0,a0; JSR 493bc.l` — FLOW
- `b0238`: `BCC.W b023e` (→`b023c`) — C 소비
- `b023c`: `RTS` — FLOW
- `b023e`: `BRA.B b01e4` — FLOW

**helper `b0260`(LONG `4a704` 참조) 15**
- `b0260`: `TST.B 9d(a6); BNE.W b026a` (→`b0268`)
- `b0268`: `RTS` — FLOW
- `b026a`: `MOVE.W (a0),d0; BTST.B #0,15(a6); BNE.W b0278` (→`b0276`)
- `b0276`: `NEG.W d0` (→`b0278`)
- `b0278`: `SWAP d0; CLR.W d0; TST.B 9f(a6); BNE.W b02a4` (→`b0284`)
- `b0284`: `MOVE.L d0,64(a6); MOVE.L d0,36(a6); JSR 4bfa4.l`
- `b0292`: `BTST.B #7,15(a6); BNE.W b029e` (→`b029c`) — FLOW
- `b029c`: `RTS` — FLOW
- `b029e`: `MOVE.W d7,d0; BRA.W b02b8`
- `b02a4`: `MOVE.L d0,7a(a6); MOVE.L d0,36(a6); JSR b0150(pc)`
- `b02b0`: `BCS.W b02b6` (→`b02b4`) — C 소비
- `b02b4`: `RTS` — FLOW
- `b02b6`: `MOVE.W d4,d0` (→`b02b8`)
- `b02b8`: `BSR.W b02c8` — FLOW
- `b02bc`: `MOVE.B a0(a6),a1(a6); MOVE.B d0,a0(a6); RTS`

**helper `b02ec` 7**
- `b02ec`: `MOVE.B a0(a6),d0; MOVE.B a1(a6),d1; CMP.B d0,d1; BEQ.W b0320` (→`b02fa`)
- `b02fa`: `CMPI.B #2,d0; BHI.W b030a` (→`b0302`)
- `b0302`: `CMPI.B #2,d1; BLS.W b0320` (→`b030a`)
- `b030a`: `CMPI.B #6,d0; BCS.W b031a` (→`b0312`)
- `b0312`: `CMPI.B #6,d1; BCC.W b0320` (→`b031a`)
- `b031a`: `ORI.B #1,ccr; RTS` — Set 생산
- `b0320`: `ANDI.B #fe,ccr; RTS` — Clear 생산

**helper `b0326`(DIVU) 3**
- `b0326`: `LEA.L cab3e.l,a0; JSR 490ba.l` — FLOW
- `b0332`: `EXT.L d0; LSL.L #8,d0; DIVU.W #50,d0; MOVE.W d0,2c(a6); JSR 49a58.l`
- `b0344`: `ANDI.W #3f,d0; SUBI.W #20,d0; ADD.W d0,2c(a6); RTS`

**helper `b0352`·`b0406` 25**
- `b0352`: `JSR 49a58.l` — FLOW
- `b0358`: `ANDI.B #7,d0; BEQ.W b0362` (→`b0360`) — Clear 생산
- `b0360`: `RTS` — FLOW
- `b0362`: `MOVEQ #0,d0; MOVEQ #0,d1; JSR 4983e.l`
- `b036c`: `BCS.W b0372` (→`b0370`) — C 소비
- `b0370`: `RTS` — FLOW
- `b0372`: `JSR 49370.l` — FLOW
- `b0378`: `MOVE.B d0,-(a7); LEA.L cabba.l,a0; JSR 490ba.l`
- `b0386`: `MOVE.W d0,-(a7); LEA.L cabd4.l,a0; JSR 490ba.l`
- `b0394`: `MOVE.W d0,-(a7); LEA.L cabee.l,a0; JSR 490ba.l`
- `b03a2`: `MOVE.W d0,-(a7); LEA.L cac08.l,a0; JSR 490ba.l`
- `b03b0`: `MOVE.W d0,d3; MOVE.W (a7)+,d2; MOVE.W (a7)+,d1; MOVE.W (a7)+,d0; BTST.B #0,15(a6); BEQ.W b03c6` (→`b03c2`)
- `b03c2`: `ADD.W d1,d0; NEG.W d0` (→`b03c6`)
- `b03c6`: `ADD.W 42(a6),d0; BTST.B #1,15(a6); BEQ.W b03d8` (→`b03d4`)
- `b03d4`: `ADD.W d3,d2; NEG.W d2` (→`b03d8`)
- `b03d8`: `ADD.W 46(a6),d2; MOVE.B (a7)+,d7; BTST.B #0,d7; BEQ.W b03f6` (→`b03e6`) — Clear 생산
- `b03e6`: `LEA.L 100cb8.l,a0; BSR.W b0406` — FLOW
- `b03f0`: `BCC.W b03f6` (→`b03f4`) — C 소비
- `b03f4`: `RTS` — FLOW
- `b03f6`: `BTST.B #1,d7; BNE.W b0400` (→`b03fe`) — FLOW
- `b03fe`: `RTS` — FLOW
- `b0400`: `LEA.L 100da8.l,a0` (→`b0406`) — FLOW
- `b0406`: `MOVE.W 42(a0),d4; SUB.W d0,d4; CMP.W d1,d4; BCC.W b041a` (→`b0412`) — C 계산 생산
- `b0412`: `MOVE.W 46(a0),d4; SUB.W d2,d4; CMP.W d3,d4` (→`b041a`) — C 계산 생산
- `b041a`: `RTS` — FLOW

**helper `b041c` 12**
- `b041c`: `TST.B 9f(a6); BNE.W b0426` (→`b0424`) — Clear 생산
- `b0424`: `RTS` — FLOW
- `b0426`: `TST.W 8a(a6); BPL.W b0434` (→`b042e`)
- `b042e`: `ANDI.B #fe,ccr; RTS` — Clear 생산
- `b0434`: `MOVE.W 42(a6),d0; SUBI.W #20,d0; CMPI.W #120,d0; BCS.W b0446` (→`b0444`) — C 계산 생산
- `b0444`: `RTS` — FLOW
- `b0446`: `BSR.W b0228` — FLOW
- `b044a`: `BCS.W b0450` (→`b044e`) — C 소비
- `b044e`: `RTS` — FLOW
- `b0450`: `MOVEA.L 76(a6),a0; MOVE.W 42(a0),d0; SUB.W 42(a6),d0; BPL.W b0462` (→`b0460`)
- `b0460`: `NEG.W d0` (→`b0462`)
- `b0462`: `CMP.W 8a(a6),d0; RTS` — C 계산 생산

**helper `b0468` 13**
- `b0468`: `TST.W 3a(a6); BMI.W b0472` (→`b0470`) — Clear 생산
- `b0470`: `RTS` — FLOW
- `b0472`: `LEA.L b067e.l,a0; JSR 4ae4a.l` — FLOW
- `b047e`: `CMPI.W #0,d0; BEQ.W b04ca` (→`b0486`) — Clear 생산
- `b0486`: `JSR 4945e.l` — FLOW
- `b048c`: `MOVE.L 36(a6),d0; BPL.W b0496` (→`b0494`)
- `b0494`: `NEG.L d0` (→`b0496`)
- `b0496`: `LSR.L #1,d0; CMPI.L #18000,d0; BCC.W b04a8` (→`b04a2`)
- `b04a2`: `MOVE.L #18000,d0` (→`b04a8`)
- `b04a8`: `MOVE.W 42(a6),d1; CMP.W 42(a0),d1; BGE.W b04b6` (→`b04b4`)
- `b04b4`: `NEG.L d0` (→`b04b6`)
- `b04b6`: `MOVE.L 3a(a6),d1; ASR.L #1,d1; NEG.L d1; MOVE.L d0,36(a6); MOVE.L d1,3a(a6); ORI.B #1,ccr` (→`b04ca`) — Set 생산
- `b04ca`: `RTS` — FLOW

**꼬리 `b057e`·`b059e` 8**
- `b057e`: `LEA.L b05de.l,a0; JSR 1ab02.l` — FLOW
- `b058a`: `BCC.W b059c` (→`b058e`) — C 소비
- `b058e`: `MOVEA.L c(a6),a0; SUBQ.B #1,62(a0); JMP 2a00.l`
- `b059c`: `RTS` — FLOW
- `b059e`: `LEA.L b05de.l,a0; JSR 1ab80.l` — FLOW
- `b05aa`: `BCC.W b05bc` (→`b05ae`) — C 소비
- `b05ae`: `MOVEA.L c(a6),a0; SUBQ.B #1,62(a0); JMP 2a00.l`
- `b05bc`: `RTS` — FLOW

(수: 9 + 17 + 20 + 5 + 32 + 8 + 6 + 22 + 1 + 12 + 5 + 5 + 15 + 7 + 3 + 25 + 12 + 13 + 8 = 225.)

### 주의할 block 의미

- `af4ee`: `MOVE.B a1(A6),D0; LSL.B #1,D0`(D0 BYTE만); `BTST.B #1,15(A6)` bit 0이면 `af522`, 아니면 `af4fe`.
- `af4fe`: `ADDI.B #10,D0; BCHG.B #0,15(A6)`; BYTE push(A7 −2, BYTE는 새 A7); `D0 = 0`; `36 = 0`; `D0 = fff80000`(`MOVE.W #fff8,D0; SWAP`); `3a = fff80000`; `JSR 4be34`(복귀 `af520`). `af520`: BYTE pop(A7 +2) → `D0.B`.
- `af522`: `8c = D0.B; 8d = 0; D0 = 0; 36 = 3a = 0; 7e = ffffb000; 20 = 0163; A1 = b0d88; D0.W = 0100; JSR 49f8c`.
- `af558` `af55e` `af56c`: `D1.W = D0.W`; 0이면 그대로, 아니면 `D0.W = (D0 & ff) + 100`, 원래 값이 음수(`D1.W` bit 15)면 `NEG.W`. `af56e`: `8e = D0.W; 15 bit 1 = 0; 9b = ff; (A6) = af582`.
- `af582`: `D0.W = 8e; WORD 8c += D0.W; BYTE 8c &= 1f; D0 = 7e; 3a += D0; JSR 4be34`.
- `af5b0`: `SCC.B 9b(A6)`: C clear면 `ff`, set이면 `00`(C 소비).
- `af5c4`: `D1.W = D0.W; D1.W &= 1000; SEQ.B D1`(위 결과 0이면 `ff`); `D1.B &= 9b`; 결과 BYTE 0이면 `af608`.
- `af5d4`: `D0.W = (D0 & 1f0) − 100; EXT.L; LSL.L #8; 36 = D0; D0 = −(3a ASR 2)`; unsigned `D0 >= 20000`이면 `af5fc`, 아니면 `af5f6`(`D0 = 20000`). `af5fc`: `3a = D0; 9b = 0; BRA af62c`.
- `af608`/`af60e`/`af614`: `D0.W` 음수면 `BCHG.B #0,15(A6)`; `D0.B & 3`이 0이면 `af626`(`(A6) = afbbe`), 아니면 `af61c`(`(A6) = af630`).
- `af65e`: `D0.B = (부호 D0.W > 부호 42(A6) WORD) ? ff : 00`(SGT); `D1.B = (15 bit 0 ≠ 0) ? ff : 00`(SNE); `D1.B ^= D0.B`; 0이 아니면 `af676`, 0이면 `af672`(`BRA af6de`). `D0`/`D1` 상위 bit는 보존.
- `af6a8`/`af6b4`/`af6b6`: `D0 = 5`; `15 bit 0`이 1이면 `NEG.W`; `SWAP D0; 64 = D0; JSR 4bfa4`.
- `af724`: BYTE pop → `D0.B`; `D0.B &= 2; BYTE 61 |= D0.B; JSR 49fc6`.
- `af7a0`(묶음): `BTST.B #7,15(A6)`; bit 1이면 `af7ba`, 0이면 `af7b4`. `af7aa`: `BTST.B #1,61(A6)`, 같은 선택.
- `af7da`: `D0.B = 9a & 9f`; 0이면 `af806`. `af7e6`: `A0 = c(A6) LONG; A1 = af80a; JSR 4941e`(경계). `af7f8`/`af93c`/`b058e`/`b05ae`: `A0 = c(A6); BYTE 62(A0) −= 1; JMP 2a00`.
- `af95e`: `CMPI.W #0,D0; SEQ.B 9c(A6)`(`D0.W = 0`이면 `ff`).
- `afc32`: `WORD 96 −= 1`; 결과 bit 15 = 0이면(BPL) `afc6c`.
- `afc40` `afc50` `afc52` `afc60`: `D1.W = D0.W; D0.W = (D0 & ff) + 20`; `D1.W` 음수면 `NEG.W`; `EXT.L; LSL.L #8; 64 = D0; JSR 49a58`; `D0.W = (D0 & 1f) + a; 96 = D0.W`.
- `afc6c`: `D0.W = 64 WORD; ASL.W #1`(WORD만); `JSR 4c1de`.
- `b0150`: LONG `3e` `32` `2e` 순서로 push; `D0 = 7a; D1.B = 9e; JSR 443d2`. `b016a`: `D1 = −D1; 36 = D1; 3a = D0; JSR 4be34`. `b0184` `b018c`: `D0 = |7a|`(`NEG.L`, `80000000`은 그대로). `b018e`: `D1.B = 9e; JSR 443d2`. `b0198`: `D0 = −D0; D1 = −D1; 36 = D0; 3a = D1; JSR 4be34`.
- `b01aa`: `MOVEM.L (A7)+,D0-D2`(LONG 3개 pop); `61 bit 1`이면 `b01d6`. `b01b8`: `2e = D0; 32 = D1; 3e = D2; JSR 4be06`. `b01c8`: `BCLR.B #1,61(A6)`; C Clear; `BRA b01e2`. `b01d6`: `D0.W = D4.W >> 8`(LSR); `9e = D0.B`; C Set. `b01e2`: `RTS`.
- `b01ee`: `76 = A0; C Set; BRA b0204`. `b01fa`: `D0 = 0; 76 = 0; C Clear`.
- `b0228`: `D0 = 76 LONG`; 0이면 `b023e`(`BRA.B b01e4`). `b0230`: `A0 = D0; JSR 493bc`(경계).
- `b026a`: `D0.W = WORD (A0)`; `15 bit 0`이 0이면 `NEG.W`. `b0278`: `SWAP D0; CLR.W D0`; `9f ≠ 0`이면 `b02a4`. `b0284`: `64 = 36 = D0; JSR 4bfa4`. `b029e`: `D0.W = D7.W; BRA b02b8`. `b02a4`: `7a = 36 = D0; JSR b0150`. `b02b6`: `D0.W = D4.W`. `b02b8`: `BSR b02c8`(U16). `b02bc`: `BYTE a1 = BYTE a0; a0 = D0.B; RTS`.
- `b02ec` 계열(BYTE `a0` = D0, `a1` = D1): 같으면 Clear. 아니면 `D0 > 2`(unsigned)거나 `D1 > 2`이고 `D0 < 6`이거나 `D1 < 6`이면 Set, 그 밖은 Clear(분기 순서 그대로 구현).
- `b0326`: `A0 = cab3e; JSR 490ba`. `b0332`: `D0 = ext(D0.W) << 8`; DIVU(위); `2c = D0.W; JSR 49a58`. `b0344`: `D0.W = (D0 & 3f) − 20; WORD 2c += D0.W; RTS`.
- `b0358`: `D0.B &= 7`; 0이면 `b0362`, 아니면 `b0360 RTS`(C Clear). `b0362`: `D0 = D1 = 0; JSR 4983e`(경계 N08).
- `b0378`~`b03a2`: `D0.B` BYTE push, 표 `cabba` `cabd4` `cabee` `cac08`의 `490ba` 결과 WORD 3개 push. `b03b0`: `D3.W = D0.W; D2.W D1.W D0.W` = WORD pop 3번; `15 bit 0`이면 `b03c2`(`D0.W = −(D0.W + D1.W)`). `b03c6`: `D0.W += 42 WORD`; `15 bit 1`이면 `b03d4`(`D2.W = −(D2.W + D3.W)`). `b03d8`: `D2.W += 46 WORD`; BYTE pop → `D7.B`(C Clear); `D7 bit 0`이 0이면 `b03f6`. `b03e6`: `A0 = 100cb8; BSR b0406`. `b03f6`: `D7 bit 1`이 1이면 `b0400`(`A0 = 100da8`, → `b0406`), 아니면 `b03fe RTS`.
- `b0406`: `D4.W = 42(A0) − D0.W`; C = `D4.W < D1.W`(unsigned); C clear면 `b041a`, set이면 `b0412`. `b0412`: `D4.W = 46(A0) − D2.W`; C = `D4.W < D3.W`. `b041a`: `RTS`.
- `b0426`: `8a WORD` 음수면 `b042e`(C Clear, RTS). `b0434`: `D0.W = 42 − 20`; C = `D0.W < 120`; C set이면 `b0446`, 아니면 `b0444 RTS`. `b0450` `b0460`: `A0 = 76; D0.W = 42(A0) − 42(A6)`; 음수면 `NEG.W`. `b0462`: C = `D0.W < 8a WORD`(unsigned); `RTS`.
- `b0468`: `3a WORD`(상위) 음수가 아니면 `b0470 RTS`(C Clear). `b0472`: `A0 = b067e; JSR 4ae4a`(경계 N08). `b047e`: `D0.W = 0`이면 `b04ca RTS`(C Clear). `b0486`: `JSR 4945e`(경계 N08; A0 반환). `b048c` `b0494` `b0496` `b04a2`: `D0 = |36| >> 1`(LSR), unsigned `< 18000`이면 `18000`. `b04a8`: 부호 `42(A6) WORD < 42(A0) WORD`이면 `b04b4`(`NEG.L D0`). `b04b6`: `D1 = −(3a ASR 1); 36 = D0; 3a = D1`; C Set.
- `b057e`/`b059e`: `A0 = b05de; JSR 1ab02`/`1ab80`; `b058a`/`b05aa` C clear면 `RTS`, set이면 부모 `62` 감소와 `JMP 2a00`.

## 구현 범위와 규약

- routing 9 범위(위 표). 짝수 PC 961개 중 block 시작 225, 내부 736(묶인 `af7b0` 포함). 내부 PC 직접 진입은 `unsupported animation objects n09 PC`다.
- **FLOW_ONLY 100개**(C 보존): `af552 af59e af5ac af5b0 af5b4 af5be af60e af62c af64a af672 af676 af698 af69e af6a4 af6c2 af6da af6de af6ec af70c af734 af738 af74a af74e af760 af764 af76e af7a0 af7aa af7ba af7c6 af7e6 af7f4 af806 af92c af932 af938 af952 af966 af96a af970 af974 af98c afc16 afc28 afc2e afc3a afc78 afc7c afc82 afc86 afc8c afc92 afc96 afcb0 afcba b005e b017a b01aa b01e2 b01e4 b01ea b0204 b0230 b0238 b023c b023e b0268 b0292 b029c b02b0 b02b4 b02b8 b0326 b0352 b0360 b036c b0370 b0372 b03e6 b03f0 b03f4 b03f6 b03fe b0400 b041a b0424 b0444 b0446 b044a b044e b0470 b0472 b0486 b04ca b057e b058a b059c b059e b05aa b05bc`(JSR/BSR/BRA/JMP/RTS/LEA/MOVEA/MOVEM/BTST/BSET/BCLR/BCHG/Scc와 Bcc만).
- **known 생산 17개**: Clear `b01c8 b01fa b0320 b042e b0358 b03d8 b041c b0468 b047e`, Set `b01d6 b01ee b031a b04b6`, 계산 `b0406 b0412 b0434 b0462`.
- 그 밖 108개는 Unknown.
- **소비자 19개**(위). Unknown이면 `objects n09 caller requires known carry`(상태 보존).
- 스택: 위 "스택". 홀수 주소 WORD/LONG(홀수 A6/A0/A7 등), work RAM 밖 쓰기, 미해결 ROM/bank 읽기는 기존 checked 오류다. I/O port 쓰기·bank 변경 없음.

## 의존·경계

- [F] N09 → 기존: 위 "나가는 호출". 실행부 없는 경계 `493bc` `4941e` `4945e` `4983e` `4ae4a`(멈춤만 test; 앞 셋 중 N08 PC와 `493bc` `4941e`는 다른 F4 단위 범위라 rollback 탐침으로 쓰지 않는다).
- [F] 다른 단위 → N09: U15 `af416`(설치 `af4ee`) `af480`(`af6ec`) `af4e6`(`af6de`), routing 밖 `af0dc`(`af6de`), 범위 밖 설치 `af926`(`af92c`) `afc10`(`afc16`) `afcea`(`af630`), 범위 밖 `BRA.W af96a`(`af8c8` `af90c`), `BRA.W b005e`(`afda2` `afe94` `aff4e` `b005a`), `JSR b0468`(`afe66`), `BSR.B b0228`(`b0240`, 참조 없음), 자료 LONG `4a704`(`b0260`). [F] 기존 test·도구 중 N09 PC를 경계·rollback으로 기대하는 곳 없음(scratch grep).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 225 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류, zero-step, 내부 736 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 범위 밖 자료/참조 없는 코드 중 다른 F4 단위가 아닌 것(`af80a` `b0240`)은 `unsupported animation machine PC`, 경계 `493bc` `4941e` `4945e` `4983e` `4ae4a`는 멈춤만, 소비자 19개 Unknown 오류, 생산자 Clear/Set/계산 값, DIVU overflow와 정상 몫, 소비자 C는 실제 생산자를 지나는 Unicorn fixture와 실제 ROM 차분의 native 분기로 확인.
- 실제 ROM 차분: callback과 모든 시작을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed): 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, seed 18 19 96 97 102 103의 진행 frame 측정.

## 작업자 검증 기록 (scratch, 계약 초안 구현)

- [F] 구현: `engine/src/animation_machine_objects_n09.cpp`(`animation_objects_n09_block`), routing 9 범위(`animation_machine.cpp` dispatch 사슬 끝 `else if` 1개), FLOW_ONLY 100개 case 묶음, `animation_machine_internal.h` 선언 1줄, Makefile(소스·test target·run 줄), `tools/verify_animation_machine.py` SOURCES. 단위 test `engine/tests/animation_machine_objects_n09_test.cpp`(scratch `ms5-scratch/n09/gen/gen.py`·`assemble.py`·`template.cpp`로 생성).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 없음. 단위 test: 701 fixture(checked 오류 29, known C 유지 267), 225 block × 3 carry, 내부 736 PC, zero-step, 홀수 PC, RAM `10fe10` `10fe20` `10fe30` `10fe40` rollback 탐침, 범위 밖 `af80a` `af80e` `b0240` `b0250`, 경계 멈춤 `493bc` `4941e` `4945e` `4983e` `4ae4a`. typed fixture가 225 시작 모두를 덮는다. UBSan(`-fsanitize=undefined -fno-sanitize-recover`) 통과.
- [F] DIVU fixture 11개(`D0.W` = 0 1 50 4fff 5000 5001 7fff 8000 ffff 1234 0123): `5000` 이상과 음수는 overflow로 `D0` 불변, 나머지는 `나머지:몫`. Unicorn native와 전체 상태가 같다.
- [F] 실제 ROM 차분(scratch `realrom/real9.py`, 시드 1·2·3 각 1,000 case, bank `200000`/`300000`, N10 포함): 불일치 0. 세 시드 합집합으로 243/243 시작 도달. 실제 생산자 뒤 소비자 native 분기 비교(세 시드 합) `af5b0` 49 `af64a` 100 `af6a4` 117 `af738` 309 `af74e` 110 `af764` 151 `af938` 93 `af970` 921 `afc78` 231 `afc92` 263 `b02b0` 83 `b03f0` 24 `b058a` 959 `b05aa` 242 `c5932` 4. 경계 멈춤 `493bc` 57 `4941e` 129 `4945e` 23 `4983e` 38 `4ae4a` 70. `16ea4`(sprite 실행부가 D7 목표를 검사)는 이 harness의 멈춤 PC로 두었다. native가 깨끗이 멈추지 않은 case는 건너뛰고 셌다(시드별 178~201).
- [F] 프레임 패스 차분(scratch `fp/new_sched`, `fp/new_rng`; 기준 `fp/base_*`): base 일치 pass 12,968·node 102,054, 불일치 0, 자연 완주 119(변화·회귀 0). RNG 400: 일치 pass 40,806·node 297,135(기준 40,800·297,077), 불일치 0, complete 102(새 0, 잃음 0; SHA256 `2f2b34079acbe29e1c88439c9fbf5c931bfb2c29980367e3fac67522862d6c58`). seed 18 19 96 97 102 103은 frame 0을 끝까지 일치(pass 0→1, node +9~10)하고 frame 1 callback `af6de` 안의 `b0362 JSR 4983e`(N08 경계)에서 상태 보존 checked 오류로 멈춘다. [I] N08 병합 뒤 다시 측정해야 이 6 seed의 진행을 알 수 있다.
- [F] ROM SHA256·mtime 작업 전후 같음. 무효화되는 기존 test·도구 기대 없음(U15/U16 test의 N09 PC는 범위 끝값과 설치 LONG 값뿐).

## 미확인·범위 밖

1. [I] `af4ee` 계열은 `9f`(0 = `af6de` 계열, ff = `af6ec` 계열)로 두 모드를 갖는 보행 객체로 보인다. `af71a`는 매 frame `b02ec`(방향 BYTE `a0`/`a1` 변화), `b041c`(대상 `76` 거리), `b0352`(무작위 1/8로 `4983e` 뒤 플레이어 `100cb8`/`100da8`와 사각형 판정)로 다음 상태(`af812` `af4ee` `af8cc` `af676`)를 고른다. 게임 의미는 미확인이다.
2. [U] 범위 밖 설치 사슬 `af812` `af8cc` `af990` `afbbe` `afcbe` `afed8`과 helper `b051a`는 이 단위 밖이다(고아 설치, 재범위 결정 3).
3. [U] N08 `4945e` `4983e` `4ae4a`의 C/A0 반환 계약은 N08 계약을 따른다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n09/`(`n09.py` block·범위·SHA 계산, `cls.py` carry 분류, `fmt.py` 목록, `n09dis.py` `hroute.py` `refs9.py`, `fp/` 기준·새 프레임 패스 차분; 저장소 밖).
