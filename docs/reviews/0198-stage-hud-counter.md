# HUD counter 4e286 전체 helper 리뷰

Baseline `90406bc`, branch `codex/stage-hud-counter`. Sol6.1/medium 세 작업자가 core/unit, runtime packer/CLI/문서, 원본 비교를 분담했다. 메인은 원본 계약과 실제 core·검증기·변경을 읽고 통합했다. 외부 Opus5.5/high는 원본 명령 listing과 core/CLI/기존 callee를 독립 검토했으며 수정이 필요한 버그는 발견하지 않았다. 실제 응답 모델은 `claude-opus-5-5`이고 중첩 위임은 없었다.

4e286의 flag/unsigned WORD 분기, BYTE counter borrow, 3af8의 두 BYTE 대기·재개, WORD 저장·복원, BYTE shift carry, full8cda, 두35f0 호출을 연결했다. 원본 LSL.B3의 carry는 입력 bit5이며 D2 상위24bit를 보존한다. 첫 숫자 출력의 SWAP은 D0 상위WORD에도 반영한다. pending은 실제 sound 상태를 이어받고 HUD 진입 flag/counter prefix를 반복하지 않는다. 실패는 RAM/state/ports/external_reads 전체를 보존한다.

기존 sound callee의 A5 상대 queue 주소 지원 범위 때문에 실제 sound 호출/재개는 A5=108000에 한정한다. 비사운드 경로는 실제 BYTE 접근이 유효한 임의 A5를 허용한다. 이를 모든 A5/24bit mirror에 대한 원본 동등성으로 확대하지 않는다. 단위검증은 늦은 lookup 실패와 sound 재개 후 실패를 확인하며, Opus가 지적한 low BYTE phase2 재개 후 실패의 별도 회귀 검증도 보강했다.

실제 런타임 데이터는 기존 MS5D v1 kind1의32byte raw lookup span `[4e272,4e292)`이며 C++ fixed-data loader가 소비한다. 명목10개 digit 뒤 코드 WORD도 허용된 비BCD 입력에서 읽히므로16개 논리 digit table로 재해석하거나 clamp하지 않는다. 원본·추출 리소스는 Git에서 제외했고 단위자료는 합성 데이터다.

관찰 fixture의 palette slot을 수정했다. 원본 MOVEQ12는 decimal12이므로 offset은c0이며 기존120은slot18이었다. 이전 관측은 실제 CPU 결과였지만 의도한slot12 조건을 제어하지 못했다. 수정 후128개를 재생성한 native SHA는 `b87af2a6a5a5e2506072e241b8c003aa9ff889cd6acd430880a23c06d17d95d5`다. 이전 리뷰0197/STATUS의 `2afe1658...` 결과는 이 fixture 수정 전의 역사 기록이다.

`.venv/bin/python tools/verify_stage_hud_counter.py` 결과:

- 기존 원본128개 + 추가 원본168개 = 실제 CLI296개 비교. 전체64KiB RAM/15레지스터/정확한21key JSON/pending/read count/ordered ports2,732개 일치.
- 추가168개는 같은 CPU의 high/low 대기·유지·해제9단계, 조건부d00046 읽기3개, 허용 상위BYTE00..99 전체154개, 실제 A5/palette 필드 alias2개다.
- native stack에서 HUD saved WORD와 sound phase를 추출한다. 같은 CPU의 CCR을 유지하고 실제 이전 C++ 출력 RAM/register/metadata를 다음 호출에 전달한다. 대기 중 HUD flag/counter를 변경해 prefix를 재실행하지 않음을 확인한다.
- A5=ff140은 counter clear 후 blend weight 읽기, A5=ff141은 동일 dirty BYTE에 clear→BSET80의 live 쓰기 순서를 확인한다.
- 오류187조건에서 입력·리소스·출력을 보존한다. FIFO, hardlink/symlink, 실제 case alias, 늦은 두 번째 lookup 실패를 포함한다.
- source/input/native/artifact 종료 해시 검사와 별도 읽기 전용 감사에서 현재 입력24개, native 입력7개, native 산출물1,185개가 모두 일치했다.

Verification SHA256 `f6bc9947607e214476a861926f22b8ba1308bb893a92bfc86e4020360e076abf`; CLI SHA256 `3be9bcef7d9370cd836356c3463001a91bf90dc812b683b3f10a4a0ad98baea6`.

전체 `make -j4 all test`는 Python196/C++139/경고0으로 통과했다. 로그는 `artifacts/stage_hud_counter_execution_build_test.log`다. 이후 테스트 파일만 수정한 phase2 rollback 보강은 `make build/stage_hud_counter_test`, `build/stage_hud_counter_test` 및 격리 UBSan으로 다시 통과했다. 제품 소스/CLI 해시는 변하지 않았다. 상위BYTE154개 sweep은 각 BYTE당 선택한 low BYTE 하나이며 모든 WORD 조합의 검증은 아니다. 이 단위는 A7/CCR/cycle·물리 mirror·렌더링 화면·자연 scheduler/IRQ의 동등성을 주장하지 않는다. 상위47c6c, 직접 플레이, 전체 게임 Goal은 미완료다.
