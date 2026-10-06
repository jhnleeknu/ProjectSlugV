# 전체 메뉴 프레임 리뷰

대상: `bda8152` 이후 변경.

메인은 a370..a708과9430, a008, 3918, 9332를 직접 분석하고 상태기계와 호출 깊이를 구현했다. 확정된 D3 API 전파/9332 문자열 출력, CLI/오류 검사, 원본 반복 비교는 gpt-6.1-sol / medium 에이전트에 파일별로 분리 위임했다. 최종 코드와 verifier의 실제 실행 경로를 메인이 검토했다.

초기 구현 검토에서 중요한 두 가지를 반영했다. 첫째, native92f0은 전역 renderer9332를 설치한다. 단순3650 출력만 지원하면 실제 메뉴 출력 경로가 빠진다. 둘째, a008은 가림 후 전역renderer로 tail-call하므로 clipped 경로에서도9332를 지원해야 한다. 3918이D1을 복원하지 않는 점, covered glyph가 renderer를 전혀 호출하지 않는 점을 원본으로 확인하고 스타일 유지/operand 미소비/커서 정지를 구현·검사했다.

프레임은 헤더가 닫기 mode를 설정해도 pending과 입력을 계속 처리한다. pending은 callback 전에ff로 지우고, callback 후 저장한 current를 복원한다. 열기 완료event6/0 및 닫기event7/0은 원본과 다른 스택 깊이를 갖는다. 메인은 최종 report의 profile/event별 실측 A7 차이를 검토해4/8/24/28/32/36 바이트의 각 경로를 확인했다. 현재 API는 초기A1=전역renderer 계약을 명시한다. 다른 초기 A1까지 지원한다고 주장하지 않는다.

최초802프레임 검증 이후 메인 리뷰로9332의 연속 실행, header exit 이후 실제 입력, 정적 재시작/watchdog를 추가했다. 에이전트는 관찰된 상태에 도달하면 루프를 종료하게 하여 반복된 빈 프레임을 줄이고, area/group 확인의 sentinel→부모event7 종료 전달도 추가했다. 최종834프레임,10시퀀스,697stage콜백,155889포트가 원본과 일치했다. 시퀀스는 원본a29c와 C++초기화부터 전체 RAM/D3를 이어간다. BIOS는c00444에서 멈추며 실행하지 않는다.

전체 RAM과 포트 외에 반환status, external_jump와 D3를 비교한다. 보고서 SHA256 `542ba232b6f0f7c9a64afebd2f4bfd665296e7a0b2631faa212c2b0ec6f78434`. 원본 매핑1MiB의 변경 없음도 검사했다. 최종 verifier는 profile/event별 콜백 스택 차이의 기대 집합도 assertion으로 검사한다. make all test(Python55개/C++전체) 통과. 새 단위검사는 header 변경 이후 미지원 pending callback으로 실패하는 늦은 오류의 RAM/result/모든 port 필드 보존을 확인한다. missing font와 stack 경계, covered@ lookahead 및 줄 위치도 검사했다.

실제 호출자/입력 스케줄링, 미분석 descriptor/flags/콜백, 전체 CPU 레지스터, 외부 CPU 스택 메모리, BIOS 동작, 픽셀/하드웨어 타이밍, 전체 부팅/게임·스테이지 실행은 남아 있다. 이 부분 메뉴 상태기계 검증을 전체 목표 달성으로 취급하지 않는다.
