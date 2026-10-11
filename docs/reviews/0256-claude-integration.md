# Claude 착수 범위 통합 리뷰 (검증 진행 중)

## 범위와 원본 보존

사용자가 2026-10-11 지정한 범위는 U15b/U15c 마무리, 이미 구현된 F2/F3/F4 U01~U16 통합, 통합 버전의 원본 비교와 전체 회귀 검증이다. U17 이후와 새 R 단위, 전체 게임 확장은 포함하지 않는다. 기존 전체 Goal의 완료 기준은 변경하지 않으며, 등록된 전체 Goal의 일시중지 상태와 이번 제한 작업을 구분한다.

- 메인 기준: `6346ef3442aafcc978db6c651e5cd0b13c87d06b`.
- Claude WIP 기준: `1aa80c8946dea11a5870654a86f889df6deccd28`; U15b `c2a90ec40be5d730be8ea2c7222e2f420d56929a`; U15c 미커밋 소스와 테스트.
- 통합 브랜치: `codex/claude-integration`. `ade4f04`는 U15b/U16 충돌 해결, `e0657a2`는 기존 메인 진행 통합, `9d5aa11`은 U15c 등록 완료다.
- 원래 checkout의 변경과 산출물을 덮어쓰지 않고 별도 작업 디렉터리에서 통합했다. native 산출물은 읽기 전용 입력으로 재사용하고 새 검증 출력은 통합 디렉터리에 둔다.
- canonical BE ROM SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.

## 담당

메인은 충돌 해결, 원본 의미 판단, 통합, 회귀 검토를 맡았다. 내부 작업자 세 개는 모두 `gpt-6.1-sol` / `medium`이며 U15b/c 및 카드 검증, F2/F3 검증, F4 원본 비교를 분담했다. 새 Claude 작업자는 생성하지 않았다.

## 통합 검토

U15b와 U16이 동시에 추가한 Makefile, 라우터, 내부 선언, 공통 검증기의 소스 목록을 양쪽 모두 보존했다. 메인과 WIP 충돌에서도 새 실행부와 그에 맞춘 단위 시험 경계를 유지했다. U15c의 등록은 U15b와 함께 연결했고 U08b 시험의 양쪽 경계 이동을 합쳤다.

U15b/U15c의 각 96개 BRA 테이블 및 U15c 96개 ORI/MOVE 본문 상수는 원본 바이트와 독립 대조했다. 고정 CPU 주소 <100000이므로 해당 단위의 CPU 주소와 ROM 파일 오프셋은 같다. 라우팅 범위는 각각 [4578a,45b12), [45b12,461ec)이며 겹치지 않는다. 정수 연산과 배열 인덱스, C 보존 등록을 검토했다.

빌드 중 동일한 공통 엔진을 모든 테스트마다 다시 컴파일하는 비용이 커서 Makefile을 동일 소스·옵션의 오브젝트 재사용 방식으로 변경했다. 테스트 목록과 링크 순서는 유지한다. 검증기 컴파일 시간 제한은 병렬 실행 시 60초 초과가 발생해 300초로 늘렸으며 실행 비교 범위는 줄이지 않았다.

## 현재 확보한 검증

- `make -j4 all test`: 종료 0, C++ 테스트 실행 파일 204개, Python 테스트 257개, 컴파일 경고 0. 로그 `/tmp/ms5-integration-build-final.log`.
- 통합 U15b/c UBSan: 종료 0, 진단 없음. U15b 803 fixture/144 block/2,584 호출; U15c 427 fixture/196 block/2,879 호출. 재현 명령은 `.venv/bin/python tools/verify_u15_integration_sanitizers.py`(새 출력 디렉터리 필요)이며, 실제 명령·입력 및 바이너리 해시는 `build/sanitize-u15review/verification.json`에 기록한다.
- F4 일반 연속 비교(보조 진단): 142 seed, 10,498 패스, 79,680 노드 비교 일치. 이 도구만으로 인수 판정하지 않는다.
- F4 RNG 연속 비교 및 별도 입력 감사: 기본 142 seed에서 24,646 패스·169,037 노드, 변형 6 seed에서 844 패스·6,116 노드 일치. 원본 종료까지 도달한 seed는 각각 61/2개이며, 나머지는 검증된 미지원 경계와 홀수 주소 오류다. 보고서 SHA256 `029560b57a24b4b1679f30ce695a40081d76309cea0dc0ea277ba6d655bcf027`. 감사 도구는 148개 고정 관측 파일, 8개 MS5D의 오프셋·CRC·ROM payload 해시, 현재 소스 및 독립된 이전 헤더 해시를 확인한다.
- F4 개별 matrix 및 인수 감사: 4,743 row 중 실행 일치 4,657, 명시적 rollback 경계 77, 원본 step limit 8, 기존 flag 전제 위반 입력 1. 미분류 불일치 0. 보고서 SHA256 `be71ac7a2f690b580dafd397cbefa035bfc08e9eacea8b6777652659d55066e0`.
- F3a: typed 560(일치 443·guard 117), 22,870 typed phase, natural 9,613, negative 1,020, zero-step 402. 보고서 `542a78105a6796eb31efabcf57ca97b140bad05d4a47e0e88fe5ccf4684910f3`; 입력 103개·관측 artifact 13개 해시 일치.
- F3b: typed 284, phase 5,081, guard 38, 의도된 차이 4, natural 471, negative 894, zero-step 351. 보고서 `99c6f9c5780f95cf70f9551f4f4e98056313f2eb0d4d337123c19905943e561e`; 입력 104개·관측 artifact 13개 해시 일치.
- F2: 142 seed, 원본 동등 whole pass 10,498, node 종료·port digest 79,680, RAM dump frame 6,946, 추가 fixture 20, negative 177, zero-step 51. 보고서 `d1ac590d286ae584897ac76802b13890b73e728fd7061b44330cce3c4127a6d0`; 입력 104개·관측 artifact 13개 해시 일치.
- 나머지 원본 회귀는 최종 도구 버전으로 완료 여부를 확인 중이다. 이전 개별 WIP 결과를 통합 완료로 대신하지 않는다.

## 검증기에서 발견한 사항

- 구현된 d72fe, e84d6, 2aac 등은 예전의 미구현 주소 검사를 그대로 적용할 수 없다. 원래 원본 정지 경계와 일치하는 앞 구간을 유지하고 새 첫 블록 및 이후 오류를 별도로 확인한다.
- U04 직접 d73ca 진입에는 원본 CMP 결과의 Z 전제가 있고, U12 직접 70198/701cc에는 live (A3) WORD의 부호에 해당하는 N 전제가 있다. 새 원본 비교 입력 변환기가 이를 빠뜨린 사례는 계약의 입력 조건으로 수정하며 C++ 결과를 보고 기대값을 주입하지 않는다.
- F3 자연 seed 재구성 시 현재 라우팅 범위에 따라 120프레임 관측을 400프레임으로 자동 확장하면 고정된 예전 관측과 범위가 달라진다. 기록된 프레임 지평을 명시하고 모든 원본 상태·노드 비교를 유지한다.
- F2 예전 22/136 seed 표현은 16개 중복을 포함한다. 142개 중 완주 6개였던 단위 결과를 F4 통합 결과와 구분했다.

추가 리뷰에서 과거 미지원 기대값 정렬이 회귀를 숨길 수 있는 조건도 수정했다. scene-core/motion-walk/scene-update/script-placement의 API-only probe는 성공 또는 오류를 모두 허용하지 않고 고정 입력별 정확한 결과를 요구한다. runtime 오류를 보고 자동으로 예외 목록에 편입하는 분기를 제거했다. input의 실행 성공에는 최종 PC와 status 검사를 추가했고, motion-walk의 19938 네 입력은 선언 stop 성공만 허용한다. stage-catalog의 superseded guard는 최종 PC/status/오류와 앞선 원본 trace 비교를 모두 수행한다. API-only controls를 native 실행 동등성으로 세지 않는다. stage-area의 세 이웃 주소(49a84/49a86/49a8c)도 F3b 경계로 명시했고, 원본 3e0061d0의 MOVE.W/BSR.S 첫 블록을 모든 public 출력과 대조했다.

이동 로직 검증의 과거 입력 `scene_frame_execution/native_0221.bin`이 새 작업트리에 없어 시작 단계에서 중단된 실행은 비교 실패로 세지 않는다. 역사적 `scene_frame_execution` 자료를 원래 작업트리에서 별도로 복사하고 모든 바이트 해시를 확인했다. 추가 disassembly 입력은 두 관측 manifest의 동일 SHA256 `f8dc5c70f2e60db0357246bec0ff02651bdec7d3fff07c3dc47117f98971edd7`에 맞춰 복사했다. 원본 자료는 수정하지 않았다.

추가 독립 리뷰에서 stage-catalog의 superseded guard가 일반 오류 처리보다 뒤에 있어, 과거 미지원 오류가 다시 발생해도 통과할 수 있음을 발견했다. 해당 원본 마지막 단계의 성공 검사를 먼저 수행하도록 바꾸고 정확한 PC·status·빈 오류와 원본 앞 구간 비교를 유지한다. input의 U06 주소 49be0/e73f8도 계약에 따른 명시적 성공 control로 분리했다. 전체 negative 531건을 별도로 재검증했으며 전체 원본 회귀는 다시 실행한다.

긴 원본 회귀 종료 후 오래된 API 오류 기대값 때문에 재실행하는 일을 줄이기 위해 별도 출력 경로에서 기존 negative 함수를 전수 사전 실행했다. screen 11, transition 12, stage-entry 2,730(+carry 12), scene-update 641(+추가 제어 17), stage-catalog 253(+carry 8), stage-area 719(+carry 10), script-placement 359(+cleanup 내부 20·추가 제어 6)이 통과했다. frame-helper의 4706c는 U09의 등록 경로를 실행한 뒤 정확한 WORD/LONG 정렬 오류를 반환하도록 기대값을 정렬했고 전체 negative 162건·stop 제어 5건·기존 추가 제어 2건이 통과했다. 모든 거부 사례의 전체 public 상태 복구 검사는 유지한다. 이는 API-only 사전 검증이며 최종 native 회귀 완료로 세지 않는다.

## 실행 사고

작업자가 자신이 시작한 오래된 통합 검증을 정리하면서 작업 경로를 확인하지 않은 이름 필터를 사용하여, 원래 checkout에서 실행 중이던 검증 프로세스 PID 30520도 종료했다. 사용자에게 즉시 알렸다. 원래 소스나 ROM은 변경하지 않았지만 해당 실행은 중단되었다. 이후 종료 작업은 자신이 생성한 정확한 PID와 작업 디렉터리를 함께 확인하도록 제한했다. 통합 버전 카드 메뉴 검증 결과는 별도 실행으로 확인한다.

## 확정된 비카드 회귀 기대값 정렬

다음 9개 검증기는 수정된 소스로 공식 전체 명령 `.venv/bin/python tools/verify_animation_machine_<name>.py`를 실행해 종료 0 및 현재 입력 해시 일치를 확인했다. native 앞 구간과 전체 상태 복구 검사는 유지한다. 보고서는 `artifacts/animation_machine_<name>_execution/verification.json`이다.

| 검증기 | 최종 보고서 SHA256 |
|---|---|
| `area_clear` | `2133af5e08f24169d797bb253b20dc2ede762b5476e08e3845be8b2965e34179` |
| `frame_helpers` | `9e634745528c6e0842a277ff35b6722c6dd09fb3daf884ec79b090d3483d4d8d` |
| `input` | `f4dd24f45c67d0a400cca6c96cd1b291fae62466a153be7b43913df4b170c964` |
| `motion_walk` | `48e338e33d212c3404b41eff82e0df89cc3e05fa02ec29814474e1093837739b` |
| `readiness` | `5a673c6ad68481515749daed6a3526db7db86937a10258ff24aef91cf0bbc934` |
| `scene_core` | `e91a1a3e75ff55760f919ae6d275287fdbb8ad0645d5339f85cfe1e4728b52e9` |
| `scene_update` | `a4370374673f1a6918c6b6d25fa4d1b170ca109e230d34cec1fc82e138202ec0` |
| `script_placement` | `ec691e787d2b4e973793c716eefb5d484a379e7e43d8a8d37f69f5513d5e212a` |
| `stage_area` | `32a3c624fdef6f9d2b38ae273f20c188fb11715d8f67227d6f10e1a31cf6636e` |

스테이지 카탈로그의 성공 필수 분기 수정도 공식 전체 실행으로 통과했다. 534개 사례, split 24,567, 원본 앞 구간 30,444프레임, native 파일 663개·blob 6,255개 해시 검사를 수행했다. 최종 보고서 SHA256은 `4d11fe782cb5f5a2d53241b4c867e4f4ca0e792876da5af6847dcd7f6fe39071`이며 입력 103개가 현재 소스와 일치한다. 과거 미지원 오류·잘못된 PC·대기 status·비어 있지 않은 오류를 주입한 네 회귀 사례는 성공 필수 분기에서 모두 거부됐다.

비카드 전체 회귀 완료 후 F4 인수 감사 두 개를 별도 출력 경로에서 현재 파일로 다시 수행해 종료 0을 확인했다. 두 receipt는 최초 인수 기록과 바이트 단위로 동일했다(객체 matrix `080b0e8844b82c487314aae7b3a5c37ece1faa13afa02d1eb8504c1766692239`, RNG `f11a95713c9407dfdd7e4412ef8050da51cfafd425dce559bb00386fb56688c0`). 152개 헤더의 이전·현재 해시 일치 및 `9d5aa11` 이후 헤더 무변경도 재확인했다.

마지막 카드 열기 API 전수 사전 검사에서 e84d6 직접 진입의 오래된 미지원 오류 기대값과 `guard-d1-ge-10-without-stop`의 오래된 실패 기대값을 발견했다. 고정 push 입력의 직접 진입은 2abe/2ac0 원본 `20564e90`(MOVE.L (A6),A0; JSR (A0)) 지점에서 A6=103000, LONG(A6)=92bdcb15인 홀수 콜백에 도달한다. 해당 API 오류를 정확히 고정하고 전체 상태 복구를 유지했다. 새 guard와 기존 e5-0/e5-3 두 guard는 모두 PC=2ac2/status=0/빈 오류 성공만 허용한다. 과거 두 guard의 임의 성공·실패 수용을 제거했으며 원본 앞 구간 비교는 유지한다. 고정 소스의 API tail(negative 317, 유지된 오류 guard 6, 명시적 성공 guard 3, boundary control 10, known-carry 30, zero-step 606, boundary-zero 12)과 잘못된 결과 주입 12개 거부 검사가 통과했다. 이전 공식 실행은 자신이 생성한 PID/cwd/명령을 확인해 종료하고 진단 자료로 보존했으며, 수정된 전체 원본 비교를 새로 실행한다. 이 마지막 실행이 끝나기 전에는 전체 통합 완료로 세지 않는다.

## 카드의 기존 superseded guard 추가 인수 검사

input/close/save의 기존 전체 보고서는 superseded guard 5개의 이후 실행을 원본 동등성 또는 negative 수에 포함하지 않는다. 이 분류를 유지하면서 `tools/audit_animation_machine_card_superseded.py`로 정확한 API 결과를 별도 검사했다. input/close 4개는 보고서에 해시가 고정된 입출력 24개를 사용하며, save 1개는 기존 출력이 삭제되어 고정 원본 관측의 마지막 guard 입력과 현재 production harness로 새로 실행했다. RAM·정규화한 PVC·레지스터 입력, binary·현재 source·8개 MS5D 및 manifest 해시를 확인한다.

- input `guard-bd26-without-stop`: PC=c1e6/status=1/`unsupported animation machine PC`, 레지스터·RAM·PVC·bank·ports·external reads 전체 rollback.
- input a662, close a698/a6da, save descriptor 0001: PC=2ac2/status=0/빈 오류의 성공만 허용한다. 원본의 이후 실행 동등성은 주장하지 않는다.
- 해당 원본 앞 구간은 각각 100/8/15/28/10 phase이며 기존 전체 보고서의 비교 결과다. guard 이후 실행을 split/native-equal 또는 negative 수에 더하지 않는지도 검사한다.
- 메인 재검증: `.venv/bin/python tools/audit_animation_machine_card_superseded.py --save-receipt /tmp/ms5-card-save-guard-supplement/receipt.json --output /tmp/ms5-card-guard-main-acceptance.json`, 종료 0, 5개 인수. 새 실행 재현은 `--run-save NEW_EXTERNAL_DIRECTORY`로 가능하다. binary/sources/resources 필수 pin을 각각 삭제한 세 변형은 모두 거부됐다.
- 도구 SHA256 `6af353144c3c42bad98a48426c926ab4d53ad109b1706d207e9e1281013fe8de`; save receipt `2aa5d4577b47c4886df984fe52952512b04b77c7bd01ca60f6df9ade0c157841`; 메인 인수 결과 `aebee4fd711e3b7c89338c42150e6bf8311b8031c8f99240c5add0d753a6dff2`. 추가 도구는 기존 전체 회귀 입력을 변경하지 않는다.

## 미완료 기준

모든 필수 통합 회귀의 최종 보고서, 입력 해시, 실제 실패·경계 분류를 대조한 뒤 이 초안을 완료 기록으로 갱신한다. 직접 플레이, 자연 부팅/IRQ, 전체 오브젝트·스테이지·사운드 동등성은 이번 제한 범위의 완료와 구분한다.
