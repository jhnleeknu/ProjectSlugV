# 그래픽·사운드 복호화 검증

## 확인된 처리
- CMC50 그래픽: MS5 키 0x19. prot_cmc.h에서 확인했다.
- M1 키: 첫 0x10000바이트의 합 modulo 65536. hashing.h/cpp의 sum16_creator로 확인했다.
- M1 실행 영역: 복호화된 ROM 첫 64KiB + 전체 512KiB = 576KiB. 실제 Z80 주소 공간의 선형 크기를 뜻하지 않는다.
- PCM2: swap 모드 2. 비트 0/16 교환, 주소 XOR 0x4e001, 소스 주소 가산 0xfe2cf6과 24비트 래핑.
- 고정 타일: 복호화된 C 영역 마지막 128KiB의 바이트 순열.

## 검증 결과
Python 결과와 고정 MAME 리비전 df09546b783c419889a2386bec9402883574b881의 원본 C++ 함수 결과를 실제 ROM 전체에 대해 비교했다. 생성 C++는 장치 의존성·비활성 디버그 덤프를 제거하고 최소 bitswap/체크섬 래퍼를 붙였다.

| 파일 | 바이트 | SHA256 |
|---|---:|---|
| m1.decrypted.bin | 524288 | df8bf6e4db78a7a1f7ff7455d42002757887e50300ec67acb8c5764eb763f3fb |
| audiocpu.region.bin | 589824 | 9f560a97999621dfba6d8ca10a3c7f9532204efe57b7de175cbf39718c88594e |
| samples.decrypted.bin | 16777216 | 860f1106a8324acb72284292ec0fd2fdce2b256fa943e15baf6e5979a14be9d2 |
| sprites.decrypted.bin | 67108864 | 94ae8e99bf986e34c408ae9405210d5c782322d76c920bce16f18529efda78fb |
| fixed.decrypted.bin | 131072 | 8cbbe34735a51a71fdce50566323a23c4afd41be5a11c94afdfcb23c2f6a7981 |

모든 파일은 extracted/media/에 있으며 전체 바이트 비교가 일치했다. 메타데이터는 manifest.json에 기록했다.

## 재생성
```sh
python3 tools/fetch_reference.py
python3 tools/assemble_regions.py
python3 tools/extract_media.py
python3 -m unittest discover -s tools/tests -v
```

참고 비교 컴파일에는 clang++가 필요하다. 검사한 단위 테스트는 총 31개이며 이전 도구 테스트를 포함한다.

## 범위와 다음 단계
- 이는 복호화 알고리즘 대응 검증이며 게임 실행 검증이 아니다.
- sprites.decrypted.bin은 아직 타일 픽셀 배열이나 완성된 캐릭터 이미지가 아니다.
- samples.decrypted.bin은 아직 트랙별 WAV가 아니다. ADPCM 디코딩 및 Z80 시퀀스 분석이 필요하다.
- 팔레트, 타일 조립, 애니메이션, 맵, 사운드 명령 해석은 미완료다.
- 다음 그래픽 단계는 pinned neogeo_spr.cpp의 optimize_helper를 기준으로 128바이트/16×16 타일을 팔레트 인덱스로 해석하는 것이다. 원본 색상을 추측하지 않는다.
