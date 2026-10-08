# 상태·요청 분기 및 fill 연결 리뷰

대상 baseline `915a4c3`, 브랜치 `codex/animation-machine-transition`. 최종 대상은 이 문서를 포함하는 통합 커밋이며 로컬 리뷰다. 앞선 HUD 단위는 완료된 진척으로 승계했다. 전체 Goal·완료 기준은 유지한다.

## 원본과 변경

메인은 canonical BE SHA `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`의 `bee..c36`, `4e216..4e24e`, `47d24..47da4`, `477ac..477c2`, `35a2..35f0` raw bytes를 읽고 C++ source·routing·unit과 대조했다. 상태 helper/요청 소비의 실제 carry, 상위 BCC/BCS, signed flag 선택, pending WORD/timer와 사운드 호출, 화면 채우기를 shared RAM/A7에 연결했다.

477ac은 WORD만 바꾸고35a2로 tail JMP한다.35a2는 폭·높이0을 명시적으로 건너뛰며35f0과 달리 tile BYTE를 증가시키지 않는다.300001 BYTE,3c0004 WORD,3c0000 LONG/WORD의 실제 접근 순서만 기록한다. watchdog/video 전체 장치나 물리 시간의 구현을 주장하지 않는다. 기존 MS5D v1 kind3 여덟 개와 실제 C++ loader/bus를 사용한다.

## 발견 사항과 해결

- 메인은 초기35bc 구현이 D6.low를 보고 BEQ 결과를 결정하는 문제를 발견했다. 원본35bc는 Z를 소비하지만 public machine state에는 Z가 없다. 따라서 임의 진입에서 이 추론은 성립하지 않는다. 실제 Z writer인35b4 MOVE.W와35c0 block의 SUBQ.W에 BEQ 처리를 합치고 direct35bc는 checked 오류로 거부했다. 관련 단위·비교기 음성 검사를 추가하고 수정된 source를 다시 동결했다.
- 독립 core/비교기 리뷰에서 새 검증기가 이전 HUD 계약만 pin하고 실제 transition 계약을 누락한 것을 발견했다. 이전 성공 보고서를 삭제하고 실제 계약을 추가한 소스로 전체 원본/C++ 비교를 재실행하도록 했다. core/common source는 바뀌지 않아 독립된 기존 회귀 실행은 유지했다.
- 메인은 caller JSR가 첫 status BYTE를 덮는 alias와 요청 BYTE가 live RTS LONG에 포함되는 alias를 제안하고 원본 기록을 확인했다. 요청 restore는 return00047d34를 유지하고 consume은00040034로 바꾸므로 후자는 guard와 C++ rollback으로 구분한다. native fault가 기존 RAM 쓰기를 되돌린다는 주장은 하지 않는다.

## 검증 현황

메인의 `make all test`는 exit0, Python257개/C++156개 실행, compiler warning0이다. 로그는 `/tmp/ms5-machine-transition-make.log`다. 수정된 unit은 일반/UBSan 각각500회 API 호출을 통과했다. Source는 `7af55a1f9f33171e4199e905484cf3b3c9dd751005abd20a278b6199a73ef77e`, unit은 `15cf436104766d2909980387bd63a5879f3c66ddfaec6e38f89610c0ceebc2c4`다.

Native 정상107조건 split224/control121단계와 guard3조건(각 split/control1단계)을 두 번씩 실행했다.440freshCPU/702실행단계이며 대기14단계, 정상 포트721개(워치독12/비디오685/PVC24)다. 세 실제 BCC/BCS에서 Clear/Set 양쪽을 확인했다. 메인은 현재2591개 입력·산출물 해시를 검사했다. Observer source SHA `dff0b6e68dcb6b3364548028dfa99e83f5721742684e43fabbf2e8ea2f607d0e`, native report SHA `edf1f5e7248601d2a708cbc7ebfb8a89c62bfdb5dcef018cb94a2c5fa26aaba4`.

독립 native 감사는 전체110개 fixture 출처,2591개 파일/2518개 단계 참조를 확인하고 대표66조건·137split/80continuous단계를 재실행했다. 대기14단계,5개 대기 fixture,3guard, 두 종류 stack alias와 세 C 분기의 양쪽을 포함한다. 감사 기록은 `/tmp/ms5-transition-native-independent-review.txt`, SHA `2ee6a56de1792853b19a1bfb60061a777b221cdc0747ca1f3028bd3d3bf36005`다. 메인이 기록을 읽고 핵심 근거를 확인했다.

실제 계약 pin을 보강한 최종 C++ 비교는107조건·224단계, 직전 실제 출력117회 재개,14대기,721포트·외부읽기0회를 통과했다. 원본 분기 근거의 known C147단계가 일치했다. 오류15조건(추가12+원본guard3)과 zero-step24조건도 통과했다. 메인은 source/input 목록의 실제 transition 계약 pin과 최종4199개 현재 참조 해시를 확인했다.

최종 비교기 SHA `80e7440a729ad7c55b55f61cc5b118514be027bcd35ad09065e9a674b4524110`, 보고서 SHA `0da18b6f00f26a2a78a4be8ef256b50a361ff9ccf89d74ea5bd30d673f2a4f2b`. 공통 검증기의 source 목록 추가 후 SHA는 `bdb514880e02354d394fad714e81d7824b2d53dd2680d4e99ccdec23d3e2480f`다.

독립 core/비교기 리뷰는 실제16개 C 보존 PC, full-width/partial-width 연산과 접근 순서,35bc Z 수정, 실제 branch successor oracle, 포트 형식과 transaction을 검토했다. 누락된 계약 pin의 수정 후 현재4199개 파일을 다시 감사했고 남은 결함은 없었다. 메인은 최종 기록을 읽었다. `/tmp/ms5-transition-core-independent-review.txt` SHA는 `24b0f5dbae8bdf588400800e5879a378150122c14e52aa5fc8059a030f841ca9`다. 임시 파일의 존속을 재현 조건으로 요구하지 않으며 핵심 근거는 본 리뷰와 versioned 도구에 남긴다.

기존 여섯 검증기도 모두 exit0으로 통과했다. 기본94조건/131단계/37재개/9오류, caller59/91/32재개/6오류, carry60/160/100재개/10오류+zero-step3, activation52/74/22재개/9오류, readiness68/154/86재개/14오류+zero-step3, HUD124/277/153재개/15오류+zero-step9다. 메인은 새 보고서를 포함한 일곱 보고서의 고유 파일 합집합18695개를 현재 파일과 대조했다.

| 보고서 (`artifacts/*_execution/verification.json`) | SHA256 | 고유 참조 |
|---|---|---:|
| animation_machine | `2c6bac72773d52692cd0a19113b51a728a94d9f20e6c30ba74b6c1922854cc9f` | 1710 |
| animation_machine_callers | `32cc2c866e5378f79d05716ca8b14871cf444e396e9ff108fa6ab795a011fac8` | 1236 |
| animation_machine_carry | `07e85b8bb4ce6c170ed6c919f90b2caba538eea39e639ea202e6b22ce91debc8` | 3045 |
| animation_machine_activation | `0f6633c300d7cb09f39efd32445707ff855be69a49bb0b729471353f68dba02f` | 1039 |
| animation_machine_readiness | `98d1a307ce3ef120c1800ab4aa79280c925aa9b22e57fa9f937f69621161da67` | 2978 |
| animation_machine_hud | `88fbed53e51772537226d54427aacf2ebbba951d5ae952766e863cb5114403ac` | 4991 |
| animation_machine_transition | `0da18b6f00f26a2a78a4be8ef256b50a361ff9ccf89d74ea5bd30d673f2a4f2b` | 4199 |

## 운영과 남은 범위

Sol6.1/medium 세 명이 core/unit, 원본 관측, 비교기/문서를 담당하고 교차 리뷰했다. 메인은 원본 의미와 Z 의존 문제, 계약·diff 검토, Makefile·상태·리뷰 및 통합을 담당했다. 동결 후 여섯 회귀는 base/callers,carry/activation,readiness/HUD를 세 작업자에게 나누고 각자 별도 출력 폴더에서 실행했다.

47f4a/477ee/47da4/480bc 및47eac의 후속 body, 자연 scheduler·IRQ/timing·일반CCR·직접 플레이·전체 스테이지/적/보스·미사용 자료 전체 의미는 미완료다. 애니메이션17중14종+14/3c 일부의 기존 집계와 전체 Goal active를 유지한다.
