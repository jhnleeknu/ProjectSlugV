# Scene tilemap bank3 구조 조사

## Source와 확정된 주소 변환

Canonical decrypted program SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 아래 주소·opcode는 16진수, 건수·크기는 10진수다. 조사 도구는 `load_verified_program`으로 8MiB 원본을 검증하고 실행 전후 source SHA를 대조한다. ROM은 수정하지 않는다.

메인이 원본 `183c6..1844e`에서 확정한 primary tilemap 경로는 bank3다. CPU `200000`은 물리 ROM 파일 offset `300000`에 대응한다. 따라서 이 조사에서 banked CPU 주소 `p`의 파일 offset은 `300000 + (p - 200000)`이다. CPU `2ffff0` 이상 PVC overlay는 tilemap payload 범위에서 제외한다. 고정 ROM에 있는 path descriptor 주소는 첫1MiB CPU 주소와 파일 offset이 같다.

CPU `200004`의 BE32 값은 lookup root `200008`이다. 원본은 selector WORD를 `LSL.W #2`로 바꾸고 결과를 signed WORD offset으로 root에 더해 BE32 map pointer를 읽는다. 선택한 map의 처음 두 BE16은 width와 height이며, +4부터 width×height개의 4byte cell이 column-major로 이어진다. 셀의 원시 offset은 `4 + 4*(column*height + row)`다. 이 배치 의미는 메인의 원본 분석 계약이며, 자동 목록화 자체가 tilemap 렌더링을 실행한 증거는 아니다.

## 77-entry lookup extent 후보

첫 lookup target은 CPU `20013c` / ROM `30013c`다. `[200008,20013c)`의 308bytes를 4byte pointer로 나누면 77개가 된다. `tools/inventory_scene_tilemaps.py`는 이 경계를 **table extent 후보**로 삼아 전부 조사한다. 이 첫 target 경계와 아래 구조의 일관성이 후보 범위를 뒷받침하지만, 모든 가능한 caller를 조사했거나 이 범위를 넘는 selector가 존재하지 않는다는 증명은 아니다.

| 조사 항목 | 결과 |
| --- | --- |
| Pointer 후보 | 77개, selector 0..76 |
| Pointer 순서 | 모두 엄격히 증가 |
| Bank3/PVC 경계 및 payload span | 77개 모두 유효 |
| Width·height | 77개 모두 양수 |
| Map 끝이 다음 pointer를 넘는 overlap | 0개 |
| 연속 map 사이 gap | 0개 |
| Header 포함 raw map bytes | 763136bytes |
| Cell 개수 | 190707개 |
| 마지막 map 끝 | CPU `2ba63c` / ROM `3ba63c` |

마지막 map 끝부터 PVC overlay 전까지 285108bytes가 남는다. 이는 마지막 map 뒤의 bank 공간이며, map 간 gap이나 다른 자료의 사용 여부를 의미하지 않는다. 77개 map의 extent는 각 header의 `4 + width*height*4`로 계산한다. 다음 pointer까지의 span을 임의로 map payload로 늘리지 않는다.

308byte lookup 후보의 SHA256은 `cdf1df4dea5f5c5d7e345af2bf3b6e43f5397cdd42559c98e3c228d105658e9a`, CRC32는 `d449d272`다. 각 entry에는 lookup CPU/ROM 주소, map CPU/ROM 주소, header raw hex, dimensions, cell 수, 정확한 raw span/end, SHA256·CRC32와 다음 pointer 대비 gap/overlap을 JSON으로 기록한다. 셀 bytes를 변환하거나 새 runtime resource로 추출하지 않는다.

## Scene path descriptor 대조

`artifacts/scene_paths/inventory.json`의 72개 unique opcode04 descriptor에는 69개 primary map selector가 있다. 여기의 opcode04는 `19e64` path 구문이며, `1a0b6` scene command의 palette opcode04와 구분한다. 도구는 descriptor raw bytes를 고정 ROM 원본 span과 다시 대조하고 `>4HI`로 해독한 필드를 기존 JSON metadata와도 대조한다. 이 원시 해독 width·height를 해당 bank3 map header와 비교한다. 72개 모두 일치하며 candidate table 밖의 참조와 치수 불일치는 0개다.

각 map의 `references`에는 descriptor 주소·raw bytes·width/height, path root, 해당 root를 가리킨 script reference를 보존한다. 기존 path inventory는 CFG 구문 후보 조사이므로 이것을 자연 frame 실행이나 해당 branch의 실제 도달성 증거로 바꾸지 않는다.

다음 8개 selector는 이 72개 descriptor 집합에서 참조를 찾지 못했다. 모든 pointer/header/payload 구조는 앞의 검사를 통과했다.

| Selector | Map CPU 주소 | Width × height |
| --- | --- | --- |
| 21 | `24924c` | 62 × 27 |
| 49 | `2984ec` | 22 × 16 |
| 59 | `2a490c` | 20 × 16 |
| 60 | `2a4e10` | 20 × 16 |
| 65 | `2a9b74` | 22 × 33 |
| 66 | `2aa6d0` | 32 × 16 |
| 71 | `2b0c64` | 42 × 16 |
| 73 | `2b3c6c` | 20 × 16 |

이 목록은 **현재 조사 집합의 알려진 참조 없음**을 뜻한다. 미사용·폐기 자료라고 단정하지 않는다. 다른 caller, 동적 selector나 이후 분석 범위의 사용 가능성은 미확인이다. Secondary selector의 bank2 자료와 column pointer 실행도 이번 조사 범위가 아니다.

## 재현과 후속 범위

```text
.venv/bin/python tools/inventory_scene_tilemaps.py
```

출력은 `artifacts/scene_tilemaps/inventory.json`이다. 이번 실행은 exit0이며 보고서 SHA256은 `4249e94dcb069c477494b40ec91a312cde0ee076ec9ac978d35db9daf1a50262`이다. 입력 scene-path inventory SHA도 보고서에 별도로 남긴다.

이번 작업은 원본 불변 구조·참조·치수 대조만 수행했다. Interpreter나 renderer를 실행하지 않았고, 새 MS5D 추출·형식 변경·C++ loader·runtime tilemap API를 추가하지 않았다. 후속 작업에서는 이 구조 근거로 추출할 자료 범위와 banked resource 계약을 결정하고, 실제 소비 helper의 좌표·column clipping·hardware write 순서를 독립 원본 실행과 비교해야 한다.
