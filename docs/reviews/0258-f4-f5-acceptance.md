# F4/F5 기존 구현 인수 보완 — 2026-10-14

대상 엔진은 `b8502bfaa8c6bebd6f02d79a9be46b16543cc289`이다. 작업 브랜치는 `codex/f4-f5-acceptance`다. 기존 주 단위의 비교 도구·회귀·출처 기록을 완성하는 작업이며, controller C1–C3, D1 전체 프레임 구동기 및 deferred b-unit의 새 구현은 포함하지 않는다. 전체 게임 Goal의 완료를 뜻하지 않는다.

## 검토한 변경

- 이전 검증기의 `deac` 기대값은 H8 범위 내부 PC의 정확한 오류로 정렬한다. 새로 실행 가능한 시작점으로 취급하지 않는다.
- `3902`는 H2의 원본 명령 실행과 이후 원본 경로의 실패를 확인한다. 오류 문구를 일괄 허용하지 않는다.
- G1/G2/RNG 비교는 현재 전체 C++ 소스·헤더, 실제 런타임 MS5D, 원본 관측 자료 및 도구를 실행 전후에 고정한다. G2 block probe에서 임의의 generic unsupported 오류를 허용하던 우회를 제거했다. 784 시작점의 probe 전용 실행은 모든 검사를 통과했다.
- G3는 기존 관측의 N03–N16a 비교 도구를 추가하고 실제 C++ 출력 사슬과 선언 상태 재진입을 구분한다.
- F5는 scratch 비교를 반복 실행 가능한 영속 harness로 옮기고 전체 RAM/PVC, 레지스터, 순서 있는 ports/waits/외부읽기 queue와 종료 상태를 검사한다.

## 직접 확인한 원본 의미

Canonical big-endian ROM SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
아래 CPU 주소는 고정 첫 1MiB 영역이며 canonical ROM 파일 오프셋과 같다.

- `710c6`: `2d400064` MOVE.L D0,64(A6), `710ca`: `4a80` TST.L D0, `710cc`: `6a000004` BPL 710d2. 현재 N15 C++와 계약의 개별 block 설명이 일치한다. 묶인 설명의 `710a0` TST.W/BEQ 문구를 `710c6`에도 붙인 관측기 문서 파싱 차이다.
- `494b4`: LEA 100cb8,A0, `494ba`: `003c0001` ORI.B #1,CCR, `494be`: RTS. `77604`의 `64000008` BCC 7760e는 반환 C 소비자다. N08 내부 소비자가 없다는 계약과 외부 호출자가 반환 C를 소비한다는 사실은 양립한다.

## 현재 실행 결과

RNG400 전체 실행은 종료 0이다. 자연 136개 완주, 선언 guard 5개 종료, 자연 seed141 홀수 PC 종료 1개다. 54,400 pass / 412,067 node가 일치했고 불일치는 0이다. answer00 변형 6개는 2,400 pass / 19,936 node가 일치했다. 보고서 SHA256 `b596175b1ac32264d70ce8a600143521c54ba2f9aaceb0fa3535cdbb27132a26`; 현재 입력과 갱신된 감사의 인수도 종료 0이다.

이는 head/controller를 생략한 선언 pass 모델이다. seed141은 앞선 node와 실패 node 진입 상태·동일 프레임 오류·rollback 확인이며, 실패 명령 이후 전체 native 예외 상태의 동등성은 주장하지 않는다.

G1 전체 재실행은 4,747행 중 원본 실행 일치 4,683, 검증된 경계 55, native step limit 8, 기존 선언 flag 전제 위반 1이다. U08b `4bc58`의 추가 fixture 4개가 모두 원본과 일치했다. 계약 본문에 이미 166 block과 분할 근거가 있었지만 목록 머리의 수만 165로 남아 있던 부분을 수정했다. 최초 실행은 이 문서 수 검증에서 실패했고, 수정 후 전체를 재실행해 종료 0 및 감사 인수를 확인했다.

G2는 자연 290 case / 14,320 node / 134,764 phase 전부 실제 출력 사슬로 일치했다(선언 재진입 0). Typed 1,215건은 정상 실행 795건 외 예상 오류·경계 및 원본에서 도달하지 않은 기록 2건을 포함한다. 110개의 24비트 주소 마스킹 차이는 native 모델 경계이며 실행 동등성으로 세지 않는다. 전체 checks 참, 종료 0; 보고서 SHA256 `5f0cb5b065197e969f9ad7b42c3da97f81876714231029af2f3f58270481c938`.

F5는 자연 4,975 + 변형 976 + 선언 파생 4,977 = 10,928개가 일치했다. 전체 H 기록 재현 5,953개, `e4a` 시작 320개 / `e74` 10,608개다. 자연·변형 stop은 `c52a`, 파생 stop은 `31d6`이다. 잘못된 결과·queue·실패 exit 검사 15개도 통과했다. 메인 리뷰에서 내부 헤더 pin 누락을 찾아 수정한 후 전체 재실행했으며 내부 헤더를 포함한 입력 8,735개가 전후 동일, 빌드 경고 0이다. 보고서 SHA256 `1a5423a79d1205354b9ffb3e3252a9b1a7d7e9061fc9b7343cad26e28866b1d0`. 원본 H 54,264개 전체의 C++ 실행이나 렌더링 결과 동등성을 주장하지 않는다.

두 F4 감사 도구는 현재 실행 중 기록한 전체 헤더 pin을 사용하므로 이전 sanitizer 산출물이 없어도 기본 경로로 인수할 수 있다. 역사적 block/pass 수 또는 오래된 내부 헤더 hash를 주입한 네 검사는 모두 종료 1이며 acceptance 파일을 만들지 않았다.

독립 검토에서 처음 추가한 pin 목록에 간접 loader·program manifest·live 계약 파일·외부 seed 원본·Unicorn/Capstone 라이브러리가 빠진 점을 찾았다. `acceptance_provenance.py`가 AST 기반 local import, 명시 데이터 파일/트리 구성, interpreter/compiler 및 두 native 라이브러리 패키지를 고정하도록 보완했다. G1/G2/RNG 전체를 다시 실행했고 같은 분류·동등 수 및 전후 불변을 확인했다. 위 SHA는 보완 후 최종 보고서다. G1 최종 보고서 SHA256은 `981950aa963530279c9b00cb69139369ed141fbbd6baec2d6d41b565c0633849`이다. G1 U01–U07 계약은 native Env 로드 시 원본 observer의 고정 SHA와 먼저 비교하며, 이후 실행 전후 목록도 검사한다.

변경하지 않은 엔진·Makefile 818개 파일은 앞 감사의 `b8502bf` 테스트 복사본과 바이트 단위로 동일하다. 그 버전의 C++ 시험 249개 통과 기록을 유지하고, 현재 worktree에서 Python 시험 257개도 다시 실행해 종료 0을 확인했다. 새 F5 C++ 하네스는 별도로 빌드·원본 비교했다.

G3 최종 전체 실행도 종료 0, `accepted=true`, 39개 checks 전부 참이다. 자연 30,632 node 중 실행 일치 30,630과 정확한 RNG guard 2개를 구분한다. 유닛 piece 133,378개, Known carry 112,306개에 불일치가 없다. Typed 2,459건은 실행 일치 1,572, 부분 일치 3, 명시적 caller-N 모순 제외 2 및 검증된 오류·경계로 분류한다. 2,203 block probe, 56,108 API 부정 호출, 비교기 오류 주입 9개와 출력 경로 부정 검사 4개도 통과했다. 보고서 SHA256 `2c2ac4ae6438eb86dc5286a351fea146832e73a4f1cfe4ffedc2b997a3c42419`의 입력·native·생성 소스·바이너리 SHA를 메인이 현재 파일과 다시 대조했다. N19 외부 carry 소비자에서의 선언 재진입과 native 주소 마스크 경계는 전체 실행 동등성으로 세지 않는다. 자세한 근거는 `0258-g3-independent.md`와 G3 실행 문서에 있다.

코드·도구 통합 커밋은 F5 `39c1fad`, 전체 provenance/G1/G2/RNG `c7f801d`, G3 `8352514`, 기존 검증기 기대값·원본 prefix 보완 `23779e0`다. 네 추가 guard 보완은 `668e142`에 저장했다. 기존 35개 회귀의 최종 인수 결과는 아래와 같다.


## 35개 회귀 중 발견한 추가 기대값 변경

전체 회귀에서 네 도구가 확장된 F5 실행 범위 이전의 기대값으로 실패했다. 원래 실패 실행의 receipt와 로그를 보존한다. 수정은 아래 해당 검사 함수와 그 검사에서만 부르는 보조 함수, scene-core의 기대값 한 개로 제한한다. 제품 엔진은 변경하지 않는다.

- 카드 메뉴 `guard-overflow-rts-unsupported-target`: CPU/파일 오프셋 `1000`의 `4e75 RTS`가 H1에서 지원된다. frozen guard의 전체 시작 `a0a0`와 실제 직전 C++ 출력 `a0c2`에서 원본을 다시 실행하면 `1000 → c2a8 → a2b8 → c2ba → a370`으로 진행한다. 두 시작 모두 RAM/PVC/16R/PC/bank/ordered ports가 C++와 같고 외부 read는 0이다. 기존 unsupported 기대를 이 원본 비교로 대체한다.
- Scene-core `guard-cond-index-negative-8000`: native target `122d4`는 H4 routine 2 cell 시작 `120c0`에서 +532 바이트(18바이트 cell 내부 offset 10)다. 정확한 오류는 `unsupported animation frame head h4 PC`이며 fresh archived phase와 전체 public rollback을 검사한다.
- Script-placement의 `3db2`는 H1에서 지원한다. 원본의 MOVEQ/BTST와 원래 스택 복귀 경로를 `ff000`까지 실행하여 16R/PC/RAM/ordered ports를 비교한다. 복귀 이후 PVC 쓰기 14회를 독립 장치 규칙으로 계산한 전체 8192바이트 PVC와 bank도 C++와 일치한다. native raw ff8/ff9 저장값과 장치의 masked 값은 다르므로 raw PVC 전체 일치로 주장하지 않는다. `3db4`는 H1 block 내부의 native 명령 주소로 정확한 H1 interior 오류를 기대한다.
- Stage-area의 `b481e`, `b4a2a`, `46f52`, `1bdde`는 기존 지원 경로에서 H1까지 이어진다. 원본과 C++를 `ea4`까지 비교하면 전체 상태와 순서 있는 port 쓰기 404개가 일치한다. 이후 원본의 첫 외부 읽기는 `eaa`에서 `3c0006` WORD다. 빈 queue에서 C++가 내는 정확한 오류와 전체 API rollback을 검사한다. 빈 queue를 원본 CPU 예외로 해석하지 않는다.

위 주소는 고정 ROM CPU 주소이며 파일 오프셋과 같다. 원본 SR 또는 실패 후 native 예외 상태 rollback 동등성은 주장하지 않는다.

517개 frozen source는 커밋 `23779e0`의 파일과 모두 동일함을 메인이 Git object와 직접 대조했다. 이 소스를 고정한 전체 실행은 31개 통과와 위 네 기대값 실패였고, 네 수정 도구의 공식 main 전체 재실행은 모두 종료 0이다. 최초 실패의 receipt·로그와 산출물 복사본(파일별 SHA/크기 inventory)을 보존했다. 카드 메뉴의 기존 산출물 48,903개도 재실행 뒤 같은 바이트로 유지됐다.

## 최종 인수

35개 표준 회귀를 인수한다. 실제 분류는 **24개 현재 input pin 일치 + 7개 제한된 변경 영향 검토 + 4개 수정 후 공식 전체 재실행**이다. 7개 과거 report의 whole-file pin은 수정하지 않았다. 독립 AST·호출·소스 내용 참조 검토에서 수정된 함수/값이 그 실행에 사용되지 않음을 확인했다. 이를 새 소스로 35개를 전부 재실행한 결과로 표현하지 않는다.

네 재실행은 card-menu 878.992초, scene-core 765.857초, script-placement 287.419초, stage-area 183.292초다. 모두 입력 해시가 전후 동일하고 기본 경로의 report와 보존 복사본 SHA도 같았다. 메인이 35개 보고서·로그·현재 입력을 다시 대조했으며 위 7개 검토 대상 외 pin 차이는 없었다. G1/G2/G3/RNG/F5의 출처 최종 확인도 28,318개 unique 파일의 해시·바이너리·생성 소스 검사를 통과했다. 생성 시점 source hash 필드가 없는 일부 하네스는 고정된 생성 규칙과 현재 파일을 비교했으며, 존재하지 않는 과거 compiler-time hash를 만들어 주장하지 않는다.

최종 목록과 SHA는 `0258-regression-manifest.json`, 독립 검토는 `0258-card-menu-delta-review.md`, 전체 실행 세부는 `0258-legacy-standard35.md`에 있다. 이번 작업은 기존 F4/F5 주 단위의 검증·인수 보완 완료다. D1 전체 프레임 연결, D9/C1–C3 controller, deferred b-unit·고아 사슬, 전체 화면·사운드 동등성 및 게임 전체 재구성은 여전히 남아 있다.
