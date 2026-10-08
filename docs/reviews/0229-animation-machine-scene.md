# 장면 설정의 실제 공유 스택 리뷰

대상 baseline `8db0a9e`, 브랜치 `codex/animation-machine-scene`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 직전 정리·해제 통합을 진척으로 승계하며 전체 목표·완료 기준을 유지한다.

## 원본 의미와 구현

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 계약의 fixed CPU 주소는 같은 ROM 파일 offset이다. 메인이43ffc/43f3e/43f5c/440c8/4410c,ccd6/cd1c,1ad9a,16f9a/1829a/1701a/182d0,47fe8의 실제 명령을 읽고 호출·분기·정수 폭·메모리 접근 순서를 확정했다. TRAP 뒤 문자열을 실행 코드로 간주하지 않는다.

47fe8의 실제48108 descriptor는12바이트 type2 node10d256+terminal이다. 기존 named descriptor15개에는 없지만 전체 fixed physical kind3에 이미 포함되어 있으므로 기존 여덟 MS5D v1 kind3와 C++ loader/bus를 그대로 사용한다. 별도 런타임 형식이나 사전 host decode를 추가하지 않는다. 기존12R `setup_scene_resources`의 host A0 save/suffix vector/D7 local count로 실제 stack을 대체하지 않는다.

MOVEA.L pop·PEA·WORD/LONG push와 호출·RTS를 shared RAM/A7으로 연결한다. MOVEM.W는 전체register sign extension이고 일반MOVE.W는lowWORD만 갱신한다. unsigned slot clamp 전에 WORD overflow가 발생하는 원본 순서를 유지한다. suffix type0은 원본이 먼저 수집한 뒤43f5c에서 TRAP하므로 기존 API처럼 수집 전에 선거부하지 않는다. RAM descriptor와 negative stride도 실제 bus 읽기와 operation budget으로 처리한다.

44074 BEQ는 초기44072 TST.W 또는44082 MOVE.W가 만든 Z를 소비한다. 두 writer 경로에서 분기까지 묶고 임의44074 진입은 거부한다. 53개 새 C 보존 block은 원본 opcode로 분류했다. 일반·UBSan unit의 선택된 call/RTS/pop/PEA 경계를 세 C 값으로 검사했으며, 이를53개 모두의 세 값 전수검사라고 부르지 않는다. Native C는 이번 범위에서 미관측이다.

## 발견 사항과 수정

- 초기 C++ 구현은 watchdog300001을 RAM/PVC만 지원하는 generic am_write로 전달했다. 메인 리뷰에서 발견해 scene 전용 BYTE 포트 기록으로 수정했다. generic MMIO 범위를 임의로 넓히지 않는다.
- Native direct44082 fixture는 A7이WORD pop 입력인데 inherited metadata가 RETURN LONG이라고 주장했다. 실제4바이트 값과 WORD 역할을 기록하고 return_pc=None으로 수정했다. 앞선 생성 결과를 삭제하고 수정된 입력 pin으로 전체 관측을 다시 생성했다.
- Unit의 video DBRA 검사에 RAM alias까지 검사한 듯한 주석이 있어 실제 검사 범위로 바로잡았다. 동작 변경은 없으며 단위 검증 수와 opcode 분류 수를 구분한다.

## Native backend와 재현

기존 도구의 memory hook 안에서 큰 bank mem_write를 수행하는 방식은 현재 Unicorn2.1.4의 격리된 합성 실행에서 충돌했다. 원인은 추정하지 않고 CPU가 소유하는 readonly bank buffer를 실제 PVC write마다 갱신하는 방식으로 새 관측기를 작성했다. work RAM16 mirror와 bank buffer 모두 CPU 수명에 맞춰 유지한다. 원본 fixedROM과 해당 시점의 bank payload 불변성을 각 phase에서 확인한다. raw PVC와 모델의 mask/bank side effect는 별도로 기록한다.

`tools/probe_scene_bank_backend.py`는 합성 fixed CPU 명령으로 bank3/2를 선택하고 CPU200000에서 서로 다른 원본 데이터1/0을 읽는 독립 backend 검사다. 메인 실행이 통과했다. 원본 게임 코드를 실행하거나 patch한 검사가 아니며, 실제 scene 조건의 bank data read0회를 이 합성 검사로 늘리지 않는다. 소스 SHA `9cf1011bb8521df035e0ec5e0732009f74d1fc5bc9b7e42f124dbc5cc5db6b83`.

## 확인한 스택 겹침

S=109194에서43ffc가 저장한 A0는 첫 node history clear와 겹친다. 중첩 return들은 그 아래에 남고44008의 live pop은0을 읽는다. 정상 부분 증거는4400a까지이며 동시에 바뀐 outer return을 원래 값으로 복구하지 않는다.

두 suffix record의 type2 node를S0-2c로 잡으면 node+26 슬롯 쓰기가4407c가 저장한 D7 WORD(S0-6)를1에서0으로 바꾼다.44082는 실제0을 읽고44086으로 일찍 분기한다. D7 상위WORD는 callee의 video 계산값을 유지한다. 별도 history-clear alias도 같은 savedWORD 변경을 관측한다. 남아 있는 suffix pointer를 건너뛴 뒤 전체 RTS까지 성공했다고 주장하지 않는다.

43fcc의 WORD push가 live descriptor operand를 바꾸는 경우,43f60의 PEA와 descriptor 겹침,182d0 WORD clear가 live RTS를0으로 바꾸는 경우도 원본에서 관측한다. 원본 fault의 부분 효과와 checked C++ API rollback은 구분한다.

## 검증 근거

메인 `make -j4 all test` exit0: Python257개, C++160개 실행, compiler warning0. 로그 `/tmp/ms5-scene-main-make.log`. 새 unit normal/UBSan 각각139 API 호출 통과, 별도 실제 kind3 loader를 연결한 unit140회 통과. 후속 수정은 검사 범위를 명확히 한 주석뿐이다. Core SHA `d0c0138e6270cdd79e8773ade9555600e75b45c8a92d2819789d4c890ec58c61`, 최종 unit SHA `02fc724e99e71d22324c3394ac4ec8d4a70e59c9d48e2f8171c21f89418d3f8b`.

원본 정상79조건225split/79continuous,guard8조건 각각8split/8continuous를 두 번씩 실행해348freshCPU/640단계를 확보했다. Native source SHA `4c5ae13f7599065008f52390636c2e8a97e3c91cbc9ccd670d642d277f24c9d9`, report SHA `46c0271dbfdc15f93e73bed69c08e62511a122c991e8c30c9e5b7979cd3b0ff3`. 메인이 현재2581개 고유 입력·산출물 SHA를 직접 확인했다. 정상 포트는PVC196/video244815/watchdog54911이며 실제 bank data read와 known C는0이다.

## 한계와 협업

Sol6.1/medium3명이 core/unit, native 관측, 비교기/문서를 분담하고 교차 검토한다. 메인은 복잡한 원본 의미·계약·실제diff·스택 겹침 설계·전체빌드·근거 확인·통합을 맡는다.47ff2의JSR e7c36은 다음 실행 전 경계다. 기존 screen/cleanup의 명시적 unsupported 경계만47ff2로 이동하고 역사적 정상stop은 그대로 유지한다.

자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체스테이지/적/보스·미사용 자료 전체 의미는 미완료다. 이 단위의 통합을 전체 Goal 완료로 취급하지 않는다.

## 새 C++ 공식 비교와 독립 감사

새 공식 비교는79조건225단계·직전 실제 C++ 출력146재개에서 full64KiB RAM/16R/PC·장치/bank·299922포트가 일치했다. 포트는PVC196/video244815/watchdog54911이다. 대기·외부읽기·native C 측정은0이다. 오류20조건(추가12+원본guard8) 및 zero-step30조건이 전체 API 출력 보존을 확인했다.

비교기 source SHA `2681bdc3db82c0292db6750b0808937d1ad4ff7034f9638261314fa761409fcd`, report SHA `26c596cb95fd59aba2f5d19a43ab65cd6baebbc8cdfe9aab46e88b09b5a19556`. 메인은4267개 현재 고유 참조의 SHA를 직접 확인했고 독립 감사도 일치했다. 실제 새 scene 계약·최종 unit·전체 C++ sources가 pin되어 있다.

독립 native 감사는 대표41조건88split/41continuous를82freshCPU로 다시 실행하고 모든8guard·2581참조를 확인했다. fullRAM/16R/PC/rawPVC/ports/read-write trace/continuous snapshots가 일치했다. alias 증거는 고정 stack 미리보기 창이 아니라 실제 A7·fullRAM·접근 trace에서 확인한다. 별도 core/비교기 리뷰는 새53개 C 보존 시작 명령을14RTS/12JSR/11BSR/6LEA/4MOVEA/3BRA/1MOVEM.W/1PEA/1JMP로 직접 분류했고 묶인 block에 숨은 flag writer가 없는지 확인했다.

비교기 초안의44074 오류 문자열 및182e0 보호된 bank WRITE 오류 분류 두 곳은 공식 실행 전에 교차 리뷰로 정정했다. Native guard와 C++ checked failure가 같은 RAM rollback을 한다는 주장은 하지 않는다.

## 최종 회귀와 참조 감사

기존 열 공식 회귀가 모두 통과했다. 메인이 새 scene을 포함한 열한 보고서의 현재 입력·산출물 SHA와 중복 경로의 일관성을 확인했다. 고유 합집합은32326개다. 각 담당자의 현재 참조 감사도 통과했다.

| 보고서 | SHA256 | 고유 참조 |
| --- | --- | ---: |
| `animation_machine` | `2fb58978f7cb7221531ec38f9cc8d8fd3d8cde87d7243f035041d6af78a70295` | 1717 |
| `animation_machine_callers` | `695ebf1e4e6ab6dae311019dd681ff3d561f1e7d45446d22aca6ff88906d5f62` | 1243 |
| `animation_machine_carry` | `5985124ab694d365fdb04d3a386ba8ed6feac469cc86ec73a14566b3d967d0c9` | 3052 |
| `animation_machine_activation` | `55904ac2700c4c3fa3049186315bf4c9c1251baa6eb1ae995485c769999f9333` | 1046 |
| `animation_machine_readiness` | `9756036b99d183cb9109d24ed42b7f5c9c397ac67cc315044bfecee45cc09fb8` | 2985 |
| `animation_machine_hud` | `72dda8779f7875d99bc67d3296f378ce3b1296c11676404aa5dc1673087561b6` | 4998 |
| `animation_machine_transition` | `075f6f71af071eb576322714b22da7b09cc30b4e6ae4ac0a4a50c06d90106c42` | 4206 |
| `animation_machine_exit` | `1f8fbb6055fe19edde40531a28f5f0faa42e80c27806c8cb09dbe3a144121f61` | 4653 |
| `animation_machine_screen` | `1095ebfce9c12a96c909e631685a09280f1e24471029138b3b46e9c7d55f7a42` | 2579 |
| `animation_machine_cleanup` | `1e6bc8517ca0fdc98e8855b00cbe85bafbbf72d37ca93ad88beb3c71f9430bc4` | 2533 |
| `animation_machine_scene` | `26c596cb95fd59aba2f5d19a43ab65cd6baebbc8cdfe9aab46e88b09b5a19556` | 4267 |

원본·추출 데이터는 커밋하지 않는다. 코드·재생성 도구·계약·검증 기록만 통합하며, 임시 감사 파일의 존속을 재현 전제로 요구하지 않는다.
