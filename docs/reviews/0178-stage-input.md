# 입력 보조 함수 리뷰

Baseline `accfb9d`, branch `codex/stage-input-helpers`. 선행 리뷰0177 장면 프레임 변경 위의 별도 입력 단위다. 신규 stage_input header/core/CLI/unit, MS5D packer, 원본 관측·CLI 검증과 Makefile 연결을 대상으로 한다. 원본 계약은 메인이 직접 분석했으며 확정 규격 구현과 반복 검증은 기존 gpt-6.1-sol / medium 에이전트에 위임했다.

메인이 모든 신규 파일을 읽었다. 49ab4의 byte 보존/전체 MOVEQ/A4 원위치/overlap 억제,49afe와49bb4 WORD 상위 보존,49c20의 WORD index 조작,49c32/49c66 A0 변경을 확인했다. 엔진은 기본 mask를 하드코딩하지 않고 실제 fixed resource를 읽는다. RAM byte 홀수 허용과 WORD 정렬, fixed 창 중복·부분 범위·주소 초과와 출력 transaction을 확인했다. CLI의 복사된 오류 문구를 stage input으로 수정하고 재빌드했다. 이후 core/CLI는 동결했다.

Packer의 source SHA/주소·payload·CRC·버전·reserved 검사를 읽고 메인에서 재생성 결과를 현재 파일과 대조했다. 기존 C++ loader로 생성된36byte 컨테이너의 CPU=ROM49ab0과 정확한4byte payload를 직접 확인했다. ROM·추출 산출물은 ignored 경로에만 둔다.

Musashi observer는 원본 fixed ROM을 유지하고 RAM/stack 이외 쓰기를 거절한다. SR 초기값 설정은 호출 전이며 실행 중 flag patch/reset은 없다. 49bb4의 실제 세 WORD 쓰기 순서를 기록하고 반환 PC/A7도 확인한다. 검증기는 합성 mask를 live RAM에만 놓고 native와 CLI 각각의 실제 출력을 다음 호출에 승계한다. 오류 입력을 원본 CPU에 실행해 C++ 방어 계약과 혼동하지 않는다.

2,694조건에서 전체64KiB RAM·13register가 일치했고42오류에서 입력/기존 출력이 보존됐다. 두 sequence12호출 중10이 호스트 수정 없는 승계다. 메인이 모든 저장 RAM·fixture·incoming register·native 쓰기 기록·report 행·현재 source/resource/oracle/core/CLI 해시를 대조했다. 전체 재실행에서도 native/verification 보고서가 동일했다. 전체 해시는 stage-input.md에 기록한다.

Callback 주소 설치는 callback 실행 완료가 아니다. 상위49b0c,47642 mask 생성과 알려진 callback들의 실제 실행 연결 및 전체480bc는 다음 단위다. 직접 플레이 화면과 전체게임 goal은 계속 미완료이며 active다.

전체 `make -j3 all test`는 Python182/C++119/경고0으로 통과했다. 로그는 `artifacts/stage_input_build_test.log`다. 새 stage_input 및 선행 frame CLI SHA가 검증 당시 값과 같음을 확인했다.
