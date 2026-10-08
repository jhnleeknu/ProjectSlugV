# 두 플레이어 입력 루프 리뷰

Baseline `58516dc`, branch `codex/stage-input-loop`. 신규 loop API/CLI/unit, bounded inventory와 원본 관측/CLI 비교, Makefile 및 문서를 대상으로 한다. 원본 계약은 메인이 직접 확인했고 구현·목록·반복 검증을 gpt-6.1-sol / medium 에이전트에 위임했다.

메인이 core/header/CLI/unit 전체를 읽었다.49b0c의 실제 callback 분기와 marker 우회, BYTE mode 선택, 처음 처리 후 두 번째 slot 재조회,49afe 조건부 호출과49bb4 무조건 게시를 확인했다. 첫 player에서 수정한 RAM/register가 둘째 처리로 넘어가며 늦은 실패는 바깥 transaction 전체를 폐기한다.47642의 marker와+61bit7 조건, 최종 A0/D0 및 다른 register 보존도 확인했다.

1da60의 equality/cross/no-cross 분기와 D7 보존,4d7a6의 BYTE 선택/A0/A4 반환을 확인했다. 기존 read_player_record를 재사용하고활성비영index에서만 exact4092-window를 요구한다. Native index0 TRAP의 API 오류와 inactive의 unused resource 우회를 구분했다. Unit은 마지막index255 주소·반환폭, inactive교차의D7, unknown inactive우회, RAMmask, second failure의전체rollback을 검사한다.

Inventory 전체와 resource audit를 읽었다.4092-byte 조회 창과320-byte 논리 prefix의 서로 다른 계약, source/container/CRC/manifest/evidence 및재생성동일검사를 확인했다.두 JSR(A1)을 정적 direct target으로 꾸미지 않는다. 기존18callback과플레이어읽기core는 수정하지 않았다.

검증도구 리뷰에서 source record의 WORD경계fixture가+1c/+1e에 쓰는 것을 발견했다.원본 D5는+20을 읽으므로+1c/+20에 명시 입력하도록 수정했다. Verifier에도 native 반환 PC/A7/MMIO와 fixture 근거 재검사를 추가하고 실제branchsuccessor를 다시 집계해보고서와대조하도록 요청했다. 최종 결과만 통합 근거로 수용한다.

## 최종 결과

수정 후3,229조건에서 원본과CLI의전체RAM·14register가 일치했다. 오류48조건과세 inactive resource 생략도통과했다. 세 sequence12호출 중9회는 호스트 재작성 없는승계다. Inventory17조건 분기 중TRAP의4d7ec만 제외한16개가 두 실제 목적지를 가지며 verifier가 raw branchsuccessor에서집계를재생성한다. 두 indirectcallsite각각19knowncallback의실제target집합을확인했다. Unknown active target은nativehook에서도실행전에차단한다.

메인이 최종3229저장RAM·fixture·incomingregister·원본개별근거·actualcarry·현재원본/resource/oracle/core/CLI/tool 해시와C++결과행을 직접확인했다. 변경된관측/검증도구와source field+20fixture도다시읽었다. 전체make Python182/C++121/경고0, 로그 `artifacts/stage_input_loop_build_test.log`. 기존callback/helper core와binary는유지됐다.

Native SHA256 `0b1b93471c22c27a0cd7623c62cfe9976f62478416e32a5a3b8ad35579e2dd2e`, verification `184414fd1ae985ad9eae7bc2b60580acfa8fea1452bc1fd003e33cd0542be7d6`, CLI `17c69e75ec803099f15a4c308776a1634780a0123bd26d5df2991c613ae0ce48`. 재현/지원제한은stage-input-loop.md를따른다. 이단위통합을수용한다. 원격없는로컬commit/review이며 전체게임goal은active다.
