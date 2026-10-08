# Stage block draw 전체 실행 및 리소스 리뷰

Baseline `cf6f102`, branch `codex/stage-block-draw`. Sol 6.1 / medium 세 작업자가 core/unit, CLI/Make/문서, packer/test를 분담했다. 메인은 실제 35f0..364e 명령을 다시 읽고 전체 diff를 리뷰했으며 native/CLI 비교 도구를 작성했다. Sol 작업자가 비교 도구와 core/CLI를 독립 검토했다.

기존 ObjectRestartState, FixedDataResource, VideoPortWrite를 재사용한다. 477a2/ddf9a/362a의 stream 처리와 35f0 rectangle 실행은 실제 BYTE·WORD·LONG 폭으로 구현한다. SWAP, D7 BYTE tile 증가의 carry 차단, D1 BYTE 증가, D0/D2/D6 WORD 변화, stream의 D2/D3 전체 초기화와 D0.low 복원, sentinel에서 미실행 상태 보존을 확인했다. RAM은 읽기만 하며 임시 state/ports 성공 게시로 실패 원자성을 유지한다. zero count wrapping loop와 원본 TRAP15는 명시적 checked 실패다. 정상 nonzero count에 임의의 작은 제한을 도입하지 않았다.

패커는 검증된 ROM의 fixed CPU=ROM [ddfa4,ddfdc) 56byte를 기존 MS5D v1 kind1로 보존한다. payload SHA256은 `14bba835b16c565a15364b794befbc8aca3c2575e28443654fbdae61ea36e30c`, container SHA256은 `6148703a4160af0b0f8514084b222444a57479ba842d8cbed617b200affe034b`다. 실제 C++ loader가 이를 읽는다. 메타데이터는 9개 레코드의 ID/원본 위치/필드/끝 sentinel을 기록한다. 재생성 결과가 같고 원본 소스 재확인, header/CRC/payload·source 변경 검사 7개가 통과했다.

리뷰에서 발견한 두 문제를 수정했다. 첫째, 단위 테스트가 실제 표 전체를 복사했으므로 C++/Python 모두 합성 레코드로 바꾸어 추출 데이터의 Git 제외 원칙을 지켰다. 실제 표는 ignored runtime 리소스로만 비교한다. 둘째, reader가 홀수 시작 raw window를 무시했다. MS5D는 이런 BYTE 창을 허용하므로 window 시작주소 제한을 제거하고 실제 WORD 읽기 주소 정렬은 유지했다. 홀수 부분 중첩의 모호성 거부와, 실제 표를 5byte/1byte/나머지로 분할한 loader 실행이 원본과 일치하는 회귀를 추가했다.

CLI는 모든 RAM/resource 입력을 일반 파일로 검사하고 모든 입력 inode와 두 예약 출력 inode를 대조한 뒤 truncate한다. 같은 inode의 반복 리소스 인수는 하나로 취급하지만 서로 다른 파일이 공급하는 중복 주소는 core에서 모호성으로 거부한다. FIFO/경로 별칭/부분 예약 실패의 보존을 확인했다. 실제 write/close 실패의 파일 원자적 교체는 보장하지 않는다.

수정 후 `make -j4 all test`는 Python189/C++136/경고0으로 통과했다. `.venv/bin/python tools/verify_stage_block_draw.py`는 원본40조건의 전체RAM/15register/2,840 orderedports와 실제CLI의 일치, 오류120조건, 추가 홀수 분할창 원본 일치를 확인했다. 원본161개 산출물의 해시/쓰기 trace/stack/RAM/ports를 감사하며 source/도구/실행파일 불변을 확인한다. UBSan 단위 실행도 수정 후 다시 통과했다.

- Verification SHA256: `48cb285a61968ae0e55df6d5fdeeb5e90716a1e703e39b8bc9a746ee0f8a55ce`
- Native observation SHA256: `8d40c12dffce8101158a029de56342902e69424ac93f5e75ee63c5c4e2c20fc9`
- Build/test log: `artifacts/stage_block_draw_build_test.log`

이 단위를 수용한다. isolated oracle stack을 사용하며 A7/CCR/cycle/physical mirror/pixels/scheduler 동등성은 주장하지 않는다. 다음은 상위 47af0/47c04 연결이며 직접 플레이와 전체 게임 목표는 미완료다.
