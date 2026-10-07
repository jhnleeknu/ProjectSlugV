# 인터럽트 선행 요청 처리 리뷰

대상 기준 커밋: `b31946c`.

메인이bbe/a74/a2c/a4e 명령을 읽고 도달 가능한 분기, BCD 차감과D0 폭을 해석해 C++/단위 검사를 작성했다. gpt-6.1-sol / medium에 CLI와 원본 비교를 분리 위임했다. 실제 산출물과 보고서를 메인이 검토했다.

bbe의 fd82 조기 반환 이후에는fd82==0만 가능하므로 standalone a74의 다른 경로를 이 API의 지원 범위로 주장하지 않는다. a2c의byte 이동과a4e의word 이동을 구분하고, 마지막D0.byte 갱신이 이전 word 이동의 상위 byte를 보존하게 했다. 원본이 계산만 하는~f006을 요청 마스크에 임의로 추가하지 않았다. BCD 차감은 SUB.W로X를 지운 후1을 빼는 경로이며 RAM0004/0005가0이면 차감하지 않는다.

원본1,326조건의 전체64KiB RAM과 전체uint32 D0가 일치했다. 모든 크레딧 byte를 유효/비정상 BCD 구분 없이 실행했고 모든 요청 byte와32회 승계를 포함한다. 실제a74/a2c/a4e/SBCD 명령 도달과 ROM 불변을 확인했다.7개 오류/파일 별칭 조건은 기존 출력을 보존했다.

`make all test`: Python73개 및 C++ 전체 통과. 로그: `artifacts/credit_request_build_test.log`. `git diff --check` 통과. 보고서 SHA256: `b18bdf7fa6e789a49e761fddfeb48a127f574e51f7a84f4c08de8d625af5e53b`.

전체 레지스터/CCR, 코인 하드웨어와 자연 IRQ 시간축은 미확인이다. 다음은c8c의 요청 처리 이후 렌더링·작업 복구와 사운드 서비스 통합이며 전체 목표는 active다.
