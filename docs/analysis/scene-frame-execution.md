# 장면 프레임 1a73c 실행

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Fixed 첫 1MiB의 CPU 주소와 ROM offset은 같다. RAM은 CPU100000..10ffff이며 A5=108000이다. Banked MS5D의 CPU 창과 physical ROM offset은 구분한다.

## 구현 계약

`ms5::step_scene_frame`은 1a73c부터1a7a6 RTS까지의 장면 프레임을 연결한다. RAM0010에 WORD1을 쓰고 2ffff2에2000,2ffff0에0을 출력한 뒤, 1a2b4 조건 → true일 때만1a26a script →1a526 설정 →19b96 camera →19d08 bounds →현재 XY로19802 시간 계산 →SWAP D7 및 unsigned phase 최대값 갱신 →1a3d6 shake →1a7a8 update →1a442 단일 placement 순서로 실행한다. 마지막으로 RAM0010을0으로 만들고 2ffff2에1000,2ffff0에0을 출력한다.

각 motion 호출 직전에 live RAMd3b4를 다시 읽어 리소스를 선택한다. 앞선 script가 새 motion/path를 게시할 수 있기 때문이다. 조건이 false면 잘못된 script cursor도 읽지 않는다. Script cursor가 null이거나 wait gate가 닫히면 decoder를 미리 실행하지 않는다. 12register helper 사이에서 A3를 보존하고 placement에 A6를 전달한다. A6는 변경하지 않는다. 단일 placement는 eligible record를 최대 하나만 처리한다.

64KiB RAM, D0..D7/A0..A4와 ordered ports를 후보 상태에서 계산하고 모두 성공해야 게시한다. 성공 시 ports는 이번 호출의 출력으로 교체한다. 실패 시 기존 RAM/register/ports를 보존한다. 실제 리소스는 기존 MS5D v1이며 458개 고유 창(고정187/뱅크271)을 사용한다. 별도의 PNG나 재생 오디오를 실행 자료로 사용하지 않는다. Live RAM motion은 기존 typed motion helper의 지원 범위 밖이다.

## 실행과 검증 재생성

```sh
make -j3 all test
.venv/bin/python tools/inventory_scene_frame_execution.py
.venv/bin/python tools/observe_scene_frame_execution.py
.venv/bin/python tools/verify_scene_frame_execution.py
.venv/bin/python tools/inventory_stage_input_callbacks.py
```

선행 일반 초기화의 검증된 `artifacts/scene_general_initialization/observation.json`, `verification.json`, 저장 RAM/ports와 기존458개 리소스가 필요하다. 해당 재생성은 scene-general-initialization 분석 문서를 따른다. Inventory는 원본과 선행 분석 문서의 해시도 고정하므로 근거 파일을 바꾸면 관측과 검증을 다시 생성해야 한다.

```text
build/step_scene_frame D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS TABLES [RESOURCE_FILE_OR_DIR ...]
```

TABLES는 `extracted/runtime/scene_debug.ms5d`다. 의존 창은 scene_scripts, scene_maps, scene_secondary, scene_placements 디렉터리로 제공할 수 있다. JSON은14register와 writes 수를 반환하며 ports는 각9바이트의 big-endian size/address/value다. 입력/출력/리소스의 경로와 inode 중복을 거절한다.

## 관측 방법과 한계

원본1a73c와 원본 callee들을 Unicorn에서 중간 초기화나 대체 없이 RTS까지 실행한다. 실행 중 SR을 읽으면 분기가 바뀌는 기존 oracle 문제 때문에 hook은 PC/register/RAM만 읽는다. 전체64KiB RAM,14개 exposed register, 순서와 값을 포함한 ports를 비교한다. 반환 PC와 A7 증가도 검사한다. 원본 fixed ROM 및 physical bank2/3 payload는 불변이며 PVC1000/2000에 따른 창 매핑만 수행한다. CCR 전체나 사이클 동등성은 이 검증의 범위 밖이다.

선행 초기화221개 실제 출력 전체를 seed로 사용한다. 연속 프레임은 첫 force 필드 설정 이후 native와 C++ 각각의 직전 출력 RAM/register를 그대로 소비한다. 일부 추가 조건은 명시된 초기 host write를 가진다. 특히 setup 재실행은 canonical script cursor로 되돌리고 wait/condition/motion/path cursor를 초기화한 통제 조건이다. 자연 진행 중 wait 뒤에서 새 motion/path를 지정했다고 표현하지 않는다.

이는 장면 프레임 함수의 재구성이다. 상위480bc의 입력·오브젝트·사운드 호출, IRQ/scheduler와 플레이어 callback을 모두 연결한 게임 프레임이나 직접 플레이 화면은 아직 아니다. 후속 계약은 `stage-frame-followup.md`에 기록한다.

## 최종 결과

594프레임의 전체 RAM·14register·ordered ports621,663건이 일치했다. 원본 초기화221출력, 연속360호출, shake4, condition3, setup replay4, 명시 debug8/16 두 조건으로 구성한다. 여섯 연속 sequence에서354회는 이전 출력을 호스트 수정 없이 소비한다. Canonical placement gate831/832는 둘 다 eligible인 상태에서도 서로 다른 연속 프레임에 처리된다. 실제 allocator 네 호출 중 두 번은 거절되어100ec6 대체 위치 쓰기를 관찰했다.

조건 분기는 true569/false25, phase 쓰기585/유지9, camera 승인583/거절11을 관찰했다. Debug8/16은 초기 F000을 명시한 두 사례에서 각각1,384ports를 출력한다. 초기화의 debug 설정만으로 다음 프레임에 해당 분기가 실행됐다고 가정하지 않는다. 오류149조건에서 입력과 기존 출력 파일을 보존했고 directory 로더도 setup replay 원본과 일치했다. 전체make Python182/C++118/경고0이며 뒤이은 입력 추가 빌드에서도 이 CLI hash는 유지됐다.

| 결과 | SHA256 |
| --- | --- |
| Native | `fc060d8c4d74b43d8bdb424f07d99478da6534f86db1426d4d7e3bd93ddac9f2` |
| Verification | `bdbeea5e8caa803f045d574a2fd67d726dc7fed23c829a43dfc50ad1dfc56fad` |
| CLI | `96abbe5073647073f8e6e8185c12b6a9d759798268b724755debc88962bef0bd` |
| Frame inventory | `f8dc5c70f2e60db0357246bec0ff02651bdec7d3fff07c3dc47117f98971edd7` |
| Input callback inventory | `bb10e55693e98b3fb08dedc6f2d8f8685b99043cf5ce940f6d2927845a68a4d9` |
