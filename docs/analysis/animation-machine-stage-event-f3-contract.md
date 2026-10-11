# stage event F3: `e9150` event interpreter 계약 초안

**상태: 메인 결정 반영 계약. 구현·검증 기록이 아니다.**

메인 결정(Claude Opus 5.5; `e98e0..e98f2`·`e938e..e93a2` capstone 재디코드로 평가기 끝 `MOVE.B (A7)+,D0; RTS`와 호출 지점 BEQ 확인):
1. `e94fe`에서 F3a(134 block)·F3b(109 block + TRAP 8)로 나눈다. F3b는 op `0c`의 `49a58` 때문에 F1c2 뒤다.
2. 계산 PC 표는 권고대로: 원본 코드가 범위를 막는 표 4개는 그대로, 상한 없는 `e97e0` 표는 F1 결정 3(대상이 지원 block 시작이면 실행, 아니면 unsupported/unaligned).
3. 이전 block Z 소비는 선택 A(묶기). `e98ea` block은 BYTE pop·Z 계산 뒤 복귀 LONG이 알려진 호출 넷이면 그 분기까지 같은 block에서 평가하고, 그 밖이면 PC=복귀 LONG이다. 6 PC 직접 진입은 묶인 PC로 거부한다. 공개 header는 바꾸지 않는다.
4. TRAP #15 8곳은 stop 경계. 5. BYTE stack push/pop은 F1c 규칙(A7±2, BYTE 하나). 6. op `09`의 `28ae` 실패는 원본대로(sentinel `100e98` 쓰기).
7. 무한 루프·과다 반복은 원본대로 block budget에 맡기고 RAM 밖 쓰기는 checked 오류. 8. ROM 자료는 physical window만.
9. 파일·오류 문자열은 본문 결정 9 권고대로.
10. seed는 node 단위(PC=`2ab8`, A6=node, `2ac2` stop). 산출물은 F1b 결정 5와 같이 모든 단계 전체 상태 SHA, 전체 dump는 typed fixture 전부와 자연 seed 표본(seed 8개 전체 frame)과 경계 frame에 둔다. 범위 근거는 `animation-machine-frontier-after-480bc-scope.md`의 F3와 F1a 계약(`animation-machine-stage-controller-f1-contract.md`)의 `e905c` 항목이다. 구조와 규약(block 시작, 묶인 분기, carry 보존 목록, 계산 PC, TRAP 경계, ROM window)은 확정된 F1a·F1b·F1c·U7 계약을 따른다. 실행 규약(node 단위 실행·프레임 패스)은 같은 시점의 F2 계약 초안(`animation-machine-scheduler-shell-f2-contract.md`)과 짝이다.

Claude Opus 5.5 / high 읽기 전용 분석 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, fixed CPU 주소=file offset)을 capstone M68000으로 디코드했다. F3의 코드와 자료는 모두 fixed `<100000`이다. 기존 실행부와 routing은 작업 트리 `/Users/start/Workspce/metalslug-input`(HEAD `543a3a4`, F1b WIP 포함)을 읽기 전용으로 참조했다. F1c block은 F1c 계약의 closure(`f1c/f1c.json`)를 기존으로 취급했다. 관측 산출물은 Unicorn으로 읽기 전용 재생했다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 수는 scratch `f23/clos3.py`·`blk3.py`·`fin3.py`가 원본 opcode에서 계산했다.

## 요약

- [F] **범위 정정.** `2a28`(node 설치)은 이미 cleanup 실행부에 있다. F3의 실체는 `e9150`(초기화)·`e9176`(매 frame callback)의 stage event 해석기, 자식 thread 해석기 `e9350`/`e9362`, 표현식 평가기 `e97c8`, opcode `08..0f` 처리기, 그리고 공유 helper(`288c`, `48502`, `1a910`/`1a92c`/`1a93e`, `49a84`)다.
- [F] 정적 closure(기존 routing·F1a·F1b·F1c에서 멈춤)는 **block 시작 243개 + TRAP 경계 8개**다. 코드 15 범위 2,076바이트, 595명령이며 미해독은 없다. 243에는 계산 PC 표 slot 61개(`e91e4` 8, `e941c` 3, `e9538` 8, `e9790` 8, `e97e4` 34)와 callback 진입 4개(`e9150` `e9176` `e9350` `e9362`)가 들어 있다. 일반 leader 규칙으로는 249개다. 결정 3에 따라 이전 block의 Z를 소비하는 6개(`e9396` `e939e` `e94c0` `e96b0` `e96d0` `e96fe`)를 묶인 PC로 옮겼다.
- [F] 범위 문서 추정(~130~150)보다 크므로 **분할을 권고**한다(결정 1).

| 단위 | 진입→끝 | block 시작 | 경계 | 자연 시작 상태 | 주 위험 |
| --- | --- | --- | --- | --- | --- |
| **F3a** 해석기 core·opcode `00..07`·평가기 | node callback `e9150`/`e9176`→RTS | 134 | `e94fe`(F3b 진입) | node 실행 11,391회(134 seed) | `e97e0` 상한 없는 계산 PC, 평가기 Z 반환, BYTE stack |
| **F3b** opcode `08..0f`·자식 thread·skip | `e94fe`, callback `e9350`/`e9362`→RTS/`2a00` | 109 | TRAP 8(`e93d8` `e9528` `e9530` `e957a` `e96d4` `e9702` `e9780` `e9788`) | node 실행 777회(frame 0 `e9150` 95 seed, 자식 676회) | 객체 생성(`2986`/`28ae`), A7 배열(op `0c`), RNG `49a58`(F1c2), copy 루프 |

- [F] 기록된 어떤 산출물도 `e9150`을 실행하지 않았다(`100bf4`=`e9150` 상태 303개, `e9176` 상태 0개). 자연 시작 상태는 F2 계약의 선언 프레임 패스 모델로 Unicorn에서 새로 만든다(아래 "자연 시작 상태").

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

### 1. F3 분할

- 선택 A: F3 전체(243+TRAP 8)를 한 실행부로 구현한다.
- 선택 B(**작업자 권고**): `e94fe`(opcode `08..0f` 진입)에서 나눈다.
  - **F3a(134)**: `e9150..e9350`(표 `e91e4` 8 slot 포함), opcode `00..07` 처리기 `e9444..e94fe`, 길이 전진 `e9768..e9774`, 평가기 `e97c8..e98ee`(표 `e97e4` 34 slot), helper `48502..4855c`, `1a910..1a91a`, `1a93e..1a952`. `e94fe`는 실행부 없는 stop 경계다.
  - **F3b(109+TRAP 8)**: `e94fe..e957c`, `e958e..e9768`, `e9774..e97c8`, 자식 해석기 `e9350..e93da`·`e93f0..e9444`, helper `288c..289e`, `1a92c..1a93e`, `49a84..49a8e`.
  - [F] 두 집합은 서로소이고 합이 243이다. F3a에서 F3b로 가는 길은 `e91ac BSR e94fe`와 평가기 반환(결정 3)뿐이다. F3b는 F3a의 opcode `05..07` 처리기(`e94b8` `e94d0` `e94f6`), `e9768`, `e97c8`, `e9298`, `e932c`를 부른다.
  - [F] 자연 node 실행 12,168회 중 11,391회(`e9176` 11,352, `e9150` 39)는 F3a block만 지난다. F3b는 frame 0의 `e9150` 95회(opcode `08`·`09`로 객체·자식 생성), `e9176` 6회, 자식 callback 676회가 지난다.
- 선택 C: F3b를 다시 자식 thread(`e9350` closure)와 opcode `08..0f`로 나눈다. [I] 비권고. 자식 thread는 opcode `09`가 만들고 자식 stream도 `08..0f`를 쓰므로 한쪽만으로는 자연 seed가 생기지 않는다.
- 순서 권고: **F3a → F2 → F3b**(F2 계약 결정 5). [F] F3b의 op `0c`는 F1c2 block `49a58`(RNG)을 부르므로 F3b는 F1c2 뒤다.

### 2. 계산 PC 표 정책

- [F] 다섯 표 중 넷은 원본이 범위를 보장한다.

| JMP/JSR | 표 | index 보장 근거 | slot |
| --- | --- | --- | --- |
| `e91ba JSR e91e4(PC,D7.W)` | 주 opcode `00..07` | `e919c` ≥`10`이면 종료, `e91a4` `08..0f`이면 `e94fe`, `LSL.W #2` | 8 |
| `e93f2 JSR e941c(PC,D7.W)` | 자식 opcode `05..07` | `e93ac` BPL, `e93be` <8, `e93d2 SUBQ.B #5`+BCC(아니면 TRAP `e93d8`) | 3 |
| `e9534 JMP e9538(PC,D0.W)` | opcode `08..0f` | `e9524` ≥`10` TRAP `e9528`, `e952a SUBQ.B #8` borrow TRAP `e9530` | 8 |
| `e978c JMP e9790(PC,D0.W)` | skip `08..0f` | `e977c` TRAP `e9780`, `e9784` TRAP `e9788` | 8 |
| `e97e0 JMP e97e4(PC,D1.W)` | 평가기 연산자 `80..a1` | `e97cc` ≥`80`만 온다. **상한 검사 없음**(index 0..`7f`) | 34 |

- 권고: `e97e0`은 F1 메인 결정 3의 계산 PC 정책을 따른다. PC=`e97e4`+4×(op−`80`)로 옮기고, 그 PC가 F3 block 시작이면 실행, 아니면 `unsupported animation stage event PC`로 처리한다. 홀수는 나올 수 없다.
  - [F] 표 밖(op `a2..ff`)에서 block 시작에 닿는 값: `a2`→`e986c`, `a5`→`e9878`, `a6`→`e987c`, `a8`→`e9884`, `aa`→`e988c`, `ac`→`e9894`, `ae`→`e989c`, `b3`→`e98b0`, `b8`→`e98c4`, `bd`→`e98d8`. 원본대로 실행한다. 예를 들어 `a2`는 `e986c`에서 BYTE `10de30+22`를 push한다.
  - [F] 명령 내부·다른 루틴(`e98ee` 이후 포함)에 닿는 76개는 unsupported다.
- [F] 표 slot 61개는 모두 `BRA.W`이며 FLOW_ONLY다.

### 3. 이전 block의 Z 소비(새 유형)

- [F] F1a~F1c와 달리 F3에는 **이전 block의 Z를 소비하는 block 시작**이 6개 있다.
  - 평가기 반환 4개: `e97c8` 평가기는 `e98ea MOVE.B (A7)+,D0`; `RTS`로 끝난다. 호출 지점의 복귀 PC가 곧바로 Z로 분기한다: `e9396 BEQ.W e9428`, `e939e BEQ.W e9428`, `e94c0 BNE.W e9768`, `e96b0 BEQ.W e96b8`. [F] `e97c8`의 호출자는 fixed ROM 전체에서 이 넷(`e9392` `e939a` `e94bc` `e96ac`)뿐이다.
  - 조건분기 fall-through 2개: `e96cc CMPA.L (A7),A0`; `BCS e96c8` 다음 `e96d0 BEQ.W e96d6`. `e96f8..e96fa CMPA.L (A1),A0`; `BCS e96f0` 다음 `e96fe BEQ.W e9704`.
- 선택 A(**작업자 권고**, 묶기):
  - `e96d0`·`e96fe`는 block 시작에서 빼고 앞 block에 묶는다. `e96cc` block은 BCS·BEQ 두 분기를 모두 처리하며 fall-through는 TRAP `e96d4`다. `e96f8` block은 fall-through가 TRAP `e9702`다.
  - `e98ea` block은 D0.B=BYTE `(A7)`, A7+=2, Z=(D0.B==0)로 처리한 뒤 복귀 LONG R을 pop한다. R이 위 넷 중 하나면 그 분기를 같은 block에서 평가한다(`e9396`/`e939e`: Z면 `e9428`, 아니면 `e939a`/`e93a2`. `e94c0`: Z가 아니면 `e9768`, 아니면 `e94c4`. `e96b0`: Z면 `e96b8`, 아니면 `e96b4`). R이 그 밖이면 PC=R로 둔다(균형이 깨진 표현식 등. 이후 routing이 판단한다).
  - 이 6 PC는 직접 진입을 거부한다(묶인 PC). 갈래 PC `e939a` `e93a2` `e96b4` `e96b8`은 F3b, `e94c4` `e9768`은 F3a다.
- 선택 B: `AnimationMachineState`에 Z 추적을 더한다. 공개 header가 바뀌어 비권고.
- 선택 C: 6 PC 진입을 checked 오류로 둔다. 자연 경로(`e94c0` 400회 이상)가 막혀 불가하다.

### 4. TRAP 경계(F3b)

- [F] 8개 모두 `TRAP #15`이고, 일부 뒤에는 ASCII 오류 문자열이 붙어 있다.
  - `e93d8`: 자식 opcode <5. 뒤 문자열 `HOJU TABLE CODE ERROR`(`e93da..e93f0`).
  - `e9528`/`e9530`: `e951c` opcode ∉`08..0f`. opcode `0a`/`0b`/`0c`가 다음 op를 바로 실행할 때만 닿는다.
  - `e957a`: opcode `08`의 `2986` 객체 생성 실패(C=0). 뒤 문자열 `SET MAKE FAIL!!`(`e957c..e958e`).
  - `e96d4`/`e9702`: op `0b`/`0c` 구간 끝을 넘어 진행했을 때.
  - `e9780`/`e9788`: skip 대상 opcode ∉`08..0f`.
- 권고: F1a 결정 4와 같다. 실행부 없는 경계로 두고, stop이면 직전 상태로 멈추고 아니면 rollback한다. 문자열 바이트는 코드 범위에서 뺀다.
- [F] 자연 재생에서 TRAP은 한 번도 닿지 않았다.

### 5. A7 위 BYTE stack과 배열

- [F] 평가기는 `MOVE.B Dn,-(A7)`·`MOVE.B #imm,-(A7)`(A7−2, 상위 BYTE 하나만 씀)로 값을 쌓는다. 연산은 `MOVE.B (A7)+,D0`, `CMP.B (A7),D0`, `Scc.B (A7)`, `AND.B`/`OR.B`/`ADD.B D0,(A7)`이다.
- 권고: F1c 결정(`3d58`/`3d6e`)과 같다. A7±2와 BYTE 하나만 쓰고 WORD push는 쓰지 않는다. 쓰기 주소가 RAM 밖이면 checked 오류다.
- [F] op `0c`(`e96da`)는 후보 LONG 배열을 A7 아래에 쌓는다. 그 개수를 `MOVE.W A1,D0`; `SUB.W A7,D0`; `LSR.W #2`(WORD 차)로 세고 `MOVEA.L (A7,D0.W),A0`로 고른 뒤 `MOVEA.L A1,A7`로 되돌린다. 원본대로 구현한다(WORD 뺄셈·부호확장 index 포함).
- [F] `e932c`는 LONG A0, WORD D0을 push/pop한다(live stack).

### 6. 객체·자식 생성과 실패 처리

- [F] op `08`(`e9558`)의 처리 순서는 다음과 같다.
  - callback 선택: A0=LONG `e8cc0+sext(WORD 8(op))`(범위 검사 없음).
  - 생성: D0=0, A1=`100bf4`, `JSR 2986`(U7. `28ae`로 event node의 자식 생성).
  - 실패(C=0)면 TRAP `e957a`이고, 성공이면 `e958e`로 간다.
  - 생성된 객체의 callback은 F3 밖이다. [F] 자연 재생에서 483회, WORD index 63종(최대 `398`=920, 표 끝 LONG), callback 63종(`d72f2` `b4d7e` 등 long tail)이었다.
- [F] op `09`(`e962a`)는 `JSR 28ae`(callback `e9350`) 뒤 **C를 검사하지 않는다**. 실패하면 A0=`100e98`(sentinel)이고 그 `2e..`, `76`, `7a`, `6b`에 쓴다.
  - 권고: F1b 결정 4처럼 원본대로 구현한다(오류로 바꾸지 않음).
  - 실패 조건: WORD `104ca0`(free 개수) ≤ 0(무부호, D0.W=0≥WORD).
- [F] op `08`의 `e9614..e9624` 복사 루프는 다음과 같다.
  - D0.W=BYTE `1(op)`−`0a`. 0이면 생략하고, 아니면 `MOVE.W (A2)+,(A1)+`, `SUBQ.W #2`, BNE를 반복한다.
  - D0이 음수 짝수면 WORD wrap까지 약 32K회를 돌며 객체 밖 RAM을 덮는다. 홀수면 0에 닿지 않아 RAM 밖 쓰기가 될 때까지 돈다.
  - 권고: 원본대로 두고, 쓰기가 RAM 밖으로 나가면 checked 오류와 rollback, 그 밖은 block budget에 맡긴다(F1a 결정 7(d)).

### 7. 무한 루프 가능 지점

- [F] 다음 지점은 원본대로 두고 기존 block budget만 한계로 둔다(F1a 결정 7(d)).
  - 자식 stream의 opcode `10..7f`: `e93c6 BSR e94fe`가 ≥`10`이면 바로 RTS하고 `e93ca`가 같은 포인터를 저장한 뒤 `e93a8`로 돌아가므로 무한 루프다. 주 stream에서는 같은 값이 frame 종료다.
  - `e9204` list walk: `100bf4` 다음 node부터 깊이 0 node까지 간다. 원형 list에 static node가 있으면 끝난다.
  - `e94fe`/`e951c` 연쇄: op `0a` 참이면 다음 op를 바로 실행하고, `0b`·`0c`는 재귀다.

### 8. ROM 자료 window와 bank

- 권고: F1a 결정 6처럼 physical `program_rom_000000.ms5d` window로만 읽는다.
- [F] 자연 재생 120 frame(142 seed)에서 F3 명령이 읽은 ROM은 모두 fixed `<100000`이었고 banked window 읽기는 0건이었다.
  - 주 stream(`e919a` 등): `48500..fbfff`. 실제 페이지는 `48500..48fff`, `da500..ddfff`, `f1000..fbfff`다.
  - 자식 stream·조건: `f6a00..fbeff`.
  - 평가기 입력(`e97ca`): `da700..fbfff`.
  - op `08` callback 표: `e8c00..e90ff`(표 `e8cc0..e905c`, LONG 231개).
- [F] PVC bank 쓰기: `e91cc..e91da`(주 종료), `e9404..e9412`(자식 frame 종료), `e9428..e9436`(자식 종료, 뒤 `JMP 2a00`). 모두 `0`→`100010`, `1000`→`2ffff2`, `0`→`2ffff0`이다(기존 `am_zero_bank`과 같은 세 쓰기).
  - `e9194`(stream null)는 bank를 되돌리지 않는다.

### 9. 실행부 파일과 오류 문자열

- 권고:
  - F3a: `engine/src/animation_machine_stage_event.cpp`(`animation_stage_event_block`). 오류 문자열은 `unsupported animation stage event PC`, `stage event caller requires known carry`.
  - F3b: `engine/src/animation_machine_stage_event_ops.cpp`(`animation_stage_event_ops_block`). 오류 문자열은 `unsupported animation stage event ops PC`, `stage event ops caller requires known carry`.
  - [F] `288c`(fixed ROM 호출자 약 100곳), `49a84`(약 30곳), `48502`(F3 밖 3곳)는 공유 helper지만 다른 실행부에 없으므로 F3 파일에 둔다.

### 10. 검증 seed와 산출물

- 권고: F2 결정 6의 관측 도구가 node 실행 단위 기준을 함께 만든다.
  - node 실행 규약: PC=`2ab8`, A6=node, A7=SPd(`10f000`), LONG `104ca4`=SPd, stop `2ac2`(card child test 선례). 입력은 Unicorn 패스에서 그 node의 `2abe` 직전 상태, 기대값은 다음 `2ac2` 상태다.
  - F3a 단계에서 `e94fe`에 닿는 101회는 `e94fe` stop 상태도 기록한다.
  - 64 KiB dump 저장 범위:
    - 전부: frame 0 `e9150` 134회, 자식 676회, F3a·F3b leader나 계산 PC index를 처음 덮는 실행.
    - 패스 가능 22 seed: 모든 frame(F2와 공유).
    - 나머지: SHA만.
  - [U] 산출물 크기와 압축 방식은 메인 결정이다.

## 원본 바이트 근거

[F] 아래 hex는 위 ROM에서 직접 추출했다. F3a 7 범위 1,124바이트(324명령), F3b 8 범위 952바이트(271명령, TRAP 포함, 문자열 제외)다.

**F3a**

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `1a910..1a91a` | `3b4054423b4154404e75` |
| `1a93e..1a952` | `4a006700000a3b7c0200544c4e75426d544c4e75` |
| `48502..4855c` | `303c00a0323c0180340036017e0041ed8cb8082d0000568e6700000e3e3cffff3028004232280046420741ed8da8082d0001568e6700000e1e3c00ff34280042362800464a076b000006340036014a476b000006300232034e75` |
| `e9150..e9350` | 512바이트, SHA256 `e450432e844e7fba45dc5f6fd33b774721b135722d44dcd157fbb2f9350c95bc`: `2d7c0010d38e003e426e007e422e0080422e00813b7c00a05e463b7c00805e482cbc000e91766100008c2d6d53bc002e2d6d53c000324eb900043e342e2e0076660000044e7520477e001e100c070010640000240c0700086500000e610003502e082d47007660e0e54f4ebb702808ae0000008167d22e082d4700763b7c0000801033fc1000002ffff233fc0000002ffff04e756000025e6000026e6000029e600002aa600002b2600002be600002d2600002f4700041ed5e3020c020c020c041ed5e3043ed8bf4600000121029006b0c40000c6400000652300000226900084a69001066e6610000f46100005c720070004eb900049392640000060001000170014eb900049392640000060001000210010c00000357ed5e3e56ed5e3d422d5e3f70004eb90004d7a64a0067000006522d5e3f70014eb90004d7a64a0067000006522d5e3f4e75422d5e40422d5e40422d5e41422d5e42422d5e44422d5e43422d5e454eb9000485027c004a476700006a382d53a23a2d53a69044924594449645382d53bc3a2d53c0904492459444964578007a00b06d5e465dc4b26d5e485dc548844885b46d5e465dc4b66d5e485dc54a4457ed5e416700000c524455ed5e4054ed5e424a4557ed5e446700000c524555ed5e4354ed5e454e752f083f0041ed5e307000d018d018d018d018d018d018d018d0181b405e3c301f205f4e75` |
| `e9444..e94fe` | `302d5418b06800026400031a1d7c00ff00814e75302d5418b06800026400000a1d7c00ff00814e75422e008070004eb90001a93e322800023001906800044eb90001a910600002de3228000230014eb90001a910600002ce70ff4eb90001a93e600002c23028000272ff4eb90001a910600002b243e800046100030a660002a6d0e800021d7c00ff00814e754a6e007e660000103d680002007e1d7c00ff00814e75536e007e6700027c1d7c00ff00814e75422e00806000026c` |
| `e9768..e9774` | `70001028000141f000004e75` |
| `e97c8..e98ee` | 294바이트, SHA256 `74a5ba5dfe2267c98737b7dbfd2a50b2ddfdf84ce0b2fd667241eca71eb08d8f`: `700010190c000080640000061f0060f0044000803200e5494efb100260000086600000826000007e6000007a60000076600000726000006e6000006a60000066600000626000005e6000005a60000062600000526000004e6000004a60000046600000426000003e6000003a6000003660000032600000466000004a6000004e60000052600000586000005e600000646000006a6000007060000076600000846000007845ed5e301f3200006000ff526100fab21f2d5e3c6000ff461f3c00ff6000ff3e1f3c00006000ff361f2e00806000ff2e101fb01757d76000ff24101fb0175ed76000ff1a101fb0175cd76000ff10101fb0175dd76000ff06101fb0175fd76000fefc101f56c0c1176000fef2101f56c081176000fee8101fd1176000fee0101f4e75` |

**F3b**

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `288c..289e` | `206e000cb0fc000066000008003c00014e75` |
| `1a92c..1a93e` | `3b4054443b4154463b4254483b43544a4e75` |
| `49a84..49a8e` | `3e0061d0c0c748404e75` |
| `e9350..e93da` | `426e007e422e0080422e00812cbc000e93624eb900043e344eb90000288c640000b8082800070061660000ae2e2e007a6700002020473018b06d54186300009a224861000434670000906100042c670000882e2e007620477e001e106a000010206e000c08e8000700626000006c0c0700086500000e610001362e082d47007660d65b076400001a4e4f` |
| `e93f0..e9444` | `e54f4ebb702808ae0000008167aa2e082d4700763b7c0000801033fc1000002ffff233fc0000002ffff04e756000009a600000ae600000d03b7c0000801033fc1000002ffff233fc0000002ffff04ef900002a00` |
| `e94fe..e957c` | `700010100c000010650000044e750c000008640000044e756100000460e2700010100c000010650000044e4f5100640000044e4fe5484efb00026000001e600000ec6000016260000176600001906000020c600001d2600001ec43faf766302800082f0820710000303c0000227c00100bf44eb900002986650000164e4f` |
| `e958e..e9768` | 474바이트, SHA256 `aaf05156d68fd1aabcdc8de1f0b4640c5aece0047c1179d0aece31771af0c61f`: `522e0080640000081d7c00ff008022577000102900020c00000c6400000e45ed5e30523200006000000470ff1140006b7000720030290004322900064840484118290003e20c6400000ad2ae004692ad53a6e20c6400000ad0ae004290ad53a21144006a1d44006a43ed538e41e8002e4eb900043e2243e80048205f2348004a7000102800010440000a6700000c45e8000a32da554066fa60000140522e0080640000081d7c00ff00802f08207c000e9350303c00004eb9000028ae43ee002e7000720041e8002e4eb900043e0841e8ffd2225f70001029000145f10000200a2140007645e90006200a2140007a302900040c40000c6400000e45ed5e30523200006000000470ff1140006b3029000241f100004e7543e80002610000be6100011a670000066000fe66600000ba3028000248700000610000a26100fe52b1d765f8670000044e4f205f4e753028000243f0000061000084b3c8670000382f09224f2f082f096100007e225fb1d165f2670000044e4f3009904fe4482f094eb900049a84225fe548207700002e496100fdfe205f4e7530280002322800047400760014280006162800074eb90001a92c600000283b6800025e463b6800045e482f086100fb46205f60000010522e0080640000081d7c00ff0080` |
| `e9774..e97c8` | `700010100c000010650000044e4f5100640000044e4fe5484efb00026000001e6000001c6000002a6000001a6000001c6000000a600000066000000260b6d0e800024e75d0e800024e75d0e800024e7561a260ac` |

- [F] 자료(코드 아님): `e93da..e93f0` 문자열 `HOJU TABLE CODE ERROR\0`, `e957c..e958e` 문자열 `SET MAKE FAIL!!\0\0`, `e8cc0..e905c` op `08` callback LONG 표.
- [F] 기존 routing 규칙·F1a·F1b·F1c와의 겹침은 없다. 인접 경계는 다음과 같다.
  - cleanup: `e90ca`/`e90d6`, `43e08` `43e22` `43e34`, `2a28`.
  - readiness: `289e`. fade_card: `28ae`, `2a00`. buffer_cue(U7): `2986`.
  - frame_helpers: `49392`. input(U6): `4d7a6`. F1c2: `49a58`.
  - F1a: `e905c..e90ca`.
- [F] fixed ROM 안 F3 진입 참조: `e9150`은 `e9064 LEA e9150(PC),A1`(F1a `e905c`→`2a28`)뿐이다. `e9176`·`e9362`는 `MOVE.L #imm,(A6)` 설치, `e9350`은 `e963a MOVEA.L #e9350,A0`(op `09`)다. `e932c`는 F3 밖 `e9144 BRA`에서도 쓰인다(`e910e..e9148` 루틴, 범위 밖). `48502`는 `4841e` `6fec8` `734a6`, `288c`·`49a84`는 다수 객체 코드가 부른다.

## 실행 의미

[F] A5 상대 d16은 live A5로 계산한다. 아래 절대 주소는 A5=`108000` 기준이다(`5e30`→`10de30`, `5418`→`10d418`, `53bc`/`53c0`→`10d3bc`/`10d3c0`, `53a2`/`53a6`→`10d3a2`/`10d3a6`, `-740c`→`100bf4`, `538e`→`10d38e`, `544c`→`10d44c`, `-7ff0`→`100010`).

1. **node 변수**(event node `100bf4`, 자식 thread 공통)
   - `+3e` LONG(=`10d38e`), `+2e`/`+32` LONG(camera 복사).
   - `+76` LONG stream 포인터(F1a `e905c`가 씀), `+7a` LONG 자식 조건 포인터.
   - `+7e` WORD 대기 counter(op `06`), `+80` BYTE 포화 counter(op `01` `07` 지움, `08` `09` `0d` 증가), `+81` BYTE frame 종료 flag(bit0을 `BCLR`로 검사).
   - `+6b` BYTE class(`0..b`, 아니면 `ff`), `+6a` BYTE, `+c` parent.
2. **event 전역**
   - `10de30..10de3b`: class별 자식 수 BYTE 12개.
   - `10de3c`: 합계.
   - `10de3d..10de45`: player·화면 flag.
   - `10de46`/`10de48` WORD: 화면 범위(초기 `a0`/`80`).
3. **`e9150`**: `+3e`=`10d38e`, CLR `+7e` `+80` `+81`, `10de46`=`a0`, `10de48`=`80`, callback=`e9176`, fall-through.
4. **`e9176`(매 frame)**
   - BSR `e9204`(`10de30..3b` 지움, `100bf4` 다음부터 깊이 0 전까지 자식의 `6b` class를 셈, `e932c` 합계, `e9298` 화면 flag, `49392`×2·`4d7a6`×2로 player flag).
   - `+2e`/`+32`=LONG `10d3bc`/`10d3c0`, `JSR 43e34`(cleanup).
   - D7=`+76`. 0이면 RTS(bank 복원 없음).
5. **주 루프 `e9198`**: D7=BYTE `(A0)`.
   - ≥`10`이면 `e91c6`: `+76`=A0, bank 복원, RTS. 포인터는 전진하지 않는다.
   - `08..0f`이면 `e91ac BSR e94fe`, `+76`=A0, 반복.
   - `00..07`이면 `JSR e91e4(PC,D7×4)`, `e91be BCLR #0,+81`. 이전 bit0=0(BEQ)이면 반복, 1이면 `e91c6`.
6. **opcode `00..07`**(길이는 BYTE `1(op)`, `e9768`이 A0+=길이)
   - `00`: WORD `10d418`≥WORD `2(op)`(BCC, 무부호)이면 전진, 아니면 `+81`=`ff`.
   - `01`: 같은 대기 뒤 CLR `+80`, `1a93e`(D0=0→CLR.W `10d44c`), `1a910`(D1=WORD `2`, D0=D1−WORD `4`→`10d442`/`10d440`), 전진.
   - `02`: `1a910`(D0=D1=WORD `2`).
   - `03`: `1a93e`(D0=ff→`10d44c`=`200`).
   - `04`: `1a910`(D0=WORD `2`, D1=`ffff`).
   - `05`: 평가기(A1=op+4)가 0이 아니면 전진. 0이면 A0+=sext(WORD `2(op)`), `+81`=`ff`.
   - `06`: `+7e`=0이면 `+7e`=WORD `2`, `+81`=`ff`. 아니면 감소해서 0이면 전진, 아니면 `+81`=`ff`.
   - `07`: CLR `+80`, 전진.
7. **평가기 `e97c8`**(A1 입력, BYTE stack)
   - <`80`: push 값.
   - `80..8b`·`8d..95`: push BYTE `10de30+(op−80)`.
   - `8c`: `e932c` 합계 갱신 후 push `10de3c`.
   - `96`/`97`/`98`: push `ff`/`0`/`+80`.
   - `99`~`9d`: a=pop, b=top, top=`Scc`(a−b)(EQ/GT/GE/LT/LE, 부호).
   - `9e`/`9f`: a=pop, top &=/|= (a≠0 ? `ff` : 0).
   - `a1`: top+=pop.
   - `a0`: D0=pop, RTS(결정 3).
8. **opcode `08..0f`(F3b)**: `e94fe`는 `08..0f`인 동안 `e951c`를 반복한다.
   - `08`: 객체 생성(결정 6). 생성 객체에 class·위치(WORD `4`/`6`<<16, flag BYTE `3` bit0/1이면 event node `+46`/`+42` LONG 더하고 `10d3a6`/`10d3a2` 뺌)를 쓰고, `43e22`, `+c0`=op 포인터, 나머지 WORD를 `+76..`에 복사한다.
   - `09`: 자식 thread 생성. `76`=op+길이, `7a`=op+6, `6b`=WORD `4` class, A0+=sext(WORD `2`).
   - `0a`: 조건이 참이면 다음 op를 즉시 실행(`e951c`), 거짓이면 건너뜀(`e9774`).
   - `0b`: 구간(A0+WORD `2`) 안 op를 모두 실행.
   - `0c`: 구간 안 op 중 하나를 `49a84`(RNG×개수>>16)로 골라 실행.
   - `0d`: `+80` 포화 증가.
   - `0e`: `1a92c`(`10d444..10d44a`).
   - `0f`: `10de46`/`10de48`=WORD `2`/`4`, `e9298`.
9. **자식 thread `e9350`/`e9362`**
   - 초기화 뒤 매 frame `43e34`, `288c`. parent가 `270e`이면 종료.
   - parent `61` bit7이면 종료.
   - `+7a`가 있으면 WORD 시한≤`10d418`이면 종료하고, 두 표현식 중 하나가 0이면 종료.
   - stream: 음수 opcode면 parent `62` bit7 설정 후 종료. `08..`이면 `e94fe`. `05..07`이면 표. 그 밖은 TRAP.
   - 종료 `e9428`: bank 복원, `JMP 2a00`(F2 결정 4의 `104ca4` 필요).
   - [F] `288c`는 parent=0이면 C=1(계속)로 돌아가며, 이때 `BTST #7,61(A0)`은 ROM BYTE `000061`을 읽는다.

## 구현 범위와 규약

**F3a (134 block 시작)**: `1a910` `1a93e` `1a944` `1a94c` `48502` `4851e` `4852a` `4853a` `48546` `4854c` `48550` `48556` `4855a` `e9150` `e9176` `e917a` `e918c` `e9194` `e9196` `e9198` `e91a4` `e91ac` `e91b0` `e91b8` `e91be` `e91c6` `e91e4` `e91e8` `e91ec` `e91f0` `e91f4` `e91f8` `e91fc` `e9200` `e9204` `e921c` `e9228` `e922c` `e9236` `e923a` `e923e` `e9248` `e924c` `e9250` `e9258` `e925c` `e9260` `e927a` `e9280` `e9284` `e928c` `e9292` `e9296` `e9298` `e92ba` `e92c2` `e930c` `e9316` `e9320` `e932a` `e932c` `e9444` `e9450` `e9458` `e9464` `e946c` `e9478` `e9488` `e948c` `e9498` `e949c` `e94a4` `e94a8` `e94b4` `e94b8` `e94c4` `e94d0` `e94d8` `e94e6` `e94ee` `e94f6` `e9768` `e97c8` `e97d4` `e97d8` `e97e4`..`e9868`(34 slot) `e986c` `e9878` `e987c` `e9884` `e988c` `e9894` `e989c` `e98a6` `e98b0` `e98ba` `e98c4` `e98ce` `e98d8` `e98e2` `e98ea`

- routing 7 범위(위 표). 짝수 PC 562개, 내부 PC 428개. 경계 `e94fe`.
- 묶인 PC 22개: `1a940` `4851a` `48536` `48548` `48552` `e9190` `e91a0` `e91a8` `e91c4` `e9224` `e9234` `e927c` `e928e` `e92be` `e9308` `e931c` `e944c` `e9460` `e94c0`(결정 3) `e94d4` `e94ea` `e97d0`.
- carry 소비 block 2개: `e9248` `e9258`(`49392` 반환 C). Unknown이면 checked 오류다.
- FLOW_ONLY 60개: `4855a` `e9176` `e9194` `e9196` `e91ac` `e91be` `e91e4`..`e9200`(8) `e9236` `e923a` `e9248` `e9258` `e9296` `e932a` `e9488` `e9498` `e94a4` `e94b4` `e94b8` `e97e4`..`e9868`(34) `e9878`.

**F3b (109 block 시작 + TRAP 8)**: `288c` `2898` `1a92c` `49a84` `49a88` `e9350` `e9362` `e9368` `e936e` `e9372` `e937c` `e9384` `e9390` `e939a` `e93a2` `e93a8` `e93b0` `e93be` `e93c6` `e93ca` `e93d2` `e93f0` `e93f6` `e93fe` `e941c` `e9420` `e9424` `e9428` `e94fe` `e950a` `e950c` `e9514` `e9516` `e951a` `e951c` `e952a` `e9532` `e9538` `e953c` `e9540` `e9544` `e9548` `e954c` `e9550` `e9554` `e9558` `e9576` `e958e` `e9596` `e959c` `e95ac` `e95b8` `e95ba` `e95d8` `e95e0` `e95e6` `e95ee` `e9604` `e961c` `e9620` `e9626` `e962a` `e9632` `e9638` `e964a` `e965c` `e9688` `e9694` `e9696` `e96a4` `e96ac` `e96b4` `e96b8` `e96bc` `e96c8` `e96cc` `e96d6` `e96da` `e96e6` `e96ec` `e96f0` `e96f8` `e9704` `e9712` `e9720` `e9722` `e9724` `e973e` `e9742` `e9754` `e975a` `e9762` `e9774` `e9782` `e978a` `e9790` `e9794` `e9798` `e979c` `e97a0` `e97a4` `e97a8` `e97ac` `e97b0` `e97b2` `e97b8` `e97be` `e97c4` `e97c6`

- routing 8 범위(위 표, 문자열 제외). 짝수 PC 476개, 내부 PC 359개.
- 묶인 PC 31개: `2894` `e9378` `e9380` `e938c` `e9396` `e939e` `e93ac` `e93c2` `e93d4` `e93fc` `e9506` `e9510` `e9524` `e952c` `e9592` `e95a8` `e95d4` `e95e2` `e9618` `e9624` `e962e` `e9684` `e96b0` `e96ce` `e96d0` `e96e8` `e96fc` `e96fe` `e975e` `e977c` `e9784`. 결정 3의 6개 중 5개를 포함한다.
- carry 소비 block 2개: `e936e`(`288c`/`289e`), `e9576`(`2986`). known carry 생산 block: `2898`(ORI, Set, block 안 RTS).
- FLOW_ONLY 48개: `e9362` `e9368` `e936e` `e9372` `e9390` `e939a` `e93b0` `e93c6` `e93f6` `e941c` `e9420` `e9424` `e950a` `e9514` `e9516` `e951a` `e9538`..`e9554`(8) `e9576` `e961c` `e9626` `e96a4` `e96ac` `e96b4` `e96b8` `e96c8` `e96d6` `e9720` `e9722` `e973e` `e9754` `e9790`..`e97b0`(9) `e97c4` `e97c6`.

**공통**
- callback 진입 4개는 `MOVE.L #imm,(A6)` 설치이거나 `2a28`/`28ae`로 설치되며 block 시작이다.
- 폭·연산:
  - MOVE.B/MOVE.W Dn은 나머지 bit를 보존한다. MOVEQ는 LONG 전체를 쓴다.
  - `LEA (A0,D0.W)`·`ADDA.W`·`(A1,D0.W)` index는 부호확장한다.
  - `Scc.B`는 `ff`/`00`을 쓴다. `SLT`/`SGT`/`SGE`/`SLE`는 부호, `SCS`/`SCC`는 무부호다.
  - `ADDQ.B #1` 포화는 BCC로 판단한다.
  - `LSR.B #1,D4`의 C를 같은 block에서 쓴다.
  - `SUBQ.B #5`/`#8`의 borrow를 같은 block에서 쓴다.
- 홀수 주소 WORD/LONG 접근은 기존 checked 오류다. BYTE stream 읽기는 홀수를 허용한다. [F] op 길이가 홀수면 이후 WORD 피연산자 읽기가 오류가 된다(원본은 주소 오류 예외).
- port 쓰기는 PVC bank 세 지점뿐이다. 객체·자식 생성은 기존 `28ae`/`2986`이 맡는다.
- 회귀 탐침 갱신: [F] `animation_machine_stage_entry_test.cpp` 391·535·714행이 `e905c` 주변 PC를 쓴다(`e9150` 이후로 진행하는 탐침은 없음). F3 구현 뒤 `e9150`으로 이어지는 무 stop 실행은 frame head(`e4a`)나 다른 미연결 callback에서 unsupported가 된다. 오류 지점이 옮겨 가므로 다시 확인해야 한다. F1b 결정 2의 "stop이 `2ac2`가 아니면 unsupported" 음성 test도 같은 이유로 확인한다.

## 자연 시작 상태(읽기 전용 재생)

[F] F2 계약과 같은 scratch 탐침이다(`f23/sched2.py`·`sched4.py`). 142 seed, 120 frame, 선언 SPd=`10f000`·`104ca4`, frame head·controller는 선언 skip했다. 게임 자연 실행이 아니라 선언 경계 모델의 Unicorn 결과다.

- [F] node 실행 12,168회의 구성:

| callback | 실행 | seed | F3a만 | F3b 접촉 |
| --- | --- | --- | --- | --- |
| `e9150` | 134 | 134 | 39 | 95 |
| `e9176` | 11,358 | 134 | 11,352 | 6 |
| `e9350` | 14 | 10 | 0 | 14 |
| `e9362` | 662 | 10 | 0 | 662 |

- [F] 계산 PC index 분포:
  - `e91ba` D7: `0` 7,622, `4` 880, `8` 20, `10` 14, `14` 400, `1c` 21. opcode `00 01 02 04 05 07`이 쓰였고 `03`·`06`은 미실행이다.
  - `e9534` D0: `0`(op `08`) 483, `4`(op `09`) 14. `0a..0f`는 미실행이다.
  - `e93f2`: `0`(op `05`) 180, `4`(op `06`) 514.
  - `e97e0` D1: `4` `8` `2c` `58` `5c` `60` `64` `68` `80`. 연산자 `81 82 8b 96 97 98 99 9a a0`이 쓰였다.
  - `e978c`: 0회.
  - TRAP 0회.
- [F] 도달 block: F3a 86/134, F3b 55/109.
  - F3a 미도달: `1a944` `4851e` `4853a` `e91f0` `e91fc` `e924c` `e925c` `e9280` `e9292` `e92c2` `e930c` `e9316` `e9320` `e949c` `e94a4`, 평가기 slot·연산자 31개(`e97e4` `e97f0`~`e9838`의 대부분, `e9850`~`e9868`, `e9878` `e987c` `e98b0` `e98ba` `e98c4` `e98ce` `e98d8` `e98e2`).
  - F3b 미도달: op `0a..0f` 전부(`e96a4..e9768`), skip `e9774..e97c6`, `2898` `1a92c` `49a84` `49a88` `e93b0` `e9424` `e9540..e9554` `e9596` `e9632`.
- [F] seed 결과:
  - 116 seed(`actual59-catalog-records`) + 16(`lookup8-null-and-nonnull-event`) + 2(`initial-physical-bank3`)는 120 frame을 완주했다.
  - 5(`wholebody-sound-wait`)는 `100b30`=`deadbeef`, 2는 BIOS `c00468`, 1(`live-RAM-record-reread`)은 `47c05` 예외다.
  - stream null(`e9194`) seed도 `e9176`을 매 frame 실행한다(RTS만).

## 검증 조건(최소)

**자연(node 실행, 결정 10)**
- F3a: `e9176` 11,352회와 `e9150` 39회를 입력 상태에서 실행해 `2ac2` 상태와 비교한다(dump가 있는 실행은 바이트, 나머지는 SHA). `e94fe`에 닿는 101회는 F3a 단계에서 `e94fe` stop을 비교한다.
- F3b: 위 101회의 끝까지, 자식 676회(`2a00` 종료 포함).
- 패스 가능 22 seed의 프레임 패스(F2) 안에서도 같은 node 구간이 일치해야 한다.

**host-write**
- opcode: `03`, `06`(설정·감소·0 도달), `00`/`01` 대기 양쪽, `05` 거짓 갈래(A0 이동, `+81`).
- 평가기:
  - 연산자 `80..a1` 전부, push 깊이 여러 단계, 부호 비교 경계(`7f`/`80`).
  - 표 밖 op `a2` `a5` `a6` `a8` `aa` `ac` `ae` `b3` `b8` `bd` 실행.
  - `a3` 등 내부와 `c4` 등 범위 밖은 unsupported.
  - 균형이 깨진 표현식(R이 4 복귀 PC가 아님).
- F3b op `0a..0f`:
  - `0a` 참/거짓, `0b` 구간 정확·초과(TRAP `e96d4`).
  - `0c` 빈 구간·후보 1/여러 개·초과(TRAP `e9702`).
  - `0d` 포화, `0e`, `0f`.
- 생성:
  - `2986` 실패 TRAP `e957a`, `28ae` 실패(op `09`, `100e98` 쓰기).
  - op `08` 홀수 길이 복사 rollback, flag bit0/1 위치 보정.
- 자식 thread:
  - parent `270e`/0/`61` bit7.
  - 시한 경과, 표현식 0.
  - 음수 opcode(parent `62` bit7), opcode <5 TRAP `e93d8`, `10..7f` 무한 루프(budget 오류).
- TRAP 8개 stop/rollback, 묶인 PC 53개·내부 PC 787개 직접 진입 거부.
- Unknown carry로 소비 block 4개에 진입하면 오류.
- bank: 진입 bank 3에서 종료 복원, `e9194`는 미복원.
- 홀수 stream·RAM 밖 쓰기 rollback, zero-step.

**비교 항목**: 기존과 같다(64 KiB RAM, 16R/PC/A7, carry 분류, PVC·bank, 순서 있는 port, external reads, status, 입력·산출물 SHA, ROM stat 불변).

## 미확인·범위 밖

1. opcode·평가기 연산자의 게임 의미(대기 기준 `10d418`=scroll 진행, class 수=동시 객체 제한, `10de3d..45`=player·화면 판정)는 [I]다.
2. op `08`이 만드는 객체 callback(`e8cc0` 표 231개)은 F4 이후 long tail이다.
3. 표 밖 평가기 op(`a2..ff`)와 자식 opcode `10..7f`가 실제 자료에 있는지. 전체 event stream 정적 조사는 하지 않았다.
4. 선언 프레임 경계(F2 결정 3)가 생략하는 `e74`·`c66a` 효과가 event 진행(`10d418` 등)에 주는 영향.
5. `e910e..e9148`(`6b` class 재배정, `e932c` 공유)의 호출자와 범위 소속.
6. 관측 산출물의 크기·압축 방식(결정 10).

작업자 scratch: 세션 scratchpad `f23/`(`clos3.py`, `blk3.py`, `fin3.py`, `split.json`, `f3lead.json`, `sched2.py`, `sched4.py`, `s2.pkl`, `s4.pkl`; 저장소 밖).
