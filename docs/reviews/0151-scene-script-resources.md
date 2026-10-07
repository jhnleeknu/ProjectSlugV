# 장면 스크립트 리소스와 C++ 디코더 리뷰

Baseline `005fcce`. Canonical ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 첫1MiB의 CPU 주소와 ROM 오프셋을 유지한다. 메인은 기존1a0b6/1a0bc..1a26a 해석에 근거해 packer와 실제 리소스 검증을 작성하고, sol이 작성한 C++ loader/decoder/CLI/unit을 검토했다. 이번 sol 재시도는 실행됐다.

## 원본 보존과 소비

59개 stage record가 가리키는 비영 script41개를 기존 MS5D v1 kind1으로 추출한다. 합계5486payload bytes이며814개 일반 명령,41개 음수 terminator,9개 opaque inline block을 포함한다. Stable ID는 scene-script와8자리 원본주소를 결합한다. Null 포인터는 별도 빈 리소스로 대체하지 않으며59개 참조와 리소스의 대응을 manifest에 보존한다.

각 창은 첫 음수opcode 뒤까지이며 기존 전체 프로그램 원본도 유지한다. 이 창을 모든 참조 데이터의 완전한 소유 범위라고 주장하지 않는다. Map/path와 기타 외부 포인터 target은 아직 별도 추출·해석이 필요하다.

C++ SceneScript는 원시 FixedDataResource와 명령별 주소/opcode/operand/inline bytes/다음주소를 보존한다. Terminator는 별도 필드다. 기존 CRC/header loader를 그대로 사용하며, 정확한종료뒤byte·지원밖opcode·잘린operand·음수/홀수inline skip을거부한다. 데이터 게시 시 vector swap을 사용해 오류가 기존 출력에 영향을 주지 않는다. 원본ROM이나 Python을 C++ 실행 중 읽지 않는다.

## 검증

`verify_scene_script_resources.py`는 manifest59참조를 원본catalog와 비교하고41개 실제MS5D를C++ CLI로읽었다.814개 명령을 원시byte로재조합하여 원본 전체5486바이트와 일치를 확인했다. 원본1a0b6의MOVE.W/JMP/BRA를각명령에서실행해20-entry dispatch의목적함수, A1+2와D7 상위16비트보존도확인했다. Handler첫명령 직전에서멈추므로handler 효과를확인한것은아니다.

10개 부정CLI조건도통과했다. 원본고정ROM 및C++바이너리불변을확인했다. 보고서 SHA256 `624fdd85a3d34445a37421e5df4413b0a70d84dd94f027a90715ff6f907ec560`. 합성Python6개와C++20opcode검사도통과했다. 전체빌드결과는 `artifacts/scene_script_resources_build_test.log` 및 분석문서에기록한다.

전체 `make -j3 all test`는Python131/C++98/경고0으로exit0을확인했다.

실제script는814일반명령+41terminator=855구문행으로이전inventory와일치한다. 이 수치는 스테이지 실행이나분석완료율이아니다. 다음은 명령 handler와외부map/path리소스를연결해1a5a4의nonzero script를실행하는것이다. 화면·자연scheduler·전체게임플레이복원은미완료다.
