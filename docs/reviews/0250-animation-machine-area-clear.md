# stage controller F1b(area clear `47da4`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core(`animation_machine_area_clear.cpp`)·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋(`e79f95c`) 위에서 작업했다. `43e34`는 메인이 cleanup.cpp로 옮겼다(WIP `177cb28`, `make all test` 종료 코드 0).
  - Claude Sonnet 5.5 / high: native Unicorn 관측(`tools/observe_animation_machine_area_clear.py`).
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. WIP 커밋에 고정된 detached worktree `/Users/start/Workspce/metalslug-vf1b`에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 F1c2까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-area-clear-f1b-contract.md`(SHA256 `6bd2e96395e73814b7d4308f03d027eb1fb7be3c17ef8019491512340f66d4f2`). 6개 code range(376바이트, 81명령), 39개 block 시작, 묶인 분기 6, FLOW_ONLY 16, carry 소비자 3(`1c5bc` `1c5d8` `47e0a`). 한 machine 실행 = 한 frame이며 `480f0 RTS`가 `2ac2`로 돌아가면 `2ac2` stop으로 끝내고 다음 frame은 F1a 결정 7(c)의 선언된 직접 재진입으로 시작한다. 마지막 frame은 `477ee` stop이다.

### 계약 보정(적용됨)

결정 7(F1b core 보고 반영): 자연 seed는 begin 출력 137개다. release 출력 5개는 WORD `104d8a`=`8001` 때문에 U1 `3c60`에서 홀수 주소 `fcd83`의 WORD 읽기(실제 68000이면 address error)가 나므로 guard row로만 쓴다. 본문의 "142건 모두 `477ee` 도달"은 address error를 모델링하지 않는 Unicorn 결과다. observer가 고정한 계약과 worktree 사본이 같아 수정 사본은 없다.

## 메인 리뷰

1. [F] C++ `case` 라벨 = 계약 39 시작, 라우팅 범위 = 6 range, `carry_preserving_pc`의 F1b 항목 16으로 어긋남 0이다.
2. [F] 계약 결정 6 반박(선언): transition case 77을 `47de4`까지 부분 실행으로 연결한다는 서술은 성립하지 않는다. 기록된 case 77 RAM에서 WORD `100c04`=`f2ee`(비영)이므로 `47db0`→`2a48`이 `2a52 TRAP #15`에 닿는다. C++는 `animation cleanup original TRAP15: nonzero object type`으로 거부한다. 선언 `100c04`:=0을 더한 `transition-case77-partial-type0`은 `47de4`에서 정상 종료하며 native와 같다. 이 선언(`100c04`=0)은 계약에 반영되어야 한다(observer `contract_discrepancies` 1건과 같은 내용).
3. [F] 자연 seed 137개는 각 237 frame(`477ee`)이고 선언 write는 frame 188 뒤 `10dd44`=`ff` 한 건이다.
4. [F] `28ae` free list 머리 `104c9c`=0이면 원본은 ROM 벡터 영역에 쓴다. native는 `unmapped_or_protected`, C++는 write device 거부다(observer 발견, 계약 본문에 없음; 원본 의미는 [U]).
5. [F] `2abe` 재진입 변형(선택 C)은 검증하지 않았다(채택 여부가 열려 있고 native 기록이 없다).
6. [F] 검증기는 batch harness(`harness_batch.cpp`)를 쓰며 one-shot harness와 같은 요청 8건의 출력 동일성을 매번 단언한다.

## 검증 결과

- Native: 256 조건(자연 137, release guard 5, 변형 17, callback 18, player 8, direct 6, transition 5, sound 3, zero-step 39, guard 18), frame 37,444, split 117,537 단계, 모델 37,330 frame 일치. 관측 SHA `88b6b075fb184b37d59cbf454dd4a9cb4eec7f9b4d4dddc2586b993a1e4fc73e`(두 번 같음), observer SHA `afeb5669e119d6c65776e3c36f58f99443d0c7a41ccfd2e085651ccbb3f20201`.
- C++ 비교(detached worktree `metalslug-vf1b`, 커밋 `e79f95c`): 256 조건 전부, frame 37,444(정상 37,418 + guard 26), split 117,537(native와 단계 수 일치), continuous 37,444, 불일치 0, 선언 직접 재진입 37,183, ordered port 8,995,253, 대기 1(`sound-ring-full-0` `3aea`), block 시작 39/39, 소비자 flip control 358, FLOW_ONLY probe 9,068, checked 부정 179, zero-step 117. native guard 26개의 C++ 오류 문자열은 모두 기대와 일치(7건은 같은 검사가 아닌 의도된 차이). 보고서 SHA `fe0de167ad0d036609b33f627e594461f5632bfef96de60faa7cf0431052be0f`(두 번 같음), 검증기 SHA `3d543e5b2c1b23d87053e83ea6dc1ccd180b607e8b25f2df2cec0a5c35bccbc4`, 실행 기록 `docs/analysis/animation-machine-area-clear-execution.md`(SHA `c9d962c8db01157dca0c823e49b6a4245ff9343614c596646646079b806ad815`).
- core `engine/src/animation_machine_area_clear.cpp` SHA `30333c627a4fee5babf1fbf32a3400faa1f4819646d032f6c3e444cbd2ff10a7`(135행), unit `engine/tests/animation_machine_area_clear_test.cpp` SHA `64d932cb28df26cf0f4e2b1c22e9faf99455ea6e7b99ec84031b10983745b989`(817행). `make -j4 all test` 종료 코드 0. 단위 시험 fixture 수는 [U] 확인하지 못했다.
- 의도된 차이 7건: transition case 77 부분·전체 TRAP15 거부(2), `transition-case77-full-type0`의 24비트 마스크 홀수 접근 거부, `a6-102000-seed0`의 ROM LONG 쓰기, `guard-28ae-pool-null-47e30` write device 거부, `observe-odd-a6-byte-47e22`(Unicorn 홀수 LONG 읽기 허용), `guard-odd-a7-47da4`(메시지 층 차이).
- 이전 검증기 경계 이동은 정렬 커밋에 기록한다: `verify_animation_machine_input.py` 861행 `outside_entry`의 `0x1bee4`(F1b block 시작이 되어 기대가 깨짐). C++ 시험은 이미 갱신됐다(motion_walk `47da4`→`5f002`, input `1bee4`→`1bef8`).

## 남은 제약

Controlled fixture이며 자연 scheduler·자연 IRQ·BIOS 실행은 미확인이다. 자식 `e4234`/`d72fe`, frame 사이 IRQ 효과, `10db85/87` `100967` `107def` `10dd44` 및 player node bit의 의미는 [U]다. native split 중간 RAM은 저장되지 않아 중간 정지 상태는 dump된 leader 레지스터로만 비교한다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback과의 동등성은 아니다. sprite 대기 `cda4`는 이 fixture 집합에 없다. 직접 플레이·전체 Goal은 미완료다.
