# 47c04 초기 활성화 구간과 후속 callback 경계

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 CPU 주소와 ROM 파일 오프셋이 같다. 메인이 원본 47c04..47c6c 및 모든 직접 helper를 읽었다. 명령 근거는 `artifacts/stage_activation_static.json`이다. 이 문서는 47c6c 도달까지의 계약이며 47c04의 전체 실행 또는 stage 활성화 완료를 뜻하지 않는다.

## 순서와 live RAM

1. BYTE(A5+5684)가0이면 9060으로 absolute107def를0으로 쓰고,4e254로 A5+5d1f=ff,+5d20=0,−75be=0,−74fa=0을 순서대로 기록한다. 이어 BYTE(A5+5683)의bit4를 세운다. 다른 레지스터는 이 helper들에서 변하지 않는다.
2. MOVEQ1 D0 뒤 BYTE(A5+5684)와 AND한다. bit0이 켜져 있으면477a2를 실행한다. 실제 ddfa4 명령표와 블록 출력의 전체 레지스터/ports를 연결해야 한다.
3. MOVEQ4 D0 뒤 같은 flag byte를 다시 읽어 AND한다. bit2가0이면ca76으로 BYTE(A5−769b)=ff를 기록한다. 이어 항상ca56으로 BYTE(A5−7699)=0을 기록한다.
4. BYTE(A5+5683)의bit2를 세운다. BYTE(A6+7c)를 D0.byte에 읽는다. 직전 MOVEQ4 때문에 상위24bit는0이다. unsigned D0.byte<6일 때만c3c0을 호출한다. c3c0은 D0.byte를 BYTE(A5−cf)와 **signed BYTE** 비교하고 greater일 때만 대상 byte를 바꾼다. 80..ff인 기존값은 음수이므로0..5보다 작다. CMP의 N xor V 의미를 unsigned 비교로 대체하지 않는다.
5. BYTE(A6+7e)=ff, WORD(A6+20)=00ea, LONG(A6)=00047c6c를 순서대로 쓴다. 원본은 여기서 반환하지 않고 **47c6c로 fall-through**한다.

A5=108000일 때 flags는10d684, 비트 갱신은10d683, screen bytes는100965/100967, c3c0 대상은107f31이다. A6는 caller의 부모 object 주소다. A5/A6/RAM 영역의 alias를 임의로 배제하지 말고 각 읽기와 쓰기의 실제 순서를 보존한다. RAM word/long의 실제 정렬과 span을 확인한다. 초기화용 flag를 미리 캐시해 이후 read에 재사용하지 않는다.

블록 출력이 없으면 A0/A4,D1..D7은 이 구간에서 보존된다. 블록 출력이 있으면 기존 execute_stage_block_draw의 최종 상태를 유지하며 이후 D0만 재설정된다. 최종 D0는 읽은 parent+7c의 unsigned byte다. RAM/ports/15regs를 관찰할 수 있지만 A7/CCR/cycle/물리 mirror는 별도 문제다.

## 바로 이어지는 47c6c는 아직 별도 분석 대상

47c6c는 BYTE(A5+5684)가 비영이면47d3e로 간다.0이면 D0를0으로 만들고 WORD(A5+567e)를 읽어4e286을 호출한다. 그 후 같은 WORD를 다시 읽어0이면47eac로 간다. 비영이면4843c의 BCD 카운터 감소와ca70을 거친다. 4e286은35f0만 호출하는 출력 함수가 아니다. 아래 RAM·레지스터·사운드·팔레트 동작이 함께 있다.

- BYTE(A5+5d1f)=0이면 즉시RTS. D0.low>99ff이면7243/c904/4×2의35f0 tail call.
- 그 외 D2=0. D0.low>=0a00이면BYTE(A5+5d20)=0. 미만이면 해당byte를1감소시키고 borrow일 때D0.low를stack에저장, D0.low=1ac3으로3af8을실행, byte=1f를게시한뒤D0.low를복원한다. 사운드 제출은 실제 대기/재개 가능성이 있으므로 원자적 무조건즉시실행으로 바꾸지 않는다.
- 낮은 값의D2는 D0.byte를복사하고LSL.B3의carry에따라NOT.B한뒤LSR.B3으로 만든다. 8cda가D0/D1/D2/A1/A2 등을 바꿀 수 있으므로 부분상태API를 그대로 연결하면안된다.
- D0.low를저장하고 D0=12,D1.low=0a0d로8cda를호출한다. 복원한D0.low에서 두자리 nibble을선택해4e272의WORD표를읽고35f0을두번호출한다. 첫 호출 전SWAP D0가 상위WORD에도 영향을 주므로 결과를 화면 출력만으로 축약하지 않는다.

4843c는flagbit4와player상태10fdb6/10fdb7의값1 여부에따라동작한다. D0.byte에567f,D1.byte에567e를읽고 D0.byte−2의X를SBCD D2(0),D1에전달한다. borrow이면D0/D1을MOVEQ0으로전체초기화한다. 유효한 BCD 숫자만을 임의 가정하지 말고 원본CPU 의미를 검증한다.

47d3e의4847c는 두 번1bdde를호출하고 경우에따라4e166을호출하여carry를반환한다. 이후stage종료/다음stage/480bc frame으로갈라진다. 전체callback을복원하려면여기서원본carry를보존해야한다. 후속47f4a..480bc에는사운드여러제출,뱅크전환,애니메이션/팔레트/오브젝트작업및BIOS경로가있다. 분석구간을완료기준으로축소하지않는다.

## 8cda의 전체 레지스터 연결 계약

기존 set_palette_blend는 RAM 효과만 제공한다. 원본8cda..8d32를 메인이 다시 읽었으며 full adapter는 다음 상태를 보존해야 한다. D0.low=(incoming D0.low&ff)<<4이며 상위WORD는 보존된다. A1=104d92, A2=A1+D0.low이고 offset은0..ff0이므로 signed WORD indexing이 음수가 되지 않는다. A2+8의WORD가0이면 이 주소/레지스터 변화만 남기고RTS한다. 이 경우D2를clamp하지않는다.

참조WORD가비영일때 D2.byte>=32면MOVEQ32로D2전체를32로바꾸고,미만이면상위24bit를보존한다. D1.low가A2+c와다르면해당WORD와A2+e BYTE를쓰고A2+f bit7을세운다. 같으면기존weight와D2.byte를비교한다. weight만달라지면BYTE를쓰고D1.low와A2+a가다를때만bit7을세운다. D1/D3..D7/A0/A3..A6는보존하며A5를108000으로강제하지않는다. 포트쓰기나외부리소스읽기는없다. WORD slot주소와전체RAM수준비교로확인한후4e286에연결해야한다.
