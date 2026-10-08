# 입력 callback 실행 리뷰

Baseline `a9cba4b`, branch `codex/stage-input-callbacks`. 신규 callback header/core/CLI/unit, bounded inventory, 원본 관측·검증 도구와 Makefile 연결을 대상으로 한다. 다음 stage_input_loop 파일은 별도 단위로 분리한다.

메인이 원본18entry와 helper의 제어 흐름/자료 폭을 직접 해석한 뒤 확정 구현과 반복 검증을 gpt-6.1-sol / medium 에이전트에 위임했다. Core/header 전체, CLI의 선행 helper 대비 diff와 unit 전체를 읽었다. LONG/WORD 투영 차이, EOR N 분기, equality의 D3 조기 보존, saved WORD/A0 복원, BYTE 상위 보존과 A6의 조건부 접근을 확인했다.

49eba/49ef0의 absolute-memory CMPA와49f66의 immediate CMPA를 구분한다.49eba의 버려지는 OR는 최종 일반 register/RAM 계약에서 효과가 없고 CCR를 노출하지 않는다.49ef0의 D0 push/D1 pop과1d628의 A0=0 유지도 원본대로 구현했다. Nested helper 실패는 바깥 candidate 상태까지 폐기하므로 앞선 callback slot 쓰기나 latch 변경이 외부로 노출되지 않는다. Null/no-op과 미사용 자료의 지연 검사를 확인했다.

Unit은 LONG crossing/equality tail, absolute-memory 비교에 따른 실제 bit 선택, D1 복원, 이미 설정된 latch의 coordinate read 우회, SNE/EOR 상위 보존, A6 부호, setter 이후 missing mask rollback과 A0zero chain을 검사한다. CLI는14register와 경로/inode 보호를 전달한다. 새로운 해시 변화 없이 기존 입력 helper를 재사용한다.

Inventory 도구 전체를 읽고10창219행 및 중요한 literal·연속 호출 바이트를 확인했다. 모든18entry가 실제 행 경계이며 원본비교 도구는 합성 카메라/좌표/flag/latch를 RAM에만 설정한다. Family 이름만으로 coverage를 주장하지 않으며 원본 branch successor와 실제 callback 진입 register를 확인한다.

## 최종 검증

관측·검증 도구 전체를 읽고 source/oracle/library/resource/core/CLI/tool 해시 검사를 확인했다. 메인이 최종2,943개 저장RAM·입력fixture·register·C++ report행·원본branchsuccessor와actual-output chain을 직접 대조했다.18entry 집합과38개 분기의 양쪽 실행을 검증했다. Absolute-memory 비교의 실제 목적지가 RAM LONG equality에 대응하는 추가 assertion도 확인했다.160오류는 원본에 잘못된 메모리를 실행하지 않고 C++ 지원범위 거절과 입력/기존 출력 보존을 검사한다.

380개의 A0zero mapper 진입,720 memory-CMPA fixture,248 D0→D1복원 조건,16 unused-mask 생략과 directory loader를 확인했다. 네 sequence32호출 중28회는 호스트 재작성 없는 실제 CLI 출력 승계다. 전체make Python182/C++120/경고0, 로그 `artifacts/stage_input_callback_build_test.log`. Python 구문/diff 검사와 inventory 재생성 동일 검사를 통과했다.

Native SHA256 `2bb75aa89ee636ee8a6afee4df7662def786b02f7a8ee9e3d1b850ff8a41cd0c`, verification `ef931982b559b333ef52a6bd9b9020c78c782568ff874cd9a01a3ef21c97c398`, CLI `7973d5cf88f0b2a5504adca95793cfe5bfc9aebd9030297a7f0ed923882b436d`. 이 단위 통합을 수용한다. 상위49b0c/47642와추가1da60/4d7a6 연결은 다음 별도 단위이며 전체게임 goal은 active다.
