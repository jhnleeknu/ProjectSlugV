# 카드 메뉴 push(`a29c`→`a0a0`→`38e8`/`386e`)와 renderer 설정(`c2a8`→`a2b8`) 리뷰

대상 baseline `bfbfe60`, 브랜치 `codex/animation-machine-card-menu-push`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 직전 카드 자식 통합(리뷰0233)을 진척으로 승계했으며 완료된 작업을 반복하지 않았다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 디코드, 계약 작성, 리뷰, 통합을 맡았다.
- Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았다. AGENTS.md 재배정 규칙에 따라 Claude 작업자로 대체했다. 작업자는 내부 Agent 도구로 실행했고 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로 기록한다.
  - Claude Opus 5.5 / high: C++ core, routing, unit 테스트, card_child unit의 경계 이동.
  - Claude Sonnet 5.5 / high: native Unicorn 관측 도구.
  - Claude Sonnet 5.5 / medium: C++ 검증기, card_child 검증기 경계 이동, 기존 회귀 재실행, 실행 문서.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-card-menu-push-contract.md`(SHA256 `0a4d095f741e151f509364118663c6470e527ea7535c1058e8d93161398a81ea`). 메인이 `a29c..a2be`, `a0a0..a1e2`, `386e..3902`, `c2a8..c2c8`, descriptor `c188..c1c4`를 원본에서 디코드했다.

`a29c` 경유에서 -f2는 `107f0e`로 초기화되므로 `a0c4` 뒤 항상 `a104`로 간다. 따라서 상자 그리기 `9b58`/`9e1a`는 이번 경로에 나타나지 않고 경계가 된다. 실행 순서는 다음과 같다.

1. 메뉴 프레임 16바이트를 `107efe`에 push한다.
2. 항목 문자열 폭을 `38e8`/`386e`로 센다. escape `\n \r \c \p \l`와 TRAP 경계 `38c8`/`38e2`가 이 단계에 있다.
3. 폭·높이 BYTE를 갱신하고 -e5=1로 둔 뒤 이전 -ee를 복원한다.
4. `c2a8`에서 renderer `e84c8`을 -ea에 쓰고, `c2b4` (A6)=`c2ba`, `c2ba` JSR `a370`에서 stop한다.

## 메인 리뷰

1. Core(`engine/src/animation_machine_card_menu.cpp`)의 모든 case를 원본 바이트와 대조했다. 결함은 없었다. 확인한 항목은 다음과 같다.
   - `a0a0`에서 이전 A5로 -ee를 push한 뒤 LEA가 온다.
   - MOVEM.L D0-D1/A0 push·pop은 메모리 오름차순 D0, D1, A0이다.
   - CMPA.W 부호확장 전체 32bit 비교, CMP.W (A7) unsigned, MOVE.B 하위 BYTE 교체, ADDQ.B count wrap.
   - `\p`의 D7 bit16-31 보존, `\l`의 D3 32bit clear와 BYTE ADD.
2. Native 최종 상태 `107efe..107f1b`를 메인이 직접 확인했다. `c188`, count 4, 폭 `11`, 높이 6, d/e `03`/`ff`, -ea=`e84c8`, -e5=1, 이전 -ee 복원이 C++ unit 기대값과 같다. 바이트 5(A2)는 push가 쓰지 않는 잔여 RAM이다.
3. 작업자 보고의 "-f2=`107f0e`"는 `a29c`의 일시값이다. 최종값은 `107efe`(`a0c4`가 덮음)이다. 테스트는 최종값을 단언한다.
4. 차이 기록: `3900`(`38fe` block 내부 RTS)의 직접 진입 오류 문자열은 card menu 문자열이 아니라 `unsupported animation machine PC`다. router 범위가 `38fe`에서 끝나기 때문이며, 거부와 rollback은 같다. 검증기가 실제 문자열을 pin했다.
5. Carry 보존 block은 계약 목록 `a0c2 a158 a17e 3878 38a4 c2a8 a2bc c2ba`와 같다. 검증기가 단일 block phase 관측으로 이를 확인했다. ADDA/SUBA는 기존 source 분류와의 일치를 위해 Unknown이다(보수적).
6. card_child 검증기의 기존 native guard 2개는 core가 확장되면서 정상 경로가 되었다. 음성으로 세지 않고 `native_guards_superseded_by_card_menu_core`에 기록했다. 대상은 `guard-stop-c2a8-never-reached`, `guard-callback-a2b8`이다.

## 검증 결과

- **빌드·테스트:** 메인 `make -j4 all test` exit 0, Python 257개, 경고 0. card_menu unit은 495 API 호출, card_child unit은 348 호출로 통과했다. UBSan 별도 빌드도 통과했다(작업자 실행, 로그 보고 확인).
- **Native:**
  - 정상 85조건, guard 10. split 2301, control 111. 모든 조건을 fresh 두 번 재현했고 split·continuous가 동등했다.
  - 계약 block 시작 41개가 모두 도달했다. 독립 Python 모델 대조 78건이 통과했다.
  - ROM SHA·mtime 불변. 관측 SHA `da76f4643efafafdc8929a9cd73a24a1e3a434e49275e5babcadd53e5c45bfbc`, 도구 SHA `adb3e9cb65175ebcb3c76347601755f951c033df673ada43533245b238951322`.
- **C++ 비교:**
  - 95조건, split 2405, continuous 111, 재개 2312, ports 5050, external read 0.
  - 음성 132(native guard 10 + API 122), zero-step 123.
  - 시작 상태는 card_child chain의 실제 C++ 출력이다.
  - 보고서 SHA `9f60e658eda41481720cf26184e4f4bc1468f8c07d9d2c783a11fb7be5aa2f37`, 검증기 SHA `d89134466824cd9a668bb9c196f7c65d7271d1f27710fb671270d74553c36afa`. 메인 재실행에서 같은 SHA가 나왔다.
- **SHA:** core `d552b0ed10a261686d6d11492c0b86b08dcb95d47565acbd6c6fcc43890aa3f6`, unit `f158d245dad7a00c3abaed8936daa8c2777bc77f6028153315f8d08b552d4daa`, card_child unit `b0908176d906fca886aff9632d935a0cebd010d92d0144a7525b81b454823f70`.

## 기존 회귀

card_child 검증기의 경계 이동 후 보고서 SHA는 `ad205196bbae9fffffe7f87f10c05b141895e531557339b5fe0880bcdc82633b`이다(32조건/split 568/음성 16/zero-step 126). 메인이 재실행해 SHA가 일치함을 확인했다.

나머지 14개는 작업자가 재실행했고 모두 통과했다. 보고서 SHA는 작업자 보고 기준이다. 아래 열은 조건/단계/재개/음성이다. `verify_animation_machine`은 match 8, 확장 85, 121단계, 음성 9이며, `fade_card`는 32/327/196/22다.

| 검증 | 조건/단계/재개/음성 |
| --- | --- |
| screen | 31/128/97/14 |
| cleanup | 69/121/52/17 |
| scene | 79/225/146/20 |
| palette_bind | 58/140/82/21 |
| map_transfer | 50/131/81/18 |
| callers | 59/91/32/6 |
| carry | 60/160/100/10 |
| activation | 52/74/22/9 |
| readiness | 68/154/86/14 |
| hud | 124/277/153/15 |
| transition | 107/224/117/15 |
| exit | 90/252/162/17 |

## 남은 제약

다음은 아직 완료되지 않았다. 전체 Goal 완료를 선언하지 않는다.

- banked 영역 descriptor: ROM에 존재하지 않으며 banked 문자열만 다뤘다.
- `a370` 메뉴 프레임과 callback `c1c4`/`bf94`, TRAP #f 처리, `c2c8` 이후.
- 자연 scheduler·IRQ/timing·일반 CCR·직접 플레이.
