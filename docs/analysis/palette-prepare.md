# MS5P를 사용하는 동적 팔레트 준비

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 ROM CPU/파일 주소7196..72ee에서 일반 조회 및 효과 우회 분기를 복원했다.

RAM100000 기준으로 노드4d92+slot16의flags+f bit7이 dirty 표시다. 이를 지우고+a/+c source ID가 같으면 일반조회4718을 수행한다. C++는 동일 변환 결과를 보존한 MS5P hardware_words[1..15]를 staging5da2+slot32에 기록하고 첫word를8000으로 설정한다. 처리한 슬롯이 있으면7dd5와7ded를ff, 없으면0으로 만든다. bank shadow0010은0으로 돌아간다. 실제 PVC MMIO 장치는 모델링하지 않는다.

효과 여부는7dc2,7dc4,7dc6의 **상위 byte만** OR한다. 효과가 있어도 node flags bit1(mask2)이 설정되면 일반조회로 우회한다. 서로 다른 두ID의 혼합4c40/504c와 효과479e는 현재 명시적 오류다. 오류 발생 시 앞 슬롯에서 수행한 변경도 포함해 전체RAM을 보존한다. 별도 원본 효과 분석이 필요하며 대체 색을 만들어 넣지 않는다.

`pack_palettes.py`는 두 initializer의 원본 MOVE/JSR 14바이트 요청6개를 확인한다. 고유ID 03d3/039d/0203/087d/087a를 기존 MS5P에 추가하여 카탈로그는22개가 되었다. 기존17개 고정 리소스와 binding은 유지한다. manifest는 동적요청 위치·flags와 고정/동적 사용근거를 구분하며 전체 카탈로그로 주장하지 않는다.

```
.venv/bin/python tools/pack_palettes.py
make all test
.venv/bin/python tools/verify_palette_prepare.py
.venv/bin/python tools/verify_palette_resources.py
```

512조건(256목적지×dirty/clean)에서 원본7196 전체64KiB RAM과 C++ 준비 결과가 일치했다. 이후 원본72fa와 기존C++ upload 함수의 staging+palette16384바이트도 일치했다. 다섯 신규ID를 순환 사용하고 효과 상위byte의 세 위치, bit1 우회, 하위byte만 바뀐 경우를 포함한다. 초기 staging의 색값은 다양하게 두고 미변경 영역까지 비교한다. 원본 버스 쓰기의 정확한 타이밍이나 최종RGB 화면 검증은 아니다.

추가 단위 검사: 둘째 슬롯의 미지원 혼합으로 실패할 때 첫째 슬롯의 변경rollback, 효과 경로 거부, 누락/중복ID 거부, clean 상태의 빈카탈로그 허용. 전체 기존검사와 고정등록→준비→업로드 회귀도 통과했다.

팔레트 소유권 API와 MS5P 준비·업로드 API가 마련되었지만, 전체 게임 프레임 호출 순서와 효과·자연생명주기 연결은 남아 있다.

후속: 일반 혼합4c40은 palette-blend.md의 전수표검증을 거쳐 C++에 연결했다. 활성효과479e/504c는 여전히 미지원이다.

후속: 활성효과479e/504c는 palette-effect.md의 원본비교를 거쳐 지원한다. 효과word/혼합계수의 게임 내 갱신 경로는 별도 남았다.
