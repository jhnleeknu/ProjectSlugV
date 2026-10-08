# 스테이지 입력 callback 실행

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Fixed 첫1MiB CPU 주소=ROM offset, RAM CPU100000..10ffff, A5=108000이다. 아래 원본 계약은 메인이 직접 해석했으며 상세 명령 대응은 `stage-frame-followup.md`와 bounded inventory를 따른다.

## 실행 계약

`ms5::step_stage_input_callback`이 지원하는 진입은 다음18개다. 원본 전체 callback의 완전한 목록이라는 뜻은 아니다.

```text
49d88 49de6 49e34 49e38 49e9c 49eba 49ef0 49f2c 49f66
1bec0 1d5ac 1d5e2 1d61a 1d628 1d664 1d6c2 1d8cc e73f2
```

좌표 목표에 따른 방향 입력, 목표 도달/교차 시 callback 교체·해제, 특정 flag·latch 처리, 기본 입력 매핑과 no-op/단일 WORD 읽기를 연결한다. 원본의 LONG 투영과 WORD 좌표 차분을 구분하고 상위 register 비트를 보존한다. X/Y 차분의 교차 판단은 XOR 결과의 N이며 일반 C++ signed 대소 비교로 바꾸지 않는다.

49eba/49ef0의 CMPA는100cb8 **주소에 있는 LONG 값**과 A0를 비교한다.49f66은 A0와 **즉시값 주소**100cb8/100da8을 비교한다.49eba의 OR20은 저장 D0 복원으로 버려지므로 D7에bit5를 추가하지 않는다.49ef0은 저장 D0 LONG을 D1으로 복원한다.1d628은49c32 후 A0=0을 유지한 채49f66을 호출한다.1d5e2의 A6+3a WORD는 해당 flag 분기에서만 읽는다. 이러한 동작을 추정한 의도로 고치지 않는다.

기존 `step_stage_input`으로 setter와 mask 매핑을 실행한다. Default mask는 `extracted/runtime/stage_input/default_masks.ms5d`이며 실제 해당 분기에 도달할 때만 필요하다. Fixed MS5D와 live RAM 읽기를 지원하고 실패 시 전체 RAM·13개 state register를 보존한다. A6는 별도 읽기 전용 인자로 전달하며 CLI는 이를 포함한14register를 반환한다.

## 재생성과 실행

```sh
.venv/bin/python tools/pack_stage_input.py
.venv/bin/python tools/inventory_stage_input_callbacks_execution.py
make -j3 all test
.venv/bin/python tools/observe_stage_input_callback.py
.venv/bin/python tools/verify_stage_input_callback.py
```

```text
build/step_stage_input_callback ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 INPUT_RAM OUTPUT_RAM [MS5D_OR_DIRECTORY ...]
```

입출력 RAM은64KiB다. CLI의 unsigned 정수·리소스 형식·경로/inode 별칭 검사는 기존 입력 helper와 같다. 성공 전까지 출력 파일을 쓰지 않는다. 장치 오류나 잘못된 원본 메모리 접근을 재현하는 API가 아니라, 확인된 지원 범위의 호출을 재구성하는 API다.

## 검증 범위

Pinned Musashi M68000에서 원본 진입과 실제 callee들을 RTS까지 중간 reset·패치·stub 없이 실행한다. 원본 fixed ROM은 불변이며 전체64KiB RAM·14register를 실제 CLI와 비교한다. RAM/stack 외 쓰기를 거절하고 반환 PC/A7도 검사한다. CCR/사이클 동등성은 주장하지 않는다.

Bounded inventory는10창219행,18entry,59control operand,10direct call을 기록한다. 미해독/gap은0이며 메인이 도구 전체와 literal 근거를 리뷰했다. 이 목록만으로 코드 분석이나 실행 검증 완료를 주장하지 않는다. 상위49b0c의 두 플레이어 호출과 추가1da60/4d7a6은 별도 후속 연결 단위다.

## 최종 결과

2,943조건에서 전체 RAM·14register가 일치했고160오류조건에서 입력과 기존 출력을 보존했다. 실제 방문 entry 집합이18지원진입과 일치하며,38개 확인 대상 조건 분기에서 모두 두 목적지를 관찰했다.380조건에서1d628→49f66 진입 A0=0을 확인했고,720개의 absolute-memory 비교 fixture와248개의49ef0 D0→D1 복원 조건을 포함한다.

네 sequence32호출 중28호출은 직전 실제 CLI RAM/register를 호스트 재작성 없이 소비한다.16개 unused mask 생략 조건과 디렉터리 로더도 원본 결과와 일치한다. 전체make Python182/C++120/경고0이다. 메인이 현재 provenance와 저장 native RAM2,943개, fixture/register, branch successor 및 C++ report 행을 재대조했다.

| 결과 | SHA256 |
| --- | --- |
| Native | `2bb75aa89ee636ee8a6afee4df7662def786b02f7a8ee9e3d1b850ff8a41cd0c` |
| Verification | `ef931982b559b333ef52a6bd9b9020c78c782568ff874cd9a01a3ef21c97c398` |
| CLI | `7973d5cf88f0b2a5504adca95793cfe5bfc9aebd9030297a7f0ed923882b436d` |
| Inventory | `7575235f04b6a94a4e005a8bb19f0e472753ebaab011b9385fc75c787edf3eee` |
