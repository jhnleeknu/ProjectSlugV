# 활성 대기·메뉴 시작 D1/D3 리뷰

대상 기준 커밋: `86d20a6`.

메인이91c2..92ce,92ce..932e,ca9e..caee,a29c/a0a0..a1e0,38e8,a5d2/a348/9b58의원본명령을추적했다. selector9086의D1byte변경은모든대기분기에남으며 idle3902는원본문구의제어문자를반영한다. 메뉴시작은ca9e에서전체D1을0으로만들고92e2에서8로설정하지만 제목측정이이를다시변경한다. 실제native최종D1은68이다.

- 직접텍스트추적은종료style/전체D3를반환한다. 메뉴제목측정은실제위치제어실행여부를보존하여D3상위초기화를계산한다. 글리프가없는종료제어문자와오류보존도단위검사했다.
- 첫메뉴프레임은현재높이byte0/목표높이양수이므로테두리출력없이a348이높이만갱신한다. D1/D3는초기화후값을보존한다. 해당근거없이이미열린a370에도이규칙을적용하지않았다. 목표높이0의변형root리소스는명시적으로거절한다.
- `make -j3 all test`: Python73개 및 C++전체검사통과, 경고없음. 로그 `artifacts/control_wait_registers_build_test.log`.
- 추가단위검사후 `make build/menu_init_test` 및 `./build/menu_init_test` 통과. 실제title파서의전체D3초기화/최종style/늦은오류롤백을확인했다.
- `.venv/bin/python tools/verify_control_wait_registers.py`: 원본1,470조건, 포트279,922개, 오류36조건통과. idle776/step135/held205/menu354(직접92ce54포함). 실제9068출력484회/9079출력144회 확인.
- 전체RAM/전체D0,D1,D3/시간순포트를비교했다. held20회씩2조건 및blink40회씩2조건은이전C++의RAM과전체D1/D3를이어입력한다. 원본코드는변경하지않았고매핑고정ROM불변도확인했다.
- 보고서 SHA256 `b6610550c3b2d04cc43cd0e9c5ff9e9e2095d4f5e2a9dd606b9b2e7c409cd1e6`.

정규control_menu_tree.ms5d/control_pause.ms5d를사용한다. 알수없는콜백, 이미열린a370메뉴프레임의전체레지스터반환, 모든CPU문맥·장치시간축·전체부팅은미완료다. 다음은a370반환을연결한뒤step_control 및호출자까지통합하는것이다.
