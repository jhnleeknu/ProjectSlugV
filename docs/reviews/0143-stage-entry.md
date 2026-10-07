# 스테이지 레코드 선택과 사운드 대기 연결 리뷰

Baseline `3512579`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인이3d58/3d64와477ee..478c4의 제어 흐름·정수 폭·재개 계약을 해석했다. sol에 sound pair, stage entry, 두 원본 verifier, 목록화와 문서 작업을 분담하고 메인이 실제 core/CLI/unit/verifier를 리뷰했다.

## 두 바이트 전송

첫0a/0b 전송 전에 원래D0.byte를 저장하고 첫 전송 후 복구한다. ADD.B20의 carry를 SCS.B D1과 OR.W로 결합하므로 입력e0..ff의 두 번째 명령은 단순 wrap 값이 아니라ff다. 각 byte 전송 후 D1.low는 queue next이고 highword는 보존한다. D0의 상위24비트와 D3 전체도 보존한다.

phase1/2는 두 개의3aea 대기를 구분하며 command/tail/next를 캡처한다. resume은 live tail을 재로드하지 않고 앞선 명령을 다시 전송하지 않는다. phase3의3af6은 마지막 원본RTS 표시이며 임의 caller PC가 아니다. saved는 원본 stack pop 이후에도 재구성 상태의 sideband로 유지한다. API 오류는 RAM/state 전체를 보존한다.

원본2180조건/오류67조건과40승계시퀀스가 통과했다. 이 중32시퀀스는 명시적 host head/tail 조작이고8시퀀스는 실제 c8c IRQ28회만으로 head를 진행시켰다. IRQ 포트48개와 RAM도 비교했다. producer MMIO는0이다. 보고서 SHA256 `77798809d958068d210e268b21306a3000b3a84a1d3e3ddc63af02e11e0034eb`. IRQ context 복원은 호스트이며 자연 BIOS/SR/RTE나 물리 timing의 증거가 아니다.

## Stage entry

실제477e4 초기 장면 준비 또는477ee부터 시작한다. 기존19그룹 MS5D catalog로 stage/area를 선택하고, 원본의 area0 재시도와 raw stage byte 보존을 따른다.59레코드의 selector는0/4/c/14이며 7빈그룹은 원본의 재시도 loop다. API의256회 guard는 이를 오류로 반환하며 정상 실행 완료나 원본TRAP으로 표현하지 않는다.

고정 오브젝트 활성 flag와 전역 상태를 원본 순서로 갱신한다. callback0도 active다. 레코드word10과 RAMd686이 같으면 sound를 건너뛰고, 다르면38/80의3d58 전송을 시작한다. 대기 후에는 sound만 재개하며 scene 초기화·catalog 조회·flag 변경을 반복하지 않는다. 완료 후 d68c.word=1 및 ca9e를 연결하고 LIVE obj76 포인터를 다시 읽어 selector를 결정한다. 실제 여섯 BRA 목적지에서 멈추며 본문은 실행하지 않는다.

메인은 A6 alias의 조회 순서를 검토했다. 짝수A6의 +7d는 홀수이므로 header 저장d684와 직접 겹칠 수 없다. +7c=d684인 경우는 가능하지만 stage를 저장 전에 읽고 다음 fallback 반복에서 다시 읽는 현재 순서가 원본과 같다. late selector/record 오류도 이미 수행한 sound/화면 포트와 RAM을 모두 rollback한다. CLI는 catalog 안의20개 실제 리소스 파일까지 output alias를 검사한다.

## 최종 검증과 남은 작업

Stage entry 원본526조건/오류81조건과 실제CLI 승계8시퀀스가 통과했다. 전체RAM·레지스터·pending과 순서 있는401942포트가 일치했다. 이8시퀀스의 queue 해제는 host 입력이며 앞의 sound pair IRQ 검증과 구분한다. 59레코드를 모두 검사했고 canonical에서 없는 selector8/10은 별도 분기 매핑 관측으로만 기록했다. 보고서 SHA256 `6ba246a33c26b91b841443ed3f26a023eb5abd150dd4f16e2b7626d775bd31fa`. 전체 `make -j3 all test` exit0, Python95개/C++90개, 컴파일 경고0개. 로그는 `artifacts/stage_entry_build_test.log`다. 분기 후 callback 본문, 전체 스테이지 진행·전투·자연 scheduler는 남아 있다. 전체 목표는 진행 중이다.
