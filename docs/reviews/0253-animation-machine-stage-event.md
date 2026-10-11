# stage event F3a(`e9150` 이벤트 해석기 core·opcode `00..07`·평가기) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 보정, 리뷰, 통합을 맡았다. `43e34` 진입을 stage event 실행부에서 cleanup 실행부로 옮긴 것도 메인이다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안(F3 계약의 F3a 절)과 C++ core(`animation_machine_stage_event.cpp`)·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋(`b77627d`, 이어서 메인의 `43e34` 이동 커밋 `177cb28`) 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측(`tools/observe_animation_machine_stage_event.py`).
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. WIP 커밋 `177cb28`에 고정된 detached worktree `/Users/start/Workspce/metalslug-vf3a`에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 F2까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약은 `docs/analysis/animation-machine-stage-event-f3-contract.md`(SHA256 `bba912176899ab0c21a0b9d54800c5f987f8fdcad9c592b714b8a713d5376c95`, 333행)의 F3a 절이다. ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소 = 파일 오프셋, 코드·자료 모두 `<100000`이다.

범위: 주 stream 루프 `e9150..e9350`(opcode 표 `e91e4` 8 slot), opcode `00..07` 처리기 `e9444..e94fe`, 길이 전진 `e9768..e9774`, 평가기 `e97c8..e98ee`(연산자 표 `e97e4` 34 slot), helper `48502..4855c` `1a910..1a91a` `1a93e..1a952`. 7개 code range(1,124바이트, 324명령), **block 시작 134개**, 경계 `e94fe`(F3b 진입, 실행부 없는 stop). 전체 F3는 block 시작 243개 + TRAP 경계 8개이고 계약 결정 1에 따라 F3a 134 / F3b 109로 나눴다. F3b는 별도 리뷰 `0254`다.

### 메인 결정 (계약 머리말 기준)

1. F3를 `e94fe`에서 F3a(134)와 F3b(109 + TRAP 8)로 나눈다. 순서는 F3a, F2, F3b다.
2. 계산 PC 표 5개 중 원본이 범위를 막는 4개는 그대로, 상한이 없는 `e97e0` 표는 F1 결정 3(대상이 지원 block 시작이면 실행, 아니면 unsupported)을 따른다.
3. **이전 block의 Z 소비: 선택 A.** `e98ea` block이 BYTE pop과 Z 계산 뒤, 복귀 LONG이 `e9396` `e939e` `e94c0` `e96b0` 넷 중 하나이면 그 분기를 같은 block에서 평가하고 갈래로 이동한다. 그 밖의 복귀 LONG이면 PC를 복귀 LONG으로 둔다. `e96d0` `e96fe`도 앞 block에 묶인다. 이 6 PC는 직접 진입을 거부한다. `AnimationMachineState`와 공개 header는 바꾸지 않는다.
4. TRAP #15 8곳은 stop 경계(F3b 소관). 5. BYTE stack push/pop은 F1c 규칙(A7±2, BYTE 하나). 6. op `09`의 `28ae` 실패는 원본대로. 7. 무한 루프는 block budget에 맡기고 RAM 밖 쓰기는 checked 오류. 8. ROM 자료는 physical window만. 9. 파일명·오류 문자열은 본문 결정 9. 10. seed는 node 단위(PC=`2ab8`, A6=node, `2ac2` stop).

### 계약 정정

- 표 밖 연산자(`e97e0` 표 index 범위를 넘는 94개)에서 거부되는 값은 계약의 76이 아니라 **84**다(94 − 실행되는 block 시작 10). 84의 내역은 block 내부 명령 시작 18, 명령 내부 5, 범위 밖 61이다. [F] native 관측과 C++ 검증기가 일치한다.
- **연산자 `8c`는 합이 계약의 12바이트가 아니라 앞 8바이트(`10de30..37`)다.** 관측 `eval-8c-*`와 C++가 일치한다.
- 계약의 "자연 node 11,391회"는 142 seed 기준이다. 본 관측은 자연 seed 137개의 9,613회(`e9150` 134, `e9176` 9,479)다. 계약의 자연 시작 상태 수치는 쓰기 가능 ROM 탐침 기반이며, 쓰기 보호 ROM 관측 수치가 우선한다(`0255`의 같은 항목 참조).
- 관측 입력 중 `engine/src/animation_machine.cpp`는 관측 이후 F3a 라우팅이 추가되어 SHA가 다르다(스케줄러 rA/rB 표시용 입력, 허용).

## 메인 리뷰

1. [F] `43e34` 이동. F3a WIP(`b77627d`)는 `43e34`(stage event `e9186 JSR 43e34.L`, `LEA 2e(A6),A0` 후 `43e38`)를 stage event 실행부에서 처리했다. 이는 기존 cleanup 실행부의 `43e04/43e34 stay unsupported` 주석과 어긋나고 파일 소유가 둘로 갈린다. 메인이 `177cb28`에서 `43e34` case(`A0 = A6 + 0x2e`, PC=`43e38`)를 `animation_machine_cleanup.cpp`로 옮기고 routing에서 `43e34` 예외 두 곳을 제거했다. 거동 변화는 없다. `make all test` 종료 코드 0이며 검증기는 이동 이후 상태(`177cb28`)에서 실행했다.
2. [F] 결정 3 선택 A는 typed `eval-return-*` 38개로 확인했다. 복귀 LONG이 네 호출 지점 중 하나이면 분기를 같은 block에서 평가해 갈래(`e9428` `e939a` `e93a2` `e96b4` `e96b8` `e94c4` `e9768`)로 이동한다. 6 PC 직접 진입은 거부한다.
3. [F] 계산 PC: `e97e0` 표 밖 연산자 94개 중 10개는 block 시작에 닿아 원본대로 실행하고(`a2`→`e986c` 등) 84개는 거부한다. [I] 거부는 보수적 정책이며 원본은 그 임의 주소를 실행한다.
4. [F] 자연 node 9,613개의 입력·출력 digest가 전부 일치한다. 이 중 856개는 RAM·PVC·port 바이트까지 비교했고 8,757개는 상태·port digest와 leader 한 곳 split 결과를 비교했다. 비dump 표본은 digest 수준이다.
5. [F] carry. consumer `e9248`/`e9258`의 Known C(`49392` 반환)가 native 분기 경로와 1,712 + 802회 일치한다. flip 대조 802회, Unknown 진입은 정확히 `stage event caller requires known carry`다.
6. [F] 평가기의 BYTE stack은 A7±2에 BYTE 하나만 쓴다.

## 검증 결과

- Native: 560 조건(비guard 443 + guard 117), block 시작 134 중 자연 71 + typed 고정자료 전용 63, split phase 23,014(조건) + 자연 360,906, fresh CPU 51,989회. 자연 node 9,613. 관측 SHA `44836842e9b132ac4909e693845f85def6d3204787c764eca33bf17e1d100ae0`(두 번 같음), observer 도구 SHA `ae0840bbd1eb22a4aaa1de78a274ef924c22b6b2ea87ae0125eefd33cd3ed9c6`, 산출물 크기 약 176 MB(git 제외).
- C++ 비교(detached worktree `metalslug-vf3a`, 커밋 `177cb28`): 조건 560 전부, split phase 22,864(guard 앞부분 포함)이 native와 일치, 비guard 443개 모두 연속 = split 사슬 = native 연속 기록(선언 A7 일치 403, 경계 stop `e94fe` 등 20). API 음성 1,034건(상태 보존: 내부 PC 428, 홀수 562, 이웃·F3b PC 21개·범위 밖), zero-step 134 start × 3 carry = 402건, native 진입 탐침 1,124와 1:1 대응. 단일 block 탐침(C=1·2) 33,542회가 FLOW_ONLY 60개를 정확히 재현했다. 보고서 `verification.json` SHA `070c665d4cdb6b3a853fbcceac8d94a0e1a7ec29e2ca98f9b226bd767d4d2f89`(두 번 같음, `diff -rq` 차이 없음), 검증기 `tools/verify_animation_machine_stage_event.py` SHA `bc85f570f0d1a39c3895694b1f295b3f0625f0f9431c741c1a28c858d3e520ff`, 실행 기록 `docs/analysis/animation-machine-stage-event-execution.md`(SHA `b1be618fe70c53990451c0bbdff6e0aa30b0a022b7fe8bfca41ba892bf6be1b6`).
- core(`177cb28`) `engine/src/animation_machine_stage_event.cpp` SHA `2ddae53ed0857c04e024747eb63baa23b5c51afefb4cd8f8a1d71d2ebdc7aa67`(339행; `b77627d` 시점은 SHA `b0dfd9cd3cd0b1b8130f301ae6b17d7ce0c3a568f4ff12fc22b4d9595f2290ba` 342행), `engine/src/animation_machine_cleanup.cpp` SHA `0471d9ba39454646f775b9f61f3603cb52cf80e009b6481e7f11ff26ccc5bbd3`(227행, `43e34` case 포함), unit `engine/tests/animation_machine_stage_event_test.cpp` SHA `759c7b448add154723878da8f83c3190ba124a446e024393df3bd9d2e2ce0358`(524행). `make -j4 all test` 종료 코드 0. 단위 시험 fixture 수는 [U] 확인하지 못했다.
- native guard 117건의 C++ 대응: 홀수 PC 1(`unaligned animation machine PC`), F3a 범위 안 비start 24(`unsupported animation stage event PC`), 범위 밖 78(`unsupported animation machine PC`), 홀수 데이터 5, `step_limit` 2(`animation machine block budget exceeded`), 보호 영역 쓰기·비매핑 4, 3c0000 1, TRAP `4d7f0` 1, PVC `2ffff0` 읽기 1(오류 없음). 모든 오류는 RAM·PVC·port·16R·PC·carry를 보존한다. 원본 CPU 예외 rollback 동등성은 주장하지 않는다.
- 의도된 차이 8건: bus error와 checked error의 층 차이 5(ROM 쓰기 2, 스택, 비매핑 읽기, device 읽기), TRAP 경계와 비라우팅 PC 1(`4d7f0`), PVC 레지스터 페이지 `2ffff0` 읽기를 C++ 버스가 모델링해 실행을 계속하는 경우 1(native는 거부). 실행 기록의 분류표는 이 7건만 나열하며 8번째 행의 내용은 [U] 확인하지 못했다.
- 이전 검증기 경계 이동(정렬 커밋에 기록, 수정하지 않음): `tools/verify_animation_machine_scene_update.py` 718·732행이 `1a910`/`1a912`를 비라우팅 이웃·stop으로 쓴다. 이제 `1a910`은 block 시작, `1a912`는 내부 PC다. 같은 파일 65행, scene_update 시험 791행, stage_entry 시험 637행은 영향 없다.

## 남은 제약

Controlled fixture이며 자연 scheduler·자연 IRQ·BIOS 실행은 미확인이다. 자연 node 입력은 스케줄러 관측의 선언 frame pass 모델이다. 자연 node 8,757개는 digest와 단일 split 비교다. F3a 경로에 대기(wait)는 없다. F3b(`e94fe` 이후)는 이 단위 실행부에 없고(`0254`), 객체 callback(F4)은 범위 밖이다. native SR은 읽지 않으며 carry는 block 분류다. 직접 플레이·전체 Goal은 미완료다.
