# 전체 stage cue frame 리뷰

Baseline `5718c53`, branch `codex/stage-cue-frame-execution`. e8a48 신규core/header/CLI/unit,리소스packer,원본관측/비교도구,Makefile및문서를대상으로한다. 후속4aa88문서는원본분석초안으로만추가하며실행검증범위에넣지않는다.

메인이전체literal계약을정하고core/header/unit/CLI를읽었다. 요청flagclear와tag범위,XY/index WORD보존복원,2986실패후fallback에도node/lookup실행,A3보존,auto/nullstream반환A0+4,debug좌표/조건/status를대조했다. 대기재개가전체frame의앞부분을건너뛰는지확인했고중첩helper실패까지바깥transaction이되돌리는것을검토했다.

Packer전체를읽고원본catalog42head의8byte범위와53참조,128byte lookup의최대두WORD읽기주소,MS5Dheader/CRC/source/reload를확인했다. 메인재생성동일검사와오염430조건거부를수행했다. 독립audit후메인도기존187fixed×새45fixed의중첩0을직접재확인했다. Lookup뒤코드를논리record로해석하지않는다.

Observer/verifier전체를읽었다. Debug offset이전부0인초기coverage빈틈을발견해비영camera/offset32조건및원본중간register관측을추가하도록요청했다. 14조건의WORDwrap과정확한상위보존을검증한다. Stream와controlbyte가겹치는fixture에서는최종host설정순서를명시해의도한livegate를원본에서관측했다. 원본실행을바꾸거나실패를숨기지않고최종822조건으로증거를재생성했다.

최종822조건/838구간의RAM·14register·waiting/status가일치했다. 모든256tag/32index와42cuehead,143allocator/node호출(87성공/56실패),8동일CPU대기chain,4회전체frame chain을확인했다. Pending A7=STACK-4,최종A7=STACK+4이며외부새requestff/oddcue를재개가소비하지않는다. 오류150조건과unusedresource/status보존도통과했다.

메인이838저장RAM·입력승계·외부변경·PC/A7·register·branch·현재provenance를직접대조했다. 실제CLI검증도재실행해동일hash를확인했다. 전체make Python182/C++124/경고0, `artifacts/stage_cue_frame_build_test.log`.

Native SHA `c4e44fc73bf700b34396d1f00d339bd37661f0aa0a193f26eb492067d108f63c`, verification `b2ed87ee0acfde987c12333593ca3593e2c1920b21fafd1677137631bf64d033`, CLI `b97a6a7cf8fcde8ad4e543ead1523ef44d22f823e363fe287d92d45279e97690`.

이단위통합을수용한다. Wholeframe debug의bit6은0이라deferred경로는독립sprite검증범위다. 임의callback/전체CCR/IRQ timing/자연scheduler/직접플레이와전체480bc완료를주장하지않는다. 전체goal은active다.
