# 스테이지 초기화 접두부와 디버그 표시 리뷰

Baseline `a29a1f2`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이1afda..1b126 및1a5a4의 null-script 경로를 해석하고 계약을 정했다. sol에 리소스 추출, C++/CLI/unit, 원본 검증과 문서 작업을 분담했다.

## 범위와 리소스

일반1afda debug 갱신과 실제477e4의 MOVEQ0/A0=0/JSR1a5a4부터477ee 직전까지 연결한다. 이 범위는 전체477e4나 임의 nonzero script의1a5a4 구현이 아니다. 기존scene node 초기화·배율·좌표 갱신과 screen reset을 원본 순서로 호출하고 실제 PVC 쓰기를 전달한다. RAM/D0/D1/D3/ordered ports를 전체 transaction으로 게시한다.

디버그 표는 기존MS5D v1 kind1으로 고정 ROM `[1af12,1b112)`를 보존한다. byte index×2로 접근 가능한512바이트이며 논리 테이블의 끝이라고 단정하지 않는다. flag 표1afd2와 겹친 코드도 원시 바이트로 보존한다. payload SHA256 `44aae050bb5e0eb32e593dee5e8d81ea41b3c18dd0c6913c763d7ef446bb7583`, container SHA256 `ca28489b53c66df310f32a2afca6312f56714f2e5af3fb65a2da17e3c2c4581f`. C++는 실제MS5D 로더와 이 데이터로 word를 조회하며 상수를 재생용 이미지에서 역으로 만들지 않는다.

## 메인 리뷰 발견 사항

초기 C++ 노드 루프가1a7a8의 scale enable 조건을 반대로 구현하고 word로 읽었다. 원본은 byte BTST 후 BNE로 scale을 건너뛰므로 `(ram[d40c] & bit)==0`일 때 실행해야 한다. 이 경로는d40c와delta가0으로 초기화되므로 scale을 생략해도 최종 RAM만 우연히 일치할 수 있다. 메인의 명령·호출 순서 리뷰로 발견해 byte 조건과 분기 방향을 수정했다. 원본이 실행하는 네 노드의 X/Y scale을 실제 helper 호출로 유지한다.

디버그 history 검사에서 두 번째 LEA는A1을 설정하지만 이후 MOVE가A0을 다시 사용한다. 첫 번째 노드만 두 번 검사하는 동작을 수정하지 않고 보존했다. SUBX의 누적 Z는 Y 차이뿐 아니라 앞선 X 차이도0이어야 하므로 이를 명시적으로 구현했다. draw의 D0/D1 word 연산은 상위word를 보존하고 D3 DBRA 완료lowword는ffff다. 첫 번째 조회가0320이면 두 번째 노드를 조회하고 아니면 건너뛴다.

검증은 uniform 화면 반복을 혼합 타일 격자로 보완했다. 원본의 실제 조회 instruction에서256 index×4 upper flag 조합 전체 방문을 검사하고, 각256개 테이블 값의 우선순위도 별도로 확인한다. 원본 루틴 실행이 아닌 테스트 이름만으로 경로를 주장하지 않는다. initializer의 잘못된 리소스는 upfront 검사이므로 late rollback으로 기록하지 않는다.

## 검증 결과와 남은 작업

최종 `tools/verify_scene_initialization.py` session7178 exit0. 원본576조건(debug524/initializer52), 오류24조건, 순서 있는 포트672744개와 CLI승계7시퀀스를 비교했다. 실제MS5D 원본 바이트를 사용하고 원본 코드 패치 없이 모든 하위 함수를 실행했다. 전체 RAM/D0/D1/D3/port stream이 일치했고 MMIO읽기0, 고정 ROM/선택 bank 불변이다. 보고서 SHA256 `451015b835b3a4e741bddf61b43e21cf5c8d72d1d4dc30ff4c4c5107f7554bb4`.

수정 전 실행 파일과 혼동하지 않도록 최종 CLI SHA256 `aab6915637f81851718c0951cfb83ea4099d132d36467848f690eb3f66e62f49`를 실행 시작/끝에 비교했다. 이 수치는 scale 분기 수정 후 결과다. 첫 실행2858의 결과를 최종 증거로 사용하지 않는다. 메인이 최종 JSON과 verifier의 실제 table instruction 방문 집합, binary port 비교 및 초기화 종료477ee를 확인했다.

`make -j3 all test` exit0, Python95검사와 C++88 test executable 통과, 경고·오류0. 로그 `artifacts/scene_initialization_build_test.log`. 새 리소스의 synthetic7검사는 원본 게임 데이터를 테스트 fixture에 넣지 않고 헤더·길이·CRC·전체 프로그램/구간 해시와 명령 근거 변조를 거부한다. `runtime-resources`에 새 packer를 연결했다.

전체 게임플레이·일반 scene script·477ee 이후 callback 및 자연 scheduler/물리 timing은 남아 있다. 다음은 stage catalog 조회와3d58의 두 byte 사운드 명령 대기·재개를 연결하는 작업이다. 전체 목표는 진행 중이다.
