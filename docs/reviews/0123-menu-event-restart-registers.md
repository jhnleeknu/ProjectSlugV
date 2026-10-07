# 상위 메뉴 이벤트·재시작 레지스터 리뷰

대상 기준 커밋: `347ada5`.

메인이 9b3e의 argument 전달과 각 콜백, 2a28→299c→2782의 정리 및 271c의 필드 초기화를 확인했다. 상위 이벤트·재시작·팔레트 해제의 구현은 메인이 담당하고, CLI·단위 검사·독립 원본 비교 도구는 서브에이전트가 담당했다. 실제 diff와 검증 입력·출력의 출처를 검토했다.

- null 콜백도 9b48에서 D1 하위 word를 항목 argument로 교체한다. debug/area/group 콜백, 하위 메뉴 push의 전체 D1/D3를 연결했다.
- 하위 메뉴 열기는 9f36의 전체 D1 초기화 후 byte 좌표 값을 전달한다. 외부 BIOS 점프는 c00444 실행 직전에서 반환값을 비교한다.
- 팔레트가 free ring으로 이동할 때 D3 하위 word는 제거 후 기존 free tail이며 상위 word를 보존한다. 연결 좌표가 활성 상태이면 이전 absolute Y 전체가 D3를 덮어쓴다. 필드 초기화의 MOVEQ #-1은 최종 D1을 ffffffff로 만든다.
- 기존 line 반환은 재시작 후에도 실제 D3 하위 word를 담는다. 이 값이 항상 텍스트 VRAM 좌표인 것은 아니다.
- CLI의 선택적 `--registers`만 JSON 필드를 추가한다. API/CLI의 모순된 line은 거절하며 RAM·포트·레지스터·결과는 오류 시 보존한다.
- `make -j3 all test`: 종료 0, Python 73개 및 C++ 전체 검사 통과, 경고 없음. 로그 `artifacts/menu_event_registers_build_test.log`.

직접 재시작 비교기는 검증 스크립트가 생성한 기본 C++11 harness를 artifacts 아래에서 컴파일한다. 원본 ROM은 그대로 실행하고 초기화/팔레트 획득도 원본 함수를 사용한다. harness는 진단용이며 실제 프로젝트 구현을 대신하지 않는다.

전체 a370 프레임·제어기·메인 루프 연결은 후속 작업이다. BIOS 실행, 다른 레지스터·SR, 연결 리스트 오브젝트의 다른 재시작 경로, 트랩 핸들러, 외부 스택 잔여값과 픽셀·실제 타이밍의 완료를 주장하지 않는다.

- `.venv/bin/python tools/verify_menu_event_registers.py`: 원본 5,551조건 및 오류 보존 28조건 통과. 보고서 SHA256 `5504bf49e774fc5e4bdf51cddc8fadc36471860d23495784550510bf86eeab81`.
- `.venv/bin/python tools/verify_restart_registers.py`: 원본 506조건 및 오류 보존 5조건 통과. 보고서 SHA256 `05862a1870c440e1ab16e914f038db0dcfce6f1b52c83201f1b8172e15ad4dad`.

상위 이벤트 비교에서 비디오/watchdog 포트 131,257개가 순서·폭·주소·값까지 일치했다. 네 메뉴의 모든 행과 event0..7, 두 렌더러를 실행했고, 8개 6단계 흐름은 실제 CLI RAM/레지스터 반환값을 다음 입력에 전달했다. 직접 재시작 506조건은 해제 없음·공유·0/ffff 참조 수와 좌표0..7 및 이전 Y의 부호 경계를 포함한다. 원본 첫 1MiB 불변을 확인했다.
