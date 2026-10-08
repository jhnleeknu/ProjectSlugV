# Animation 전체 상태 실행 초기 연결 리뷰

Baseline `2110d5e`, branch `codex/animation-execution`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, runtime packer/test를 맡았다. 메인은 원본 의미 계약과 실제 변경을 검토하고 원본 비교 검증기를 작성했다. 별도 Sol은 검증기와 최종 core/CLI를 읽기 전용으로 독립 검토했다.

`49fc6`의 opcode00/04/08/28을 전체15레지스터, RAM, carry, PVC와 sprite 대기 재개로 연결했다. 나머지13개 opcode는 명시적인 오류이며 기존 부분 API를 제거하지 않는다. live RAM script, 실제 도달한 주소 검사, 부분 레지스터 보존, MOVEM.W 부호확장과 저장 A0/A1/bank 복원을 검토했다. 현재 draw 재개와 이후 draw의 object 재읽기를 구분한다. 실패 시 RAM/state/carry/ports는 보존한다.

원본 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 이 단위의 고정 CPU 주소는 ROM 파일 오프셋과 같다. 실제48980/489c2의65/80byte consumed script를 기존 MS5A와 C++ loader로 연결했다.48a12의1024byte raw window는 MS5D로 보존했지만 이 API가 소비하지 않는다.489c2의 live composition group은 미확정이다. 원본·추출 데이터는 Git에 넣지 않는다.

## 검증과 수정

- 원본90조건/98단계를 재실행하고 실제CLI의 전체64KiB RAM/15regs/continuation/carry/ordered PVC3280개와 일치함을 확인했다.8회 재개는 이전 실제 C++ 출력과 명시적 host 변경만 사용했다.
- 추가 live RAM script15조건은 원본 코드 수정 없이 duration0, control/palette, sentinel/flash와 entry clear에 의한 script 변경을 검증했다. 합성 RAM 입력을 자연 gameplay 도달성으로 주장하지 않는다.
- 오류157조건에서 parser/unsupported/span/resource/callback/continuation 및 FIFO·alias·예약 실패 시 파일 보존을 확인했다. API 단위 검사는 false/true carry 양쪽 rollback, 늦은 resume 실패, 모든 미지원 opcode와 명령 수 제한을 포함한다.
- 패커 합성 테스트10개와 실제 재생성 일치가 통과했다. 전체 `make all test` exit0, Python215/C++145/경고0이다. core normal/UBSan도 통과했다.
- 구현 중 단위 fixture의 entry palette counter 감소와 clip 경로 PVC 기대값을 원본 계약에 맞게 수정했다. 메인은 최종 문서의 빌드 명령을 실제 실행한 `make all test`로 바로잡았다. 독립 최종 리뷰에서 추가 수정할 core/CLI 문제는 없었다.
- 검증 보고서 SHA256 `60a5594afb637884eaf51d61cf5ff5ddd9f6af32869ea6a9775ec7b627160082`. 입력22/산출물670개, 총692개 참조 파일을 독립 검토자가 현재 해시와 대조했다. CLI SHA256 `3661de51195a29a01a13d5e38040d18d735bffcd5817bf60b60aaf1d407d7541`.

재현 명령과 인터페이스는 `docs/analysis/animation-execution.md`에 기록했다. CLI의 실제 I/O 실패는 두 출력의 원자적 교체를 보장하지 않는다. 자연 scheduler/IRQ, 직접 플레이, 상위 활성화 callback, 모든 animation opcode 및 전체 게임 목표는 미완료다. 다음은 남은 handler의 원본 계약과 상위 caller 연결이다.
