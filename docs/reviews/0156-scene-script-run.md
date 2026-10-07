# 장면 스크립트 실행 루프 리뷰

Baseline `a6b4158`. 직전 사용자 응답은 상태 설명으로 소스 변경 없는 no progress였으며, 이번에는 작업 트리·원본 decode·검증 보고서를 다시 확인하고 구현을 통합했다. 원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 원본 범위 `[0x1a26a,0x1a29e)`는 고정 첫1MiB CPU주소=ROMoffset이다.

## 메인 검토

원본을 직접 다시 decode하여 A1의 최초 d412 load, 매 반복의 LIVE d418→D0.low, unsigned d416 gate, 음수 종료 표식과 d416=ffff, handler 뒤 cursor publication 순서를 확인했다. C++는 D0 상위 word를 유지하고 command가 바꾼 register와 RAM을 다음 반복에 전달한다. Gate가 cursor 역참조보다 먼저라서 null/initial waiting은 API에서 리소스를 검사하지 않는다. 종료 표식은 cursor를 남기며 다음 호출의 phaseffff는 다시 terminal에 도달할 수 있다.

Raw source를 재디코딩하고 정확한 command/terminal 경계를 요구한다. 성공 command는 앞으로만 전진하므로 decoded command 수의 bound가 지원 script를 조기에 자르지 않는다. 기존20 handler를 재사용하며 candidate RAM·12register·result·orderedports를 성공시에만 교체한다. 늦은 오류의 전체 rollback은 unit에서 선행 영상쓰기 후 누락 dependency로 검사했다.

CLI의 전체 script dependency preload와 API의 실행시 접근은 다르다. CLI는 null/wait에도 script/node를 로드하고, 초기 gate 통과시 미도달 command의 파일도 요구한다. 이를 원본 memory 접근과 동등하다고 주장하지 않는다. 파일 검증/API 오류의 출력 보존을 검사했으며 디스크 쓰기 실패까지 두 출력 파일의 원자적 교체를 제공하는 것은 아니다.

## 검증과 수정

`make -j3 all test` exit0, Python139/C++100, 경고0. 로그 `artifacts/scene_script_run_build_test.log`. 메인이 core/CLI/unit/Makefile과 native verifier를 직접 검토했다.

`tools/verify_scene_script_run.py`: native2211 / negative70 / orderedports7657120 / 원본 handler 실행26170회. 41script×5phase×3threshold×2register=1230, 모든814명령 cursor에서 시작하는 whole-loop814, 41script×4 실제 CLI carry164, null/invalidcursor waiting/terminal3이다. RAM전체·12register·reason·명령수·orderedports·RTS/A7를 비교한다. 원본 호출 내부에서 context를 재설정하지 않는다. Palette fixture는 원본3ef2로 준비하고 bank2/3 mapping과 immutable ROM을 확인한다.

초기 malformed descriptor 사례는 preload 오류여서 late-error라는 잘못된 label을 수정했다. CRC-valid descriptor의 CPU/ROM identity를 +2한 별도 사례를 추가하여 선행48 뒤08의 실제 API 오류 메시지를 확인했다. 기존 native 결과는 보존하고 negative-only 실행으로 수정 검증했다.

Report `artifacts/scene_script_run/verification.json` SHA256 `e9cc49c1c4fead4cdb7454f9af6adac3cf9d9c3ff3205b1fcf8936430acc5113`. Binary SHA256 `8c57516bc0f861da15f8f8b9d16d434f7e3be4d0a4d40fc3f6a3d2a6afe8289c`. 메인이 실제 파일의 해시와 수치를 확인했다.

## 남은 범위

Carry의 phase 변경은 명시적인 host fixture이며 자연 frame/IRQ 시간이 아니다. A3/A6=0, A5=108000과 호출간 stack/SR reset은 검증 입력이다. 현재 1a5a4 일반 초기화, motion 평가와 장면 갱신,47a94 이후 연결, 실제 스테이지 화면은 미완료다. 다음은 일반1a5a4가 호출하는1972a 경로 이동/18fd2 평가와 후속 갱신을 분석해 연결하는 것이다. 전체 목표를 완료로 처리하지 않는다.
