# 팔레트 프레임 최종 D1 리뷰

대상 기준 커밋: `b09c1e4`.

메인이5728의 byte 연산과7196의 분기,4718/479e/4c40/504c의 첫·마지막 색 명령을 직접 확인했다. timer 경로는 상위24비트, 변환 경로는 상위16비트를 보존한다. 효과만 적용할 때의 중간 채널과 혼합 시의 전체 인덱스를 구분했고, 단순복사는 앞선 D1을 유지한다.

기존 API에 선택적D1 입출력을 추가하고 C++11 명시적 정수 연산으로 구현했다. 새 CLI 인자 처리의 실제 diff를 확인했다. 검증에서는 원본 D1을 직접 읽으며 MS5P 전체 파일과 원본 추출 결과를 비교한다.

- `make all test`: Python73개 및 C++ 전체 검사 통과, 경고 없음. 로그 `artifacts/palette_d1_build_test.log`.
- `make build/palette_frame_test && ./build/palette_frame_test`: 추가된 상위 비트 보존·오류 시 RAM/D1/포트 보존 검사 통과.
- `.venv/bin/python tools/verify_palette_d1.py`:566조건과43,684개 MMIO 일치. 오류14조건 통과.
- 메인 리뷰 후 invalid D1 문자열6개에 대한 CLI 출력 보존 검사를 보강하고 재검증했다.
- 보고서 SHA256 `010f6796927413e435e052d512a9c69bce3ff10f644bcee4ade45162a01222c6`.

다른 scratch 레지스터와 CPU flags는 출력 계약에 포함하지 않는다. f46부터 실제 팔레트 실행 뒤 f4c 대기와 다음 입력을 연결하는 것은 후속 작업이다. 전체 메인 루프·부팅·SR/RTE/BIOS·장치 시간축은 미완료다.
