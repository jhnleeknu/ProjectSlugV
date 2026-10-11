# scheduler shell F2(노드 디스패처 프레임 패스·`270e` idle callback·`4fcce` fade 자식) 리뷰

대상은 이 문서를 포함하는 로컬 커밋이다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: 계약 초안과 C++ core(`animation_machine_scheduler.cpp`)·routing·unit 테스트를 맡았다. 별도 git worktree `metalslug-input`의 임시 WIP 커밋(`55261ac`) 위에서 작업했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측(`tools/observe_animation_machine_scheduler.py`). F3 node 단위 seed(`f3_node_seeds.json.gz`)도 이 도구가 만들었다.
  - Claude Sonnet 5.5 / medium: C++ 검증기와 실행 문서. WIP 커밋에 고정된 detached worktree `/Users/start/Workspce/metalslug-vf2`에서 작업했다.
- 일부 작업자는 API 사용량 제한으로 중단됐다. 각 작업자는 자기 transcript에서 재개했으며, 완료된 실행은 반복하지 않았다.
- 통합 방식: 각 단위 WIP 커밋 상태(detached worktree)에서 해당 단위 검증기가 통과했다. 이전 검증기들의 경계 음성 이동과 전체 회귀는 F2까지 적용한 최종 상태에서 한 번에 수행하고 그 결과는 정렬 커밋(별도)에 기록한다.

## 원본 의미와 범위

계약은 `docs/analysis/animation-machine-scheduler-shell-f2-contract.md`(SHA256 `6584431718e82293372350b9fa736b2c949e6947e4f989b85aa60079d52f1c1b`, 194행)다. ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 코드·자료 모두 fixed `<100000`이다.

범위: routing 범위 `2aac..2ab8`, `270e..271c`, `4fcce..4fd0a`, `4fd58..4fda6`. block 시작 **17개**(boot 진입 `2aac`, idle callback `270e` `2716` `271a`, stage controller fade 자식 `4fcce` 13개). 묶인 분기 6(`2712` + `4fcea` `4fd5a` `4fd78` `4fd80` `4fd88`). `2ab2`는 참조 없는 `2aac` block 내부 PC다. 디스패처 루프 `2ab8..2ac6`과 자기 삭제 `2a00..2a06`은 이미 fade_card에, `2a28`(node 설치)은 cleanup 실행부에 있어 파일을 옮기지 않았다.

### 메인 결정 (계약 머리말 기준)

1. 새 block 4개와 `4fcce` 자식(13 block)을 함께 `engine/src/animation_machine_scheduler.cpp`에 둔다(선택 B 포함).
2. **프레임 패스(선택 A).** PC=`2ac2`, A6=`1008e4`에서 시작해 실제 node 목록(자식 삽입·삭제 포함)을 따라 frame head callback LONG `(100820)`(`e4a`/`e74`)에서 stop한다. 실행부가 없는 node가 하나라도 있으면 패스 전체를 rollback한다. F1 직접 재진입은 패스의 `100b30` 구간과 같은 상태 변화이므로 F1a~F1c 검증은 부분 구간 검증으로 유효하다.
3. frame head `e74`와 controller `c66a`는 선언 효과 없이 건너뛴다(생략되는 원본 효과 목록은 계약 결정 3).
4. 디스패처 수준 A7 SPd=`1ff000`(work RAM `10f000`의 64 KiB mirror, 같은 물리 RAM)으로 선언하고 첫 패스 전에 LONG `104ca4`=SPd를 선언 쓰기한다.
5. 순서는 F3a, F2(+`4fcce`), F3b.
6. 관측 도구 `tools/observe_animation_machine_scheduler.py`를 새로 두고 F3 node 단위 seed도 만든다.

### 계약 정정과 관측 수치 우선 (쓰기 보호 ROM)

- **계약의 탐침 수치는 쓰기 가능 ROM으로 매핑한 작업자 scratch 결과이며, 쓰기 보호 ROM 관측 수치로 대체된다.** 원본 프로그램 ROM은 쓰기 불가이므로 관측 도구는 ROM 쓰기를 guard로 센다. 이 차이로 계약의 "142 seed 중 134개가 120 frame 완주"는 **91개**다. 51 seed가 일찍 멈추며 분류는 ROM 쓰기 41(초기화되지 않은 링 포인터로 RNG `49a58`이 ROM에 씀), 미지원 bank 매핑 2, BIOS 경계 2, 홀수 PC 1, fetch 비매핑 5다. 계약의 `270e` 실행 70,154회(static 69,638 + zombie 516)는 47,886회(static 47,886 + zombie 0)로, F3 node 실행(`e9150` 134, `e9176` 11,358, `e9350` 14, `e9362` 662)은 (134, 7,799, 10, 364)로 낮아진다. `100da8` 간격(`f0`) 등 일부 세부 수치도 관측과 달랐다고 메인 기록에 있으나 계약 값과의 정확한 대응은 [U]다. 이 항목들은 이 리뷰의 관측 수치가 우선한다.
- 같은 이유로 F3a 문서(`0253`)와 F3b 문서(`0254`)의 계약 수치도 관측 수치를 따른다.
- 자연 zombie는 0회다. 계약의 "pool zombie 516회"는 사라졌고 `2716`(zombie 방문 증가)은 typed fixture로만 닿는다. 관측에서 zombie는 typed로만 나타났다.
- 패스 가능 seed: **완전히 실행 가능한 seed 22개를 확인했다**(계약의 "8개 + `4fcce` 14개 = 22"와 같다). 6 seed(100 101 106 107 110 111)는 기록 400 frame 전체를, 나머지 16 seed는 기록 마지막 패스의 BIOS `c00468` 경계까지(2 seed는 240 frame, 14 seed는 244 frame) 완주한다.
- `MOVEM.W D3-D4,(A4)`(`4fd8c`)의 port 표기. C++는 `3c0000` size 4 한 건, native는 WORD 두 건(`3c0000` `3c0002`)이다. map_transfer 관례에 따라 검증기는 `4fcce`/`4fcda` node에서만 둘을 대응시켜 digest를 비교한다(차이가 아니라 기록 규약).

## 메인 리뷰

1. [F] 완주 패스 6,296개(22 seed)는 시작·끝 digest, 순서 port digest, 패스 전체 = node 연쇄 바이트가 모두 일치한다. dump frame 6,296은 RAM 바이트까지 일치하고 node 구간 89,850 중 종료 digest 38,629, 진입 digest 38,765가 일치한다.
2. [F] carry. 단일 block 탐침(C Unknown/Clear/Set)에서 FLOW_ONLY는 `271a`와 `4fda4`뿐이다(둘 다 RTS만). `4fda4`는 F2 WIP의 `carry_preserving_pc`에 추가해(주석 포함) 넣었고, 정적 감사로 ROM 명령에서 도출한 FLOW 집합과 C++ 표가 일치함을 확인했다. 나머지 15 block은 Unknown이다. 소비 block은 없다.
3. [F] 136 seed는 C++에서 패스 전체가 checked error다(상태 보존). 오류는 대부분 `unsupported animation machine PC`(실행부 없는 callback)다. 예외는 `deadbeef` guard 5(`animation fade card odd JSR target`)와 홀수 `47c05` 1(`unaligned animation machine PC`). frame 0 'node' 종류 실패 104 seed는 모두 native에서도 실행부 없는 callback이다(`b4d7e` 10, `e5120` 11 등). 최초 callback에서 rollback하는 seed 수는 `dbdb6` 13, `b4d7e` 12, `e5120` 11, `b631c` `be8a4` `f1a0e` `f1a4e` 각 4 등이다. BIOS `c00468` 경계 18 seed는 C++도 같은 partial node(`48090` 16, `47af0` 2)에서 멈춘다.
4. [F] `4fcce` 13 block 전부가 자연 node에서 도달한다. `4fcda`의 `7a(A6)` 변형 20개를 독립 native replay와 비교해 RAM·16R·PC·bank·순서 port가 일치한다. 형제 변형 `4fd0a`/`4fd20`은 자연 seed가 없고 범위 밖이라 거부한다.
5. [F] typed fixture: native 18 중 15 실행(`270e` 4 + boot 2 + pass 9, pass 1개는 host 규칙 기록만). f3-child 3개는 F3b 경계라 제외했다. `pass-gate-wait-released`는 `47af0`에서 Waiting하고 선언 해제 뒤 완주한다. `104ca4` 불일치 음성은 `program bus write requires RAM mirror units`다.
6. [I] `104ca2`(zombie 방문 수)의 소비자는 [U]이며, 선언 skip에서는 패스마다 누적된다.

## 검증 결과

- Native: 142 seed(자연 137 + release guard 5), 패스 14,715 중 완주 14,648, node 방문 130,135, fixture 18, 모델 비교 66,188 일치. 관측 SHA `c330e597f9585c2595006239be49ab0bcb029f4b5fed5c70ebf872fe91a2b4ff`(두 번 같음), observer 도구 SHA `62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c`, 산출물 약 206 MB(git 제외). 같은 도구가 F3 node seed 9,987개(dump 509)를 만들었고 replay가 9,987 / 9,987 일치한다.
- C++ 비교(detached worktree `metalslug-vf2`, 커밋 `55261ac`): 22 seed에서 기록 패스 14,715 중 C++ 완주 6,296 일치. 오류를 기록한 136 seed(앞선 22 seed 중 16개 포함)의 기록 패스 8,419개(첫 실패 패스 포함)는 C++ 비교 대상이 아니다(실패 이전 node는 기록과 일치). API 음성 177건(내부 PC 65 `unsupported animation scheduler PC`, 홀수 82(+3) `unaligned animation machine PC`, 범위 이웃·`4fd0a` 형제 변형·범위 밖 20 `unsupported animation machine PC`, 홀수 operand 5, 홀수 stop 1, `4fd8c` 홀수 video 포인터 1 등, 상태 보존), zero-step 17 start × 3 carry = 51건. 보고서 `verification.json` SHA `ddc29c669a3b9fc6c1ec7d8498d4a1fd1bd29566efe07f779a1f2ec799750d3b`(두 번 같음), 검증기 `tools/verify_animation_machine_scheduler.py` SHA `fadbf5002be4387ce6d342e21947cbcdfeb01bd6491df1dfdbf6ec5d9ffe2a5a`, 실행 기록 `docs/analysis/animation-machine-scheduler-execution.md`(SHA `112d840e1ef7f4b171652e5cab6272c1fca1cfd1f85bed127ac28dfef5aecb56`).
- core `engine/src/animation_machine_scheduler.cpp` SHA `1deb3bcc13ed13b061d0d1d0e5980653f5a0c271f14a54d002fb07ef2e87b587`(85행), unit `engine/tests/animation_machine_scheduler_test.cpp` SHA `adefcf7dc22f451cc7ba260e564791239bb573a1f933c6c45e3f3871234c8ee9`(382행), 라우팅 `engine/src/animation_machine.cpp` SHA `90ac84f0a1e6f720d78ef772d10e6b4729b86a8c992bd6a729385685afcfa5b7`. `make -j4 all test` 종료 코드 0. 단위 시험 fixture 수는 [U] 확인하지 못했다.
- 기존 시험 수정(WIP 커밋에 포함): `animation_machine_fade_card_test.cpp`의 `outside[]`에서 `2aac` `2ab2`를 `5f038` `5f03a`로 바꿨고, `animation_machine_card_menu_nested_test.cpp`는 재진입이 `270e`를 실행하도록 기대를 바꿨다.
- 이전 검증기 경계 이동(정렬 커밋에 기록, 수정하지 않음): `tools/verify_animation_machine_fade_card.py` 472행 `dispatcher_entry_2aac_unsupported`(`2aac`가 block 시작이 되어 기대 무효). 메인 트리 `engine/tests/animation_machine_fade_card_test.cpp` 135행 `outside[]`도 같은 이유로 갱신이 필요하다(vf2 worktree의 시험에는 이미 반영됨).

## 남은 제약

선언 프레임 모델이며 BIOS 실행·자연 IRQ·자연 scheduler 진행은 주장하지 않는다. 프레임 머리 `e4a`/`e74`와 controller `c52a`/`c66a` 본문은 실행하지 않는다(F5 범위). 완주 22 seed 외의 seed는 첫 callback 실행부가 생길 때까지 패스 전체를 검증하지 못한다(`dbdb6` `b4d7e` `e5120` 등 long tail callback은 다른 단위). Waiting은 typed fixture(`47af0`)만 실행하며 자연 seed의 Waiting은 0건이다(sound `3aea`, sprite `cda4` 미실행). 자연 SPd와 boot 직후 첫 frame 상태, 선언 skip이 생략하는 `e74` `c66a` 효과의 영향 크기, frame head의 자식, `104ca2`의 소비자, `4fd0a`/`4fd20` fade-out 변형의 실제 사용 경로는 [U]다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다. 직접 플레이·전체 Goal은 미완료다.

## 통합 전 독립 감사 보정 (2026-10-11)
원래 단위 보고서의 142개 자연 seed 중 22개는 하나 이상의 C++ 패스를 완료했고, 136개는 이후 또는 첫 패스에서 오류를 기록했다. 두 집합은 16개가 겹친다(22 + 136 - 16 = 142). 오류 없이 기록된 400프레임을 완료한 seed는 6개다. 22개 모두의 전체 지평 완주로 해석하지 않는다. 이후 F4 통합 결과는 별도 통합 검증 보고서로 구분한다.
