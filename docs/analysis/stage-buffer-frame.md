# Stage buffer frame 4aa88 구현과 검증

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 fixed 첫1MiB이므로 CPU=ROM offset이다. RAM은CPU100000..10ffff, A5=108000이다. 메인이 원본4aa88..4abc0 및4b784..4b82e를 직접 읽은 계약이다. 아래 범위의 C++ 구현과 원본 실행 비교를 완료했다.

## 4aa88 정상 처리

Debug 검사 이후4aafe에서D7=0,A0=LONG RAMdc88을읽는다.16개의WORD에대해각각LSR.W (A0)+를실행한다. 최종A0가unsigned10dc88이상이면A0=10db88로설정하고LONGdc88=A0를쓴다. 주소범위를논리ring내로강제하지말고실제16개의순차read/write와그뒤비교순서를구분한다.

BYTEdb85를db84로복사하고db85=0; BYTEdb87을db86으로복사하고db87=0. BYTEf001.bit0이켜져있고(BYTE4cab|BYTE4cb1)&80이비영이면db84=ff다. 이때D0.byte의중간변화는뒤의MOVEQ로덮인다.

A4=10d746,A3=10d918을설정하고BYTEd744.bit7을토글한다. **이전bit가0일때** A3/A4를교환한다. D1=ffffffff를설정한후WORD(A4+1d0)=0. 그후D0..D7을각각0으로만들고A4+=d0(hex208). MOVEM.L D0-D7,-(A4)를6회, D0-D3,-(A4)를1회실행해총208byte를뒤에서앞으로지운다. 최종A4는선택한버퍼시작이고A3는다른버퍼시작이다. A0는ring진행후주소, A1/A2는debug가없으면보존한다. A6는정상처리에서바뀌지않는다.

## 앞선 debug16-slot 처리

BYTE10f001.bit7이켜지면원래A6를stack에보존한다. A4=10daf8,D7=0으로시작해각8byte slot의LONG(A4)를A6, LONG(A4+4)를A0로읽는다. A6/A0중하나가0이면skip. 비영이면D6.byte=BYTE(A6+6d)&0f이며D7.byte와같을때만호출한다.

호출전A4 LONG/D7 WORD를보존하고A0+=4,D7=0000122b로4b784를호출한다. 반환후D7는**하위WORD만복원**하고A4를복원한다. WORD RAM0010=0, WORD port2ffff2=1000, WORD port2ffff0=0을순서대로쓴다. D7.low+=1,A4+=8 후unsignedA4<10db78이면반복한다.16slot종료후원래A6를복원하고4aafe로간다. Debug내에서발생한A1/A2반환효과는정상경로가덮지않는한남는다.

## 4b784 두 sprite 제출

D1=ffff0000. BYTE(A6+15).bit2가켜지면D1.low=4. LONG(A0)+를D0로읽는다. 같은flag.bit0이켜지면D0상위WORD를NEG하고D1.bit0설정, bit1이켜지면D0하위WORD를NEG하고D1.bit1설정한다. SWAP/ADD.W(A6+42)/SWAP/ADD.W(A6+46)으로좌표를더한다.

D0/D1/D7/A0의LONG을stack에보존하고D5=ffffffff,cd58을호출한다. 반환후A0/D7/D1/D0를역순복원한다. 이어WORD(A0)+를D2.low,다음WORD(A0)+를D3.low로읽는다. D1.low ^=3. Objectflag.bit0이면D2.low NEG,bit1이면D3.low NEG. D0상위WORD에D2.low,하위WORD에D3.low를더한다.

이번에는A0 LONG만보존하고D5=ffffffff,cd58을두번째호출한다. A0를복원한뒤WORD RAM0010=0, WORD port2ffff2=1000, WORD port2ffff0=0을쓰고RTS한다. 다른register는두번째sprite제출결과대로남는다. D1.bit6은이구성에서켜지지않는다.

둘중어느sprite에서도대기할수있으므로각호출지점의stack보존값과상위slotloop복귀상태를유지해야한다. 첫대기재개뒤두번째좌표WORD를읽는것은live읽기이며미리캐시하면원본과달라질수있다. 기존 sprite 실행 API를 재사용하고 단계별 저장 상태를 유지한다. 원본 전체 MMIO 실행은 Unicorn으로, debug-off 경로는 독립 Musashi로도 비교했다.

## 구현을 위한 메인 확정 상태 계약

전체4aa88을하나의API로연결한다. 기본register13개와현재A6를포함하며,phase0은fresh/완료,phase1은4b7d4의첫sprite대기,phase2는4b80e의둘째sprite대기다. Pending에는원래outerA6,slot A4/slot D7 WORD,첫sprite의savedD0/D1/D7/A0를저장한다. 둘째sprite에서는savedA0를둘째호출전값으로바꾼다. phase1재개후saved4LONG을복원하고크기WORD와objectflag를live로읽는다. phase2재개후A0만복원한다. 그뒤helper의bankreset,outer slot복원과bankreset,다음slot을순서대로실행한다.

CPU bank선택은RAM0010shadow와구분한다. API상태의bank2/3을실제현재mapping으로전달하고fixed/해당bank MS5D를선택한다. 초기4aa88호출자는보통앞선1a73c의bank2reset결과를전달하지만API는bank3도명시적으로지원한다. 각4b816및4aad8reset은RAM0010=0과두portwrite를게시한뒤bank2를선택한다. RAM0010이alias로바뀌었다고그자체를hardwarebank전환으로해석하지않는다. 각API호출의ports는이번호출에서발생한write만순서대로제공한다. 오류는RAM/state/기존ports전체를보존한다.

완료시phase와savedmetadata는0으로정리한다. Pending metadata는실제slot범위10daf8..10db70/stride8와index0..15의일치를검사한다. 이방어검사는원본의임의손상된stack을실행한다는주장이아니다. 첫 제출 복귀 후 더 이상 필요 없는 saved_d0/d1/d7은 0으로 정리한다. 이는 원본의 남은 stack bytes를 재현한다는 뜻이 아니다.


## 검증 결과와 재현

`StageBufferFrameState`와 `step_stage_buffer_frame`은 C++11로 구현했다. CLI 인자와 이어 실행하는 방법은 `engine/README.md`를 따른다. 기본 cd50 callback만 지원하며 다른 callback이 실제 필요하면 오류다. 두 번째 제출 대기 재개는 이미 끝낸 좌표 읽기나 callback을 다시 실행하지 않는다.

```sh
make -j2 all test
.venv/bin/python tools/inventory_stage_buffer_frame.py
.venv/bin/python tools/observe_stage_buffer_frame.py
.venv/bin/python tools/verify_stage_buffer_frame.py
```

- 원본 659조건·695단계의 전체64KiB RAM,14register,bank/phase/저장 상태 및 순서 있는 포트 쓰기1,340건이 실제 CLI 결과와 일치했다. 조건분기20개 중19개는 양쪽을 관측했다. cdb2의 deferred 분기는 이 호출자가 bit6을 설정하지 않아 normal 쪽만 관측했다.
- 14개 대기 chain에는 첫/둘째 모두 대기4개, 처음부터 둘째만 대기4개, 앞 슬롯의 포트4건을 게시한 뒤 다음 슬롯에서 대기2개가 포함된다. 원본 CPU/stack을 유지하고 외부 RAM 변경을 명시했다. 첫 대기 재개10회는 live 크기/flag를 읽고 둘째 재개8회는 이를 다시 읽지 않았다.
- debug-off337조건은 독립 Musashi에서도 전체 RAM·14register가 일치했다. Unicorn hook은 실행 중 SR을 읽지 않는다. 원본 fixed ROM과 실제 bank payload 불변을 각 단계에서 검사한다.
- CLI 오류196조건, 직접 API 오류 원자성5조건과 성공 시 기존 ports 교체를 검증했다. 정상 frame4회 중3회는 호스트 RAM/register 수정 없이 직전 출력을 소비한다.
- 메인이 전체 도구와 구현을 읽고 실제 CLI 검증을 다시 실행했다. 저장된695단계의 원본 순서 있는 RAM writes를 독립 재생하여 snapshot과 일치함을 확인하고 현재 provenance와 branch 집계도 대조했다. 전체make Python182/C++125,경고0.

기존458 MS5D 목록에서 fixed `scene_scripts/scene_0488c4.ms5d`(CPU/ROM0488c4),bank2 `scene_scripts/palette_bindings_200504.ms5d`(CPU/ROM200504),bank3 `scene_maps/primary_lookup.ms5d`(CPU200008/ROM300008)의 원본 검증된8byte를 실제 로더로 소비했다. 좌표 offset을 조정해 첫 제출이 clipping을 통과하도록 검증했으며 bank3→reset2→bank2 연속 조회도 확인했다. 이는 해당8byte를 자연 실행 sprite record라고 분류한 근거가 아니다. 신규 리소스는 만들지 않았다.

Native SHA256 `6b77299d0809fd21439effba2e1edf8a27cd32e7f2287ef25da009693320850c`.
Verification SHA256 `3a96ceb91f257dbcd2e1cd94694d73c178f2ad85101d3aa938d5357849d4f197`.
CLI SHA256 `e7cb83ef01ec4e7c09171e545ec440628047b7d986eafdbd57c5d07819e8e21d`.
Inventory SHA256 `b9533ff7a63016ad3fa4b770579ec76dffce253aeeeb51e2e2975a5cd4e5125a`.

임의 callback, 전체CCR, IRQ timing, 자연 scheduler와 전체480bc/직접 플레이는 후속 범위다. 검증 오류의 출력 보존은 계산·입력검증 실패에 대한 것이며 파일 저장 중 I/O 실패의 두 출력 파일 원자성을 보장하지 않는다. 리뷰0184 참조.
