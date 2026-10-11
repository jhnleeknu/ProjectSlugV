# stage controller 완성 F1b: area clear(`47da4`) 계약 초안

**상태: 메인 결정 반영 계약. 구현·검증 기록이 아니다.** 범위 근거는 `animation-machine-stage-controller-f1-contract.md`(F1a 계약)의 "F1b 개요"와 `animation-machine-frontier-after-480bc-scope.md`의 F1이다. 구조와 규약(block 시작, 묶인 분기, carry 보존 목록, 계산 PC, 경계, 대기)은 확정된 F1a·U6·U7 계약을 따른다.

Claude Opus 5.5 / high 분석 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, fixed CPU 주소=file offset)을 capstone M68000으로 디코드했다. 기존 실행부는 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `cc28e6f`, U1~U7 WIP와 커밋되지 않은 F1a `animation_machine_stage_entry.cpp`·routing 포함)의 `engine/src`를 읽기 전용으로 참조했다. 기존 관측 산출물은 Unicorn으로 읽기 전용 재생했다. [F]=원본 바이트 또는 기록 산출물·작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. 명령 단위 정답은 원본 바이트 자체다. block 수는 scratch 스크립트(`f1b/leadb.py`, F1a의 `f1/lead.py` 규칙 재사용)가 원본 opcode에서 계산했다.

같은 루틴의 typed host 재구성(`engine/src/stage_entry*.cpp`, `game_startup.cpp` 등의 `107def`·`10d683` 쓰기)은 machine 실행부가 아니며 교차 확인 자료로만 쓴다.

메인 결정(Claude Opus 5.5 메인 리뷰, `47e00..47e50`·`1c5b0..1c5ea` capstone 재디코드로 carry 소비 근거 확인):
1. 새 실행부 `engine/src/animation_machine_area_clear.cpp`(`bool animation_area_clear_block(AnimationMachineContext&)`), routing 6 범위. Unknown carry 오류 문자열은 단위별 관례대로 `area clear caller requires known carry`.
2. frame 대기는 Waiting을 쓰지 않는다. 한 machine 실행=한 frame이며 `480f0 RTS`가 `2ac2`로 돌아가면 `2ac2` stop으로 끝내고, 다음 frame은 F1a 결정 7(c)의 선언된 직접 재진입(A6=`100b30`, A5=`108000`, `(A7)`=`2ac2`, PC=`(A6)` callback LONG)으로 둔다. 마지막 frame은 `477ee` stop.
3. 자식 완료(`62(A6)`), `10dd44`, `10d68e`, `10d683` bit0은 frame 사이 선언된 host 쓰기로만 바꾼다. 자식 `e4234`/`d72fe` 실행은 범위 밖이며 `2ac2` stop이 그 진입을 막는다.
4. `47e3a JSR 28ae` 실패는 원본대로 구현한다(fallback A0=`100e98`, WORD `100f0e` 쓰기, 오류 아님).
5. 자연 검증: 모든 frame의 전체 상태 SHA(64KiB RAM·16R·PC·A7·bank·port 순서열)를 기록하고 전체 dump는 경계 frame(0, 29, 188, 189, 236)과 typed fixture 전부, 그리고 자연 seed 8개의 모든 frame에 둔다. C++ 검증은 모든 frame에서 SHA 일치, dump가 있는 frame에서 바이트 비교를 한다.
6. 직접 진입 문맥은 권고대로(A6=`100b30`, SP `10effc`, `(A7)`=`2ac2`). transition case 77 연결은 `47de4`까지 부분 실행으로만 쓴다.
7. (F1b core 보고 반영) 자연 seed는 137 begin 출력이다. 5 release 출력은 WORD `104d8a`=`8001` 때문에 U1 `3c60`에서 홀수 주소 `fcd83` WORD 읽기(실제 68000 address error)가 나므로 guard row로만 쓴다. 본문의 "142건 모두 `477ee` 도달"은 address error를 모델링하지 않는 Unicorn 결과다.

## 요약

- [F] F1b는 코드 6 범위 376바이트, 81명령, 미해독 0이다. **block 시작 39개**(일반 규칙 34 + `MOVE.L #imm,(A6)`로 설치되는 dispatcher callback 5)다. 짝수 PC 188개 중 내부 PC는 149개다. F1a 개요의 39와 같다.
- [F] F1b 안에는 TRAP, 계산 PC 표, PVC bank 쓰기, ROM 자료 읽기가 **없다**. 모든 피연산자는 즉치값, RAM, PC 상대 주소 계산(`1bee4` LEA, 읽기 없음)이다.
- [F] 끝은 `47ea8 BRA 477ee`(F1c 경계, 실행부 없음)이다. frame 사이 대기는 모두 `BNE/BEQ 480bc` → U1 `480bc`..`480f0 RTS` → dispatcher 복귀 `2ac2`로 표현된다. 새 상태 값이나 Waiting은 필요 없다(결정 2).
- [F] 자연 reach는 없다. 다만 stage_entry_body begin 출력 137개 RAM에 `47da4` 직접 진입하면(F1a의 `47c04` 직접 진입과 같은 유형) scratch Unicorn 재생에서 137개 모두 선언 host write 1건(`10dd44`)만으로 237 frame 뒤 `477ee`에 도달했다.

| 항목 | 값 |
| --- | --- |
| 진입 | `47d6e BNE 47da4`(transition, 유일한 참조) |
| callback | `47de4` `47e22` `47e62` `47e70` `47e92` |
| 끝 | 매 frame `480bc`→`2ac2`; 마지막 frame `47ea8 BRA 477ee` |
| block 시작 | 39 |
| 묶인 조건분기(Z) | 6 |
| carry 소비 block | 3(`1c5bc` `1c5d8` `47e0a`) |
| carry 보존(FLOW_ONLY) | 16 |
| 기존 실행부 출구 | `289e` `2a48` `28ae` `3af8` `8c16` `9060` `49c20` `480bc` |
| 경계(실행부 없음) | `477ee` |

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

### 1. 실행부 파일과 routing

- 선택 A(**작업자 권고**): 새 실행부 파일 `engine/src/animation_machine_area_clear.cpp`(`animation_area_clear_block`)와 routing 6 범위(아래)를 둔다. F1a `animation_machine_stage_entry.cpp`가 아직 커밋 전 WIP라 파일 충돌을 피할 수 있다. unit 단위 파일 관례(U1~U7, F1a)와도 맞다.
- 선택 B: `animation_machine_stage_entry.cpp`에 F1b block을 더한다. F1a 리뷰가 끝난 뒤에만 가능하다.
- Unknown carry 오류 문자열 제안: `area clear caller requires known carry`. F1a WIP는 `stage entry caller requires known carry`를 쓴다. 공용 문자열로 맞출지도 메인 결정이다.

### 2. frame 대기와 재진입 모델 (가장 중요)

**원본 동작**
- [F] 다섯 대기는 모두 같은 모양이다. `MOVE.L #callback,(A6)`로 다음 frame 진입점을 node에 두고, 같은 frame에서 callback 본문으로 fall-through한다. 조건이 아직 안 되면 `BNE.W/BEQ.W 480bc`로 U1 frame helper를 실행하고 `480f0 RTS`로 dispatcher에 돌아간다.
  - `47de4`/`47e62`/`47e92`: `SUBQ.W #1,7a(A6)`; `BNE.W 480bc`(WORD 결과의 Z).
  - `47e22`: `TST.B 62(A6)`; `BEQ.W 480bc`.
  - `47e70`: `TST.B 5d44(A5)`(BYTE `10dd44`); `BEQ.W 480bc`.
- [F] dispatcher는 `2ab8` LEA A5 → `2abe MOVEA.L (A6),A0` → `2ac0 JSR (A0)`(복귀 `2ac2`) → `2ac2 MOVEA.L 8(A6),A6` → `2ac6 BRA 2ab8`이다. 기존 fade_card 실행부가 이 다섯 block을 실행한다.
- [F] 따라서 F1b의 "frame 대기"는 원본에서 바쁜 대기가 아니다. callback이 정상 복귀하고 다음 frame의 dispatcher 호출에서 같은 callback이 다시 불린다. 기존 Waiting(`3aea` sound, `cda4` sprite, F1a `47af0` gate)과는 다르다. 그것들은 원본 자체가 같은 PC에서 spin하는 경우다.
- [F] 기존 선례: F1a 결정 7(c)는 `47af0`/`47b5c`/`47bfc` 재진입을 "선언 디스패처 재진입(A6=`100b30`, A5=`108000`, `(A7)`=복귀 LONG `2ac2`)"으로 정했다. F1a WIP test(`animation_machine_stage_entry_test.cpp`)는 SP=`10effc`, LONG `10effc`=`2ac2`, NODE=`100b30`, RET_FRAME=`2ac2`를 쓴다. fade_card `48090`(`SUBQ`/`BEQ`, callback `4806a`/`48090`)도 같은 구조이며 Waiting을 쓰지 않는다.
- [F] `28ae`는 새 자식 node를 부모 바로 뒤에 연결한다(`28fc MOVE.L A0,8(A6)`). 그래서 원본에서는 같은 dispatcher pass에서 `2ac2` 다음에 자식 callback(`e4234`, `d72fe`)이 실행된다. 이 자식들은 실행부가 없다.

**선택지**
- 선택 A(**작업자 권고**): 새 상태 값을 두지 않는다. 한 frame은 callback PC(첫 frame은 `47da4`) 직접 진입부터 stop `2ac2`까지의 한 번의 `run_animation_machine` 호출이다. 다음 frame은 출력 상태에서 F1a 결정 7(c)와 같은 선언 재진입(A6=`100b30`, A5=`108000`, `(A7)`=`2ac2`, PC=`(A6)` LONG)으로 시작한다. 마지막 frame은 stop `477ee`로 실행한다. stop을 `2ac2`로 두지 않으면 `2ac2`→`2ab8`→자식 callback으로 진행해 `unsupported animation machine PC`로 전체 rollback된다(이는 음성 검사로 쓴다).
- 선택 B: callback 대기 지점에서 `c.waiting=true`로 Waiting을 돌려준다. 원본에는 그 지점의 spin이 없어 비권고다. `480bc` frame helper를 건너뛰게 되어 U1~U7 통합 검증도 사라진다.
- 선택 C: dispatcher `2abe`에서 시작해 `2ac2`에서 멈춘다(F1a scratch `second.py`와 같은 방식). A와 결과가 같고 `2abe`/`2ac0` 두 block이 더 실행된다. 검증 도구에서 A의 보조 변형으로 둘 수 있다.

### 3. 외부 생산자(자식 완료·`10dd44`·`10d68e`·`10d683` bit0) 표현

- [F] 각 값을 쓰는 원본 코드:
  - `62(A6)`: 자식 `e4234` 끝 `e43fe MOVEA.L c(A6),A0`; `MOVE.B #1,62(A0)`; `JMP 2a00`. `c(child)`=부모는 `28ae`의 `28de MOVE.L A6,c(A0)`가 쓴다.
  - `10dd44`: 객체 코드의 `ST.B 5d44(A5)`(`50c22`, `511be` 등 fixed 15곳 중 쓰기)와 `CLR.B`(`1d77c`, `1d854`, `1d86e`).
  - `10d68e`: 매 frame U1 `47642`가 지우고, 두 player node(`100cb8`/`100da8`)가 `289e` C=1이고 `61(A0)` bit7=0이면 bit0/1을 세운다(`4766a BSET D0,568e(A5)`).
  - `10d683` bit0: 유일한 쓰기 `4833e BSET #0,5683(A5)`. 객체 코드 9곳(`50c54`, `51476`, …, `f0172`)에서 LONG 리터럴로 참조된다.
- 선택 A(**작업자 권고**): F1a `47bfc`(`62(A6)`)·결정 2와 같이 선언 host write로 둔다. frame 사이(`2ac2` stop 뒤, 다음 재진입 전)에만 적용한다. 자식 `e4234`/`d72fe`와 객체 코드는 F1b 범위 밖이다. 적용 값은 원본 쓰기와 같게 둔다(`62(A6)`=`01`, `10dd44`=`ff`, `10d68e`=player mask, `10d683`|=1).
- 선택 B: 자식 `e4234`·`d72fe`까지 F1b에 넣는다. 정적 closure가 크게 늘고(`e4234..e4412`만 수백 바이트, `8c16`·`3af8`·`28ae`·`e3aec` 호출) 자연 seed도 없다. 비권고.

### 4. `47e3a JSR 28ae` 뒤 carry 미검사

- [F] `28ae` 실패(C=0)는 `290e LEA -7168(A5),A0`(A0=`100e98`), `ANDI #fe,CCR`, RTS다. 실패 조건은 D0.W ≥ WORD `104ca0`(무부호) 또는 A0=0이다. `47e30`은 D0.W=`14`, A0=`d72fe`이므로 [F] 실패는 WORD `104ca0` ≤ `14`일 때뿐이다.
- [F] `47e40`은 C를 보지 않고 `MOVE.W D0,76(A0)`를 한다. 실패면 WORD `100f0e`(`100e98`+`76`)에 `7c(A6)`+1이 쓰인다. scratch 재생(`104ca0`=`14`: 첫 `28ae` 성공, 둘째 실패)에서 `100f0e`=`0001`이 확인됐다.
- 권고: 원본대로 쓴다. 오류로 바꾸지 않는다. `47e40`은 carry 보존 block이 아니며 C를 소비하지 않는다.

### 5. 자연 검증 규모와 산출물

- [F] 자연 RAM 직접 진입 1 seed는 237 frame(선언 write 1건)이다. 137 seed면 32,469 frame 실행이다.
- 선택 A(**작업자 권고**): 새 관측 산출물(제안 `artifacts/animation_machine_area_clear_native`, 도구 `tools/observe_animation_machine_area_clear.py`)을 만든다. 137 seed의 모든 frame에 대해 RAM/PVC/16R/ports SHA256을 남기고, 전체 64 KiB 덤프는 phase 경계 frame(0, 29, 188, 189, 236과 각 typed 변형의 대기 해제 frame)에만 남긴다. C++는 frame마다 직전 C++ 출력에서 재개하고, 같은 frame의 Unicorn 해시와 비교한다.
- 선택 B: 전체 frame 덤프. 137×237×64 KiB ≈ 2.1 GB로 비권고.
- 선택 C: seed 일부(예: family별 대표)만 전 frame, 나머지는 frame 0·29만.

### 6. 직접 진입 문맥

- 권고: `47da4` 직접 진입은 A6=`100b30`, A5=`108000`, callback 수준 A7(F1a WIP와 같은 RAM mirror SP `10effc`, LONG=`2ac2`)로 둔다. [F] F1b block은 A6 상대·A5 상대·절대(`100cb8`, `100da8`, `107def`)만 쓴다. A6 값 자체에 의존하는 분기는 없다.
- [F] transition 관측 case 77(`negative-gate1-bit1`)은 A6=`102000`, 고립 stack `1feffc`, 진입 `47d60`, stop `47da4`이다. 이를 이어 실행하는 연결 검사는 부분 stop(`47de4`)까지만 권고한다. 그 RAM은 대부분 0인 합성 fixture라 `480bc` 전체 frame의 의미가 없다.

## 원본 바이트 근거

[F] 코드 6 범위 합계 376바이트, 81명령, 미해독 0이다. 범위 안 빈틈은 없다.

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `47da4..47eac` | `4eb90004b6e44eb90004b6ec41ed8bf44eb900002a484eb90001c5b04eb90001bee408ad0005568308ad000156834eb90000ca483d7c001e007a2cbc00047de4536e007a660002d24a2d568e6700003e4eb900009056207c000e4234303c00004eb9000028ae54ee00626400000c7000102e007c314000762cbc00047e224a2e0062670002944eb900009060207c000d72fe303c00144eb9000028ae7000102e007c524031400076303c19db4eb900003af83d7c00a0007a2cbc00047e62536e007a660002542cbc00047e704a2d5d446700024670e172e174e176304eb900008c163d7c0030007a2cbc00047e92536e007a66000224522e007c1b6e007c5680422d56816000f944` |
| `4b6e4..4b6f4` | `1b7c00ff5b854e751b7c00ff5b874e75` |
| `1c5b0..1c5ea` | `41f900100cb84eb90000289e6400000e08e80006006108e8000000a841f900100da84eb90000289e6400000e08e80006006108e8000000a84e75` |
| `1bee4..1bef8` | `41faffda70004eb900049c2070014ef900049c20` |
| `ca48..ca50` | `1b7c00ff89674e75` |
| `9056..9060` | `13fc00ff00107def4e75` |

- [F] 인접 경계:
  - `47da0 BRA 480bc`까지는 transition(routing `47d24..47da4`), `47eac`부터는 exit(routing `47eac..47fca`)이다.
  - `4b6f4`는 다른 루틴(`TST.B 5b86`)이다.
  - `1c5ea`는 다른 루틴(`482e2`에서 호출)이다.
  - `1bef8..1bf02`는 자료(`0101…0100`)이다. `1bec0..1bee4`는 U6이다.
  - `ca50`은 다른 루틴(`TST.B -7699`)이다. `ca56`은 F1a다.
  - `9060`은 F1a다.
- [F] 기존 routing(WIP `animation_machine.cpp`, F1a 포함)과 겹침이 없다. 6 범위의 모든 짝수 PC가 현재 routing에서 미배정이다(`animation_machine.cpp` 범위 조건 대조).
- [F] 참조: `47da4`는 `47d6e BNE.W`의 유일한 대상이다. fixed 1 MiB의 Bcc/BRA/BSR/JSR(PC)/LEA(PC) 변위 스캔과 8 MiB LONG `00047da4` 검색 결과 다른 참조는 없다. 스캔에서 나온 `41e60`→`47e62`는 자료 영역(`a000 e000 …`)의 우연한 일치다. callback LONG `00047de4` 등은 각 `MOVE.L #imm` 명령 안에만 있다.

### block 목록(39)

| block | 원본 바이트 | 명령 |
| --- | --- | --- |
| `47da4` | `4eb90004b6e4` | jsr 4b6e4.l |
| `47daa` | `4eb90004b6ec` | jsr 4b6ec.l |
| `47db0` | `41ed8bf44eb900002a48` | lea.l -740c(a5), a0; jsr 2a48.l |
| `47dba` | `4eb90001c5b0` | jsr 1c5b0.l |
| `47dc0` | `4eb90001bee4` | jsr 1bee4.l |
| `47dc6` | `08ad0005568308ad000156834eb90000ca48` | bclr.b #5, 5683(a5); bclr.b #1, 5683(a5); jsr ca48.l |
| `47dd8` | `3d7c001e007a2cbc00047de4` | move.w #1e, 7a(a6); move.l #47de4, (a6) |
| `47de4` | `536e007a660002d2` | subq.w #1, 7a(a6); bne.w 480bc |
| `47dec` | `4a2d568e6700003e` | tst.b 568e(a5); beq.w 47e30 |
| `47df4` | `4eb900009056` | jsr 9056.l |
| `47dfa` | `207c000e4234303c00004eb9000028ae` | movea.l #e4234, a0; move.w #0, d0; jsr 28ae.l |
| `47e0a` | `54ee00626400000c` | scc.b 62(a6); bcc.w 47e1c |
| `47e12` | `7000102e007c31400076` | moveq #0, d0; move.b 7c(a6), d0; move.w d0, 76(a0) |
| `47e1c` | `2cbc00047e22` | move.l #47e22, (a6) |
| `47e22` | `4a2e006267000294` | tst.b 62(a6); beq.w 480bc |
| `47e2a` | `4eb900009060` | jsr 9060.l |
| `47e30` | `207c000d72fe303c00144eb9000028ae` | movea.l #d72fe, a0; move.w #14, d0; jsr 28ae.l |
| `47e40` | `7000102e007c524031400076303c19db4eb900003af8` | moveq #0, d0; move.b 7c(a6), d0; addq.w #1, d0; move.w d0, 76(a0); move.w #19db, d0; jsr 3af8.l |
| `47e56` | `3d7c00a0007a2cbc00047e62` | move.w #a0, 7a(a6); move.l #47e62, (a6) |
| `47e62` | `536e007a66000254` | subq.w #1, 7a(a6); bne.w 480bc |
| `47e6a` | `2cbc00047e70` | move.l #47e70, (a6) |
| `47e70` | `4a2d5d4467000246` | tst.b 5d44(a5); beq.w 480bc |
| `47e78` | `70e172e174e176304eb900008c16` | moveq #e1, d0; moveq #e1, d1; moveq #e1, d2; moveq #30, d3; jsr 8c16.l |
| `47e86` | `3d7c0030007a2cbc00047e92` | move.w #30, 7a(a6); move.l #47e92, (a6) |
| `47e92` | `536e007a66000224` | subq.w #1, 7a(a6); bne.w 480bc |
| `47e9a` | `522e007c1b6e007c5680422d56816000f944` | addq.b #1, 7c(a6); move.b 7c(a6), 5680(a5); clr.b 5681(a5); bra.w 477ee |
| `4b6e4` | `1b7c00ff5b854e75` | move.b #ff, 5b85(a5); rts |
| `4b6ec` | `1b7c00ff5b874e75` | move.b #ff, 5b87(a5); rts |
| `1c5b0` | `41f900100cb84eb90000289e` | lea.l 100cb8.l, a0; jsr 289e.l |
| `1c5bc` | `6400000e` | bcc.w 1c5cc |
| `1c5c0` | `08e80006006108e8000000a8` | bset.b #6, 61(a0); bset.b #0, a8(a0) |
| `1c5cc` | `41f900100da84eb90000289e` | lea.l 100da8.l, a0; jsr 289e.l |
| `1c5d8` | `6400000e` | bcc.w 1c5e8 |
| `1c5dc` | `08e80006006108e8000000a8` | bset.b #6, 61(a0); bset.b #0, a8(a0) |
| `1c5e8` | `4e75` | rts |
| `1bee4` | `41faffda70004eb900049c20` | lea.l 1bec0(pc), a0; moveq #0, d0; jsr 49c20.l |
| `1bef0` | `70014ef900049c20` | moveq #1, d0; jmp 49c20.l |
| `ca48` | `1b7c00ff89674e75` | move.b #ff, -7699(a5); rts |
| `9056` | `13fc00ff00107def4e75` | move.b #ff, 107def.l; rts |

## 실행 의미

[F] A5 상대 d16은 live A5로 계산한다. 아래 절대 주소는 A5=`108000` 기준이다(`5683`→`10d683`, `568e`→`10d68e`, `5680`/`5681`→`10d680`/`10d681`, `5d44`→`10dd44`, `5b85`/`5b87`→`10db85`/`10db87`, `-740c`→`100bf4`, `-7699`→`100967`). 절대 LONG 주소를 쓰는 명령은 A5와 무관하다: `1c5b0`/`1c5cc` LEA, `9056`. [F] `47db4` 이후 호출된 `2a48`(→`299c`), `28ae`, `8c16`은 각자 A5=`108000`을 다시 쓴다. 공통 폭 규칙은 U2·F1a와 같다. MOVE.W/MOVE.B Dn은 나머지 bit를 보존하고, MOVEQ는 LONG 전체를 쓴다. X 소비 명령은 F1b에 없다.

1. **첫 frame 준비(`47da4`..`47dde`, 같은 frame).**
   - `47da4` JSR `4b6e4`(BYTE `ff`→`10db85`, 복귀 `47daa`). `47daa` JSR `4b6ec`(BYTE `ff`→`10db87`, 복귀 `47db0`).
     - [F] 두 BYTE의 소비자는 U7 `4ab36..4ab48`(`5b85`→`5b84`, `5b87`→`5b86`로 복사 후 0)다. 초기화는 U7 `4aa30..4aa42`다. 같은 frame의 `480bc` 안에서 소비된다.
   - `47db0`: A0=`100bf4`, JSR `2a48`(cleanup, 복귀 `47dba`).
     - [F] `2a48`은 WORD `10(A0)`(=`100c04`)≠0이면 `2a52 TRAP #15`다. 기존 cleanup 실행부는 이를 checked 오류 `animation cleanup original TRAP15: nonzero object type`로 처리한다.
     - 0이면 push A6, A6=A0, BSR `299c`(port BYTE `300001`←D0.B, BSR `2782`, LONG `270e`→`(100bf4)`, 해제·연결 정리), pop A6, RTS. 이 node는 F1a `e905c`가 `2a28`로 설치한 stage event node(`e9150`)다.
   - `47dba` JSR `1c5b0`(복귀 `47dc0`).
     - `1c5b0`: A0=`100cb8`, JSR `289e`(readiness, 복귀 `1c5bc`). `289e`는 LONG `(A0)`==`270e`이면 C=0, 아니면 C=1(ORI)이다.
     - `1c5bc` BCC `1c5cc`. C=1이면 `1c5c0` BSET #6,`100d19`, BSET #0,`100d60`이다.
     - `1c5cc`: A0=`100da8`, JSR `289e`(복귀 `1c5d8`). `1c5d8` BCC `1c5e8`. C=1이면 `1c5dc` BSET #6,`100e09`, BSET #0,`100e50`이다.
     - `1c5e8` RTS.
   - `47dc0` JSR `1bee4`(복귀 `47dc6`).
     - `1bee4`: A0=`1bec0`(PC 상대 주소 계산만), D0=0(MOVEQ), JSR `49c20`(U6, 복귀 `1bef0`). `49c20`은 LONG A0→`10d734`다.
     - `1bef0`: D0=1, **JMP** `49c20`. LONG A0→`10d738`이고, `49c20`의 RTS가 `47dc6`으로 돌아간다.
     - 끝 상태: D0=`00000004`(`ANDI.W #1`/`LSL.W #2`), A1=`10d738`, A0=`1bec0`.
     - [F] 두 slot은 U6 `49b0c`가 player node `289e` C=1일 때만 `JSR (A1)`로 부른다.
   - `47dc6`: BCLR #5, BCLR #1 BYTE `10d683`; JSR `ca48`(BYTE `ff`→`100967`, 복귀 `47dd8`).
   - `47dd8`: WORD `1e`→`7a(A6)`, LONG `47de4`→`(A6)`. `47de4`로 fall-through한다.
2. **30 frame timer(`47de4`).** SUBQ.W #1,`7a(A6)`. 결과 WORD≠0이면 `480bc`. [F] 준비 frame이 첫 감소를 하므로 `7a`=`1e`에서 30번째 호출(준비 frame 포함)에 0이 되어 `47dec`로 간다. 0에서 감소하면 `ffff`가 되어 65,535 frame을 더 기다린다(원본대로).
3. **player 생존 분기(`47dec`, 같은 frame).** TST.B `10d68e`. 0이면 `47e30`. [F] 이 값은 직전 frame `480bc`의 `47642`가 계산한 것이다(이번 frame의 `480bc`보다 먼저 읽힌다).
   - `47df4` JSR `9056`(BYTE `ff`→절대 `107def`, 복귀 `47dfa`).
   - `47dfa`: A0=`e4234`, D0.W=0, JSR `28ae`(fade_card, 복귀 `47e0a`). 성공 C=1, A0=새 node이다. 실패 C=0, A0=`100e98`이다.
   - `47e0a`: **SCC.B `62(A6)`**: C=0이면 BYTE `ff`, C=1이면 `00`. CCR은 바뀌지 않는다. 이어서 BCC `47e1c`.
     - 성공(C=1)이면 `47e12`: D0=0, D0.B=BYTE `7c(A6)`, WORD D0→`76(A0)`(자식)이다.
   - `47e1c`: LONG `47e22`→`(A6)`. `47e22`로 fall-through한다.
   - `47e22`(callback): TST.B `62(A6)`. 0이면 `480bc`(자식 완료 대기)다. 실패 경로는 `ff`이므로 같은 frame에 통과한다.
   - `47e2a` JSR `9060`(F1a, CLR.B `107def`, 복귀 `47e30`).
4. **자식 `d72fe`와 sound(`47e30`, 같은 frame).**
   - A0=`d72fe`, D0.W=`14`, JSR `28ae`(복귀 `47e40`). C 검사는 없다(결정 4).
   - `47e40`: D0=0, D0.B=`7c(A6)`, ADDQ.W #1(WORD, `ff`→`0100`), WORD→`76(A0)`.
   - D0.W=`19db`, JSR `3af8`(sound queue, 복귀 `47e56`). 기존 sound 실행부의 `3aea` Waiting이 가능하다.
   - `47e56`: WORD `a0`→`7a(A6)`, LONG `47e62`→`(A6)`, fall-through.
5. **160 frame timer(`47e62`).** `47de4`와 같다. 0이 되는 frame에 `47e6a` LONG `47e70`→`(A6)`, fall-through.
6. **`10dd44` poll(`47e70`).** TST.B `10dd44`. 0이면 `480bc`다. 매 frame 다시 검사한다.
7. **fade와 48 frame(`47e78`).**
   - D0=D1=D2=`ffffffe1`, D3=`00000030`(MOVEQ, LONG 전체), JSR `8c16`(exit, 복귀 `47e86`).
   - `47e86`: WORD `30`→`7a(A6)`, LONG `47e92`→`(A6)`, fall-through.
   - `47e92` timer. 0이 되면 `47e9a`.
8. **다음 area(`47e9a`).** ADDQ.B #1,`7c(A6)`(BYTE, `ff`→`00`), BYTE `7c(A6)`→`10d680`, CLR.B `10d681`, BRA `477ee`(F1c 경계). [F] `477ee`는 `10d680`→`7c(A6)`, `10d681`→`7d(A6)`를 읽는다(F1c).

[F] F1b block 자신의 port·PVC 쓰기와 ROM 읽기는 없다. port 쓰기는 callee `299c`(BYTE `300001`)와 `480bc` helper(기존 실행부)에서만 생긴다.

## 구현 범위와 규약

- **routing 6 범위**: `47da4..47eac`, `4b6e4..4b6f4`, `1c5b0..1c5ea`, `1bee4..1bef8`, `ca48..ca50`, `9056..9060`. [F] 짝수 PC는 188개이다. block 시작 39를 빼면 내부 PC는 149개다.
- **Block 시작 PC (39개)**: 루틴 진입, 분기 대상, 조건분기 fall-through, 호출 복귀, dispatcher callback 진입 5개. 일반 규칙으로 34개를 계산했고 callback `47de4` `47e22` `47e62` `47e70` `47e92`를 더했다.

`9056` `ca48` `1bee4` `1bef0` `1c5b0` `1c5bc` `1c5c0` `1c5cc` `1c5d8` `1c5dc` `1c5e8` `47da4` `47daa` `47db0` `47dba` `47dc0` `47dc6` `47dd8` `47de4` `47dec` `47df4` `47dfa` `47e0a` `47e12` `47e1c` `47e22` `47e2a` `47e30` `47e40` `47e56` `47e62` `47e6a` `47e70` `47e78` `47e86` `47e92` `47e9a` `4b6e4` `4b6ec`

- **묶인 조건분기 PC (6개, 직접 진입 거부)**: `47de8` `47df0` `47e26` `47e66` `47e74` `47e96`. [F] 모두 같은 block의 SUBQ.W(Z) 또는 TST.B(Z) 뒤에 온다. 이전 block의 Z나 N을 소비하는 block 시작은 없다.
- **Carry 소비 block (3개)**: `1c5bc`·`1c5d8`(`289e`의 C), `47e0a`(`28ae`의 C).
  - [F] `47e0a`는 SCC.B로 C를 메모리 BYTE로 옮기고 같은 C로 BCC한다. 내부 PC `47e0e`(BCC)는 생산자가 block 밖에 있으므로 묶인 분기 목록과 따로 두고 내부 PC로 거부한다.
  - 진입 C가 Unknown이면 checked 오류(결정 1의 문자열)와 전체 rollback이다. SCC 쓰기 전에 검사한다. 어차피 rollback이므로 결과는 같다.
- **Known carry 생산 block**: F1b 안에는 없다. [F] 생산자는 기존 실행부다. `289e`(block 안 `return_carry`), `28ae`의 `2908`(Set)/`290e`(Clear)이며, 복귀 block `290c`/`2916`/`28ac`는 이미 보존 목록에 있다.
- **Carry 보존(FLOW_ONLY) block (16개)**: `1c5b0` `1c5bc` `1c5c0` `1c5cc` `1c5d8` `1c5dc` `1c5e8` `47da4` `47daa` `47db0` `47dba` `47dc0` `47dc6` `47df4` `47e0a` `47e2a`.
  - 기준은 F1a와 같다. 전 명령이 LEA/MOVEA/JSR/JMP/BSR/BRA/RTS/BTST/BSET/BCLR/조건분기인 block에 **Scc**를 더했다. [F] M68000에서 Scc는 condition code를 바꾸지 않는다.
  - [I] 정확성에 필요한 것은 `1c5bc`·`1c5d8`·`47e0a`(소비 block 자신)뿐이다. 나머지는 규약상 목록이다.
  - `47dfa`·`47e30`(MOVE.W #imm,D0 포함)·`47e12`·`47e40`(MOVEQ) 등은 Unknown으로 둔다.
- **경계(실행부 없음)**: `477ee`(F1c). stop=`477ee`이면 그 직전 상태로 멈추고, 아니면 `unsupported animation machine PC`로 rollback한다. F1b에는 TRAP 경계가 없다. `2a52` TRAP은 기존 cleanup 실행부의 checked 오류다.
- **기존 실행부로 나가는 지점(모두 기존 block 시작임을 확인)**:

| 대상 | 실행부 | 나가는 곳 → 복귀 |
| --- | --- | --- |
| `2a48` | cleanup | `47db4`→`47dba` |
| `289e` | readiness | `1c5b6`→`1c5bc`, `1c5d2`→`1c5d8` |
| `49c20` | input(U6) | `1beea`→`1bef0`, `1bef2` JMP(복귀는 `47dc6`) |
| `28ae` | fade_card | `47e04`→`47e0a`, `47e3a`→`47e40` |
| `9060` | stage_entry(F1a) | `47e2a`→`47e30` |
| `3af8` | sound | `47e50`→`47e56` |
| `8c16` | exit | `47e80`→`47e86` |
| `480bc` | frame helpers(U1) | `47de8`/`47e26`/`47e66`/`47e74`/`47e96` Bcc |

- 폭·연산:
  - BSET/BCLR 메모리 bit 번호는 mod 8이며 BYTE read-modify-write다.
  - `SUBQ.W #1,7a(A6)`+BNE는 WORD 결과의 Z만 쓴다(F1a `47b5c`의 BCC=borrow와 다르다).
  - `SCC.B` 메모리는 machine에서 BYTE 쓰기 1회로 둔다(fade_card `c38e` CLR.B 주석과 같은 층위). [I] 68000의 Scc/CLR read-before-write는 RAM 대상이라 관측 차이가 없다.
  - `ADDQ.B #1,7c(A6)`는 BYTE wrap, `47e46 ADDQ.W #1,D0`는 WORD다. `76(A0)`에는 WORD `0100`까지 쓰일 수 있다.
  - MOVEQ `e1`은 LONG `ffffffe1`이다.
  - 홀수 A6/A0에서 WORD/LONG 접근(`7a`, `(A6)`, `76(A0)`)은 기존 checked 오류와 rollback이다. BYTE `62`/`7c`/`61`/`a8`는 홀수도 허용한다.
- 루프: F1b 안에는 루프가 없다. frame 대기는 결정 2를 따른다.
- 기존 회귀 탐침 갱신이 필요하다. [F] 아래 PC가 미연결 탐침으로 쓰인다.
  - `engine/tests/animation_machine_motion_walk_test.cpp:773`: `outside[]`의 `0x47da4`가 `unsupported animation machine PC` 탐침이다. block 시작이 되므로 F1c PC(예: `477e4`, `47800`) 또는 `4b6f4`로 옮긴다.
  - `engine/tests/animation_machine_input_test.cpp:885`: `outside[]`의 `0x1bee4`가 같은 탐침이다. `1bef8`(자료, 미연결) 등으로 옮긴다.
  - `animation_machine_transition_test.cpp:72`와 `tools/verify_animation_machine_transition.py:322`는 stop=`47da4`로 쓴다. stop은 routing보다 먼저 검사되므로 변경이 필요 없다. F1b 연결 뒤에도 같은 결과임을 회귀로 확인한다.

## 대기·frame 진행의 근거

- [F] F1b의 다섯 대기는 원본 spin이 아니라 callback 복귀다(결정 2). machine에서 한 frame은 `480bc`(U1~U7 전체)→`480f0 RTS`→`2ac2` stop이다.
- [F] scratch 재생에서 natural RAM seed의 frame 수:

| frame(0부터) | 실행 block | 끝 |
| --- | --- | --- |
| 0 | `47da4`→…→`47dd8`→`47de4` | `480bc`→`2ac2`, `7a`=`1d` |
| 1..28 | `47de4` | `2ac2` |
| 29 | `47de4` `47dec` `47e30` `47e40` `47e56` `47e62` | `2ac2`, `7a`=`9f` |
| 30..187 | `47e62` | `2ac2` |
| 188 | `47e62` `47e6a` `47e70` | `2ac2`(`10dd44`=0) |
| (host write `10dd44`=`ff`) | | |
| 189 | `47e70` `47e78` `47e86` `47e92` | `2ac2`, `7a`=`2f` |
| 190..235 | `47e92` | `2ac2` |
| 236 | `47e92` `47e9a` | `477ee` |

  - `10dd44`≠0이 frame 188에 이미 성립하면 frame 188에 `47e78`까지 가며 총 236 frame이다.
  - player 생존 분기에서 `28ae` 성공이면 `47e22` 대기 frame이 최소 1개 더 생긴다(아래 typed 변형).
- [F] 기존 실제 대기와의 관계: `47e50`의 `3af8`→`3be4`→`3ac8`→`3aea`(ring 가득)는 기존 sound Waiting이다. `480bc` 안의 `cda4`/`3aea`도 기존대로 Waiting을 돌려준다. 재개는 기존 규약(같은 PC·A7에서 재호출)이다. 이번 재생 142 seed에서는 Waiting이 0건이었다.

## I/O: RAM·ROM·MMIO

**F1b block이 직접 읽고 쓰는 RAM(A5=`108000`, A6=`100b30` 기준)**

| 주소 | 폭 | 읽기/쓰기 | 위치 |
| --- | --- | --- | --- |
| `10db85` / `10db87` | B | W `ff` | `4b6e4` / `4b6ec` |
| `100bf4` | (A0) | callee `2a48`이 node 해제 | `47db0` |
| `100cb8`/`100da8` LONG | L | R(`289e`) | `1c5b0`/`1c5cc` |
| `100d19`/`100d60`, `100e09`/`100e50` | B | RMW bit6/bit0 | `1c5c0`/`1c5dc` |
| `10d734` / `10d738` | L | W `0001bec0` | `49c20`(U6) |
| `10d683` | B | RMW bit5·bit1 해제 | `47dc6` |
| `100967` | B | W `ff` | `ca48` |
| `7a(A6)`=`100baa` | W | W `1e`/`a0`/`30`, RMW −1 | `47dd8` `47e56` `47e86` / `47de4` `47e62` `47e92` |
| `(A6)`=`100b30` | L | W callback 5종 | `47dd8` `47e1c` `47e56` `47e6a` `47e86` |
| `10d68e` | B | R | `47dec` |
| `107def`(절대) | B | W `ff` / `00` | `9056` / `9060` |
| `62(A6)`=`100b92` | B | W(SCC) / R | `47e0a` / `47e22` |
| `7c(A6)`=`100bac` | B | R / RMW +1 | `47e12` `47e40` / `47e9a` |
| `76(child)` 또는 `100f0e` | W | W | `47e18` / `47e48` |
| `10dd44` | B | R | `47e70` |
| `10d680` / `10d681` | B | W `7c(A6)` / CLR | `47e9e` / `47ea4` |

- callee가 쓰는 RAM은 기존 실행부의 계약을 따른다.
  - `28ae`: pool head `104c9c`, 개수 `104ca0`, 새 node, 부모 `8(A6)`.
  - `3af8`: ring `104d82..`, 그리고 `100012` `10fd82` `10fe80` `10fd8d` `104d7e` `10f001` 읽기.
  - `8c16`: `107dc2..107dd4`.
  - `299c`/`2782`.
  - `480bc` helper 전체.
- **ROM 자료 window**: [F] F1b block은 ROM 자료를 읽지 않는다. `480bc` frame은 F1a·U7과 같은 physical `program_rom_000000.ms5d` window와 bank 자원을 쓴다. 새 window는 필요 없다.
- **MMIO**: F1b block에는 없다. [F] callee 쪽 접근:
  - `299c`: BYTE `300001`←D0.B. D0은 `47da4` 진입 D0이 그대로 남은 값이다(`4b6e4`/`4b6ec`는 D0을 바꾸지 않는다).
  - `3af8`의 `3b54`: TST.B `d00046`(external read). BYTE `100012`=1, `10fd82`≠0, `10fe80`=0일 때만 일어난다.
  - PVC 쓰기: 없음.

## 자연 시작 상태(읽기 전용 재생)

[F] 기록된 산출물에는 F1b block을 실행한 사례가 없다.
- `artifacts/` 전체 JSON에서 F1b PC(10진)를 찾았다. 나온 것은 범위 끝값과 정적 목록뿐이다. buffer_cue `existing_ranges`, 각 `source.json` `ranges`, `stage_activation_remaining_static.json`, `animation_word_callbacks`가 해당한다.
- `*.bin` 전체(약 28 GB)에서 callback LONG `00047de4`/`00047e22`/`00047e62`/`00047e70`/`00047e92`를 찾았다. ROM 사본(`physical_program_execution/bus_all_bytes.bin`)과 무관한 `gfx.bin` 외에는 0건이다. 즉 F1b 대기 중인 controller node를 담은 RAM 덤프는 없다.

**1. transition 관측의 `47da4` 경계(SHA256 `edf1f5e7248601d2a708cbc7ebfb8a89c62bfdb5dcef018cb94a2c5fa26aaba4`)**
- [F] case 77 `negative-gate1-bit1`이다. 진입 `47d60`, stop `47da4`, A6=`102000`, A7=`1feffc`(복귀 `ff000`), A5=`108000`이다.
- [F] host write: `10d681`=`80`, `10d68e`=1, `10d683`=1 등. 결과 phase는 RAM 변화 없이 `47da4`에서 멈춘다.
- 합성 fixture이며 F1b 본문을 실행하지 않는다. 연결 검사(stop `47de4` 부분 실행)용이다.

**2. stage_entry_body begin 출력 RAM에 `47da4` 직접 진입(scratch `f1b/replay_b.py`)**
- [F] 조건:
  - 입력은 `artifacts/stage_entry_body/observation.json`(SHA256 `1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207`)의 final PC `ff000` phase 142개다. begin 137개와 `wholebody-sound-wait` release 5개이며, F1a 관례대로 앞의 137개를 주 seed로 권고한다.
  - 레지스터는 결과 그대로이고 A6=`100b30`, A5=`108000`, SR=`2000`이다. A7은 `10eff4`, LONG=`2ac2`이다.
  - frame 1부터는 `2abe`에서 A6=`100b30`, A7=`10eff8`로 시작한다(dispatcher `JSR (A0)`가 같은 `10eff4`에 `2ac2`를 넣는다).
  - stop은 `2ac2`/`477ee`이고, BIOS·TRAP·`3aea` 반복을 감시했다. bank 쓰기 hook은 F1a 재생과 같다.
- [F] 입력 RAM 상태(142 모두): `10d681`=`00`, `10d68e`=`00`, `10dd44`=`00`, `(100bf4)`=`e9150`과 type WORD 0, player node 둘 다 `270e`, `7c(A6)`=0, `104ca0`=`50`/`4f`/`4a`. `10d683`=`2a`(137) / `00`(5).
- [F] 결과: 142 모두 동일한 F1b block 경로로 237 frame 뒤 `477ee`에 도달했다.
  - 경로: `1c5bc`/`1c5d8`는 C=0 → `1c5c0`/`1c5dc` 미실행, `47dec`는 0 → `47e30`, `28ae(d72fe)` 성공.
  - 선언 host write는 frame 188 뒤 `10dd44`=`ff` 1건뿐이다.
  - 예외·BIOS·TRAP·Waiting은 0건이다.
  - 끝 상태(137): `10d680`=1, `10d681`=0, `7c(A6)`=1, `10d683`=`08`(`2a`의 bit5·bit1 해제, bit3 유지), `10db85`/`10db87`=0(U7이 소비), `10d734`/`10d738`=`1bec0`, `100967`=`ff`, `(A6)`=`47e92`.
- [F] 미실행 F1b block: `1c5c0` `1c5dc` `47df4` `9056` `47dfa` `47e0a` `47e12` `47e1c` `47e22` `47e2a`.

**3. typed 변형(같은 seed, 선언 host write; scratch `f1b/replay_v.py`, 각 3 seed)**
- `alive`: frame 28 뒤 `10d68e`=1. frame 29에 `47dec`→`47df4`→`9056`→`28ae(e4234)` 성공→`47e0a`(`62`=`00`)→`47e12`→`47e1c`→`47e22` 대기. frame 29 뒤 `62(A6)`=1. frame 30에 `47e22`→`47e2a`(`9060`)→`47e30`… 238 frame이며 `477ee`에 도달한다.
- `fail`: `104ca0`=0. 두 `28ae` 모두 실패한다. `62`=`ff`라서 frame 29 안에 `47e22`→`9060`→`47e30`까지 가고, `100f0e`=`0001`이 쓰인다. 237 frame이다.
- `half`: `104ca0`=`14`. 첫 `28ae` 성공(개수 `13`), 둘째(D0=`14`≥`13`) 실패로 `100f0e`=`0001`이 쓰인다. 238 frame이다.
- [I] `alive`의 `10d68e` 직접 쓰기는 frame 29의 `480bc`(`47642`)가 다시 0으로 계산한다. 이후 frame 동작에는 영향이 없다(F1b는 `47dec`에서 한 번만 읽는다).

## 검증 조건(최소)

**자연 RAM 직접 진입**
- stage_entry_body begin 137 seed를 `47da4`부터 frame 단위로 실행한다(결정 2·5). frame 0..235는 stop `2ac2`, frame 236은 stop `477ee`이고, frame 188 뒤 선언 `10dd44`=`ff`를 쓴다. 매 frame Unicorn 재생과 64 KiB RAM·16R/PC/A7·carry 분류·PVC·bank·ordered ports·external reads·status를 비교한다(새 관측 산출물 필요).
- [I] 이는 U1~U7 전체 `480bc` frame을 F1b 상태(`10db85`/`10db87`=`ff`, slot `1bec0`)로 236번 연속 실행하는 통합 검증이다.
- split/continuous: frame 0을 중간 stop(`47dc6`, `47dd8`, `47de4`)으로 나눈 실행과 한 번 실행이 같아야 한다.

**host-write·typed 직접 진입**
- 생존 분기:
  - `alive`(위 3): `47e22` 대기 frame에서 host write 없이 재진입하면 같은 대기를 반복해야 한다(`480bc`만 진행). `62(A6)`=1 뒤 통과한다.
  - `fail`/`half`: `62`=`ff`, `100f0e` 쓰기를 확인한다. 성공 시 `76(child)`=WORD `7c`이다.
- `1c5b0` player node:
  - 하나 또는 둘 다 LONG≠`270e`일 때 `1c5c0`/`1c5dc` BSET을 확인한다. stop `47dc0`의 부분 실행을 권고한다. 생존 node는 이후 `480bc`에서 U6 slot `1bec0`을 부르므로 전체 frame은 별도 fixture가 필요하다.
  - `61` bit6 기존 값 1(멱등)도 확인한다.
- callback 재진입: 다섯 callback 각각에서 `7a`=1(통과)/2(대기)/0(`ffff`로 wrap 후 대기), `62`=0/≠0, `10dd44`=0/≠0을 확인한다.
- `7c(A6)`=`ff`: `10d680`=`00`, `76(child d72fe)`=WORD `0100`, `76(e4234)`=WORD `00ff`이다.
- `8c16`: `107dc2..107dc6`이 목표와 같은 경우(`8ca0` 즉시 RTS)와 다른 경우(DIVS 경로)를 확인한다.
- `3af8` `19db`: ring 가득으로 `3aea` Waiting 후 재개한다. `100012`=1·`10fd82`≠0·`10fe80`=0 경로의 `d00046` external read도 확인한다.
- A6=`102000` 문맥(transition 관측과 같은 node) 1건.

**경계·오류**
- stop≠`477ee`로 `47ea8`에 도달하면 `unsupported animation machine PC`와 전체 rollback이다.
- frame stop을 `2ac2`로 두지 않으면 자식 callback 진입에서 rollback이다(`28ae` 성공 상태).
- `100c04`≠0이면 `2a48` checked 오류와 전체 rollback이다(F1b 쪽 쓰기 `10db85`/`10db87` 포함).
- Unknown carry로 `1c5bc`/`1c5d8`/`47e0a`에 진입하면 오류다. Known Clear/Set으로 진입하면 양쪽 경로가 나와야 한다.
- 묶인 분기 6개, `47e0e`를 포함한 내부 PC 149개를 거부한다.
- 홀수 A6(`7a`/`(A6)` 접근), 홀수 child A0(`76`)은 오류다.
- 각 block 시작의 zero-step(stop=진입 PC)은 상태 불변이다.
- 위 회귀 탐침을 갱신한다. transition의 stop `47da4` 회귀는 그대로 통과해야 한다.

**비교 항목**
- 기존과 같다: 64 KiB RAM 전체, 16R/PC/A7, carry 분류, PVC 장치와 bank, 순서 있는 port, external reads, status, 입력·산출물 SHA, ROM stat 불변.
- stack은 F1a 검증과 같은 RAM mirror 규약(`10effc`)을 따른다.

## F1a 계약 "F1b 개요"와의 차이

- [F] 맞는 내용: 범위 목록, block 시작 39, 기존 실행부 호출 목록, carry 소비 `1c5bc`/`1c5d8`/`47e0a`, `47e3a` 미검사와 fallback `100e98`(정확히는 WORD `100f0e`), 30/160/48 frame, `10dd44` poll, `7c`+1→`10d680`, CLR `10d681`, `477ee`, transition 관측 SHA와 `47da4` stop 1 phase.
- 부정확하거나 빠진 내용:
  1. "자식 `e4234`, 그 완료 대기(`62(A6)`), `9060`": 완료 대기는 `28ae` 성공 때만 생긴다. 실패하면 `SCC`가 `62`=`ff`로 두므로 같은 frame에 `9060`으로 간다.
  2. frame 수는 timer를 설정한 frame을 포함한다. 30번째 호출에 `47dec`, 그로부터 160번째 호출에 `47e70` 첫 검사가 일어난다. 48도 같다. `10dd44`가 이미 ≠0이면 대기 frame이 없다.
  3. 범위 끝이 열려 있었다(`1bee4..`). 정확히는 `1bee4..1bef8`(2 block, 뒤는 자료), `4b6e4..4b6f4`(두 루틴), `ca48..ca50`, `9056..9060`이다.
  4. "자연 seed는 없다"는 맞다. 다만 stage_entry_body begin 출력 RAM에 `47da4` 직접 진입하면 137 seed 모두 원본 재생이 끝까지 간다. F1a의 activation 직접 진입과 같은 등급의 시작 상태를 쓸 수 있다.
  5. F1b 고유의 MMIO·ROM 읽기·TRAP은 없다. 위험은 carry 소비 3곳과 frame 재진입 규약이다. "`28ae` 실패 무시"는 원본 동작이며 위험이 아니라 구현 대상이다.

## 미확인·범위 밖

1. 자연 reach: `10d681` bit7(F1c `479b0`이 `ff`), `10d68e`≠0, `10d683` bit0(`4833e`, 객체 코드에서 호출)을 동시에 만드는 실제 플레이 관측이 없다. 재생 seed는 `10d681`=0인 47a94 출력이다.
2. 의미 [I]/[U]:
   - `10db85`/`10db87`(U7 buffer 요청), `100967`(`ca48`/`ca50`/`ca56` 플래그), `107def`(`9160 TST.B -211(A5)` 읽기, 게이트로 추정).
   - `10dd44`(객체 코드의 `ST.B 5d44`, area 끝 객체로 추정). `10dd44`가 `47e70`에서 이미 ≠0일 가능성도 있다(`50c22`가 `4833e` 호출보다 먼저 쓴다).
   - player node `61` bit6·`a8` bit0의 의미.
3. 자식 `e4234`(`8c16`·sound·`e3aec`·추가 자식 `e4412`, 끝에 부모 `62`=1)와 `d72fe`(`76`−1이 0..4일 때 `d72b6` 12바이트 record, 아니면 즉시 `2a00`)는 범위 밖이다. 같은 dispatcher pass에서 부모 뒤에 실행되는 점은 F2(scheduler) 범위다.
4. `4830a..48336`은 F1b 준비부(`4b6e4` `4b6ec` `2a48` `1c5b0` `1bee4`)와 거의 같은 별도 루틴이다(`482fa` 진입, 객체 코드 `50c26` 등에서 호출). F1b 범위 밖이다.
5. frame 사이의 IRQ 효과(frame counter, watchdog, palette)는 모델링하지 않는다(F1a 결정 2와 같다).
6. 재생에서 Waiting(`3aea`, `cda4`)이 없었다. 해당 재개 경로는 typed fixture로만 검증된다.
7. 산출물 크기·frame 수(결정 5)와 `2abe` 재진입 변형의 채택 여부.

작업자 scratch: 세션 scratchpad `f1b/`(`leadb.py`, `leadb.json`, `table_b.py`, `replay_b.py`, `replay_v.py`, `agg_b.py`, `*.pkl`; 저장소 밖). F1a 규칙 재사용을 위해 `f1/lead.py`·`f1/dis2.py`를 import했다.
