# Scene path와 primary tilemap 원시 리소스

## Source·mapping·범위

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. `tools/pack_scene_maps.py`는 원본과 path/tilemap inventory의 raw bytes 및 metadata를 다시 대조한다. 모든 검증과 모든 container 생성이 성공한 뒤 임시 디렉터리의 파일을 출력 위치로 게시한다. 검증 실패 전에 기존 출력 파일을 바꾸지 않는다. 파일 전체 묶음을 filesystem 수준의 단일 atomic transaction으로 게시한다는 뜻은 아니다.

기존 MS5D v1의 32byte `<4s7I` header와 kind1/kind2를 그대로 사용한다. Magic, version, kind, CPU address, ROM offset, payload size, CRC32, reserved=0이며 payload는 원본 raw bytes다. 새로운 포맷이나 논리 레코드 의미를 추가하지 않는다.

- Kind1 path는 첫 1MiB 고정 ROM이며 CPU 주소=ROM offset이다.
- Kind2 primary 자료는 bank3의 CPU200000..2fffef이며 ROM offset=CPU 주소+100000이다. PVC overlay tail은 제외한다.

각 파일에 stable ID, source CPU/ROM/end, container와 payload SHA256, 길이, references를 기록한다. 알려진 reference가 없는 map도 보존하며 이를 미사용 데이터라고 판정하지 않는다. Secondary bank2 lookup/data는 이번 추출에 포함하지 않는다.

## 파일 묶음

출력 디렉터리는 `extracted/runtime/scene_maps/`이다.

| File | Count | Kind | Payload |
| --- | --- | --- | --- |
| path_%06x.ms5d | 72 | 1 | 각 root부터 negative opcode 2bytes까지, 22 또는 30bytes |
| primary_root.ms5d | 1 | 2 | CPU200004/ROM300004, 4bytes |
| primary_lookup.ms5d | 1 | 2 | CPU200008/ROM300008, 308bytes |
| tilemap_%06x.ms5d | 77 | 2 | 각 map의 4byte header+4×width×height bytes |

총 151개 resource이며 payload 합계는 765048bytes다. Path ID는 `scene-path:%08x` CPU 주소 기반, map ID는 `scene-tilemap:%08x` **ROM offset** 기반으로 bank를 구분한다. Root/lookup ID는 각각 `scene-tilemap-root:00300004`, `scene-tilemap-lookup:00300008`이다.

Path의 CFG row는 원본 walk와 정확히 일치해야 한다. Root부터 모든 row가 연속되어야 하고 마지막 row만 terminal이어야 한다. Branch cycle·오류·불연속 창은 이 packer가 지원하지 않는다. Canonical 72개는 이 조건에 맞는다. 이 검사는 19e64 interpreter나 handler body의 C++ 실행 완료를 뜻하지 않는다.

Map header의 BE16 width/height와 inventory dimensions, 계산 extent, 원시 SHA, end 주소를 검사한다. Cell의 원본 4bytes는 삭제·변환 없이 보존한다. Manifest에 selector, width/height, descriptor 및 script references와 known_reference_count를 기록한다. Logical tile/frame 업데이트나 자연 게임 도달성은 별도 과제다.

## 재생성·합성 검사

```text
.venv/bin/python tools/inventory_scene_paths.py
.venv/bin/python tools/inventory_scene_tilemaps.py
.venv/bin/python tools/pack_scene_maps.py
.venv/bin/python -m unittest discover -s tools/tests -p test_scene_maps_pack.py
```

Packer exit0, 합성 Python unit 8개 exit0을 확인했다. Synthetic bytearray에서 container 길이/CRC/header, fixed/bank3 mapping 및 PVC tail, map dimensions/extent/hash/truncation, path terminal extent/metadata, 불연속 branch, empty payload, selector/pointer metadata, 중복 root 및 path reference 불일치를 검사한다. ROM을 patch하여 실행한 테스트가 아니다.

입력 inventory SHA256:

- Paths: `0bb2ed9b1c73335e983b72290187eed473e1229f0b3db47df5402d81ebc91a07`
- Tilemaps: `4249e94dcb069c477494b40ec91a312cde0ee076ec9ac978d35db9daf1a50262`

출력 manifest SHA256은 `8312156694a7cf20a6782ad6834285965734c579cb532e09d82f40839080411e`이다. Root container SHA는 `64fcba37adea1344ae3f341e8fc367d691cc5b344012ddc12b09abb73e5f2f7b`, lookup container SHA는 `cfef35537b468668b2537bf348f0415b368fd2fde3824e1389188db8334c0882`이다. 각 path/map container와 payload SHA는 manifest에 기록한다.

C++ typed resource loader/decoder 검증은 session20577 exit0으로 완료됐다. `artifacts/scene_map_resources/verification.json`을 직접 읽고 SHA256 `7d799705deddddfc37482d63fdc9aa8ee4b903594f8064bf89d048e3df3ed6ec`를 확인했다. 151개 resource의 header/CRC/CPU·ROM/payload/metadata가 일치한다. 72개 path의 218row(positive146/terminal72)를 복원하고, 77개 map의 190707개 column-major cell을 CPU/ROM 주소·두 BE16 word·source bytes와 비교했다. Root4/lookup308은 77개 map 연결을 별도로 확인한다. 부정조건 39개가 통과했다.

검증 CLI는 read-only이며 negative input은 임시 복사본이다. API caller-output atomicity는 별도 C++ unit의 근거이고 이 read-only CLI 검사가 mutable handler의 rollback을 확인한 것은 아니다. 19e64/183c6 handler body 효과, MMIO, 자연 reachability는 검증 범위에 포함하지 않는다. Source/resources와 검증 binary의 시작·끝 hash는 동일하다. Packer의 metadata/중복 검증 보강 뒤 재생성한 manifest도 동일 SHA여서 이 resource 비교 결과를 유지한다.

```text
.venv/bin/python tools/verify_scene_map_resources.py
``` 원본 ROM 및 추출 리소스는 Git에 추가하지 않으며 이 문서는 추출·규격 근거를 기록한다.
