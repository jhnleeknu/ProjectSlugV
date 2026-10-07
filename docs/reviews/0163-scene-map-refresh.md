# 맵 스크롤 갱신 helper 리뷰

Baseline `8009b90`. 이전goal turn은183c6 전송과secondary리소스를통합한progress다. 메인이16f0e/18702/1861a/18656의원본명령을읽어계약을제공했고sol이구현·원본반복실행·비교를담당했다. 메인이최종core/CLI/unit/nativeharness/verifier와보고서를읽고아래수정을요청·확인했다.

## 제어 흐름과 정수 연산

Column control의DBRA zero-count는65536반복이며후퇴/전진cursor와byte/word register부분보존을재현했다. Node2e descriptor는columns진입시에재로드한다. Wrapping의초기A1과이descriptor가같다고가정하지않는다. DIVU/SWAP은unsigned16bit coordinate를나눠quotienthigh/remainderlow를만들며signedmodulo와다르다.

Wrapping의각183c6호출후MOVEM.W sign-extension과마지막대각호출의미복원차이를보존한다. Map dimension과flag는helper이후LIVE로읽는다. Full refresh는원본WORD상수/ASR4를사용하고moved refresh는xstrip호출후yflag/좌표를읽는다. MOVEQfa는fffffffa이다. Port순서는내부전송마다append하며late실패는호출전체RAM/register/ports를되돌린다.

기존transfer_scene_map본문은변경하지않고같은번역단위의private 주소도구를재사용했다. 새로운MS5D규격이나게임데이터를도입하지않았다. 전체CCR/stack/자연scheduler를지원한다고주장하지않는다. Column search1048576회와하위transfer cell1048576개의임시한계는문서화된미해결범위다.

## 리뷰 수정

LIVE descriptorwidth unit이width2→33으로변해도둘째column1은cachedwidth2와LIVE33에서둘다통과했다. 메인이이검사의변별력부족을발견해초기width1로바꾸도록요청했다. 현재둘째column은LIVE33일때만쓰이며수정한단위를다시통과했다. 엔진binary는그뒤변경없다.

초기원본harness가18702입력A1을descriptor로설정하지않아invalidread를일으켰다. 18702의선행A1읽기계약에맞게fixture를수정했고실패증거를별도보존했다. 원본실패를C++성공으로대체하거나호출중context를재설정하지않았다.

메인리뷰에서비power-of-two height의ffff좌표DIVU4조건과초기A1≠node2e6조건을추가했다. 또추가검증모드가binaryhash만보고이전positive결과를재사용하던문제를발견했다. Resources/hash/count/현재nativeprefix정확serializedSHA/각case의entry·RAM·ports일치검사를추가했다. Observer추가모드도source/완료상태/fixture/inputRAMhash를확인하고중복extra를거부한다. 마지막에는재사용없이전체1744조건을다시C++와비교했다.

## 최종 검증

원본1744조건은18702 1322개,1861a18개,18656 282개,16f0e122개다. Canonical descriptor72개,4wrapflags,registerhigh2,slot0/ffff,경계좌표,양/음이동과NULLdescriptor,합성RAMcolumncursor/default/sentinel/zeroDBRA를포함한다. 모두원본RTS/A7+4로복귀했고내부호출중contextreset은없다. Native ROM과bank payload는변경하지않았다.

전체RAM/13register/ordered23636ports가C++와일치하며CLI오류35조건도기존입출력파일을보존했다. RawSR은참고관찰이며전체flag동등성claim이아니다. Canonical nonnull column리소스가확인되었다는의미도아니다.

- Native SHA256 `867c7a7a892dc130c5fc37c91a407f75a85e307cf527e747e72abd3cdfa8073b`.
- 최종전체비교 SHA256 `2ec30f6b5727a14a977d3d1d525a5a1c02d253580749d134790dc4bd7ba45944`.
- Binary SHA256 `4f12a22cb671a3925fab9e8f2877f70ae7676bfaa27bf937c2234a572ebf982e`.
- 기존183c6 회귀492/오류29/16620ports도통과했고현재report SHA256은 `9ce11ab6a2fe4b75fbeeb91db32c02fad42f94f55bed9e9ae68681d7d1ce0404`다.

전체make시Python162/C++105/경고0을확인했다. 이후LIVEunit수정은해당unit만재실행했고검증도구변경은별도검사했다. 메인이현재binary/모든resource hash와보고서수치를재확인했다.

증거재사용guard의합성8개를 `tools/tests/test_scene_map_refresh_guards.py`로보존했고전체Python170tests exit0을확인했다. ROM이나이전보고서없이binary/resource/nativeprefix/case변조와중복추가를검사한다. 로그는 `artifacts/scene_map_refresh/python_guard_suite.log`다. 엔진binary는이후변경하지않았다.

## 다음 작업

19e64 path handler와16ff8 descriptor설정,1afda register승계,전체1a7a8 및일반1a5a4/47a94 진입연결이남아있다. 다회CLI호출승계와자연frame·직접플레이가능스테이지화면도미완료다. 전체goal은active로유지한다.
