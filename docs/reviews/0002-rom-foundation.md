# ROM 기반 검증 리뷰

- 기준 커밋: 0339753. 대상: analysis/rom-foundation의 검사 도구·테스트·기준 JSON·참고 소스 도구·분석 문서 변경.
- 서브에이전트: gpt-6.1-sol / medium이 검사 도구와 합성 테스트 구현. 메인 에이전트가 전체 코드를 읽고 검증을 직접 실행했다.
- 확인: 파일 내용 스트리밍 해시, ZIP CRC 검사, 누락·추가·중복 탐지, 실패 종료 코드, 원본 덮어쓰기 방지.
- 기준 JSON의 13개 파일을 고정된 MAME ROM_START(mslug5) 블록과 대조했다.
- python3 -m unittest discover -s tools/tests -v: 9개 통과. 손상 ZIP/내용, 누락, 추가, 중복, 해시·크기 불일치, 결정적 출력·원본 보존을 검사한다.
- python3 tools/inspect_rom.py: 실제 게임 ROM 13개 검증 성공.
- python3 tools/fetch_reference.py: 5개 참고 파일의 고정 SHA256 확인 성공. 다운로드 경로는 최초 자료 확보에 사용했고 재실행은 캐시 검증이었다.
- 별도 단순 해시 비교 스크립트로 실제 ROM 일치를 교차 확인했다.
- 제한: 이 검증은 ROM 식별·검사 도구에만 해당한다. 복호화·게임 동작을 검증하지 않았다.
