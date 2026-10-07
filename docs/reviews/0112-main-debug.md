# 메인 진단 리소스와 조건부 출력 리뷰

대상 기준 커밋: `bc4ecb7`.

메인이ec4조건과3a70→396e→386e의최종style반환을확인했다. 종료직전제어문자의style은RAM에저장되지않을수있으므로선택적final_style출력을추가했다. 진단경로D1상위16비트는보존한다. 오브젝트상태는byte접근이어서홀수주소를허용하고10ff7b상한을검사한다. bit0꺼짐은오브젝트를,상태0은리소스를사용하지않는다.

추출기는원본해시와234바이트payload해시,20포인터를검사하고기존MS5D규격과안정ID로저장한다. embedded NUL제어피연산자를보존하고e40부터의코드는제외한다. 메인이packer/CLI/검증diff를직접확인했다.

- `.venv/bin/python tools/pack_main_debug.py`:266바이트MS5D와manifest생성,기존C++로더를통한원본실행비교에사용했다.
- `make all test`:Python73개및C++전체검사통과,경고없음. 로그 `artifacts/main_debug_build_test.log`.
- 추가단위검사:종료제어문자style과RAM값의차이,꺼진플래그의오브젝트우회,홀수오브젝트상태읽기,활성잘못된리소스롤백.
- `.venv/bin/python tools/verify_main_debug.py`:790조건/61,272포트/오류11조건통과. 전체RAM/최종32비트D1/시간순포트를비교했다. 원본코드불변,font읽기0.
- 보고서SHA256 `bbe8deb1e9bd518172600538a3eb79a5295cff5edd8000fe9efb3bad0c5c38ee`.

ef2대기와이후입력은이번API의실행범위밖이다. 다음연결에서는D3줄위치등필요문맥도확인해야하며전체CPU레지스터보존을이번D1검사로주장하지않는다. 실제게임콜백·전체부팅·SR/RTE/BIOS·장치시간축은미완료다.
