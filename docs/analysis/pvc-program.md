# 68000 프로그램 영역 조립과 PVC 복호화

## 바이트 순서 근거
고정 MAME 리비전 df09546b783c419889a2386bec9402883574b881 기준:
- romentry.h: ROM_LOAD32_WORD_SWAP은 GROUPWORD | REVERSE | SKIP(2)다.
- neogeo.cpp의 mslug5 maincpu 영역은 16비트 big-endian이며 p1은 오프셋 0, p2는 오프셋 2에 로딩된다.
- romload.cpp의 region_post_process는 little-endian 호스트에서 이 영역의 각 2바이트를 다시 뒤집는다.
- 두 번의 워드 바이트 반전이 상쇄되어 내부 LE 배열은 p1[0:2], p2[0:2], p1[2:4], p2[2:4] 순서다.
- endianness.h의 BYTE_XOR_LE는 LE 호스트에서 0, BE 호스트에서 1을 XOR한다.

최초 작업 지시의 BYTE_XOR_LE 가정은 반대였다. 구현 전에 헤더로 정정했고, 최종 구현은 LE와 BE 두 경로를 전체 출력으로 비교한다.

## 재생성
저장소 루트에서:

```sh
python3 tools/fetch_reference.py
python3 tools/assemble_regions.py
python3 tools/verify_pvc_reference.py
python3 tools/extract_program.py
python3 -m unittest discover -s tools/tests -v
```

차등 검증에는 clang++가 필요하다. 참고 C++는 고정 소스에서 해당 함수 본문을 추출하여 artifacts/pvc_reference/에 생성한다. 엔진 구현이 아니라 비교용 참고 프로그램이다.

## 산출물과 검증 범위
- extracted/regions/manifest.json: 네 암호화 영역과 입력 파일 대응·SHA256.
- extracted/program/maincpu.decrypted.be.bin: 8,388,608바이트의 canonical big-endian 프로그램 이미지.
- 출력 SHA256: 29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f.
- artifacts/pvc_reference/verification.json: 실제 ROM 및 SHAKE256 합성 입력에 대해 각 8MiB 전체를 Python과 원본 MAME C++ 함수로 비교.
- 입력과 출력을 워드 스왑한 BE 경로도 LE 경로와 대응하는지 전체 비교한다.
- 처음 두 long 값은 0010f300, 00c00402다. 이 값만으로 정상 부팅을 주장하지 않는다.

## 주소 해석과 한계
출력 파일 오프셋은 복호화된 ROM 영역 오프셋이다. 8MiB 전체를 68000 CPU 주소 0부터 직접 대응하면 안 된다. PVC 뱅킹과 BIOS 벡터 매핑은 별도 분석 대상이다.

이번 검증은 알려진 MAME 복호화 알고리즘과의 동등성이다. 독립적인 암호 해독 발견, 에뮬레이터 부팅 검증, 코드·데이터 분류, 게임 로직 복원은 아니다.

MAME에서 변환한 Python 알고리즘의 BSD-3-Clause 고지는 tools/licenses/mame-pvc.txt에 보존한다.
