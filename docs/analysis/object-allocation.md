# 28ae 오브젝트 할당과 4fb1a 요청 wrapper

원본 프로그램 `extracted/program/maincpu.decrypted.be.bin`의 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 ROM CPU 주소는 고정 매핑에서 파일 오프셋과 같다. RAM offset은 CPU 주소에서 `100000`을 뺀 값이다. 예를 들어 free-list head RAM `4c9c`는 CPU `104c9c`다.

메인이 원본 28ae와 4fb1a의 명령 순서·폭·분기를 해석했다. C++ API는 확인된 RAM/레지스터 효과를 구현하며, 일반 ROM 실행기나 후속 callback 실행기는 아니다. 자동 역어셈블 목록만으로 의미를 확정하지 않았다.

## 입력과 정상 할당 실패

`AllocationState`는 전체 D0/A0/A1/A6와 bool carry를 담는다. A6는 parent의 절대 CPU RAM 주소, A0는 저장할 callback이다. `allocate_object`는 정확히 64KiB RAM을 받는다.

28ae는 CMP.W RAM4ca0,D0 뒤 BCC로 정상 실패를 선택한다. 즉 unsigned D0.low >= free count이거나 입력 A0=0이면 RAM을 그대로 두고 A0=`100e98`, carry=false를 반환한다. D0/A1/A6는 전체를 보존한다. 실패 sentinel `100e98`의 후속 동작은 이 API에서 실행하지 않는다. 이 분기는 parent/free node를 역참조하지 않으므로 해당 입력 포인터가 유효한지 검사할 필요가 없다.

정상 실패와 API 오류는 구분한다. 잘못된 RAM 크기나 실제 역참조 대상의 범위·정렬 위반은 false/error를 반환하며 RAM 및 입력 state 전체를 보존한다. 원본의 NULL 주소 또는 RAM 밖 주소 쓰기를 재현하지 않는다.

## 성공의 실제 읽기·쓰기 순서

정상 할당 조건에서 다음 순서로 처리한다. 각 단계의 live RAM 읽기는 앞 단계 변경을 관측한다.

1. RAM4c9c.long에서 node를 읽고 node+8.long을 읽어 RAM4c9c.long에 쓴다.
2. RAM4ca0.word를 1 감소시킨다. 지원 범위에서는 node는 유효한 nonzero RAM 주소다.
3. node+c.long에 parent A6를 쓴다.
4. **live** parent+10.word를 읽어 16bit wrap으로 1을 더한다. D0 상위 word를 보존하고 하위 word에 결과를 넣은 뒤 node+10.word에 쓴다.
5. **live** parent+8.long을 A1에 읽는다.
6. node+4.long=parent, node+8.long=A1, A1+4.long=node, parent+8.long=node를 차례로 쓴다.
7. node callback long에 입력 A0를 쓴다. **live** parent+6a.byte를 node+6a.byte로 복사한다.
8. A0=node, carry=true를 반환한다. A1은 위에서 읽은 successor이며 A6는 보존한다.

node와 parent의 요구 범위는 각각 6b byte, successor A1은 +4.long까지 포함한 8byte다. 모두 짝수 CPU RAM 주소여야 한다. free head에 저장되는 node+8 값 자체는 그 단계에서 역참조하지 않으며, 그 값을 임의로 별도 검증하거나 수정하지 않는다. 실제 successor는 이후 parent+8에서 live로 다시 읽는다.

전역 head/count, node, parent, successor가 겹칠 수 있으므로 구조체 필드를 먼저 snapshot한 뒤 일괄 기록해서는 안 된다. 단위 테스트는 node가 전역 head/count와 겹치는 배치 및 node==parent를 검사한다. head pop, count 감소, parent 저장, index 쓰기가 순서대로 서로 덮을 수 있다. 오류가 뒤늦게 발견되더라도 candidate RAM에서 처리하므로 caller에게는 앞선 변경이 노출되지 않는다.

## 4fb1a wrapper

`request_game_object`는 RAMfd82!=0 && RAM1==1일 때 A0=`4fb64`, D0.low=0으로 만든 뒤 실제 allocator를 호출한다. D0 상위 word는 보존한다. 호출 결과 carry에 따라 **live** parent+62.byte를 성공0/실패ff로 쓴다.

조건이 충족되지 않으면 allocator를 호출하지 않고 parent+62.byte=ff, carry=false로 반환한다. D0/A0/A1/A6는 그대로다. 이 분기는 parent의 +62까지 포함한 63byte aligned RAM span을 요구한다. wrapper 전체도 transactional이며 allocator의 정상 실패 후 parent 검증 오류가 나도 변경한 입력 레지스터를 포함해 RAM/state를 보존한다.

wrapper의 API carry는 allocation 결과를 나타낸다. 전체 CCR을 운반하거나 마지막 MOVE/SCC 후의 모든 condition flag를 구현했다는 뜻은 아니다. callback `4fb64`는 새 node에 저장할 뿐이며 그 후속 실행은 범위 밖이다.

## CLI와 재현

```sh
build/allocate_object [--request] D0 A0 A1 A6 INPUT_RAM OUTPUT_RAM
```

기본 모드는 28ae, leading `--request`는 4fb1a wrapper다. 숫자는 unsigned32 decimal 또는 0x hex로 입력한다. RAM은 정확히 65536byte이고 input/output의 같은 경로·canonical alias·hardlink·symlink를 거부한다. API 검증 실패 시 기존 output을 열거나 덮어쓰지 않는다. JSON은 d0/a0/a1/a6/carry이며 MMIO 포트 파일은 없다.

```sh
make build/allocate_object build/object_allocation_test
./build/object_allocation_test
python3 tools/verify_object_allocation.py
```

단위 테스트는 정상 성공/word wrap, unsigned threshold 경계와 zero callback 정상 실패, 전역 overlap/node-parent alias, 뒤늦은 successor 오류의 rollback, wrapper 성공/가득찬 실패/조건 불충족/오류를 통과했다. targeted build는 C++11 및 기존 warning flags로 성공했다.

## 원본 대조 상태와 한계

`artifacts/object_allocation/verification.json`은 Unicorn 2.1.4에서 원본을 수정하지 않고 439회 실행했다. 전체 RAM과 전체 D0/A0/A1/A6/carry가 일치하며 MMIO 쓰기는0이다. direct/active wrapper는 원본2908/2912의 결과와 최종 SR.bit0를 확인했고 inactive wrapper의 최종 carry=false도 독립적으로 관측했다. 오류50조건은 출력을 보존하며, 잘못된 포인터 오류에서는 원본을 실행하지 않는다.

승계3시퀀스는 실제 CLI 출력 RAM/레지스터를 다음 호출에 넘겼다. 두 synthetic 시퀀스는 각각3호출이며, 세 번째는 원본2790 초기화 결과를 실제 MS5I CLI RAM과 비교한 뒤2회 할당하여 free count80→79→78을 확인했다. 다음 callback과 요청 lowword는 호스트 입력이며 initializer의 register 반환을 검증했다고 주장하지 않는다. controlled pointer alias는 원본 읽기·쓰기 순서의 근거이고 자연 allocator 사용 관측과 구분한다.

원본 보고서 SHA256은 `9e6e6ad033a3683950fec1eeb40bdc66526b1b31f1c250e83b015c1c7e3abf6c`다. 전체 `make all test` 및 Python88개 시험도 통과했다. 다른 CPU 레지스터·전체 CCR·stack 동등성, 자연 caller/오브젝트 스케줄러 실행 및 callback4fb64의 후속 동작은 별도 분석 범위다.
