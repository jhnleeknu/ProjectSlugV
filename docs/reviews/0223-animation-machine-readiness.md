# 0223 — Readiness의 실제 호출과 상위 carry 분기

Baseline `93b5b40`, branch `codex/animation-machine-readiness`. 이전 활성화 갈래 통합을 진척으로 승계하고 목표 파일·현재 소스·원본을 다시 확인했다. 전체 목표와 완료 기준은 유지한다.

## 변경과 판단

새 `animation_machine_readiness.cpp`가4847c와1bdde/289e/4dee2/4e166을 실제 JSR/RTS로 연결한다.47d20 BRA와47d3e JSR 이후47d42의 원본 BCC가 Clear이면47d72,Set이면47d46으로 간다. 두 successor 자체의 실행은 아직 지원하지 않는다.

메인은 원본 명령·실제 diff·589회 API 검사·native observer와 C++ 비교기를 읽었다. CALL 직후 live operand를 읽는 순서, 상위 비트·WORD 폭,80개의 C 보존 block 중 새22곳, 실제 writer와 직접 RTS의 구분, 실패 시 모든 출력 보존을 검토했다.4e166의 반환 C는 mask 값과 같지 않으므로 Unknown으로 유지한다. 상위 TST는 C를 소비하지 않는다. 상세 의미는 `animation-machine-readiness-contract.md`를 따른다.

스택 겹침을 final 분기까지 관측했다. Direct1bdde에서 A5=206340, A0=1feff8, 초기 marker270e를 놓고 bit4=0/flag61 bit7=1로 시작한다. 실제 JSR289e가 marker를 복귀주소1bdf4로 덮는다.289e가 새 marker를 읽고,1bdde가 flag61을 읽어 Clear로 반환해47d72로 간다. Stack 쓰기를 생략하면 초기 inactive marker를 읽어 Set으로 반환하는 다른 동작이 된다. 원본 stack 차이를 가리거나 marker를 미리 고친 비교를 하지 않았다.

Canonical BE 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이번 fixed CPU 주소는 같은 파일 offset이다. 기존8개 MS5D kind3를 실제 C++ loader/bus로 계속 사용한다. 원본·리소스 규격은 변경하지 않았다.

## 검증

- 신규589회 API 검사 normal/UBSan 통과. 직접 RTS·JSR·BCC·BTST의 C 보존, Unknown 소비 오류, writer/record80조건, 상위392개 조합, 실제 stack bytes·marker alias와 실패 보존을 확인했다.
- `make all test` exit0: Python257개, C++154개 실행, 경고0. 로그 `/tmp/ms5-animation-readiness-make.log`.
- Native68조건, split154단계와 별도 fresh continuous86단계를 각2회 실행했다.272 CPU/480단계이며 Clear40조건·Set28조건이다.18개 wait 단계의 C는 미관측(null)이다.
- 실제 C++68조건154단계와 직전 실제출력86회 재개가 일치했다. Full64KiB RAM·16R/PC·carry·상태와 독립 장치 모델·ordered ports·읽기 수를 비교했다. C는 SR을 읽지 않고 실제47d42 BCC successor에서 도출한다. Stop/resume 없는 continuous control도 일치했다.
- Checked 오류14조건, 유효한 zero-step3조건 통과. 별도 C++ 전용47cae 입력은 consumer WORD만 명시적으로 바꿔 wait를 해제하고, 먼저47d42까지 성공하며 RAM/ports가 변하는 것을 확인했다. 같은 초기 입력에서 stop을 지원 범위 밖으로 바꾼 호출은 모든 출력을 보존했다. 이 추가 control은 원본과 비교한68조건에 합치지 않는다.
- 독립 Sol이43조건/split104단계·continuous61단계를 재실행했다. 모든18wait 재개와 mixed 활성화 경로, operand/stack alias 및 실제 분기 결과를 확인했다. Native1916개 입력·산출물 참조와1848개 phase 참조,68개 fixture metadata가 일치했다. 메인도1916개 현재 파일 해시를 확인했다.

독립 Sol의 core·unit·비교기 리뷰에서도 추가 결함은 없었다. 메인과 독립 작업자가 최종 C++ 보고서의60입력+2961산출물 참조를 정규화한2976개 파일의 해시를 확인했다. 실제 C++ 비교의 포트 수는126, 외부읽기는0이며 별도 C++ 전용 성공 control의42포트는 이 수치에 합치지 않는다.

## 검토 중 수정과 남은 범위

Late JSR stack 쓰기 거부의 예상 오류 문구를 실제 helper의 `program bus write requires RAM mirror units`로 수정하고 비교기를 다시 실행했다. Core 동작 불일치는 없었다. 첫 실패 때 이전 성공 report가 남지 않은 것도 확인했다. 비교기는 모든 실패의 상태 보존을 최종 실행에서 검사했다.

기존 caller 오류 보고서의 `unmodeled_caller_return` 필드는 이제 지원하는47d20을 미구현으로 잘못 설명했다. 이를 `original_caller_return`으로만 바꾸고, 기존 stop/error/state 보존 검사는 유지했다. 이 도구 소스를 입력으로 pin하는 caller/carry/activation/readiness 네 보고서를 다시 생성했다. 해당 소스를 참조하지 않는 기본 machine 보고서는 불필요하게 반복하지 않았다.

실제 자연 scheduler 도달,47d46/47d72 이후 frame·전환, 앞선 HUD/BCD, IRQ/timing·일반 CCR/XNZV·물리 기판·전체 stage/직접플레이·적/보스·미사용 자료 전체 의미는 미완료다. Standalone helper의47d42 return은 명시적인 통제 adapter다. Guard 코드 검토를 모든 오류 경로의 native 실행 검증으로 확대하지 않는다.

전체 애니메이션17명령 중14종+14/3c 일부 집계와 전체복원율 미산정, Goal active를 유지한다. 원격이 없어 소스·도구·규격·분석·리뷰만 로컬 커밋하며 ROM/추출물/artifacts는 제외한다. 재현·최종 해시는 `animation-machine-readiness-execution.md`를 따른다.

## 최종 회귀와 식별

기본 machine94fixture/131단계·37재개/9오류, caller59조건91단계·32재개/6오류, carry60조건160단계·100재개/10오류 및 zero-step3조건, activation52조건74단계·22재개/9오류가 모두 통과했다. 메인이 다섯 보고서의1708/1234/3043/1037/2976 고유 참조 파일을 확인했으며 합집합9686개 해시가 일치했다. 독립 리뷰에서도 수정된 metadata key와 네 재생성 보고서의 현재 해시를 확인했다.

| 보고서 | 최종 SHA256 |
| --- | --- |
| readiness native | `a93d54a8b9001073a469795b70e00541ab5c9f09dcee9af9c2aa7b7393157ada` |
| readiness C++ | `a26fde94977d049b482e83721589adce71f6dfd8c5188a8a413dd072dde477bc` |
| machine 회귀 | `101cb4c586a32d64ed1960ca8e6fd2f40036fb72efcf31c988855a7bd949fc6c` |
| caller 회귀 | `d4ee15f9267d762a9c9f92ac68f97b9c6579496d743a837d8bf8e43354f435b4` |
| carry 회귀 | `125de83133bcaf29a3724eeb787d54841ae2a2203fb5730e923e726adf597802` |
| activation 회귀 | `de0906f83e9c10aae190d875f279d2b86cb2619065645497a99b556297bd00a7` |

새 native 파일을 stage한 뒤 발견한 빈 줄의 공백 한 곳도 제거했다. 원본 관측과 이를 pin하는 readiness 비교 보고서만 다시 생성했으며 동작·검증 수치는 같았다. 기존 네 회귀 보고서의 입력에는 해당 새 Python 소스가 없으므로 그 결과는 유지했다.
