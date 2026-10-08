# 오브젝트 정리·해제 공유 스택 리뷰

대상 baseline `54a69c4`, 브랜치 `codex/animation-machine-cleanup`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 전체 목표 범위·완료 기준·기존 진행을 유지한다.

## 원본 의미와 구현

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 계약의 fixed CPU 주소는 같은 ROM 파일 offset이다. `299c/2782/271c/287e/2a0a`의 실제 호출, 목록 연결·free-list/count 갱신, palette reference 해제, coordinate 부모·stamp 처리, 네 wrapper와 `477c2/47fe4`를 공유 RAM/A7 C++11 실행기로 연결했다. 기존 여덟 MS5D v1 kind3와 실제 C++ loader/bus를 사용한다.

메인은 원본 의미 계약과 최종 실제 TU·routing·carry 분류·비교기·독립 리뷰를 확인했다. WORD 비교는 unsigned이며 부분 register 쓰기는 상위 비트를 보존한다. 연결 정보와 palette reference는 앞선 쓰기 뒤 live 읽기이며 임의 count4 제한을 두지 않는다. 좌표의 두 WORD carry는 인접 ADDX 의미로만 계산하고 일반 CCR 지원으로 확대하지 않는다. 좌표 publication 뒤 global stamp를 다시 읽는 순서를 보존한다. 원본 코드·RAM 예상값 주입·SR 읽기·stack mask를 사용하지 않는다.

## 발견 사항과 수정

1. `2a44/2a5c/2a80/2aa8`의 A6 pop과 RTS를 합치면 원본의 복원 직후 checkpoint에 도달할 수 없었다. 각각 pop과 실제 RTS를 분리했다. 저장 slot이 reset에 의해 바뀌어 A6=`ffff3400`이 되는 원본 사례는 `2a46` RTS 전까지 검증한다. 함께 손상된 outer return의 정상 실행을 주장하지 않는다.
2. 독립 리뷰는 `2a40`의 A0 pop과 `2a42`의 LONG pop/write가 합쳐져 중간 checkpoint를 건너뛰는 문제를 찾았다. `2a40→2a42→2a44`로 분리했고 MOVEA만 수행하는 `2a40`은 C 보존, MOVE.L 쓰기의 `2a42`는 Unknown으로 분류했다. 첫 공식 비교는 이 문제로 실패했고 성공 보고서를 게시하지 않았다. 수정 후 공식 비교를 새로 실행했다.
3. 최종 62개 C 보존 block과 fixture checkpoint 도달성을 감사했다. 원본 stack-overlap guard는 `278e` RTS가 `ff0029ac`를 읽는 경우다. 초안의 다른 fault 주소는 관측 후 동결 전에 정정했다. API transactional rollback과 실제 CPU fault의 부분 효과를 구분한다.

## 검증

메인 `make -j4 all test` exit0: Python257개, C++159개 실행, compiler warning0. 최종 로그 `/tmp/ms5-cleanup-main-make-final.log`. 새 unit 일반·UBSan 각각223 API 호출 통과. 최종 core SHA `742e749f2c7450ae6844511f65b8f075d0c446f5835c0087f50f759c1e44df91`, unit SHA `a185ae1ae93d8a62bdf39fad8103efe3d68a72444eb2d9891cfe98f3acbf919b`.

원본 정상69조건121split/69continuous, guard3조건 각각3split/3continuous를 두 번씩 실행해288freshCPU/392단계를 확보했다. 실제 C++69조건121단계·직전 실제 출력52재개가 full64KiB RAM/16R/PC·PVC/bank·63watchdog포트·외부읽기0·대기0과 일치했다. 원본 분기 successor로 known C29단계, 오류17조건 및 zero-step33조건을 확인했다.

Native source SHA `d1e5051a482423c0078b53e958b59ac403cdd294b1d7494befd18de2abd032be`, native report SHA `12b825b02281f215bc554605dffc30c8d1e28d9921ac3a49cc40081df0e7553a`. 비교기 SHA `4f0cd7fc20b71b1af8a7200e64c640b03d00cd68aea984939ee6e7f9cb6cf215`, C++ report SHA `5f547e6405afd24dff36bbf5f2eb1ae7b61e1b605c6c3b02bd55c838c2ac5988`. 실제 cleanup 계약을 입력 pin에 포함한다.

독립 native 감사는57조건109split/57continuous, 모든3guard와1458개 고유 참조를 확인했다. 메인도 native1458개 참조의 현재 SHA를 직접 확인했다. 독립 비교기 감사는 최종2520개 고유 참조와 실제 이전 C++ 출력 전달을 확인했다. 반복 branch의 carry는 실행 순서와 바로 다음 successor로 판정한다. `2a16`은 같은 체인에서 Clear/Set 모두 관측했고 `29c4`는 사례 전체에서 두 방향을 관측했다. 후자의 같은 cascade에서 반대 carry가 관측됐다고 주장하지 않는다.

## 협업과 제약

Sol6.1/medium3명이 core/unit, native 관측, 비교기/문서를 담당하고 교차 리뷰했다. 동결 뒤 기존 아홉 회귀를 세 명에게 세 개씩 나눴다. 메인은 복잡한 의미 해석·계약·실제 diff·전체 빌드·최종 근거 확인·통합을 맡았다. 독립 작업 세 개를 사용하며 외부 작업자 수를 채우기 위한 중복 작업은 만들지 않았다.

`47fe8`의 LEA48108/43ffc는 실행 전 경계다. 기존 screen의 명시적 unsupported 검사만 `47fe4`에서 이 경계로 이동했다. 기존 native 관측과 역사적 stop 경계는 변경하지 않았다. 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체스테이지/적/보스·미사용 자료 전체 의미는 미완료다. 현재 단위의 성공을 전체 게임 완료로 취급하지 않는다.

## 최종 회귀 및 참조 감사

기존 아홉 공식 회귀가 모두 통과했다. 메인이 새 cleanup을 포함한 열 보고서의 입력·산출물 SHA를 현재 파일과 직접 대조했다. 중복 경로는 같은 SHA인지 확인했으며 고유 합집합은28143개다. 독립 최종 감사도 일치했다.

| 보고서 | SHA256 | 고유 참조 |
| --- | --- | ---: |
| `animation_machine` | `6bdca969f068d6278ed07ac31adfe216ffe7da61da85037ace7366187565b555` | 1716 |
| `animation_machine_callers` | `cc7ea9f4228c8a182efb7981c89b004926e3d163520621f55fa82c26157fef84` | 1242 |
| `animation_machine_carry` | `f58ff8e9376cf6ceff8fa2b1c0699855ba6208d9c9a76c69f8983c66ab885c6a` | 3051 |
| `animation_machine_activation` | `db205194096f7522f26931b5373e3bed225c895b87bc518f6aef330e98e81bdb` | 1045 |
| `animation_machine_readiness` | `2a567d72f2d1a871ed6144a384901b71b2cd6536b603f0349d247f52b9f1541c` | 2984 |
| `animation_machine_hud` | `6f238ddebec7269cfa60aa1573fc1167ed4b7c7120ad608b70d6808b985d7bcd` | 4997 |
| `animation_machine_transition` | `4f120d767c24dfc8f15f57fef24b57fa9a00f637a9cb5382bfdaeee18edd1b6f` | 4205 |
| `animation_machine_exit` | `1c74d24f813d79902a6e8dcb225f4f4bc9b51848e4917950d5c924c216edd445` | 4652 |
| `animation_machine_screen` | `c5f023a3c75a264c194aae43db0cbeded7a8c0f0d6052edb0e2fa1bb8a9e8df8` | 2572 |
| `animation_machine_cleanup` | `5f547e6405afd24dff36bbf5f2eb1ae7b61e1b605c6c3b02bd55c838c2ac5988` | 2520 |

원본·추출 데이터를 제외한 코드·재생성 도구·규격·검증 문서만 버전 관리한다. 임시 감사 파일의 존속을 재현의 전제로 요구하지 않는다.
