# Stage region frame b4a2a 구현과 검증

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이 문서의 명령 주소는 fixed 첫1MiB CPU=ROM offset이다. RAM CPU100000..10ffff, A5=108000. 메인이 원본 전체5창(b4a2a..b4ab0,49392..493bc,1c028..1c052,b481e..b4850,4d9d6..4da08)을 읽어 확정한 구현 계약이다. 아래 범위의 C++ 구현과 원본 실행 비교를 완료했다. 이름 region은 편의 이름이며 모든 소비자를 조사해 충돌 판정 의미를 확정한 것은 아니다.

## 49392 활동 조회

A5=108000이 아니면 원본은 TRAP15다. API는 A5 고정을 전제로 한다. A0=100cb8; D0.low &=1; 결과가 비영이면 A0=100da8. BYTE RAMd68e의 bit(D0.low)를 검사하고 설정되었으면 carry=true, 아니면 false다. 앞선 ANDI.W가 C를0으로 만들고 BTST는 C를 바꾸지 않으므로 false를 이전 carry로 보존하지 않는다. Capstone의 btst.l 표기와 달리 memory bit test 대상은 BYTE다. D0 상위16비트 보존. A1/A4 및 나머지 register 보존.

## 4d9d6 영역 포인터 조회

D0.byte가0이면 A4=10dcba, 비영이면10dce6. WORD(A4)가0이면 A0=0으로 반환한다. 이때 D0/A1은 보존한다.

활성 WORD가 비영이면 D0 LONG=A6; D0.low=WORD(A4+6). 이 lowWORD가0이면 MOVEA.W D0,A0으로 A0=0을 반환하고 A1은 보존한다. lowWORD가 비영이면 A0=D0 LONG, A1=LONG(A4+8)으로 반환한다. A6 상위16비트와 저장된 lowWORD를 결합하는 동작을 임의로100000에 고정하지 않는다. 이 함수 자체는 만든 A0를 역참조하지 않는다.

## 1c028 fallback 조회

입력 D0 WORD를 저장하고4d9d6을 호출한 후 D0 하위WORD만 복원한다. 상위WORD는 helper 결과를 유지한다. A0가 비영이면 그대로 반환한다. A0가0이면 A0=100cb8; D0.low &=1; 비영이면 A0=100da8. A1=LONG(A0+56)으로 반환한다. 활동 slot 선택은 원래 D0.byte 비영이고 fallback 선택은 원래 D0.low bit0이므로 arbitrary input에서는 서로 다를 수 있다. A4는 helper 결과를 유지한다. 기존4d7a6의 lookup 리소스를 사용하지 않는다.

## b481e 교대 목록 초기화

D0.low=WORD RAM000e; D0.low &=1. 결과0이면 A1=10dd5c,A2=10dd98, 1이면 A1=10dd98,A2=10ddd4. D0 LONG=0. A1==A2까지 WORD(A1)=0, A1+=10(decimal)을 반복한다. 정확6WORD를 지우고 A1=A2로 종료한다. 나머지 register는 보존한다.

## b4a2a 전체 처리

WORD RAMdd48=8000; D0 LONG=0;49392. carry=false면 첫 게시를 건너뛴다. true면 D0 LONG=0;1c028. A1=0이면 건너뛴다. 비영이면 MOVEM.W (A1),D0-D3로4WORD를 읽고 각각32bit sign extension한다. D0.low +=WORD(A0+42), D1.low +=WORD(A0+46), 상위WORD 보존. 그후4개하위WORD를 dd48/dd4a/dd4c/dd4e에 순서대로 저장한다.

WORD RAMdd50=8000; D0 LONG=1;49392. carry=true면 D0 LONG=1;1c028하고 A1비영일때 같은 동작으로 dd50..dd56에 저장한다. 모든 RAM 읽기는 실제 실행 순서의 live 값이다. 첫 게시 영역을 두 번째 source/좌표 포인터가 가리키는 alias를 인위적으로 배제하지 않는다. 고정 활동mask d68e 및 slot dcba/dce6은 게시 영역과 겹치지 않는다. MOVEM의4WORD읽기는 후속coordinate읽기와 게시보다 먼저 완료한다.

A0=10dd58; BYTE(A0)가 비영이면1감소. A0+=2; BYTE(A0)가 비영이면1감소. A0+=2로10dd5c. b481e 호출 후 반환한다. ADDQ.W to address register는 주소 전체32bit를 증가시킨다. 최종 D0=0,A0=10dd5c,A1=A2는교대목록끝. A4와D1..D3는 실제 실행한 조회/게시경로의 결과를 유지한다. 전체A6보존.

## 구현 규격

`step_stage_region_frame(ram,entry,windows,SceneMapTransferState&,parent_a6,bank,bool& activity_carry,error)`의 C++11 API/CLI로5entry를지원한다. entry49392만 activity_carry를 원본 C결과로 갱신하며 다른entry는 별도의 API 입력값을 보존한다(전체 CCR 반환 주장 아님). bank2/3는 MS5D의 실제 mapping 선택용이고 본 단위는 전환/port출력을 하지 않는다. Fixed와 matchingbank read를 지원하고 RAM은64KiB다. 메모리 접근·로드 오류는 RAM/register/carry 전체를 보존한다. CPU상위byte alias나24bit wrapping 지원은 주장하지 않는다.

기존 MS5D의 검증된 raw8byte를 게시 source로 쓰는 제한된 fixture는 가능하나 자연 논리record/사용성으로 분류하지 않는다. Native 기본경로는 Musashi로 whole original 실행한다. Banked source 조건은 immutable 실제 bank mapping과 no-SR-hook Unicorn 전체 실행으로 검증하고 oracle 종류를 구분한다. Frame 전체에 의미 없는 activity_carry를 CCR처럼 비교하지 않는다.


## 실행 검증

```sh
make -j2 all test
.venv/bin/python tools/inventory_stage_region_frame.py
.venv/bin/python tools/observe_stage_region_frame.py
.venv/bin/python tools/verify_stage_region_frame.py
```

801조건의 전체64KiB RAM·14register·bank·activity_carry가 실제CLI와 일치했다. 797조건은 pinned Musashi, banked source4조건은 Unicorn2.1.4의 실제 원본 bank mapping으로 전체 함수를 실행했다. 두 oracle 모두 ROM을 수정하거나 callee를 stub으로 대체하지 않았다. SR은49392 반환 후 C를 읽을 때만 사용하고 실행 hook에서 읽지 않는다. 나머지 entry의 carry는 별도 API값 보존이며 원본 CCR 전체를 반환한다는 주장이 아니다.

15개 지원 조건분기의 양쪽을 확인했다. A5 불일치 TRAP 분기는 A5=108000 고정 전제 밖이다. MOVEM.W 부호확장 중간 snapshot65건, D0.byte선택과bit0 fallback선택이 다른40조건을 확인했다. 첫 게시를 둘째 source/좌표가 읽는 경우와, 둘째 source가 자신의 dd50 sentinel을 읽어 ffff8000으로 signextend하는 경우도 관측했다. 교대 목록의 정확한6WORD 쓰기와 타이머0/1/ff를 비교했다.

전체frame6회 중5회는 호스트 RAM/register 수정 없이 이전 실제CLI 출력을 전달했다. CLI 오류154조건과 직접API원자성5조건이 통과했다. Fixed/bank2/bank3 기존 MS5D를 실제 소비한8조건 및 각 directory loader, 리소스가 필요 없는5entry의 생략도 확인했다. 원본8byte probe는 자연 논리record/사용 여부 증명이 아니다. CPU/ROM resource 대응은 stage-buffer-frame.md 및 inventory resource_audit를 따른다.

메인은 core/header/unit/CLI와 목록·관측·검증 도구 전체를 읽고 실제CLI검증을 다시 실행했다. 801저장RAM을 원본 쓰기2,407건의 순서대로 독립 재생해 일치함을 확인했다. 현재provenance·입력승계·PC/A7·branch도 대조했다. 전체make Python182/C++126/경고0 (`artifacts/stage_region_frame_build_test.log`).

Native SHA256 `46a80065db1ccc48d27696743c04e9e005f8dedc8024eecf2fcd4f27c3d0c1a9`.
Verification SHA256 `7aa3576aa81864ba55e3ab21252ebe3d31ee4e8c1f81658d8443dbce67bce078`.
CLI SHA256 `5bf69cc5ad55e73bd130f2519792389fe950cf38cf337aef83fd188d36c77e09`.
Inventory SHA256 `6d6420d626f88ba55187d02820119ebd48460cbd18990ec0e6bbf021fba229d7`.

이 단위는 whole480bc/IRQ timing/자연scheduler/직접플레이 완료가 아니다. 전체goal은active이며 리뷰0185를 따른다.
