# 원본 ID 팔레트 리소스 리뷰

기준02aeb8d. 두 고정 슬롯 등록 테이블에 근거한3개 source ID를 MS5P v1으로 추출했다. 메인 에이전트가 원본0x8da2 레코드 처리와 호출부 A0 설정, normal lookup signed16 주소 계산 및 dirty flag 제거를 검토했다. 하드웨어 색상word와 RGB를 구분하고, 카탈로그가 incomplete sparse임을 명시한다.

C++ 로더의 파일 상한·길이·곱셈 범위·CRC·중복/정렬·BEword 복원·transactional 교체를 리뷰했다. 첫 word 검증 오류 설명에서 검증하지 않은 투명도 의미를 제거하고 숫자0 조건으로 고쳤다.

검증: make all test; pack_palettes.py; verify_palette_resources.py. 원본 초기화→고정 등록→normal 준비→전송의 실제 CPU 실행 결과96바이트와 리소스가 일치하며 C++ 로더가 실제 파일을 읽었다. 전체 팔레트, 혼합 분기, 실제 RGB 표시, Neo Geo 장치 효과는 검증 범위 밖이다.
