# Opcode10 indexed draw의 전체 상태 구현 계약

기준 `27cadc4`. 원본 canonical BE SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 고정 CPU 주소는 ROM 파일 오프셋과 같다. 메인이4a22c..274 및4a1dc..22a의 원본 명령을 읽고 기존 draw/callback 복귀와 구분했다. 이 문서는 다음 C++ 구현 계약이며 구현 완료 보고가 아니다.

## 원본 선택 순서

1. `4a22c MOVEQ0 D0`, selector BYTE(A1)+→D0, ADD.W D0,D0. A2=4a76c, WORD(A2+signed16(D0.low))→D0.low. selector는BYTE라 이 첫 인덱스는0..1fe다. 필요한 raw WORD 창은 `[4a76c,4a96c)`512byte이며 기존wide MS5D 안에 있다.
2. `4a23c` length WORD(A1)+→D1.low. D1 상위WORD는 보존한다. 이때 A1이 list base다. `4a23e PEA(A1,D1.W)`는 **signed16(length)**를 더한 list end LONG을 stack에 저장한다.
3. `4a242` BYTE(A6+signed16(D0.low))→D0.byte. 조회 WORD의 bits8..15를 지우지 않는다. 이 읽기는 length0에서도 수행한다. `4a246 LSL.W3 D0`은 그 lowWORD 전체를16bit로 wrap하며 이동한다. D0 상위WORD는 MOVEQ0 이후0이다.
4. `4a248 CMP.W D1,D0`, `4a24a BCC`는 **unsigned16(index)>=unsigned16(length)**이면 그리기를 생략한다. 길이와 인덱스를 둘 다 signed로 비교하면 틀린다.
5. 선택된다면 BYTE(list base+signed16(D0.low))가04인지 검사한다. 다르면 실제 원본은4a258 TRAP15다. checked 구현에서는 명시적 실패로 처리하며 no-op 성공으로 만들지 않는다. 그뒤4a25a..267의 assertion 문자열을 실행 코드로 재구성하지 않는다.
6. `4a268` A1=list base+signed16(D0.low)+1, `4a26c BSR4a10c`. 기존 draw가7operand BYTE와 실제 register/skip/sprite/PVC 효과를 처리한다.
7. skip 또는 draw 복귀 후 `4a270 MOVEA.L(A7)+,A1`으로 **저장한 list end**를 복원하고4a272→49ffe dispatch한다.4a276을 거치지 않으므로 상태포인터 LONG(A0)를 쓰거나 D6=A1로 만들지 않는다.

모든 BYTE/WORD/LONG 접근은 실제 순서와 필요한 span에 맞춰 검사한다. 선택 조건은 index<length뿐이다. **index+8<=length라는 추가 조건을 만들지 않는다.** 원본 length7/index0은 header 뒤8byte를 읽을 수 있다. 제공된 script window가 실제 opcode/operand bytes를 덮어야 하지만 선언된 length가 반드시8의 배수일 필요는 없다.

end 계산과 선택된 record 주소 계산은 signedWORD를 사용하지만 비교는 unsignedWORD다. 예를 들어fff8/fff0 길이는 큰 unsigned 길이면서 list base보다8/16byte 앞의 주소를 end로 저장한다. 이 주소에 다른 유효 명령이 있을 수 있다. 일반적인 vector/list 길이로 치환하면 안 된다. 계산은 넓은 signed 타입으로 하고 표현 범위 밖 주소는 checked 오류로 처리한다. end의 script bytes를 미리 읽거나 window 제공을 선제 요구하지 않는다.

## Draw 복귀와 실제 대기 프레임

S를10 진입의 A7이라 하면 PEA가 S-4에list end, BSR가 S-8에4a270을 저장한다. draw는 A0/A1 LONG과 bank WORD, callee return4a200을 추가한다. 실제 cd58 대기에서 다음 프레임을 관측했다.

| 저장 위치 | 의미 |
| --- | --- |
| S-22 | return4a200 LONG |
| S-18 | saved bank WORD |
| S-16 | draw saved A0 LONG |
| S-12 | draw saved A1 LONG: selected record+8 |
| S-8 | draw return4a270 LONG |
| S-4 | saved list end LONG |

`saved_a1`과 `saved_list_end`는 서로 다른 값이다. 대기 중 object index, header length, selected opcode/operand 또는 현재 object를 바꿔도 캡처된 현재 sprite를 마무리하고 원래 list end로 복귀해야 한다. list end에서 다음 명령을 읽을 때는 현재 RAM을 읽는다.

원본의 sentinel/음수timer/flash skip도 list end를 복원하지만 cd58에 진입하지 않으므로 저장 bank/draw frame이 없는 경로다. draw가 정상 완료하면 기존4a200 bank/PVC, MOVEM.W D0/D7 부호확장, A0/A1 복원을 재사용한 뒤 별도로 list end를 복원한다. callback용 복귀 helper를 사용하면 잘못된 pointer write와 D6 변경이 생긴다.

## 확정할 상태·CLI 연결

- `AnimationExecutionState`에 uint32 `saved_list_end`를 추가하고 기본값0으로 한다. phase3은 indexed sprite pending이며 sprite.waiting=true, callback metadata는 모두비활성이다. phase0/1/2에서는 saved_list_end=0을 요구한다.
- phase3 재개는 cd58 wait만 실행한다. hold는 list/table/object prefix를 재조회하지 않고 MS5A/MS5D가 없어도 반환할 수 있다. actual sprite callee의 canonicalA5 제한을 유지하되 대기 중 A6를 미리 검증하지 않는다.
- 해제 후 saved_list_end를 별도 local에 보존하고 기존 draw_return을 실행한다. A1=list end, saved_list_end=0, phase0으로 복귀한 뒤 다음 dispatch를 수행한다. D6은 draw의 실제 결과를 유지한다. pointer write를 추가하지 않는다.
- 기존 세 API overload 모두10과phase3을 지원하도록 확장한다. 이 명령에는 외부 sound 입력이 없으므로 별도 API/CLI를 만들지 않는다. sound callback1f/phase2의 기존 external-input overload 제한은 그대로다.
- 기존 일반CLI는20→21개의숫자로 확장하며 SPRITE_WAITING 뒤 SAVED_LIST_END를 추가한다. JSON21→22개key다. fullsoundCLI는 공유하는21개숫자 뒤 callback4개와EXTERNAL을받아 총26개숫자/27JSON key가 된다. 두CLI는 새 `saved_list_end`를 항상 반환하고 phase3의carry는null이다.
- 세 원본 비교 도구의 shared input/output schema와 초기상태/기대값을 함께 갱신하고 기존4opcode/control/sound 회귀를 전부 다시 수행한다. source resource 형식은 바꾸지 않는다.

## 근거와 아직 남은 범위

원본 관측 도구 `observe_animation_indexed_execution.py`는846조건/854단계와 네sameCPU대기연쇄를 제공한다. SHA256 `db3247ceba5327719b84882b7d1abe006f0e30c87d28642ed7c2f9a9f75a6508`. 실제S-22 프레임, length0의fieldread, length7의8byte읽기,fff8/fff0의signedend, retained highBYTE와POISON후capturedresume를 포함한다. 모든selector/length조합·자연게임실행은 증명하지 않는다. 기존known fixed script에는0c/14/10이 함께 있으므로 실제 연결된script의 원본 실행과 C++ 비교도 후속으로 확인한다.

실제 리소스 범위와 알려진8개list는 `animation-indexed-resource-spans.md`, 프레임 상세는 `animation-indexed-continuation.md`를 따른다. 아직 C++10/phase3 구현과 전체 통합은 미완료이며 다른opcode·callback·상위흐름·자연scheduler/IRQ·직접플레이를 전체Goal에서 제외하지 않는다.

## 분석 단위의 최종 재검증

메인이 합성 목록846조건/854단계를 전부 메모리에서 다시 실행하여 전체 RAM,15regs,carry,ordered PVC3564개,read/write/PC/stack trace와 입력6개/단계 파일3416개의 현재 해시를 대조했다. 원본 보고서를 덮어쓰지 않았다.

`observe_animation_indexed_fixed_scripts.py`는 기존 MS5A 원본 범위65f56..662c2와 실제0c/14/10 경로를30조건에서 실행한다. 보고서 SHA256은 `7f50c9d4ddf4023e47dd22abc6849cbd6322bd4916f2e620a04a2ca78b61fd37`이며 독립 Sol이30조건/30RTS 전체 RAM15regs/trace/PVC300개와 입력9개/산출물120개 해시를 확인했다. 실제 도달한 indexed 명령은65f64와6605a 두 곳이다. 알려진8개 전체 실행이나 자연 게임 도달성으로 일반화하지 않는다.
