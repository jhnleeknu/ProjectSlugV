# 두 좌표의 경로 검사와 구간 선택 리뷰

Baseline `4b0eaee`, 브랜치 `codex/scene-motion-pair`. 메인이 원본 제어 흐름·좌표 변환·반환 carry·구간 이동 순서를 해석했고 sol / medium 에이전트에 확정 사양 구현, 독립 검증, 근거 목록화를 분담했다. 검증 중 발견한 플래그 관찰 문제로 독립 실행기 추가 작업도 분담했다.

## 코드 검토

메인이 core 전체 diff, CLI 전체, C++ unit과 inventory 도구를 읽었다. 192c4는 입력 A1을 사용하고 19832는 RAMd3b4를 사용한다. 36종 변환, D6/D7 상위 WORD 보존, EXT.W 후 low BYTE 덮어쓰기, signed 범위 검사와 WORD wrap을 원본과 대조했다. 역방향 Y 변환의 열 명령은 두 번째 좌표에도 D0를 더한다. Raw `d680`을 확인했고 대칭 공식으로 고치지 않았다.

19832의 시간 투영은 처음 두 번만 수행한다. 구간 전환 뒤 D6/D7을 보존하고 192c4 결과 carry로 반복 여부를 결정한다. 전진과 후진에서 RAM cursor 게시 시점이 다르며 되돌림 뒤 원래 구간 경계에 제한한다. 공개 API는 전체 RAM·12레지스터·carry를 성공 때만 게시한다. null은 19832만 지원한다. 임시 반복 한도와 RAM motion 미지원은 명시 오류다.

advance/retreat/projection 공통 부분을 추출했으므로 기존 세 API 회귀를 확인했다. C++에서 부호 있는 오버플로를 사용하지 않으며 LONG 비교는 sign-bit 변환, WORD 판정은 원본 명령에 맞춰 signed 비교 또는 N-only로 구분한다.

## 기존 회귀

전체 make: Python 182 / C++ 115, 경고 0. 로그는 `artifacts/scene_motion_pair_build_test.log`다.

| 기존 실행 경로 | 원본 일치 | 오류 검사 | Verification SHA256 |
| --- | ---: | ---: | --- |
| 19938 | 12,170 | 69 | a3ddcff8567e3e87ef590dfd048f98003d9eb11bddf6bce6a4a648e0334f87de |
| 19802 | 2,664 | 69 | bdf7b10516a79a7d247867090ee14f54f1be9becf55d7883a935be501b5b4dd0 |
| 기존 bounds | 3,606 | 117 | 6b994d12955cc34d8246f41ac8db589400b0a31a9ccbab9d7103917c6a2a9270 |

Bounds verifier의 binary pin은 실제 재빌드 hash `26a6a36905958222df410a61b662d9a224fa134755390bc1a9f54dfdafbbcd3d`로 갱신했다. 이전 근거를 새 binary 검증인 것처럼 재사용하지 않고 모든 조건을 재비교했다.

## 플래그 관찰 문제

Unicorn 2.1.4 M68000에서 외부 SR.C 조회가 실제 연속 BCS 결과와 다르며, **실행 중 SR을 읽는 hook 자체가 이후 분기를 바꾸는 사례**를 재현했다. 단순 명령 뒤 BCS만 검사한 30조건으로는 이 차이를 충분히 드러내지 못했다. 메인은 별도 RAM의 AND/BNE, 호출/RTS, MOVEM 복원 세 형태에 대해 no-hook / PC-only / SR-read hook, AND 결과 0/비영, 두 실행기를 조합한 36조건을 직접 작성했다.

세 가지 코드 형태 모두 Unicorn SR-read hook의 비영 AND 조건에서만 잘못된 BCS를 관찰했다. No-hook과 PC-only는 일치하며 Musashi는 세 관찰 방식 모두 일치한다. 따라서 MOVEM만의 결함으로 단정하지 않는다. 실제 원본 case545에서도 이전 SR hook이 있는 Unicorn 기록은 구간 선택이 달랐다. 최종 secondary 관찰에서 실행 중 SR 읽기를 제거하고 반환 후 raw SR만 진단값으로 보존한다. 원본 명령·플래그를 패치하거나 정답 값으로 보정하지 않는다.

반환 carry의 독립 근거로 공식 Musashi revision `313ebf1bd9f4d0d93341eb5ce21fd8a119e9dbdd`를 고정했다. 메인은 builder·C bridge·Python wrapper 전체, 메모리 범위·register 대응·instruction slice·callback 예외 전파를 리뷰했다. CCR 7조건, hook 유무 전체 2 MiB/18레지스터 일치, write 관측, 정확한 budget, unmapped fault와 callback 실패 거절 검사를 직접 재실행했다.

Oracle library SHA256 `e8bce7cc0e7b266cb474841bd733b728188cc46f028ad2053d36258eeece98c9`, metadata `bedf4563145ab662e3be6172e2ca690fada22d401c7c1be3765d0a894c9cf8e3`. 공식 archive와 191 vendor 파일, 생성 코드, 컴파일 옵션·출력·라이선스 근거는 ignored artifact에 남기며 source·library 현재 hash를 검증에 결합한다. Prefetch/사이클 정확도와 MMIO 모델은 이번 oracle 범위 밖이다. 별도 oracle 빌드에는 macOS linker의 common-section alignment 하향 경고 1개가 있으며 build metadata에 보존했다. 앞의 경고 0은 게임 프로젝트 make 결과다.

메인 diagnostic report SHA256 `65178c381f8ebfcc116cd854930c039b18b663bbdb2c4557ef8148d6b3f5e1a7`. 이 결과를 기존 모든 분석이 잘못됐다는 주장으로 확대하지 않는다. 이후 SR을 실행 중 읽는 observer를 사용할 때에는 이러한 간섭을 검사해야 한다.

## 신규 검증

4,232조건에서 전체 64 KiB RAM·12레지스터와 Musashi의 반환 C가 C++와 일치했다. Canonical 2,376 / null 10 / 합성 주소 정규화 1,846을 구분한다. 후자는 native RAM106000과 C++ MS5D60000을 쓰고 출력 A1/RAMd3b4만 정규화한다. Canonical 37리소스/108record, 합성 36type과 signed 폭·확장 WORD wrap을 포함한다.

N-only 비교에서 V=1인 LONG 117 / 전진 WORD 4 / 후진 WORD 4 관찰을 실제 다음 PC와 대조했다. 전진 검사 C0/C1은 200/224회, 후진은 115/381회다. 반복을 두 번 이상 실행한 조건은 578개이며 세 번 이상 반복도 별도로 확인했다. 중간 구간에서 시간 투영을 반복하지 않는다는 호출 횟수 근거도 검사했다.

8개의 CLI 승계 sequence는 24호출이며 16호출이 직전 출력을 소비한다. XY는 host가 명시적으로 갱신한다. 오류 107조건에서 입력/기존 출력이 유지된다. 현재 불변 리소스 최대 길이와 단조 cursor로는 방어적 반복 cap까지 도달하지 않아 cap 소진을 검증했다고 주장하지 않는다.

실행 중 SR 조회를 제거한 Unicorn의 모든 RAM·12레지스터도 Musashi와 일치했다. 반환 후 SR.C만 1,326조건에서 다르다. 메인이 두 실행기의 모든 저장 RAM hash·입력·공개 register·RTS/A7를 직접 재대조했다. 최종 observer 소스로 primary 기록을 다시 생성했고 C++ 전체 비교를 다시 통과했다. 메인이 최종 4,232행과 두 native RAM 파일, 모든 현재 원본·리소스·oracle·binary·probe hash를 재확인했다.

최종 verification SHA256 `5cb8f44eff5d7552bba9eed5e146bb3c6b984d1180e1622df5ef4f13c3917853`, primary native `e9aaaf121cdddf157aa8d756d29ee2659a18611ee62f5b6fd426ea17d4ae9408`, secondary `3f0aca47fa0b98223679471812168b7f526ecefda0c6663a58aaff741213d77f`, C++ CLI `b7ecd5ffc7b33b94e537ab1f0293656150dddc65da4e2d9604c6827bb0cce7e4`다. 마지막 file-alias 오류 검사의 기존 출력 보존 assertion을 추가한 뒤 오류 107조건을 별도 재확인했다. Python 구문 검사와 git diff 검사는 통과했다.

메인은 이 단위의 통합을 수용했다. 원격이 없어 로컬 branch/commit/review로 남긴다. 다음 19a40/19ac8/19b96의 분석 계약은 `docs/analysis/scene-camera-progress.md`에 저장했다. 전체 1a73c frame, 직접 플레이 화면과 전체 게임 복원은 미완료이며 goal은 active다.
