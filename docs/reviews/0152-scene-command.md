# 장면 명령 실행 리뷰

Baseline `cf8e834`. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 고정 첫 1MiB의 CPU 주소이자 프로그램 ROM 오프셋이다. 원본 ROM은 변경하지 않았다.

메인은 1a0b6 dispatch 및 각 handler의 저장 순서·레지스터 폭·종료점을 확인하고 sol 세 작업으로 C++ 구현, native 비교, 분석 문서를 분담했다. 기존 scene_node API는 노드 상태에 필요한 일부 레지스터만 노출했으므로, 이를 사용하는 새 명령 API의 전체 data-register 승계는 별도로 검토했다.

## 발견과 수정

- opcode14는 16fee→43e38의 parent=0 경로를 사용한다. D7은 상위 비트도 보존하지 않고 전체0이 된다. D2/D3은 이전 world X/Y, D4.byte는0, D5.byte는 world 쓰기 뒤 RAMd494이다. D4/D5 상위24비트와 D6은 보존한다. 이 부수효과를 반환 상태에 반영했다.
- opcode1c의 operand0 경로는 flag만 지우지 않는다. 1701a는 node26을 D7.word로 읽으며 음수이면 반환한다. 비음수이면 watchdog byte를 쓰고 32회에 걸쳐 VRAM long 두 개씩을 기록한다. WORD 덧셈→SWAP→하위WORD 교체 및 각 LONG 증가를 명시적인 unsigned 폭으로 구현한다. D5/D6/D7 변화도 반환한다.
- 노드18 쓰기는 마지막 byte2b까지이므로 요구 span은2c이며,14는2e,1c는7b이다.
- opcode14에서 global stamp가 노드 history 영역과 겹칠 때는 history 쓰기 전 byte가 D5 결과다. wrapper는 이 값을 보존하며 합성 unit으로 확인한다. 이 합성 node table을 canonical ROM에 주입해 검증했다고 주장하지 않는다.

## 범위와 데이터

기존 MS5D v1 kind1에 node table1a08e의16바이트를 추가했다. selector0/4/8/12만 지원하며 전체 signed-index 조회를 구현한 것은 아니다. C++은 script.source를 재디코딩하고 A1의 정확한 명령 경계를 확인하므로 변경된 캐시 명령 메타데이터를 실행하지 않는다. 정상 출력은 RAM·D0..D7/A0/A1·순서 있는 포트 기록이며 오류는 이 API 출력 전체를 보존한다.

15종 handler 중 canonical41개 script에 등장하는 것은14종586회다. 나머지5종00/04/08/10/24의228회는 명시적인 미지원 오류다. 4c는 합성 unit 범위이며 canonical 실행 비교가 아니다. 이 수치는 전체 게임의 완료율을 뜻하지 않는다.

## 검증 결과

`tools/verify_scene_command.py`는 3385조건/부정65조건/순서 있는 포트18720건을 통과했다. Canonical 지원586개×4 RAM/register profile=2344조건, CLI승계586회, node slot 경계260조건, video shadow 경계195조건이다. 118개 인접 지원 명령 run에서 CLI의 실제 RAM·D0..D7/A0/A1 결과를 다음 호출로 넘겼다. 모든 native 호출은 원본1a0b6에서 handler RTS까지 실행하고 A7 반환도 확인했다.

보고서 `artifacts/scene_command/verification.json` SHA256 `ea129b9adc8158c195cd1bd92ee4488d24aae78ca87e6327a3a0dad5ffe9e65d`. 검증 시작/끝의 실행파일 SHA256 `7424ae5fd62e55d4180579da798c2d3354e86853181cf6c1729f8cd90c04a253` 및 고정 ROM 불변을 확인했다. 메인은 verifier 코드·최종 보고서·실행파일 해시를 직접 대조했다.

최종 `make -j3 all test`는 exit0, Python131/C++99/경고0이다. 로그 `artifacts/scene_command_build_test.log`. 기존 scene_node native 회귀1904/부정94/CLI승계8도 통과했으며 보고서 SHA256 `c900dfc01d94c31633856b8ffae34478ce9ad281366b9322e23ccebd85a0c1c6`를 유지했다. 공유 scene_node 구현은 수정하지 않았다.

단계별 실행 context는 각각 초기화하며 인접 지원 명령의 CLI RAM·반환 레지스터·A1 승계와 전체 스크립트의 자연 실행을 구분한다. 미지원 명령은 native로 실행하지 않고 지원 run의 경계를 끊는다. CCR, 하드웨어 시간축, 자연 scheduler, 전체 스테이지 렌더링은 이번 검증에 포함하지 않는다. 다음은 map 초기화43ffc, motion/path19772/197da/19e60, palette8da2 및 포인터 간접호출 의존성을 리소스와 연결하는 작업이다.
