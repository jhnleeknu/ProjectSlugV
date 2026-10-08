# Stage activation 경계·의존성 및 원본 관찰 리뷰

Baseline `2c45159`, branch `codex/stage-activation-analysis`. 이번 단위는 상위 callback 연결을 위한 원본 증거와 구현 간극 조사다. 새 C++ 구현 완료를 주장하지 않는다. Sol 6.1 / medium 세 작업자가 직접 callee/API 목록, animation 의존성, 원본 prefix 관찰을 맡았다. 메인은 47c04..480bc의 제어 흐름과 주요 helper 명령을 읽고 prefix 계약 및 8cda 전체 레지스터 계약을 작성했다.

47c04는callback47c6c를게시한뒤해당주소로fall-through한다. 관찰 도구는 그 명령을 실행하기 전에 중단하므로 RTS/전체callback 반환과 명시적으로 구별한다. 처음부터 끝까지 실제callee를 실행하며 hook은 관찰과 중단에만 사용한다. patched helper나 합성포트oracle은 없다. fullRAM15regs, RAM/stack/port 쓰기순서와 branch후속PC를 기록한다. SR은A7보다먼저설정하고실행중읽지않는다. 최종A7는entry와동일하며return sentinel과stack guard가보존된다.

104조건은 기본72, parent/flag alias24, helper가parent필드를바꾸는alias8이다. 마지막8조건의A6=1009c6에서는4e254가100a42를0으로쓴뒤47c48이그값을다시읽는다. 초기parent6/ff도실제0을읽고c3c0에진입하는근거를확보했다. signedBYTE c3c0의음수이전값과0..5의비교, bit0블록출력과bit2screenflag, 초기flag0분기를확인했다. 다섯조건분기모두양쪽경로를실행했다.

메인은 도구 전체를 읽고 저장된104조건을 별도CPU객체로 재실행했다. RAM·15register·ports·모든trace/metadata가일치했다. 전체761 RAM writes와6,576 ports를확인했다. 이후재현성보완으로도구가필요한정적명령artifact를직접재생성하도록바꾸고다시104조건/불일치0을확인했다. 변경은diagnostic listing생성뿐이며CPU fixture/실행의미는바꾸지않았다.

재현 명령: `.venv/bin/python tools/observe_stage_activation_prefix.py`. 최종 report SHA256 `d27d39fa7129934db20f0a7735056822e2b27f30a54e474e0609bb3e347c51ce`. 보고서와416개native파일은ignored artifacts에저장한다. source·oracle·도구·정적근거해시는실행전후검사한다. C++제품코드변경이없으므로전체build회귀를반복하지않았다.

두 inventory는기존header/source와검증문서의지원범위를나눈자료다. 새callees의완료증거가아니다. 메인은16ed2/16ea4/47672/49f8c의새명령목록도직접대조했고,49fc6의기존RAM/carry부분구현을전체레지스터·PVC·대기재개API로확대해석하지않는한계를확인했다. 다음연결에필요한4e286사운드wait,8cda전체상태,4843c BCD,4847c carry,애니메이션및BIOS경계를그대로남긴다.

이 분석·관찰 단위를 수용한다. 다음 구현은47c04초기화효과와8cda전체상태를검증된계약으로연결하고,4e286 및47c6c의연속실행으로확장한다. prefix에서중단하는것을최종완료기준으로삼지않는다. 직접플레이·자연scheduler/IRQ·전체게임Goal은미완료다.
