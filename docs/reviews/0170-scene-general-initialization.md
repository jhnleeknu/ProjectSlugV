# 일반 장면 초기화 통합 리뷰

Baseline `6d3e1dd`. 직전goal turn은전체배치실행의원본비교·리뷰·커밋을완료한progress다. 이번에는메인이1a5a4와callee/caller원본을대조하고sol에게구현,독립원본비교,명시창·stage입력목록을분담했다.

## 메인 코드 검토

신규core전체와CLI/unit을읽었다. D0.low target/A0 script를처음저장한뒤초기화하고,19e30 metadata+c BYTE쓰기(+d보존),d40c WORD clear,197da의D7 highWORD보존,199d4/199ea/phase목표 unsigned제한,19938→전체1a7a8,후반좌표정리→duration조건호출→1a414를원본순서로연결한다. 12register helper의변환에서A3를유지하고13register update의A3결과는승계한다.

Resource선택은사용시수행하며null/대기는불필요한script읽기를피한다. 기존null-script특화API는변경하지않았다. 전체RAM/state/port transaction,bank시작·종료와callee port순서,명시반복한도와하위helper지원제약을확인했다. CLI는fixed/banked loader와RAM/resource/port alias검사를사용하고성공뒤출력한다.

Unit은null targetclamp,비영script,script로motion/placement/wait를설정하는실제composite호출,metadata인접byte보존,A3보존,후반placement실패의전체RAM/state/기존ports rollback을검사한다. 전체make Python175/C++111/경고0,로그artifacts/scene_general_initialization_build_test.log.

## 원본 비교 검토

메인이observer/verifier를읽었다. Original2790/3ef2를호출전fixture생성에사용하며1a5a4 내부는callee reset/대체없이연속실행한다. 실제bank2/3전환에따라CPU200000창을바꿔map/palette자료를읽으며ROM와bankpayload불변·MMIO읽기0·RTS/A7+4를확인한다. Resource dedup identity에는CPU뿐아니라ROM bank도포함하도록보강했다.

Source창10개211행과59catalog record의script/target rawfield를재생성했다. Canonical41script,target0및59실제입력쌍의관찰을확인했다. 메인이directory인자를사용해canonical첫조건을별도로실행하여RAM과orderedports가원본자료와같음을확인했다. Python검증만가능한환경으로한정하지않고C++CLI directory사용법도확인했다.

최종221조건/오류111조건/ordered3,176,113ports가통과했다. 메인은native/verification의모든fixture·RAM/port hash·14register일치와현재458resource/manifest/context/binaryhash를확인했다. Phase최대13회,map성공856회,placement102회,allocation거절23회가관찰됐다. 4CLIsequence8호출중4는실제이전출력을사용하되target/script/parent는명시host입력이다.

Native SHA256 `7cf8f965dd1b774eafff1ad73400eab54dca1a8373f8a75ce6cb14557ddffa6e`. Verification SHA256 `950e3dd90209d2efd6a6629bf1568996396fb6005bede6e79df0f2ae290316eb`. CLI SHA256 `ec40eaeb8e7f0d379c841c331629552fc38a47851a84385cafc5d1ce2c13c163`. 초기192조건통과뒤큰target/debug별분기와승계를추가하여최종전체221조건을검증했다. 기존부분시험을최종개수에합산하지않는다. 자연scheduler·IRQ·화면·callback실행을이helper검증으로대체하지않는다.

## 다음 경계

47a94의일반initializer반환후e8a1c/48398/e905c와480bc가남아있다. 메인이후속원본을읽고scene-general-initialization.md에raw호출계약과미확인사항을기록했다. 특히e905c의2a28호출은기존D1/D3부분register API만으로전체연결을주장할수없다. 전체goal은active다.
