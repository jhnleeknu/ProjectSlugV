# Animation 직접 sound30 통합 리뷰

대상: baseline `51bdf61` 이후 `codex/animation-direct-sound`의 opcode30/phase4 구현·CLI·단위 검사·원본 관측·비교 도구·문서 변경. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`; 아래 고정 CPU 주소는 같은 ROM 파일 오프셋이다. 원격 없는 로컬 리뷰이며 PR이 아니다.

## 원본 의미와 구현 검토

메인이4a2da..4a2f0을 확인했다. padding은 읽지 않고 건너뛰며 D0 전체를0으로 한 뒤 WORD를 읽는다. 3af8 호출 후4a2ec는 A0/A1 LONG만 복원한다. callback14의 bank/PVC 복원 또는 MOVEM.W D0/D7 부호확장을 가져오면 원본과 달라지므로 전용 복귀를 사용한다. 복귀 후 D6와 오브젝트 script pointer를 갱신한다.

phase4는 기존 sound metadata를 공유하며 saved_bank/list_end/callback_saved_a0=0, sprite.waiting=false를 요구한다. high/low 대기는 원래 outer A0/A1과 captured low를 유지하고 callee에서 재개한다. prefix 재독출은 없다. 전체 호출 실패 시 RAM·상태·carry·ports·외부읽기 횟수를 보존하는 기존 transaction을 유지한다. 기존 두 API와 일반 CLI는30/phase4를 명시적으로 거부한다. 외부입력 CLI의26인자/27JSON 규격은 유지한다.

A5=108000은 현재 sound callee 모델 지원 제한이다. 원본의 모든 early filter가 이 조건을 요구한다고 주장하지 않는다. fullstate13R+a5/a6를 비교하며 원본 carry는 RTS 뒤에만 읽는다.

## 위임과 독립 검토

Sol6.1/medium의 부분 구현 후 사용량 제한으로 초기 작업이 종료됐다. Sonnet5.5/medium이 core를 검토하고 CLI/문서 및 별도 공식 비교 검증기를 담당했다. Opus5.5/high는 수정하지 않은 원본의 독립 관측을 담당했다. 재시도한 Sol6.1/medium은 core/CLI 독립 리뷰·UBSan 검사와 원본 전체 재실행 감사를 완료했다. 메인은 실제 diff와 각 보고서·원본 명령·검증기를 확인했다. 동시 작업자 전체5/내부3 상한을 지켰다.

Claude 반환 JSON에서 요청 모델과 실제 modelUsage가 일치했다. medium/high는 명령줄에 명시했으며 적용 effort 자체는 반환 필드가 없어 독립 확인하지 못했다. 위임 작업자들의 완료 주장만으로 통합하지 않았다.

## 발견과 조치

C++ 동작 결함은 발견하지 못했다. 공식 검증기가 파일 별칭 오류 검사에 사용하는 MS5D 복사 원본을 입력 해시에 기록하지 않은 점을 메인이 보완했다. 원본 파일을 alias 목적지로 사용하지 않고 임시 복사본을 사용한다. 보완 후 공식 검증기 전체를 재실행했다. 원본 observer가 작성 중 갱신된 임시 해시는 최종 고정 관측 해시로 대체됐으며, 최종 소스·입출력 해시를 다시 확인했다.

## 검증

- `make all test`: exit0, Python234/C++145, 경고0. Sonnet normal/UBSan과 Sol의 독립 UBSan 단위 검사도 통과했다. Sonnet의 ASan+UBSan 시도는 macOS 시작 단계에서 멈춰 ASan 성공으로 계산하지 않았다.
- `.venv/bin/python tools/observe_animation_direct_sound.py`: 원본207조건/255단계,18대기 연쇄,828 PVC,17 external reads. high/low/high→low/순차 명령을 동일 CPU 문맥에서 재개한다. native SHA `4ef6c7dd0ea871f98dacf1145e1a57fabdffb3ef587cfe3ec8cf55c7871c9386`.
- `.venv/bin/python tools/verify_animation_direct_sound.py`: 모든 원본 단계를 재실행하고 실제 CLI의 전체RAM/15regs/metadata/carry/ports/외부읽기 일치. 직전 실제 C++ 출력으로48회 재개, 오류·파일 보존41조건 통과. SHA `72669c031841d8c019df09addc9469848aeb3b390286ad3fdf8004a69c92851f`. 메인이 입력30/산출물2049항목, 고유2077개 참조 해시를 검사했다.
- Sol 원본 독립 감사:207조건/255단계와1028개 참조 해시, guard control2개 일치. 메인도 별도 임시 코드로 실제 CLI207조건/255단계 전체를 비교했다.
- 기존 회귀5종 모두 통과. execution90/98+15추가/164오류, control178+2혼합/48오류, sound22/30/73오류, indexed846/854+fixed30+signed6+soundCLI12/60오류, field818+실제script12+겹침1/64오류. 현재 보고서 SHA는 STATUS에 기록했고 모든 참조 해시를 확인했다.

## 남은 범위

18대기 연쇄의 head release와 poison은 명시적 host 입력이다. 자연 IRQ/Z80 소비, 실제 재생, cycle/fullCCR, 홀수 WORD큐, 자연 script/group binding을 검증하지 않았다. 합성 liveRAM 원본 비교와 실제 게임 실행을 구분한다. 분리된 MS5A padding 미독출은 C++ 단위 검사 범위다. 다른14 callback,3c,40·상위 활성화·전체게임 목표는 미완료다. 자동 역어셈블이나14/17 명령 수를 전체 복원율로 취급하지 않는다.
