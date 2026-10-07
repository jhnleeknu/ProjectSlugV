# Scene secondary 접근 구간 리소스

Canonical decrypted source SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. Bank2 CPU200000..2fffef는 동일 ROM offset에 대응하며 PVC overlay tail은 제외한다. 주소·상수는 16진수, 건수는 10진수다.

`inventory_scene_secondary.py`는 scene path의 opcode04 raw descriptor를 source 및 metadata와 대조한다. +2의 nonzero secondary selector를 word shift 후 signed offset으로 root에 더하여 4byte pointer lookup을 읽는다. CPU200010 root는 20204a다. Canonical 40개 descriptor reference에 selector/pointer 37개가 있으며 sentinel은 없다.

메인이 원본 18568..185a0에서 확인한 column layout에 따라 full descriptor width W/height H, sourceColumn/sourceRow base0의 후보를 기록한다. Offset 후보는 pointer에서 시작하는 4×W bytes, 즉 2W개의 signed WORD다. 각 cell window 시작은 **각 offset WORD 자신의 주소+sign16(offset)**이며 H개의 LONG을 읽는다. 전체 8642개 column 후보/238982개 LONG 읽기에 bounds 오류는 없다. Alias/overlap은 개별 원시 주소와 hash로 보존한다. 이는 동적 sourceColumn/sourceRow의 모든 접근이나 collision 의미를 확정한 것이 아니다.

## 추출 계약

`pack_scene_secondary.py`는 inventory를 순수 함수로 원본에서 재계산하여 전체 JSON metadata/raw/hash와 대조한다. 다음 구간만 모아 union을 계산한다.

- CPU200010 root 4bytes
- 알려진 lookup 각각 4bytes
- 각 descriptor의 offset 후보 4×W bytes
- 각 valid cell window 4×H bytes

겹치거나 인접한 구간은 합친다. Hole은 추출하지 않는다. 따라서 runtime 주소 reader에 중복 window가 없으며, 이 union을 논리 자료의 전체 extent로 해석하지 않는다. Sentinel이면 offset/cell 구간을 만들지 않는다. Bounds 오류·빈 범위·잘린 source는 실패한다.

기존 MS5D v1 32byte `<4s7I` header/kind2를 사용한다. CPU와 ROM address가 모두 bank2 원시 주소이며 reserved=0, payload CRC32를 기록한다. Stable ID는 `scene-secondary:%08x` 물리 ROM start, filename은 `secondary_%06x.ms5d`다. Manifest는 source CPU/ROM/end, size/payload size, container/payload SHA256 및 coverage origins를 보존한다. 별도 포맷을 만들거나 기존 scene_maps 자료를 변경하지 않는다.

모든 source/metadata 검증과 container 생성 후 임시 디렉터리 파일을 게시한다. Validation 실패 전에 기존 파일은 바뀌지 않는다. 전체 묶음 게시가 filesystem 수준의 단일 atomic rename이라는 뜻은 아니다.

## 재생성 결과

```text
.venv/bin/python tools/inventory_scene_paths.py
.venv/bin/python tools/inventory_scene_secondary.py
.venv/bin/python tools/pack_scene_secondary.py
.venv/bin/python -m unittest discover -s tools/tests -p test_scene_secondary_pack.py
.venv/bin/python tools/verify_scene_secondary_resources.py
```

Inventory와 packer는 exit0이며 결과는 `extracted/runtime/scene_secondary/`의 47개 resource, payload 총 164960bytes다. Inventory 순수 함수 분리 후에도 보고서 SHA256은 `cbe8455db63a1b1570e95024b32e31be31bd93312639a8a4e7890cc454fdd98f`로 동일하다. Manifest SHA256은 `c4bf74b00417e295d57e176d94cb2145d6f91ef37ef51ab85ccf83bb7d415170`이다. 각 원시 window/container hash는 manifest에 있다.

합성 unit 8개가 통과했다. Overlap/adjacency/dedup/hole union, empty/odd/outside/PVC 범위, kind2 bank2 header와 CRC, 잘린 header/payload 및 wrong ROM mapping, sentinel coverage, bounds 실패 및 자기주소 기준 signed negative/positive offset, 두 entry의 동일 cell alias를 검사한다. 원본 ROM을 patch하여 실행한 테스트가 아니다.

독립 Python resource 검증이 exit0으로 완료됐다. `artifacts/scene_secondary/resource_verification.json` SHA256은 `79f4678387ed1d40a8c1257dc992e0b7c622fc6e414ad65e4098f33bf75e597b`다. 47개 container의 header/CRC/원본 전체 payload와 manifest metadata/hash를 검사했다. 원본 재계산된 8723개 coverage origin을 packer의 merge 함수와 별도의 endpoint sweep으로 union하여 resource interval과 완전히 일치함을 확인했다. 빠진 구간·추가 hole·겹치는 resource가 없으며 source/resources는 읽기 중 불변이다.

이 결과는 Python 검증만이다. 현재 inspection CLI에서 이 원시 bank2 union 자료의 일반 loader 검증 경로를 확인하지 못했으며 C++ bank2 loader 및 transfer 실행은 후속 검증 과제다. Handler body 실행 역시 별도 작업이다. 자연 scene 실행·collision 해석·logical 전체자료 extent는 미확정이다. ROM과 추출 데이터는 Git에 추가하지 않는다.
