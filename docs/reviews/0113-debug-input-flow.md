# 진단 출력의 줄 위치와 다음 입력 연결 리뷰

대상 기준 커밋: `99c133f`.

메인이396e의D3.word읽기,386e의제어문자처리와NUL종료를확인했다. 종료직전줄바꿈은RAMline에저장되지않으므로파서의최종line을선택적출력으로반환한다. 진단생략/실패는입력line을보존한다. 기존CLI JSON은유지하고LINE입력시에만line필드를추가했다.

- `make -j3 all test`:Python73개및C++전체검사통과,경고없음. 로그 `artifacts/debug_input_flow_build_test.log`.
- C++추가검사는종료줄바꿈의RAM/반환값차이와실패및생략시line보존을확인했다.
- `.venv/bin/python tools/verify_debug_input_flow.py`:29경계/469포트/잘못된LINE6조건통과. 실제MS5D를읽고전체RAM/읽기횟수/순서있는포트와진단D1/line을비교했다.
- 메인리뷰에서진단전후A5/A6/A7보존검사를추가하고,두번째프레임D1/D3는원본에서가져온외부조건임을명시하도록수정했다. API출력으로검증하지않은최종CPU상태까지복원완료로취급하지않는다.
- 보고서SHA256 `f8554a23827ace276e07b389230258d3ec00a0ecaaf439d925b3d814d344fb12`.

입력style/line은진단CLI출력을직접소비한다. 신호는실제c8c가생성하고대기재개는진단을재실행하지않는다. 컨트롤러최종문맥·임의콜백·SR/RTE/BIOS·물리시간축및전체부팅은미완료다.
