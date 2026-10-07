# 메뉴 개폐·테두리 D1/D3 리뷰

대상 기준 커밋: `12360e0`.

메인이 a348/a2be, 9b58..9cd2, 9e94 및 a018의 명령을 확인했다. a348은 D1을 보존하고, a2be는 D1.word에 실제 지울 행 수를 남긴다. 두 경로 모두 테두리 출력이 만든 D3를 반환한다. 테두리의 마지막9cd0 증가와 높이1에서도 두 행을 그리는 동작을 포함했다. 가림 helper는 D1/D3를 변경하지 않는다.

- `trace_menu_border`의 선택적 전체D3와 `open_menu_step`/`close_menu_step`의 선택적 전체D1/D3를 추가했다. 후보 상태만 변경하여 늦은 오류에도 모든 출력이 보존된다.
- CLI `step_menu_motion --registers D1 D3 open|close ...`는 두 반환값을 JSON으로 출력한다. 기존 빈stdout과4바이트 VRAM 기록 형식은 그대로다.
- `make -j3 all test`: Python73개 및 C++ 전체 검사 통과, 경고 없음. 로그 `artifacts/menu_motion_registers_build_test.log`.
- 단위검사에서 리소스 오류의 레지스터 보존, 높이0의 우회, 닫기 감소량 제한, 일반테두리와 clear-only의 최종D3 차이를 확인했다.

전체 a370 프레임, 콜백, 픽셀 출력과 장치 타이밍은 이번 범위가 아니다. native catalog의 네 descriptor는 모두 flags0이므로 flags1 경로의 원본 동등성은 이번 native 검사에 포함하지 않는다. 이 경로는 원본 명령 분석과 C++ 단위검사로만 확인했다.

- `.venv/bin/python tools/verify_menu_motion_registers.py`: 원본408조건, 출력256,136개 및 오류34조건 통과. 전체RAM/전체D1/D3/순서있는출력을 비교했다. 정규 control_menu_tree.ms5d의 실제 네 descriptor를 사용하며 원본 첫1MiB 불변을 확인했다.
- 8개16단계 개폐 흐름은 이전 C++의 RAM과전체D1/D3를 다음 호출에 전달한다.
- 메인 리뷰에서 가림 설정만으로 실제 겹침을 보장할 수 없음을 발견해 원본 a076/a06c 도달 횟수를 추가했다. 가림39,416회/표시256,136회를 확인했다. 가림 연속조건의 y위치를 맞춘 뒤 각4조건에서 실제 가림1,024회씩 확인했다.
- 최종 보고서 SHA256 `284aa6f0548802896fcc6b9d8657a7d03efd770b77fd66100553fe91e7c3b0d2`.
