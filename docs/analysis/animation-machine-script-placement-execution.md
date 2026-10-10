# `480bc` 프레임 helper U5 실행부 검증 기록: script opcode·배치 `1a0b6`/`1a470`

대상: `engine/src/animation_machine_script_placement.cpp`(대상 커밋 `018d0b2`)와 cleanup 실행부의 `43e08`/`43e22` case. 검증기: `tools/verify_animation_machine_script_placement.py` → `artifacts/animation_machine_script_placement_execution/verification.json`(Git 제외). 계약: `animation-machine-script-placement-u5-contract.md`(SHA256 `08f3f1ea9bd6e7344d97fd9bb7a2fa3cd776f40b2d46c1e305f5688ef6c1ff4c`). 원본 ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(canonical BE, 고정 CPU 주소=파일 오프셋). native 관측 `artifacts/animation_machine_script_placement_native/observation.json`(SHA256 `cbe215f0a9803ad9f49fc067a3fdbf66e20cef031c8651d3b41a8bdfecabcf13`, 관측기 SHA256 `f05a7d1117b4d2612f517b491da4619ba8f5c7c0b57a06991e3533137659ae03`). [F]=검증기가 확인한 사실, [I]=추론, [U]=미확인.

## 방법 [F]

- native 관측 산출물(56,503개)은 불변 입력이다. 검증기는 전부 읽어 SHA를 대조하고 관측기를 실행하지 않는다. ROM은 읽기만 하며 mtime·SHA 불변을 확인한다.
- 정적: 계약 표 13개 범위의 바이트가 ROM과 같고(코드 872바이트 258명령, 자료 32바이트), 원본 opcode에서 독립 유도한 block 시작이 계약 88개와 정확히 같다(`jmp` 목표 포함, 양방향 차이 0). 묶인 분기 13개, FLOW_ONLY block 35개, carry 소비 block 1개(`197a2`), ORI/ANDI/EORI/MOVE-to-CCR 생산자 0, X 소비 명령 0을 같은 방식으로 재유도해 계약과 대조했다. C++ `case` 라벨 = 계약 시작 86개(U5 파일) + cleanup의 `43e08`/`43e22`.
- 동적: native 658 행(정상 626 + guard 32)의 split phase 5,475개를 실제 C++ 공개 API로 재생한다(full 64KiB RAM, 16R, PC, A7, PVC page, bank, 순서 있는 port 스트림(`3c0006` 포함), 외부 읽기, status). split의 첫 phase는 선언된 시작 상태, 이후 phase는 직전 실제 C++ 출력과 native step에 기록된 host RAM 변경(2,703개)만으로 재개한다. 연속 control 663개도 같은 시작에서 재생해 split 끝과 비교한다.
- 시작 상태: 19개 natural chain은 `scene_frame_execution` 입력을 `scene_general_initialization` 시드와 host write로 재구성(RAM SHA 일치 확인)하고 `1a73c`→`1a0b6`/`1a470`→…→`ff000` 3단계를 실제 C++로 잇는다. 나머지 628행은 native 산출물에 SHA로 고정된 선언 상태(원본 실행의 hit 상태 + 선언된 RAM/레지스터/스택 변형), 11행은 쓰기 전 이미지가 산출물에 없어 phase 0의 쓰기 후 이미지(선언된 쓰기가 이미 반영됨을 확인)에서 시작한다. 선언 상태 중 실제 C++ chain 출력이 같은 상태(RAM SHA, 16R, PC, PVC SHA, bank)를 독립 재현한 것은 26개, 아닌 것 613개 [F].
- carry: native SR은 읽지 않는다. phase마다 C++ carry가 원본 opcode 분류(ORI/ANDI CCR 알려진 값, U3의 `19710`/`1971c` TST.W·`19372`/`1957a` AND.W 알려진 Clear(U3 계약 결정 2), U2의 `1a2e0` 계산 carry와 fade_card 규칙, FLOW_ONLY 보존, 그 밖 Unknown)과 같음을 대조했다(Unknown 5,283 / Clear 35 / Set 157). 입력 carry 1·2 probe 10,890회에서 단일 block 87개의 보존 여부가 계약의 FLOW_ONLY 목록과 정확히 일치한다(보존 34개 + 소비 block `197a2` 별도 검사 = 35).
- `197a2`(BSR `18c06` 복귀 직후 BCC, carry 소비): 이 PC가 phase의 첫 PC인 30개에서 Unknown 입력은 모두 `script placement caller requires known carry`와 전체 보존 오류, 원본이 간 갈래와 일치하는 known carry(Set→`197a6`, Clear→`197b2`)는 native 출력과 같다. 반대 갈래 실행은 native phase의 stop을 통과하지 못하므로(4건만 성공) 비교 대상이 아니다.

## 통합 검증: scene_frame 594 seed 전체 프레임 [F]

`1a73c` 직접 진입(A7=`1feffc`, 복귀 LONG `ff000`, bank `200000` page, 14R+A5=`108000`)에서 `ff000`을 pop하는 RTS까지 U2~U5와 기존 실행부로 594개를 연속 실행했다(C++ 단일 호출, 로드: script 진입 111, placement 진입 6, 총 port 621,663개).

- 기록된 원본(flat map) 실행과 비교: 순서 있는 port 스트림(바이트 단위, port 수 포함), 14개 결과 레지스터, 최종 PC=`ff000`·A7=`1ff000`, 최종 bank, RAM(스택 창 밖)이 594/594 일치. 명령 수는 C++ API가 노출하지 않아 비교하지 않는다.
- 스택 창: machine image는 work RAM을 미러링하고 live 스택(A7 `1feffc`부터 아래)이 image offset `effc` 아래에 놓이며 flat 원본은 다른 곳에 둔다. 창은 native 기록의 `[lo, f000)`(frame마다 18~56바이트: `efc8`/`efd4`/`efe0`/`efe8`/`efee`..`f000`)이고 원본 비교에서만 제외한다. native machine-style 전체 프레임 기록(`outgoing_ram_sha256`, `ports_sha256`)과는 창 포함 64KiB 전체 image SHA가 594/594 일치한다.
- `1a7a8`(U4 진입)에서 끊어 이어 실행한 결과가 연속 실행과 RAM/PVC/ports/16R/bank 모두 같다(594/594). 19개 natural chain(3단계 C++)의 최종 RAM·port·상태·bank가 같은 case의 연속 프레임과 같다(19/19).

## 부정·경계 검사 [F]

- 88개 block 시작 × carry 3종 zero-step(stop=PC): 264개 모두 성공, 상태 불변. 정확한 오류 문자열은 모두 오류 시 API 출력 전체 보존(RAM/PVC/bank/16R/PC/ports 표식/status)을 함께 확인했다.
- 직접 진입 거부: 라우팅 범위 안의 비-block-시작 짝수 PC 340개(묶인 분기 13개, 명령 중간, operand word, `1a08e..1a0b6` PC 상대 자료 16 WORD 포함) → `unsupported animation script placement PC`. 홀수 PC 8개 → `unaligned animation machine PC`. 범위 바로 바깥 12개(`3db2`, `16ff0`, `19768`, `1a07a`, `1a414`, `e89f8`, `e8a0c` 등) → `unsupported animation machine PC`. `197a2` Unknown carry → `script placement caller requires known carry`. 도달 못하는 stop 4건은 상태 의존 checked 오류로 끝나며 전체 보존이다.
- cleanup 실행부의 `43e08..43e34` 비시작 짝수 PC 20개는 `unsupported animation machine PC`다(U5 오류가 아님, 사실만 기록).
- native guard 32행 → 정확한 C++ 오류(원본 native guard의 종류·접근·목표 PC에서 규칙으로 기대 문자열을 정한 뒤 비교): 홀수 읽기 `program bus requires even WORD/LONG address` 6, 홀수 쓰기 `invalid animation machine write size/alignment` 4, ROM 쓰기 `unsupported animation machine write device` 4, 스택 push ROM 쓰기 `program bus write requires RAM mirror units` 1, 목표 PC 오류(홀수 `unaligned animation machine PC` 2, 라우팅 범위 밖 `unsupported animation machine PC` 6, 내부 PC `unsupported animation script placement PC` 1). 홀수 길이 복사(`fixture-place-copy-length-odd-1/-3`)는 block budget이 아니라 `200000` 창 쓰기에서 `unsupported animation machine write device`로 끝난다(알려진 사실과 일치). placement 6 case의 `1a470` 경로(U3 `19812` 경유, D7 비교 `1a484`)는 split/control 모두 native와 일치했다(비교 대상은 C++ 출력과 native 레지스터·RAM이며 D7 의미 자체는 별도 가정하지 않는다).
- 계산 PC 정책 [F]: native `fixture-opword-0052-mid-block`은 opcode WORD `0052`로 `1a0bc+0x52=1a10e`(block `1a10c`의 중간)에 착지해 계속 실행한다. C++는 이 phase에서 `unsupported animation script placement PC`와 전체 보존으로 거부한다(split·control 각 1건). 뒤따르는 native phase 4개는 C++ 대응이 없다(정책상 의도된 비재생).

## 이전 verifier에서 U5로 인해 의미가 달라지는 부정 검사 (적용하지 않음) [F]

- `tools/verify_animation_machine_scene_core.py` 46행 `BOUNDARY_PCS`(`1a0b6`·`1a470` zero-step/경계), 72~73행 `GUARD_ERRORS`의 `guard-bad-stop-1a0b6-on-full-path-seed`/`guard-bad-stop-1a470-on-full-path-seed`(native U2 관측의 라벨, U5 이후 해당 PC가 실행부를 가지므로 `unsupported animation machine PC` 기대가 달라질 수 있음 [I]), 813행 `for stop in (…, 0x1a0b6, 0x1a470, …)` 도달 못하는 stop 목록, 8·939행 설명 문구.
- `tools/verify_animation_machine_scene_update.py` 717행 `outside` 목록의 `0x1a470`(직접 진입 시 `unsupported animation machine PC` 기대): 이제 `1a470`은 U5 block 시작이라 오류 문자열이 달라진다(이 검증에서 `1a0b6`/`1a470`/`16fee`/`3d7e`/`e89fa` 직접 진입이 `unsupported animation machine PC`가 더 이상 아님을 확인).
- `16fee`/`3d7e`/`e89fa`를 unsupported로 쓰는 verifier 문구는 발견되지 않았다. C++ 테스트 쪽 기대(`animation_machine_scene_core_test.cpp` 80·116·123행, `motion_walk_test.cpp` 645행)는 `make test` 결과로 판단한다.

## 미확인·한계 [U]

- native 8행(`fixture-op04-index-1fff/2000/6000/0100`, `op14-index-10`, `op24-index-10`, `op14-index-7ffe`, `op24-index-7ffe` exploratory)은 native 관측기가 고정 ROM 읽기(`fd2b4` 부근 등)를 `unmapped_or_protected`로 막았지만, C++ 공개 API는 같은 읽기를 원본 ROM 바이트로 수행하고 이후 쓰기에서 checked 오류로 끝난다(오류 문자열은 JSON `native_vs_cpp_guard_divergences`). 두 쪽 모두 오류이지만 오류 지점이 다르다. native의 이 guard가 원본 동작인지 관측기 매핑 한계인지는 미확인이다.
- 5,624 상태 census는 native 모델 대 원본 일치(5,634/5,634) 증거이며 상태가 저장되지 않아 C++로 재생하지 않았다. 자연 480bc 프레임은 U5에 도달하지 않는다(U5 도달은 scene_frame 직접 `1a73c` 진입 seed, 초기화 seed, 선언 fixture).
- 기존 실행부(`18c06`·`197da`·`19802`·`8da2`·`43ffc`·`17012`·`1701a`·`28ae`·`43e38`)는 결과 전체(RAM/16R/port/bank)로만 비교한다. 검증기 호출 사이의 carry 보존은 원본 opcode 분류이며 SR 실측이 아니다. 실패 시 보존은 API 출력 보존이지 원본 CPU 예외 rollback 동등성이 아니다.
