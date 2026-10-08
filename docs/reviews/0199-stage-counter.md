# Stage counter 4843c 리뷰

Baseline `fb5e823`, branch `codex/stage-counter`. Sol6.1/medium 세 작업자가 core/unit, CLI/Make/문서, 원본 관찰·실제 C++ 비교를 분담했다. 메인은 원본 의미와 oracle 차이를 분석하고 core/단위검사/관찰기/검증기/개발용 batch harness를 읽었다. 원격 없는 로컬 통합이다.

## 발견과 수정

원본은 SUBQ.B2의 binary borrow/X를 source0 SBCD에 전달한다. gate가 켜져 있으면 두 SEQ BYTE 효과가 생기므로 조기 반환에서도 D0/D1 전체 보존으로 축약할 수 없다. SBCD carry 분기는 D0/D1 전체32bit를 지우며 나머지 경로는 상위24bit를 유지한다. 도달한 BYTE 주소만 검사하고 임의/홀수 A5, 정확한 high→low 쓰기 순서를 보존한다. 실패는 candidate RAM/state로 격리한다.

초기 pinned Musashi 비BCD 보정은 수용하지 않았다. 메인이 미수정 원본을 SBCD 직후에서 멈추는512조건 교차 검증에서 Unicorn과 불일치를 발견했다. [Flamewing의 실기 검증 보고 및 기준](https://github.com/flamewing/68k-bcd-verifier/tree/39a01be528b0744302bf1dc9b3463fc22a3fc45f)을 고정 revision/hash로 확보하고 별도 빌드했다. source0/destination256/X2의 결과BYTE·C/X는 Unicorn과 모두 일치하며 Musashi는301조건이 다르다. Sol이 table indexing, 양쪽Z, 입력 hash와 결과를 독립 감사했다. 외부 저자의 실기 검증과 이 프로젝트의 직접 측정을 구분한다.

이에 따라 C++은 X0에서 모든 raw BYTE를 그대로 보존하고, X1에서만 low nibble에 따른 감산을 수행한다. dst0/X1의 raw99/carry1 이후 원본 caller가 전체D0/D1을0으로 지우는 효과를 반영한다. 새 동작에 맞게 비BCD 단위 기대값도 수정했다. 초기 Musashi 관측은 별도 진단으로 보존했으며 전체WORD39,914개에서 결과/레지스터가 다르므로 acceptance 근거로 사용하지 않는다. 외부 GPL 구현과 생성 table은 ignored artifacts에 보존하고 engine에 복사하지 않았다.

지원 도구의 이전 성공 보고서를 먼저 지우는 보강 중 report 경로와 reference 경로가 겹친 변수 문제를 발견했다. 별도 `report_path`로 수정하고 임시 reference LICENSE를 고정 원본/hash로 복원했다. 재실행 후 보고서 존재, 도구·LICENSE 포함5개 reference·table·ROM·oracle hash를 독립 감사했다. 게임 ROM/엔진 소스에는 이 도구 오류의 영향이 없다.

## 검증 근거

- `tools/check_stage_counter_bcd.py`:512조건, Unicorn0/Musashi301 차이. 보고서 SHA `bf692382e2f4905834e6cfc806944c4633d23d9989879a1b0adcf471c75d294e`.
- `tools/observe_stage_counter.py --oracle unicorn`:원본65,536 WORD +109 상세 gate/status/상위bit/홀수·경계A5 조건. 실제 ordered BYTE 쓰기131,072개, clamp2개, 세 분기 양쪽 관찰. 원본 hash·stack·전체RAM replay 검사.
- `tools/verify_stage_counter.py`:실제 C++ API65,536개, CLI621개에서64KiB RAM/15레지스터 일치. 개발용 batch harness는 원본 write 결과로 기대RAM을 재구성하며 BCD 수식을 기대값으로 복제하지 않는다.
- 오류·입출력 보존116조건, 실제 case alias, FIFO, 잘못된 숫자/크기/도달 주소, 새 출력 생성/미생성 검사 통과. API의 늦은 오류 rollback은 별도 합성 단위로 확인했다.
- `make -j4 all test`:Python196/C++ 실행 파일140/경고0, exit0. `artifacts/stage_counter_build_test.log`. 수정 core 단위의 격리 UBSan도 통과했다.
- 메인이 현재 inputs9/native_inputs18/native_artifacts453/reference_inputs7의 모든 해시를 다시 대조했다(그룹 간 중복 있음).

Verification SHA `2c9836dea6930615c4cd392af1f12fa880b38ace9fe57b96955c577df49368a4`; native SHA `aea00334404fbac5a894eedaa9049b639145e19f41f840bad29141900886f5b0`; CLI SHA `adc46a309be42550a22cc91f5d31756d9c5a2c353b83de2882deeb81d896e0f9`.

이 RAM 연산에는 runtime 리소스가 추가로 필요하지 않다. 최종CCR/N/V/cycles, 물리mirror, 자연scheduler/IRQ, 직접플레이와 전체47c6c는 완료 범위가 아니다.

## 다음 readiness 원본 준비

`stage-readiness-contract.md`의4847c→1bdde/289e/4dee2/4e166 전체 호출을 메인이 원본에서 확인했다. `observe_stage_readiness.py`의 실제 CPU/stack/read/write/carry 캡처를 읽고, 별도 Sol이 현재642개 case artifact hash와6조건의 메모리 내 재실행을 독립 감사했다. 원본214조건,19개 조건분기 양쪽,carry true86/false128,실제 callee 호출과 RAM 불변을 관찰했다. Musashi 선택10조건도 전체RAM/15regs/carry와 일치한다. SHA `45ad59018ae534c4059d6348dc835e09d37d9d08dbc3554e2562c7cfe90a4844`. 이 결과는 native 준비이며 해당 C++ 구현 완료가 아니다.
