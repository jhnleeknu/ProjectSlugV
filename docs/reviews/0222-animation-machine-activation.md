# 0222 — Stage 활성화 출력 경로의 공유 stack 연결

Baseline `6c90612`, branch `codex/animation-machine-activation`. 이전 carry 단위를 진척으로 승계했다. 목표 파일·현재 Git·기존 분석과 실제 ROM을 다시 확인했다. 전체 목표와 완료 기준은 변경하지 않았다.

## 변경과 원본 의미 검토

`16ea4` 좌표 wrapper와 `16ed2` signed 비교/bit2 helper를 기존 machine에 추가하고 실제 `47cae..47cec`를 연결했다. 이제 이 갈래의 좌표 설정→16ed2→47672 sound→16ea4/cd58 sprite→기존49f8c/49fc6 animation이 같은16R/PC/A7와 RAM을 사용한다. 원본 `16ecc`는 tail JMP이므로 새 return slot을 만들지 않고, 세 caller JSR는 각각47cc6/47cca/47cec를 실제 stack에 쓴다.

메인은 원본 bytes와 C++ diff·새 unit·observer·검증기를 직접 검토했다. WORD modulo 연산, LSR가 넘긴 X와 ADD carry의 구별, D2/D5 상위 비트 보존, signed 비교, live read/write 순서, 실제 RTS와 transaction을 확인했다. `47cca`의 BYTE index는 raw LONG span48a12..48e12를 읽는다. 논리적256항목 table 전체를 해석했다고 주장하지 않는다. 세 JSR는 C를 보존하고 나머지 새 block은 Unknown이며 일반 CCR을 확장하지 않았다.

Canonical BE 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이번 fixed CPU 주소는 같은 ROM 파일 offset이다. 런타임은 기존8개 MS5D kind3를 실제 C++ loader/bus로 읽는다. 리소스 규격·ROM은 바꾸지 않았다.

## 실행 증거

- 새 unit6672회 API 검사 normal/UBSan 통과. 256flag×좌표경계·mirror, signed WORD 경계×256flag,256lookup index, 세 실제JSR, 전체 갈래, sprite wait/hold/release와 늦은 실패를 검사했다. 합성 lookup unit을 실제 ROM 증거와 구분한다.
- `make all test` exit0: Python257개/C++153개 실행, 경고0.
- Native52조건/74단계: standalone sprite25, signed helper11, 실제 activation chain16. 각각 fresh CPU2회로104 CPU/148단계. SameCPU 재개22회,636PVC포트,외부읽기0회다. ROM patch·SR 읽기·중간register 주입·stack 차이 mask 없이 fullRAM/16R/PC를 기록했다.
- C++ 비교기가 원본 전부 재실행 후52조건74단계와 실제출력22회 재개를 대조했다. Full64KiB RAM,16R/PC,status,장치모델PVC/bank,포트·외부읽기가 일치했다. Carry는 native 미관측이며 실제값 전달과 waitUnknown의 API 계약만 확인한다.
- 마지막 mixed 조건은 같은 CPU에서 sound high wait/hold→low wait/hold→sound release 및 wrapper wait→wrapper hold→wrapper release 및 animation wait→animation hold→최종 release의9단계다. 앞선 좌표 전처리/호출을 반복하지 않고 변경된 hostRAM·saved low BYTE를 실제 후속 읽기에 반영했다.
- 오류9조건은 홀수 WORD, 두 번째 읽기의 device 경계, 읽기 성공 후 ROM 쓰기 실패, MOVEM 세 번째 LONG의 경계 실패, 미지원 callback, 두 helper의 변경된 live return, 전체 갈래 이후 미지원 PC, 실제 조회 span만 누락한 kind3에서 모든 API 출력을 보존했다. 원본 exception rollback을 주장하지 않는다.
- 독립 Sol은33조건55단계와 모든22재개를 재실행해 payload/trace 전체가 일치함을 확인했다. Native510참조(65입력+445산출물),444phase참조와52fixture metadata도 확인했다. 메인이 native510 및 C++1036 고유 참조 해시를 별도로 확인했다.

독립 Sol의 C++ core·6672회 unit 구성·검증기 리뷰에서도 조치할 결함을 발견하지 못했다. 최종 비교기56입력+1023산출물 참조를 정규화한1036개 파일의 해시도 확인했다. 검증기는 prior actual C++ 출력을 전달하며 원본 기대 register를 재개 입력에 주입하지 않는다.

## 기존 회귀와 최종 보고서

기존 machine94fixture/131단계·37재개/9오류, caller59조건91단계·32재개/6오류, carry60조건160단계·100재개/10오류·zero-step3조건을 현재 core로 다시 통과했다. 기존 verifier 소스와 native 근거는 변경하지 않았다. 메인이 네 C++ 보고서의1707/1233/3042/1036 고유 참조를 재검사했고 합집합6795개 파일의 해시가 일치했다.

| 보고서 | SHA256 |
| --- | --- |
| activation native | `9244bfafbf4fe921ccbb8d293e5b713fa16f4fdc35b38246d851c7726fac8e61` |
| activation C++ | `de726ac51b78c06d33925d287298c71162984f7f334aa8579893b3bdc283433b` |
| machine 회귀 | `2a0851f7a88595e16d7f85df46483851ef6e9451033873dd97d1b716f4ea8cba` |
| caller 회귀 | `5f8638bc3cf76ac8197f957753926a03e34b3024b802a50672e6db5f97f7894f` |
| carry 회귀 | `a7182575f26b86101befee13b515bc32f2f634154854cf2a0e20e75ceee799f5` |

## 범위와 인수인계

Exact 의미는 `docs/analysis/animation-machine-activation-contract.md`, 재현·최종 report 해시는 `docs/analysis/animation-machine-activation-execution.md`를 따른다. Source/diff·실제결과를 리뷰하여 통합하며 ROM·추출물·artifacts는 Git에 넣지 않는다. 원격이 없어 로컬 리뷰·커밋으로 진행한다.

47c6c 이전/진입 조건, HUD/BCD,47d20 이후 readiness·frame 연결은 남아 있다. 물리 기판·일반 CCR·자연 IRQ/scheduler·전체 stage/직접플레이·적/보스·미사용 데이터 전체 의미는 미완료다. 애니메이션17명령 중14종+14/3c 일부 집계와 전체복원율 미산정, Goal active를 유지한다.
