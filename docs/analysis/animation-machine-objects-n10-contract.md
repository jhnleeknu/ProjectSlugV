# 객체 callback F4 N10: 정지 객체 callback `c5896`과 설치 callback `c58ee` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N10 행(`c5896..c593e`, callback `c5896` `c58ee`, 새 seed RNG 18 19 96 97 102 103, 경계·TRAP·표 없음, 옛 R10 18)과 메인 결정 1·2다. 규약은 N09 계약(`animation-machine-objects-n09-contract.md`, 같은 작업)과 N07 계약(SHA256 `cbbb8fbf769a9cad4b656ff71600a9ffdb85242a76c5c78c253a0fafe23a21d0`)을 따른다. ROM·routing 기준과 표기([F]/[I]/[U])는 N09 계약 머리말과 같다(작업 트리 `metalslug-n09` HEAD `de7108c`, `animation_machine.cpp` SHA256 `a050463fca2b4eb8c6136b1349f468fba6d9b27845563fceab916fab7820b875`).

## 요약

- [F] **N10 = 18 block**, 코드 1 범위 `c5896..c593e` 168바이트(SHA256 `51042c7830e640ac6cfa7e3e7e26997a5d49ae0923bdc5c9f6b502b74f63e30b`), 37명령이다. 짝수 PC 84개 중 내부 66개. 미도달 명령 0. 재범위 N10 행 18과 같다. TRAP·계산 PC·묶인 Bcc·X/DIV·I/O port 쓰기·bank 변경 없음.
- [F] 진입: 노드 callback `c5896`(stage event 표 LONG `e9010`; 앞 `d6d8c`, 뒤 `c593e`), 설치 callback `c58ee`(`c58e8 MOVE.L #c58ee,(A6)`, fall-through).
- [F] 범위 밖 이웃: `c584c..c5896`은 자료(`c584c` 사각형 `ffc0 ffe0 0080 0040`, `c5854` LONG 표 11개, `c5880` WORD 표 11개)다. `c593e..`는 stage event 표의 다음 callback(다른 단위)이다.
- [F] **표 읽기**(live bus, fixed ROM): `c5896` block은 `D0.W = 76 WORD; D0.W += D0.W` 두 번(WORD wrap) 뒤 LONG `(c5854 + sext(D0.W))`를 `7c(A6)`에 쓰고, 다시 `D0.W = 76; D0.W += D0.W` 뒤 WORD `(c5880 + sext(D0.W))`를 `D0.W`로 읽는다. 원본은 `76` 범위를 검사하지 않는다. [F] 표 길이는 11개라 원 의도는 `76` 0~10으로 보이나([I]), 구현은 원본대로 어떤 `76`이든 같은 주소를 live bus로 읽는다(홀수 주소는 생기지 않음; 읽을 수 없는 주소는 기존 checked 오류).
- [F] **나가는 호출(routing됨)**: `8ebe`(U02, `D0.W` = 표 WORD, `D1.B = 0`), `4c0ac`(U12), `4be2c`(U18), `43e34`(cleanup), `16ea4`(sprite, `D7 = 7c`, `D0 = 0`), `1ab02`(U05, A0 = `c584c`, C 반환), `2a00`(JMP).
- [F] **carry**: 소비 block 1개 `c5932`(`BCC.W c593c`, `1ab02` 반환). known 생산 없음. FLOW_ONLY 12개 `c58d4 c58e2 c58f8 c5902 c5908 c590c c5912 c5916 c5928 c5932 c5936 c593c`. 나머지 6개(`c5896 c58c0 c58da c58e8 c58ee c591c`)는 Unknown. N/Z 재계산 없음.
- [F] 자연 도달(재범위 `N1R`): RNG 400 frame에서 seed 18 19 96 97 102 103이 frame 0에 `c5896`(노드 2개), frame 1부터 `c58ee`를 실행한다. 18 시작 중 11개가 TB 시작으로 나타난다(`c58d4 c58f8 c5902 c5908 c590c c5912 c5936` 미도달). base 120 frame에서는 실행되지 않는다.
- [F] 기준(N09 계약과 같은 측정): 6 seed는 RNG frame 0 `c5896`이 첫 미연결 PC다. [I] N10 뒤 frame 1 N09 `af6de`/`af6ec`, 이어 N08 `4945e`/`4983e`/`4ae4a`에서 멈춘다(검증에서 측정).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n10.cpp`의 `animation_objects_n10_block`. 오류 `unsupported animation objects n10 PC`, `objects n10 caller requires known carry`(`c5932`).
2. **표 색인 무검사.** 원본대로 `76` 범위를 검사하지 않고 live bus로 읽는다(test는 합성 physical 바이트를 `c5854`/`c5880`/`c584c`에 둔다; ROM 자료를 test에 넣지 않음).

## block 목록과 실행 의미

[F] 18 block. 표기는 N09 계약과 같다.
**callback `c5896`·`c58ee`(설치) 18**
- `c5896`: `LEA.L c5854(pc),a0; MOVE.W 76(a6),d0; ADD.W d0,d0; ADD.W d0,d0; MOVE.L (a0,d0.w),7c(a6); LEA.L c5880(pc),a0; MOVE.W 76(a6),d0; ADD.W d0,d0; MOVE.W (a0,d0.w),d0; MOVE.B #0,d1; JSR 8ebe.l`
- `c58c0`: `MOVE.W #0,68(a6); MOVE.W #0,1e(a6); TST.W 78(a6); BEQ.W c58da` (→`c58d4`)
- `c58d4`: `BSET.B #0,15(a6)` (→`c58da`) — FLOW
- `c58da`: `TST.W 7a(a6); BNE.W c58e8` (→`c58e2`)
- `c58e2`: `JSR 4c0ac.l` — FLOW
- `c58e8`: `MOVE.L #c58ee,(a6)` (→`c58ee`)
- `c58ee`: `CMPI.W #2,7a(a6); BNE.W c5916` (→`c58f8`)
- `c58f8`: `BTST.B #7,15(a6); BNE.W c590c` (→`c5902`) — FLOW
- `c5902`: `JSR 4be2c.l` — FLOW
- `c5908`: `BRA.W c5912` — FLOW
- `c590c`: `JSR 43e34.l` — FLOW
- `c5912`: `BRA.W c591c` — FLOW
- `c5916`: `JSR 43e34.l` — FLOW
- `c591c`: `MOVE.L 7c(a6),d7; MOVEQ #0,d0; JSR 16ea4.l`
- `c5928`: `LEA.L c584c(pc),a0; JSR 1ab02.l` — FLOW
- `c5932`: `BCC.W c593c` (→`c5936`) — C 소비
- `c5936`: `JMP 2a00.l` — FLOW
- `c593c`: `RTS` — FLOW

### 의미

- `c5896`: 위 "표 읽기"; `D1.B = 0; JSR 8ebe`(복귀 `c58c0`). A0 = `c5880`(끝 값).
- `c58c0`: `68 = 0; 1e = 0`(WORD); `78 WORD`가 0이면 `c58da`, 아니면 `c58d4`(`BSET.B #0,15(A6)`).
- `c58da`: `7a WORD ≠ 0`이면 `c58e8`, 아니면 `c58e2`(`JSR 4c0ac`). `c58e8`: `(A6) = c58ee` (→ `c58ee`).
- `c58ee`(설치): `7a WORD ≠ 2`이면 `c5916`(`JSR 43e34`), 아니면 `c58f8`: `15 bit 7`이 1이면 `c590c`(`JSR 43e34`), 0이면 `c5902`(`JSR 4be2c`); 둘 다 `BRA c591c`.
- `c591c`: `D7 = 7c LONG; D0 = 0; JSR 16ea4`. `c5928`: `A0 = c584c; JSR 1ab02`. `c5932`: C clear면 `c593c RTS`, set이면 `c5936 JMP 2a00`.

## 구현 범위와 규약

- routing 1 범위. 시작 18, 내부 66(직접 진입은 `unsupported animation objects n10 PC`). FLOW_ONLY 12, 소비자 1, 생산자 0, Unknown 6. 스택은 JSR 복귀 LONG만.

## 검증 조건(최소)

- N09와 같다(단위 test 18 시작 × 3 carry, 내부 66, zero-step, RAM `10fe00..10fefe` rollback 탐침, `c584c`/`c5880`/`c5854` 자료 PC는 `unsupported animation machine PC`, 소비자 Unknown 오류, 실제 `1ab02` 생산자 뒤 native 분기, 실제 ROM 차분, 프레임 패스·RNG 400 차분).

## 작업자 검증 기록 (scratch, 계약 초안 구현)

- [F] 구현: `engine/src/animation_machine_objects_n10.cpp`(`animation_objects_n10_block`), routing `else if` 1개, FLOW_ONLY 12개 case 묶음, 선언 1줄, Makefile·verify SOURCES(N09와 같은 변경). 단위 test `engine/tests/animation_machine_objects_n10_test.cpp`: 65 fixture(checked 오류 5, known C 유지 22), 18 block × 3 carry, 내부 66 PC, zero-step, 홀수 PC, RAM rollback 탐침, 범위 밖 자료 `c584c` `c5854` `c5880` `c5894`. 합성 표 바이트로 `76` = 0 1 5 a 2000 c000 9000(WORD wrap·부호확장 색인)을 native와 비교. UBSan 통과. `make -j4 all test` 종료 0.
- [F] 실제 ROM 차분과 프레임 패스 차분은 N09 계약 기록과 같은 실행이다. RNG 400에서 seed 18 19 96 97 102 103은 frame 0 `c5896`을 지나 frame 0을 완주하고 frame 1의 N09 `af6de` 안 N08 경계 `4983e`에서 멈춘다. base 120은 변화 없음(N10 미실행).

## 미확인·범위 밖

1. [I] `c5896`은 `76`(종류 0~10)으로 소리(`8ebe`)와 sprite 값(`7c`, `16ea4`의 D7)을 고르는 정지 장식 객체로 보인다. `78`은 좌우(`15 bit 0`), `7a` 0이면 U12 `4c0ac`, 2이면 화면 판정(`15 bit 7`)에 따라 `4be2c`/`43e34`를 고른다. 게임 의미는 미확인이다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n09/`(N09와 공유).
