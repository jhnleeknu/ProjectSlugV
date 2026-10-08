# 맵 전송·반복 경계의 실제 공유 스택 리뷰

대상 baseline `6212b39`, 브랜치 `codex/animation-machine-map-transfer`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 직전 팔레트 연결 통합을 진척으로 승계한다. 전체 목표·완료 기준·기존 진행을 유지하며 사용자의 지시에 따라 이 단계의 구현·검증·커밋을 마친 뒤 Goal을 일시중지한다.

## 원본 의미와 구현 범위

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Fixed CPU 주소는 같은 ROM 파일 offset이다. 메인이 실제16f0e/183c6/1861a/18702 명령, 기존 부분 API 및 리소스 주소를 읽어 폭·접근 순서·분기·실제 호출을 확정했다.48042→4804e의 JSR1861a/JSR17012와 열 제어·클리핑·primary/secondary 맵 전송·반복 경계를 공유 RAM/A7 실행기에 연결한다. 기존13R API의 host saved WORD 배열은 사용하지 않는다.

16f0e는 매 반복마다 live width를 읽고, column record의 앞·뒤 탐색 및 BYTE 게시 후 operand 재읽기를 유지한다.183c6은 WORD wrap과 unsigned borrow로 경계를 자른 뒤 실제MOVEM.W 여섯WORD를 stack에 저장한다. Bank3 primary 전송 뒤 live stack에서 sign-extended32bit로 복원하고 bank2 secondary를 처리한다.18702는 별도의 외부MOVEM.W frame을 만들어 실제 helper 결과 뒤 flags/dimension을 다시 읽는다. 마지막 추가 전송 뒤에는 복원이 없는 원본 순서를 유지한다.

Z/N-only 분기는 원본 writer와 묶고 해당 분기 PC만 임의 진입하는 것은 거부한다. DIVU는 선행ANDI.Lffff와 묶어 선언되지 않은 임의32bit dividend overflow를 암묵 지원하지 않는다. divisor를 다시 읽고0은 별도 checked 오류로 처리한다. ASR은 unsigned mask와 sign bit 확장으로 계산한다.185ee/185f4의 명시적인 C 설정은 지원하며 native SR 관측과 구분한다.

새39개 C 보존 block을 메인이 원본 opcode와 전체 block으로 확인했다:7RTS/8MOVEM/5BTST/7BSR/2JSR/2address ADDQ·SUBQ/4MOVEA/1LEA/2BRA/1BSET. Native 일반CCR 측정 또는39개 전수 native flag 검증으로 부르지 않는다.

## 실제 리소스와 출력

기존 여덟 MS5D v1 kind3와 C++ loader/bus를 사용한다. Fixed480f2 header는 `003c000000140010`이다. Bank3 CPU200004=physical300004에서 root200008을 읽고, CPU2000f8=physical3000f8에서 map CPU2a4e10을 읽는다. 물리 범위3a4e10..3a5314는20×16/1284byte이며 기존 chunk300000에 포함된다. 새 형식이나 이미지 확인물을 실행 리소스로 대체하지 않는다.

직전 palette fixture의 slotffff는 primary 전송을 건너뛰므로 일반 drawing 증거로 사용할 수 없다. 이번에는 원본47fe8→48042가 실제 할당한 slot348을 사용한다. 그 상태에서48042→4804e는320cell의640video LONG과6PVC 쓰기를 수행한다.47fe8부터 연결한 원본 실행도 포함한다. Video 출력은 instruction port 쓰기이며 완성 화면·물리bus cycle·직접플레이를 증명하지 않는다.

## 실행 한도 조정

기존100000 semantic block 한도는 원본의 정상 WORD count0→65536회 반복도 처리하지 못한다. 메인은 무제한 내부 loop로 우회하는 대신 유한 한도를1000000으로 늘리기로 결정했다. 공개stop API는 반복 PC의 임의 회차를 선택할 수 없으므로 수십만 번 호출하는 인위적 재개를 정상 완료 증거로 만들지 않는다. Native의 별도 instruction CAP과 semantic block 한도는 다른 단위다.

폭0의65536 skip loop는 원본327689 PC 진입으로 완료된다. C++ 전체 완료와 거대한 반복의 유한 budget 오류·전체 API rollback을 함께 검사한다. 전체 Goal의 완료 기준을 이 임시 실행 한도로 축소하지 않는다.

## 경계·비교 규약

실제 list/node/record/secondary source와 stack이 겹치는 입력은 live bus 순서로 실행한다. 원본 CPU fault의 부분 효과와 checked API 실패의 전체 rollback은 다르다. 초기 원본 준비 결과를 사용하는 새 fixture와 처음부터 이어가는 connected fixture를 구분한다. ROM 수정·예상register 주입·초기화 이후SR 읽기·stack masking을 사용하지 않는다.

기존screen/cleanup/scene/palette 비교기의 명시적인 unsupported 경계를4804e로 이동하고 역사적 정상stop은 유지한다. 기존 legacy palette 초기화 제약의 guard는 그대로 둔다. 184d2의 별도 zero-fill body,185fa/18656 wrapper 및4804e 뒤 timer/frame은 이번 호출 경로의 지원 범위에 포함하지 않고 후속 항목으로 남긴다.

## 검증과 인수인계

최종 원본/비교기 동결, 전체 빌드, 기존 회귀 및 현재 참조 감사 결과를 아래에 기록한다. 이 단계 완료와 전체 게임 완료를 구분하며, 검증·커밋 뒤 사용자가 요청한 일시중지를 실행한다.

메인 첫 `make -j4 all test`는 기존transition unit의 budget 기대값에서 실패(exit2)했다.35a2의65535열·높이0은 옛10만 한도에서만 실패했던 정상 무출력 반복이며 새100만 한도에서는 끝난다. 메인은 이를 fullreturn·D0 WORD wrap ffe0·D2.low0·RAM 불변·세 포트 순서/값을 확인하는 성공 검사로 바꿨다. 새 map의 거대한 반복 budget 실패/rollback 검사는 유지한다. 이 변경 후 전체 재실행 exit0: Python257개/C++162개 실행, 경고0. 최종 로그 `/tmp/ms5-map-transfer-main-make-final.log`, 최초 실패 로그 `/tmp/ms5-map-transfer-main-make.log`.

신규 unit 일반/UBSan 각각103 API 호출 통과, 경고0. Core SHA `5574db28d8cd3736af046b69b954e9119816291da96602abd330f139e540d24c`, unit SHA `066bb581013158c3652823504f9900f2fb9072752fba3b103afba0c2513be786`. 독립 core 검토는 원본298개 명령 바이트와39개 C 보존 block, 실제 체크포인트·live MOVEM·읽기 순서·한도 처리를 확인했고 추가 결함을 찾지 못했다. 검토 기록 SHA `7dc52847aca73a16aba4fe234eb41ae53ed8a02328fbeb61335f8ec017fcb3b6`.

## 공식 비교와 독립 감사

Native 정상50조건131split/50continuous와guard5조건을 두 번씩 실행해220freshcaseCPU/382case단계를 확보했다. 별도 원본 준비 실행은 이 수에 합산하지 않는다. C++50조건131단계·직전 실제출력81회 재개가 fullRAM/16R/PC/A7/PVC-bank·11666포트와 일치했다. 포트는video9212/watchdog2292/PVC162다. 독립 orderedPVC 계산으로bank2787/fixed280읽기를 검증했다. 대기·외부status읽기·native C 측정은0이다. 오류18조건(추가13+nativeguard5),zero-step33조건,source-only C writer 검사6조건을 통과했다.

Native tool SHA `5c3e49d5f3b74f275e2efc7d5c670b462be3f2e6a1b9e4c651a9d4816dbaf5e8`, report SHA `3cbf2b1b6b49c675f116c8298f09d36feb817ae76173fcab4d03a71b1428abf8`. C++ verifier SHA `75ffc969bee9f16ed916aad7abe9d96207268b8d321380f2150aef84129bb8c4`, report SHA `78f2dfb30e4a8710a4044f6be7985f8220632213190af5eff4a28f8beb854844`. 메인이 현재 native1549개/C++2715개 고유 참조를 직접 SHA 대조했다.

독립 native 감사는 대표27조건73split/27continuous, 모든5guard와 두 profile의 whole/connected tile전송·65536loop·live MOVEM/column/secondary alias를 재실행해 fullRAM/16R/PC/rawPVC/ports/trace/stack/snapshots가 일치함을 확인했다.65536 loop의 continuous PC수는327689이며 split에는 반복checkpoint PC 한 번이 추가된다. 독립검토를 추가 전체matrix 실행으로 부르지 않는다.

Shadow RAM100010의 실제 bank3 write가 savedD5 WORD를1로 바꾸고18530이1로 pop한다. 외부MOVEM의 savedD0가 node+7a와 겹치면 BSET 후8000을1874a가ffff8000으로 복원한다. Secondary source/destination overlap은 다음 상대offset0040을1236으로 바꾸고1857c가 그 변경값을 읽는다. Column write가 savedBSRreturn00018742를00218742로 바꾸는 fault는 정상 복귀 증거로 계산하지 않는다.

독립 native 검토 SHA `69e334b6acad2dd78a848cfc21dced8e0b5ad0cdb3bda713254651e28e8229d0`, 최종 core 검토 SHA `a0965f39538377b900492383e10e9983ff2cb663bbce087a2eb1853c6c2f80fc`, verifier 검토 SHA `2b34334bb5221bcef7059d205a78364bf77266d740142c46680c1553bc3af4cd`. 최종 core 검토는 실제native의14개 incoming checkpoint가 구현된 block임을 추가 확인했다. 역할을 나눠 자기 구현을 독립 검토했다고 주장하지 않는다. 메인은 실제소스·검토 기록·검증 결과를 읽고 수용했다.


## 최종 회귀·참조 감사와 일시중지

기존12개 공식 회귀가 모두 통과했다. 메인은 새 map을 포함한13개 보고서의 현재 입력·산출물 SHA와 중복 경로 일관성을 직접 확인했다. 고유 합집합37744개가 일치했고 각 담당자의 감사도 통과했다.

| 보고서 | SHA256 | 고유 참조 |
| --- | --- | ---: |
| `animation_machine` | `f2d668f028a71ae9cfd70ab5a54d4795dd596daf2be10580a1783bfa238db097` | 1719 |
| `animation_machine_callers` | `51eab1bb8b488d4443e09f09bd27ca77ea227017ebce113ba3cd1ed1919fe758` | 1245 |
| `animation_machine_carry` | `1fbe17ff593684444ee14d846c15232a646832c4f3b0d8ca2685d5bb04595b9c` | 3054 |
| `animation_machine_activation` | `9a6d28b0c65457785225c131d48b8140aa81ececf98df744f688246827a0b673` | 1048 |
| `animation_machine_readiness` | `372520936cefebf290812da2e69362bed7fd18e905f8d35846593daffcd74e1c` | 2987 |
| `animation_machine_hud` | `2cb08a971e63229eda34e512a2fb03aff59952784d6c2918b05bcbbed562dd46` | 5000 |
| `animation_machine_transition` | `74013fc99a7c5fc02aa06a0a52568360bee9e5c5bcd8e32bec10b4549cace67b` | 4208 |
| `animation_machine_exit` | `f22815dc6aecbd1bbec15ca91825b43a137e82d78623eff90f7c0e2915c90ddd` | 4655 |
| `animation_machine_screen` | `7eec616d93762c7a3bd746ba99eb2c981360d6bf0da83176808fa799cc34a6db` | 2593 |
| `animation_machine_cleanup` | `55d9c40a4faafdf74857bcffd3a9fe0ba90092e8213467e68af7b15b2ca0a408` | 2553 |
| `animation_machine_scene` | `e2dd5fa948dfb33e51647b19b4bed084085898af227049cf947df650aad6c8af` | 4287 |
| `animation_machine_palette_bind` | `7c1100ad7aa0a857c47460ba3227d741742b817ed9b38d07bff5e61024bbe52e` | 2868 |
| `animation_machine_map_transfer` | `78f2dfb30e4a8710a4044f6be7985f8220632213190af5eff4a28f8beb854844` | 2715 |

새 파일을 포함한 staged whitespace 검사를 통과했다. 원본·추출물을 제외한 소스·도구·규격·검증 기록만 로컬 커밋한다. 원격은 없으며 로컬 커밋을 PR이라고 부르지 않는다. 사용자의 “지금 단계만 하고 일시중지” 지시에 따라 이 통합 후 Goal을 paused로 전환한다.4804e 후속 구현은 시작하지 않았고, 전체 Goal 완료를 선언하지 않는다.
