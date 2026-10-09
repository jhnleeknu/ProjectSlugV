# 맵 뒤 페이드·타이머·프레임 재진입·BIOS 카드 경계 리뷰

대상 baseline `55606fa`, 브랜치 `codex/animation-machine-fade-card`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 직전 맵 전송 통합(리뷰0231)을 진척으로 승계하며 완료된 작업을 반복하지 않았다. 원격이 없으므로 로컬 커밋이며 PR이 아니다.

## 세션 역할과 실제 작업자

- 메인: Claude Opus 5.5 (Claude Code). 원본 의미 분석·계약 작성·리뷰·통합을 맡았다.
- Codex Astra/Sol은 이 Claude 세션에서 호출할 수 없어 위임하지 않았다(codex-cli 0.144.6이 설치되어 있으나 Sol은 Codex 내부 서브에이전트 역할이다). AGENTS.md의 재배정 규칙에 따라 Sol 몫을 Claude 작업자로 대체했다. 동시 작업자는 최대 3개로 상한 5 이내다.
- Claude Opus 5.5 / high: C++ core·unit(구현), 이후 별도 인스턴스로 독립 core/native 읽기 전용 리뷰.
- Claude Sonnet 5.5 / high: native Unicorn 관측 도구.
- Claude Sonnet 5.5 / medium: C++ 검증기, 기존 검증기 경계 이동, 실행 문서.
- 작업자는 Claude Code 내부 Agent 도구로 실행했으며 모델·effort는 호출 시 명시했다. 실제 적용 effort는 harness가 보고하지 않아 요청값으로만 기록한다.

## 원본 의미와 범위

계약 `docs/analysis/animation-machine-fade-card-contract.md`(SHA256 `b3d0f86df3b54da1b390c32800fee6127beefd2dc5aff8e71441f730a6811a5c`). 메인이 canonical ROM에서 `4804e..480bc`, `c364..c3c0`, `28ae..2918`, `2a00..2a0a`, `2aac..2ac8` 원본 바이트를 직접 디코드했다. 첫 페이드(8c16, D0-2=0, D3.W=40)→7a=80 타이머→두 번째 페이드(e1, D3.W=20)→7a=20 타이머→caf0→c364→BIOS `c00468` 경계, BIOS 뒤 `10fdc6` 응답에 따른 62(A6) 설정·`28ae` 자식(`c250`) 할당, `480ac` 대기, `2a00` 자기 제거와 `104ca4` A7 복원, 디스패처 `2ab8..2ac6` 재진입을 실제 RAM/A7 실행기에 연결했다.

`c00468`은 실행하지 않는다. BIOS 재개는 선언된 host 변경(PC=`c37c`, A7+=4, BYTE `10fdc6`, carry Unknown)이며 BIOS 효과로 주장하지 않는다. 프레임 재진입은 PC=`2ab8`만 바꾸는 선언 fixture로 자연 scheduler가 아니다.

## 메인 리뷰 발견과 수정

1. Core 리뷰: 모든 case를 원본 바이트와 대조했다. 28de 열한 개 접근 순서, 음수 A5 displacement(cc9c/cca0/cca4/8e98), unsigned BCC, CMPA.W 전체32bit, 2908 Set/290e Clear, carry 보존 목록(LEA/MOVEA/JSR/JMP/BSR/BRA/RTS만)을 확인했다. 결함 없음.
2. 독립 리뷰가 native 보고서의 계약 입력 hash가 계약 문구 수정 전 값임을 발견했다. 메인이 계약을 확정(타이머 횟수 표현, BIOS 재개 carry Unknown)한 뒤 관측을 재실행시켜 해소했다.
3. 독립 리뷰의 관측 보강 사항(c00468 stop을 c376 JSR 직후로 한정, fresh 프레임의 모든 단계 비교, 홀수 write guard가 기록 없는 RAM 변경을 남기지 않게 복원, 함수명)을 반영했다. 강화된 비교가 video/watchdog write의 `before` 바이트가 장치 페이지 잔여값임을 드러내 0으로 정규화했다(주소·값·순서는 불변).
4. 검증기의 자기 재귀 callback 음성 검사가 여러 오류를 허용하던 것을 메인이 원인 확인 후 정확한 오류로 고정했다. 재귀 JSR push가 mirror RAM을 내려가 live push가 (A6)를 return `2ac2`로 덮고 이후 unsupported PC로 나간다(stop을 `2ac2`로 둔 별도 C++ 재현은 정상 정지).
5. palette_bind·map_transfer whole fixture의 첫 실패가 write device로 바뀐 이유를 메인이 확인했다: 레거시 `48042` whole fixture의 A6=0이므로 `4805e`의 7a(A6) WORD가 ROM 주소 쓰기가 된다. 추정이 아닌 사실로 기록한다.

## 검증 결과

- 메인 `make -j4 all test` exit0: Python257개/C++163개 실행, 경고0. 신규 unit 319 API 호출 통과, 별도 UBSan 빌드 통과(작업자 실행, 메인이 로그 보고 확인).
- Native: 정상25조건 split319/continuous196, guard7. 모든 조건 fresh 두 번 split·continuous 재현. 정상 ports video13985/watchdog2308/PVC24, bank read1296/fixed206, external read0. ROM SHA·mtime 불변. 관측 SHA `f53387b7122286eca94c55371a34a09f900489eb9ab2766f9c98e086da7f57fc`, 도구 SHA `01d932ba16a1ab16679b888d5b02b53b5ea071b194aaa1fcbd345f3a0672baf5`.
- C++ 비교: 32조건 split327/continuous196, 재개299, ports18389, 음성22, zero-step117, source 분류 carry Unknown312/Clear2/Set13. 보고서 SHA `ad6e83ea686fe864319ff6c288710a069f78734765ce61e2781a4666740058c5`, 검증기 SHA `bc438cd1cffe81d5d7d04db544146afa2a751773fcab35da50d16055ccf0e065`.
- 독립 리뷰가 별도 harness로 native 16단계를 C++에 재생해 16R/PC/full RAM/ordered ports 일치를 확인했다.
- Core SHA `73a0ac85fbba29fcbb2e48890b0cfded80300dc9f71ac586e97c70523ee42550`, unit SHA `466719ae15cbe334421507994732c656269795a3893e09fbc82d75d0f3072c7d`.

## 기존 회귀

기존 13개 공식 검증이 모두 통과했다. 경계 이동 대상 5개와 기본 검증은 작업자가, 나머지 7개는 메인이 재실행했다.

| 검증 | 조건/단계/재개/음성 | 보고서 SHA256 |
| --- | --- | --- |
| screen | 31/128/97/14 | `9c799bf3caf55d639ecbb202e646e20f2b56497ee488e31c81cdfd276b9358f0` |
| cleanup | 69/121/52/17 | `2bb6f6162e26d3ac8f12c8e4c64b8f7be7062c1bb0485dd6bea9fd78bfb333df` |
| scene | 79/225/146/20 | `67640b29d9c6edbf516cbeff42d2111c2a1523eedf0529799a31011d49b50a5f` |
| palette_bind | 58/140/82/21 | `aa3d935f7ebe5957be9178e396be0bc5125c0e4a4bff61b8f5e02a064a7e2f7d` |
| map_transfer | 50/131/81/18 | `c296d4deab83477a752085622ffcfb522301cad4133d1683da8bcb72483337d2` |
| animation_machine | 8 match/2 chain/85 확장/121단계/9음성 | `537aa25f1c725bec1bb930b22ecc3a8019d2083b66100677d718e48c86e7f7c6` |
| callers | 59/91/32/6 | `f5b2a69e6159cdf5bbf949953b5605aaa6fca7421b3f9612a0f93cee4fc52a17` |
| carry | 60/160/100/10 | `f804cd8059f43a6ca37ae4c59bb55e0daf011a1a2ffc02b137c98f2b31849e5d` |
| activation | 52/74/22/9 | `0cd99df55c7b18d35d8df77338f359d9379105082e82c3efb10563baf873d9c3` |
| readiness | 68/154/86/14 | `7a8e6c00809823c792d3ec1cb9381d7e42a4e85cfae55c86c71724d14726e486` |
| hud | 124/277/153/15 | `1483c1f2eb53551fa1de248e62bf56d6ee180b5ead413a650ff83f969cae967e` |
| transition | 107/224/117/15 | `9263717edfb08463b2b490de0a922d25fe4387b73803c6ca383170d819e67c96` |
| exit | 90/252/162/17 | `9948cd8511d559771aab7ada8ba9da1b69382910cab3e716735331acacb820c9` |

기존 검증의 `4804e` unsupported 경계는 `c00468`으로, 기존 screen unit의 경계는 `480bc`로 옮겼다. 역사적 정상 stop은 유지했다. 기존 보고서별 고유 참조 합집합의 전수 SHA 재대조는 이번에 수행하지 않았고, 각 검증기의 자체 입력·산출물 hash 재검사 통과로 대신했다.

## 남은 제약

BIOS `c00468` 내부와 카드 응답 의미, 자식 `c250`(페이드→`de424`→`a29c/a2b8/a370` 메뉴→부모62=ff→`2a00`)과 `c188` 본문, `480bc` 프레임 helper 묶음, 다른 객체 callback, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 스테이지/적/보스·미사용 자료 전체 의미는 미완료다. 전체 Goal 완료를 선언하지 않는다.
