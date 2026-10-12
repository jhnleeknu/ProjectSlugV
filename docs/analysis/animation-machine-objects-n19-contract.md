# 객체 callback F4 N19: N18이 넘긴 설치 callback `86742`, `b16ea` 계열 객체(stage event callback `b16ea`, 설치 `b16fc`, `28ae` 자식 `b175a` `b1842` `b1b24`와 그 설치 callback, helper `b15e0` `b160a` `b17f4` `b182e` `b1b62` `b1b76` `b1b8c` `b1bc2` `b1bf6` `b1c0e` `b1c4a` `b1cf8` `b1d1e` `b1d40` `b1dae` `b1dfa` `b1fd6`), stage event callback `dbf5e` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N19 행(122 block, `86742..86814` `b15e0..b19f2` `b1b24..b1e2a` `b1fd6..b2004` `dbf5e..dbf6e`(+`8625a..86372` 공유), callback `86742` `b16ea` `b16fc` `b1842` `b188e` `b1b24` `b1b42` `dbf5e`, 경계 `44602` `b160a` `b1dae` `b43de` `b441e` `cc778`, 표 `862a0`:27(공유), bank 1, 미실행 설치 8(+40), 새 seed 12 13, 옛 R11 105·U27 30)과 메인 결정 1·2(이름 `objects-nNN`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계), N18 계약(SHA256 `c6ca8211c8b8f2e3ea1d343418d2d45bfd3fe91bf584a4a0e458ddc3fb3789eb`) 결정 1(설치 callback `86742`의 본문 `86742..86814` 28 block을 N19로 넘김)이다. 단위 형식과 규약은 N18 계약을 따른다. 메인 작업 지시:
- flag 재계산은 선행이 유일할 때만(아니면 각 선행에 접어 넣음).
- 범위 안 미참조 코드는 routing하지 않고, 참조된 범위 안 진입은 넣는다.
- RTS 앞 known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로만 확인한다(Unicorn SR 불가).
- 다른 단위 실행부(`animation_machine_interpreter.cpp` 포함)는 고치지 않는다. 기존 실행부의 두 번째 진입 누락은 scratch 패치와 결정으로 보고한다. DIV 0 제수는 단위 checked 오류(N19에는 DIV가 없다).
- 약 220 block을 넘으면 나누고 목표 seed(12 13)가 쓰는 부분을 먼저 구현한다. N20(`49580..495e2` `735b0..739c0` `b9832..b9d0a`)이 동시에 진행한다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback과 `MOVEA.L #imm,A0`+`JSR 28ae` 자식 callback)로 정한다. fall-through로 이어지는 설치 대상도 시작으로 센다. 묶인 연속 Bcc는 없다. Unicorn TB 분할은 시작이 아니다. TRAP 자리는 경계다(N06 결정 6).
- 결정 5(관례): 단위는 함수 본문 전체다(이번에는 아래 결정 1의 분할이 예외). 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N18 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`ADDQ`/`SUBQ`/`ANDI`/`ADD`/`SUB`/`NEG` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block, callee C를 소비하는 Bcc block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N19 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. N19는 banked window를 읽지 않는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n19`(HEAD `b212aea` = N18까지 통합, `engine/src/animation_machine.cpp` SHA256 `56927533037123cf742cff1227738a6f701b0374ac5be01a1560a583ac7a156c`, routing 규칙 75개, `engine/src/animation_machine_interpreter.cpp` SHA256 `bd2bffb36ccf99cc18fe141949335e6ef1e07f7255cb1f137e387d0451ebac05`)을 참조했다. N19 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. `86742..86814`는 N18 `..86742`와 `86814..` 사이다(다시 routing하지 않는다). 동시에 진행하는 N20과 범위·경계가 겹치지 않는다(N19는 N20 PC를 부르지 않는다). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n19/n19.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **재범위 N19 행 5 범위(hull)의 정적 도달 전체는 241 block**(행 callback 8개에서 210, 범위 밖에서 참조되는 범위 안 진입 `b1656` `b16d6` `b1d8c`와 그 범위 안 도달 31)이다. 220을 넘으므로 메인 지시대로 나눈다(결정 1).
  - **N19(이 계약) = 210 block**: 행 callback `86742` `b16ea` `b16fc` `b1842` `b188e` `b1b24` `b1b42` `dbf5e`에서 범위 안 설치·자식·`JSR (PC)` callee를 따라간 정적 도달 전체다. 코드 8 범위 1,788바이트, 403명령이다. routing 짝수 PC 894개 중 내부 PC 684개다. N18이 넘긴 `86742..86814` 28 block을 포함한다.
  - **N19b로 넘기는 31 block**: stage event 표 LONG(`e8ec8` = `b1656`, `e8ed0` = `b16d6`)과 범위 밖 미연결 `b1f4e JSR b1d8c(PC)`만 참조하는 진입과 그 도달(`b1656..b16ea` `b1c82..b1cf8`(TRAP `b1c90` 제외) `b1d8c..b1dae`). 목록은 "N19b로 넘기는 block" 절.
- [F] 재범위 행의 "경계 callee" `b160a` `b1dae`는 행 hull 안에 있고 N19 본문(`b1918` `b1682` / `b191c`)에서 `JSR (PC)`로 정적 도달하므로 이 계약의 시작이다(재범위는 400 frame 안 실행 여부로 함수를 나눠 경계로 적었다). 재범위의 경계 `cc778`은 N18 `8625a` 꼬리의 경계이고 N19는 직접 부르지 않는다.
- [F] 미해독·레지스터 간접 점프·PC 상대 표·묶인 Bcc·SUBX/ADDX/MULx/DIVx·I/O port 쓰기·bank 변경·bank 읽기는 없다. 스택 직접 조작은 `MOVE.W Dn,-(A7)`/`MOVE.W (A7)+,Dn`/`MOVE.L An,-(A7)`/`MOVEA.L (A7)+,An`/`MOVEM.W`(결정 6)다.
- [F] 진입:
  - stage event callback(고정 ROM LONG 표): `b16ea`(`e8ecc`), `dbf5e`(`dbf7a`).
  - 설치 callback: `86742`(N18 `86734` fall-through 설치), 범위 안 `b16fc`(`b16f6`, fall-through), `b17dc`(`b17d6`, fall-through), `b188e`(`b1888`, fall-through), `b192c`(`b1924`, 설치 후 RTS), `b1986`(`b1978`, 설치 후 RTS), `b1b42`(`b1b2e`, fall-through).
  - `28ae` 자식 callback: `b175a`(`b172e`), `b1842`(`b1d50`), `b1b24`(`b1852`).
  - 범위 안 `JSR (PC)` helper: `b15e0` `b160a` `b17f4` `b182e` `b1b62` `b1b76` `b1b8c` `b1bc2` `b1bf6` `b1c0e` `b1c4a` `b1cf8` `b1d1e` `b1d40` `b1dae` `b1dfa` `b1fd6`.
  - 범위 밖 참조가 있는 시작(scratch `n19xref.py`): `b15e0`(N19b `b16be`), `b160a`(N19b `b1682`), `b186a`(N19b `b16e6 BRA.W`), `b19b2`(N19b `b16c2 BCS.W`), `b1b76`(N19b `b16cc`, 범위 밖 미연결 `b1a02` `b1a5c` `b1b1e`), `b1c0e`(N19b `b166c` `b16e2`), `b1cf8`(N19b `b1cc6`), `b1dfa`(N19b `b16d0`), `b1fe0`(범위 밖 미연결 `b1e40 JSR (PC)`; `b1fdc BCS`의 fall-through 시작과 같다).
- [F] **경계(실행부 없음, 모두 미연결)**: `44602`(`b1ff6 JSR`), `b43de`(`b1e06`), `b441e`(`b1e16`), `b1e2a`(`b1936 JSR (PC)`), `b1f1a`(`b193a`), `b1ee6`(`b1948`), `b1e74`(`b1950`), `b1ecc`(`b1dd4`). 모두 `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **범위 밖 설치 값(노드 LONG에 저장만)**: `86e76` `86fca` `8698c` `86d0c` `871ee`(`86742` 계열; N18 범위 밖 고아 설치와 같다), `86f1c`(N18 시작), `b19f2`(`b19ea`). 범위 밖 자료 주소: `56(A6)` = `b150a`(`b1b2e`), `b14b0`/`b14ce`(`b1bf6`), 사각형 `b14a0`(`1ab02`), `b14a8`(`b43de`), `b15bc`(`b441e`), `c8e5e`(`490ba`), animation 기록 `b2040` `b2022` `b2004` `b23f0` `b2206` `b225c` `b22e0` `b213a` `b205a`(`49f8c` A1).
- [F] **carry**(아래 "carry" 절):
  - 소비 block **14개**(BCC/BCS): `b15e6` `b1b4e`(`4b54e`), `b1702`(`287e`), `b173e`(`28ae`), `b1760`(`497a6`), `b17e8`(`49fc6`), `b1804`(N19 `b1fd6`), `b1898`(N19 `b1dfa`), `b18f2` `b1966` `b19a0`(N19 `b15e0`), `b194c`(경계 `b1ee6`), `b1b80`(`1ab02`), `b1fdc`(`4945e`).
  - known 생산 block **4개**: Set `b15fe`(`ORI.B #1,CCR; RTS`), Clear `b1604`(`ANDI.B #fe,CCR; RTS`), Set `b174c`(`ORI.B #1,CCR`, 소비자 없음, 결정 5), Clear `b1ffc`(`MOVEA.L (A7)+,A0; ANDI.B #fe,CCR` → `b2002 RTS`).
  - FLOW_ONLY 98개(소비 14 포함), Unknown 108개. 98 + 4 + 108 = 210.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n19seen.py`): RNG 400 frame 기록에서 seed 12 13만 N19 범위 PC를 실행한다(seed마다 TB 시작 86개). callback 실행 수(seed마다): `86742` 74, `b16ea` 6, `b16fc` 510, `b1842` 6, `b188e` 510, `b1b24` 6, `b1b42` 510, `dbf5e` 1. base 120 frame 기록에서는 seed 12 13이 `dbf5e` `b16ea`를 1회씩 실행한다. 자연 TB 시작 86개는 모두 이 계약의 시작이다. N19b 범위와 경계 PC는 자연 실행되지 않는다.
- [F] **새 완주 seed 12 13(RNG, 재범위 행과 같음)**. 기준 `b212aea`에서 seed 12 13은 frame 0 `dbf5e`에서 멈춘다(RNG 기록 `checked-current-first-unrouted-PC`). base 120 기록에서 seed 12 13은 native 자신이 frame 0 `49a80`(난수 포인터 미초기화, 쓰기 보호 주소 `30`)에서 멈추는 기록이라 N19 뒤에도 완주 수는 그대로이고 C++는 같은 지점에서 guard 오류 `stage area RNG pointer outside work RAM`(상태 보존)를 낸다(아래 검증 기록).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **분할: N19 = 210 block, 31 block은 N19b로.** [F] 재범위 N19 행 hull의 정적 도달 전체(범위 안 설치·자식, 범위 밖에서 참조되는 범위 안 진입 포함)는 241 block이다. 메인 지시(약 220 초과 시 분할, 목표 seed 우선)에 따라 행 callback 8개의 정적 도달 210을 N19로 두고, 행 callback에서 도달하지 않는 진입 3개(`b1656` stage event `e8ec8`, `b16d6` stage event `e8ed0`, `b1d8c` 범위 밖 미연결 `b1f4e`의 `JSR (PC)` 대상)와 그 범위 안 도달(`b1c82` TRAP 함수, `28ae` 자식 `b1660`, 설치 `b16b0`)을 N19b로 넘긴다. seed 12 13의 자연 경로는 N19b PC를 쓰지 않는다. N19 block은 N19b 쪽에서 다시 나눌 필요가 없다(N19b가 부르는 N19 PC `b15e0` `b160a` `b186a` `b19b2` `b1b76` `b1c0e` `b1cf8` `b1dfa`와 `b16e6 BRA.W b186a`, `b16c2 BCS.W b19b2`의 대상은 모두 N19 시작이다). [I] 대안: 241 block 전부를 N19에 넣는다(220 초과 21).
2. **범위 안 함수 `b160a` `b1dae` 포함.** [F] 재범위 행은 둘을 "경계 callee"로 적었지만 hull 안에 있고 N19 본문에서 `JSR (PC)`로 정적 도달한다(`b1918 JSR b160a`, `b191c JSR b1dae`). 결정 2(범위 안 참조 진입 포함)대로 시작으로 넣는다. 빼면 196 block이고 두 함수는 routing 구멍이다.
3. **RTS 앞 known C: `b15fe`(Set)·`b1604`(Clear)·`b1ffc`(Clear, `b2002 RTS` 앞).** [F] `b15e0`은 `61` bit 7을 C로 돌려준다. 소비자는 N19 `b18f2` `b1966` `b19a0`(그리고 N19b `b16c2`), `b1fd6`의 C는 `b1804`가 쓴다(`b1fdc`에서 `4945e` Set이면 그대로, 아니면 `b1ffc` ANDI Clear). typed fixture는 실제 소비자(`b18f2` `b1966` `b19a0` / `b1804`)를 복귀 LONG으로 둔 `b15f4`/`b1ffc` 진입과 `b18ee` `b1962` `b199c` 진입(실제 `4b54e` 추종)으로 native 분기를 확인했다(Unicorn SR은 쓰지 않음).
4. **`b194c`는 경계 `b1ee6`의 C를 소비.** [F] `b1948 JSR b1ee6(PC)`의 `b1ee6`(`b1ecc` 좌표와의 거리 3 이내면 `ORI` Set, 아니면 `ANDI` Clear; 범위 밖 미연결)은 이 단위의 경계다. `b194c`는 typed C(실제 ROM 차분 포함)로만 검사한다. `b1ee6`이 routing되면 실제 생산자 추종 확인을 그 단위에서 한다.
5. **`b174c ORI.B #1,CCR`은 Set 생산(소비자 없음).** [F] `28ae` 성공(Set) 뒤 `b1742 CLR.W D0; CLR.W D1; JSR 4970a` 다음 `b174c`가 C = 1을 만들고 `b1750 JSR b182e(PC)`(FLOW)로 이어진다. `b182e`의 `MOVE.W`가 C를 덮어 소비자가 없다. N18 결정 5(`b6544`) 선례대로 Set으로 둔다. [I] 대안: Unknown(관찰 차이는 한 block 단위 test의 C뿐).
6. **스택 WORD·`MOVEM.W`.** [F] `b1d28 MOVE.W D0,-(A7)`/`b1d34 MOVE.W (A7)+,D1`, `b1d46 MOVE.W D0,-(A7)`/`b1d7a MOVE.W (A7)+,D0`은 A7 ±2(WORD)다. `b1d4c MOVEM.W D0-D1,-(A7)`은 D1.W를 먼저(높은 주소), D0.W를 다음(낮은 주소)에 쓴다. `b1d60 MOVEM.W (A7)+,D0-D1`은 낮은 주소 WORD를 D0, 다음을 D1에 **부호확장 LONG**으로 넣는다(68000 MOVEM.W 메모리→레지스터). `b1d6e MOVE.L A0,-(A7)`/`b1d7a MOVEA.L (A7)+,A0`, `b1fe0 MOVE.L A0,-(A7)`/`b1ffc MOVEA.L (A7)+,A0`은 LONG이다. 모두 기존 `am_push`/`am_pop`(work RAM 밖은 기존 checked 오류)이다. [U] 68000 `MOVEM (An)+`의 끝 추가 읽기 bus cycle은 모델링하지 않는다(상태에 영향 없음).
7. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n19.cpp`의 `animation_objects_n19_block`. 오류는 `unsupported animation objects n19 PC`(내부 PC), `objects n19 caller requires known carry`(소비 14 block). 메인 지시와 같다.
8. **무효화 탐침 없음.** [F] `engine/tests`·`tools/*.py`·`engine/src`에서 N19 routing 범위의 PC를 경계·rollback 탐침으로 쓰는 곳은 없다. N18 test는 `86742`에서 stop만 확인한다(stop은 실행 전에 판정하므로 routing 뒤에도 성립; `make test` 통과).
9. **interpreter·다른 실행부의 두 번째 진입 누락 없음.** [F] N19가 부르는 다른 단위 진입(`864b6` `8625a`(N18), `4be06`(U11), `49fc6` `49f8c`(interpreter), `4c1de`(U15), `4b54e`(U01), `49a58`(stage_area), `49a84`(stage_event_ops), `287e` `2a24` `43e34`(cleanup), `28ae` `2a00`(fade_card), `4970a`(N14), `497a6`(U20), `8ebe` `443d2`(U02), `43ea4`(U04), `1ab02`(U05), `490ba`(U12), `49290`(U08), `3af8`(sound), `4945e`(N08))는 모두 기존 실행부의 `case`로 시작한다(scratch routing 검사). 패치 파일은 없다.

## 원본 바이트 근거

[F] 코드 8 범위 합계 1,788바이트. 범위 순서로 이어 붙인 SHA256 `50594fda2ef80bd66385267e28ab5ca279c8ebe9ac38c0257b82f00fd0c890ae`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `86742..86814` | 210 | `ac17c5430910ae77ea4e5bdd73a7c168ea90e846bc8372d4679abfa5c9973d94` | 28 |
| `b15e0..b1656` | 118 | `aa5a823940d471dc0f7c03eadeff1b7e706fdca5a4bdfbb6b2c3234ce5219803` | 15 |
| `b16ea..b19f2` | 776 | `03a47cce18476fa4b009c99dfe754ff40587022b3dbd30fbf7f0ec6cfdbf4cc7` | 96 |
| `b1b24..b1c82` | 350 | `f54dc063d9087a8e181e23bf62515949e94e9c36cd5f42934dab029930b5ba28` | 36 |
| `b1cf8..b1d8c` | 148 | `3aeacac5f7f2bab5539afb65b0eb78c5f98d0ea956d55f13e33598cb6a34cfad` | 12 |
| `b1dae..b1e2a` | 124 | `2a7993b01569b8d69bf22e3b8b446622711c19618ad7d7fe00346cf49af11dbb` | 16 |
| `b1fd6..b2004` | 46 | `0eb68867641a4b9afd9a56b841f02c058e23ec349e21d563962a73f4e1d7827a` | 5 |
| `dbf5e..dbf6e` | 16 | `8ac8b3951f13aa5467a9942052e38ac9cd8d6628675b2ec92814e9c011080f8a` | 2 |

- [F] 범위 밖 이웃(모두 `unsupported animation machine PC`): `86740`/`86814`(N18), `b14a0..b15e0`(자료: 사각형 `b14a0` `b14a8` `b14b0` `b14ce`, LONG 표 `b15c0`, `b150a`, `b15bc`), `b1656..b16ea`(N19b), `b19f2..b1b24`(범위 밖 고아 설치 `b19f2` `b1a46` `b1ac2` 본문, 미연결), `b1c82..b1cf8`(N19b; TRAP `b1c90` `4e4f`+문자열 `TK205A ERR\0\0` `b1c92..b1c9e`), `b1d8c..b1dae`(N19b), `b1e2a..b1fd6`(경계 `b1e2a` `b1e74` `b1eb6` `b1ecc` `b1ee6` `b1f1a` `b1f68`, 미연결), `b2004..`(animation 기록 자료), `dbf5c`/`dbf6e..`(자료; stage event 표 LONG `dbf7a` = `dbf5e`).
- [F] 범위 밖 → N19 참조(scratch `n19xref.py`, 고정 ROM 전수: LONG 값, Bcc/BRA/BSR 변위, `JSR`/`JMP`/`LEA (PC)`): 요약의 "범위 밖 참조가 있는 시작"과 `86742`(N18 `8673e` LONG = `MOVE.L #imm,(A6)` 즉치), `b16ea`(`e8ecc`), `dbf5e`(`dbf7a`)다. 모두 block 시작으로 간다. 내부 PC와 같은 값(`86772` `86784` `867a8` `867e0` `867f4` `b1800` `b2000` 등)은 다른 명령의 즉치 바이트나 자료(고정소수 LONG `000b1800` 등)의 우연 일치다. `86800`(시작)의 LONG 일치(`3604c` 등)도 자료 값이다.

## block 목록과 실행 의미

[F] 210 block. 각 줄은 block 안 명령 전체다(capstone 표기, 즉치·주소 16진). "(→x)"는 fall-through다. 태그: "C 소비"(Unknown이면 checked 오류), "Set/Clear 생산", "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호확장한다(`-7348(A5)` = A5 − `7348` = `100cb8`, `-7258(A5)` = `100da8`). `.B`/`.W` 연산은 나머지 bit를 보존한다(`MOVE.W #x,Dn`·`CLR.W Dn`·`NEG.W`·`ADDI.W`·`SUBI.W`·`SUB.W`·`ANDI.W`·`SUBQ.W`는 하위 WORD만, `MOVE.B`·`ANDI.B`는 하위 BYTE만). `MOVE.L #x,Dn`은 LONG 전체다. 메모리 WORD `2e(A6)`/`32(A6)`은 LONG `2e`/`32`의 **상위** WORD다(`b17a2`의 `ADD.W D1,2e(A6)`·`ADDI.W #10,32(A6)`). 비교 분기: `BCS`(`CMP.W 98(A6),D0`: 무부호 `D0.W < 98.W`), `BLE`(`CMP.W 8c(A6),D0`: signed `D0.W ≤ 8c.W`), `BGE`(`CMPI.W #30,D0`: signed `D0.W ≥ 30`), `BPL`/`BMI`(결과 최상위 bit; `SUB.W; BPL`은 차의 bit 15, `SUBQ.W #1,x; BPL/BMI`는 감소 결과 bit 15, `TST.B; BPL/BMI`는 BYTE bit 7, `TST.L; BMI`는 LONG bit 31), `BEQ`/`BNE`(0 여부; `CMP.B a0(A6),D0; BEQ`는 하위 BYTE 비교, `ANDI.B #3,D0; BNE`/`ANDI.B #1,D0; BNE`는 결과 BYTE), `BTST.B #0,D6`은 `D6` bit 0이다. `BTST`/`BSET`/`BCLR`는 Z만 쓰고, `BSET`/`BCLR`는 대상 BYTE bit만 바꾼다. 읽기·쓰기는 명령 순서대로다(예: `b1c6c`는 `78`을 읽어 `98`에 쓴 뒤 `78`에 `32`를 쓴다; `b1ba4`는 `82`를 쓴 뒤 다시 읽어 부호를 본다).

**설치 callback `86742`(N18 `86734`가 설치; `864b6` `4be06` `49fc6` 뒤 대상 거리·`84` bit로 다음 callback 설치, `8625a`로 BRA) 28**
- `86742`: `JSR 864b6(pc)` — FLOW
- `86746`: `JSR 4be06.l` — FLOW
- `8674c`: `JSR 49fc6.l` — FLOW
- `86752`: `TST.B 85(a6); BMI.W 86800` (→`8675a`)
- `8675a`: `BTST.B #0, 84(a6); BNE.W 8676e` (→`86764`) — FLOW
- `86764`: `MOVE.L #86e76, (a6); BRA.W 86800`
- `8676e`: `TST.B 85(a6); BNE.W 8677e` (→`86776`)
- `86776`: `LEA.L -7348(a5), a0; BRA.W 86782` — FLOW
- `8677e`: `LEA.L -7258(a5), a0` (→`86782`) — FLOW
- `86782`: `MOVE.W 42(a0), d0; SUB.W 42(a6), d0; BPL.W 86790` (→`8678e`)
- `8678e`: `NEG.W d0` (→`86790`)
- `86790`: `CMP.W 8c(a6), d0; BLE.W 867b2` (→`86798`)
- `86798`: `BTST.B #7, 84(a6); BEQ.W 867ac` (→`867a2`) — FLOW
- `867a2`: `MOVE.L #86fca, (a6); BRA.W 867b2`
- `867ac`: `MOVE.L #8698c, (a6)` (→`867b2`)
- `867b2`: `CMPI.W #30, d0; BGE.W 867e8` (→`867ba`)
- `867ba`: `MOVE.W #fff8, d0; BTST.B #0, 15(a6); BNE.W 867ca` (→`867c8`)
- `867c8`: `NEG.W d0` (→`867ca`)
- `867ca`: `JSR 4c1de.l` — FLOW
- `867d0`: `BTST.B #0, d6; BNE.W 867e2` (→`867d8`) — FLOW
- `867d8`: `MOVE.L #86fca, (a6); BRA.W 867e8`
- `867e2`: `MOVE.L #86d0c, (a6)` (→`867e8`)
- `867e8`: `TST.W 8e(a6); BNE.W 86800` (→`867f0`)
- `867f0`: `BTST.B #3, 84(a6); BEQ.W 86800` (→`867fa`) — FLOW
- `867fa`: `MOVE.L #871ee, (a6)` (→`86800`)
- `86800`: `BTST.B #7, 15(a6); BNE.W 86810` (→`8680a`) — FLOW
- `8680a`: `MOVE.L #86f1c, (a6)` (→`86810`)
- `86810`: `BRA.W 8625a` — FLOW

**helper `b15e0`(`4b54e` 정지 판정, `5e`→`a7`, `61` bit 7을 C로 RTS) 6**
- `b15e0`: `JSR 4b54e.l` — FLOW
- `b15e6`: `BCC.W b15f4` (→`b15ea`) — C 소비
- `b15ea`: `MOVE.B 5e(a6), a7(a6); CLR.B 5e(a6)` (→`b15f4`)
- `b15f4`: `BTST.B #7, 61(a6); BEQ.W b1604` (→`b15fe`) — FLOW
- `b15fe`: `ORI.B #1, ccr; RTS` — Set 생산
- `b1604`: `ANDI.B #fe, ccr; RTS` — Clear 생산

**helper `b160a`(`49a58` 난수 하위 2 bit로 animation 기록 `b2040`/`b2022`/`b2004`) 9**
- `b160a`: `JSR 49a58.l` — FLOW
- `b1610`: `ANDI.B #3, d0; BNE.W b162a` (→`b1618`)
- `b1618`: `MOVEA.L #b2040, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b1628`: `RTS` — FLOW
- `b162a`: `CMPI.B #1, d0; BNE.W b1644` (→`b1632`)
- `b1632`: `MOVEA.L #b2022, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b1642`: `RTS` — FLOW
- `b1644`: `MOVEA.L #b2004, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b1654`: `RTS` — FLOW

**stage event callback `b16ea`(자식 생성 `b1d40`, `b182e`, 설치 `b16fc`)와 설치 callback `b16fc`(`287e` 비교, 타이머 `9c`, `28ae` 자식 `b175a`) 17**
- `b16ea`: `JSR b1d40(pc)` — FLOW
- `b16ee`: `CLR.B a6(a6); JSR b182e(pc)`
- `b16f6`: `MOVE.L #b16fc, (a6)` (→`b16fc`)
- `b16fc`: `JSR 287e.l` — FLOW
- `b1702`: `BCS.W b170c` (→`b1706`) — C 소비
- `b1706`: `JMP 2a00.l` — FLOW
- `b170c`: `JSR b17f4(pc)` — FLOW
- `b1710`: `SUBQ.W #1, 9c(a6); BPL.W b171e` (→`b1718`)
- `b1718`: `MOVE.W #0, 9c(a6)` (→`b171e`)
- `b171e`: `TST.W 9c(a6); BNE.W b1754` (→`b1726`)
- `b1726`: `TST.B a6(a6); BEQ.W b1754` (→`b172e`)
- `b172e`: `MOVEA.L #b175a, a0; MOVE.W #14, d0; JSR 28ae.l`
- `b173e`: `BCC.W b1750` (→`b1742`) — C 소비
- `b1742`: `CLR.W d0; CLR.W d1; JSR 4970a.l`
- `b174c`: `ORI.B #1, ccr` (→`b1750`) — Set 생산
- `b1750`: `JSR b182e(pc)` — FLOW
- `b1754`: `CLR.B a6(a6); RTS`

**`28ae` 자식 callback `b175a`(`497a6`, `8ebe`, 부모 `8a` 대상 위치 복사, 설치 `b17dc`) 15**
- `b175a`: `JSR 497a6.l` — FLOW
- `b1760`: `BCS.W b1776` (→`b1764`) — C 소비
- `b1764`: `MOVE.W #37a, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `b1772`: `BRA.W b1784` — FLOW
- `b1776`: `MOVE.W #3ba, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `b1784`: `BCLR.B #0, 15(a6); JSR 49a58.l` — FLOW
- `b1790`: `MOVE.W #c, d1; TST.B d0; BPL.W b17a2` (→`b179a`)
- `b179a`: `BSET.B #0, 15(a6); NEG.W d1` (→`b17a2`)
- `b17a2`: `MOVEA.L c(a6), a0; MOVEA.L 8a(a0), a0; MOVE.L 2e(a0), 2e(a6); MOVE.L 32(a0), 32(a6); ADD.W d1, 2e(a6); ADDI.W #10, 32(a6); MOVE.W #e2, 20(a6); MOVEA.L #b23f0, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b17d6`: `MOVE.L #b17dc, (a6)` (→`b17dc`)
- `b17dc`: `JSR 43e34.l` — FLOW
- `b17e2`: `JSR 49fc6.l` — FLOW
- `b17e8`: `BCC.W b17f2` (→`b17ec`) — C 소비
- `b17ec`: `JMP 2a00.l` — FLOW
- `b17f2`: `RTS` — FLOW

**helper `b17f4`(`b1fd6` 대상 선택 → `443d2` 속도)와 `b182e`(`49a84` 타이머 `9c`) 8**
- `b17f4`: `CLR.L 36(a6); CLR.L 3a(a6); CLR.L 8a(a6); JSR b1fd6(pc)`
- `b1804`: `BCS.W b1826` (→`b1808`) — C 소비
- `b1808`: `MOVE.L a0, 8a(a6); ANDI.W #ff, d0; MOVE.W d0, d1; MOVE.L #20000, d0; JSR 443d2.l`
- `b181e`: `MOVE.L d0, 36(a6); MOVE.L d1, 3a(a6)` (→`b1826`)
- `b1826`: `JSR 43ea4.l` — FLOW
- `b182c`: `RTS` — FLOW
- `b182e`: `MOVE.W #50, d0; JSR 49a84.l`
- `b1838`: `ADDI.W #28, d0; MOVE.W d0, 9c(a6); RTS`

**`28ae` 자식 callback `b1842`(`b1d4c`가 생성; 설치 `b188e` `b192c` `b1986`, 경계 `b1e2a` `b1e74` `b1ee6` `b1f1a`) 56**
- `b1842`: `MOVE.W #1fb, 20(a6); MOVE.B #1, 9e(a6); JSR b1c0e(pc)`
- `b1852`: `MOVEA.L #b1b24, a0; MOVE.W #14, d0; JSR 28ae.l`
- `b1862`: `TST.W 90(a6); BNE.W b1918` (→`b186a`)
- `b186a`: `BCLR.B #0, 15(a6); CLR.L 64(a6); MOVEA.L #b2206, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b1884`: `JSR b1b62(pc)` — FLOW
- `b1888`: `MOVE.L #b188e, (a6)` (→`b188e`)
- `b188e`: `JSR 4be06.l` — FLOW
- `b1894`: `JSR b1dfa(pc)` — FLOW
- `b1898`: `BCC.W b18ac` (→`b189c`) — C 소비
- `b189c`: `MOVEA.L #b2206, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b18ac`: `SUBQ.W #1, 94(a6); BPL.W b18ea` (→`b18b4`)
- `b18b4`: `JSR b1b62(pc)` — FLOW
- `b18b8`: `JSR 49a58.l` — FLOW
- `b18be`: `ANDI.B #1, d0; BNE.W b18da` (→`b18c6`)
- `b18c6`: `MOVEA.L #b225c, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b18d6`: `BRA.W b18ea` — FLOW
- `b18da`: `MOVEA.L #b22e0, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b18ea`: `JSR b1b76(pc)` — FLOW
- `b18ee`: `JSR b15e0(pc)` — FLOW
- `b18f2`: `BCS.W b19b2` (→`b18f6`) — C 소비
- `b18f6`: `SUBQ.W #1, 9a(a6); BMI.W b1918` (→`b18fe`)
- `b18fe`: `MOVE.W 10d418.l, d0; CMP.W 98(a6), d0; BCS.W b1916` (→`b190c`)
- `b190c`: `MOVE.W #ffff, 98(a6); BRA.W b1918`
- `b1916`: `RTS` — FLOW
- `b1918`: `JSR b160a(pc)` — FLOW
- `b191c`: `CLR.B 62(a6); JSR b1dae(pc)`
- `b1924`: `MOVE.L #b192c, (a6); RTS`
- `b192c`: `CMPI.B #1, 9e(a6); BNE.W b193e` (→`b1936`)
- `b1936`: `JSR b1e2a(pc)` — FLOW
- `b193a`: `JSR b1f1a(pc)` — FLOW
- `b193e`: `CMPI.B #2, 9e(a6); BNE.W b1954` (→`b1948`)
- `b1948`: `JSR b1ee6(pc)` — FLOW
- `b194c`: `BCS.W b186a` (→`b1950`) — C 소비
- `b1950`: `JSR b1e74(pc)` — FLOW
- `b1954`: `JSR 43ea4.l` — FLOW
- `b195a`: `JSR b1dfa(pc)` — FLOW
- `b195e`: `JSR b1b76(pc)` — FLOW
- `b1962`: `JSR b15e0(pc)` — FLOW
- `b1966`: `BCS.W b19b2` (→`b196a`) — C 소비
- `b196a`: `TST.B 62(a6); BNE.W b1974` (→`b1972`)
- `b1972`: `RTS` — FLOW
- `b1974`: `JSR b1b8c(pc)` — FLOW
- `b1978`: `MOVE.W #7, 96(a6); MOVE.L #b1986, (a6); RTS`
- `b1986`: `MOVE.L 82(a6), 36(a6); MOVE.L 86(a6), 3a(a6); JSR 43ea4.l`
- `b1998`: `JSR b1dfa(pc)` — FLOW
- `b199c`: `JSR b15e0(pc)` — FLOW
- `b19a0`: `BCS.W b19b2` (→`b19a4`) — C 소비
- `b19a4`: `JSR b1b76(pc)` — FLOW
- `b19a8`: `SUBQ.W #1, 96(a6); BMI.W b1918` (→`b19b0`)
- `b19b0`: `RTS` — FLOW
- `b19b2`: `MOVE.W #187f, d0; JSR 3af8.l`
- `b19bc`: `CMPI.B #7, a7(a6); BNE.W b19da` (→`b19c6`)
- `b19c6`: `MOVEA.L #b213a, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b19d6`: `BRA.W b19ea` — FLOW
- `b19da`: `MOVEA.L #b205a, a1; MOVE.W #100, d0; JSR 49f8c.l`
- `b19ea`: `MOVE.L #b19f2, (a6); RTS`

**`28ae` 자식 callback `b1b24`(`b1852`가 생성; 설치 `b1b42`) 7**
- `b1b24`: `CLR.W d0; CLR.W d1; JSR 49290.l`
- `b1b2e`: `MOVE.L #b150a, 56(a6); MOVE.W #7000, 54(a6); MOVE.L #b1b42, (a6)` (→`b1b42`)
- `b1b42`: `JSR 43e34.l` — FLOW
- `b1b48`: `JSR 4b54e.l` — FLOW
- `b1b4e`: `BCC.W b1b60` (→`b1b52`) — C 소비
- `b1b52`: `MOVEA.L c(a6), a0; MOVE.B #1, 62(a0); CLR.B 5e(a6)` (→`b1b60`)
- `b1b60`: `RTS` — FLOW

**helper `b1b62` `b1b76` `b1b8c` `b1bc2` `b1bf6` `b1c0e` `b1c4a` 29**
- `b1b62`: `MOVE.W #dc, d0; JSR 49a84.l`
- `b1b6c`: `ADDI.W #50, d0; MOVE.W d0, 94(a6); RTS`
- `b1b76`: `LEA.L b14a0(pc), a0; JSR 1ab02.l` — FLOW
- `b1b80`: `BCC.W b1b8a` (→`b1b84`) — C 소비
- `b1b84`: `JMP 2a24.l` — FLOW
- `b1b8a`: `RTS` — FLOW
- `b1b8c`: `JSR 49a58.l` — FLOW
- `b1b92`: `ANDI.W #7f, d0; MOVE.W d0, d1; MOVE.L #38000, d0; JSR 443d2.l`
- `b1ba4`: `MOVE.L d0, 82(a6); MOVE.L d1, 86(a6); BCLR.B #0, 15(a6); TST.L 82(a6); BMI.W b1bc0` (→`b1bba`)
- `b1bba`: `BSET.B #0, 15(a6)` (→`b1bc0`) — FLOW
- `b1bc0`: `RTS` — FLOW
- `b1bc2`: `TST.W 76(a6); BEQ.W b1be0` (→`b1bca`)
- `b1bca`: `MOVE.W #b7, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `b1bd8`: `MOVE.B #1, 9f(a6); RTS`
- `b1be0`: `MOVE.W #e46, d0; MOVE.B #0, d1; JSR 8ebe.l`
- `b1bee`: `MOVE.B #0, 9f(a6); RTS`
- `b1bf6`: `LEA.L b14b0(pc), a0; CMPI.B #0, 9e(a6); BNE.W b1c08` (→`b1c04`)
- `b1c04`: `LEA.L b14ce(pc), a0` (→`b1c08`) — FLOW
- `b1c08`: `MOVE.L a0, 56(a6); RTS`
- `b1c0e`: `JSR b1bc2(pc)` — FLOW
- `b1c12`: `JSR b1c4a(pc)` — FLOW
- `b1c16`: `MOVE.W #e0ed, 68(a6); MOVE.W #e0ed, 1e(a6); JSR b1bf6(pc)`
- `b1c26`: `LEA.L c8e5e.l, a0; JSR 490ba.l` — FLOW
- `b1c32`: `MOVE.W d0, 54(a6); CLR.B a5(a6); CLR.B a0(a6); CLR.B a7(a6); MOVE.W #7fff, 9a(a6); RTS`
- `b1c4a`: `CMPI.B #1, 9e(a6); BNE.W b1c62` (→`b1c54`)
- `b1c54`: `MOVE.W 7a(a6), 90(a6); MOVE.W 7c(a6), 98(a6); RTS`
- `b1c62`: `CMPI.B #2, 9e(a6); BNE.W b1c80` (→`b1c6c`)
- `b1c6c`: `MOVE.W 78(a6), 98(a6); MOVE.W 2e(a6), 76(a6); MOVE.W 32(a6), 78(a6); RTS`
- `b1c80`: `RTS` — FLOW

**helper `b1cf8` `b1d1e`와 자식 생성기 `b1d40` 12**
- `b1cf8`: `MOVE.W 76(a6), 76(a0); MOVE.W 78(a6), 78(a0); MOVE.W 7a(a6), 7a(a0); MOVE.W 7c(a6), 7c(a0); MOVE.W 7e(a6), 7e(a0); MOVE.W 80(a6), 80(a0); RTS`
- `b1d1e`: `MOVE.W #11, d0; JSR 49a84.l`
- `b1d28`: `MOVE.W d0, -(a7); MOVE.W #11, d0; JSR 49a84.l`
- `b1d34`: `MOVE.W (a7)+, d1; SUBI.W #8, d0; SUBI.W #8, d1; RTS`
- `b1d40`: `MOVE.W 78(a6), d0; SUBQ.W #1, d0` (→`b1d46`)
- `b1d46`: `MOVE.W d0, -(a7); JSR b1d1e(pc)`
- `b1d4c`: `MOVEM.W d0-d1, -(a7); MOVEA.L #b1842, a0; MOVE.W #14, d0; JSR 28ae.l`
- `b1d60`: `MOVEM.W (a7)+, d0-d1; JSR 4970a.l` — FLOW
- `b1d6a`: `JSR b1cf8(pc)` — FLOW
- `b1d6e`: `MOVE.L a0, -(a7); MOVE.W #101, d0; JSR 49a84.l`
- `b1d7a`: `ADDI.W #100, d0; MOVEA.L (a7)+, a0; MOVE.W d0, 92(a0); MOVE.W (a7)+, d0; SUBQ.W #1, d0; BPL.B b1d46` (→`b1d8a`)
- `b1d8a`: `RTS` — FLOW

**helper `b1dae` `b1dfa` 16**
- `b1dae`: `CMPI.B #2, 9e(a6); BEQ.W b1dba` (→`b1db8`)
- `b1db8`: `RTS` — FLOW
- `b1dba`: `MOVE.W #3, d0; JSR 49a84.l`
- `b1dc4`: `CMP.B a0(a6), d0; BEQ.B b1dba` (→`b1dca`)
- `b1dca`: `MOVE.B d0, a0(a6); BCLR.B #0, 15(a6); JSR b1ecc(pc)`
- `b1dd8`: `SUB.W 2e(a6), d0; BMI.W b1de6` (→`b1de0`)
- `b1de0`: `BSET.B #0, 15(a6)` (→`b1de6`) — FLOW
- `b1de6`: `MOVE.W #3d, d0; JSR 49a84.l`
- `b1df0`: `ADDI.W #3c, d0; MOVE.W d0, 9a(a6); RTS`
- `b1dfa`: `TST.B 9f(a6); BEQ.W b1e22` (→`b1e02`)
- `b1e02`: `LEA.L b14a8(pc), a0; JSR b43de.l` — FLOW
- `b1e0c`: `TST.B d0; BEQ.W b1e22` (→`b1e12`)
- `b1e12`: `LEA.L b15bc(pc), a0; JSR b441e.l` — FLOW
- `b1e1c`: `JMP 2a24.l` — FLOW
- `b1e22`: `JSR 49fc6.l` — FLOW
- `b1e28`: `RTS` — FLOW

**helper `b1fd6`(`4945e` 대상 player, 경계 `44602`) 5**
- `b1fd6`: `JSR 4945e.l` — FLOW
- `b1fdc`: `BCS.W b2002` (→`b1fe0`) — C 소비
- `b1fe0`: `MOVE.W 42(a0), d0; SUB.W 42(a6), d0; MOVE.W 46(a0), d1; ADDI.W #20, d1; SUB.W 46(a6), d1; MOVE.L a0, -(a7); JSR 44602.l`
- `b1ffc`: `MOVEA.L (a7)+, a0; ANDI.B #fe, ccr` (→`b2002`) — Clear 생산
- `b2002`: `RTS` — FLOW

**stage event callback `dbf5e` 2**
- `dbf5e`: `MOVE.W #19d7, d0; JSR 3af8.l`
- `dbf68`: `JMP 2a00.l` — FLOW

## N19b로 넘기는 block(31, 결정 1)

[F] 재범위 N19 행 hull의 정적 도달 가운데 이 계약에 넣지 않는 시작(scratch `starts_full.txt` − `starts.txt`; `N19EXTRA="b1656 b16d6 b1d8c"`): `b1656 b165a b1660 b1670 b1686 b1690 b16a4 b16aa b16b0 b16c2 b16c6 b16cc b16d0 b16d4 b16d6 b16e6 b1c82 b1c9e b1ca0 b1cb4 b1cb8 b1cc2 b1cc6 b1cca b1cce b1cdc b1cec b1cf6 b1d8c b1d92 b1da4`. routing 범위는 `b1656..b16ea` `b1c82..b1c90` `b1c9e..b1cf8` `b1d8c..b1dae`(TRAP `b1c90`과 문자열 `b1c92..b1c9e`는 routing하지 않는다)이고 N19 block과 겹치지 않는다. 내용:
- `b1656`(stage event `e8ec8`): `JSR b1c82(PC); JMP 2a00`. `b1c82`: `MOVE.W 78(A6),D0; SUBQ.W #1,D0; CMPI.W #5,D0; BLS.W b1c9e`, 아니면 `TRAP #f`(`TK205A ERR`). `b1c9e..b1cf6`: `MOVEM.W D0-D1,-(A7)`, `28ae` 자식 `b1660` 생성(C 소비 `b1cb4`, `ORI` Set `b1cc2`), `b1cf8`, `MOVEM.L D0-D1/A0`과 `49a84` 난수로 겹치지 않는 bit(`BTST.L D2,D1`/`BSET.B D2,D1`, D2 & `1f`)를 골라 자식 `8e`에 쓰는 반복.
- `b1660`(`28ae` 자식): `20` = `1fb`, `9e` = 0, `b1c0e`, LONG 표 `b15c0`+4·`8e` → `86`, `b160a`, `49a84`, `EXT.L`/`LSL.L #8` 속도, 설치 `b16b0`(fall-through): `b15e0`(C 소비 `b16c2` → `b19b2`), `43ea4`, `b1b76`, `b1dfa`.
- `b16d6`(stage event `e8ed0`): `20` = `1fb`, `9e` = 2, `b1c0e`, `BRA.W b186a`(N19 시작).
- `b1d8c`(범위 밖 미연결 `b1f4e`의 `JSR (PC)` 대상): `49a58`, `ANDI.W #ff`, `443d2`, `ADD.L` 두 번.
- [F] 두 기록 어느 seed도 N19b PC를 실행하지 않는다.

## carry

- [F] **소비 14 block**(BCC/BCS 한 명령, FLOW_ONLY). Unknown C로 들어오면 `objects n19 caller requires known carry`(상태 보존)다. Clear면 BCC는 분기 대상, BCS는 fall-through; Set이면 반대.
  - `b15e6 BCC.W b15f4`, `b1b4e BCC.W b1b60`: U01 `4b54e`의 C(U01 결정 2: `4b6be` Clear, `4b6ca` ORI Set).
  - `b1702 BCS.W b170c`: cleanup `287e`의 C(`CMP.W 10(A0),D0`; 무부호 `WORD 10(A6) < WORD 10(8(A6))`이면 Set → 생존, 아니면 Clear → `JMP 2a00`).
  - `b173e BCC.W b1750`: fade_card `28ae`의 C(`2908` ORI Set = 자식 생성 / `290e` ANDI Clear = 빈 slot 없음).
  - `b1760 BCS.W b1776`: U20 `497a6`의 C(BYTE `10fd92` = 0이면 `497b0` ORI Set, 아니면 Clear).
  - `b17e8 BCC.W b17f2`: interpreter `49fc6`의 C. Set → `JMP 2a00`.
  - `b1804 BCS.W b1826`: N19 `b1fd6`의 C(`b2002 RTS` 앞: `4945e` Set 그대로 또는 `b1ffc` ANDI Clear).
  - `b1898 BCC.W b18ac`: N19 `b1dfa`의 C(`b1e28 RTS` 앞 `49fc6`의 C; `9f` ≠ 0이고 `b43de` 결과 ≠ 0이면 `JMP 2a24`로 돌아오지 않는다).
  - `b18f2` `b1966` `b19a0 BCS.W b19b2`: N19 `b15e0`의 C(`b15fe` Set / `b1604` Clear).
  - `b194c BCS.W b186a`: 경계 `b1ee6`의 C(결정 4).
  - `b1b80 BCC.W b1b8a`: U05 `1ab02`(사각형 `b14a0` 화면 판정)의 C(U05 `1ab7a` Clear / U01 `1aafc` Set). Set → `JMP 2a24`.
  - `b1fdc BCS.W b2002`: N08 `4945e`의 C(`494a6`/`494ae` ANDI Clear, `494ba` ORI Set).
- [F] **known 생산 4 block**: Set `b15fe`(`ORI.B #1,CCR; RTS`), Clear `b1604`(`ANDI.B #fe,CCR; RTS`), Set `b174c`(`ORI.B #1,CCR`, 결정 5), Clear `b1ffc`(`MOVEA.L (A7)+,A0; ANDI.B #fe,CCR`, → `b2002`). 앞의 둘과 `b1ffc`는 RTS 앞 known C이고 소비자는 위 목록이다(결정 3).
- [F] **FLOW_ONLY 98 block**(C 보존): JSR/JMP/BRA/RTS block, `LEA`+`JSR`(`b1b76` `b1e02` `b1e12`), `LEA`+`BRA`(`86776`), `LEA`(`8677e` `b1c04`), `MOVEM.W (A7)+`+`JSR`(`b1d60`), BTST/BSET/BCLR(Z만)+Bcc block, BCC/BCS 소비 14개. 목록: `86742` `86746` `8674c` `8675a` `86776` `8677e` `86798` `867ca` `867d0` `867f0` `86800` `86810` `b15e0` `b15e6` `b15f4` `b160a` `b1628` `b1642` `b1654` `b16ea` `b16fc` `b1702` `b1706` `b170c` `b173e` `b1750` `b175a` `b1760` `b1772` `b1784` `b17dc` `b17e2` `b17e8` `b17ec` `b17f2` `b1804` `b1826` `b182c` `b1884` `b188e` `b1894` `b1898` `b18b4` `b18b8` `b18d6` `b18ea` `b18ee` `b18f2` `b1916` `b1918` `b1936` `b193a` `b1948` `b194c` `b1950` `b1954` `b195a` `b195e` `b1962` `b1966` `b1972` `b1974` `b1998` `b199c` `b19a0` `b19a4` `b19b0` `b19d6` `b1b42` `b1b48` `b1b4e` `b1b60` `b1b76` `b1b80` `b1b84` `b1b8a` `b1b8c` `b1bba` `b1bc0` `b1c04` `b1c0e` `b1c12` `b1c26` `b1c80` `b1d60` `b1d6a` `b1d8a` `b1db8` `b1de0` `b1e02` `b1e12` `b1e1c` `b1e22` `b1e28` `b1fd6` `b1fdc` `b2002` `dbf68`.
- [F] **carry 보존 목록 98 PC** = FLOW_ONLY 98.
- [F] **Unknown 108 block**: 그 밖 `MOVE`/`CLR`/`TST`/`CMP`/`CMPI`/`ADDI`/`SUB`/`SUBI`/`SUBQ`/`NEG`/`ANDI` 포함 block, `MOVE.L #imm,(A6)` 설치 block, `MOVEA.L #imm,A0`+`MOVE.W`+`JSR 28ae` 자식 block(`b172e` `b1852` `b1d4c`), animation block(`MOVEA.L #rec,A1; MOVE.W #100,D0; JSR 49f8c`), 스택 WORD/LONG block. 목록: `86752` `86764` `8676e` `86782` `8678e` `86790` `867a2` `867ac` `867b2` `867ba` `867c8` `867d8` `867e2` `867e8` `867fa` `8680a` `b15ea` `b1610` `b1618` `b162a` `b1632` `b1644` `b16ee` `b16f6` `b1710` `b1718` `b171e` `b1726` `b172e` `b1742` `b1754` `b1764` `b1776` `b1790` `b179a` `b17a2` `b17d6` `b17f4` `b1808` `b181e` `b182e` `b1838` `b1842` `b1852` `b1862` `b186a` `b1888` `b189c` `b18ac` `b18be` `b18c6` `b18da` `b18f6` `b18fe` `b190c` `b191c` `b1924` `b192c` `b193e` `b196a` `b1978` `b1986` `b19a8` `b19b2` `b19bc` `b19c6` `b19da` `b19ea` `b1b24` `b1b2e` `b1b52` `b1b62` `b1b6c` `b1b92` `b1ba4` `b1bc2` `b1bca` `b1bd8` `b1be0` `b1bee` `b1bf6` `b1c08` `b1c16` `b1c32` `b1c4a` `b1c54` `b1c62` `b1c6c` `b1cf8` `b1d1e` `b1d28` `b1d34` `b1d40` `b1d46` `b1d4c` `b1d6e` `b1d7a` `b1dae` `b1dba` `b1dc4` `b1dca` `b1dd8` `b1de6` `b1df0` `b1dfa` `b1e0c` `b1fe0` `dbf5e`.
- [F] N/Z 재계산이 필요한 block 경계는 없다(block을 flag 읽기로 시작하는 곳은 위 C 소비 14곳뿐이다). 모든 비교·`TST`·`SUB`·`SUBQ`·`ANDI`와 그 Bcc는 같은 block 안에 있다(`b1d7a`의 `SUBQ.W #1,D0; BPL.B b1d46`, `b1dc4`의 `CMP.B; BEQ.B` 포함).

## 구현 범위와 규약

- routing 8 범위(위 표). 짝수 PC 894개 중 block 시작 210, 내부 684. 내부 PC 직접 진입은 `unsupported animation objects n19 PC`다. 범위 이웃과 구멍(N19b 범위, TRAP·문자열, 자료)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow에 기대지 않는다. 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 98 PC를 넣는다. `b15fe` `b174c`는 실행 뒤 Set, `b1604` `b1ffc`는 Clear를 둔다.
- 제어 이동: 모두 정적이다. 설치 값(`MOVE.L #imm,(A6)`)은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다. `28ae` 자식 대상(A0 = `b175a`/`b1842`/`b1b24`)과 `56(A6)` = `b150a`, `b14b0`/`b14ce`도 자료다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(`b16f6`→`b16fc`, `b17d6`→`b17dc`, `b1888`→`b188e`, `b1b2e`→`b1b42`). `b1924` `b1978` `b19ea`는 설치 뒤 RTS다.
- 스택: JSR 복귀 LONG, 결정 6의 WORD/LONG/MOVEM.W. work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 live bus(`am_read`)다(N19 자신은 고정 ROM 자료를 읽지 않는다; 다른 단위 callee가 사각형·기록을 읽는다). work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] 주소만 넘기는 고정 ROM 자료: 사각형 `b14a0`(A0, `1ab02`; `ffe0 fff0 0040 0020`), `b14a8`(A0, `b43de`; `fff8 fffe 0010 000c`), `b15bc`(A0, `b441e`), `c8e5e`(A0, `490ba`), animation 기록(A1, `49f8c`; D0.W = `100`): `b2040` `b2022` `b2004`(`b160a`, `49a58` 결과 & 3 = 0 / 1 / 그 밖), `b23f0`(`b17a2`), `b2206`(`b186a` `b189c`), `b225c` `b22e0`(`b18c6` `b18da`, `49a58` 결과 bit 0), `b213a` `b205a`(`b19c6` `b19da`, `a7` = 7 여부). 노드에 저장: `56(A6)` = `b150a`(`b1b2e`; `ffe0 ffe0 0040 0040`), `b14b0`/`b14ce`(`b1c08`; `9e` ≠ 0 / = 0).
- [F] work RAM:
  - 노드 A6: BYTE `15`(bit 0: `867ba` 읽기, `b1784` `b186a` `b1ba4` `b1dca` 지움, `b179a` `b1bba` `b1de0` 세움; bit 7: `86800` 읽기), `5e`(`b15ea` → `a7`, CLR; `b1b52` CLR), `61`(bit 7 `b15f4`), `62`(`b191c` CLR, `b196a` TST), `84`(bit 0 `8675a`, bit 3 `867f0`, bit 7 `86798`), `85`(TST 부호·0), `9e`(= 1 `b1842`, CMPI 1/2/0), `9f`(= 1/0 `b1bd8`/`b1bee`, TST), `a0`(CMP·저장), `a5` `a7`(CLR `b1c32`; `a7` = 7 비교), `a6`(CLR `b16ee` `b1754`, TST); WORD `1e` `68`(= `e0ed`), `20`(= `1fb` `b1842`, `e2` `b17a2`), `2e`/`32`(LONG 복사 뒤 상위 WORD 덧셈; `b1c6c` → `76`/`78`; `b1dd8` SUB), `42` `46`(위치), `54`(= `490ba` 결과 `b1c32`, `7000` `b1b2e`), `76`(TST `b1bc2`; `b1cf8` 복사), `78`(→ `b1d40` 개수, `98` `b1c6c`), `7a` `7c`(→ `90` `98` `b1c54`), `7e` `80`(복사), `8c`(비교), `8e`(TST), `90`(TST `b1862`), `92`(자식 `92` = `100`+난수 `b1d7a`), `94`(= `50`+난수, 감소), `96`(= 7, 감소), `98`(비교·`ffff`), `9a`(= `7fff`, 감소, = `3c`+난수), `9c`(= `28`+난수, 감소·0 하한); LONG `(A6)`(설치), `c`(부모 노드), `8`(목록 이웃, `287e`), `36` `3a`(CLR·속도), `56`, `64`(CLR), `82` `86`(`443d2` 결과, `b1986` → `36`/`3a`), `8a`(대상 노드 `b1808`, CLR).
  - player 노드 `100cb8`(`-7348(A5)`)·`100da8`(`-7258(A5)`)의 WORD `42`; `4945e`가 돌려준 A0의 WORD `42` `46`(`b1fe0`); 부모 노드 `c(A6)`의 BYTE `62`(= 1 `b1b52`)와 LONG `8a`(대상 노드, `b17a2`) → 대상 노드 LONG `2e` `32`; `28ae`가 돌려준 자식 A0의 WORD `76`~`80`(`b1cf8` 복사), `92`; 절대 WORD `10d418`(`b18fe`, 무부호 비교).
- [F] 상수 인자: `4c1de` D0.W = ±8, `49a84` D0.W = `50`(`b182e`) `dc`(`b1b62`) `11`(`b1d1e` 두 번) `101`(`b1d6e`) `3`(`b1dba`) `3d`(`b1de6`), `443d2` D0 = `20000`(`b1808`, D1.W = D0.B) / `38000`(`b1b92`, D1.W = D0 & `7f`), `8ebe` D0.W/D1.B = `37a`/`3ba`/`b7`/`e46`, 0, `28ae` D0.W = `14`, `4970a` D0.W/D1.W = 0/0(`b1742`) 또는 `MOVEM.W`로 돌려받은 부호확장 난수 −8..+8(`b1d60`), `3af8` D0.W = `187f`(`b19b2`) / `19d7`(`dbf5e`), `49290` D0.W/D1.W = 0/0.
- [I] 게임 의미: `86742`는 N18 `8664c` 계열 객체의 `92` ≠ 0 상태 대기(대상 거리에 따라 공격 `86fca`/`8698c`, 지형 `4c1de` 결과로 `86d0c`/`86fca`, `8e` = 0이면 화면 판정 `871ee`)다. `b16ea`는 `78`마리의 `b1842` 자식(무작위 −8..+8 위치)을 만드는 생성기이며, 자신(`b16fc`)은 목록 이웃과의 순서 비교(`287e`)로 지워질 때까지 타이머 `9c`마다 `b175a` 자식(조준 대상 `8a` 위치의 효과)을 만든다. `b1842`는 `b1b24` 자식을 붙인 비행 객체로 `94`/`9a` 타이머와 `b1dae` 방향 선택, `b15e0` 피격 판정(`b19b2` 파괴 소리 `187f`)을 갖는다. `dbf5e`는 소리 `19d7`만 내고 지워지는 stage event다. 확인하지 않았다.

## 의존·경계

- [F] N19 → 기존(모두 routing됨, 진입 case 있음): N18 `864b6` `8625a`(BRA), U11 `4be06`, interpreter `49fc6`(C 반환) `49f8c`, U15 `4c1de`, U01 `4b54e`(C 반환), stage_area `49a58`, stage_event_ops `49a84`, cleanup `287e`(C 반환) `2a24`(JMP) `43e34`, fade_card `28ae`(C 반환) `2a00`(JMP), N14 `4970a`, U20 `497a6`(C 반환), U02 `8ebe` `443d2`, U04 `43ea4`, U05 `1ab02`(C 반환), U12 `490ba`, U08 `49290`, sound `3af8`, N08 `4945e`(C 반환).
- [F] 실행부 없는 경계: `44602` `b43de` `b441e` `b1e2a` `b1e74` `b1ecc` `b1ee6` `b1f1a`. 단위 test는 그 PC에서 stop만 확인한다(F4 test 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`와 영구 비routing 자료·TRAP(`b14a0` `b15c0` `b1c90` `b1c94` `b2004`)만 쓴다(N19b 범위 PC는 쓰지 않는다).
- [F] 다른 단위 → N19: N18 `86734`의 설치 `86742`, stage event 표(`e8ecc` `dbf7a`), 범위 밖 미연결 코드의 `JSR (PC)`(요약). N19b가 병합되면 `b1656` `b16d6` `b1d8c`가 이어진다.
- [F] N18·N20과 범위가 겹치지 않는다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 210 시작 모두 typed fixture로 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, Set 2·Clear 2, 그 밖 Unknown), zero-step, 내부 684 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`와 영구 비routing 자료·TRAP만, 소비 14곳의 Unknown carry 오류, 경계 stop. 사각형은 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 소비자 C는 실제 생산자(`4b54e` `287e` `28ae` `497a6` `4945e` `1ab02`, N19 RTS 생산자 `b15fe` `b1604` `b1ffc`)를 따라 들어간 fixture로 native 분기를 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다.
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, 회귀 0, complete 126 → 128(seed 12 13).

## 작업자 검증 기록 (scratch)

- [F] 변경 파일: 새 `engine/src/animation_machine_objects_n19.cpp`(SHA256 `c6e9075591a22f52868b5c993938a95e8d6b75e7eeff346db9c9329f110e2eef`), 새 `engine/tests/animation_machine_objects_n19_test.cpp`(SHA256 `352a7812b5b50ae2496dbd656bb2d9deec6bdf376557dfdea172f391ca9b4100`), 공유 최소 수정 `engine/src/animation_machine.cpp`(routing `else if` 1개 8 범위, carry 보존 case group 1개 98 PC; SHA256 `09282b7c05e36c4ea33e23601b6651552bc30c03f8f05e70f6de310b4f085394`, routing 규칙 75 → 76), `engine/src/animation_machine_internal.h`(선언 1줄; SHA256 `73c1f0372a1b89af922a6414c639a22136847604f0333dc5304287a7ddee1652`), `Makefile`(source list·test target·run line; SHA256 `570a499d6213c9b4e6c60c9a55a287ad0ae123a1efd36667b7289a67c9e976e6`), `tools/verify_animation_machine.py`(SOURCES; SHA256 `8731e585bfebf45ec09af8b89548fd01045647ad8faa1ffe3784718c865bc724`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 고치지 않았다. 패치 파일 없음(결정 9).
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0. 새 test: `animation machine objects n19: 624 fixtures (24 checked errors, 176 kept C), 210 blocks, 2603 calls`. N18 test(`86742` stop 포함)도 그대로 통과. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen19.py`, Unicorn + 합성 물리 바이트 `b14a0`; 표 SHA256 `d9a5fa3372d6b74049f4d165ee7fec651eb5d4957e6ae4d146e96a24ffda1126`): 210 시작 모두 fixture로 덮임. 실제 생산자 추종 fixture: `4b54e`(`56` = 0, `5e` 0/≠0, `61` bit 7 → `b15e6`·`b18f2`·`b1966`·`b19a0`·`b1b4e`), `287e`(`10` WORD 대소 6조합 → `b1702`), `28ae`+`4970a`/`49214`/`43e38`(성공/실패 → `b173e`, `b174c` ORI 뒤 `b1750`; `b1852`, `b1d4c`), `497a6`(`10fd92` 0/≠0 → `b1760`), `4945e`+`49370`(`568e` 0/1/2/3, 거리 → `b1fdc`, Set이면 `b2002` RTS → `b1804`), `1ab02`(사각형 `b14a0`, 안/밖 → `b1b80`). RTS 앞 known C: `b15f4` 진입에 복귀 LONG `b18f2`/`b1966`/`b19a0`(`61` bit 7 양쪽), `b1ffc` 진입에 복귀 LONG `b1804`로 native 분기 확인. `b17e8`·`b1898`(`49fc6`)과 `b194c`(경계 `b1ee6`)는 typed C, `b17e8`·`b1898`은 실제 ROM 차분에서도 실제 `49fc6` 뒤 확인. block 표는 시작마다 incoming C clear/set의 native 후계·digest와 계약 C 분류(시작별 generic 추가 상태: `b1d34` WORD+복귀 LONG, `b1d7a` A0 LONG = work RAM), Unknown C는 소비 14곳에서 정확한 오류, zero-step 210×3, 내부 684 PC 정확한 오류, 홀수 PC(범위마다 양 끝), RAM rollback 탐침 `10fe10` `10fe20` `10fe30`과 RTS 복귀 `10fe40`(11 fixture), routing 밖 `b14a0` `b15c0`(자료) `b1c90`(TRAP) `b1c94`(문자열) `b2004`(기록), 경계·다른 단위 stop 34곳(`44602` `b43de` `b441e` `b1e2a` `b1e74` `b1ecc` `b1ee6` `b1f1a`와 다른 단위 진입). checked 오류 fixture 10개(홀수 노드 읽기·쓰기, 홀수 자식 쓰기, ROM 노드, 장치 쓰기, 스택 장치, RTS 장치, WORD push 장치, WORD pop 장치, `b17a2` 홀수 대상 노드). 돌연변이 16개(`86790` 부호 비교, `867b2` 부호 비교, `b15fe` C, `b1ffc` C 누락, `b1d60` 부호확장, `b1d4c` push 순서, `b17a2` 상위 WORD, `b18fe` 무부호 비교, `b1702` 분기 방향, `b1710` BPL, `b1c6c` 읽기·쓰기 순서, `b1d7a` 반복 조건, `b1ba4` LONG 부호, `b1808` BYTE mask, `b174c` Set 누락, `b1dc4` BYTE 비교)가 모두 test를 실패시켰다(scratch `mut/mut.out`).
- [F] 실제 ROM 차분(`realrom/real19.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, 무작위 work RAM, seed 1·2·3 각 1,500건): 불일치 0/0/0, 시작 도달 209/209/210(합집합 210). native stop은 STOP·`2a00`·`2a24`와 경계(`44602` `b43de` `b441e` `b1e2a` `b1e74` `b1ecc` `b1ee6` `b1f1a`, N18 꼬리의 `cc778`). 실제 생산자 뒤 소비자 native 분기 비교(seed 1): `b15e6` 261, `b1702` 143, `b173e` 40, `b1760` 70, `b17e8` 32, `b1804` 31, `b1898` 62, `b18f2` 124, `b1966` 60, `b19a0` 55, `b1b4e` 76, `b1b80` 236, `b1fdc` 123건(`b194c`는 경계 `b1ee6` 때문에 0). native가 깨끗이 멈추지 않은 입력(무작위 포인터로 낮은 PC, 3M 명령 안에 끝나지 않음)은 건너뛰고 셌다(145/117/128건). 홀수 주소·Unknown C 진입 차이 0.
- [F] 기준(`b212aea` `git archive` 사본 `ms5-scratch/n19/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 14,168·node 118,740, 불일치 0, 자연 완주 71(`diff_results.json` SHA256 `e816f7bf7abe04ae099e515e746e4c0475772b7b4e221d3945c5fa08e39ee5f3`). N19 뒤: 일치 pass 14,168·node 118,748, 불일치 0, 완주 71, 회귀 0, 바뀐 seed는 12 13뿐(SHA256 `2a0827daa074507b03e71232567e8f3ec31375155c9299ab98199cb7c168002b`). seed 12 13(base 기록 native frame 1)은 이제 `dbf5e` `b16ea`를 지나 native 끝과 같은 지점(native `49a80` 쓰기 보호 주소 `30`, 난수 포인터 미초기화)에서 C++ guard `stage area RNG pointer outside work RAM`(상태 보존)로 멈춘다(node 4 → 8). 기록 자체가 frame 0에서 끝나므로 완주 수는 바뀌지 않는다.
- [F] RNG 초기화 400 frame 차분: 기준 complete 126, 일치 pass 50,400·node 374,353, 불일치 0(verification.json SHA256 `b4475247097c81765d6bcf70d70eb7b718b471a5457cc78343f9763352c42eeb`). N19 뒤: complete **128**(+12 13), 일치 pass 51,200·node 382,637, 불일치 0, 회귀 0, `other` 0, 응답 `00` 변형 6 seed complete 6 유지, 도구 종료 0(SHA256 `2490f4b4038e7167121ef8c55ba8a92fd929661dca2f3cbfebb051c5a5081e8b`). 분류가 바뀐 seed는 12 13(`checked-current-first-unrouted-PC` → `complete`, pass 400, node 4,146)뿐이다. 재범위 예측(N19 누적 RNG 128)과 같다.
- [F] ROM SHA256·mtime 작업 전후 같음(`29112a94…`, `1791291625`).

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] N19b 31 block(결정 1)과 범위 밖 경계 `44602` `b43de` `b441e` `b1e2a` `b1e74` `b1ecc` `b1ee6` `b1f1a`, 고아 설치 `b19f2`(와 그 본문의 `b1a46` `b1ac2`), `86e76` `86fca` `8698c` `86d0c` `871ee`의 동작은 해당 단위에서 정한다.
3. [U] `b194c`(경계 `b1ee6`의 C)의 실제 생산자 추종 확인은 `b1ee6`이 routing된 뒤에 한다.
4. [U] `4b54e`의 `56(A6)` ≠ 0 경로(U01 본문)를 따라간 `b15e6`·`b1b4e` 소비는 실제 ROM 차분의 무작위 입력으로만 확인했다(typed fixture는 `56` = 0).
5. [U] 68000 `MOVEM.W (A7)+`의 끝 추가 읽기 bus cycle은 모델링하지 않았다(결정 6).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n19/`(`n19.py` block·범위 계산(`N19EXTRA`/`N19STOPS`), `n19cls.py` carry 분류, `n19fmt.py` block 목록, `n19stat.py` 범위 SHA·짝수 PC, `n19xref.py` 범위 밖 참조, `n19seen.py` 자연 도달, `unitdef.py`, `gen/` typed fixture 생성·test 조립, `mut/` 돌연변이, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스·RNG 차분, `doc/` 계약 조립; 저장소 밖).
