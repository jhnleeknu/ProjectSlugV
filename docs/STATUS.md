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

## 다음 작업
1. CMC50 그래픽·M1 및 PCM2 복호화를 구현·검증한다.
2. 68000 역어셈블 도구와 주소/뱅크 대응을 구축한다.
3. 공통 리소스 규격과 대표 타일 디코딩으로 진행한다.

## 미해결
- 그래픽·사운드 복호화, 리소스 해석, 엔진 재구성은 아직 미완료.
- 원본 비교 실행을 위한 에뮬레이터 환경·BIOS는 확인되지 않았다.
- 원격 저장소와 공개 범위 미정.
