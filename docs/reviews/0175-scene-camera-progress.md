# 장면 좌표 진행 리뷰

Baseline `0d6cf3a`, 브랜치 `codex/scene-camera-progress`. 직전 goal turn은 pair 경로 선택과 독립 carry 검증을 완료한 progress다. 메인이 현재 clean checkout·직전 commit·원본 두 코드 창을 다시 확인하고, 분석 계약에 따라 구현과 원본 비교·목록화를 sol / medium 에이전트에 분담했다.

## 구현 검토

메인은 새 scene_camera header/core/unit 전체와 기존 bounds CLI 대비 신규 CLI 차이를 읽었다. API는 19a40 X 요청, 19ac8 Y 요청, 전체 19b96 진행을 지원한다. 기존 19802·19832·19978 API를 후보 RAM/state 안에서 순서대로 연결하며, callee의 결과를 임의로 바꾸지 않는다. 실패는 전체 RAM·12레지스터를 보존한다. Standalone axis는 리소스를 읽지 않고, 전체 진행은 비영 cursor에서 기존 exact motion MS5D 계약을 사용한다.

ASR.W/L, WORD 상위 보존, N-only 분기, signed 비교, ADD.L 뒤 BGE의 N xor V를 원본과 대조했다. 부호 있는 C++ 오버플로 없이 unsigned 연산으로 처리한다. Y가 요청량을 먼저 저장한 뒤 같은 RAM을 빼는 순서, 후진 Y 검사에 X의 ADD.W가 없는 비대칭을 유지한다. 강제 속도는 WORD를 zero-extend하고 8비트 왼쪽으로 옮긴다.

거절 시 현재 XY만 보존하며 이미 계산한 제안 XY·경로 변경을 되돌리지 않는다. 양쪽 요청량은0이 된다. 초기화할 경계의 쓰기 순서가 원본과 다르던 한 곳을 메인 리뷰에서 발견해 d3ce,d3d2,d3d0,d3d4 순서로 맞췄다. 최종 RAM 차이는 없지만 불필요한 순서 변경을 제거했다.

전체 make는 Python182/C++116/경고0, 로그 `artifacts/scene_camera_build_test.log`다. 경계 쓰기 순서 수정 후 camera CLI/unit만 다시 빌드해 통과했다. 기존 motion core와 세 API는 수정하지 않았고 기존 pair/bounds binary hash도 그대로다. 따라서 무관한 기존 원본 corpus를 다시 실행하지 않았다.

## 분석 근거

Camera inventory 도구의 두 창 전체 193행, byte/source/주소 연속성, 지정된 여섯 비대칭 명령과 37개 motion 리소스의 현재 원본 대조를 읽었다. 목록은 실행 의미 증명과 구분한다. JSON SHA256 `79a749a3f11a230413f20d7a579def2fa7049b435df32353755adc7f2b0cec16`, ASM `3f8ac530dd1c06d731f352dc78510cec800c86ed0adb4afa4bf5608a706b5949`다.

후속 frame 제어도 원본과 대조했다. 진행 조건의 RAMd422는 setup dependency가 아니라 scene command2c의 inline 데이터다. 메인이 41개 script의 source/container/catalog 폐쇄를 확인하는 새 inventory를 리뷰했고 9개 조건·98바이트를 확인했다. 이 데이터는 이미 기존 MS5D 안에 있으며 새 리소스를 중복 생성하지 않는다. 조건·사각형·기간·설정·흔들림·단일 배치와 전체 1a73c 계약을 scene-frame-control.md에 저장했다. 이 후속 분석은 아직 실행 구현 완료가 아니다.

## 독립 검증

Observer/verifier 전체를 읽었다. 메인 리뷰에서 unsigned 시간 제한의 이전 시간 fallback과 강제 속도 LONG wrap 조건을 보강했다. 원본 native 2,773조건/오류102조건을 통과했다. 축별 요청 1,152, canonical37리소스/108record의 1,080, 합성 주소 정규화465, null 전체 진행76을 구분한다. 전체 RAM·12레지스터·RTS/A7·callee 호출·실제 분기를 검사하고 CPU write hook으로 RAM/stack 밖 쓰기를 거절한다.

X385/Y382회의 ADD V1 관찰은 N xor V와 실제 다음 PC가 일치했다. 비영 N과 비영 V의 혼동을 막기 위해 결과 부호 양쪽을 확인했다. 축별 V1 335조건에서는 Unicorn의 전체 RAM·12레지스터도 독립적으로 일치했다. Unicorn에서는 실행 중 SR을 읽지 않는다.

Unsigned 제한의 다섯 분기에서 양쪽 목적지를 모두 확인했다. 강제 속도 ffff의 추가로 ff fe 0000이00 fd ff00으로 감싸더라도 원본은 전진 제한으로 간다는 조건도 검사했다. 확정1,164/거절457 중 실제 cursor가 바뀐 뒤 거절한128조건을 확인했고 제안 XY/cursor 유지·현재 XY 보존·요청량 초기화를 검증했다. 모든36 motion type을 실제 callee에서 관찰했다.

8개 CLI sequence의24호출 중16호출이 직전 출력을 소비한다. 매 호출 host가 bounds·center·margin·speed·old velocity·시간 제한·force·fixed delta·flags·camera WORD를 다시 쓰는 점을 명시했다. 나머지 RAM·12레지스터의 승계이며 자연 frame이나 velocity 연속성을 주장하지 않는다.

메인이 최종2,773개의 native 저장 RAM hash와 assertion 근거, C++ report 행·register·현재37resources/manifest/원본/oracle/binary hash,335개 secondary 결과와128개 cursor변경 거절 기록을 직접 재대조했다. Python 구문과 git diff 검사도 통과했다. 반환 CCR·사이클/MMIO timing은 API 검증 범위 밖이다.

최종 verification `6e98c13f63080f3859d99446d618990d615e2e1c2fb756a818be46b74f0b86c2`, native `94e5b900cb10941cccca10dbf08392218beefb4fda498b6ad8ba72eb61736e65`, CLI `8371c0c02165583693691ae20e33ef0b974b4e97ddc033957cb7243f15445944`.

메인은 이 단위의 통합을 수용했다. 원격 없는 로컬 branch/commit/review다. 다음은 진행 조건·설정/흔들림·단일 배치와 전체1a73c 연결이다. 직접 플레이와 전체게임복원은 미완료이며 goal은 active다.
