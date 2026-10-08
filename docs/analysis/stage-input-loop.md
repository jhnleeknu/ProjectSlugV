# 두 플레이어 입력 루프와 활동 mask

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Fixed 첫1MiB CPU=ROM offset, RAM CPU100000..10ffff,A5=108000이다. 상세 원본 계약은 `stage-frame-followup.md`, 기존 데이터 레지스터 조회는 `player-record-capture.md`를 따른다.

## 네 진입의 동작

`ms5::step_stage_input_loop`은49b0c 두 플레이어 입력,47642 활동 mask,4d7a6 플레이어 기록 읽기,1da60 목표교차 callback을 지원한다. D0..D7/A0..A4와 읽기 전용 A6를 운반한다. 실패 시 전체64KiB RAM과13개 state register를 보존한다.

49b0c는 첫 플레이어 처리 후 두 번째 callback slot을 **live RAM에서** 읽는다. Callback이null이면 입력byte와 mode에 따른 기본/RAM mask로49ab4를 호출한다. Callback이비영이어도 object marker270e이면 실행을 건너뛴다. 활성일 때 현재 지원하는19개 대상(기존18개 및1da60)을 실제 실행한 뒤49afe를 호출한다. 어느 경로든49bb4로 일회성 mask를 소모하고 입력을 게시한다. 첫 callback이 둘째 slot을 해제하거나 교체한 효과가 같은 호출에서 적용된다. 미지원 대상은 실제 실행이 필요할 때만 오류이며 원본의 임의 코드 실행을 지원한다는 뜻은 아니다.

47642는 BYTEd68e를0으로 만들고 object100cb8/100da8 각각 marker!=270e이며+61.bit7이0이면 해당bit를 켠다. 결과 D0전체=1,A0=100da8이며 다른 register는 보존한다. 사각형 검사에서 사용하는 object+15.bit7과 구분한다.

4d7a6은 기존 `read_player_record`의 D0..D6를 재사용하며 A0/A4 반환을 보완한다. 선택은 입력 D0.lowbyte가0인지로 결정한다. Inactive/활성WORD0 경로에서는 조회리소스를 요구하지 않는다. Active 비영 index에서는 기존4092-byte raw lookup을 읽고 A4=4cf64+index*16으로 반환한다.0index TRAP 경로는 구조화된 API 오류다.1da60은 X 차분/교차 뒤 이 함수를 호출하고 반환 D0.byte가비영이면 반환 A0의 player index로49c32→49f66을 실행한다.

## 리소스와 실행

```sh
.venv/bin/python tools/pack_stage_input.py
.venv/bin/python tools/pack_player_record_lookup.py
.venv/bin/python tools/inventory_stage_input_loop.py
make -j3 all test
.venv/bin/python tools/observe_stage_input_loop.py
.venv/bin/python tools/verify_stage_input_loop.py
```

```text
build/step_stage_input_loop ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 INPUT_RAM OUTPUT_RAM [FIXED_MS5D_OR_DIRECTORY ...]
```

필요한 리소스는 `extracted/runtime/stage_input/default_masks.ms5d`와 `extracted/runtime/player_record_lookup.ms5d`다. 기존20-record `game_records.ms5d`는lookup의320-byte prefix와 같지만 다른 범위의 리소스다. 두 overlapping 창을 동시에 전달하면 활성lookup의 유일성 검사에서 거절한다.4092-byte 창에 포함된 code/미분류 byte를256개의 논리 record라고 부르지 않는다. JSON은14register를 반환한다.

## 검증 방식

고정 Musashi에서 원본 네 진입과 실제 nested/동적 callee를 중간 reset·patch·stub 없이 RTS까지 실행하고 실제 CLI와64KiB RAM·14register를 비교한다. Unknown pointer는 원본에서 비활성 marker로 우회되는 경우만 실행한다. Active unknown/RAM code와TRAP은 C++ 지원범위 거절로 검사하며 원본 invalid 동작과 같은 결과라고 주장하지 않는다. CCR/사이클과 자연 플레이 도달성은 범위 밖이다.

Bounded inventory는5창125행,직접control34개와JSR(A1) 두 개를 구분한다. Gap/undecoded0이다. 기존lookup/defaultmask/prefix의3개 컨테이너·3개manifest를 원본 및 packer 규격과 대조하고 index255 끝주소까지 확인한다. 파일을 재생성하거나 ROM을 변경하는 inventory가 아니다.

## 최종 검증 결과

3,229조건에서 전체 RAM·14register가 일치했다.4d7a6은1,551조건,1da60은504조건,49b0c는1,142조건,47642는32조건이다. 두 플레이어 각각 모든255개 active index와3개 BYTE 선택 profile을 사용한다. 두 원본 JSR(A1)에서 각각19개 지원 callback을 실제 관찰했다. 첫 callback이 둘째 unknown slot을 해제하거나49e34로 교체한 뒤 live 읽기가 바뀌는 사례도 포함한다.

48오류조건에서 입력/기존출력을 보존하고, 세 sequence12호출 중9회는 호스트 재작성 없이 이전 실제 CLI 출력을 소비한다. 리소스를 아예 생략한 세 inactive 조건도 원본과 일치했다. Inventory의17조건 분기 중 index0 TRAP의4d7ec만 제외한16개에서 양쪽 목적지를 관찰했다. Verifier가 반환 PC/A7/MMIO와 개별 fixture 근거를 재검사하고 실제 branchsuccessor를 다시 집계한다.

메인이 검증fixture의 WORD 주소를+1e에서 실제 읽는+20으로 바로잡은 뒤 최종 원본/CLI 비교를 다시 실행했다. 저장RAM3,229개·입력승계·현재provenance·branch집계 및 각 플레이어19target 집합을 메인이 직접 확인했다. 전체make Python182/C++121/경고0, 로그 `artifacts/stage_input_loop_build_test.log`. Runtime core는 이 검증 보강 중 변경하지 않았다.

| 결과 | SHA256 |
| --- | --- |
| Native | `0b1b93471c22c27a0cd7623c62cfe9976f62478416e32a5a3b8ad35579e2dd2e` |
| Verification | `184414fd1ae985ad9eae7bc2b60580acfa8fea1452bc1fd003e33cd0542be7d6` |
| CLI | `17c69e75ec803099f15a4c308776a1634780a0123bd26d5df2991c613ae0ce48` |
| Inventory | `4d6df6f09d111f372eee6d85d0b983cbd62c32a1380f6190ec6726e826c37a14` |

전체480bc와 오브젝트·사운드·sprite producer 연결, 직접 플레이 화면은 아직 남아 있다. 지원되지 않은 callback을 임의로 실행 완료 처리하지 않는다.
