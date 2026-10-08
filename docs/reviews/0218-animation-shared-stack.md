# 0218 — 공유 RAM stack primitive와 원본 호출 근거

Baseline `68bd083`, branch `codex/animation-shared-stack`. 이전 전체 프로그램 리소스 통합은 progress로 승계했다. 이번 단위는 whole49fc6에 실제 stack을 연결하기 위한 C++ 기반과 원본 증거를 추가한다. Whole40 C++ 통합 완료나 애니메이션 완료 수 증가를 선언하지 않는다.

## 변경과 리뷰

`program_stack.h/.cpp`는 기존 program bus 위에서 BYTE/WORD/LONG push/pop을 제공한다. BYTE는 A7을2만큼 바꾸되 한 BYTE만 접근하며 padding을 보존한다. Pop은 live bus memory를 읽고, 접근 성공 후에만 SP/값을 commit한다. 실패 시 원래 RAM/SP/출력을 유지한다. MOVEM 순서, JSR/RTS target 및 여러 접근의 transaction은 상위 실행기의 책임이다.

메인은 실제 구현·unit·검증기와 기존 callee 소스를 읽고 수용했다. 독립 Sol 리뷰에서 계산 결함은 없었고 추가 UBSan probe로 bus1fffff BYTE 접근이 bank 쪽 padding을 건드리지 않음을 확인했다. Callers가 서로 다른 A7/value 출력 변수를 제공해야 한다는 계약도 명시했다.

검증기 리뷰에서 재현성 보강2개를 적용했다. 재실행이 실패했을 때 이전 성공 보고서가 남지 않도록 시작 시 삭제하며, 실행 전13개 입력의 해시를 저장하고 publish 전에 다시 확인한다. 수정 뒤110성공/14거절 결과는 이전과 같았다.

## Stack primitive 검증

- `make all test` exit0: Python257, C++실행148, 경고0. 새 helper의 standalone normal/UBSan도 통과했다.
- `verify_program_stack.py`는 synthetic M68000 명령6개를110조건에서 각각 fresh process/CPU2회 실행했다.16 RAM mirror, BYTE padding·odd SP, mirror 내부 경계, 명시적 입력 변경과 bank ROM pop을 포함한다. 실제 helper를 호출한 별도 C++ harness의 전체RAM/SP/값이 native와 일치했다. BYTE/WORD pop에서 D0 상위 비트가 유지되는 CPU 동작은 zero-extended helper 반환값과 구분했다.
- C++ checked 오류14조건은 native fault와 동일하다고 주장하지 않는다. Late LONG 실패와 잘못된 크기·RAM·장치 접근에서 SP/값/RAM 보존을 확인했다. High logical 주소의 자동24bit mask는 이 backend가 제공하지 않으므로 native 비교에서 제외하고 기존 bus/helper unit의 범위와 구분했다.
- 최종 verifier source SHA `18f5bac67fab804a99dfcc5541370aff57b7bf2ef6fc0f6d03b75b930117dfeb`, report SHA `494cbfcc321c2a643ffabd1963be54953cfb33413a510b5134c5102627fe4bbc`. 메인과 독립 Sol이485개 고유 참조 해시를 확인했다. 독립 Sol은 대표17조건의 native 결과를 별도 재실행했다. ROM·whole frame·CCR·물리 bus cycle의 증거가 아니다.

## 원본 shared stack과 설계

메인은 stack inventory의68개 명령과 별도6개 분기의 raw bytes를 canonical ROM과 비교했다.67개 PC witness/26개 고유 trace의 현재 해시·실제 pcs도 확인했다.1개 cd56 RTS는 해당 관측군에서 정적 근거만 있다. 정적 목록을 새 실행 증거로 취급하지 않는다.

새 observer는 원본49fc6와 caller return을 실제64KiB RAM backing/16mirror에서 실행한다. 별도 scratch stack을 쓰지 않는다. Callback14/03, direct30 early return, indexed10 skip, direct04 sentinel 뒤40이 S−8/S−4를 읽는8조건을 기록한다. 추가 high-wait 연쇄는 같은 CPU를 재개하면서 호출 사이에 canonical RAM의 saved low BYTE·outer A0와 queue head만 바꾼다. 코드 patch나 실행 중 register 주입은 없다.

메인 리뷰에서 SR API 읽기가 wait 사이의 lazy flag에 개입할 가능성을 발견해 제거하도록 했다. 새 관측에는 initial SR 설정만 필요하며, 레지스터 결과에 SR 값을 넣거나 continuation 사이에 읽을 필요가 없다. 이는 C++ 계산 오류가 아닌 관측 개입 제거다. 기존 scratch-stack 보고서의 범위는 변경하지 않는다.

수정 후8비대기조건과1대기연쇄(2단계)를 각각 fresh CPU에서 두 번 실행했다. 총18CPU/20단계이며 전체RAM event replay·16mirror 일관성·원본 불변을 확인했다.14의 S−8/S−4는106006/102026,30은102026/106004,10 skip은104800/10600c,04 sentinel은104800/4a108을 읽는다. 마지막4a108의 원본 명령 bytes도 여기서는 두 번째 LONG의 데이터다.

High wait는 실제3aea/A7=S−18에서 멈췄다. 호출 사이 saved low55→77, saved outer A0→104900, queue HEAD1→40을 canonical RAM에 반영했다. 같은 CPU의3c00이77을 읽고04/77을 enqueue했으며4a2ec가 새 A0를 복원했다.4a278은104900에106004와10600a를 순서대로 썼고40은104900을 통해106004를 읽었다. Padding은 유지됐다. 이는 host metadata만으로 복원하면 빠지는 live stack 효과의 직접 근거다.

최종 source SHA `3965fe15ec0852a454ed2005a3f0fd88bab34567d780336e5bfd1c44201af371`, report SHA `43a6627828fa9047ba1b3a89becc0731c1f19e38aa2f1f2dd8f4f9e098cb94cc`. 메인이 입력11/산출물60의71고유파일 해시를 확인했다. 수정 전5395d8be 보고서는 SR 읽기를 포함한 이전 결과로 대체됐다. PVC는 실제 native 쓰기를 기록하고 별도 pinned 모델로 bank를 계산했다. 이 fixture의 완전한 쓰기 쌍은 모두 bank2로 돌아오며 PVC read가 없으므로 일반 PVC 읽기 부수효과 구현을 주장하지 않는다.

독립 Sol도 최종 source의8조건과 same-CPU 대기 연쇄를 모두 재실행했다. 전체 incoming/outgoing·근거·검사와60개 payload가 보고서와 일치했고71참조와 backend library/wrapper 해시를 전후 확인했다. ROM hash/mtime와 기존 source/report는 변하지 않았다. 메인이 이 source·diff·독립 검증을 리뷰한 범위에서 이번 기반 단위를 수용한다.

설계 문서는 machine state의 A7/PC, caller가 제공하는 return LONG, live RAM 복원, 임시 frame/dead bytes, 원래 push-before-fetch 순서, PVC와 invocation transaction의 권위를 정한다. 기존 metadata API는 역사적 증거 재현용으로 구분하고 최종 엔진은 shared-stack 경로로 전환한다. A7만 추가하거나 stack RAM diff를 mask하는 방식은 채택하지 않는다.

## 재현과 남은 작업

```sh
make all test
.venv/bin/python tools/verify_program_stack.py
.venv/bin/python tools/observe_animation_shared_stack.py
```

Sol6.1/medium 세 작업자가 stack 목록·helper/검증기, 원본 관측, 통합 영향 감사·교차 리뷰를 담당했다. 메인은 원본 의미·상태/transaction 설계·실제 source 리뷰·수정·통합을 담당했다. 내부 최대3명을 유지했고 이 독립 작업 범위에서는 외부 작업자를 추가하지 않았다.

다음은 새 machine 경로에 기존 animation/callee와40을 연결하고 모든 지원 wait·hold·release의16register/PC·전체RAM·PVC를 비교하는 작업이다. Script/queue/shadow alias, 변경된 return dispatch와 A5/mirror 제약도 후속 범위에 포함한다.17명령 중14종+14/3c 일부와 전체 Goal active·기존 완료 기준을 유지한다.
