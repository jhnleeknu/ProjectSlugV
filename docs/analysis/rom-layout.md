# 입력 ROM 및 복호화 경로

## 확인된 사실
- 입력: `mslug5.zip`, SHA256 `2bae48b9c5df7dbc6254745150a6414a0ba6f0c8bad1feae29baa36e763ce1e6`.
- 게임 ROM 13개의 실제 바이트 길이, CRC32, SHA1이 고정된 MAME `mslug5` 정의와 일치한다.
- 기준 리비전: `df09546b783c419889a2386bec9402883574b881`.
- `mslug5h`가 아니라 `268-p1cr.p1`, `268-p2cr.p2`를 사용하는 MVS NGM-2680 세트다.
- 게임 데이터 합계: 92,798,976바이트. BIOS 포함 여부와 게임 ROM 완전성은 별개이며 이 ZIP에는 게임 ROM만 있다.

| 영역 | 파일 | 크기 | 처리 |
|---|---|---:|---|
| 68000 프로그램 | p1cr, p2cr | 8 MiB | 32비트 워드 인터리브·바이트 순서 정규화, PVC 복호화 |
| 그래픽 | c1c–c8c | 64 MiB | 짝별 바이트 인터리브, CMC50 복호화 |
| Z80 사운드 코드 | m1 | 512 KiB | CMC50 M1 복호화 및 실행 영역 구성 |
| ADPCM 데이터 | v1c, v2c | 16 MiB | 연결 후 PCM2 swap 모드 2 |
| 고정 문자 타일 | 별도 S ROM 없음 | 128 KiB 영역 | 복호화된 C 영역에서 추출 |

## 구현 전 주의점
- 파일 오프셋, 조립된 영역 오프셋, CPU 주소를 동일시하지 않는다.
- `ROM_LOAD32_WORD_SWAP`와 MAME의 호스트 바이트 순서를 추적한 후, 저장 결과는 명시적인 68000 big-endian 규격으로 통일한다.
- P 영역의 8 MiB 전체가 CPU에 동시에 보이는 것은 아니다. PVC 뱅킹은 별도로 분석한다.
- 그래픽 복호화와 타일 디코딩은 다른 단계다. 팔레트·조각 조립·애니메이션 해석도 아직 필요하다.
- V 영역 복호화는 음악 트랙의 WAV 추출 완료를 뜻하지 않는다. Z80 코드와 사운드 명령·시퀀스 구조를 조사해야 한다.

## 근거
- ROM 정의: https://github.com/mamedev/mame/blob/df09546b783c419889a2386bec9402883574b881/src/mame/snk/neogeo.cpp
- 처리 순서: 같은 리비전 `src/devices/bus/neogeo/pvc.cpp`, `neogeo_pvc_mslug5_cart_device::decrypt_all`.
- 68000: `prot_pvc.cpp`, `mslug5_decrypt_68k`.
- 사운드 데이터: `prot_pcm2.cpp`, `swap`의 value=2.
- 그래픽·사운드 코드·고정 타일: `prot_cmc.cpp`의 CMC50 및 sfix 처리.
- 참고 소스는 `config/mame_sources.json`의 SHA256으로 고정한다. `python3 tools/fetch_reference.py`로 재확보한다.

## 현재 한계
위 결과는 입력 식별 및 원본 처리 경로 조사다. 68000 프로그램은 후속 PVC 검증 문서에서 알고리즘을 검증했다. 그래픽·사운드 복호화와 리소스 디코딩, 실행 동작은 아직 미검증이다.
