# Scene coordinate prefix의 명시 원본 창

## Source와 지원 경계

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 아래instruction CPU주소는first1MiB고정ROM이며동일파일offset이다. RAM/MMIO주소는별도로기록한다. 주소·상수는16진수,개수는10진수다.

이번구현범위는 **1a7a8→1a8ca 직전의coordinate prefix만**이다.1a8ca의1afda와뒤의19e64호출4회는남은tail이며아직연결하지않는다. Whole1a7a8 routine·scene전체frame update·자연scheduler를완료했다고주장하지않는다.

## 재생성 도구와 원본 창

`tools/inventory_scene_coordinates.py`는 `load_verified_program`으로canonicalSHA를확인하고 `disassemble_range`로아래창전체를보존한다.

| Start | End exclusive |
| --- | --- |
| 1a7a8 | 1a910 |
| 43dda | 43e04 |
| 43e22 | 43e34 |
| 43e38 | 43ea4 |
| 43ea8 | 43eb8 |
| 16fac | 16ff8 |
| 1724c | 17292 |

7개창에166instruction row가있다. 첫RTS에서자동종료하지않고window를넘는불완전/invalid명령은helper의dc.w로남긴다. 이출력은명시창의candidateinstructions이며code/data소유권·reachablepath·semantic완료의증거가아니다.

17292는처음상한17500까지310row를확인했지만RTS가없었다. 메인이더긴원본을확인해실제RTS18298을알렸고도구는 `[17292,1829a)`2051row를추가보존한다. Raw `[17298,18298)`가22c0×2048,18298의word가4e75임을assert한다. LEA/MOVEQ뒤2048longstore와RTS라는명령패턴확인이지caller의임의RAM범위나scene의미를확대하는것은아니다.

## Prefix call과 미연결 tail

Prefix의직접call13개를주소와rawinstruction으로별도기록한다.1a7cc→43ea8이1회이고각node에1724c/1726c/1728c가4회씩이다. 이목록은branch조건에따른실제실행횟수의주장이아니다. Rawcallsite는다음과같다.

| Callsite | Target |
| --- | --- |
| 1a7cc | 43ea8 |
| 1a7ee/1a82a/1a866/1a8a2 | 1724c |
| 1a802/1a83e/1a87a/1a8b6 | 1726c |
| 1a808/1a844/1a880/1a8bc | 1728c |

Deferredtail은1a8ca→1afda,1a8da/1a8ea/1a8fa/1a90a→19e64다. 명령목록과prefix지원범위를분리하며이5callee가실행API에연결됐다고주장하지않는다.

```text
.venv/bin/python tools/inventory_scene_coordinates.py
```

재생성exit0이며 `artifacts/scene_coordinates/disassembly.json`의최종SHA256은 `bf2d3184db48c2228156d48f796fc446868fc784da73f5bbd7e893528ed16174`다. Source·window start/end/rawSHA·instructions·prefix/tailcall목록을남기며원본ROM을변경하지않는다. ROM/추출데이터는Git에추가하지않는다.

## 현재 API와 레지스터 계약

`engine/include/ms5/scene_coordinates.h`의 API는 다음과 같다.

```cpp
bool update_scene_coordinates(std::vector<std::uint8_t>& ram,
    SceneNodeState& state, std::string& error);
```

`SceneNodeState`는 D0..D7, A0, A1, A2, A4의 full 32bit 값을 전달한다. RAM은 정확히 65536bytes이며 CPU RAM 100000..10ffff에 대응한다. 실패하면 RAM과 12개 레지스터 전체를 보존한다. 후보 RAM/state에서 모든 helper를 실행한 뒤 성공할 때만 게시하므로, 후반 node의 잘못된 parent pointer도 앞선 쓰기를 취소한다. API에 ports 출력은 없으며 이 prefix의 MMIO 계약은 없다. 다른 address register, CCR, stack, hardware timing은 노출 계약에 포함하지 않는다.

Core는 먼저 A0=10d38e를 설정한다. RAM d3bc.long+d38e.long의 32bit 합을 부호 반전해 D0 및 d396.long에 저장하고, d3c0.long+d392.long−01000000의 합을 부호 반전해 D1 및 d39a.long에 저장한다. 43ea8을 호출한 뒤 d404.word를 D0.lowword에 읽어 상위 16bit를 보존하며, node+18의 **주소에 있는 WORD**에 더한다. 이는 node+18.long의 상위 word를 바꾸는 연산이다.

이어 A0를 109156, 10b1d6, 10d256, 10d2d6 순서로 설정한다. 각 node에서 LIVE d40c.byte의 bit 0/2/4/6이 clear이면 d396.long을 D0에 읽고 1724c를 호출한다. bit 1/3/5/7이 clear이면 d39a.long을 D1에 읽고 1726c를 호출한다. 각 조건은 해당 시점의 RAM byte를 읽으며, set인 경우 그 scale 호출을 생략한다. 이후 1728c와 같은 scroll WORD 덧셈은 항상 수행한다. 1a8ca를 실행하기 직전에 반환하며, 마지막 A0는 10d2d6이다.

### Node primitive의 full register 확장

`step_scene_node(ram, entry, state, error)`는 43dda/16fac 초기화, 43e22/16fee parent/local 좌표 설정, 43e38/43ea8/1728c 좌표 갱신, 1724c/1726c scale, 17292 clear를 지원한다. 정확한 RAM 크기와 정렬된 A0의 전체 span을 검사한다. Parent pointer가 nonzero이면 정렬된 RAM 범위도 검사한다. 실패 시 RAM/state를 보존한다.

Scale은 unsigned lowword 곱, ASR32 8bit, fraction byte 덧셈의 carry, signed highword 곱을 원본 폭으로 순서대로 처리한다. D5/D6/D7 scratch 값도 반환하며 scale의 D7.lowword 쓰기는 상위를 보존한다. Position은 old node+14/+18을 D2/D3에 읽고, parent 합산·lowword carry와 history stamp에 따른 D4/D5/D6/D7 변경을 반환한다. A2/A4는 이 지원 helper들에서 보존한다. 기존 `position_state`의 RAM-only 코어를 변경하지 않고 별도 full register 읽기 순서를 구현했다. 이것이 나머지 CPU context까지 API가 반환한다는 뜻은 아니다.

17292는 A0+80에서 시작하는 8192bytes를 지우며 D0=0, A1=A0+2080을 반환한다. 첫 80bytes는 보존한다. 이 primitive는 node 버퍼 영역의 해당 clear 명령을 지원하며 scene 전체 초기화의 완료를 뜻하지 않는다.

## CLI와 재현

기존 5개 register 입력 CLI는 유지되며, 새 CLI가 12개 register를 전달한다.

```text
build/step_scene_node ENTRY D0 D1 D3 A0 A1 INPUT_RAM OUTPUT_RAM
build/step_scene_node_registers ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM
build/update_scene_coordinates D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A4 INPUT_RAM OUTPUT_RAM
make -j3 all test
```

새 두 CLI는 성공 시 출력 RAM 파일과 JSON의 d0..d7/a0/a1/a2/a4를 반환한다. Coordinate CLI에 PC 인자는 없으며 위 prefix 경계가 고정이다. 사용 안내의 `1a7a8 prefix stops before1a8ca`는 설명이고 인자가 아니다. Decimal 또는 `0x` 형식 unsigned32 숫자만 받으며 RAM 크기와 입력/출력 path alias를 검사한다. 검증 오류에는 출력 RAM을 쓰지 않는다. 기존 5개 register CLI를 full 12register carry에 사용하지 않는다.

## 검증 상태와 남은 범위

현재 core/header/CLI/unit 구현은 완료됐다. 메인이 확인한 전체 `make -j3 all test` 결과는 exit0, Python 139개/C++ 102개, warning 0이다. 새 full register node와 coordinate prefix의 원본 비교는 5248건(leaf 1132/prefix 4116), negative 135건을 통과했다. `artifacts/scene_coordinates/verification.json`을 직접 읽고 SHA256 `f903e4444ad1f690bc8a4ae0aa016e20418479fa34ec5cc634189dbd6fd8bf0a`를 확인했다. 전체 RAM과 노출 12개 register가 일치하며 MMIO 쓰기는 0이다. Leaf는 원본 RTS 뒤 A7=initialSP+4를, prefix는 1a8ca 직전 A7=initialSP를 확인한다.

4개 sequence에서 각 5회, 총 20회 실제 CLI RAM/full register 출력이 다음 호출에 이어진다. Prefix 내부 helper들은 CPU context를 재설정하지 않고 연속 실행한다. 호출 사이의 외부 stack/SR reset과 초기 camera/node·parent/self/overlap/stamp alias는 통제 fixture이며 자연 scene/frame scheduler의 증거가 아니다. 원본 ROM은 불변이다. 기존 5개 register node 및 scene command 회귀도 아래와 같이 통과했다. 위 bounded listing 자체를 native equivalence 결과로 취급하지 않는다.

```text
.venv/bin/python tools/verify_scene_coordinates.py
```

이번 문서는 coordinate prefix 근거이며 미연결 1afda/four19e64, 전체 scene frame, 자연 게임 도달 및 scheduler, CCR/hardware timing은 미완료다.


공유 코어 회귀: 기존5register node1904조건/오류94조건/8sequence48호출/MMIO0,보고서SHA256 `c900dfc01d94c31633856b8ffae34478ce9ad281366b9322e23ccebd85a0c1c6`으로이전과동일하다. Scene command4535조건/오류104조건/1737175orderedports도통과했다. 최신보고서SHA256 `1a08295adfc94be432f14a46b013a760808ef0706679220b0f6355cb0d1b1019`,binarySHA256 `7fea703ec8fac8c64103f113fcab67d7a2b7fa787b62600703fbd09b7bda0c1e`. 로그는 `artifacts/scene_coordinates_node_regression.log`와 `artifacts/scene_coordinates_command_regression.log`다.
