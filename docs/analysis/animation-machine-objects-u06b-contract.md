# 객체 callback F4 U06b: U06 경계 callee `e7562`와 공용 leaf `48250` 계약(구현·검증 기록)

[F]=원본 바이트 또는 이 작업의 Unicorn/C++ 실행에서 확인한 사실, [I]=추론, [U]=미확인.

- ROM: canonical BE program(`extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB). 관련 코드는 모두 `<100000`이므로 file offset = CPU 주소이고 bank와 무관하다.
- 근거 문서: `animation-machine-demo-seed108-frame22.md`(SHA256 `1017122a0f6502a158fc02cf7576ebfa473af74249d5e007f7fa44819e57b62c`, 원인 분석과 단위 제안; 메인이 제안을 수용), U06 계약 `animation-machine-objects-u06-contract.md`(SHA256 `6d628d0fa1e907e75f06d2906433fb5afbf2d215320be6beee8ebeb6bebd7e63`, `e7562`를 "경계 callee(실행부 없음)"로 둠).
- 기준 트리: `claude/b-followups` `d991ea3`(작업 트리 변경, 미커밋). 조사자의 scratch patch(`demo108/u06b.patch`)를 검토해 실행부·routing·carry 목록을 그대로 채택했고(아래 "검토") 시험·생성기·문서를 더했다.

## 요약

- [F] **block 시작 3개**: `e7562`, `e756c`(JSR 복귀점), `48250`. 범위 2개: `e7562..e7570`(14바이트), `48250..48256`(6바이트). 짝수 PC 10개 중 block 시작 3, 내부 PC 7개(`e7564 e7566 e7568 e756a e756e`, `48252 48254`).
- [F] 표·간접 분기·bank 변경·port 쓰기·TRAP 없음. 경계 callee 없음(`48250`이 닫힘 안에 있다). C 소비자 0, known C 생산 0.
- [F] 쓰기: work RAM BYTE `5681(A5)`(`A5 = 108000`이면 `10d681`)와 스택 LONG 2개(`e7562`의 `MOVE.L A0,-(A7)`와 `JSR`의 복귀 LONG). 읽기: 스택 LONG 2개(`e756c`의 pop과 RTS). ROM 데이터 읽기 없음.
- 실행부 `engine/src/animation_machine_objects_u06b.cpp`(`animation_objects_u06b_block`), 내부 PC 오류 `unsupported animation objects u06b PC`.
- routing(`engine/src/animation_machine.cpp`): `(next.pc>=0xe7562 && next.pc<0xe7570) || (next.pc>=0x48250 && next.pc<0x48256)`를 U06 줄 바로 뒤에 둔다.

## 원본 바이트

| 범위 | 바이트 | SHA256 |
| --- | --- | --- |
| `e7562..e7570` | `2f08 7001 4eb9 0004 8250 205f 4e75` | `dde6af8e405d225c4247e4e1bb9a53a8186875bb320e211e04da9602c34443c0` |
| `48250..48256` | `1b40 5681 4e75` | `4059f5ad05a638d48bf5c7c73732b66068f04b1ebfa55e29b4287548408b76ec` |

- `e7562`: `MOVE.L A0,-(A7); MOVEQ #1,D0; JSR 48250.L`(복귀 `e756c`). D0 전체가 1이 된다(MOVEQ는 LONG).
- `e756c`: `MOVEA.L (A7)+,A0; RTS`.
- `48250`: `MOVE.B D0,5681(A5); RTS`. 변위 WORD `5681`은 양수(`> 0`)이므로 주소는 `A5 + 5681`(`am_index`의 WORD 부호 확장, 24비트 절단).
- 스택 모양(진입 A7 = SP): `e7562` 뒤 `[SP-4] = A0`, `[SP-8] = e756c`, A7 = SP-8; `48250`의 RTS 뒤 A7 = SP-4; `e756c`의 pop 뒤 A7 = SP; RTS 뒤 A7 = SP+4.

## 진입(호출자)

- [F] `e7562`: U06 `e7462`/`e7478`/`e7486`의 `BSR.W e7562`(복귀 `e7466`/`e747c`/`e748a`)와 script 끝 항목 `e774e`(지속 `ffff`, 처리기 `e7752 + sext(fe10) = e7562`)를 `e74ac JSR (A0,D0.W)`가 부르는 경우다.
- [F] `48250`: 절대 `JSR 48250.L` 6곳: `965a`, `308c0`, `d64b2`, `d6b3c`, `d6c98`, `e7566`. `e7566` 외 5곳은 아직 routing 밖(호출자 단위가 생길 때 이 실행부를 재사용한다).
- [F] 소유: U06 계약이 `e7562`를 경계로 뺐고 C2 계약은 `48250`을 범위 밖(`4823a..48250` 배타 끝)으로 두었다. F4 범위 문서·재범위 문서·B 계약 어디에도 담당이 없었다(seed 108 문서 §소유 판정).

## carry

- [F] 68000 CCR 규칙: `MOVEA`(주소 레지스터 대상)는 CCR를 바꾸지 않는다. `RTS` `JSR`는 CCR를 바꾸지 않는다. `MOVE.L An,-(A7)` `MOVEQ` `MOVE.B`는 N·Z를 정하고 V·C를 지운다.
- 분류(관례 U01~U16: `MOVE`/`MOVEQ`는 소비자가 있을 때만 known 생산):
  - `e756c`는 **FLOW_ONLY**(C 보존)다. `carry_preserving_pc`에 `case 0xe756c:`를 더한다(U06 `e74d6`·`e755e`와 같은 형태).
  - `e7562`(MOVE.L+MOVEQ)와 `48250`(MOVE.B)은 원본에서 C를 지우지만 **known C로 생산하지 않고 Unknown**으로 둔다. 소비자가 없다: `e7466`(`TST.B`)과 `e74b0`(`MOVE.L`)이 곧 flag를 다시 정하고, `48250`의 다른 호출자 5곳은 아직 미연결이다 [F: 호출자 뒤 명령 분석은 seed 108 문서 §정적 디코드, 나머지 5곳은 [U]].
  - 따라서 chain `e7562 → 48250 → e756c`는 입력 C와 무관하게 Unknown으로 끝난다. `e756c`만 단독 진입하면 입력 C(Unknown/Clear/Set)를 그대로 돌려준다.
- 오류 문구 `... caller requires known carry`는 U06b에서 나오지 않는다(소비자 없음).

## 구현 규약

- `e7562`: `am_push(4, A0)`; `D0 = 1`; `am_call(48250, e756c)`. `e756c`: `am_pop(4) → A0`; `am_return`. `48250`: `am_write(A5 + 5681, 1, D0 & ff)`; `am_return`.
- 오류는 모두 기존 공용 checked 오류이고 실행 전체가 원자적으로 되돌려진다(RAM·레지스터·A7·C). 관찰한 문구(C++ 실행 기록, 시험 `errors()`):
  - 홀수 A7(`e7562`의 push, `e756c`의 pop, `48250`의 RTS): `program bus requires even WORD/LONG address`
  - A7이 work RAM 경계 밖이라 push가 RAM mirror 단위를 벗어남(`e7562`, 첫 push 뒤 JSR push 실패 포함): `program bus write requires RAM mirror units`
  - pop 대상이 ROM(물리 resource 없음): `missing program bus ROM unit`
  - `A5 + 5681`이 work RAM(`100000..1fffff`)도 PVC 쪽도 아닌 주소(예: A5 = 0, `300000`): `unsupported animation machine write device`
  - 내부 PC 직접 진입·RTS 도착: `unsupported animation objects u06b PC`; 홀수 도착: `unaligned animation machine PC`; routing 밖: `unsupported animation machine PC`.
- [I] `A5 + 5681`이 PVC 쪽(`2fe000..2fffff`)이면 공용 `am_write` 의미대로 BYTE port 쓰기로 기록된다. 이 단위 시험의 native 관측기는 그 주소의 BYTE 쓰기를 지원하지 않아(`pvc-page` 무효) 비교 대상이 아니다. 실제 프로그램의 A5는 `108000`이다.
- 원본과의 의도된 차이: 홀수 A7의 68000 address error를 Unicorn이 재현하지 않는다. C++는 checked 오류로 멈춘다(native 비교 대상 아님; 시험 `errors()`의 정확한 문구로 확인).

## 검토(조사자 patch)

- [F] 실행부 3 case는 spec과 원본에 맞다: push는 MOVEQ 앞(MOVEQ가 A0를 바꾸지 않으므로 순서는 결과에 영향 없음, 스택 모양은 native와 RAM digest가 일치), `am_call`이 복귀 `e756c`를 JSR 뒤 PC로 쌓는다, `48250`은 BYTE만 쓴다(`d[0]&255`).
- [F] `carry_preserving_pc`는 `e756c`만 추가(주석에 `e7562`/`48250`은 Unknown임을 적음). routing 줄은 U06 줄 뒤. 변경 없이 채택했다. `tools/verify_animation_machine.py` SOURCES에 `animation_machine_objects_u06b.cpp`를 U06 뒤에 더했다.

## 바뀐 기존 시험·주석

| 파일 | 변경 |
| --- | --- |
| `engine/tests/animation_machine_objects_u06_test.cpp` | `boundaries()`의 `e742c-clear-key1` `e7462` `script-end` 행이 더 이상 `e7562`에서 rollback하지 않는다. 세 행(stop = `e7562`)은 stop-PC 행으로 그대로 두고, 같은 입력을 return LONG `ff000`까지 실행하는 native 행 `e742c-clear-key1-to-stop` `e7462-to-stop` `script-end-to-stop`을 더해 성공(`10d681 = 1`, C Unknown)을 확인한다(`e7462-to-stop`만 입력에 `10e07a:0005`를 더해 callback이 ROM을 읽지 않고 카운트다운으로 끝나게 했다). 헤더 주석(21행 부근)과 `interior()` 주석(496행 부근)의 "경계 e7562" 서술을 고쳤다. rollback 행은 하나도 삭제하지 않았다. |
| `engine/src/animation_machine_objects_u06.cpp` | 74~76행 주석 "e7562 no executor"를 U06b로 고쳤고 `e7462` `e7478` `e7486` 줄 주석을 "U06b callee"로 바꿨다(코드 변경 없음). |
| `engine/src/animation_machine.cpp` | routing 1 줄, `carry_preserving_pc`에 `case 0xe756c:`(주석 포함). |
| `engine/src/animation_machine_internal.h` | `animation_objects_u06b_block` 선언. |
| `Makefile` | `ANIMATION_MACHINE_SOURCES`에 `animation_machine_objects_u06b.cpp`(한 줄 유지), 시험 target과 실행 줄. |
| `tools/verify_animation_machine.py` | SOURCES 목록. |
| 새 파일 | `engine/tests/animation_machine_objects_u06b_test.cpp`, `tools/generate_animation_machine_objects_u06b_test_table.py`(Unicorn 생성기; 시험의 generated section과 U06 행 3개를 만든다). |

## 시험 구성(`animation_machine_objects_u06b_test.cpp`)

- native 행 91개(생성기, 원본 코드를 Unicorn M68000으로 실행; ROM 데이터 읽기·port 쓰기·홀수 접근이 있으면 생성 중단): `e7562` 전체 chain 8 시나리오(D0·A0·기존 BYTE·A5(`108000`/`10a000`/`10ffff` mirror/`108001` 홀수)·A7 변형) × 입력 C 3종, 중간 stop(`48250`, `e756c`), `48250` 단독 D0.B `00 01 7f 80 ff`(상위 비트 오염) × 3종과 A5 변형, `e756c` 단독(pop 값 `0` `ffffffff` `10e400` 홀수 × 3종), U06 BSR 호출점 `e7462`/`e7478`/`e7486` → 복귀 PC(`e7466`/`e747c`/`e748a`) × 2 입력 × 3종. 각 행은 16 레지스터, RAM digest, PC, bank, PVC `ff8/ff9`, C 분류를 비교한다.
- block 표 3행 × 입력 C 3종(한 block 후 후계 `48250` / `ff004` / `ff000`과 digest, carry 분류), zero-step 3 × 3, 분할 실행(`48250` stop → `e756c` stop → 마지막 RTS)이 연속 실행과 같음(3 시나리오 × 3종).
- 내부 PC 7개 × 3종: 정확한 문구와 실패 PC(시작 PC 자신), 홀수 PC 7개 × 3종, work RAM 탐침 `10fe00..10fefe` 5개, 범위 이웃 6개(`e7560` `e7570` `e7572` `4824e` `48256` `48258`)가 U06b 문구로 끝나지 않음.
- 실패 PC 확인(review 0264 L-1): 모든 기대 오류가 `reject_at()`을 거친다. 같은 입력에서 stop PC를 실패 PC로 두면 성공하고 정확히 그 PC에서 끝나며, 내부 PC는 단위 문구·그 밖은 routing 문구와 일치한다. 홀수 도착 PC는 stop PC가 될 수 없어 문구만 확인한다(별도 집계).
- RTS 도착 rollback: 내부 PC 7개로 돌아가는 chain(`e7562` 시작과 `48250` 시작), work RAM 탐침 `10fe00` `10fe04` `10fe40` `10fe9e`로 돌아가는 chain(`e7562` 시작과 `e756c` 시작; `10d681` 쓰기와 push까지 되돌려짐), 홀수 도착 4개.
- 스택·쓰기 오류 9종 × 3 C(위 문구), `e7562`는 후계 `48250`으로의 실행도 같은 문구로 실패함을 확인.
- 기존 시험의 PC 사용 규칙: 다른 단위의 ROM PC를 rollback 탐침으로 쓰지 않고 work RAM `10fexx`만 쓴다.

## 검증 기록

(아래 표의 결과는 이 작업에서 실제 실행한 값이다.)

| 항목 | 명령 | 결과 |
| --- | --- | --- |
| 전체 빌드·시험 | `make -j3 all test`(로그 `ms5-scratch/u06b/make_all2.log`) | 종료 0, 경고 0, Assert 없음, 시험 실행 267, Python 310 OK. `u06b: 91 fixtures (8 kept C), 3 blocks, 92 located errors (25 odd landings), 27 stack/write errors, 414 calls`, `u06: 154 fixtures ...` |
| UBSan | `clang++ -O1 -g -fsanitize=undefined -fno-sanitize-recover=undefined` 전 SOURCES + u06b/u06 시험 | 둘 다 통과 |
| mutation | 19개 mutant(push 생략, MOVEQ 0, MOVEQ 상위 보존, JSR 복귀 PC, pop WORD, pop 대상 A1, 쓰기 변위 `5680`, 쓰기 마스크 `7f`, 쓰기 기준 A6, 쓰기 값 D1, 오류 문구, 쓰기 WORD, carry 목록에서 `e756c` 제거, `e7562` 추가, `48250` 추가, routing 끝 `e756e` `48254` `e7572` `48258`) | 19/19 시험 실패(처음 17/19; routing 끝 확장 2개는 이웃 PC 탐침을 보강해 잡음) |
| 실제 ROM 차분 | Unicorn(원본 코드) vs C++(`run_animation_machine`, 추출 `program_rom` 8 resource), 시작 `e7562` `e756c` `48250` 직접 + 호출점 `e7462` `e7478` `e7486`, 임의 레지스터·RAM·스택(5 seed × 1,500 = 7,500 case) | 불일치 0. 시작 3개 모두 도달. 내부 PC 도착(native는 계속 실행하지만 C++ checked 오류) 5 seed 합계 737건은 오류 문구 일치로 확인. native가 깨끗이 끝나지 않는 case(홀수 A7·ROM 쓰기·RTS 홀수 stop 등)는 건너뜀 |
| 프레임 D1(`MS5_SEED_DIR=artifacts/stage_entry_body`, 출력 `build/u06b_frames/`) | `verify_animation_machine_frame_driver.py --workers 2 --out build/u06b_frames/d1` | 종료 0. 54,406 frame, 54,400 complete 일치, 불일치 0, natural 136 seed가 400 frame 완주(+1 native 정지), deterministic·negative_ok true |
| controller `--declare game` | `... frame_controller.py --workers 2 --declare game --out build/u06b_frames/ctrl_game` | 종료 0. 54,406 frame, 54,400 일치, 불일치 0, controller segment 54,264 ok, fixtures_ok·negative_ok true |
| IRQ | `... frame_irq.py --workers 2 --out build/u06b_frames/irq` | 종료 0. natural 54,400/54,400 일치(기준과 같음), 불일치 0, deterministic true |
| controller 무선언 | `... frame_controller.py --workers 2 --out build/u06b_frames/ctrl_none` | 종료 0. 54,406 frame, 54,400 일치(기준과 같음), 불일치 0 |
| controller demo 전체 | `... frame_controller.py --workers 2 --declare demo --out build/u06b_frames/ctrl_demo` | 종료 0. 137 seed 전체, complete **45,684/45,684 일치, 불일치 0**(기준 45,680/45,684; seed 108·109의 frame 22·60 오류 4건이 해소). `complete-mismatch` 0 |

## 미확인

1. [U] `5681(A5)` := 1의 게임 의미(구역 선택 BYTE `SelectStageArea`로 보임). `48250`의 나머지 호출자 5곳(`965a` `308c0` `d64b2` `d6b3c` `d6c98`)의 단위 소속.
2. [U] 자연 상태(선언 없이 boot부터)에서 `e7426`이 입력 bit `30`을 보는 경로. seed 108·109의 도달은 선언 `demo` 입력 때문이다.
3. [U] `e74f8` script 처리기와 그 자식(`2b7be` `e7996`)의 담당 단위(U06b 범위 밖).
