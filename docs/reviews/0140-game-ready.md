# c654 준비 제어 경계 통합 리뷰

Baseline `e3f389e`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이 원본 c654..c6ce 명령과 C++ core/header/CLI/unit, Makefile 및 native verifier를 직접 대조했다. sol에 구현, 검증, 목록화와 문서 작성을 분담했다.

## 계약과 리뷰

c654의 고정100b30 restart 이후 D0 전체0, D1/D3 helper 반환값 및 현재 A6 callback을 승계한다. c66a는 callback0도 active로 판단하며 replay byte가 정확히1인 경우만 c724로 간다. 나머지는 canonical ROM180.word=0 경로의 제거→화면 reset→flag→allocator를 실행한다. D0.low만0으로 만들고 정상 allocation 실패도 무시하는 원본 순서를 확인했다. 제거가 반환한 live A6를 후속 쓰기에 사용한다.

c6c0의 종료는 c73e 또는 BIOS c00444이며 해당 명령은 실행하지 않는다. 설치한477e4/e66aa callback도 실행하지 않는다. API는 RAM/state/ports 전체를 복사 후 성공할 때 교체하므로 late pointer 오류에도 이전 결과를 보존한다. CLI는 unsigned32 범위와 입력/출력 alias를 검사한다. 파일 저장 중 I/O 실패의 다중 파일 원자성은 API transaction 계약에 포함하지 않는다.

## 검증

원본246조건과 오류39조건, 순서 있는 포트274484개가 일치했다. 보고서 SHA256 `4f09a7ef5db74efe5b5ab29bf8a4646cf9cb49145dc5c05a2508e0dcffc1fe17`. 실제2790/MS5I list와3ef2/8ebe palette 상태, 실제 controller1008e4 및 sentinel100820을 사용한다. callback0/270e/다른값, mode0/1/2/ff, 정상 allocation 실패와 사용하지 않는 잘못된 freehead, 좌표와 공유 팔레트 정리를 포함한다. 세 실제 종료 경계와 필요한 중첩 호출 도달도 assert한다.

4승계시퀀스 중2개는 실제 restart CLI 출력과 원본c610 반환 RAM/전체D0D1D3A6를 비교한 다음 c654에 넘긴다. 다른2개는 실제 CLI RAM/register를 재사용하지만 +62 flag는 호스트가 변경한다. 자연 scheduler나 e66aa 실행을 검증한 것으로 확대하지 않는다. BIOS page는 경계의 instruction hook을 받기 위해 매핑하고 경계 실행 전에 중단한다. 원본 프로그램은 변경하지 않는다.

`make -j3 all test` session36063 exit0. Python88검사와 C++86 test executable 통과, 경고·오류0. 메인은 로그와 최종 보고서 수치 및 verifier 비교 대상도 확인했다. 이번 리뷰에서 core 변경이 필요한 불일치는 발견하지 않았다.

Makefile 리뷰에서는 새 테스트와 이전 테스트들이 `build/tile_resource_test`의 무관한 선행 대상으로 누적된 것을 발견했다. 간접 빌드 덕분에 검사는 실행됐지만 타일 코드 변경과 관계없는 재빌드를 유발하는 구조다. 해당11개 테스트를 `test`의 직접 선행 대상으로 옮겼다. 수정 후 `make -j3 all test` exit0, Python88검사와 C++86개 실행 통과, 경고·오류0을 다시 확인했다. 최종 로그는 `artifacts/game_ready_build_test.log`다.

## 다음 단계

477e4→1a5a4 초기화를 조사했다. 별도 목록화의111명령후보/23호출/17helper는 분석 범위 안내이며 완료 증거가 아니다. 메인은17292의2048연속 long store를 원시 바이트로 확인했고1a7a8의 후속 호출 및1afda의 입력 flag 분기를 확인했다. 기존43e38/43ea8 RAM 효과 API는 재사용 후보지만 scratch 레지스터 계약을 추가로 분석해야 한다. BIOS, 실제 callback 본문, 자연 scheduler와 전체 게임 복원은 남아 있으며 전체 목표는 진행 중이다.
