# 메인 초기화와 난수 상태 복원 리뷰

Baseline `e8bb9c9`. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이 e4a/e7bf4/8da2/8e82 및49a1a/49a58/49a84의 원본 명령과 자료구조를 해석하고 계약을 확정했다. sol 세 에이전트에 각각 코어·CLI·테스트, 원본 비교, 추출 도구를 맡겼다. 추출 완료 에이전트는 이어 난수 구현·검증을 맡았다. 메인이 전체 diff와 최종 보고서를 검토했다.

## 주요 판단

8da2는 source bucket의 tail이 아니라 sentinel+2의 head를 비교하고 선두에 삽입한다. 고정 참조 해제는 free ring의 tail에 붙이며 D3.low에는 실제 읽은 링크 값이 남는다. sourceffff는 disabled 슬롯이고 destinationffff만 종결자다. 이를 구분해 metadata는 보존하고 팔레트ffff 추출은 제외했다. MS5D는 새 포맷 없이 기존 kind1을 사용하며104바이트 테이블만 담는다. sparse MS5P는22→29 ID로 늘었다.

initialize_main_frame은 이 등록과 slot6 blend, object/controller 초기화를 순서대로 수행한다. 실패 시 모든 출력이 보존된다. e7bf4 부분은 private helper로 분리했다. 최종 D0=0/D1.low=1 및 high 보존, D3의 마지막 실제 목록 이동값을 원본과 비교한다. API는e74에서 끝나며 기존 준비 단계에 RAM/D1/D3를 넘긴다.

난수 seed는 비영 D0.low를 직접 seed로 사용하지 않고 RAMf02c를 증가시킨다. 55word 생성의 word 덧셈·unsigned 제곱·전체 EXG를 구현했다. next는 변경할 target word가 아니라 원래 cursor word를 반환한다. scale은 product의 양쪽word를 SWAP하므로 상위word도 반환 계약에 포함한다. 정수 연산은 unsigned 비트폭을 사용하며 잘못된 cursor는 변경 전에 거부한다.

## 검증

startup verifier session76027 exit0: 209조건, watchdog418포트, 오류32조건. 실제 native3ef2/e7bf4/8ebe fixture와 다섯3호출 CLI 상태 승계를 사용했다. 일반 참조 비대상 슬롯 보존111조건 포함. startup→준비2조건은 동일한 native context와 실제 CLI 반환을 연결하여 추가24포트/영상2읽기 일치. SHA256 `2bf5387682dae840040749fb882917080a43ecedb22a1dd13766ca123cccea7a`.

난수 최종 verifier는1,690조건(seed110/next460/scale1120), 오류26조건 통과. 최초1,469조건 통과 뒤 메인이 연속scale의 limit가0으로 줄어드는 검증 약점을 지적했다. 별도seed와 고정limitffff의220호출을 추가해 네 wrap/220비영 결과를 확인했다. 기존480호출 전체 레지스터 승계도 유지한다. 최종 SHA256 `886e457b96b4ea5c9655c432d208eeca198e840a42c29a6a119d92d6c57308ff`. 원본 ROM은 변경하지 않았다.

`make -j3 all test` session80356 exit0: Python81개 및 C++전체 검사 통과, 경고 없음. 로그 `artifacts/main_startup_random_build_test.log`. 이후 변경은 Python verifier 강화와 문서뿐이며 C++ 재빌드는 필요하지 않았다. 메인이 두 보고서의 실제 집계·해시와 추출 metadata를 확인했다.

## 남은 범위

실제 BIOS 부팅/스케줄러 및 전체 게임 실행을 검증한 것은 아니다. 다음 초기 노드c52a→c560의 palette fill 대기와 IRQ 해제, 이어지는c56e의 e7bf4/49a1a/47570 호출을 연결해야 한다. 이번 난수 함수는 독립 실행 API이며 자연 호출자와의 연결은 아직 없다. CPU의 모든scratch/CCR/물리시간과 전체 스테이지·전투·사운드 복원은 진행 중이다.
