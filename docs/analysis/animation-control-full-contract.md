# Animation 분기·콜백 전체 상태 확장 계약

기준은 `c8595e0`의 전체 상태 API와 기존 animation 계약이다. 이 문서는 후속 구현 계약이며 새 C++ 지원 완료 보고가 아니다. 원본 `maincpu.decrypted.be.bin` SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 고정 CPU 주소는 ROM 파일 오프셋과 같다. 메인이 해시 검증된 원본을 padded decoder로 읽고 원본 바이트·제어 흐름을 대조했다.

## 0c 조건 분기

dispatch 후 A1은 operand 첫 BYTE를 가리킨다.

1. `4a3b8` MOVE.B(A1)+→D1.byte, `4a3ba` SNE.B D1: 0이면00, 그 외ff. D1의 상위24bit는 보존한다.
2. `4a3bc` MOVE.W(A1)+→D0.low, `4a3be` ADD.W D0,D0. 두 배를16bit로 wrap하며 상위WORD를 보존한다.
3. `4a3c0` A2=4a76c, `4a3c6` WORD(A2+signed16(D0.low))→D0.low. signed 인덱스를 unsigned 인덱스로 바꾸지 않는다.
4. `4a3ca` LONG(A1)+→D7. 분기 불일치여도 target을 먼저 읽는다.
5. `4a3cc` BYTE(A6+signed16(D0.low))를 live RAM에서 검사한다. `4a3d0` SNE.B D0은 최하위BYTE만00/ff로 바꾸므로 offset의 bits8..15와 기존 bits16..31은 남는다.
6. `4a3d2/3d4` D0.byte와 D1.byte가 다르면 현재 A1을 유지하고, 같으면 `4a3d8` A1=D7이다.
7. `4a276/278` D6=A1 전체32bit, LONG(A0)=D6 후 dispatch한다. 이 저장이 다음 RAM script를 덮을 수 있으므로 다음 fetch도 live다.

handler 자체의 PVC·callee는 없다. 마지막 carry는 이후00/28/기타 명령에서 정해지며 중간 CMP의 carry를 반환하지 않는다. 전체RAM 크기와 각 reached span을 검증하고 실패는 외부 상태·ports를 변경하지 않는다.

전체 WORD selector는32768개의 signed-even offset(-8000..7ffe)을 만든다. 따라서 가능한 raw WORD 조회창은 `[4276c,5276c)`의65536byte다. 이 창의 SHA256은 `00fd4b3f850678709eb4da84d61addd145491b9a6f0afc5637b8bd273ad32bd4`다. selector와 selector+8000은 같은 주소를 읽는다. 이 계산은 모든 값의 자연 사용 또는 하나의 논리적 표 존재를 뜻하지 않는다. 기존 `[4a76c,4a88e)`290byte 창은 기존 범위에 유효하지만 전체 selector에 충분하지 않다.

## 14 콜백 프레임

`4a408`에서 현재 A0를 LONG으로 저장한다. D0=MOVEQ0, selector BYTE를 읽고 WORD 두 배를 두 번 계산하여0..3fc를 만든다. A0=4a500, `4a418`에서 callback LONG→D7, `4a41c`에서 operand LONG→A0이다. operand 뒤 A1 LONG을 저장하고 A1=D7, live bank WORD(A5-7ff0)를 저장한다. shadow0 뒤 PVC WORD1000→2ffff2, WORD0→2ffff0을 출력한 후 `4a43c JSR(A1)`을 실행한다.

callback 진입 stack의 SP+0에는 return4a43e, +4에는 bank WORD, +6에는 saved A1 LONG, +10에는 saved A0 LONG이 있다. callback의 내부 stack과 이 외부 프레임을 혼동하지 않는다.

return4a43e는 **복귀 시 live A5** 기준으로 bank WORD를 복원한다. D0/D7의 lowWORD를 저장하고 shadow를 읽어 `((bank+1)<<12)&ffff`를 PVC2ffff2에,0을2ffff0에 쓴다. `4a460 MOVEM.W`는 두 저장WORD를 signed16→32로 복원한다. 이후 A1/A0 LONG을 복원하고4a276의 D6=A1/LONG(A0)=D6를 실행한다. 보통 MOVE.W처럼 상위WORD를 보존하면 잘못된다.

full BYTE callback 조회창은 `[4a500,4a900)`1024byte이며 위0c raw window 내부에 완전히 포함된다. 별도 겹치는 MS5D 두 개를 동시에 공급할 필요가 없다. callback 주소를 조회했다는 사실만으로 임의 target 실행을 지원한다고 주장하지 않는다.

## 확인된 1d/1e callback

table4a574→2b3e8,4a578→2b3fa는 각각 BYTE(object+7c/+7d)를 사용한다. D0 전체0 뒤 BYTE를 읽고 WORD×4하여0..3fc를 만든다. LONG(A0+signed16(D0.low))를 먼저 읽고 LONG(object+78)에 쓴 뒤 RTS한다. object의 인덱스와 source LONG은 호출 시 현재 RAM 값이며 alias가 있으면 이 읽기·쓰기 순서를 유지한다. source는 live RAM 또는 명시적으로 공급한 fixed MS5D 창으로 해석한다. fixed6431a의 기존1024byte 창을 재사용할 수 있다.

1d/1e에는 내부 대기나 sound 호출이 없다. D0는0..3fc, D7은 callback 주소로 돌아오지만 외부 MOVEM.W 후 D7은 lowWORD 부호확장값이 된다. A0/A1은 외부에서 복원하고 A2 등 다른 register는 이 callback 자체에서 바꾸지 않는다. canonical A5를 무조건 요구하지 않고 실제 reached RAM 주소를 검사한다.

## API 연결과 남은 결정

- 기존 호출을 유지하는 overload에 `const std::vector<FixedDataResource>& windows`를 추가한다. 기존 인자형은 빈 windows로 위임하여 기존4opcode 동작을 유지한다. 새 opcode의 reached fixed 조회에는 유일한 완전한 window가 필요하다.
- MS5A는 명령 fetch, MS5D는 조회 데이터의 provenance를 구분한다. RAM은 항상 현재 RAM이다. 모든 산술에서 실제16/32bit 폭과 signed 주소 덧셈을 명시한다.
- CLI는 script/data를 식별하여 기존 MS5A·MS5D loader로 읽고 모든 입력을 output alias 보호에 포함해야 한다. loader 오류를 미사용 경로라는 이유로 무시하지 않는다.
- 14/1f→47672는 기존 full sound lookup을 재사용할 수 있지만 내부 word sound 대기와 animation 외부 저장 프레임을 함께 보관해야 한다. 현재 phase1(sprite 대기)로 이를 대신하지 않는다. 실제 동일 CPU 대기·재개 근거와 별도 상태 계약이 필요하다.
- 임의 callback, 남은 opcode, banked lookup, 자연 IRQ와 전체 gameplay는 계속 전체 목표의 미완료 항목이다.0c/14 일부 콜백의 증거로 이들을 완료 처리하지 않는다.
