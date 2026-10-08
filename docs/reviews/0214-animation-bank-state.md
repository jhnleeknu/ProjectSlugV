# 0214 — Animation 실행의 실제 bank 상태 보존

Baseline `35aa5d5`, branch `codex/animation-banked-lookup`. 메인 리뷰·수정·재검증을 완료했다. 새 native bank-chain 및 해당 C++ 대조도 통과했다. opcode40·전체 Goal 완료 기록이 아니다.

## 문제와 변경

RAM bank shadow와 복귀용 saved_bank만으로는 직접 sound30 대기 전 실제 선택된 ROM bank를 복원할 수 없다. `AnimationExecutionState.current_bank_base`를 추가하고 실제 PVC 쌍 완료 시 갱신한다. phase1..4의 포트 쓰기 없는 hold는 이 값을 보존하며, candidate transaction 실패는 새 필드도 보존한다. 두 기존 CLI와 일곱 Python 검증기의 상태 형식을 함께 변경했다. 새 바이너리 리소스 규격을 만들거나 기존 ROM을 수정하지 않았다.

## 발견 사항과 수정

- **P1, 초기 계약의 최종 bank 식 오류, 수정 완료.** 첫 ff9=value 쓰기가 get_bank_base를 호출하며 저장 ff9의 bit15를 지운다. 다음 ff8=0 쓰기의 bank 계산은 이미 mask된 ff9를 사용한다. 따라서 쌍 완료 값은 `100000+((value&7fff)<<8)`이다. 초기 `&ffff` 식을 계약·구현 지시·이전 설계 문서에서 수정했다. raw port WORD는 그대로 유지한다. 메인이 pinned neogeo.cpp1231..1240/prot_pvc.cpp71..76을 읽었고 독립 Sol이 4개 incoming ff8 × 전체65536 WORD값을 순차 모델과 대조했다.
- CLI 파서·파일 보호 함수는 baseline과 동일하며 공통 argv22에 bank를 넣어 이후 인덱스를 함께 이동했다. implicit old-schema fallback은 없다. inactive continuation metadata처럼 bank를 0으로 제한하지 않는다.
- Python 기대 bank는 실제 원본 ports와 독립 native_bank에서 도출한다. 실제 C++ 출력으로 다음 실행을 재개하는 경로와 분리했다. 원본 RAM shadow나 C++ bank를 기대값으로 복사하지 않는다.
- 메인과 별도 Sol은 실제 core/unit, 일곱 verifier 및 두 CLI diff를 검토했다. 추가 확정 결함은 발견하지 않았다.

## 현재 확인한 검증

- `make all test` exit0, C++ test 실행145개, 경고0. Python unittest discover243개 통과. core의 별도 normal/UBSan 실행도 통과했다.
- 새 unit은 임의 uint32 입력의 fresh overwrite, phase1..4 resource-free hold, shadow poison, raw8000/f000 쌍, direct high→low/hold/release, direct→direct wait 및 candidate bank 변경 후 실패 rollback을 확인한다.
- 별도 두 CLI 빌드와 표적33호출 통과: fresh6, phase4 resource-free hold3, parser/파일 보호 negative24. 기존 native hold snapshot에 별도 입력 bank를 주입한 CLI 검사이며, 자연 원본 bank-chain 증거는 아니다.
- 기존 일곱 verifier 모두 새 schema로 exit0. 메인이 보고서7개와 입력·산출물의 고유24461개 참조 해시를 다시 확인했다. 원본 native 보고서는 변경하지 않았다. 검증 결과의 bank는 실제 ports와 pinned PVC 모델에서 도출한 값이다.

| 검증기 | 현재 report SHA256 |
|---|---|
| execution | `655efaec402aef10e4bd18a2e4bd284c5ad5d99485c1ca130b3db9ef594bcfb1` |
| control | `28db79eafee07265dfabc0fa15fef59691315471b087314a75f97a6381f0e998` |
| sound | `2891c53ab15c48d38bb2fa07db3be2b5b41fdfdd1ccfc34e320bcfc6f29ff351` |
| indexed | `54e03d4da1e45f09c8e753e227ea6bce2da039515896a1891b53b048f73ae1d3` |
| field | `b507030e6c2d6bafdc9a951035c0a1675655120f2e1255672307fa112d8d4e09` |
| direct sound | `581c44fefa9c2f54a789f64d028e203926b5024c42645b64ddd23a46b093d381` |
| WORD callback | `ae24ef16f288b40831a98442140e5ed150f40880a078a131821720634f6627b5` |

## 새 원본 bank-chain 통합 판정

- Opus5.5/high가 독립 원본 관측기를 작성했다. 메인은 원본 의미와 실제 source를 검토하고 제한 설명 두 문장을 정정했다. 원본 window의 mapped port page와 callback guard의 실제 중단 위치를 정확히 표시했으며 실행 로직 변경은 없었다. 새 관측92조건/276단계/560PVC와 guard3개를 메인이 다시 실행했다.
- 별도 Sol은92조건/276단계/1104payload를 메모리에서 재실행하고1116고유참조 hash를 확인했다. 실제560쓰기에 별도address_map 상태전이를 적용해 쌍 중간 값과 최종 값, shadow poison을 대조했다.
- 새 verifier는 원본276단계를 다시 실행하고 실제CLI276단계/184이전출력재개/560PVC/0외부읽기, 오류5조건을 통과했다. 메인은 verifier 전체 source와 고유2256참조 hash를 확인했다. 별도 Sol의 정적 verifier 리뷰도 확정 결함이 없었다. 간접 import provenance 누락 후보를 보강하고 재실행했다.
- 최종 nativeSHA `28060b3d2ea2edcd9048929b34855e8698c13504314c81421bde9764aa7fe777`; C++ reportSHA `efc034849e741abbaedfc92478a0cafc85dad370f3b632fce1da2c24b0d6ad67`. 실행 명령·source SHA·정확한 범위는 animation-bank-state-execution.md에 기록했다.
- **이 변경 단위 수용.** 모델은 JSON modelUsage에서claude-opus-5-5를 확인했고 CLI effort high를 명시했다. 반환 JSON에는 적용effort 독립 확인 필드가 없었다. Sol3개는 medium으로 구현·검증·독립 리뷰를 분담했고 최대동시작업자는외부포함4개였다.

## 후속 범위

 현재 의미는 animation이 발행하는 완전한 WORD PVC 쌍에 한정되며 일반 PVC 장치 전체·색 변환·임의 단일 write를 구현하지 않는다. 실제 banked 데이터 소비와 opcode40은 다음 연결 대상이다. 후속 reader에는 PVC overlay뿐 아니라 RAM mirror 및 LONG의 영역 경계 접근도 필요하다. 자연 scheduler/IRQ, 직접 플레이, 전체 스테이지/적/보스, 미사용 데이터 전체 의미와 Goal은 계속 미완료다.
