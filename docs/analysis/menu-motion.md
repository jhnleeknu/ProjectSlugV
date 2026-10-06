# 메뉴 열기·닫기 단계

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정CPU/파일a348은열기단계,a2be는닫기단계다. RAM슬롯은current pointer107f12로선택하며+4/+5가8.8형태높이word다.

## 갱신과 표시 순서

열기는**이전상태**로9b58테두리를그린다음목표높이byte(+c)의64배를높이word에더한다. 합은16비트wrap한다. 그결과가목표높이×256보다unsigned로크면목표값으로제한한다. 원본상위호출자의완료판정은이함수바깥이다.

닫기는항목수byte(+6)의64배를높이word에서뺀다. borrow가생기면0으로하고실제감소량을이전높이로한다. 갱신된높이로9b58을그린뒤`((새높이&ff)+실제감소량)>>8`행을00ff로지운다. 지우기시작주소는기존x/y주소의하위byte에새높이상위byte를ADD.B한값이다. carry를상위byte에넘기지않는다.

닫힌행을지우는루프도a018가림판정을쓴다. 그러나테두리와달리**가려져도주소를20증가**시킨다. 두루프의동작차이를보존했다. 종료한메뉴의스택제거와callback은a662이후의별도작업이다.

## C++ 연결

`open_menu_step`/`close_menu_step`는기존MS5D와테두리API를사용한다. 두함수는모든작업성공시에만RAM과FixedWrite목록을동시에교체한다. 높이0일때테두리가descriptor를읽지않는기존동작도유지한다. 가림판정은공통`menu_position_occluded`로공유하며같은slot검증을사용한다.

```
make all test
build/step_menu_motion open INPUT_RAM INPUT_MS5D OUTPUT_RAM OUTPUT_WRITES
build/step_menu_motion close INPUT_RAM INPUT_MS5D OUTPUT_RAM OUTPUT_WRITES
.venv/bin/python tools/verify_menu_motion.py
```

원본a348/a2be와경계560단계및실제메뉴초기화후연속16단계,총576단계에서전체RAM과포트쓰기의순서/값이일치했다. 실제메뉴는8회열기/8회닫기후높이0으로돌아온다. 경계는word wrap,소수부,목표/항목수0..255,flags별표시와가림을포함한다. 오류시RAM/출력보존및height0리소스접근생략unit검사가통과했다.

이는a370전체상태기계나메뉴문자/선택callback/화면타이밍검증이아니다. 원본의단계함수를C++로연결한범위이며픽셀단위완료를주장하지않는다.
