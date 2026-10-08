# 480bc 활성 경로 fixture 준비와 원본 실행 관측

원본 canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`를 사용했다. 고정 CPU 주소 `0x0480bc`는 canonical ROM 파일 오프셋 `0x0480bc`와 같다. 이 문서는 통제한 RAM 초기 상태로 상위 원본 호출이 활성 spatial/region/cue 할당 경로를 실행하는지 확인한 기록이다. 자연적인 게임 입력이나 scheduler로 해당 상태에 도달했다는 주장은 아니다. C++ 통합 비교 결과는 별도 검증 기록에서 확인한다.

## 재현 입력과 실행

초기 RAM은 이미 전체 호출을 반환한 `artifacts/stage_frame_plan/input.bin`(SHA256 `d51aba17d6dba2ff67ce77774f44df8c175c12c3cc52203e8dc34a7c61e266ec`)이다. 레지스터 14개는 같은 디렉터리 `probe.json`의 `incoming`을 그대로 사용한다. 세 fixture는 각각 이 seed부터 시작하고 기존 개별 helper fixture의 **선택한 span만** 진입 전에 복사한다. 전체 RAM을 개별 fixture의 무작위 배경으로 바꾸지 않는다. 원본 ROM은 수정하지 않는다.

준비 스크립트와 로컬 결과는 다음 경로다.

```sh
.venv/bin/python artifacts/stage_frame_active_probe/prepare.py
```

- `artifacts/stage_frame_active_probe/active.json`: 원본/seed 해시, 개별 선택 case, 진입 전 변경 주소·길이·이전/새 바이트·목적, 레지스터, 호출 PC와 상태 snapshot, 결과 해시.
- `{spatial,region,cue_allocate}_input.bin`: C++ 통합 검증에 넘길 64 KiB RAM.
- 같은 접두사의 `_native.bin`, `_ports.bin`: 원본 전체 호출의 RAM과 순서 있는 9바이트 ports.

기존 `observe_scene_frame_execution.Observer`에서 ENTRY를 `0x480bc`로 변경한다. 추가 hook은 PC·레지스터·RAM을 읽고 호출을 기록한다. 원본 code/physical bank payload 비교는 기존 Observer 검사를 그대로 통과했다. stub, ROM patch, 실행 중 host RAM 쓰기, callee 진입 재초기화, 실행 중 SR 읽기는 없다. 모든 fixture가 `0x480f0`에 도달하고 외부 반환 sentinel까지 반환했다.

## 진입 전 변경과 관측 결과

주소 범위는 아래에서 반열린 CPU 주소 `[start,end)`로 표기한다. 변경 로그에는 값이 기존과 같은 의도적인 seed 쓰기도 포함한다.

| fixture | 선택한 진입 전 RAM span | 실제 전체 호출 관측 |
|---|---|---|
| spatial | `[0x10d4e6,0x10d646)` 8개 0x2c바이트 node, `[0x106000,0x106009)` source, `[0x102000,0x102026)` parent, `0x10d494` stamp | 2050 instructions; `0x4701e` 1회, `0x46f52` 8회 |
| region | 각 player `0x100cb8/0x100da8`의 marker LONG, +0x61 BYTE, +0x42/+0x46 WORD 좌표, +0x56 LONG source; `0x10dcba/0x10dce6`의 active WORD, +6 6바이트 object/source와 +0x27 capture index; `[0x106000,0x106008)`, `[0x106010,0x106018)` source | 1301 instructions; region 진입 시 activity=3; `0x4d9d6`과 `0x1c028` 각각 2회; `0xb4a50/0xb4a84` publication 각각 1회 |
| cue_allocate | `[0x10de26,0x10de2a)` cue pointer, `[0x10de2e,0x10de30)` manual/allocate, `[0x106000,0x106008)` cue, `[0x104c9c,0x104ca2)` free head/count, `[0x100bfc,0x100c00)` successor, `[0x100c04,0x100c06)` depth, `0x100c5e` metadata, `[0x100804,0x100808)` successor back link, 각 `0x100408/508/608/708` next LONG, `0x10f001` debug bit clear | 1321 instructions; `0x2986` allocation 1회, `0x2992` original-parent metadata copy 1회 |

spatial은 기존 `verify_stage_spatial_frame.cases()`의 entry4701e/all_active/parent1/timer1 case를 사용한다. source와 node는 RAM에 놓이고 기존 scene/control 영역은 보존한다.

region은 기존 `observe_stage_region_frame.build_cases()`의 entryb4a2a/activity3/active[1,1]/nonnull/좌표0 case를 사용한다. marker를 `0x270e`와 다른 0으로 하고 player +0x61 bit7을 지워 기존 `47642`가 activity를 산출하게 한다. 기존 null input callback을 보존한다. record의 +0x27 capture index는 명시적으로 0으로 설정해 무작위 fixture 배경의 lookup 선택이 유입되지 않게 한다. 두 source는 각각 `0x106000/0x106010`이며 좌표는 0이다. activity 바이트 자체를 3으로 덮어쓰지 않았다.

cue_allocate는 기존 `observe_stage_cue_frame.build_cases()`의 allocate1/manual1/debug0/tag0x1c case에서 필요한 cue/할당 링크만 선택했다. 기존 전체-frame A6를 유지하고 개별 cue fixture의 임의 original A6를 가져오지 않았다. free node는 `0x100400`부터 0x100 간격, successor는 `0x100800`이다. 전체 호출의 이전 helper와 충돌 없이 반환하는 것은 관측했지만 자연적인 free-list 도달성은 미확인이다.

세 case 모두 상위 `47642 → 1a73c → 49b0c → 4aa88 → b4a2a → 6f1c2 → 4701e → e8a48 → 2efa6` 각 entry를 한 번씩 실행했다. 각 port 출력 SHA256은 `ec9a98dcf560c9a3d75d3aa816ff15afba90cf4d1d4e8601072c7c5bb50d1df4`이며 기존 scene bank 전환의 4개 write다.

| fixture | input SHA256 | native output SHA256 |
|---|---|---|
| spatial | `1e90ec1c660fa17ffc608c8625e1e5dc80383354de27166c3d8bb9ff66ec3a1a` | `03d9716af9eb7acd7fa4f2aca4061c94d54a377de5a11f0f803d73b669cb5a8e` |
| region | `5b3180d4394753c4dda118089af725ef188b3b3f0dc2173808911e9f58fb72d1` | `3f0b0ea870beef943c28e511773f00aad3164587b39e7c681866d18bc5d966e8` |
| cue_allocate | `8ab71a859ab7e3b1183f82ce301aa13cb271d2fd8a7d99566dfd36f6fb06488e` | `ef470c3f496bea20b7f7a2b547f68fc35576e168cac775f52c9203b428051279` |

## 다음 검증과 제약

통합 verifier는 각 input과 기존 incoming 레지스터를 사용하고 신규 STAGE0/BANK2 상태로 CLI를 호출해 RAM 전체, 14개 레지스터와 ordered ports를 위 원본 결과와 비교한다. 개별 helper fixture 통과를 전체-frame 비교 통과로 대신하지 않는다. 이 준비 단계는 원본 전체 호출 관측을 마쳤으며 C++ 비교의 최종 수용은 메인 리뷰와 통합 검증 결과에 따른다. 세 case는 독립 fixture이고 서로 다른 목적의 RAM source `0x106000`을 쓰므로 바이트를 단순 합쳐 하나의 fixture로 만들지 않는다.
