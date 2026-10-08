# 장면 프레임 실행 리뷰

Baseline `9d8e430`, branch `codex/scene-frame-execution`. 본 리뷰는 baseline 이후 scene_frame API/CLI/unit, full-frame 관측·검증·목록 도구와 후속 입력 후보 목록을 대상으로 한다. Stage input 구현은 별도 후속 변경 단위다. 원격 없이 로컬 커밋/리뷰로 관리한다.

메인이 원본1a73c의 명령 순서, 기존 helper 계약, 새 core/header/CLI/unit과 Makefile을 검토했다. 조건의 carry에 따른 script 단락 평가, live motion cursor의 호출별 재조회, 전체 SWAP과 unsigned phase 비교, A3 보존, A6 전달 및 프레임당 단일 배치를 확인했다. 성공 시 RAM/register/ports를 함께 게시하고 오류 시 모두 보존한다. 새 런타임은 기존 MS5D 리소스를 사용한다. 코드 복사로 남은 CLI helper 오류 문구를 scene frame으로 수정하고 바이너리를 다시 빌드했다.

관측·검증 도구 전체를 읽었다. 원본 고정 ROM과 뱅크2/3 자료의 불변 검사, 쓰기 guard, 정확한 bank 전환, callee 대체와 호출 중 reset 부재, 기존 initializer 결과와 resource/source hash 결합을 확인했다. Unicorn 실행 중 SR hook을 사용하지 않으며 전체 CCR 검증으로 확대하지 않는다. 연속 호출은 native와 CLI 각각 직전 RAM/register를 소비한다. Setup replay는 canonical script 재진입을 명시한 초기 통제 입력으로 분리했다.

메인 리뷰에서 negative resource 목록의 string/Path 비교 오류를 찾아 explicit relative string 비교로 수정했다. 검증 에이전트가 실제 A6를 읽지 않는 경로의 오류 기대를 제거했고, 배치 경계에서 거절되어 allocator에 도달하지 않던 빈 풀 사례도 교체했다. 최종 사례는 실제28ae/2912와100ec6 대체 위치 쓰기를 확인한다. 단순한 fixture 이름이나 호출 의도만으로 coverage를 기록하지 않는다.

Unit은 script→motion→phase→단일 배치 연결, false 조건의 invalid script 우회, debug 출력의 bank envelope 순서, early selector와 late placement 실패의 전체 상태 보존을 검사한다. 원본 비교는 실제 초기화221조건 전체와 여섯 연속 프레임 sequence, 조건/흔들림/setup 통제 입력을 사용한다. 모든 원본/callee의 일반 입력 공간이 검증됐다는 뜻은 아니다.

Frame inventory는 두 창36행,9개 호출과14개 literal 및7개 write operand를 원본과 대조한다. 고유458resources 중 fixed187개의 overlap은0이다. 후속 입력 inventory는 두 창101행과 별도4-byte DATA를 구분하고20개 raw 참조 후보를 수집한다. Raw 후보는 실행 가능한 callsite나 callback 도달성의 증명이 아니다. 메인이 두 목록 도구를 읽고 재생성 내용을 기존 산출물과 직접 대조했다.

최종 수치와 해시는 아래 검증 결과에 기록한다. 직접 플레이 화면, 상위480bc의 나머지 호출 및 전체게임 goal은 미완료다.

## 최종 검증

594프레임/오류149조건/ordered ports621,663건이 통과했다. 여섯 sequence360호출 중354가 실제 이전출력을 소비한다. 조건 true569/false25, phase 갱신585/유지9, camera 승인583/거절11을 관찰했다. Debug8/16 초기화 seed만으로는 다음 프레임의 해당 분기 실행을 보장하지 않아, native cache를 유지하고 F000만 명시한 두 초기 fixture를 추가했다. 둘 다 실제1b0e0을 실행하고1,384ports를 출력한다. Directory-loader도 원본 setup replay와 일치했다.

메인이594개 저장 native RAM/ports·입력 fixture·모든 register·C++ report 행·연속승계와 현재 원본/리소스/oracle/CLI hash를 직접 재대조했다. 두 inventory도 재생성 내용이 현재 JSON과 같음을 확인했다. Python 구문과 diff 검사 통과. 전체make Python182/C++118/경고0 로그는 `artifacts/scene_frame_execution_build_test.log`다. 후속 입력 추가 전체빌드 Python182/C++119/경고0에서도 frame CLI는 동일하다.

Native SHA256 `fc060d8c4d74b43d8bdb424f07d99478da6534f86db1426d4d7e3bd93ddac9f2`, verification `bdbeea5e8caa803f045d574a2fd67d726dc7fed23c829a43dfc50ad1dfc56fad`, CLI `96abbe5073647073f8e6e8185c12b6a9d759798268b724755debc88962bef0bd`. 세부 재현·범위·목록 해시는 scene-frame-execution.md를 따른다. 이 장면 프레임 단위의 통합을 수용하며 전체 goal은 active다.
