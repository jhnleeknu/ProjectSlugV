# 스테이지 좌표 기반 함수 리뷰

Baseline `4091376`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이43dda/16fac/43e22/16fee/43e38/43ea8/1728c/1724c/1726c/17292의 명령을 해석하고 구현 계약을 정했다. sol에 C++/CLI/unit, 원본 검증, 원본 관측 및 목록·문서 작업을 분담했다.

## 구현 검토

`scene_node.cpp`는 기존 `update_position`의 RAM 효과를 재사용하면서 이 호출자에 필요한 D0/D1/D3/A0/A1을 운반한다. 초기화에서 쓰지 않는 필드와 레지스터는 보존한다.43ea8은 local0/4만 먼저 변경하므로 old worldY와 parent를 advance 전 캡처해도43e3e/43e44와 같은 값을 얻는다. 부모를 설정하는43e22/16fee는 prefix 쓰기 후 캡처한다. 실패는 prefix 쓰기까지 포함해 RAM/state 전체를 보존한다.

1724c/1726c는 low word의 unsigned 곱과 high word의 signed 곱을 구분한다. low 곱은32비트 부호를 가진 산술 우측 시프트를 사용하고 fractional byte ADD의 carry를 더한다. signed16 곱은 int32 범위 안이며 이후 uint32로 변환해8비트 shift하므로 음수 left shift나 signed overflow에 의존하지 않는다. 결과는 modulo32 연산이다. 다른 축의 레지스터와 D3/A1은 보존한다.

17292는 LEA A0+80, MOVEQ0 뒤2048개의 `22c0`와 RTS라는 원시 패턴을 스크립트로 검증한다. 실제 쓰기는8192바이트이며 끝 A1은 A0+2080이다. 첫128바이트와 이후 범위를 지우지 않는다. entry별 완전한 RAM span을 검사하고 CLI는 unsigned32 파싱과 파일 alias를 검사한다.

## 원본 관측 도구 리뷰

초기 `probe_stage_initialization.py`는 Unicorn code hook의 size로 읽은 짧은 바이트를 Capstone에 전달했다. 메인이 잘못 표시된 BSR 목적지와 코드를 대조해 문제를 발견했다.24바이트 실제 메모리 창에서 한 명령을 디코딩하고 그 명령 전체 raw bytes를 canonical ROM의 source offset과 대조하도록 수정했다.1b0ac의 `61000032`,1b0c8의 `61000016`은 모두1b0e0을 가리킨다. 수정 전 호출 표시는 근거로 사용하지 않는다.

수정 후 native 관측16조건 모두 실제 RTS에 도달했다. zero/seeded RAM 및 원본2790/3ef2 적용 여부, f000 bits3/4의 네 조합을 사용한다. flag0은4개의 PVC 쓰기, 나머지는4개의 PVC와1280개의 VRAM 쓰기를 기록했다. MMIO 읽기는0이다. D0=0,D1=D3=01000000으로 반환하며 원본 코드/선택 bank 원시 바이트는 변하지 않았다. 보고서 SHA256 `18c241850f4c7e0adf715963cbe3bb98f653590cacb97e12715e9afd458c4e05`.

이 관측은 A0=0/D0=0인1a5a4 경로이며 C++ 동등성 검사가 아니다. PVC 모델은 이 경로의2000/1000 두 word만 허용한다. 일반 PVC 동작, nonzero script, 전체477e4 및 자연 scheduler를 증명하지 않는다.

## 검증 및 다음 단계

`tools/verify_scene_node.py` session29294 exit0: 원본1904조건/오류94조건 및 실제CLI승계8시퀀스 통과. RAM 전체와 D0/D1/D3/A0/A1을 비교하며 MMIO쓰기0, ROM불변을 확인한다. 보고서 SHA256 `c900dfc01d94c31633856b8ffae34478ce9ad281366b9322e23ccebd85a0c1c6`. 메인은 verifier의1080배율조건,720좌표/부모중첩/스탬프조건,실제노드주소와상하span경계,CLI출력승계를 확인했다. 에러 검사는 원본의 잘못된 포인터 실행을 제외하고 CLI출력보존을 검증하며 C++ unit이RAM/state rollback을 검사한다.

`make -j3 all test` exit0. Python88검사와 C++87 test executable이 통과했고 경고·오류0이다. 로그 `artifacts/scene_node_build_test.log`. 메인이 로그와 최종보고서를 확인했고 core 변경을 요구하는 불일치는 없었다. sol의 별도 읽기 검토에서도 probe 호출21296개의 전체 raw bytes/명령길이/표시/원본주소 매핑이 일치했다.

다음 단계는 이 기반 함수와 원본 리소스를 이용한1a5a4 초기화의 C++ 연결이다. 디버그 표시의1280회 쓰기와 테이블 참조를 생략하지 않는다. 전체 스테이지와 게임 복원 목표는 진행 중이다.
