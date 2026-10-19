# frontier 단위 FR2b(FR2a 뒤 새 IO frontier `48256` `76852` `b336a` `a92a`와 그 자연 후속) 구현 계약

**구현 전 계약 — 작업자(Claude Opus 5.5 / high) 초안.** 이 문서를 먼저 쓰고 그대로 구현한다. FR2 계약(`animation-machine-frontier-fr2-contract.md`)의 구조·공통 규칙을 따르고 다른 점만 적는다. 메인 결정(실행 수/block 비로 재배열): FR2b는 FR2a IO 재실행에서 새로 나온 작은 root `48256` `76852` `b336a` `a92a`를 맡고, 약 220 이하이면 다음으로 좋은 작은 root를 더한다(약 230을 넘지 않는다). 결정 항목은 작업자 권고안으로 구현하며 메인이 바꾸면 그에 맞춰 고친다.

## 기준 입력

- [F] ROM: `extracted/program/maincpu.decrypted.be.bin`, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB, mtime `1791291625`. 코드·고정 표는 모두 `<100000`이라 CPU 주소 = 파일 오프셋이다. bank 창 읽기 `2000d0` `2000d4` `200140` `20017c`는 CPU 주소이고 물리 오프셋은 `bank_base + (주소 − 200000)`이다. ROM·추출 데이터는 수정하지 않았고 저장소에 넣지 않는다.
- [F] 저장소 기준 `b4a7e21`(branch `claude/frontier-units-2`, FR2a 커밋). routing 기준 `engine/src/animation_machine.cpp` SHA256 `eadc97b080cbeacbf16524ca1626fb4013b07acdc0042340743ab34509201923`(= FR2a IO 재실행 `frontier.json`의 `routing_file_sha256`).
- [F] frontier 입력: FR2a 뒤 IO 재실행 `/Users/start/Workspce/ms5-scratch/fr2/ioA/frontier.json`(SHA256 `4a8077c738598c9a8ab3d8714217a783254e12411dec206ed4e12bae7f3769b7`; 첫 실패 전 일치 **151,848**, frontier run **53**). 이 단위의 확정 frontier(모두 phase N):
  - `48256`: P1 11 + P1b 1, frame 325, A6 = `100f5c`, LONG(A6) = `e525a`(U02), A7 = `1feff8`, 복귀 LONG `e528c`(`e5286 JSR 48256.l`). U06b가 `48250..48256`을 routing했고 `48256`부터 routing 밖이다.
  - `76852`: P1 11 + P1b 1, frame 133, A6 = `101eac`, LONG(A6) = `76852`(U09 `7679a`/`767cc MOVEA.L #76852,A0`의 `28ae` 자식), 복귀 `2ac2`. FR2a `c0ace` run의 다음 root.
  - `b336a`: P1 2 + P1b 1, frame 120, A6 = `101eac`, LONG(A6) = `b336a`(FR1b `b319e MOVEA.L #b336a,A0`의 `28ae` 자식), 복귀 `2ac2`. FR2a `b33d8` run의 다음 root.
  - `a92a`: boot-title-start 1(+ fixture fx-start-c79a), frame 117, A6 = `100f5c`, LONG(A6) = `b344`, A7 = `1feff0`, 복귀 LONG `9e14`(card menu 표 LONG의 `JSR (An)` live 대상). FR2a `a8ee` run의 다음 root.
- [F] **자연 후속 확인**(scratch `tools/predict.py` `tools/unrnew.py` `tools/l0trace.py`, 읽기 전용): IO 관측 `artifacts/animation_machine_io_native/runs/*/*.json.gz`의 frame별 `cbs`(node callback)와 `unr_new`(그 run에서 처음 실행된 routing 밖 PC 목록; 관측 당시 routing 기준)를, 현재 routing + 이 단위 범위로 다시 걸러 frontier frame 뒤 첫 routing 밖 PC를 찾았다. node LONG(A6) 추적(`states/P1/000.pack.gz` node `101eac`): frame 133 `76852` → 134..165 `768b6`(설치 값, 목록 `76a1c..76aa0`) → 166..183 `718c8` → 184 `71d48`(N15, routing됨) → 185 `70c0c` → 186 `72a18` → 187.. `72bcc`(routing됨). 같은 run의 `unr_new`: frame 153 `769ac` `769b4` …(`28ae` 자식 `76944` 생성 함수), 156 `769b2`, 165 `4c2cc`, 167 `769f4`, 252 `c5370`. boot-title-start frame 117: `a8d0` `a8d4`(다른 메뉴 처리기), 122 `ca50`(`4e68e` 계열). bc844 run(`P1/22`): 218 `bc8b6` → 263 `bc8f2` → 264 `bc924` → 276 `bc93c` → … → 301 `bc404`. b336a run(`P1/72`) node `101eac`: 121 `b33bc` → 133 해제 → 430 `dd574`(다른 node, U01 `dd546`의 설치 값).
- [F] 정적 디코드: capstone M68000, FR2 계약과 같은 block 시작 규칙(분기 대상·fall-through, JSR/BSR 대상과 복귀 PC, DBcc 대상, `MOVE.L #imm,(A6)` 설치 값, 범위 밖에서 들어오는 실제 분기 대상). routing된 PC, `RTS`, `TRAP`, `JMP`/`JSR (An)`에서 멈춘다. `28ae`/`2986` 자식 값은 기록만 한다. 이 단위만의 정지 집합(결정 1): 설치 값 `71884` `70d92` `70e2a` `71468` `72978` `72f8a` `bc93c`.
- 작업자 scratch(저장소 밖, 재현용): `/Users/start/Workspce/ms5-scratch/fr2b/`
  - `tools/`: FR2 scratch의 `hroute.py` `fclos.py`(경로만 바꿈), `unit_fr2b.py`(= `unit_fr1.py` + 환경 변수 `FR2STOP` 정지 집합), `c1.py`(closure 요약), `dsm.py`(디스어셈블), `xref.py` `longref.py` `callers.py` `refs.py` `cread.py` `leafscan.py`(경로만 바꿈), 새 `nextcb.py` `predict.py` `unrnew.py` `l0trace.py`(IO 관측 읽기), `probe_scan_b.py`(기존 시험의 범위 안 상수), `specs_next.py`(FR2c 이후 재측정).
  - `starts_b.txt`(시작 214개) SHA256 `03dc3024660d84a18120b4de31989cf63fddda710e7ec6a41af10a239e7f9b71`; `unit_b.out`(block별·범위 전체 디코드), `xref_b.out` `longref_b.out` `callers_b.out` `probe_b.out`.
  - 재현: `FR1PART=b FR2STOP=71884,70d92,70e2a,71468,72978,72f8a,bc93c FR2G='48256:48256;76852:76852;b336a:b336a;a92a:a92a,a8d0;76944:76944,769ac,769b2,769f4;70c0c:70c0c;dd574:dd574;bc844:bc844;4c2cc:4c2cc' .venv/bin/python …/fr2b/tools/unit_fr2b.py B D`.
- 표기: [F] 원본 바이트·현재 소스·기존 기록에서 확인한 사실, [I] 추론, [U] 미확인.

## 재확인과 범위

- [F] **root closure**(현재 routing, 같은 규칙): `48256` 1(`48256..48262`, 명령 4), `b336a` 8(설치 `b33bc` 포함), `a92a` 12(`a92a..a952` `a8dc..a8ee` `9ef2..9ef8` `bb6..bbe`), `76852` 설치 값 전부 따라가면 494 — 그중 `76852` 본체·설치 `768b6`·`JMP` 대상 `70674`/`70764`와 그 설치 값 `718c8`까지가 62(`71884` 정지).
- [F] **더한 것(결정 1)**: 위 네 root(83 block)는 약 220보다 훨씬 작다. 다음 후보 중 IO 관측이 같은 run에서 곧바로 실행한다고 보여 준 것(위 "자연 후속 확인")을 실행 수/block 순으로 넣었다.
  - `76852` run(12)의 후속: `70c0c`(설치 값, 72; 그 설치 값 `70d92` `70e2a` `71468` `72978` `72f8a`와 표 `70d72` 값은 정지), `28ae` 자식 `76944`(8)와 그것을 만드는 표 처리기 `769ac` `769b2` `769f4`(11; LONG 표 `4a720..4a72c`), `4c2cc`(5; U12 `704fc`·밖 5곳의 `JSR` 대상).
  - `a92a` run(1)의 후속: 메뉴 처리기 `a8d0`(+2).
  - `b336a` run(3)의 후속: U01 `dd546`의 설치 값 `dd574`(14; 설치 사슬 `dd5a6`..`dd69c` 전부 범위 안).
  - `bc844`(3 run; FR1c `bc15c`/`bc182`의 `28ae` 자식)의 첫 설치 단계(19; `bc93c` 정지): 전체 66을 넣으면 233이라 약 230을 넘는다.
- [F] **합 214 block**, 17 범위, 명령 559, 짝수 PC 1,231(내부 1,017), 이어 붙인 바이트 2,462, SHA256 `2d78ff43454c467c5ea4c891794c39a8321f100b192ab2de54d6ddb4b6786671`. 기존 routing과 겹침 0, 연속 Bcc 묶음 0.
- [I] **예상 진척**(scratch `predict.py`, 상한 추정; IO 비교 재실행이 실제 측정값): `48256` 12 run frame 325 → 끝(599), `76852` 12 run 133 → 252(`c5370`), `b336a` 3 run 120 → 끝, `bc844` 3 run 217 → 276(`bc93c`), `a92a` 117 → 122(`ca50`, FR2c 이후), fixture fx-start-c79a 269 → 끝. 합 약 +6,355 frame. 나머지 frontier(`4e68e` 14, `50dae` 3, `5ab82` 3, `1d1f4` 1, fixture `2634` 2)는 그대로.

| 묶음(진입) | block | 명령 | 범위 |
| --- | --- | --- | --- |
| `48256` | 1 | 4 | `48256..48262` |
| `76852`(+ `768b6` `70674` `70764` `718c8`) | 62 | 173 | `76852..76922` `76926..76944` `70674..7086a` `718c8..718ec` `702cc..702f0` |
| `76944` `769ac` `769b2` `769f4` | 19 | 44 | `76944..769fc` |
| `70c0c`(+ `70c76`) | 72 | 176 | `70c0c..70d72` `702f0..702fa` `70302..703f6` `70606..7062a` |
| `b336a`(+ `b33bc`) | 8 | 22 | `b336a..b33d8` |
| `a92a` `a8d0` | 14 | 22 | `a8d0..a8ee` `a92a..a952` `9ef2..9ef8` `bb6..bbe` |
| `dd574`(+ 설치 7) | 14 | 54 | `dd574..dd6b2` |
| `bc844`(+ `bc8b6` `bc8f2` `bc924`) | 19 | 49 | `bc844..bc93c` |
| `4c2cc` | 5 | 15 | `4c2cc..4c2fa` |
| 합 | **214** | 559 | 17 범위 |

## 요약

| 범위 | 바이트 | SHA256 | block | 짝수 PC |
| --- | --- | --- | --- | --- |
| `bb6..bbe` | 8 | `8def87d91db4d482e58a0ea559807cfeb5160c2235a45e1f02d9ae162a3a8b9b` | 1 | 4 |
| `9ef2..9ef8` | 6 | `1493cacabc2ba42eb3e08e164d647996d5cdd5d83b5a743533838dad8e36f82a` | 1 | 3 |
| `a8d0..a8ee` | 30 | `84280c12c87e8102daff03f8b902cb4c0c5f77a64eab96d39b608eed343f17d3` | 5 | 15 |
| `a92a..a952` | 40 | `8946dc6751dc060b780566a49d887779fb2838a88cb5a997b891ad2d392a7e71` | 7 | 20 |
| `48256..48262` | 12 | `5dbd07ca3161dfddc7a687d2f7f515b0b23ff1370b9894f126c8b9e16a9218af` | 1 | 6 |
| `4c2cc..4c2fa` | 46 | `2823a6e1622b438e9e29ad10f457853e3be4796fdc06105d8d5b69afeafc76d7` | 5 | 23 |
| `702cc..702fa` | 46 | `882523c29c866d58665e00bd9da803a3bee4b0bfc0358f6563a9ce24faf8cff7` | 2 | 23 |
| `70302..703f6` | 244 | `2237d9f78b1691a7df23176fc36bf877db091d2e416eb9acc1ee07fa0dc74e92` | 25 | 122 |
| `70606..7062a` | 36 | `fe70cfcbf4c3e3e4962fc38d05bafafdadff51af84c900856623ee862f458f99` | 4 | 18 |
| `70674..7086a` | 502 | `90e20f260fbe48a6dd523566a4c76e6b3174a7116cf3c9d7443225c984a6259a` | 31 | 251 |
| `70c0c..70d72` | 358 | `4bbf6c854dbc53b76ee6e6e839c5943fa5e4899b08fbc3e3714348725c12ce09` | 42 | 179 |
| `718c8..718ec` | 36 | `7322a03bcc50347fa59ad5398437138ba978b422194447f119812a9c6d6741e0` | 5 | 18 |
| `76852..76922` | 208 | `7f2fe682a8eda6ecb52b8442c644c485de04e833d3e0058f875e6c42797bb8ac` | 20 | 104 |
| `76926..769fc` | 214 | `05390b7802ba9cc1726d191edc9585d1f1072d3ca92ef15a57d53709b95927b2` | 24 | 107 |
| `b336a..b33d8` | 110 | `c4c0f4b05280cbf5aeec6c309e706b159b930c29b503ce64ae980ff5dfa94f70` | 8 | 55 |
| `bc844..bc93c` | 248 | `61bf0e55c792503f38831e61d70011510b639bc806c18c0d3742ef0240629481` | 19 | 124 |
| `dd574..dd6b2` | 318 | `c7117749fe1118d447f31028bdbd6205735da136734634cf7e80f1540a941743` | 14 | 159 |
| 합계 FR2b | 2462 | 이어 붙인 바이트 `2d78ff43454c467c5ea4c891794c39a8321f100b192ab2de54d6ddb4b6786671` | **214** | 1231(내부 1017) |

- [F] closure가 17 범위를 빈틈없이 덮는다(도달하지 않는 명령 0). `76922 BRA.W 76932`(`7691c JMP` 뒤 죽은 코드 4 byte)는 범위 밖이다. X 소비는 같은 block 안에서만 일어난다: `7036a`(`ADD.B D1,D1; ADDX.W D2,D0` × 8, 켜진 bit 수 세기), `70394`·`703a8`..`703e4`(`ADD.B D2,D2; SUBX.W D3,D1; BCS`). 계산 점프 없음. `JSR (An)` 없음. `TRAP` 없음. I/O port·bank 쓰기 없음. `MULU`/`DIVU` 없음. `ASR.L #5`(`702cc` 두 번), `ASR.L #4`(`76984`).
- [F] **경계 이웃**: routing된 것 `bb4`(H1) `bbe`(F6a) `9ef0`(FR2a) `9ef8`(FR2a) `a8ce`(C2) `a8ee`(FR2a) `48254`(U06b) `4c2fa`(B2b) `702ca` `70604`(N15) `7086a`(U14) `76850` `769fc`(U09) `b3368`(FR1b) `b33d8`(FR2a) `dd572`(U01). 그 밖은 routing 밖 형제 코드·자료: `a928`, `48262`(`JSR 474e2(PC)`, 다른 함수), `4c2ca`(`4c2c4 JSR 4bce0(PC); BRA.W 4c2d0`), `702fa..70302`(LONG 자료 `ffc80000 00700050`), `7062a` `70672` `70c0a`, `70d72..70d92`(LONG 표), `718c6` `718ec`, `76922`(죽은 `BRA.W`), `bc842` `bc93c`, `dd6b2`.
- [F] **나가는 곳은 모두 routing돼 있다**(각 실행부의 `case` block 시작): callee `288c` `28ae` `8ebe` `8ff4` `a73e` `43e34` `43ea4` `46d72` `491b6` `491c4` `49214` `49274` `49290` `494c0`(`702f0 JMP`) `497a6` `49a84` `49f8c` `49fc6` `4bc44` `4be2c` `4be34`(`702cc JMP`) `4bfa4` `70036` `7028e` `70418` `7054c` `705ca` `c6a96`, 출구 `JMP 2a00`(`7693c` `769a4` `b33d0`), `BRA.W 72dd2`(`70d6e` `718e8`), `BEQ.W a70a`(`a8d4` `a8dc` `a8e4`), `BEQ.W 71c90`(`70c76`). 32곳.
- [F] **참조**(ROM 전체 직접 분기·LONG 상수, scratch `xref_b.out` `longref_b.out` `callers_b.out`): 범위 밖에서 들어오는 실제 분기·설치·LONG은 모두 block 시작이다 — `48256`(`e5286` U02 / `e5ba6` U07 / `4842a` `JSR`), `76852`(U09 `7679a` `767cc` 자식 값), `b336a`(FR1b `b319e`), `bc844`(FR1c `bc15c` `bc182`), `dd574`(U01 `dd546` 설치), `70c0c`(U13 `70a5c`, N15 `71dcc` 설치; 71xxx·7axxx LONG 여러 곳), `70302`(N15 `711e2`, `70fe0` `71fde BSR.W`), `702cc`(`6f8a4 JMP`, `71884 BSR.W`), `a8dc`(`a988 JSR`, `aef2 BSR.W`), `9ef2`(`b812 JSR`), `bb6`(LONG `a94c`), `4c2cc`(U12 `704fc`, `8f854` `9b564` `a6426` `a738a` `ea868 JSR`, `961fe` `96208` `a6dc4` `a6dce` `a7b14` `a7b1e JMP`), `4c2d0`(`4c2c8 BRA.W`), `769ac` `769b2` `769f4`(LONG 표 `4a720` `4a724` `4a728`), `a8d0` `a92a`(card menu 표 LONG). 내부 PC로 보이는 분기(`76868` ← `768c6`, `7686c` ← `768b4`, `768ca` ← `768ac`, `768e4` ← `7689c`, `76908` ← `76982`, `b3396` ← `b33fe`)와 LONG(`bb8` `9ef4` `a8de` … 4xxxxx 영역 값, `70702` ← `292dba`…, `70d3c` ← `16d1e` 등)은 명령 중간·자료의 우연한 바이트다 [F](각 위치 디코드: `768c2 CMPA.L #76aa0,A0` 안, `768b0 MOVE.L #768b6,(A6)` 안, `768a8 MOVE.L #76a1c,7e(A6)` 안, `76898 MOVEA.L #76c46,A1` 안, `7697e MOVE.L #76984,(A6)` 안, FR2a `b33fa JSR c6a96.l` 안; 1 MiB 밖 값과 홀수 대상). `76932` ← `76922 BRA.W`는 죽은 코드다. `73744`(N20) `SUB.L 76974(PC),D0`는 코드 바이트를 자료로 읽을 뿐이다. `5a8d6`(N13)의 `dc.w a8dc`는 자료 해석이다.
- [I] 의미: `48256`은 `-7453(A5)`(= BYTE `100bad`) + 1을 BYTE `5681(A5)`(= `10d681`)에 넣는 stage/area 갱신 helper다(U06b `48250`과 같은 BYTE, `tools/verify_stage_catalog.py`의 `next_area`). `76852`는 U09 객체의 `28ae` 자식(효과 연출): `49290` `491c4`로 부모 위치, `497a6`의 C로 소리 `c54`/`c4e`(`8ebe`), 애니메이션 `76c46`, 설치 `768b6`이 WORD 쌍 목록 `76a1c..76aa0`을 따라 이동(`43e34` `49fc6`, `288c`로 삭제 판정), 목록 끝에서 부모 BYTE `89`로 `70674`/`70764`(N15 계열 객체의 초기화 꼬리: bank 창 `2000d0`/`2000d4` 애니메이션, 설치 `71884`/`718c8`/`71b04`, `8ff4`, U12 `70418`, 속도 LONG `64`/`36`)로 넘어간다. `718c8`은 `702cc`(LONG `36`/`3a`를 목표 쪽으로 1/32씩, `4be34`)와 `49fc6`로 움직이다 BYTE `15` bit 7이면 `71d48` 설치. `70c0c`는 같은 계열의 상태 판정 callback(거리 WORD `8e` − `42`, N15 판정 `7054c` `705ca` `7028e`, `70302`가 BYTE `87`의 켜진 bit 중 난수(`49a84`)로 하나를 골라 표 `70d72`의 다음 상태, `70606` 화면 판정; 설치 값 여럿 중 마지막 것이 남는다). `76944`는 효과 자식(소리 `c53`, 애니메이션 `76c84`, LONG `3a`를 `fffe0000` 쪽으로 1/16씩, `43ea4`), `769ac`/`769b2`는 그 자식을 만드는 표 처리기(방향 BYTE를 스택에, `(A0)`의 WORD 쌍 위치, `49214` `491b6`, 필요하면 자식 BYTE `15` bit 0 반전), `769f4`는 BYTE `61` bit 3을 켠다. `b336a`는 FR1b `b30f6` 계열의 연출 자식(bank 창 `20017c`, 수명 WORD `86`). `a92a`/`a8d0`은 card menu 항목 처리기(`a73e`의 D0로 `a70a` 분기; `a92a`는 D0.W = 3이면 부모 BYTE `62` := 1, `9ef2`(BYTE `-e6(A5)`), `bb6`(BYTE `100014` |= D0.B)). `dd574`는 U01 객체의 설치 사슬(RAM 기록 `10b1d6`/`10d256`의 LONG `8`/`c` 속도, LONG `76` += `60000`이 한계를 넘으면 다음 단계). `bc844`는 FR1c `bc08c`의 자식(bank 창 `200140` 애니메이션, 부모 BYTE `62`와 WORD `76`으로 단계 진행). `4c2cc`는 지형 판정 helper(`4bc44`, U12 `46d72`의 C, Set이면 D0.W := −상위 WORD D6). 이름은 확정하지 않는다.

## 공통 규칙·native 검증 계획

FR2 계약 "공통 규칙·native 검증 계획"을 그대로 따른다. 다른 점만 적는다.

- **실행부·이름.** `engine/src/animation_machine_objects_fr2b.cpp`, 함수 `animation_objects_fr2b_block`. 오류 문자열은 `unsupported animation objects fr2b PC`(범위 안 내부 PC 직접 진입), `objects fr2b caller requires known carry`(C 소비 block에 Unknown C; 소비자 10개). 그 밖의 오류는 공용 bus/스택 오류다.
- **공유 파일 최소 수정.** dispatch 사슬 마지막 `else return am_error(...)` 앞에 `else if` 하나(17 범위, FR2a 줄 뒤), `carry_preserving_pc`의 `// BTST/BEQ changes only Z` 앞에 주석 달린 case 묶음 하나(11개, "carry"), `animation_machine_internal.h` 끝에 선언 하나, `Makefile`(`ANIMATION_MACHINE_SOURCES` 한 줄에 추가, 시험 target, test 목록 실행 줄; SOURCES·HEADERS 줄은 각각 하나 유지), `tools/verify_animation_machine.py` `SOURCES`.
- **경계.** routing 밖 실행 PC는 없다(live 대상·TRAP 없음). 정지 설치 값 `71884` `70d92` `70e2a` `71468` `72978` `72f8a` `bc93c`와 표 `70d72`의 값(`71502` `71562` `715c2` `71622` `716ca`)은 `MOVE.L ...,(A6)`로 쓰기만 하고 실행하지 않는다(결정 2). 기존 시험이 stop으로만 보던 PC(`48256` `76852` `b336a` `bc844` `70302` `4c2cc` `dd574` `70c0c`)는 stop 판정이 routing보다 먼저라 그대로 통과한다. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. dispatcher 오류 확인에 쓰는 범위 옆 PC는 자료 PC(`702fa` `70d72` `76922`)뿐이다; 다른 단위·다음 frontier가 routing할 코드(`48262` `4c2c4` `769fc..`(U09) `bc93c` `c5370` `71884` …)는 탐침으로 쓰지 않는다.
- **오류 fixture의 실패 PC**(리뷰 0264 L-1): FR2와 같다. 행의 run stop은 실패 block 바로 뒤 PC다.
- **자료 읽기**(live bus, 상한 검사 없음): LONG `(70d72 + sext(4·D0.W))`(`70d22`; 자연 D0.W = 0..7, [I]), WORD `(A0)+` 두 번(`768b6`, 목록 `76a1c..76aa0`; `769c8`, 호출자가 넘긴 A0), bank 창 LONG `2000d0` `2000d4` `200140` `20017c`와 그 LONG `d(…)`(`d` = `180` `1cc` `20` `28` `c` `1c` `8c`). RAM 읽기: node field(A6), 부모 LONG `c(A6)`의 BYTE `89`/`62`, `-7453(A5)`(= BYTE `100bad`), `-e6(A5)`(= BYTE `107f1a`), LONG `3e(A6)`·`2e`·`32`(`4c2d0`). 단위 시험은 고정 ROM·bank 주소에 합성 typed physical byte를 둔다(ROM 자료가 아니다, 자료 영역 `70d72..70d92` `76a1c..76aa0`과 bank `2000d0..2000d8` `200140..200144` `20017c..200180`, 그 뒤 LONG만; 코드 바이트와 겹치지 않음). V1·실제 ROM 차분은 원본 ROM을 읽는다.
- **스택.** `MOVE.B #e2,-(A7)`(`7068c`) / `MOVE.B #10,-(A7)`(`7077c`) / `MOVE.B 15(A6),-(A7)`(`70806`)와 `MOVE.B (A7)+,D0` · `MOVE.B (A7)+,87(A6)`(`70832`)은 BYTE를 WORD 칸에 넣고 뺀다(A7 ±2, 값은 높은 BYTE; `am_push`/`am_pop` 크기 1). `70806`이 넣은 BYTE는 `JSR 70418` 뒤 `70832`가 먼저 꺼내고, `7068c`/`7077c`가 넣은 BYTE는 그다음에 꺼낸다(그 사이 `JSR 8ff4`·`JSR 70418`의 복귀 LONG은 각자 돌아온다). `MOVE.W D1,-(A7)`/`(A7)+`(`70350`/`70362`), `MOVE.B D0,-(A7)`·`MOVE.L A0,-(A7)`(`769b4`)와 `MOVEA.L (A7)+,A1`(`769c8`)·`TST.B (A7)+`(`769e6`), JSR/BSR 복귀 LONG. 홀수 A7은 checked 오류다.
- **정수 연산.** WORD/BYTE 대상은 하위만 바꾸고 상위를 유지한다(`MOVE.W/.B`, `ADD.W` `ADDQ.B` `SUBQ.W` `SUBI.W` `NEG.W` `EOR.W` `ANDI.B` `OR.B` `BCLR`/`BSET`/`BCHG`, `EXT.W`, `SEQ.B`/`ST.B`). `MOVEQ`는 LONG 전체(부호 확장). `SUB.L`/`ADD.L`/`ADDI.L`/`NEG.L`/`CMPI.L` LONG, `ASR.L #5`/`#4`(32 bit 산술: 부호 bit 복제, 명시 구현), `SWAP`, `MOVEM.L 2e(A6),D0-D1`(D0 = LONG `2e`, D1 = LONG `32`), `CMPA.L #76aa0,A0`(무부호 32 bit), `CMPA.W #0,A0`(A0 = sext(0) = 0 비교), `MOVEA.L (A0,D0.W),A0`(sext 색인), `ADD.B Dn,Dn`의 X(= 옛 bit 7)와 같은 block의 `ADDX.W D2,D0`(D0.W + D2.W + X, X/C = 올림) / `SUBX.W D3,D1`(D1.W − D3.W − X, C = 빌림: 무부호 D3.W + X > D1.W), `BCLR.B #1,D1`(Dn: LONG bit 1, Z = 옛 bit), `BTST.B #n,d(An)`, `BSET.B #n,d(An)`(flag는 다음 `TST`가 덮음), `TST.B`/`TST.W` + `BNE`/`BEQ`/`BPL`/`BMI`, `CMPI.W #10/#30/#48/#110`·`CMPI.B #3`·`CMPI.L #8b00000/#14900000/#15900000`(무부호 `BCS`/`BCC`, `BEQ`/`BNE`), `SUBQ.W #1,d(A6)` + `BCC`(옛 WORD ≠ 0). 같은 block 안에서 만들고 소비한다(예외: "carry"의 callee C).

## carry

- [F] **소비 block 10개**(callee가 돌려준 C):
  - `7031e BCC.W 703f0`: `7031c BSR.B 702f0` → `702f0`(`LEA 702fa(PC),A0; JMP 494c0.l`)의 꼬리 호출 FR1c `494c0`(`49508` → N08 `49462`, known C). Clear → `703f0`, Set → `70322`.
  - `7686e BCC.W 76884`: U20 `497a6`(`TST.B 10fd92` Clear / `497b0 ORI` Set). Clear → `76884`, Set → `76872`.
  - `76938 BCS.W 76942`: `288c`(stage_event_ops `2898 ORI` Set, readiness `289e` `28a8 ORI` Set / `28ac` Clear). Set → `76942 RTS`, Clear → `7693c JMP 2a00`.
  - `769a0 BCC.W 769aa`, `bc930 BCC.W bc93a`: `49fc6`(interpreter known C). Clear → `769aa RTS` / `bc93a RTS`, Set → `769a4 JMP 2a00` / `bc934`.
  - `70cf8 BCC.W 70d02`, `70d06 BCC.W 70d10`, `70d14 BCC.W 70d1e`: N15 `7054c`(`70588 ANDI` Clear / `7058e ORI` Set), `705ca`(`705fe ANDI` Clear / `705f8 ORI` Set), `7028e`(`70298` `702c6 ANDI` Clear / `702c0 ORI` Set / `7029e` CMPI 빌림 → `702ae RTS`). Clear → 다음 판정, Set → 설치 쓰기 block(`70cfc` `70d0a` `70d18`).
  - `70d4c BCC.W 70d60`: 이 단위 `70606`(`7061e ORI` Set / `70624 ANDI` Clear). Clear → `70d60`, Set → `70d50`.
  - `4c2e8 BCS.W 4c2ee`: U12 `46d72`(`46eda` Clear / `46ee6 ORI` Set → `46eea RTS`). Set → `4c2ee`, Clear → `4c2ec RTS`.
- [F] **C를 넘기는 `RTS` 1개**(결정 3): `4c2ec RTS`는 `4c2e8`의 Clear(BCS가 떨어진 쪽)를 그대로 돌려준다. [F] `4c2cc`의 직접 호출자 6곳이 복귀 직후 `BCC.W`로 읽는다(U12 `704fc` → `70502`(routing된 소비자), 밖 `8f854` `9b564` `a6426` `a738a` `ea868`; scratch `cread.py`). Set 쪽은 `4c2ee`가 자기 block에서 `ORI.B #1,CCR; RTS`로 정한다.
- [F] **known C 생산**: `7061e`(`ORI; RTS` Set), `70624`(`ANDI; RTS` Clear), `4c2ee`(`…; ORI; RTS` Set). 그 밖의 모든 block은 진입 때 Unknown이 되고 Unknown으로 끝난다.
- [F] **읽는 곳이 없는 known C**(carry 보존 목록에 넣지 않음): `703f0`(`MOVEQ` Clear) `703f4`(`SUBX` 빌림 Set) — `70302`의 호출자 4곳(`70d1e` 이 단위, N15 `711e2`, `70fe0` `71fde`)이 복귀 뒤 C를 읽지 않는다; `76942` `769aa` `b33d6` `bc8f0` `bc93a` `dd5c0` `dd612` `dd664` `dd69c`(node callback의 `RTS`: dispatcher 복귀 `2ac2`), `a8ec` `a938` `a950` `bb6` `9ef2` `48256` `769f2` `769f4` `70860`(호출자 C 읽기 0: `cread.py` `bb6` `9ef2` `a8dc` `a92a` `48256` `702cc` `70302` `70674` `70764` `718c8` `76852` `76944` `769ac` `769b2` `769f4` `b336a` `bc844` `dd574` `70c0c` `a8d0` `4c2d0`).
- [F] 그래서 `carry_preserving_pc`에 넣는 것은 11개다: 소비자 `7031e` `7686e` `76938` `769a0` `bc930` `70cf8` `70d06` `70d14` `70d4c` `4c2e8`, 통과 `RTS` `4c2ec`. Unknown C로 소비자에 들어오면 checked 오류다(통과 `RTS`는 Unknown을 그대로 돌려준다).
- [F] flag 재계산(block 경계를 건너 다시 계산하는 flag)은 없다.

## 객체 `48256`, `b336a`, card menu 처리기 `a92a` `a8d0`

- **`48256`**: D0.B := BYTE `-7453(A5)`, D0.B += 1, BYTE `5681(A5)` := D0.B, `RTS`.
- **`b336a`**(FR1b `28ae` 자식 값): WORD `68` `1e` := `1001`, D0.W := `5e`, D1.W := 3, D2.B := 0, `JSR c6a96`(복귀 `b3388`). **`b3388`**: anim(`15b`, `20017c`, `c`)(복귀 `b33b0`; FR2 "공통 꼴"). **`b33b0`**: WORD `86` := `c`, 설치 `b33bc`.
- **`b33bc`**(설치 값): `JSR 43e34`(복귀 `b33c2`). **`b33c2`**: `JSR 49fc6`(복귀 `b33c8`). **`b33c8`**: WORD `86` −= 1, 옛 WORD ≠ 0(빌림 없음) → `b33d6 RTS`, 아니면 `b33d0 JMP 2a00`.
- **`a92a`**(메뉴 기록 LONG, `JSR (An)` 진입): `JSR a73e`(복귀 `a92e`). **`a92e`**: `BSR a8dc`(복귀 `a930`). **`a930`**: D0.W = 3 → `a93a`, 아니면 `a938 RTS`. **`a93a`**: A0 := LONG `c(A6)`, BYTE `62(A0)` := 1, `JSR 9ef2`(복귀 `a94a`). **`a94a`**: `JSR bb6`(복귀 `a950 RTS`).
- **`a8d0`**: `BSR a73e`(복귀 `a8d4`). **`a8d4`**: D0.W = 3 → `a70a`, 아니면 `a8dc`. **`a8dc`**: D0.W = 4 → `a70a`, 아니면 `a8e4`: D0.W = 1 → `a70a`, 아니면 `a8ec RTS`.
- **`9ef2`**: D0.B := BYTE `-e6(A5)`, `RTS`. **`bb6`**: BYTE `100014` |= D0.B, `RTS`.

## 객체 `76852`와 꼬리 `70674` `70764` `718c8` `702cc`

- **`76852`**(U09 `28ae` 자식 값): D0 := 0, D1 := 0, `JSR 49290`(복귀 `7685c`). **`7685c`**: `JSR 491c4`(복귀 `76862`). **`76862`**: WORD `1e(A6)` := WORD `1e(A0)`, `JSR 497a6`(복귀 `7686e`). **`7686e`**(소비자): Clear → `76884`, Set → `76872`.
- **`76872`** / **`76884`**: D0.W := `c54` / `c4e`, D1.B := 0, `JSR 8ebe`(복귀 `76880` / `76892`). **`76880`**: `BRA 76892`. **`76892`**: WORD `20` := `b`, A1 := `76c46`, D0.W := `100`, `JSR 49f8c`(복귀 `768a8`). **`768a8`**: LONG `7e` := `76a1c`, 설치 `768b6`.
- **`768b6`**(설치 값): A0 := LONG `7e`, D0 := 0, D1 := 0, D0.W := WORD `(A0)+`, D1.W := WORD `(A0)+`, 무부호 A0 ≥ `76aa0` → `768f8`, 아니면 `768cc`: LONG `7e` := A0, BYTE `15` bit 0 = 0 → `768dc`, 아니면 `768da`: D0.W := −D0.W. **`768dc`**: SWAP D0, SWAP D1, LONG `2e` := D0, LONG `32` := D1, `JSR 43e34`(복귀 `768ee`). **`768ee`**: `JSR 49fc6`(복귀 `768f4`). **`768f4`**: `BRA 76932`.
- **`768f8`**: `JSR 43e34`(복귀 `768fe`). **`768fe`**: `JSR 49fc6`(복귀 `76904`). **`76904`**: `JSR 49274`(복귀 `7690a`). **`7690a`**: A0 := LONG `c`, BYTE `89(A0)` ≠ 0 → `76926`(WORD `70` := 1, `JMP 70764`), 아니면 `76916`(WORD `70` := 1, `JMP 70674`).
- **`76932`**: `JSR 288c`(복귀 `76938`). **`76938`**(소비자): Set → `76942 RTS`, Clear → `7693c JMP 2a00`.
- **`70674`**: WORD `70` ≠ 0 → `70686`(WORD `9c` := 1), 아니면 `7067c`(WORD `9c` := 0, `BRA 7068c`). **`7068c`**: BYTE `e2` 넣기(A7 −2), BYTE `6a` = 0 → `706fe`, 아니면 `70698`: WORD `9c` ≠ 0 → `706cc`, 아니면 `706a0`.
- **`706a0`** / **`706cc`**: anim(3, `2000d0`, `180`) / anim(`b`, `2000d4`, `1cc`)(복귀 `706c8` / `706f4`). **`706c8`**: `BRA 706f4`. **`706f4`**: LONG `(A6)` := `71884`(쓰기만), `BRA 70760`.
- **`706fe`**: WORD `9c` ≠ 0 → `70732`, 아니면 `70706`. **`70706`** / **`70732`**: anim(3, `2000d0`, `20`) / anim(`b`, `2000d4`, `20`)(복귀 `7072e` / `7075a`). **`7072e`**: `BRA 7075a`. **`7075a`**: LONG `(A6)` := `718c8`(쓰기만; fall-through `70760`). **`70760`**: `BRA 707e2`.
- **`70764`**: WORD `70` ≠ 0 → `70776`(WORD `9c` := 1), 아니면 `7076c`(WORD `9c` := 0, `BRA 7077c`). **`7077c`**: BYTE `10` 넣기, WORD `9c` ≠ 0 → `707b4`, 아니면 `70788`. **`70788`** / **`707b4`**: anim(3, `2000d0`, `28`) / anim(`b`, `2000d4`, `28`)(복귀 `707b0` / `707dc`). **`707b0`**: `BRA 707dc`. **`707dc`**: LONG `(A6)` := `71b04`(쓰기만; fall-through `707e2`).
- **`707e2`**: BYTE `15` bit 3 := 1, WORD `70` ≠ 0 → `707fa`(WORD `9c` := 1), 아니면 `707f0`(WORD `9c` := 0, `BRA 70800`). **`70800`**: `JSR 8ff4`(복귀 `70806`). **`70806`**: WORD `76` := 2, `7a` := `3c`, `78` := `3c`, `7c` := `5a`, `7e` := 0, `80` := 0, BYTE `15` 넣기, `JSR 70418`(복귀 `70832`).
- **`70832`**: D0.B := 꺼낸 BYTE, D0.B &= 1, BYTE `15` := (BYTE `15` & `fe`) | D0.B, BYTE `87` := 꺼낸 BYTE, D0 := `28000`, D1 := `fffccccd`, BYTE `15` bit 0 = 0 → `70860`, 아니면 `7085c`: D0 := −D0, D1 := −D1(LONG). **`70860`**: LONG `64` := D0, LONG `36` := D1, `RTS`.
- **`718c8`**(설치 값): `BSR 702cc`(복귀 `718cc`). **`718cc`**: `JSR 49fc6`(복귀 `718d2`). **`718d2`**: BYTE `15` bit 7 = 0 → `718e8`, 아니면 `718dc`: BYTE `15` bit 3 := 0, LONG `(A6)` := `71d48`(쓰기만). **`718e8`**: `BRA 72dd2`.
- **`702cc`**: D0 := ASR.L 5 (LONG `64` − LONG `36`), LONG `36` += D0, D0 := ASR.L 5 (`fff00000` − LONG `3a`), LONG `3a` += D0, `JMP 4be34`.

## 객체 `70c0c`와 helper `70302` `702f0` `70606`

- **`70c0c`**(설치 값; U13 `70a5c`·N15 `71dcc`·N15 `71d48`이 설치): WORD `9c` ≠ 0 → `70c40`, 아니면 `70c14`. **`70c14`** / **`70c40`**: anim(3, `2000d0`, `c`) / anim(`b`, `2000d4`, `c`)(복귀 `70c3c` / `70c68`). **`70c3c`**: `BRA 70c68`. **`70c68`**: LONG `64` := 0, 설치 `70c76`.
- **`70c76`**(설치 값): BYTE `15` bit 7 = 0 → `71c90`(N15), 아니면 `70c80`: `JSR 4bfa4`(복귀 `70c86`). **`70c86`**: `JSR 49fc6`(복귀 `70c8c`). **`70c8c`**: BYTE `6e` = 3 → `70d10`, 아니면 `70c96`.
- **`70c96`**: D0.W := WORD `8e` − WORD `42`, D1.B := (BYTE `15` bit 0 = 0) ? `ff` : 0, D1.W := sext(D1.B), D1.W ^= D0.W, D0.W의 N = 0 → `70cb2`, 아니면 `70cb0`: D0.W := −D0.W. **`70cb2`**: 무부호 D0.W < `10` → `70cc0`, 아니면 `70cba`: LONG `(A6)` := `70e2a`(쓰기만). **`70cc0`**: D1.W의 N ≠ 0 → `70cd8`, 아니면 `70cc6`: 무부호 D0.W < `30` → `70cd4`, 아니면 `70cce`: LONG `(A6)` := `71032`. **`70cd4`**: `BRA 70cf4`.
- **`70cd8`**: 무부호 D0.W < `30` → `70ce6`, 아니면 `70ce0`: LONG `(A6)` := `71bc0`. **`70ce6`**: 무부호 D0.W < `48` → `70cf4`, 아니면 `70cee`: LONG `(A6)` := `71468`.
- **`70cf4`**: `BSR 7054c`(복귀 `70cf8`). **`70cf8`**(소비자): Clear → `70d02`, Set → `70cfc`: LONG `(A6)` := `71a80`. **`70d02`**: `BSR 705ca`(복귀 `70d06`). **`70d06`**(소비자): Clear → `70d10`, Set → `70d0a`: LONG `(A6)` := `71dd6`. **`70d10`**: `BSR 7028e`(복귀 `70d14`). **`70d14`**(소비자): Clear → `70d1e`, Set → `70d18`: LONG `(A6)` := `72978`. **`70d1e`**: `BSR 70302`(복귀 `70d22`).
- **`70d22`**: A0 := `70d72`, D0.W := 4·D0.W(`ADD.W` 두 번), A0 := LONG `(70d72 + sext(D0.W))`, A0 = 0 → `70d38`, 아니면 `70d36`: LONG `(A6)` := A0. **`70d38`**: BYTE `82` bit 0 ≠ 0 → `70d48`, 아니면 `70d42`: LONG `(A6)` := `70d92`. **`70d48`**: `BSR 70606`(복귀 `70d4c`). **`70d4c`**(소비자): Clear → `70d60`, Set → `70d50`: BYTE `15` bit 3 ≠ 0 → `70d60`, 아니면 `70d5a`: LONG `(A6)` := `72a18`. **`70d60`**: WORD `7c` ≠ 0 → `70d6e`, 아니면 `70d68`: LONG `(A6)` := `72f8a`. **`70d6e`**: `BRA 72dd2`.
- **`70302`**: WORD `78` ≠ 0 → `703f0`, 아니면 `7030a`: BYTE `82` bit 3 = 0 → `703f0`, 아니면 `70314`: BYTE `86`의 N ≠ 0 → `703f0`, 아니면 `7031c`: `BSR 702f0`(복귀 `7031e`). **`7031e`**(소비자): Clear → `703f0`, Set → `70322`.
- **`70322`**: D1.B := BYTE `87`, BYTE `15` bit 7 ≠ 0 → `70334`, 아니면 `70330`: D1.B &= 2. **`70334`**: BYTE `82` bit 6 = 0 → `70364`, 아니면 `7033e`: 옛 D1 bit 1 = 0 → `70364`(bit 1 := 0), 아니면 `70346`: BYTE `82` bit 1 = 0 → `70364`, 아니면 `70350`: WORD D1 넣기, D0.W := `ff`, D2.W := WORD `42`, D3.W := WORD `46`, `BSR 70036`(복귀 `70362`). **`70362`**: D1.W := 꺼낸 WORD. **`70364`**: D1.B = 0 → `703f0`, 아니면 `7036a`.
- **`7036a`**: D0 := 0, D2 := 0, 여덟 번 (D1.B := D1.B + D1.B, X := 옛 bit 7; D0.W := D0.W + D2.W + X), `JSR 49a84`(복귀 `70394`).
- **`70394`**: D1.W := D0.W, D2.B := BYTE `87`, D3 := 0, D0.W := 7, (D2.B += D2.B, X := 옛 bit 7; D1.W := D1.W − D3.W − X, C := 빌림) C → `703f4`, 아니면 `703a8`. **`703a8` `703b2` `703bc` `703c6` `703d0` `703da` `703e4`**: D0.W −= 1, 같은 (`ADD.B D2,D2; SUBX.W D3,D1`) C → `703f4`, 아니면 다음(`703e4` → `703ee`). **`703ee`**: D0.W −= 1(fall-through `703f0`). **`703f0`**: D0 := 0, `RTS`. **`703f4`**: `RTS`.
- **`702f0`**: A0 := `702fa`, `JMP 494c0`.
- **`70606`**: D0.W := WORD `42` − `18`, 무부호 D0.W ≥ `110` → `70624`, 아니면 `70616`: BYTE `86`의 N = 0 → `70624`, 아니면 `7061e`(C Set, `RTS`). **`70624`**: C Clear, `RTS`.

## 객체 `76944`와 자식 생성 `769ac` `769b2` `769f4`

- **`76944`**(`28ae` 자식 값, `769b4`가 생성): D0.W := `c53`, D1.B := 0, `JSR 8ebe`(복귀 `76952`). **`76952`**: WORD `68` `1e` := `8821`, WORD `20` := `b`, A1 := `76c84`, D0.W := `100`, `JSR 49f8c`(복귀 `76974`). **`76974`**: D0 := 0, LONG `36` `3a` := 0, 설치 `76984`.
- **`76984`**(설치 값): D0 := ASR.L 4 (`fffe0000` − LONG `3a`), LONG `3a` += D0, `JSR 43ea4`(복귀 `7699a`). **`7699a`**: `JSR 49fc6`(복귀 `769a0`). **`769a0`**(소비자): Clear → `769aa RTS`, Set → `769a4 JMP 2a00`.
- **`769ac`** / **`769b2`**(LONG 표 `4a720`/`4a724`): D0 := 0 / 1(`769ac`은 `BRA 769b4`). **`769b4`**: BYTE D0.B 넣기, LONG A0 넣기, A0 := `76944`, D0.W := `1e`, `JSR 28ae`(복귀 `769c8`). **`769c8`**: A1 := 꺼낸 LONG, D0.W := WORD `(A1)+`, D1.W := WORD `(A1)+`, BYTE `15` bit 0 = 0 → `769da`, 아니면 `769d8`: D0.W := −D0.W. **`769da`**: `JSR 49214`(복귀 `769e0`). **`769e0`**: `JSR 491b6`(복귀 `769e6`). **`769e6`**: BYTE 꺼내기(A7 +2), 0 → `769f2 RTS`, 아니면 `769ec`: BYTE `15(A0)` bit 0 반전(fall-through `769f2`).
- **`769f4`**(LONG 표 `4a728`): BYTE `61` bit 3 := 1, `RTS`.

## 객체 `dd574`, `bc844`, helper `4c2cc`

- **`dd574`**(U01 `dd546` 설치 값): A1 := `10b1d6`, LONG `8(A1)` := `fffa0000`, LONG `c(A1)` := `fffa0000`, A1 := `10d256`, LONG `8(A1)` := `ffffa000`, LONG `c(A1)` := 0, 설치 `dd5a6`. **`dd5c6` `dd618` `dd66a`**: 같은 꼴(LONG `c(10b1d6)` = 0 / `fffa0000` / 0), 설치 `dd5f8` / `dd64a` / `dd69c`.
- **`dd5a6` `dd5f8` `dd64a`**(설치 값): D0 := LONG `76` + `60000`, 무부호 D0 < `8b00000` / `14900000` / `15900000` → `dd5c0` / `dd612` / `dd664`, 아니면 `dd5ba` / `dd60c` / `dd65e`: LONG `(A6)` := `dd5c6` / `dd618` / `dd66a`(쓰기만). **`dd5c0` `dd612` `dd664`**: LONG `76` := D0, `RTS`. **`dd69c`**: D0 := LONG `76` + `60000`(`CMPI.L #1e000000`의 flag는 읽지 않음), LONG `76` := D0, `RTS`.
- **`bc844`**(FR1c `28ae` 자식 값): BYTE `15` bit 0 := 1, D0.W := `4f`, D1.W := 7, D2.B := 0, `JSR c6a96`(복귀 `bc85c`). **`bc85c`**: anim(`e3`, `200140`, `1c`)(복귀 `bc884`). **`bc884`**: WORD `68` `1e` := `8800`, LONG `36` `64` := `30000`, LONG `3a` := 0, D0.W := 8, WORD `76` := 8, 설치 `bc8b6`.
- **`bc8b6`**(설치 값): BYTE `15` bit 7 = 0 → `bc8ca`(`JSR 4bfa4`, 복귀 `bc8d0`), 아니면 `bc8c0`(`JSR 4be2c`, 복귀 `bc8c6`: `BRA bc8d0`). **`bc8d0`**: A0 := LONG `c`, BYTE `62(A0)` = 0 → `bc8ea`, 아니면 `bc8dc`: WORD `76` −= 1, 옛 WORD ≠ 0 → `bc8ea`, 아니면 `bc8e4`: LONG `(A6)` := `bc8f2`(쓰기만). **`bc8ea`**: `JSR 49fc6`(복귀 `bc8f0 RTS`).
- **`bc8f2`**(설치 값): BYTE `62` := `ff`, anim(`e3`, `200140`, `8c`)(복귀 `bc91e`). **`bc91e`**: 설치 `bc924`. **`bc924`**: `JSR 43e34`(복귀 `bc92a`). **`bc92a`**: `JSR 49fc6`(복귀 `bc930`). **`bc930`**(소비자): Clear → `bc93a RTS`, Set → `bc934`: LONG `(A6)` := `bc93c`(쓰기만; fall-through `bc93a`).
- **`4c2cc`**: `JSR 4bc44`(복귀 `4c2d0`). **`4c2d0`**: D2 := 0, D3 := 0, D3.W := D0.W, SWAP D3, D0 := LONG `2e`, D1 := LONG `32`, A0 := LONG `3e`, `JSR 46d72`(복귀 `4c2e8`). **`4c2e8`**(소비자): Set → `4c2ee`, Clear → `4c2ec`(C를 넘기는 `RTS`). **`4c2ee`**: SWAP D6, D0.W := D6.W, D0.W := −D0.W, C Set, `RTS`.

## 자료 표(전사, routing 밖으로 둠)

[F] 원본 바이트 그대로다. 실행부는 표 내용을 코드에 넣지 않고 live bus로 읽는다.

| 표 | 범위 | 읽는 곳 | 내용 |
| --- | --- | --- | --- |
| 상태 LONG | `70d72..70d92`(8 LONG, SHA256 `5f730967c50f9d50b76cf9bf7990d17a077792b76b617e5148b9fa6cd8307476`) | `70d22`(index 4·D0.W, D0.W = `70302`의 남은 bit 번호 0..7 [I]) | `00000000 00071502 00071562 000715c2 00071622 000716ca 000716ca 000716ca`(0 = 설치 없음) |
| WORD 쌍 목록 | `76a1c..76aa0`(33 쌍, SHA256 `7b077b21de7ec40177d2f1c8821bf38508f5d54277dc7208474307d6c34872a0`) | `768b6`(LONG `7e` 위치, 끝 `76aa0` 비교) | 예 `003c fff8` `003b fff4` …(속도 쌍) |
| LONG 자식 처리기 | `4a720..4a72c` | 밖의 `JSR (An)`(routing 밖) | `769ac` `769b2` `769f4` |
| bank LONG | CPU `2000d0` `2000d4` `200140` `20017c` | anim 꼴(`LONG d(…)`) | 물리 `200000` bank 값은 V1·실제 ROM 차분이 원본으로 읽는다(단위 시험은 합성). [U] 물리 `300000` bank에서의 쓰임 |

- [F] **callee에게 넘기기만 하는 자료**: `49f8c`의 A1(`76c46` `76c84`, bank 창 LONG), `28ae` 자식 `76944`(`769b4`), `8ebe` `c6a96` `49290` `491c4` `49214` `491b6` `70036` `494c0`(A0 = `702fa`) `46d72` `4bc44`의 D0..D7/A0.

## 경계·routing 밖 출구

- [F] 이 단위 안에는 live 대상 호출·TRAP·계산 점프가 없다. 설치 쓰기의 routing 밖 값(결정 2)은 실행하지 않는다.
- [F] routing된 출구·callee: "요약"의 목록. `RTS`로 끝나는 block 24개: `bb6` `9ef2` `a8ec` `a938` `a950` `48256` `4c2ec` `4c2ee` `703f0` `703f4` `7061e` `70624` `70860` `76942` `769aa` `769f2` `769f4` `b33d6` `bc8f0` `bc93a` `dd5c0` `dd612` `dd664` `dd69c`.
- [F] **native 정지 규칙 주의**(V1): FR2 spec의 `first_unrouted`(`8c16 < pc <= 8ca6` 내부, 정지 `2a00` `2a24`, 홀수 live 정지 PC 버림)를 그대로 쓴다. 이 단위의 출구 중 C++가 한 block으로 처리하는 잎은 없다(scratch `leafscan.py`).

## seed·fixture

- 자연 부모 seed 116/117(N28 객체 `2b99c`, FR1·FR2 spec과 같은 `BASE_CALLBACKS`). V1 기반 world: seed 116/117 frame 2의 자연 node(A6)에 선언 편집(레지스터, node field, A0 := 자연 node, LONG `c(A6)` := 자연 node, LONG `7e(A6)` := 목록 `76a1c..76a9c`의 위치, LONG `3e(A6)` := 자연 node, 스택 BYTE/WORD/LONG, PC).
- [I] IO 관측 상태가 이 단위의 실제 진입 상태다(`fr2/ioA/frontier.json`의 확정 frontier). V1 spec에는 이 출처를 주석으로 적고, IO 비교 재실행(검증 작업자)이 자연 경로를 직접 확인한다.
- 사슬(chain) fixture: 소비자를 실제 생산자로 들어간다 — `494c0`(`702f0`) → `7031e`(`7031c`), `497a6` → `7686e`(`76862`), `288c` → `76938`(`76932`), `49fc6` → `769a0`(`7699a`)·`bc930`(`bc92a`), N15 `7054c` → `70cf8`(`70cf4`), `705ca` → `70d06`(`70d02`), `7028e` → `70d14`(`70d10`), 이 단위 `70606` → `70d4c`(`70d48`), U12 `46d72` → `4c2e8`(`4c2d0`; 단위 시험은 합성 RAM으로, V1은 실제 사슬), `4c2ec` 통과(`4c2cc`).
- node fixture: callback·설치 값(`76852` `768b6` `718c8` `70c0c` `70c76` `76944` `76984` `b336a` `b33bc` `dd574` `dd5a6` `dd5c6` `dd5f8` `dd618` `dd64a` `dd66a` `dd69c` `bc844` `bc8b6` `bc8f2` `bc924`)을 dispatcher 복귀나 첫 routing 밖 PC까지 실행한다.
- callee fixture: `48256` `a92a` `a8d0` `a8dc` `9ef2` `bb6` `70302` `70606` `702cc` `702f0` `769ac` `769b2` `769f4` `4c2cc`를 subroutine으로(복귀 LONG = sentinel) 들어간다. `70674` `70764`는 node 진입(LONG(A6) = `76852` 꼴)으로도 들어간다.
- 단위 시험(Unicorn 생성기, FR2 꼴): 시작 214개 × 들어오는 C 3가지, zero-step, 내부 PC 1,017개 정확한 오류, 경계 stop(출구 전부), rollback 탐침 `10fe00..10fefe`, 오류 fixture마다 실패 PC(실패 block 바로 뒤를 run stop으로), 부호·영 확장 경계(`70c96` WORD 부호 `8000`/`7fff`·`EXT.W`, `70cb2`/`70cc6`/`70ce6` 무부호 `f`/`10`/`2f`/`30`/`47`/`48`, `70606` `17`/`18`/`127`/`128`, `768b6` `NEG.W` 뒤 `SWAP`, `76984`/`702cc` `ASR.L`의 부호 bit, `dd5a6..` LONG `8afffff`/`8b00000`/`ffffffff`, `70d22` 음수 WORD 색인(`8000`) — 합성 ROM 위치로, `7036a` X 사슬(`ff`/`80`/`01`), `70394..` `SUBX`(D1.W = 0·X = 1), `4c2ee` 상위 WORD, `769c8`/`769e6` 꺼낸 레지스터·BYTE, `70832` 꺼낸 두 BYTE 순서).

## 영향받는 기존 시험·검증기

- [F] 16진 상수 전수 검색(scratch `tools/probe_scan_b.py`, `engine/tests` `engine/tools` `tools/unit_fixture_specs` `tools/*.py`, `probe_b.out` 61줄)으로 확인한 결과:
  - 그대로 참인 것(stop-only·레지스터 값·자기 범위 끝·`!in_ranges`만): U02(`rom_outside[]`의 `48256`, `e5286` 행 stop), U07(`rom_outside[]`, `st3-out` 행 stop `48256`), U06b(`rom_outside[]` `48256` `48258`: `ok || error != U06b 문자열`), U09(`rom_outside[]` `76852` `76854`), N15(`711e2` 등 stop `70302`, `at_pc[]`, 합성 자료 `70d6a..`: N15 `711e6`도 표 `70d72`를 읽는 자기 시험 자료), U12(`704ac`/`70496` 행 stop `4c2cc`), FR1b(`b319e` 행 A0 = `b336a`, `RANGES` 끝 `b336a`), FR1c(`bc15c` … 행 A0 = `bc844`), frame_head_h1 `RANGES` 끝 `bb6`, FR2 시험 `RANGES` 끝 `9ef2`, B4·U11·motion_walk의 같은 값(레지스터·RAM 값), `tools/verify_stage_catalog.py`(별도 C++ `stage_state` 도구; routing과 무관), 관측기 `observe_animation_machine_objects_g1.py`의 고정 경계 표(pin된 역사 기록).
  - **옮길 것(결정 6, 이전 기대값 기록):**
    - `engine/tests/animation_machine_objects_u01_test.cpp` `boundaries()`: `dd512-far` 실행 뒤 callback `dd574`로 `reject(... "unsupported animation machine PC")`(이전 기대). FR2b 시작이 됐으므로 stop = `dd574`의 stop-only 확인(바로 멈춤, 상태 그대로)으로 바꾼다.
    - `engine/tests/animation_machine_objects_fr1b_test.cpp` `rules()`의 범위 옆 자료 PC 목록: `b336a`(이전 기대: `unsupported animation machine PC`)를 RAM `10fe6a`로 바꾼다.
    - `engine/tests/animation_machine_objects_u02_test.cpp` `boundaries()`: `e5286`(`JSR 48256`) 행을 rollback 목록에서 뺀다(이전 기대: `unsupported animation machine PC`; 이제 `48256 RTS` → `e528c JMP 2a00` → routing된 `2a00`이 이 시험의 합성 ROM에 없는 vector를 읽어 다른 오류). 그 success 행의 stop `48256`(stop-only)은 그대로다.
    - `engine/tests/animation_machine_objects_u07_test.cpp` `boundaries()`: `e5ba6-c1` `e5ba6-c2` `st3-out` `st3-out-max`(stop `48256`)의 rollback 기대(이전: `unsupported animation machine PC`)를 stop-only 확인(최종 PC·fixture stop = `48256`)으로 바꾼다.
  - [I] V1 spec 중 native 사슬이 `48256` `76852` `b336a` `bc844` `dd574` `70c0c` `70302` `4c2cc`를 첫 routing 밖 PC로 멈추던 것은 더 진행한다(정지는 routing에서 계산되므로 spec 수정은 필요 없을 것으로 본다; 검증 작업자가 회귀로 확인). 계산 점프 guard 행(stage_event `e97d8` 꼴): routing된 `JMP d(PC,Dn)` 중 이 단위 범위 근처의 것(`cf6e`…`1a2c2`, `39e76`…`4a01e`, `862a0`, `b3dc8` `b3fca`, `e74fc`…`e97e0`)은 모두 자기 근처 `BRA` 표를 가리키고 이 단위 범위에 닿는 전사 대상은 없다(`make test`로 확인).
- [F] stage_event / stage_event_ops 검증기의 `CPP_PINS`(`animation_machine.cpp` `eadc97b0…`, `animation_machine_internal.h` `522199f9…`)는 이 단위의 공유 수정으로 맞지 않게 된다(FR1 `2f74353`·FR2a 관례대로 새 값으로 갱신 필요; 메인 결정).

## 결정

1. **범위.** FR2b = 메인이 정한 네 root(`48256` 1, `76852` 묶음 62, `b336a` 8, `a92a` 12) + IO 관측이 같은 run에서 곧바로 실행한다고 보여 준 후속(`70c0c` 72, `76944`·`769ac`·`769b2`·`769f4` 19, `4c2cc` 5, `a8d0` 2, `dd574` 14) + `bc844` 첫 설치 단계 19 = **214**. 정지 설치 값 `71884`(433 block 꼬리) `70d92` `70e2a` `71468` `72978` `72f8a` `bc93c`. 메인이 예로 든 `bc844`+`e6952`(212)는 네 root와 합쳐 289, `50dae`(211)·`5ab82`(202)도 약 230을 넘는다. 자연 후속을 고른 근거는 run 기록의 `cbs`·`unr_new`다([I] 예상 +6,355 frame 중 `48256` 3,300, `b336a` 1,440은 각 1·22 block이 연다). 메인이 다른 조합을 원하면 다시 잰다.
2. **설치 값 정지.** `MOVE.L #v,(A6)`(그리고 `70d36 MOVE.L A0,(A6)`의 표 값)은 v가 바로 다음 PC일 때만 그 block으로 들어간다(`ofr2b_install`). 나머지는 LONG 쓰기뿐이고 정지 값은 다음 frame의 callback이므로 이 단위가 실행하지 않는다.
3. **carry 보존 목록.** 소비자 10개 + `4c2ec`(Clear를 U12 `70502`와 밖 5곳의 `BCC`로). `7061e` `70624` `4c2ee`는 자기 block에서 C를 정한다. `703f0` `703f4` 등 읽는 곳이 없는 known C는 넣지 않는다(FR1c 결정 5 관례).
4. **X 사슬.** `ADD.B`의 X와 `ADDX.W`/`SUBX.W`는 같은 block 안에서 명시 계산한다(block 경계를 넘는 X 없음). `SUBX`의 C는 무부호 빌림(D3.W + X > D1.W)이고 바로 다음 `BCS`만 읽는다.
5. **`4c2cc`의 위치.** 옛 F4 범위 표 U38 행(`4b8e4..4c38c`) 안이지만 이 PC는 지금 routing 밖이고(U12가 경계 callee로 둠) 남은 F4 단위 중 이것을 범위로 가진 것은 없다(FR1c 결정 2와 같은 확인). `4c2c4`(형제 진입, `BRA.W 4c2d0`)는 IO에서 실행되지 않아 넣지 않는다(`4c2d0`은 이미 block 시작).
6. **숨은 탐침 이전.** U01 시험 `dd574` rollback → stop-only, FR1b 시험 `b336a` → RAM `10fe6a`, U02 시험 `e5286`·U07 시험 `e5ba6`/`st3-out` 계열의 `48256` 너머 rollback → stop-only(`make test`가 찾음). stage_event / stage_event_ops `CPP_PINS` 갱신은 메인이 정한다.
7. **FR2 계획 재배열.** FR2 계약 "FR2b 이후 명세"를 이 단위 기준으로 고친다(FR2c `4e68e` helper, FR2d/FR2e `4e68e` 본체, FR2f `bc93c` 나머지 + `e6952`, …). 이 단위 다음 자연 frontier: `c5370`(76852 run frame 252, 82 block), `bc93c`(bc844 run frame 276), `bc404`(frame 301, 10 block), `ca50`(boot-title-start frame 122, FR2c).

## 미확인

- [U] node field 의미(BYTE `15` `61` `62` `6a` `6e` `82` `86` `87` `89`, WORD `1e` `20` `42` `46` `68` `70` `76`..`80` `86` `8e` `9c`, LONG `2e` `32` `36` `3a` `3e` `64` `76` `7e`), 표 `70d72`·목록 `76a1c` 값의 의미, RAM `10b1d6`/`10d256` 기록·BYTE `100bad` `10d681` `100014` `107f1a`의 정체.
- [U] `70d22`의 D0.W가 항상 0..7인지(원본에 상한 검사 없음; `70302`의 경로상 그렇다 [I]).
- [U] 물리 `300000` bank에서 bank 창 LONG의 쓰임.
- [U] 자연 frame에서 이 단위 뒤 다음 첫 미routing PC(IO 비교 재실행으로 확인; [I] 예상은 결정 7).

## 구현·검증 기록(작업자)

- 파일: `engine/src/animation_machine_objects_fr2b.cpp`(case label 214 = scratch `starts_b.txt`와 집합 일치, scratch 검사), `engine/tests/animation_machine_objects_fr2b_test.cpp`(생성 구역 + 수작성 규칙: `48256` BYTE 올림·부호 확장 변위, `9ef2` `-e6(A5)`, `bb6 OR.B`, `7033e` 레지스터 `BCLR`, `7036a` `ADDX` bit 세기(D0 상위 0, D1 상위 유지), `70394..` `SUBX` 사슬(세 번째 켜진 bit = 2, 첫 bit 빌림), `703a8` `SUBX` 빌림 세 경우, `70d22` 음수 WORD 색인(합성 위치 `68d72`; 0 확장이면 `78d72`라 오류)·0 항목, `70c96` `SEQ`/`EXT`/`EOR`, `702cc`/`76984` `ASR.L` 부호 bit, `768b6` 목록 끝(무부호 `CMPA.L`, 상위 0), `769b4` push 순서, `769c8` 꺼낸 A1, `769e6` 꺼낸 BYTE(WORD 칸 높은 쪽), `70832` 두 BYTE pop 순서와 `NEG.L`, `4c2d0` `MOVEM` 순서·D3 0 확장, `4c2ee` `SWAP`/`NEG.W`, `70606` 무부호 비교, `dd5a6` 무부호 LONG 한계·`fffa0000` wrap, `b33c8` 빌림, `7690a` 부모 BYTE `89`, 범위 옆 자료 PC `702fa` `70d72` `76922`의 dispatcher 오류), `tools/generate_animation_machine_objects_fr2b_test_table.py`(생성기; 두 번 실행해 시험 파일 바이트 단위 같음, 약 4분), `tools/unit_fixture_specs/fr2b.py`(V1 spec; 정적 검사만 함 — `load_routing` 규칙 123개 뒤 시작 214개와 내부 1,017개가 모두 `animation_objects_fr2b_block`, sentinel·자료 PC는 routing 밖, 정적 후속은 시작이거나 routing된 출구, 사슬 10개와 통과 사슬 1개의 소비자가 진입에서 닿음; 합성 기반 상태와 가짜 tracer로 world·hint·error·chain/node/callee 생성 함수를 native 없이 실행해 Python 오류 0, 오류 fixture 1,040개 이름 중복 0). 공유 수정은 "공통 규칙"의 다섯 곳과 "영향받는 기존 시험"의 이전 네 곳뿐이다.
- [F] 단위 시험 world: A7 = `10ef00`, 합성 typed physical byte(ROM 자료 아님, 자료 영역만): 상태 표 `70d72..70d92`(0과 RAM 탐침 값), 목록 `76a1c..76aa0`(경계 WORD 포함), 상자 `702fa..70302`(폭·높이 `8000`), bank 창 `2000d0`(→ `2a1000`) `2000d4`(→ `2a2000`) `200140`(→ `2a3000`) `20017c`(→ `2a4000`)와 그 뒤 LONG. 실제 생산자 사슬은 RAM만 읽는 생산자로 두 C 값을 모두 만든다: `494c0`(`49370` `4941e` `49462`, 상자 `702fa`) → `7031e`, `497a6` → `7686e`, `288c` → `76938`, `7054c` → `70cf8`, `705ca`(`4bc04` RAM 표 `5b88(A5)`) → `70d06`, `70606` → `70d4c`. `49fc6`(ROM script)·`7028e`(Set은 `4ae4a`)·`46d72`(지형 자료)를 생산자로 갖는 `769a0` `bc930` `70d14` `4c2e8`은 선언 C 행만 있다(V1·실제 ROM 차분이 실제 사슬). 통과 `RTS` `4c2ec`는 복귀 LONG `7686e`로 선언 C를 넘겨 그 분기로 확인한다. path 행은 소비자 PC에서 멈출 수 있다(`70d22`/`70d38` → `70606` → `70d4c`: `7061e`/`70624`가 정한 C를 행의 모형 C로 확인).
- [F] `make -j3 all test`(작업자, scratch `make_all2.log`): 종료 0, 경고 0, Assert 줄 0, 시험 실행 275개, Python 310개 통과, `ANIMATION_MACHINE_SOURCES`·`_HEADERS` 각 1줄. FR2b 시험 줄: `animation machine objects fr2b: 740 fixtures (522 single-block, 135 path, 36 producer chain, 22 declared C, 25 checked error (6 with a later failing PC), 75 kept C), 214 blocks, 4065 calls, 111967 checks`. FR2a 기준(scratch `../fr2/make_all5.log`) 대비 다른 시험 줄 변화는 u02 `1614` → `1613 calls`, u07 `1060` → `1056 calls`(위 이전)뿐이다. 첫 실행(`make_all1.log`)은 u02(`e5286`)·u07(`e5ba6` 계열)의 `48256` 너머 rollback 기대에서 멈췄고 이전 뒤 통과했다. 단일 block 표에서 모든 조건 분기의 두 쪽을 들어갔고(생성기 `branch blocks with a missing successor []`), 출구 32개 + STOP이 모두 어떤 행의 stop이다.
- [F] 검증 작업자 준비물(scratch, 실행하지 않음): `build_ubsan.sh`, `mut/run_mut.py`·`mut/mutants.py`(변이 193개; 패턴 유일성 확인, `--check`는 문법 검사까지 통과), `realrom/real_fr2b.py`(FR2a harness에 FR2b world·소비자·진입; `py_compile`만), `runwrap.py` `run_frames.sh` `run_area_clear.py` `run_stage_entry.py` `run_regs.sh` `v1_all.sh` `v1_one.sh` `io_ab.sh` `legacy/`(경로만 바꿈, frame·V1 명령마다 `MS5_SEED_DIR=artifacts/stage_entry_body`). 실행 순서와 기대값은 scratch `HANDOFF.md`.

## 검증 기록(검증 작업자, Claude Sonnet 5.5 / medium)

- [F] 환경: 저장소 `b4a7e21` + 미커밋 FR2b, ROM SHA256 `29112a94…` 불변, 모든 frame·V1·legacy 명령은 `MS5_SEED_DIR=artifacts/stage_entry_body`, 공유 `artifacts/`에는 쓰지 않았다(출력은 scratch `ms5-scratch/fr2b/`).
- [F] 빌드: `make -j3 all test` 종료 0, 경고 0, Assert 0. 첫 실행의 FR2b 줄은 `740 fixtures … 4065 calls, 111967 checks`였고, 변이 생존 7개를 닫은 뒤(아래) `774 fixtures (555 single-block, 136 path, 36 producer chain, 22 declared C, 25 checked error (6 with a later failing PC), 75 kept C), 214 blocks, 4200 calls, 117982 checks`. FR2a 기준 대비 다른 시험 줄은 u02 `1614→1613`, u07 `1060→1056` calls뿐이다. 생성기는 두 번 실행해도 시험 파일 SHA가 같다.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`): 종료 0, `runtime error` 0(수정 전·후 모두).
- [F] 변이: 처음 193개 중 186 killed, 생존 7개 — `bchg-as-bset`(769ec의 BCHG 비트가 항상 0이던 입력), `subx-d3-long`(D3 상위 WORD 입력 없음), `9ef2-zext` `48256-zext`(`A5 = 108000`에서는 `ff1a`/`8bad` 영 확장이 작업 RAM 64KiB 거울이라 같은 주소: 거울 위쪽 `A5 = 1f8000` 규칙 필요), `7068c-word`(BYTE 대신 WORD 읽기: `6a`가 0이고 `6b`만 0이 아닌 입력 없음), `70c76-bit6`(bit 7 대신 6: 둘 중 하나만 켜진 `15` 입력 없음), `76974-only-3a`(`36`이 쓰기 전용이라 이미 0). 모두 시험 빈틈이며 동등 변이는 없다. 생성기 `hints()`에 행을 더하고(`7068c` WORD `6a`, `70c76` `15`, `76974` `36`/`3a`, `769ec` `A0` 대상 `15`, `703a8` 계열 D3 상위 WORD) 시험 `rules()`에 `9ef2`·`48256` 거울 규칙 2개를 넣은 뒤 **193 중 193 killed**.
- [F] 실제 ROM 차분(Unicorn 대 C++, 8개 `program_rom_*.ms5d`, 5 × 1,500 = 7,500 사례, seeds s1 s2 s3 plain + f4 f5 FOLLOW_ANIM): 모든 batch `mismatches 0`; 시작 214/214가 s1·s2·f4에서 모두 덮이고 s3는 `768a8`, f5는 `4c2ee`가 빠지나 다른 batch가 덮는다; 소비자 16곳이 실제 생산자 뒤 native 분기와 비교됐다. harness 수정 없음.
- [F] V1 `fr2b` 두 번: 1,761 fixture(match 715, error 1,036, mismatch 10) 모두 ok, `[(name,digest)]` 동일. `fr2b: carry oracle ok`, visited 214/214, 누락 후속 `70d14 → 70d18` 1개(`70d14` Set 출구는 지형 자료가 필요한 `46d72` 생산자 쪽이라 이 spec의 native 사슬이 만들지 못함 [I]), 미도달 결과 같은 1개. 그 외 모든 spec 실패 0(통과 fixture 수: fr2 1,592 fr1 1,631 fr1b 1,441 fr1c 1,755 b2a 1,386 b4 1,830 b4b 1,723 b1a 2,807 b1b 1,892 b1c 1,842 b2b 1,419 b2c 1,707 b2d 1,485 b2e 1,054 b3a 1,468 b3b 1,360 b3c 625 c1 1,741 c2 1,607 c3b 480 d9 26 f6a 320 f6b 726 f6c 1,538), FR2a 기준과 같다.
- [F] 이전한 기존 expectation의 회귀 검증: scratch root에서 `stage_entry`(cases 335, split 23,761, negatives 2,757, carry 21,829/100/1,832), `area_clear`(conditions 256, frames 37,418, split 117,537, continuous 37,444, negatives 181, guards 26), `frame_helpers`(cases 199, split 3,683, negatives 180) 통과. `stage_event`·`stage_event_ops`는 `CPP_PINS` 새 값 `animation_machine.cpp` `4fc41a76…`, `animation_machine_internal.h` `142f253e…`로 갱신(이전 값을 주석에 기록) 뒤 통과(stage_event typed 560, phases 22,870, negatives 1,020; ops typed 284, phases 5,081, negatives 894).
- [U] 실행하지 못한 legacy 검증: `verify_animation_machine_card_menu_close`는 scratch root에서 두 번(10분·20분) 실행했으나 출력이 2.3 GiB 이상이라 작업 디스크(여유 약 3 GiB, 다른 작업과 공유)가 가득 차 `OSError: [Errno 28]`로 중단했다(단언 실패 아님; 중단 전 어떤 비교도 실패하지 않았음). `verify_animation_machine_objects_g1`은 4,752행 중 4,701행까지 `execution-equal`/`checked-boundary`/`native-step-limit`만 나온 뒤 `contract_coverage`가 `docs/analysis/animation-machine-objects-u06b-contract.md`에서 `'## block 목록'`을 찾지 못해 `ValueError`(FR2b와 무관한 기존 문제: 그 글로브 `objects-u*-contract.md`가 `u06b` 문서도 잡는다 [I]). 이 둘은 디스크 여유가 충분한 곳에서 다시 돌려야 한다.
- [F] frame 회귀: D1 54,400/54,400, controller game 54,400/54,400, IRQ 54,400/54,400, demo 45,684/45,684, natural mismatch 0, 변한 frame 없음(FR2a 기준과 로그가 순서 외에 같다).
- [F] IO 비교(`io_ab.sh`, 두 번 동일: `verification.json` SHA `e4ab37a1dfc522080afd36a0629c662458d1aca93f0a9d6dcf93bfb5f2fba7b7`, `frontier.json` SHA `2aeb3d7434511dad69bc08c26e9e4825139f457b4a0c738b77b862fe5a4b0bfd`, `routing_file_sha256` `4fc41a76…`): 비교 173,966 frame, **일치 158,202**, mismatch 0, 예기치 않은 C++ 오류 0, chain 분기 0, frontier run 53 → **37**(+ 기존 guard 두 fixture).

| 설정 | FR2a 기준 | FR2b | 차 |
|---|---|---|---|
| P0 | 81,600 | 81,600 | 0 |
| P1 | 63,840 | 69,252 | +5,412 |
| P1b | 5,031 | 5,964 | +933 |
| boot-demo-0 | 381 | 381 | 0 |
| boot-title-idle | 600 | 600 | 0 |
| boot-title-start | 117 | 122 | +5 |
| fixtures | 279 | 283 | +4 (fx-start-c79a) |
| 합계 | 151,848 | 158,202 | **+6,354**(예측 +6,355) |

- [F] 새 frontier(첫 routing 밖 PC, run 수, frame): `4e68e` 15(P1/P1b frame 2·222, boot-title-start frame 122), `c5370` 12(frame 252), `5ab82` 3(frame 141), `bc93c` 3(frame 276), `50dae` 3(frame 271), 그리고 기존 guard fixture 쪽 `2634` 2(fx-c-input-read / fx-n-input-read, frame 3), `1d1f4` 1(boot-demo-0, frame 381). 사라진 frontier: `48256`(12) `76852`(12) `b336a`(3) `bc844`(3) `a92a`(2 = boot-title-start과 fx-start-c79a). [I] 예상 `ca50`은 나타나지 않았다: boot-title-start은 frame 122에서 `4e68e`로 멈춘다(`ca50`보다 `4e68e`가 먼저 첫 routing 밖 PC가 된 이유는 추적하지 않았다 [U]).

## block 목록

[F] scratch `starts_b.txt`(SHA256 `03dc3024660d84a18120b4de31989cf63fddda710e7ec6a41af10a239e7f9b71`)와 같다.

- **`bb6..bbe`(1)**: `bb6`
- **`9ef2..9ef8`(1)**: `9ef2`
- **`a8d0..a8ee`(5)**: `a8d0 a8d4 a8dc a8e4 a8ec`
- **`a92a..a952`(7)**: `a92a a92e a930 a938 a93a a94a a950`
- **`48256..48262`(1)**: `48256`
- **`4c2cc..4c2fa`(5)**: `4c2cc 4c2d0 4c2e8 4c2ec 4c2ee`
- **`702cc..702fa`(2)**: `702cc 702f0`
- **`70302..703f6`(25)**: `70302 7030a 70314 7031c 7031e 70322 70330 70334 7033e 70346 70350 70362 70364 7036a 70394 703a8 703b2 703bc 703c6 703d0 703da 703e4 703ee 703f0 703f4`
- **`70606..7062a`(4)**: `70606 70616 7061e 70624`
- **`70674..7086a`(31)**: `70674 7067c 70686 7068c 70698 706a0 706c8 706cc 706f4 706fe 70706 7072e 70732 7075a 70760 70764 7076c 70776 7077c 70788 707b0 707b4 707dc 707e2 707f0 707fa 70800 70806 70832 7085c 70860`
- **`70c0c..70d72`(42)**: `70c0c 70c14 70c3c 70c40 70c68 70c76 70c80 70c86 70c8c 70c96 70cb0 70cb2 70cba 70cc0 70cc6 70cce 70cd4 70cd8 70ce0 70ce6 70cee 70cf4 70cf8 70cfc 70d02 70d06 70d0a 70d10 70d14 70d18 70d1e 70d22 70d36 70d38 70d42 70d48 70d4c 70d50 70d5a 70d60 70d68 70d6e`
- **`718c8..718ec`(5)**: `718c8 718cc 718d2 718dc 718e8`
- **`76852..76922`(20)**: `76852 7685c 76862 7686e 76872 76880 76884 76892 768a8 768b6 768cc 768da 768dc 768ee 768f4 768f8 768fe 76904 7690a 76916`
- **`76926..769fc`(24)**: `76926 76932 76938 7693c 76942 76944 76952 76974 76984 7699a 769a0 769a4 769aa 769ac 769b2 769b4 769c8 769d8 769da 769e0 769e6 769ec 769f2 769f4`
- **`b336a..b33d8`(8)**: `b336a b3388 b33b0 b33bc b33c2 b33c8 b33d0 b33d6`
- **`bc844..bc93c`(19)**: `bc844 bc85c bc884 bc8b6 bc8c0 bc8c6 bc8ca bc8d0 bc8dc bc8e4 bc8ea bc8f0 bc8f2 bc91e bc924 bc92a bc930 bc934 bc93a`
- **`dd574..dd6b2`(14)**: `dd574 dd5a6 dd5ba dd5c0 dd5c6 dd5f8 dd60c dd612 dd618 dd64a dd65e dd664 dd66a dd69c`
