# stage controller F1c2(area·player 초기화 `479b0..47a94`) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core(`animation_machine_stage_area.cpp`)·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋(`2aae52f`) 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측(`tools/observe_animation_machine_stage_area.py`).
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. WIP 커밋에 고정된 detached worktree `/Users/start/Workspce/metalslug-vf1c2`에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 F1c2까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약은 F1c1과 같은 `docs/analysis/animation-machine-stage-catalog-f1c-contract.md`(SHA256 `f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575`)의 F1c2 절이다. 24개 code range(1,580바이트, 명령 381개 + 경계 TRAP `4d824`), 153개 block 시작, 묶인 분기 24(조건분기 23 + DBRA `4aa72`), FLOW_ONLY 77, 소비자 5(`47716` `47732` `4776c` `1bd34` `1bd96`, 모두 `289e` 복귀 직후 Bcc). 메인 결정은 F1c1 리뷰(`0251`)에 적은 계약 머리말과 같고 F1c2에 고유한 것은 결정 9(`49a58` RNG의 A5 덮어쓰기는 원본대로, 포인터가 RAM 밖이면 checked 오류)와 `4d824` stop 경계다.

### 계약 정정(적용 필요)

- 데이터 창: 계약의 group 0~4 `d99e2..dd4be`는 group 4 extent `dd382..dd4d0`보다 짧다. `47a20`(`MOVEA.L 76(A6),A0; MOVE.W 10(A0),D0`)이 창 밖 `dd4be..dd4bf`를 읽는다(자연 4회, observer `contract_discrepancies` 1건). 정정 내용은 `0251`과 같다. 계약의 seed 수 142는 137 + release guard 5로 정정된다.
- RNG 포인터 정책(결정 9)의 범위는 아래 "의도된 차이 A"에 따라 계약에 기록되어야 한다.

## 메인 리뷰

1. [F] C++ `case` 라벨 = 계약 153 시작, 라우팅 24 range(`4d824` 제외), `carry_preserving_pc`의 F1c2 항목 77로 어긋남 0이다.
2. [F] 연쇄 seed 137개의 32,606 frame이 `47a94`까지 native와 일치하고 runtime 236건(1,252 frame)도 일치한다. runtime frame base는 살아있는 node가 아니라 dead node(`270e`)를 써야 하며 fixture에 root ring이 필요하다(fixture 작성 시 발견).
3. [F] RNG 정책 deliberate difference: C++는 LONG `10d722`의 24비트 주소가 `100000..1fffff`가 아니면 `stage area RNG pointer outside work RAM`으로 거부한다. 정책을 끈 원본은 RAM 아래 `fffd0..fffff`의 포인터(`fffd0` `fffd2` `fffe0` `ffff0` `ffffc` `ffffe`, 6행)에서도 frame을 정상 완료하지만 C++는 거부한다. 원본 동작이 아니라 보수적 정책이다. ROM·미매핑 주소 포인터 4행(`0` `30` 등)은 원본이 `49a80`에서 `unmapped_or_protected`로 멈추고 C++는 더 이른 RNG 검사로 거부한다.
4. [F] 24비트 상위 바이트 동작(`rng-outside-high-ff10d720`): C++는 거부하지 않고 완료한다. 범위 검사와 bus 접근이 24비트 주소 `10d720`을 쓰고 레지스터 비교·산술은 32비트라 `A3=ff10d722`는 `A4=0010d722`보다 작지 않아 두 감산(`-6e`)이 모두 적용되어 `A3=ff10d674`로 끝난다(독립 Python 모델과 일치). [I] 24개 주소선 M68000 bus와 같은 동작이다. native 뒷받침은 없다([U], Unicorn은 상위 바이트를 마스크하지 않아 `rng_pointer_high_byte`로만 기록).
5. [F] TRAP 경계 `4d824`/`4d7f0`은 stop 전용이며 stop 없이 닿으면 `unsupported animation machine PC`다.
6. [F] 자식 완료 `62(A6)`는 선언 host 쓰기이고 자식 `4fcb8`/`4fd0a`/`4ff4c`/`d764a` 코드는 모델링하지 않았다([U]).

## 검증 결과

- Native: 753 조건(자연 137 = 129 + 8, release guard 5, runtime 236, area 18, music 16, players 20, players-direct 48, rng 10, rng-guard 14, rng-difference 10, effect 15, trap-boundary 6, trap-guard 2, lookup 10, alloc 4, area-direct 26, sound 16, guard 7, zero-step 153), frame 3,735(전부 dump), split 63,558 / continuous 3,735 단계. 관측 SHA `851281ab5037a7daac6d1831d814406057245839271ed3591df225e4ce2b44ca`(두 번 같음), observer 도구 SHA `80f890edced7d875607f9dfbd924ce302e3db12703db1df4e03f1c41bb4bb82a`.
- C++ 비교(detached worktree `metalslug-vf1c2`, 커밋 `2aae52f`): 753 조건 전부, frame 3,735(정상 3,695 + native guard 34 + 차이 6), split 63,538(native 63,558; 차이 20은 의도된 차이 행의 거부 지점 앞당김), split = continuous = native 3,695/3,695, 선언 직접 재진입 2,968, ordered port 1,386,546, 대기 12(`sound-wait-*`), block 시작 153/153, 소비자 flip control 998, FLOW_ONLY probe 80,756, 총 checked 부정 719, RNG 포인터 API 14건, zero-step 462(153/153 조건). 보고서 SHA `4adc09552dcb22edce8e54783802390c0037395f9eb230fe21707212b53c3656`(두 번 같음), 검증기 SHA `80b760b0ee6a1de578ebfc816b51180b7b8bacdae38d430be0509c50d3bbe8c6`, 실행 기록 `docs/analysis/animation-machine-stage-area-execution.md`(SHA `d6132921a2b1ba1def345e0b3ea935af0e88025a2d519c73c8dec035c450ec16`).
- core `engine/src/animation_machine_stage_area.cpp` SHA `dd273339b0a98d71bdf4f1b492e9354079c399f99eea0c7ad4ad078e43eb8d10`(365행), unit `engine/tests/animation_machine_stage_area_test.cpp` SHA `e5e22cd0bfabe3f30b11d1fe8677f148bad76884e724a3d64acb5ac9b2c744c9`(897행). `make -j4 all test` 종료 코드 0. 단위 시험 fixture 수는 [U] 확인하지 못했다.
- 의도된 차이 17행(검증기 기록): 정책 끈 원본이 완료하고 C++가 거부 6, 정책 끈 원본이 ROM 쓰기 fault이고 C++가 이른 RNG 거부 4, native 관측 없이 C++가 24비트 마스크로 완료 1, TRAP 경계 stop 전용 2(`481de-trap-no-stop` `48180-u6-trap-undeclared`), ROM 쓰기 vs write device 거부 2(`d760a-28ae-empty-list` `475ca-players-alive-null-8c`), 홀수 A7 push 메시지 층 차이 1, 비영 object type TRAP15 검사 1(`guard-node-depth-47770`).
- 이전 검증기 경계 이동은 정렬 커밋에 기록한다(2곳, 주 작업 트리): `verify_animation_machine_frame_helpers.py` 541행 `reject` 목록의 `0x2efdc`(block 시작이 됨; `0x2eff4` 같은 미연결 PC로 이동), `verify_animation_machine_input.py` 861행 `outside_entry`의 `0x4d81c`(`0x4d84e`로 이동). 이 두 파일은 vf1c2 worktree에 없다. 영향 없음 항목 4곳은 실행 기록에 있다.

## 남은 제약

Controlled fixture이며 자연 scheduler·자연 IRQ·BIOS 실행은 미확인이다. native 시작 SR은 선언 값이고 모든 fixture는 C++에서 Unknown carry로 시작한다. `478de` gate 대기와 `cda4`는 이 fixture 집합에 없다. 자식 코드, `4d824`·`4d7f0` TRAP의 실행, 상위 바이트 비영 RNG 포인터의 native 동작, 실제 하드웨어의 ROM 쓰기 결과는 [U]다. native split 중간 RAM은 저장되지 않아 중간 정지 상태는 dump된 leader 레지스터로만 비교한다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다. 직접 플레이·전체 Goal은 미완료다.
