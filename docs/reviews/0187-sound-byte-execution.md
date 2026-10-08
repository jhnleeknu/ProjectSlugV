# Sound byte execution 리뷰

Baseline `b28848a`, branch `codex/sound-byte-execution`. 신규 C++ core/header/CLI/unit, Makefile, 원본 비교 도구 및 분석 문서가 대상이다. AGENTS.md/docs/GOAL.md의 사용자 협업 규칙 변경은 별도 커밋으로 보존한다.

메인이 원본 3ac8..3af8과 구현을 대조해 command3 우선 처리, signed WORD 주소 계산, D1 상위 보존, byte 쓰기 후 tail 게시, 대기 재개의 live head 비교를 확인했다. RAM 밖 쓰기는 지연 검사하며 오류 시 RAM/상태를 보존한다.

Opus CLI 읽기 전용 독립 리뷰를 `--model claude-opus-5-5 --effort high`로 실행했다. 결과 modelUsage도 claude-opus-5-5이며 별도 effort 확인 필드는 제공되지 않았다. 143초, 보고된 비용 $0.6000984, 출력14294 tokens(그중 thinking10174), 입력14/cache creation35786/cache read139372다. 중첩 작업자0, 권한 거부0. 로그는 artifacts/sound_byte_opus_review.json. 작업자는 테스트를 실행하지 않았고 메인이 아래 검증을 수행했다.

독립 리뷰의 유효 지적 두 건을 수정했다. (1) head의 상위 byte만 다른 경우가 없어서 잘못된 byte 비교가 통과할 수 있었다. fresh6조건과 동일CPU 대기/재개4단계를 추가해 fullWORD 비교를 확인하고 API 테스트도 보강했다. (2) Makefile에 간접 header fixed_data_resource.h/video_port.h 의존성을 추가했다.

수동으로 만든 32bit A0의 24bit alias는 정상3ac8 캡처에서 발생하지 않는다. 재개는 이 API의 캡처 주소를 입력한다는 범위를 header에 명시했다. CLI 출력은 실행 오류 전에 열지 않지만 I/O 실패 시 파일 교체 원자성은 보장하지 않는다. 기존 도구와 같은 범위이며 API 상태 원자성과 구분한다.

수정 후 make test exit0: Python182/C++128/경고0. 실제 원본 비교564단계: 신규548, 동일CPU9체인의 재개16, CLI오류4. 두 원본 조건분기 양쪽과 전체RAM/14register/waiting이 일치한다. 검증 hash `90428c4bf9aacb97adb28b37b7d95aaf019427e1086bd3bca96e991aab041408`, CLI `9936913fae7569a3863a7c8f6569f28ace4724e829ab723936cef0ddb6826ee8`.

이 단위의 로컬 통합을 수용한다. 3af8/3c44/2efa6 계약 문서는 후속 정적 분석이며 동적 검증 완료가 아니다. 전체CCR/IRQ/사운드 재생/자연scheduler/직접플레이와 전체Goal은 미완료다.
