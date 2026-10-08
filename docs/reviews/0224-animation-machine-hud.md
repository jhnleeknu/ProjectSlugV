# HUD·BCD 공유 스택 통합 리뷰

대상 baseline `24d13ff`, 작업 브랜치 `codex/animation-machine-hud`. 이 기록의 최종 대상은 본 문서를 포함하는 통합 커밋이다. 원격 PR이 아닌 로컬 리뷰다.

## 변경과 근거

메인은 원본 `47c6c..47cae`, `4843c..4847c`, `4e286..4e332`, `8cda..8d34`, `35f0..362a` bytes를 다시 읽고 새로운 C++ HUD 모듈의 접근 순서, 비트 폭, 실제 JSR/RTS, tail JMP, 데이터 조회와 원자적 실패 계약을 대조했다. 전체 프로그램 MS5D v1 kind3를 실제 loader/bus로 읽으며 ROM과 리소스 형식을 변경하지 않는다.

사운드·팔레트·숫자 출력의 saved WORD는 호스트 metadata가 아니라 공유 RAM에 있다. 실제 스택 alias가 복귀값을 손상시키는 경우도 오류로 드러난다. 일반 CCR을 추측하지 않고 새 block은 기본 Unknown이며 확인된 JSR/BSR/RTS/LEA-only block만 C를 보존한다. 비디오 trace는 기존 LONG/WORD 명령 접근 단위이고 PVC 모델·WORD 포트와 구분한다.

## 발견 사항과 조치

- 메인의 초기 정상 palette alias 제안은 잘못된 추론이었다. 원본 관측에서 target 쓰기가 saved WORD뿐 아니라 JSR return의 low WORD도 덮어 `00040a0d`로 복귀했다. 정상 pop 증거로 사용하지 않고 원본 guard와 C++ 전체 rollback 음성 검사로 분류했다. 구현과 계약에 반영했다.
- 원본 관측 초안의 정상 rectangle 입력 일부가 원본 TRAP 한계를 넘었다. 유효 범위의 정상 입력과 명시적 TRAP guard로 나눴다. 잘못된 명령 경계3626과 누락된 RTS3628도 원본 bytes로 수정했다.
- 독립 검토에서 HUD gate0/특수 숫자 경로가 upper fixture 초기화로 빠져 실제 도달하지 않는 checkpoint를 지정하는 문제를 발견했다. fixture 분기를 group별로 한정하고 재생성하도록 했다.
- 독립 검토에서 alias fixture의 사용하지 않는 초기 쓰기가 RAM 밖 주소로 표시되지만 helper가 low16으로 RAM에 쓰는 출처 오류를 발견했다. RAM mirror 범위를 검사하고 실제 canonical 사운드 초기화 주소를 사용하도록 수정했다. 원본 실행 결과 주입으로 해결하지 않았다.

## 검증 현황

메인의 `make all test`는 exit0, Python257개와 C++155개 실행, compiler warning0으로 통과했다. 새 단위 검사는 작성자의 일반/UBSan 각각1283회 API 호출을 통과했다. 메인은 실제 소스를 읽고 전체 빌드 검증 결과를 확인했다.

원본 관측은 정상124조건·분할277단계·연속138단계와 guard3조건(각1단계)을 각각2회 실행했다. 합계508개 fresh CPU/842단계 실행이다. 정상 분할 실행의 대기14회, 비디오732/PVC24포트, raw lookup16개 WORD주소 전부를 확인했다. 메인은 현재 입력71개와 산출물3083개, 합계3154개 고유 해시를 직접 검사했다.

원본 도구 SHA `715b9631674bf3a5cafa13b9254d45398448de6ac67f891376fac63d3a1619fe`, 보고서 SHA `41408a8aa9f6f47468632aca987db6f8fb773660ae2e78b4990a0545ff536a72`.

C++는 정상124조건·277단계와 직전 실제 출력153회 재개를 통과했다. 전체64KiB RAM·16레지스터/PC·장치 상태/bank·ordered756포트·외부 읽기0회가 일치했다. 준비 상태 분기의 known C12회도 실제 BCC 근거와 일치했다. 별도 오류15조건(추가 API 오류12+원본 guard3)의 전체 출력 보존과 zero-step9조건을 확인했다. 메인은 현재 고유 참조4990개 해시를 검사했다.

비교기 SHA `715e52b014bab1af7bc4bf723a020ffc161e682c559eeb3b4c9a294c27085282`, C++ 보고서 SHA `ddfa3e768c229bee082c7321579236670fbef75e14a7da4b846226210c269d91`. Source 목록에 HUD 파일만 추가한 공통 비교기의 SHA는 `c77866127c68924f785251c4123d115142e6ff2e4339e2fa1b3ddb52e3850a2b`다.

독립 원본 감사는127개 fixture 출처와 전체3154개 해시를 검사하고 대표60조건·분할132단계·연속74단계를 재실행했다. 대기14단계와 guard3개를 모두 포함했다. 별도 core/비교기 리뷰는 실제12개 C 보존 PC(6호출/5RTS/1LEA), 원본 읽기·쓰기 순서, 포트 형식과 rollback을 검토하고 최종4990개 해시를 확인했다. 남은 결함은 발견하지 못했다. 메인은 두 감사 기록의 내용도 읽었다.

감사 기록 SHA: `/tmp/ms5-hud-native-independent-review.txt`는 `dc142074c3970162866130b586033084e5a01e420b1a01f2f04ce3d67595b9ab`, `/tmp/ms5-hud-core-independent-review.txt`는 `9da356037989e3c3ce425fc8e68945fd7ddd53f73428fa677532c5b48577fc6f`다. 임시 경로의 존속을 재현 조건으로 요구하지 않으며 핵심 결과는 본 리뷰와 버전 관리 도구에 기록한다.

기존 다섯 machine 검증기도 모두 exit0으로 통과했다. 기본94조건/131단계/37재개/9오류, caller59/91/32재개/6오류, carry60/160/100재개/10오류+zero-step3, activation52/74/22재개/9오류, readiness68/154/86재개/14오류+zero-step3이다. 새 HUD를 포함한 여섯 보고서의 합집합14589개 고유 참조 파일을 메인이 현재 파일과 대조해 모두 일치했다.

| 보고서 | SHA256 | 고유 참조 |
|---|---|---:|
| animation_machine_execution | `ec26d29e69a54bb93121af0f3c651ee628a1838c77f012996421a88fd1b0558c` | 1709 |
| animation_machine_callers_execution | `b673a46a7b88c4bb31563062afa80b6493fb8107605cfa3136a313f4bf408573` | 1235 |
| animation_machine_carry_execution | `ba24cf0e425d2fa506fef9f2a6e00d667ebe475a8dd11bf43274962916837dec` | 3044 |
| animation_machine_activation_execution | `e3d59b40f4cfd5188f44b2fd4e27620b7c1e7c1aacf8bf9d6f680f3b36151f38` | 1038 |
| animation_machine_readiness_execution | `8c334f1bdd20338a9f5657b021ceea3196d8f12995142159a9ffd5adc2838f6f` | 2977 |
| animation_machine_hud_execution | `ddfa3e768c229bee082c7321579236670fbef75e14a7da4b846226210c269d91` | 4990 |

## 범위와 운영

Sol6.1/medium 세 작업자가 C++/단위 검사, 원본 관측, 비교기/회귀/실행 문서를 나누어 담당했다. 메인은 복잡한 원본 계약, 실제 diff 검토, Makefile, 본 리뷰와 상태 기록 및 통합을 담당했다. 구현 완료 작업자는 독립 원본 감사로 재배정했다. 초기 두 회귀 이후 아직 시작하지 않은 carry/activation/readiness 검증은 서로 다른 출력 폴더와 동결된 입력을 사용함을 확인하고 세 작업자에게 병렬 배정했다. 독립 작업3개에 맞춰 내부 작업자3명을 운영했다.

전체 Goal과 기존 완료 기준을 유지한다. 애니메이션17종 중14종 및14/3c 일부 callback의 기존 집계를 유지하며 전체 복원율은 산정하지 않는다. 자연 scheduler·IRQ/timing·직접 플레이·전체 스테이지/적/보스·미사용 데이터 전체 의미는 미완료다.
