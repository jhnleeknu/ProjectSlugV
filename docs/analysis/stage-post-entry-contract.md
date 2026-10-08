# 첫 프레임 이후 stage callback 계약 — 정적 분석

이 문서는 다음 작업을 위한 메인의 정적 분석이다. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 아래 고정 CPU 주소와 ROM 오프셋은 같다. 명령 근거는 `artifacts/stage_post_entry_contract.json`에 저장했다. 실제 callback 전체 실행·플레이 완료 증거가 아니다.

## 47af0 gate와 dispatch

72f0은 A5-0x213의 byte를 D0.byte에 읽고 byte단위로0x80을 뺀 뒤 반환한다. A5=108000일 때 RAM107ded다. 이전 byte가0x80 미만이면 borrow/carry=1이며47af6 BCC가 반복하지 않는다.0x80 이상이면 carry=0이므로47af0으로 돌아간다. D0의상위24bit를 보존한다. 기존478de transition에도 같은 gate가 있지만 IRQ가 이 byte를 언제 바꾸는지는 별도 계약이다. busy loop를 타이머나 임의true로 대체하지 않는다.

통과 뒤 live LONG(A6+76)를 A0에 읽고 D0전체를0으로 만든 뒤 BYTE(A0+1)를 D0.byte에 읽는다. JMP47b06+D0.W는 원시 byte를 그대로 오프셋으로 쓴다. 정수 index로 나누거나 범위에 맞게 clamp하지 않는다. 정규 branch 시작점은 다음과 같다.

| record+1 | 원본 분기 | 후속 동작 |
| --- | --- | --- |
| 0 | 47b26 | caf0 화면 초기화, D0..D3=0,8c16 효과,47c04 |
| 4 | 47b3e | D0..D2=0,D3=20,object+7a=20,8c16,caf0,callback47b5c |
| 8 | 47b68 | D0..D2=0,D3=32,object+7a=32,47b4a로 공통 처리 |
| 12 | 47b76 | callback4fcce,D0.low=0으로28ae; 실패47b26,성공47be4 |
| 16 | 47b8c | callback4fd20,D0.low=0으로28ae; 실패47b26,성공47be4 |
| 20 | 47ba2 | live record+6 cue좌표e8af4,scene좌표WORD추가,callback4ff12 할당 및child+76/+78 게시 |
| 24 | 480b6 | 2a00 제거 루틴으로tail jump |
| 28 | 4809a | caf0,c364,callback480ac;parent+62가0이면RTS,아니면2a00 |

현재59개 canonical record의 해당 byte는12가40개,4가13개,0이2개,28이1개,24가3개다.8/16/20 경로는 branch table에는 있지만 이 catalog에는 없다. 이 사실만으로 미사용 기능이나 도달 불가능으로 단정하지 않는다.

47b5c는 object+7a WORD를1 감소시킨다. 이전 값이0이 아니면borrow가없으므로480bc로가며,0이면ffff를남기고47c04로간다.47be4는parent+62를0으로, D0..D3를0으로 만든뒤8c16을실행하고callback47bfc를게시한다.47bfc는parent+62가0이면480bc,비영이면47c04로이어진다. 성공한28ae의A0/A1등 실제레지스터반환을 보존해야한다.

## 아직 필요한 전체 helper 계약

8c16은A5=108000을직접설정하고D0..D3를변경한다. 기존set_palette_effect는RAM효과만반환하므로전체레지스터caller연결에단독사용하면안된다. D0..D2 signedWORD clamp,LSL.W8,delta SUB.W, D3.lowANDff 및최소duration1,deltaOR가0이면D3.low0과timer0,아니면DIVS의remainder상위WORD/quotient하위WORD를보존해야한다. caf0의기존API도노출하지않는레지스터가실제로불변인지원본으로확인한다. 부분레지스터API를전체동작증거로확대하지않는다.

47c04부터는9060,4e254,477a2,ca76,ca56,c3c0 등의호출과callback47c6c 이후진행이추가로필요하다.47af0의분기선택만구현하고이를stage활성화완료라부르지않는다. 전체연결을위해callee상태/호출순서/대기·IRQ/화면·오디오효과를단계적으로확정해야한다.
