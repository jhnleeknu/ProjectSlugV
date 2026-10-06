# 진행 상태

## 2026-10-06 — ROM 기반 검증 완료
- 작업 브랜치: analysis/rom-foundation.
- mslug5.zip의 게임 ROM 13개가 고정 MAME 정의와 크기·CRC32·SHA1 모두 일치한다.
- 누락·추가·중복 파일 없음. ROM 원본은 변경하지 않았다.
- 검사 도구: tools/inspect_rom.py. 결과: artifacts/rom_inventory.json.
- config/mslug5_mame.json에 기준 해시를, config/mame_sources.json에 참고 소스 리비전·SHA256을 기록했다.
- tools/fetch_reference.py로 고정된 참고 소스를 확보할 수 있다.
- 합성 데이터 테스트 9개와 실제 ROM 검증 통과. 메인 에이전트 코드 리뷰 완료.
- docs/analysis/rom-layout.md에 데이터 영역과 복호화 순서·한계를 정리했다.
- 로컬 Git 구성 완료. 원격은 없어 실제 PR은 생성하지 않았다.

## 2026-10-06 — 영역 조립 및 68000 복호화
- 네 암호화 영역 P/C/M/V를 검증된 ROM으로 조립하고 파일 대응·해시를 저장했다.
- MAME ROM 로더와 endianness 헤더로 P 영역 바이트 순서를 확인했다.
- PVC 복호화 Python 구현을 메인 에이전트가 리뷰했다.
- 실제 ROM 및 합성 입력 각각 8MiB 전체가 원본 MAME C++ 함수 출력과 일치했다. BE/LE 대응도 일치한다.
- canonical BE 프로그램 이미지: extracted/program/maincpu.decrypted.be.bin.
- 합성 단위 테스트 총 20개 통과.
- 근거·재생성 명령·검증 범위: docs/analysis/pvc-program.md.

## 2026-10-06 — 그래픽·사운드 복호화
- CMC50 C/M1, PCM2 V 및 고정 문자 타일 추출 구현 완료.
- 실제 출력 5개가 원본 MAME C++ 함수 결과와 전체 바이트 일치한다.
- M1 512KiB, Z80 실행 영역 576KiB, ADPCM 16MiB, C 64MiB, 고정 타일 128KiB.
- 산출물·해시: extracted/media/manifest.json. 구현은 tools/extract_media.py로 재실행한다.
- 단위 테스트 총 31개 통과. 메인 에이전트가 구현 및 원본 대응을 리뷰했다.
- docs/analysis/media-decryption.md에 검증 범위·명령·출력 해시를 기록했다.

## 2026-10-06 — 런타임 타일 리소스
- 사용자 지침 반영: PNG·재생용 오디오는 확인용이며 최종 사용 데이터는 C++ 런타임 형식이다.
- 서브에이전트 사용자 상한 5개를 기록했다. 현재 도구 상한 때문에 동시에 최대 3개를 사용한다.
- C 타일 524288개와 S 타일 4096개를 indexed8 중간 데이터로 디코딩했다.
- C 픽셀 134217728바이트가 pinned MAME optimize_helper C++ 결과와 전체 일치, S 262144픽셀도 렌더러 nibble 매핑과 전체 일치했다.
- MS5T v1 바이너리 런타임 규격과 C++11 로더를 구현했다. 규격: docs/resource-format.md.
- extracted/runtime/sprites.ms5t 및 fixed.ms5t를 실제 C++ check_tiles로 읽었다.
- Python 테스트 총 41개와 C++ 로더 테스트 통과. 메인 에이전트 코드 리뷰 완료.
- 원본 팔레트는 미해석이다. 타일 인덱스는 보존되며 임의 색상을 런타임에 넣지 않았다.

## 다음 작업
1. 68000 역어셈블과 주소/뱅크 대응을 구축한다.
2. 팔레트·애니메이션·맵 테이블과 이를 참조하는 코드를 분석한다.
3. 원본에 근거한 대표 오브젝트 표시·애니메이션·이동을 C++ 런타임에 연결한다.
4. Z80 사운드 시퀀스와 런타임 사운드 리소스 규격을 분석한다.

## 미해결
- 복호화된 데이터의 리소스 해석, 코드 분석, 엔진 재구성은 아직 미완료.
- 원본 비교 실행을 위한 에뮬레이터 환경·BIOS는 확인되지 않았다.
- 원격 저장소와 공개 범위 미정.
