# 47a94 진입 본문과 480bc 연결의 후속 계약

메인이 canonical BE 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`를 정적으로 확인했다. 고정 CPU 주소는 동일 ROM 파일 오프셋이다. 이 문서는 후속 구현 계약이며 전체 본문 실행 완료를 뜻하지 않는다.

기존 stage_sound_initialization은47a94에서 멈춘다. 이후 원본은 다음 순서다.

1. A4=LONG(A6+76), A0=LONG(A4+2), D0.low=WORD(A4+e)를 읽고1a5a4 전체 scene 초기화를 실행한다.
2. A4=LONG(A6+76)를 다시 읽고 A0=LONG(A4+6)으로e8a1c cue 선택을 실행한다. 앞 호출이 live record를 바꿀 수 있으므로 첫 A4/포인터/target을 계속 재사용하면 안 된다.
3. RAM10d683의 bit1,bit3,bit5를 순서대로 설정하고48398을 호출한다.
4. 48398은30f4를 호출한다. 30f4는BYTE10fd8c→D0.byte, D0.low &=7, BYTE fixedROM30ec+signed(D0.low)→D0.byte 순서다. D0 상위WORD를 보존하며 다른 register를 변경하지 않는다. 48398은 결과byte를10d67e에 게시하고10d67f에ff를 쓴다. 이 표의8byte를 기존버전리소스로공급해야하며게임의난수함수로대체하면안된다.
5. A4=LONG(A6+76)를 다시 읽고 A0=LONG(A4+a)를 읽는다. A0가0이 아니면 LONG(A0)를 한번 더 읽어 A0로 만든다. D0.low=WORD(A4+e), e905c 전체 event 초기화를 실행한다.
6. LONG(A6)=47af0을 게시하고480bc로 tail branch한다. 따라서 이 본문의 최종 대기는480bc의 pending상태로 연결하며 재개 때 초기화/flags/callback 게시를 반복하지 않는다.

기존 initialize_scene, step_stage_cue_control(entrye8a1c), initialize_stage_events 및 새 step_stage_frame 계약을 재사용할 수 있다. event API는D0..D7/A0..A6를 포함하므로13레지스터 공통상태에A5=108000/A6를 명시적으로 운반하고 반환A5/A6효과를 확인해야 한다. 기록+2/+6/+a 포인터의 실제 MS5D 경계와 뱅크 의미를 원본실행에 근거해 확인한다. 이 후속 wrapper는 신규진입과frame재개를 구분하고ports 순서를 연결하며 오류transaction을유지해야한다.

메인이 원본 명령을 다시 확인한 정적 근거는 `artifacts/stage_entry_body_contract.json`이다. 30ec의 8바이트는 `60 70 80 90 90 90 90 90`이며 기존 `tools/pack_stage_events.py`가 만드는 `extracted/runtime/stage_events/lookup_0030ec.ms5d`에 이미 보존된다. 새 리소스 형식이나 중복 packer를 만들 필요가 없다. 이 계약은 A5=108000 진입을 전제로 한다. 47ab4/47aba/47ac0 및4839e/483a2의 실제 주소 계산은 A5 상대이므로 이 전제를 검증 없이 일반 A5 입력으로 확대하지 않는다.

47af0은별도의다음callback이다. 72f0을반복호출해carry1을기다린뒤 A0=LONG(A6+76),D0=0,BYTE(A0+1)→D0.byte,47b06+signed(D0.low)로indexedJMP한다. 47b06..47b22에4byte BRA8개가보이나잘못된BYTE를임의로나누거나정규화해서는안된다. 각분기와72f0의실제대기/IRQ관계는별도분석이다. 원본은480bc주소를LONG상수로갖지않는PC상대분기를사용하므로raw4byte검색만으로호출자가없다고판정하지않는다.

완료증거는 실제record/runtime리소스로원본47a94부터초기화와480bc를연속실행한전체RAM/레지스터/ports/pending 비교다. 다음47af0 callback의scheduler진입,자연적인플레이어활성화,화면과오디오동등성은별도검증이며현재미완료다.
