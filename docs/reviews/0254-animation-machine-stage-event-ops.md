# stage event F3b(`e94fe` opcode `08..0f`·자식 thread·skip) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 보정, 리뷰, 통합을 맡았다. F3a 실행부의 낡은 주석(`e94fe`가 "실행부 없는 boundary"라는 설명)을 F3b 커밋에서 고쳤다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안(F3 계약의 F3b 절)과 C++ core(`animation_machine_stage_event_ops.cpp`)·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋(`679c882`) 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측(`tools/observe_animation_machine_stage_event_ops.py`).
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. WIP 커밋에 고정된 detached worktree `/Users/start/Workspce/metalslug-vf3b`에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 F2까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약은 F3a와 같은 `docs/analysis/animation-machine-stage-event-f3-contract.md`(SHA256 `bba912176899ab0c21a0b9d54800c5f987f8fdcad9c592b714b8a713d5376c95`)의 F3b 절이다. ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.

범위: opcode `08..0f` 진입 `e94fe..e957c`, `e958e..e9768`, `e9774..e97c8`, 자식 해석기 `e9350..e93da`·`e93f0..e9444`, helper `288c..289e`, `1a92c..1a93e`, `49a84..49a8e`. 8개 code range(952바이트, 271명령, TRAP 포함, 문자열 제외), **block 시작 109개**, TRAP 경계 8개(`e93d8` `e9528` `e9530` `e957a` `e96d4` `e9702` `e9780` `e9788`). 묶인 PC 31개(F3a 22 + 31 = 53). F3b는 op `0c`가 F1c2의 `49a58`(RNG)을 부르므로 F1c2 뒤다.

### 메인 결정

계약 결정 1~10은 `0253`과 같다. F3b에 직접 관련된 것은 결정 3(Z 소비 묶음 선택 A, 갈래 PC `e939a` `e93a2` `e96b4` `e96b8`은 F3b block 시작이고 `e96cc` `e96f8`의 fall-through는 TRAP `e96d4` `e9702`), 결정 4(TRAP 8곳은 실행부 없는 stop 경계), 결정 6(op `09`의 `28ae` 실패는 원본대로, sentinel `100e98` 쓰기), 결정 7(무한 루프·음수 길이 복사 루프는 block budget과 RAM 밖 checked 오류).

**op `08` 실패 경로 (메인 결정, U7 선택 A).** op `08`(`e9558`)은 `2986`으로 객체를 만들고 실패(C=0)이면 TRAP `e957a`로 간다. C++는 U7의 `2986` 실패 반환이 호출자를 알아야 한다는 규칙을 유지한다. 직접 진입에서는 호출자 X를 알 수 없으므로 `cue wrapper failure requires known caller X`로 거부하고 상태를 보존한다. 이는 원본 동작(TRAP `e957a`에서 정지)과 다른 **의도된 차이**다.

### 계약 정정

- 오류 문자열 자료는 계약의 `SET MAKE FAIL!!`이 아니라 ROM 바이트 `ESET MAKE FAIL!!\0\0`(`e957c..e958e`, 맨 앞 `E` 포함)이다. 데이터라 실행되지 않으며 코드 범위에서 빠져 있다.
- 계약 표의 "node 실행 777회(frame 0 `e9150` 95 seed, 자식 676회)"는 쓰기 가능 ROM 탐침 값이다. 쓰기 보호 관측은 F3b를 건드리는 자연 node 471회(`e9150` 95 + `e9176` 2 + `e9350` 10 + `e9362` 364, 95 seed)다. 쓰기 보호 관측 수치가 우선한다.
- native 정적 점검의 `interior_pcs 367`은 TRAP 8곳을 내부로 센 값이며 C++ 내부 PC 359와 일치한다(359 + 8). 계약의 묶인 PC 53·내부 PC 787은 F3a 22 + 31, 428 + 359와 일치한다.
- 관측 입력의 `animation_machine.cpp` SHA는 F3b 라우팅 추가로 달라졌다(`3436aca9…` 에서 `be9da5b4…`, 표시용 입력, 허용).

## 메인 리뷰

1. [F] 자연 node 471개(자기 삭제 6 포함)의 입력·출력·순서 port digest가 전부 일치하고, 전부 RAM·PVC·port 바이트까지 일치한다. 실제 경로 기준 전체 split 11,763 phase가 일치한다.
2. [F] 의도된 차이: op `08` 실패. native 비guard 조건 3(`op08-fail` `op08-null-callback` `trap-e957a-op08-fail-declared`)은 선언 stop인 TRAP `e957a`(native 15 phase)에서 끝나고, C++는 14번째 구간(stop `e9576`)에서 `cue wrapper failure requires known caller X`로 거부한다. 앞 13 phase는 일치한다. 선언 없는 TRAP guard 2건(`op08-fail-undeclared`, `trap-e957a-op08-fail-undeclared`)도 같은 오류이며 구간이 native보다 하나 앞이다. [I] 자연 흐름에서 op `08` 실패 후의 거동은 C++에 없다(`e9576` Clear 경로는 직접 진입 `carry-e9576-sr2000`으로만 닿는다).
3. [F] RNG 정책. op `0c`의 RNG는 F1c2 규칙을 따른다. 링 포인터가 작업 RAM 밖이면 `stage area RNG pointer outside work RAM`으로 거부한다. 같은 정책 6건(`0` `fffd0` `200000` `2fffff` `3fffff`, 자연 상태의 미초기화 0)은 native guard 행과 일치한다. 별개로 `op0c-rng-original-completes`(링 포인터 `fffd0`)는 정책을 끈 native가 정상 완료하지만 C++는 24 phase 뒤 거부한다(**의도된 차이**, 보수적 정책이며 원본 동작이 아니다).
4. [F] 상위 바이트 차이. `op0c-rng-high-byte`(LONG `10d722` = `0110d6b4`): native는 24비트 마스크를 따라가지 못해 guard 행, C++는 24비트 주소 `10d6b4`로 마스크해 오류 없이 계속하며 stop까지 연속 = split 사슬이 일치한다. [I] 24개 주소선 M68000 bus와 같은 동작이며 native 뒷받침은 없다([U]). 이 1건만이 24비트 마스크로 갈린 행이다.
5. [F] op `08` 음수 짝수 길이(`op08-neglen-08`/`-06`). `SUBI.W #a`로 D0.W가 음수·짝수가 되면 복사 루프가 WORD wrap(32,767/32,766 WORD)을 돌며 작업 RAM 미러 전체(스택 포함)를 덮고, `e9768`의 RTS가 LONG 0을 pop한다. C++도 루프를 끝까지 실행하고 PC 0에 도달한 뒤 `unsupported animation machine PC`로 거부한다(native와 같은 27 phase 구간). 스택 덮어쓰기 자체를 C++가 막지는 않는다.
6. [F] carry. consumer `e936e`(`288c`/`289e`/`2898`)와 `e9576`(`2986`)의 Known C가 native 분기와 일치한다(자연 491회 + typed 72회). flip 대조 72회, Unknown 진입은 정확히 `stage event ops caller requires known carry`다. `2898`은 입력 C와 무관하게 Known Set을 만든다.
7. [F] TRAP 8곳은 선언 stop이면 직전 상태로 멈추고 stop이 없으면 `unsupported animation machine PC`다. 문자열 영역 직접 진입은 짝수 20 `unsupported animation machine PC`, 홀수 20 `unaligned animation machine PC`다.

## 검증 결과

- Native: 284 조건(비guard 242 + guard 38 + 비guard인데 C++가 오류인 차이 4), block 시작 109 중 자연 54 + typed 전용 55, 자연 node 471, 조건 split 5,161 / 자연 11,763, fresh CPU 4,025회, 산출물 약 62 MB(git 제외). 관측 SHA `e8a81643f5b62af0f4c570cd1173c7bf7262601fe20e212a711ff9cf5c61239b`(두 번 같음), observer 도구 SHA `c27b2d1cbd01ad02590357589413d3982d0d5c3b8d855a10b64ce3638a738605`.
- C++ 비교(detached worktree `metalslug-vf3b`, 커밋 `679c882`): 조건 284 전부, 조건 split 5,147 중 5,081 phase가 native와 일치(비guard·guard·차이 행의 오류 지점 앞부분 비교. 나머지 66 phase는 오류 지점 뒤라 비교하지 않았다 [I]), 비guard 242개 모두 연속 = split 사슬 = native 연속 기록(선언 A7 일치 167, stop `2ac2` 183 + TRAP 선언 stop 8곳 + `e9362` 1 + `e951c` 1). API 음성 894건(내부 PC 359, 홀수 476, TRAP 직접 진입, 문자열 영역 40 등, 상태 보존), zero-step 117 × 3 carry = 351건, native 진입 탐침 1,000행과 1:1 대응. 단일 block 탐침 6,280회가 FLOW_ONLY 48개를 정확히 재현했다. 묶인 PC 31개 직접 진입 거부 확인. 보고서 `verification.json` SHA `2e4e3a984d086008c366dce1d8140b9776f4a408c6669d37cae084702e4b0d2a`(두 번 같음), 검증기 `tools/verify_animation_machine_stage_event_ops.py` SHA `65f101027fa5847af2be5334f2445be0b37f27bc8d9bbf9d636181fe89460458`, 실행 기록 `docs/analysis/animation-machine-stage-event-ops-execution.md`(SHA `2394aaf7e81e398caec6bd6a98f42e9c93c8379178d90e26df73e92322c35c63`).
- core `engine/src/animation_machine_stage_event_ops.cpp` SHA `5369d279877922f015249c3d4173cccd46beabdf6c3a50d9c220c175b982f61c`(299행), unit `engine/tests/animation_machine_stage_event_ops_test.cpp` SHA `bae8f9192fc53806df02557f177c435a8d173e760789805e7e2459eb41b7e5cf`(578행), 갱신된 `engine/tests/animation_machine_stage_event_test.cpp` SHA `8629f6e27fff059f4da93929d46159dc68f1316bfc38eb2f059d44d007500b92`(532행), 낡은 주석을 고친 `engine/src/animation_machine_stage_event.cpp` SHA `e074f25f82b8e1bd7d84068bfe773db6b9f435cb35d22e95a59e24ead6952d9c`(339행), 라우팅 `engine/src/animation_machine.cpp` SHA `be9da5b4cbdaf50a9d20f3de4198b9621bfbc8b77f3ca9c3dd298220f2e7e2d9`. `make -j4 all test` 종료 코드 0. 단위 시험 fixture 수는 [U] 확인하지 못했다.
- native guard 38건의 C++ 대응: `unsupported_code_target`(op `08` 음수 짝수 길이) 2는 `unsupported animation machine PC`, 홀수 접근 7은 `program bus requires even WORD/LONG address`, `step_limit` 5는 `animation machine block budget exceeded`, 보호 영역 쓰기 5는 `unsupported animation machine write device`, 비매핑 읽기 2와 3c0000 1은 `unsupported program bus device address`, 선언 없는 TRAP 9 중 7은 `unsupported animation machine PC`와 op `08` 실패 2는 `cue wrapper failure requires known caller X`, RNG 포인터 밖 6은 `stage area RNG pointer outside work RAM`, 상위 바이트 1은 오류 없음(의도된 차이).
- 의도된 차이 분류(`difference_classification_counts`): op `08` 실패 경로 3, native TRAP `e957a` 대 C++ cue 실패 2, RNG 정책 대 원본 완료 1, 24비트 마스크 1, 같은 RNG 정책 6, TRAP 경계 대 비라우팅 PC 7, bus error 대 device check 7, watchdog 대 block budget 5, code target guard 대 비라우팅 PC 2, 3c0000 1, 같은 홀수 검사 7.
- 이전 검증기 경계 이동(정렬 커밋에 기록, 수정하지 않음): `tools/verify_animation_machine_stage_event.py` 1046행 `f3b_pc_without_stop` 21 PC(TRAP 8곳만 유효, block 시작 9개와 `e94fe`는 실행되고 묶인 `e9396` `e939e` `e96b0`은 `unsupported animation stage event ops PC`), 1301행 `harness_equivalence`의 `e94fe` stop 사례, `negatives()`의 F3a 범위 이웃 7개 중 `e9350` `e94fe` `e9774` `e97c6`은 block 시작, `1a93c` `e9442` `e9766`은 내부 PC, `CPP_PINS` SHA pin 재고정 필요. `tools/verify_animation_machine_stage_area.py` 1035행 `UNROUTED_NEIGHBOURS`의 `49a84`(F3b block 시작) `49a86` `49a8c`(내부 PC). 전체 목록은 `invalidated_expectation_candidates` `old_expectation_checks` `old_verifier_pin_audit`에 있다.

## 남은 제약

Controlled fixture이며 자연 scheduler·자연 IRQ·BIOS 실행은 미확인이다. 자연 node 입력은 스케줄러 관측의 선언 frame pass 모델이고 native SR은 관측하지 않았다(초기 SR은 선언 값). 기존 executor(cleanup `43e08` `43e22` `43e34`, fade_card `28ae` `2a00`, buffer_cue `2986`, input `289e`, stage area `49a58`, F3a block)는 전체 결과로만 비교하며 내부는 모델링하지 않는다. 자기 루프 block(`e9620` 등)은 zero-step이 되어 첫 도달 탐침을 6회 건너뛰고 다른 조건이 같은 block을 탐침한다. 대기(wait)는 F3b 경로에 없다. op `08` 실패 후 자연 거동, 상위 바이트 비영 RNG 포인터의 native 거동, 다른 형태의 검증기 pin은 [U]다. F4 객체 callback(op `08`이 만든 객체의 callback 63종)은 범위 밖이다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다. 직접 플레이·전체 Goal은 미완료다.
