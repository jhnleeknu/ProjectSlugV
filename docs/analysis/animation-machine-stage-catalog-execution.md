# Stage controller F1c1(catalog 선택·음악 비교·진입 효과표·dispatcher callback)의 실제 C++ 실행 검증

Baseline `3360752`(U1–U7 + F1a + F1b + F1c1, detached). [F1c 계약](animation-machine-stage-catalog-f1c-contract.md)의 F1c1 절(7개 code range 564바이트, 67개 block 시작, TRAP 경계 `478a6`, F1c2 진입 `479b0`에서 자름)을 공개 animation-machine API(`engine/src/animation_machine_stage_catalog.cpp`, SHA256 `a431f6b99d0d84bf00189f96ea2f0c781c55d61fadad03a5a2a0cd1beb94a56c`)에 연결한 구현을 native 관측과 대조했다. 입력은 통제된 fixture이며 자연 scheduler·자연 IRQ·BIOS 실행·실제 플레이 도달을 뜻하지 않는다. [F] 확정, [I] 추론, [U] 미확인으로 구분한다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다(fixed CPU 주소 = ROM 파일 offset, bank 영역은 modeled bank로 구분). 원본 ROM은 실행 전후 해시·mtime이 같다.

## 입력 고정

- [F] 계약 `docs/analysis/animation-machine-stage-catalog-f1c-contract.md` SHA256 `f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575`. 검증기가 7개 code range의 원본 바이트를 ROM과 대조하고(564바이트, 이어 붙인 SHA256 `40c8dfbe…25ef`), 67개 시작·묶인 분기 9개·FLOW_ONLY 32개·소비자 4개를 계약 문장에서 읽어 독립 디코드(capstone, 명령 141개)로 다시 유도한 값과 비교했다. 어긋남 0.
- [F] Native 관측 `artifacts/animation_machine_stage_catalog_native/observation.json` SHA256 `15f7411230a5885e2737403e7584c6e263e2dce60ee3cc94f04ef3a1d3edd3fd`, observer `tools/observe_animation_machine_stage_catalog.py` SHA256 `22b038c1300bfb99ff0b81f19d87f3d0c1572040185a61c367c6e7209d0a23c6`. 검증기는 observer를 import하거나 실행하지 않고 동결된 관측만 읽는다. 기록된 입력 253개(도구 SHA, seed RAM 파일, 이전 관측)의 해시를 다시 확인했고, 조건 파일 663개와 content-addressed blob 6,255개(파일명 = 내용 SHA256)를 모두 해시 검증했다.

## 실제 대조 범위

[F] Native 관측은 조건 534개(callback 7, catalog 8, catalog-guard 3, gate 9, guard 5, music 4, natural 137, release-guard 5, runtime 236, sound 9, table 11, table-boundary 6, table-guard 19, transition 4, transition-guard 4, zero-step 67)이며 frame 4,036개(one run = one frame: callback PC에서 dispatcher 복귀 `2ac2`까지, 또는 선언 stop·wait까지), split 단계 24,602개, continuous 단계 4,036개다. 그 밖에 natural seed 129개의 F1b prefix frame 0~235(30,444 frame)는 전체 상태 SHA256만 한 번 기록되어 있다.

| 항목 | 값 |
| --- | --- |
| 조건 | 534 (natural 137 = 전체 frame 8 + prefix·tail 129, release-guard 5, runtime 236, 나머지 typed 보조) |
| 실제 C++로 재생한 split 단계 | 24,567 (+ 첫 checked error 단계 35 = native split 24,602) |
| 실제 C++ continuous 재생(frame당 1회) | 4,001 frame 모두 split 연쇄의 최종 출력과 같음 |
| natural prefix frame(continuous 1회씩) | 30,444 frame, SHA256 일치 30,444 (전체 dump 대조 645 frame) |
| tail 시작 상태 | 129개 모두 실제 C++ prefix 출력(frame 235)이며 native fixture RAM·PVC SHA256과 일치 |
| trace 재구성 대조 frame | 3,801 (split 경계 24,095, leader register 경계 18,295) |
| 순서 있는 port(split 단계 합) | 1,878,733 (+ prefix 3,741,837) |
| 대기(Waiting) | 20: `478de` gate 17, `3aea` sound 3 |
| 실행된 block 시작(첫 PC) | 67/67 |
| native guard → checked error | 35 (모두 native split 단계와 같은 단계에서 발생) |
| 원본 ROM 읽기 감사(trace 안의 fixed / bank 읽기) | 110,787 / 1,368,556, 모두 물리 offset의 원본 바이트와 같음 |

[F] 단계마다 실제 C++ 출력의 64KiB RAM, 16 register, PC, A7, PVC, bank, ordered port, external read, status를 native와 대조했다. 각 단계는 직전 실제 C++ 출력(RAM·16R·PC·PVC·bank·carry)과 선언된 host 변경(RAM 쓰기 68,193회, dispatcher 재진입 PC redirect 33,927회·A7 delta 33,927회, gate의 선언 IRQ 효과, sound 해제 write)만으로 재개한다. 재개 입력에 native 기대값 주입은 없다.

### Native 기록이 주는 것과 대조 방법

- [F] Native 관측은 split 단계마다의 상태를 따로 저장하지 않는다. frame마다 선언 step(host 변경, split checkpoint 목록, stop PC)과 continuous 실행의 최종 상태(16 register, PC, A7, bank, RAM·PVC·ordered port의 SHA256, port 수, external read, waiting, 관측기의 상태 SHA256)를 저장하고, typed fixture·dump 8 seed·경계 frame(3801 frame)에는 RAM before/after, PVC, ordered port, PC·bus event trace, leader register 전체가 있다.
- [F] 모든 frame에서 실제 C++ split 연쇄(checkpoint 순서대로 stop)의 최종 출력과 continuous 출력을 native continuous 최종 상태·상태 SHA256(`F1C1-FRAME-STATE-v1`)과 비교했다.
- [F] dump가 있는 frame은 native trace(PC, 순서 있는 bus event)에서 split 경계(checkpoint 첫 도달 직전)의 native RAM·PVC·port·external read·PC를 재구성해 각 C++ split 단계와 대조했다(재구성한 최종 RAM은 기록된 RAM-after와 같음). 그 경계가 F1c1 leader이면 기록된 leader register 16개도 대조한다. dump가 없는 frame(natural prefix, natural-gate의 일부)은 최종 상태 SHA256만 대조한다.
- [F] 같은 계열의 split 연쇄·continuous C++ 실행끼리도 비교했다(위 표의 continuous 재생).

## 대기와 재개

[F] 대기 20건 모두 C++가 `AnimationMachineWaiting`(status 1)으로 native와 같은 PC와 A7에서 멈췄고(gate `478de`는 A7 `1feffc`, 선언 재진입 직후와 같음), 선언된 변경 뒤 정상 재개했다. gate 대기는 `107ded` bit7=1(값 `80`/`ff`/`c3`/`81`)일 때이며 효과 없이 재개하면 같은 Waiting이 반복되고(`gate-resume-no-effect`), 선언 IRQ 효과(`107ded` := 00)를 넣은 뒤에야 `478e6`으로 진행한다. `107dea`≠0 조건(`gate-wait-107ded-81-107dea-nonzero`)은 선언 IRQ 효과가 bit7을 지우지 않으므로(host write 없음) 네 번의 재개 모두 같은 Waiting이다. `gate-pass-*`(`107ded`=`7f`/`00`/`01`)는 첫 검사에서 통과한다. `3aea` 대기는 sound ring full(`104d74`=(`104d76`+1)&`7f`)에서 나며 선언 head release 뒤 재개한다.

- [F] 대기 시 carry: gate 대기 17건 Clear(`72f4 SUBI.B`의 Clear가 BCC를 지나 보존), `3aea` 대기 3건 Unknown(API wait 규약). native 분류와 같다.

## Carry

- [F] Native는 SR을 읽지 않는다. C는 원본 opcode로 분류한다(ORI #1,CCR Set, ANDI #fe,CCR Clear, `72f4 SUBI.B #80,D0`은 native가 읽은 BYTE의 borrow, U3 return-C 루틴의 논리 연산 Clear, `289e` 비교 분기 Clear, FLOW_ONLY opcode는 보존, 그 밖은 Unknown). dump frame의 C++ 단계 24,076개에서 C++ carry가 분류와 같았다.
- [F] 소비자 4개(`478e4`←`72f0`, `47944`·`4795c`·`47974`←`28ae`): 단계 안에서 C를 만든 BCC 위치 385곳에서 분류 C가 실제 native 다음 PC와 같았다. 소비자가 단계 첫 block이면 직전 실제 C++ 출력의 C(known)가 실제 branch를 고르고, 뒤집은 C가 다른 목적지를 고르는 control을 386회 실행했다: `478e4` 191, `47944` 178, `4795c` 2, `47974` 15(Clear/Set 분포는 `verification.json`). `478e4`의 Clear는 `478de`에서 Waiting이다.
- [F] 4개 소비자 직접 진입에서 C=Unknown이면 `stage catalog caller requires known carry`로 거부하고 전체 출력을 보존한다. Known C 양성 control 8개(Clear/Set × 4)는 분기 목적지로 진행하고 C 보존·상태 불변이다.
- [F] FLOW_ONLY 32개: 단일 block 단계에 incoming C 1/2를 넣어(26,532회 probe) 보존 여부를 실제 C++로 관찰했다. probe된 block 시작 61개의 결과가 계약 목록과 일치한다(보존 관찰 27개). 소비자 4개는 flip으로, 아직 관찰되지 않은 `47558`는 직접 API probe(carry 1/2 보존, A0 갱신 확인)로 확인했다. 경로가 incoming C에 의존하는 단계는 probe하지 않는다.
- [F] 정적: C++ `case` 라벨 67개 = 계약 시작 67개, C++ 라우팅 범위 7개 = 계약 code range(`478a6` 제외), `carry_preserving_pc`의 F1c1 항목 32개 = FLOW_ONLY 32개. 어긋남 0.

## Native guard 35개

실제 C++의 checked error 문자열은 아래와 같고 모두 phase 입력의 상태·RAM·PVC·bank·port를 보존한다(continuous 단계 시작에서 돌려도, 다른 incoming C에서도 같은 오류). 오류는 native guard가 난 split 단계와 같은 단계에서 발생했다. 기대 문자열은 native guard 종류에서 허용 집합(odd data access는 두 bus 문자열, 쓰기 오류는 두 device 문자열)으로 정하고 관측된 문자열을 기록했다.

| C++ error | 수 | guard |
| --- | --- | --- |
| `animation machine block budget exceeded` | 3 | `empty-group-09-loop`, `empty-group-0a-loop`, `empty-group-0f-loop` |
| `invalid animation machine write size/alignment` | 1 | `guard-odd-a6-477ee` |
| `program bus requires even WORD/LONG address` | 7 | `guard-odd-a7-477ee`, `guard-odd-record-47842`, `release-guard-136`, `release-guard-137`, `release-guard-138`, `release-guard-139`, `release-guard-140` |
| `unsupported animation machine PC` | 2 | `guard-undeclared-cut-479b0`, `table-18-trap-478a6-undeclared` |
| `unaligned animation machine PC` | 12 | `table-01-odd-pc`, `table-03-odd-pc`, `table-05-odd-pc`, `table-07-odd-pc` … `table-17-odd-pc` 등 |
| `unsupported animation stage catalog PC` | 6 | `table-02-interior-pc`, `table-06-interior-pc`, `table-0a-interior-pc`, `table-0e-interior-pc`, `table-12-interior-pc`, `table-16-interior-pc` |
| `unsupported program bus device address` | 4 | `transition-66-past-47934`, `transition-67-past-47934`, `transition-68-past-47934`, `transition-69-past-47934` |

## 의도된 차이(수와 규칙)

1. [F] PVC 영상 표현: 34,357 frame에서 native 관측기의 PVC 영상(마지막으로 쓴 raw WORD가 `1ff0`/`1ff2`에 남음)과 C++ device(정규화된 bank word)가 다르다. C++ 출력과 ordered port의 raw 쓰기값에서 native 영상을 다시 만들어 SHA256·blob과 비교하고, 정규화 word는 기록된 `ff8`/`ff9`와 독립 fold(`common.fold_device`)로 비교한다. 불일치 0.
2. [F] 초기 SR 선언 없음: 모든 조건이 C=Unknown으로 시작한다(native Unicorn은 SR 2000 = C Clear). 소비자 block으로 직접 들어가는 native 조건은 zero-step 4행뿐이며 실행되는 명령이 없어 Unknown C를 소비하지 않는다(4행).
3. [F] native guard 35개는 관측기 fault·watchdog이고 C++는 같은 단계에서 checked error로 phase 입력을 보존한다(원본 CPU fault rollback과의 동등성은 주장하지 않는다). 분류:
   - `computed_PC_inside_a_table_slot_instruction_native_refused_fetch_vs_cpp_unsupported_catalog_PC`: 6
   - `native_watchdog_vs_cpp_block_budget`: 3
   - `native_write_to_unmapped_address_vs_cpp_checked_device_address_error`: 4
   - `odd_WORD_LONG_data_access_native_address_error_vs_cpp_checked_bus_error`: 8
   - `odd_computed_PC_refused_before_the_jump_native_vs_cpp_unaligned_PC_error_at_the_fetch`: 12
   - `undeclared_stop_only_boundary_reached_native_refused_fetch_vs_cpp_unsupported_machine_PC`: 2
   - [F] 빈 group 3행은 native watchdog 30,000 명령에서 끊고(원본에는 상한 없음) C++는 1,000,000 block 상한에서 rollback한다. [I] 원본은 영원히 돈다.
   - [F] `478a8` 계산 JMP의 홀수 목적지 12행은 native가 jump 직전에 거부하고(관측기), C++는 jump 뒤 홀수 PC를 `unaligned animation machine PC`로 거부한다. 비 slot 짝수 목적지 6행은 둘 다 거부(`unsupported animation stage catalog PC`).
4. [F] gate IRQ palette 효과와 sprite·sound 해제 write는 선언 host RAM write이다. IRQ 자체는 모델링하지 않는다(20 frame).
5. [F] 같은 입력 상태에서 native의 `47934` 이후 garbage 객체 pool 경로(transition 4행)는 C++에서 `unsupported program bus device address`로 거부되고(native: 미매핑 주소 `36506676` 쓰기 fault) 입력을 보존한다.

## 계약·관측 불일치

- [F] 계약 "ROM 자료 window"의 group 0~4 `d99e2..dd4be`는 실제 group 4 extent `dd382..dd4d0`보다 짧다: `47864 MOVE.W 10(A0),D0`가 마지막 record `dd4ae`의 +`10` WORD `dd4be..dd4bf`를 읽는다. native 관측 trace에서 이 창 밖 읽기는 `47864`의 4회(최대 주소 `dd4bf`)뿐이고 모두 실제 group extent 안이다. C++는 물리 ROM(live bus)에서 읽으며 이 읽기를 포함한 frame의 전체 상태가 native와 같다. 직접 probe: `47842` 진입, `76(A6)`=`dd4ae`, WORD `dd4be`는 원본 ROM `19de`; C++의 D0.W가 같고 `10d686`과 같게 하면 `47890`, 다르면 `47872`로 진행한다(probe 5행).
- [F] 계약 "연쇄 seed 142건" 대 137건 + release guard 5건은 native observer의 `contract_discrepancies`(contract-text-differs)와 같다: 5건의 release 출력은 `3c60`(3건, frame 0)·`3bb2`(2건, frame 29)의 U1 `CMP.W`가 홀수 주소 `fcd83`를 WORD로 읽는 경로이며 C++는 `program bus requires even WORD/LONG address`로 거부한다(위 guard 표).

## API-only 부정·경계 검사

- 계약 범위의 내부 PC 214개(짝수 PC 282 − 시작 67 − TRAP 1; 비시작 명령과 피연산자 WORD, 묶인 분기 9개 포함): 직접 진입이 `unsupported animation stage catalog PC`, 전체 출력 보존.
- `478a6`(TRAP 경계)·`479b0`(F1c2 진입) 직접 진입: `unsupported animation machine PC`. 라우팅 밖 이웃 PC 6개(`3d62` `3d7c` `474f4` `4755e` `48156` `47a54`): 같은 오류. 범위마다 첫·끝 홀수 PC 14개와 임의 홀수 5개: `unaligned animation machine PC`. 범위 밖 짝수 PC 4개: `unsupported animation machine PC`.
- 홀수 stop, 짧은 RAM·PVC, 물리 window 누락: checked error와 전체 보존. 소비자 4개의 Unknown carry 거부 4행.
- 67개 시작 × carry 3종 zero-step 201회 성공(상태·RAM·PVC 불변). 경계 `478a6`·`479b0`의 zero-step도 같은 결과.
- 총 checked 부정 253행(소비자 거부 포함), 양성 control 8행.

## 이전 검증기·시험 중 경계가 바뀌는 항목 [목록만, 수정하지 않음]

F1c1이 `3d58..3d62` `3d6a..3d7c` `ca8a..ca9e` `474e2..474f4` `47540..4755e` `477e4..479b0`(`478a6` 제외) `4814e..48156`을 라우팅하므로 `477ee`가 더 이상 “지원 밖 경계”가 아니다.

- C++ 시험은 이 커밋에서 이미 갱신됐다(F1b `animation_machine_area_clear_test.cpp`의 `47e9a` 무 stop 행은 합성 ROM의 `474ec` 읽기 오류로, `animation_machine_motion_walk_test.cpp`의 `outside[]`는 `5f002`로 대체). `make -j4 all test` 종료 코드 0.
- Python 검증기(F1b `verify_animation_machine_area_clear.py`, vf1b worktree, 수정 필요):
  - `GUARD_EXPECTED`의 `guard-stop-not-477ee`(stop `2ac2`만으로 `47e92`에서 시작, native: `47ea8 BRA.W 477ee`가 거부). 이제 C++는 `477ee`를 실행하고 F1c1 frame을 `2ac2`까지 진행한다. 이 저장소 fixture `natural-001`의 `47e92` 상태에서 stop `2ac2`는 성공(PC `2ac2`, A7 `1ff000`)하고, stop `477ee`는 `477ee`에서 멈춘다. 기대 오류(`unsupported animation machine PC`)가 깨진다(F1b typed RAM에서는 다른 오류가 날 수 있음 — [U]).
  - 849–850행 API job `boundary_477ee_without_stop_from_47e9a`(stop `ff000`): 같은 문자열의 오류이나 원인이 `477ee`에서 frame이 끝난 뒤 `2ac2` 복귀로 바뀐다(자연 RAM 재생에서 확인: stop `ff000`과 `479b0`은 `unsupported animation machine PC`, `2ac2`는 성공). 기대 문자열은 유지되나 근거 서술(“477ee는 선언 stop으로만 도달”)이 바뀐다.
  - `guard-no-2ac2-stop-d72fe`·`guard-no-2ac2-stop-e4234`: stop이 `2ac2`가 아니면 `2ac2`의 복귀가 미연결이라는 기대로, 문자열은 유지된다.
  - F1b native 관측 `frame-stop-2ac2-only`(guard `target=477ee`)는 관측 당시 경계 기록이며 C++ 쪽 기대만 바뀐다.
- 영향 없음: `verify_animation_machine_transition.py` 322행 zero-step의 `477ee`(stop = 진입이라 라우팅 전에 끝남), 전이 시험 `animation_machine_transition_test.cpp` 41/71행의 `477ee` stop·점프 대상 검사.
- [U] 위 목록은 grep과 C++ 재생 3건에서 얻었다. F1b·F1a·U 단위 검증기 전체 재실행은 하지 않았다. 계약이 적은 F1c2 쪽 시험 `outside[]` 갱신(`frame_helpers_test.cpp:297-298`, `input_test.cpp:887`, `stage_entry_test.cpp:719`)은 F1c2 단위의 몫이다.

## 재현과 한계

```sh
.venv/bin/python tools/verify_animation_machine_stage_catalog.py   # artifacts/animation_machine_stage_catalog_execution/verification.json
make -j4 all test
```

- [F] 검증기를 같은 입력으로 두 번 실행한 `verification.json` SHA256이 같다(값은 최종 보고에 기록). `make -j4 all test`는 종료 코드 0이다.
- [U] Controlled fixture이며 자연 scheduler, 자연 IRQ, BIOS 실행은 확인하지 않았다. gate의 IRQ palette 효과는 `107ded` bit7 최소 효과의 선언이다. typed fixture의 RAM 영상(원본 `2790`→`3ef2`→`49a1a`를 영 RAM에서 실행한 결과 + 선언 write)은 native 기록 영상을 선언 fixture로 쓴 것이며 그 생성 과정은 native 쪽 증거다. 기존 executor(F1a, F1b, U1–U7, exit, screen, fade_card, sound, transition)는 결과 전체로만 비교하며 내부는 모델링하지 않는다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다. split 단계 중간의 register는 leader에서만 native 값이 있으며, 그 밖의 경계는 RAM·PVC·port·PC·external read만 native와 대조한다. C 분류의 U3 논리 clear 4곳은 68000 규칙(TST/AND는 C를 지움)에서 온 [I]이며 모든 경로가 실제 native 분기로 교차 확인됐다.
- [F] `verification.json`의 `totals.leader_alignment_failed`=12는 비교 실패가 아니다. 대상은 `478a8` 계산 JMP의 홀수 목적지를 관측기가 jump 직전에 거부한 guard frame 12개(`table-01…17-odd-pc`)이며, 이 frame의 마지막 PC(`478a8`)는 leader로 기록되지 않아 검증기의 leader 정렬(guard frame은 마지막 PC도 기록된다고 가정)이 맞지 않는다. 마지막 PC를 제외한 정렬은 12개 모두 맞고(별도 확인), 이 frame들에서도 guard 이전 split 경계의 RAM·PVC·port·PC 대조와 checked error 대조는 수행됐다. 해당 frame의 leader register 대조만 생략됐다.
- [U] 진입 효과 index의 게임 의미, `62(A6)` 자식의 동작, 빈 group 9~15에 자연 진입 가능성은 계약의 미확인 항목 그대로이다.
