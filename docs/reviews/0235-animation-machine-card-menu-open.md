# 카드 메뉴 첫 프레임들(`a370` 열림 → `a5ea` 첫 전체 그리기·callback) 리뷰

대상 baseline `34814b7`, 브랜치 `codex/animation-machine-card-menu-open`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 직전 메뉴 push 통합(리뷰0234)을 진척으로 승계했다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성·보정, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort를 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: C++ core, routing, unit 테스트. 별도 git worktree에서 작업했고, 메인이 push 커밋 뒤 diff를 이전했다.
  - Claude Sonnet 5.5 / high: native Unicorn 관측.
  - Claude Sonnet 5.5 / medium: C++ 검증기, 이전 검증기 경계 이동, 기존 회귀, 실행 문서.
- 검증기 작업자는 API 사용량 제한으로 한 번 중단됐다. 같은 작업자 transcript에서 재개했으며, 완료된 회귀는 반복하지 않았다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-card-menu-open-contract.md`(SHA256 `1eb6c80ebcbef6a2f8c6488c23342ee4a85dae1c0acbf9037ad3ccb280549c4b`). 범위는 다음과 같다.

1. 열림 프레임: `a370` 프레임 루프, `a5d2`/`a348` 높이 증가, `9b58` 상자.
2. `a018` 가림 검사: known C를 반환하며, 호출자 BCS 15곳이 이를 소비한다.
3. `a5ea` 첫 전체 그리기: `9b26` 커서 탐색, `9e1a`/`9d3a`/`9cd4`/`9f7c`/`3918`, renderer `a008`/`e84c8`→`3650`.
4. 사건 전달과 callback: `9b3e` 사건 전달, callback `c1c4`/`bf94`, `a73e` 효과음, `a216` 커서 이동.
5. 프레임 종료: `c2c0`/`c2c6`을 거쳐 `2ac2`.

## 메인 리뷰와 계약 보정

1. 작업자 보고로 계약 공백 3건을 확인해 보정했다(원본 확인 후 SHA 갱신, 실행 중인 관측 작업자에게 재pin 전달).
   - `c2c0`/`c2c6`을 범위에 넣고 `c2c8`을 경계로 두었다.
   - `9f7c` 팔레트 조건은 "또는"이 아니라 "이고"다.
   - block 시작은 202개다.
2. Core 400줄을 원본과 대조했다. 결함은 없었다. 확인한 항목은 다음과 같다.
   - `a018` MOVEM 순서, BHI/BCC/BCS unsigned 방향, ASR.B 부호.
   - `a350`의 WORD RMW(바이트 5 포함), `a216` BYTE push(A7-2, 짝수 주소).
   - `a06c`/`a076` known C가 RTS를 넘어 호출자 BCS로 전달되는 것.
   - carry 보존 68 block.
3. 이후 단위(입력)에서 볼 사실: f bit0 재그리기는 `9e1a`가 `3918`의 JSR (A1)를 남은 A1로 실행한다. 원본 동작이며 C++ 결함이 아니다(미확인 기록).
4. Push 단위 실행부의 오래된 주석(`9b58`/`a370` 실행부 없음)을 메인이 고쳤다. 주석만 바꿨다.

## 검증 결과

- **빌드·테스트:** 메인 `make -j4 all test` exit 0, Python 257개, 경고 0. open unit은 2530 API 호출로 통과했다(UBSan은 작업자 실행).
- **Native:**
  - 정상 79조건, guard 9. split 14493, control 275. 모두 두 번 재현했고 split·continuous가 동등했다.
  - 열림 높이 `0088`→`0208`→`0388`→`0508`→`0600`(clamp는 같은 프레임 안).
  - 프레임별 port는 0/34/51/85/189이며, `a5ea` 프레임은 LONG 158 + WORD 31이다.
  - 관측 SHA `154b4ed588a1bf7c9615bc7c6c3710492e4c0a711aca710b20f6bd21a7390ab4`, 도구 SHA `17dea0a98c5a8ca3aa34ccf7524d132872877774ffcfd39970037fa0f7d04316`.
- **C++ 비교:**
  - 88조건, split 14969, continuous 282, 재개 14881, ports 34605, external read 0.
  - 음성 365(native guard 9 + API 356), zero-step 606.
  - known-carry 탐침 26220건.
  - 보고서 SHA `ee5010f1ac280ef533f700a2d426fd6c888a243f9076f997b3daf071b557f3c3`, 검증기 SHA `ecf5dea3cbb751cf6046b64ef43288126285a82a2cf311548c071b1683847973`.
  - 메인은 검증기 재실행(약 2.5시간) 대신 보고서·입력 파일 SHA 재계산, `make` 재실행, diff 검토로 확인했다.
- **SHA:** core `2ffbb626751fb40aca74486c5b8f1cd9e734af6ffa41d64c7f59f2459eade598`, unit `23c2bfab0e48097c25405941899c4e05ce5059a3592d823acd9d439e8efeb378`.

## 기존 회귀

push 검증기와 card_child 검증기의 경계를 옮겼다(`a406`/`9e94`/`c2c8`). 이제 정상 경로가 된 native guard는 superseded로 기록하고 음성으로 세지 않았다. 보고서 SHA는 card_menu `89640e8b3031450e9e34464ad5af6cae36c9afc5fdf86de29758581b3896d2f4`, card_child `eb734d58c0385791a2027fd9470b3f5eafb5b226e2c093b353841520987b0c94`이다.

나머지 14개 검증은 작업자가 재실행했고 모두 exit 0이었다. 보고서 SHA는 다음과 같다.

| 검증 | 보고서 SHA256 |
| --- | --- |
| animation_machine | `eaa7a124322e3bb048c952abffa1eceb964f16b2ca33578efe63670451b683dd` |
| fade_card | `0b5f13665dce4f609402be9f363f6b3a24230e35fc89f795cb34a2d2dd17ea99` |
| screen | `1e9a5376d90b6904730be088b5879178e4a552c5989c47d4468a3162403ee901` |
| cleanup | `951826b51781c410cf211da233744575d0995ae55e8563abe5f5907eae0dea8d` |
| scene | `0e67e83295e3d3002ab3a87b46008c640f18f094d74fe60b5a1cde301a91872b` |
| palette_bind | `4ce7ad448d193c9b28db8d9c16e3cf67c9fe999f57e7d0f994a30bfde5b69524` |
| map_transfer | `d6b18b11d9b84d2bd33a46f35c7ffaa6fba51ce4c9733227dac521ab32908b18` |
| callers | `ab3175ab87175d03d5e31bfdeef9a0cbcdd9efd0c50bc9efb5e2392ac34272b7` |
| carry | `1ec919673e786b593d0917d39ce504dd58b7d13f1469993bfbc73decd3416a21` |
| activation | `8dddffee3ccd26ab46ed2b6fe587bd0f9d8873ee349ee444151309fb5be22d1b` |
| readiness | `666295f0ace138a6a7a2a03a2d23c050ddbbc7eed967f919ae9530f7be8c590d` |
| hud | `5200a476a9e2c5c6bb35aa7477810c99bae78580303a600fa92911f8b84c64ef` |
| transition | `855b612890b592e2a00043b0adc9a21bafd34ba86ad7b97a16ade0427fed91d4` |
| exit | `1662e962d7d3f8c41b3250889e023a635ec8b8011aa155e3a4938992f3ad762c` |

## 남은 제약

다음은 아직 완료되지 않았다. 전체 Goal 완료를 선언하지 않는다.

- 자연 경로 미도달 block: block 시작 202개 중 8개는 native 미관측이다. `c1ee..c208`은 `bd26` 뒤, `a3ac`/`a3b4`는 `a2be`/`a6da` 뒤에 있고, `9b78`은 구조적으로 도달하지 않는다. 이들은 zero-step과 carry 분류로만 다룬다.
- 다음 단위: `a406` 입력, 닫기, BIOS 카드 처리.
- 미해석·미구현: video port 화면 의미, TRAP #f.
- 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이.
