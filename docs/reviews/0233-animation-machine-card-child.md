# 카드 자식 callback c250의 페이드·장면 준비·타이머 리뷰

대상 baseline `e25f276`, 브랜치 `codex/animation-machine-card-menu`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 직전 fade/card 통합(리뷰0232)을 진척으로 승계한다. 원격이 없어 PR이 아니다.

## 역할과 작업자

메인은 Claude Opus 5.5(원본 의미·계약·리뷰·통합). Codex Astra/Sol은 이 세션에서 호출할 수 없어 위임하지 않았고 Claude 작업자로 재배정했다: Opus 5.5/high(core·unit), Sonnet 5.5/high(native 관측), Sonnet 5.5/medium(검증기·회귀·실행 문서). 동시 작업자 최대 3개. effort는 요청값이며 harness가 실제 적용값을 보고하지 않는다.

## 원본 의미와 범위

계약 `animation-machine-card-child-contract.md`(SHA256 `1e0e0bf005af423e8a768c01ccc152264a2c3cfe5faae515d3c877108ef61991`). 부모 `480ac` RTS→`2ac2`→`2ab8`로 host 변경 없이 자식 `c250`이 dispatch된다. `c250` 페이드, `c266`의 `de424`(e7c16 palette, 8da2 palette49, 43ffc scene de40c, 16fac/16ff8 node109156·map header de41c, 1861a 전송, 17012), 두 번째 페이드, 7e=14 타이머(SUBQ.W+BCS unsigned borrow), `c290`→`JSR a29c` 경계를 연결했다. 기존 helper 실행부를 그대로 사용하며 새 descriptor/node/palette/map도 기존 범위로 처리됐다(native가 새 range 필요 없음을 확인).

## 리뷰 발견과 수정

1. 메인이 core 전 case를 원본 바이트와 대조했다(de444 WORD shift·signed index, live A5 bank zero, c290 접근 순서, carry 보존 목록). 의미 결함 없음.
2. 검증기가 block 경계 불일치를 발견했다: core가 `c27a..c280`, `c290..c29e`를 묶어 native split checkpoint에서 멈추지 못했다. 메인이 명령별 block으로 분리하고 unit 내부 진입 목록을 고쳤다. 이후 실제 core에서 검증 통과.
3. 계약의 7e=8000 표현이 모호해 메인이 수정했다(이전 WORD 0만 borrow; 8000→7fff, `c28e` RTS). 계약 hash가 바뀌어 메인이 관측을 재실행했다(동일 결과, 새 pin).
4. Core 작업자의 실제 ROM 보조 실행에서 node26=0이었던 것은 native 비교에 포함된 결과이며 별도 결함이 아니다.

## 검증 결과

- Native: 정상26조건 split555/continuous111, guard6, 모두 fresh 두 번 split·continuous 재현. 정상 ports video38920/watchdog11460/PVC120, bank read6480/fixed1070, external0. 보고서 SHA `3e48b69e4827d5a25f7085aee1c81bf6bc0b41a64daa159a3232e690c16f3312`, 도구 SHA `d9b229b7ecd79f1e412ccc55e78c2c57061e376bf32fbbed83237272cb03b7ae`. ROM SHA·mtime 불변.
- C++ 비교: 32조건 split568/continuous112, 음성18, zero-step126, source 분류 carry Unknown549/Set19. 보고서 SHA `c22a93a33209745915f03606cdcd25dce8c33db5345a50e3b49d332d764c8f9f`, 검증기 SHA `281f2324d8b840d48c635ab51a5f9f16565729ecf3c1f0a35840e398cbce4822`.
- Core SHA `3ff5b441d1870c2747e722443e455c59341a2bfc94fe719cd3817ec9f3a28adb`, unit SHA `b28483bcd21442240ea77afbb22cc26c8a5a545e57bc5a006ddb0e283be46074`; unit 346 API 호출, 메인 UBSan 빌드(card_child·fade_card) 통과.
- 메인 `make -j4 all test` exit0: Python257/C++164 실행, 경고0.

## 기존 회귀(최종 core 기준, 메인 재실행)

모두 exit0, 조건 수는 리뷰0232와 같다. 보고서는 현재 입력 hash를 포함하므로 SHA가 갱신됐다.

| 검증 | 보고서 SHA256 |
| --- | --- |
| animation_machine | `96dacbd61bfb84b9e651d66e0149d9d3823b0c981f41b958e43d532df1d5a815` |
| callers | `16012107866de711021b9aec49e1a3e8ce1bcdff3f45357fc8c52670be8833b7` |
| carry | `96d5f82e43ba41a5364db45daa94b07d5693cfd16d302b77ce814ae4abf05f0e` |
| activation | `46db53ca5de676a4acdc843f31567a3e0754c693f75ff18e1c477a689ffe37c3` |
| readiness | `47c4021b24fdc718f997bb0645daaf08e24dc2fa3bc95a521d46d0fc61e0eb8f` |
| hud | `a2b9e30d0776ac4ba7a46a25f6515f1b16d59af1dae200ebe1267cb67b4814d8` |
| transition | `73a2fca21ddea860c1334a6af473f97bea29ca40c8f78193965104ef637020e9` |
| exit | `2171e9adba38f41cfd83c49eb3839ec7c3d528dada370ddb01e12e51b83cdda0` |
| screen | `56da083f3e4122ce5d5ee2df4e129c0e369a7620def65f82f795339fc53ff40b` |
| cleanup | `9cbd66f9b4e147eb8cefc026a6b0d77410723658d245c76cfb0d3de259723f40` |
| scene | `3666789b9ca4664d252cf944d04608738d9c36e054975e99a26ed2e5e7a1df23` |
| palette_bind | `8fc0239b9a73eaffcacc10c95d7f597a02eb82dd711b07943056184ec38f6443` |
| map_transfer | `d721e780474b52dcd1849a7568578022cc698b3a9a7c14083703f534700c61ce` |
| fade_card | `bf19444988693ab94eecde9c123c27ad4d533be2e39ca12c91384bd42d04ee2d` |

기존 검증기와 unit의 경계 이동은 필요 없었다(새로 지원된 PC를 경계로 쓰는 검사가 없음). 보고서별 고유 참조 합집합의 전수 재대조는 수행하지 않았고 각 검증기의 자체 hash 재검사 통과로 대신했다.

## 남은 제약

`a29c/a0a0/a2b8/a370` 카드 메뉴(약29함수·1150명령, 간접 callback, 입력 읽기), descriptor `c188`의 `c1c4`(a73e/bd26/9f36/a71a/a216; bd26은 BIOS c00468 재호출), `c2c8` 이후 페이드·부모62=ff·`2a00`, BIOS 내부, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal은 미완료다.
