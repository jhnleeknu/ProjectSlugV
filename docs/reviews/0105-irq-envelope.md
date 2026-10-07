# IRQ 저장 프레임 진입·종료 리뷰

대상 기준 커밋: `0676386`.

메인이20c..23a/248..29a의 원본 명령을 해석하고 외부 스택 byte span을 입력·출력으로 받는 API를 구현했다. 진입의18개 쓰기와 종료의 임시 MOVEM.W 두 쓰기를 보존한다. 마지막 레지스터 복구는 실제 스택에서 읽으며 BIOS/callback이나 RTE를 실행했다고 주장하지 않는다.

- `make all test`: Python73개 및 C++ 전체 검사 통과. 로그 `artifacts/irq_envelope_build_test.log`.
- `.venv/bin/python tools/verify_irq_envelope.py`: 원본1,342조건, 오류/별칭20조건 통과. 전체 RAM·전체 스택·16개 레지스터·포트와 실제 스택 쓰기 순서 및 비디오 읽기 횟수가 일치한다.
- 16개 진입→호스트 변경→종료 쌍에서 원래 레지스터가 복구된다. 중간 callback/BIOS는 명시적인 호스트 입력이며 실행 검증으로 기록하지 않는다.
- bankffff의16비트 순환, 스택 경계, BIOS 분기의 사용하지 않는 stack 조건과 출력 보존을 확인했다.
- 보고서 SHA256 `3a0116a7b2da28ed49999cfbfd306291247b6c2720be9241dd781d35a5b7b06b`.

콜백 슬롯 목록은 별도로 검토했다. 원본3dce는bit 제거와3dcc RTS 주소 설정을 한다. 보고서 SHA256 `82881d4f8233e31d372dc3036225f4c1080ce962811d28579c77f4d20fa72bbc`. 직접/상대 주소 명령 근거와 자연 실행 여부를 구분했다.

원본 BIOS가 입력 archive에 없으므로 BIOS 내부·RTE/예외 프레임·전체 IRQ 실행 및 시간축은 후속 범위다. 계약 내 비교에서 통합 차단 문제는 없다.
