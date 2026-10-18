# 입력·스테이지 진행 관측(단위 IO-1) 관측기 기록

**상태: 구현·관측 기록(IO-1 관측기). C++ 비교와 frontier 보고는 IO-2의 몫이다.**

- 범위·결정: `docs/analysis/input-stage-progress-observation-scope.md`(이하 범위 문서, 메인 결정 포함). 이 문서는 범위 문서 §8의 "IO-1 관측기" 하위 작업의 구현·결과·검증 기록이다.
- 작성: Sonnet 5.5 / high 작업자. 작업 트리 `metalslug-io`(브랜치 `claude/input-observation`, 기준 HEAD `836035f`), 커밋하지 않았다.
- 도구: `tools/observe_animation_machine_io.py`(관측기, SHA256 `c9f93abd75303ecd6eb4b5379fc9ec7514adc67de1ff3e7a389882d3a499e2c6`), `docs/analysis/data/io-input-scripts.json`(버전 있는 입력 스크립트·선언 host 쓰기·구성, SHA256 `d8971c44441bca01705de85467edda166523c9a5d9181175e2ac5d8850ab322a`).
- 표기: [F] 이 도구가 원본 ROM을 native로 실행해 확인한 사실, [I] 추론, [U] 미확인.
- 모든 관측은 선언 모델이다. BIOS 실행, 자연 IRQ 시점, 자연 scheduler를 주장하지 않는다. host 쓰기, 장치 값, IRQ 전달, BIOS 반환, 재진입은 모두 선언이고 기록에 남는다.
- 원본 ROM과 추출 자료는 수정하지 않았고 Git에 넣지 않는다. 관측 산출물(`runs/`, `states/`, `boot/`)도 Git 대상이 아니다. 저장소 도구·엔진은 수정하지 않았다(관측기는 기존 도구를 프로세스 안에서 import만 한다).

## 1. 요약

- 관측기와 입력 스크립트를 범위 문서 §8대로 구현했다. 구성은 S `P0`/`P1`(자연 seed 137개 × 600 frame; case 141은 frame 0 `odd-pc`), `P1b`(동치류 대표 14개), B `boot-demo-0`/`boot-title-start`/`boot-title-idle`이다.
- IO-1 탐침 재현: P0 완료 136 + case 141 `odd-pc`, 모두 `c7fc`→`c79a`, 새 미routing 없음(`3900` 제외). P1 완료 136 + case 141, 플레이어 seed 12개, 새 미routing PC **1864**개. 탐침과 seed별 정지·첫 미routing·미routing PC별 횟수가 일치한다(§7).
- B: demo는 frame 577 `rom-write`, title-start는 frame 906 `system-return`(BIOS `c00444`), title-idle은 600 frame 완주이다(IO-1과 같은 지점).
- 반복 실행 두 디렉터리의 `compared_sha256`: 3cc9adbb2692267e (A) / 3cc9adbb2692267e (B) — 같다. split 대 continuous: 19개 실행 모두 일치(§9).
- 출력 93.9 MB(상한 3 GB). 자연 실행의 입력 소비 순서 위반 0. guard(자연 2 + 합성 5) 7/7 일치.
- 범위 문서와 다른 점 두 가지: replay mode의 입력 소비는 0건이 아니라 앞 3건(§6.5), 선언 player start는 seed 상태의 `a74` 결과가 아니라 BIOS가 enable·credit를 갖춘 상태의 결과를 선언한 것(§6.6).

## 2. 입력 pin

ROM과 선언 입력은 시작과 끝에 SHA256을 확인한다. 가져다 쓰는 저장소 도구와 routing 파일은 SHA256이 아래 값과 다르면 관측기가 시작하지 않는다(`TOOL_PINS`, `ROUTING_SHA`).

| 항목 | 값 |
| --- | --- |
| ROM `extracted/program/maincpu.decrypted.be.bin` | SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 크기 8,388,608. 시작·끝에 SHA·크기·mtime_ns가 같았다(mtime_ns는 `platform.json`) |
| seed 관측 | `artifacts/stage_entry_body/observation.json` SHA256 `1f65100f…`(`historic`; `D.apply_seed_option`, 다른 SHA는 오류) |
| routing 기준 | `engine/src/animation_machine.cpp` SHA256 `8ce8eb93…`. `MC.parse_routed_atoms`의 범위·단일 PC 895(범위 817, 단일 78, routed 223,188바이트)개 atom, 단일 PC 실행부는 함수 내부 분기 closure까지 routed로 센다 [I] |
| 가져다 쓰는 도구(SHA256 앞 16자리) | `address_map` `5e11a86662c4dd84…`<br>`measure_code_coverage` `637d2cc8a2520a38…`<br>`observe_animation_machine_frame_head` `1b6cd5bddbd55ce6…`<br>`observe_animation_machine_pvc_banks` `86ebf962e3b83eef…`<br>`observe_animation_machine_scheduler` `62bb23ff6d2f61a5…`<br>`observe_animation_machine_scheduler_rng` `659f8636fa82311b…`<br>`verify_animation_machine_frame_controller` `45d163c4f6dc747a…`<br>`verify_animation_machine_frame_driver` `55bdc6cee56cbc00…`<br>`verify_animation_machine_frame_irq` `4f327616df45a5dc…` |
| 범위 문서 | SHA256 `1a1bcf4a7e0a4af6dcba838d72b002bfb52fb231e16986facb8799b0a559c4be` |
| 입력 스크립트 확장 | 스크립트별 2,048 frame 확장 SHA256을 `observation.json`의 `pins.input_scripts.expanded`에 둔다 |

## 3. 관측 protocol

범위 문서 §5.1을 그대로 구현했다. 구현은 D1 frame 구동기·controller Execute·IRQ 검증기의 native 클래스를 import해 합성한 하위 클래스(`IoRun`)이고, 저장소 도구는 수정하지 않았다.

1. **frame 0**: N0(seed 상태 그대로, S 계열은 선언 준비 P1 적용 후, B 계열은 §3.2의 frame 0 선언 상태). 외부 읽기가 없다.
2. **frame k ≥ 1**: (a) 그 frame의 선언 host 쓰기(`cfg['writes']`, H 시작 직전에 적용하고 `old → new`를 기록한다) → (b) H: frame head `e4a`/`e74`가 controller 전이 LONG `(1008e4)`까지 → (c) C: controller callback을 **실행**해 dispatcher 복귀 `2ac2`(A7 = SPd)까지 → (d) N: F2 node pass.
3. **대기와 IRQ**: H·C·N 모든 구간의 `ef2`/`16bd0`/`cda4`/`3aea`/`47af0`/`478de` 대기마다 IRQ를 1회 전달한다(F6-D 규약: SR `2000` push, SR := `2100`, PC := ROM LONG `64`, BIOS `c0044a` 선언 resume, RTE 모사, 레지스터 복원 확인, 구간당 16회). card 요청 `c00468`은 선언 resume(답 `0x80`)이다. IRQ 장치 값은 BYTE `320000` = 0, WORD `3c0006` = 0이다 [U: 실제 값·시점].
4. **외부 읽기**: H의 WORD `3c0006`과 BYTE `300000`/`340000`/`380000`은 frame별 선언 queue에서 소비한다. queue는 입력 스크립트로 만들고(§4), 같은 값을 그 frame의 모든 읽기에 준다. **queue는 `FH.run_head`가 대입할 때 하위 클래스의 `queue` 속성(setter)이 스크립트 queue로 바꿔 치운다. `FH.script_queue` monkeypatch는 쓰지 않는다.**
5. **frame당 기록**(§5)은 H·C·N 시작/끝, IRQ 전후의 전체 상태 digest, 순서 있는 port(IRQ port 제외)의 개수·SHA, native 외부 읽기 소비 목록(H, C, N 순서 = C++ queue 순서), host 쓰기, 진행 필드, guard, 미routing PC를 담는다.

### 3.1 S 계열

게임 mode 선언(D9 (ii): `1008e4 := c7fc`, `10fdaf := 2` @frame 1), 선언 준비 P1(원본 `3dce`, `c42`를 native로 실행해 레지스터는 버리고 `10fd80 |= 80`; 바꾼 바이트 9개를 `declared_seed.p1_prep`에 남긴다), P1은 선언 player start(`10f006 |= 1` @frame 1)와 `walkfire` 입력이다. 선언 player start는 `a74`의 `OR.B D0,10f006`(`ae4`)의 효과를 선언한 것이다. 관측기는 frame 1에서 같은 pre-state로 `a74`를 native로 실행해(`10fdb4 := 1`, `b0a`의 RTS까지, 레지스터 버림) 교차 확인한다(§6.6).

### 3.2 B 계열(BIOS 없는 boot)

`boot_native(fdae)`가 범위 문서 §3.3의 `p3_boot.py`를 정식화한 것이다. 0 RAM, `10fdae` := 요청값, A7 = ROM LONG 0(`10f300`), SR `2700`, PC `852`에서 native로 `2ab8` 첫 fetch까지 실행한다. 선언 목록은 `observation.json`의 `declared`(kind `boot`)와 `boot/boot_fdae*.json`에 이유·근거와 함께 있다.

- 선언 장치 읽기: `320000`/1 = 1(`10ea`), `3c0002`/2 = 0(`10c8`), `3c0006`/2 = 0(`9a4`), `300000`/1 = ff(`2634`), `380000`/1 = ff(`1322`). 이 5개 밖의 장치 읽기는 boot 실패다.
- BIOS 호출 2개: `c0045c`(`1302`), `c004c2`(`1100`)는 RTS로 선언한다. 다른 BIOS 호출은 boot 실패다.
- bank 창 WORD 쓰기 `25fff0 := a`(`874`)는 무시하고 기록한다.
- 두 번 boot해 RAM·기록이 같음을 assert한다.
- frame 0 선언: PC := `2ac2`, A6 := `1008e4`, A5 := `108000`(boot 상태와 같다), A7 := `1ff000`, LONG `104ca4` := `1ff000`(결정 1: 선언, 공개 헤더는 바꾸지 않는다).
- boot 중 palette RAM 쓰기는 0바이트다. frame 0의 palette bank는 둘 다 0이다(IO-1과 같다).

## 4. 구성과 입력 스크립트

`docs/analysis/data/io-input-scripts.json`(`format ms5-io-input-script`, `version 1`)이 입력 스크립트(`scripts`), 선언 host 쓰기 묶음(`host_write_sets`, 각 쓰기에 이유·근거), 구성(`configs`)을 한 파일로 가진다.

- 스크립트: 기본값 `{380000: ff, 300000: ff, 340000: ff, 3c0006: 0000}`에 구간 목록을 얹는다. 구간은 `from`/`to`(포함, `null` = 끝없음), `port`, 선택 `every`+`phase [a,b]`(절대 frame 번호 mod every가 [a,b] 안), `value`/`clear`/`set`이다. 파일 순서로 적용한다. 선택 `queue_limit`는 port별 queue 길이(기본 32)이다.
- `walkfire`(IO-1 탐침과 같다): frame 20부터 P1 오른쪽, A는 `frame mod 8 ∈ [0,3]`, B는 `frame mod 64 ∈ [0,5]`. start/select/coin bit는 없다(결정 3).
- `walkfire-start`: `walkfire`에 `380000` bit 0(start)를 frame 5~7, 60~62, 200~202에 더한 guard 시험용.
- 의미: frame k에 그 port를 몇 번 읽든 같은 값이다. C++에 넘기는 것은 이 표가 아니라 native 소비 목록이다.

| 구성 | 계열 | 입력 | host 쓰기 묶음 | frame |
| --- | --- | --- | --- | --- |
| `P0` | S | `none` | game-mode | 600 |
| `P1` | S | `walkfire` | game-mode, player-start-p1 | 600 |
| `P1b` | S | `walkfire` | game-mode, player-start-p1, player-start-p2 (`10f006` OR 2) | 600 |
| `boot-demo-0` | B | `none` | (`10fdae` = 2) | 최대 2,000 |
| `boot-title-start` | B | `walkfire` | title-start (`10fdaf := 2` @100) | 최대 2,000 |
| `boot-title-idle` | B | `none` | (`10fdae` = 3) | 600 |
| `fx-*` 5개 | S | 구성별 | 구성별 | 짧음(guard 시험, §8) |

seed 집합은 자연 seed 137개(case 141 포함, case 141은 frame 0 `odd-pc`)이다. P1b는 P1 결과 동치류 대표다: 서명 = (P0의 미routing 합집합을 뺀 첫 새 미routing `[frame, phase, pc]`, 플레이어 frame 수, 새 미routing PC 수), 대표 = 류 안 최소 case, 순서 = 류 크기 내림차순 → 대표 case 오름차순이다. split 대상은 이 순서의 앞 8개 대표(P0·P1 모두)와 B 3개다.

## 5. 기록 형식

출력 디렉터리 구조(`--out DIR`, 비어 있는 새 디렉터리여야 하고 도구는 아무것도 지우지 않는다):

| 경로 | 내용 | 비교 |
| --- | --- | --- |
| `observation.json` | 비교 필드만 + 최상위 `compared_sha256` | 비교 대상 |
| `platform.json` | Unicorn·capstone 버전, 라이브러리 파일 SHA, Python, OS, worker 수, 경과 시간, 생성 시각, git HEAD, ROM mtime_ns, 출력 파일 목록·SHA | 비교 제외 |
| `runs/<구성>/<case>.json.gz` | 실행 하나의 frame 기록 전체 + 요약 + 미routing PC 횟수 | `records.sha256`(압축 전 정규 JSON)이 observation에 있다 |
| `states/<구성>/<case>.pack.gz` | frame 시작 상태 pack(§5.3) | `states.sha256`(압축 전)이 observation에 있다 |
| `boot/` | boot 선언·기록 JSON, frame 0 RAM(gzip) | 파일 비교 |

`compared_sha256` = `observation.json`(자기 자신 제외)의 정규 JSON(`sort_keys`, 공백 없음) SHA256이다. 압축 파일(gzip은 `mtime=0`)의 바이트는 같은 플랫폼에서 같지만, 다른 플랫폼의 zlib 차이를 피하려고 비교 필드에는 **압축 전** SHA만 둔다.

### 5.1 observation.json

`pins`(ROM·seed·도구·관측기·routing·입력 스크립트 확장·범위 문서 SHA), `protocol`, `declared`(선언 목록: protocol, irq, card, palette, controller-return, seed-prep-p1, stack, guards, boot), `configs`, `classes`(동치류), `class_baseline`, `runs`(실행마다 1행), `aggregates`, `fixtures`, `compared_sha256`.

`runs[]` 행: `config`, `case`, `mode`(`continuous`), `frames`, `records`(`path`, `sha256`, `bytes`), `digest_chain`(frame별 비교 view의 정규 JSON SHA), `host_writes`(선언 쓰기 행), `summary`(정지·guard·controller 종료 callback·입력 mode 분포·queue 검사·플레이어·카메라·IRQ·미routing 집계·a74 교차 확인·마지막 진행 필드·`declared_seed`), `states`, `split`(해당 실행만), `rerun_identical`.

### 5.2 frame 기록(`runs/*.json.gz`의 `frames[]`)

| 필드 | 의미 |
| --- | --- |
| `f` | frame 번호(0부터) |
| `start` | frame 시작 상태 digest(선언 host 쓰기 적용 후) |
| `mode` | frame 시작의 BYTE `104cd4` |
| `hw` | 선언 host 쓰기 `[address, size, old, new, mode]` |
| `H` | `stop`, `end`(H 끝 = C 시작 digest), `ports [개수, SHA]`(IRQ port 제외), `head_cb`, `ctrl_cb`, `waits [[pc, kind]]`(IRQ 대기 제외), `status`(상태 byte `d00046` 읽기 수) |
| `C` | `res`(`returned`/…), `entry`(controller callback), `exit`(종료 callback LONG `1008e4`), `start`, `end`, `ports`, `waits [[pc, address]]`, `status`, `path`(C3a leader 방문) |
| `N` | `stop`, `start`, `end`, `ports`, `cbs`(pass별 node callback 목록), `waits`, `status` |
| `irq` | IRQ마다 `seg`(H/C/N), `pc`(대기 PC), `res`, `reads`, `bios`, `sr`, `pre`, `post`(전후 전체 상태 digest), `ports` |
| `q` | **native 외부 읽기 소비 목록** `[address, size, value]` — H, C, N 순서(= C++ queue 순서) |
| `qchk` | `none`(frame 0) / `ok` / `order:…` / `value:…`(§6.5) |
| `fields` | 진행 필드(`stagecb` `p1cb` `p2cb` `ctrlcb` 카메라 3개 `mission` `area` `aid` `d684` `mod1` `mod2` `inmode` `replay_cur` `replay_ptr` `fdae` `fdaf` `f004` `f006` `f007` `mode12` `fd82` `inblk`(`104ca8..104cbd`)) — **직전 frame과 달라진 항목만**, frame 0은 전부 |
| `guard` | `null` 또는 `{kind, seg, reason, detail}` |
| `unr_new` | 이 실행에서 처음 나온 미routing PC `[pc, 횟수, phase]` |
| `unr_n`, `unr_first` | 이 frame에 닿은 미routing PC 수, 실행 순서상 첫 `[phase, pc]` |
| `tb` | 고유 TB 수, 정렬한 `(phase, addr, size, 횟수)` 목록의 SHA 앞 32자 |
| `tbs` | (key frame만: frame 0·1·2, 첫 미routing frame, 정지 frame, 마지막 frame) 실행 TB `[phase, addr, size, 횟수]` |

주소·PC는 정수(10진)로 둔다(요약의 집계 키만 16진 문자열).

- **상태 digest**: `sha256("MS5-IO-STATE-1" + 헤더 78바이트 + RAM 64 KiB + PVC page 8 KiB + palette bank 0 8 KiB + bank 1 8 KiB)`. 헤더는 `>16IIIHHBB`로 D0~D7, A0~A7, PC, bank base, ff8, ff9, 상태 byte(`d00046`), palette 선택이다. PVC page는 D1 규약대로 ff8/ff9를 `1ff0`에 정규화한 값이다.
- 미routing 판정 [I]: 실행한 TB 안에서 routing bitmap 밖인 첫 명령 시작 PC를 센다(IO-1 탐침의 정의). 같은 PC는 TB가 실행될 때마다 1회로 센다.

### 5.3 상태 pack(`states/*.pack.gz`)

gzip을 푼 바이트: 8바이트 `MS5IOST1` 뒤에 레코드가 이어진다. 레코드 = `>IBH`(frame, 종류 0 = 전체 / 1 = 바로 앞 레코드 대비 delta, page 수) + 헤더 78바이트 + page마다 `>H`(page 번호) + 256바이트. page 번호 0~255 = RAM, 256~287 = PVC page, 288~319 = palette bank 0, 320~351 = bank 1. 첫 레코드는 전체이다. 읽는 함수는 `read_pack`(import 가능)이며 각 레코드에서 digest를 다시 계산해 기록의 `start`와 같음을 도구가 검증한다(`states.roundtrip_ok`). 담긴 frame은 `states.frames`이다.

기본(`--keep-all-states all`)은 모든 실행의 **모든 frame 시작 상태**를 담는다(IO-2가 frame마다 resume할 수 있다). 600 frame 한 실행당 약 0.05~0.65 MB이다.

### 5.4 IO-2(C++ 비교)가 읽는 방법

- 실행 목록은 `observation.json.runs[]`이다. `records.path`의 `frames[]`에서 frame k의 `q`(native 소비 목록 = C++ queue), `hw`(선언 host 쓰기), `guard`, 기대 digest를 읽고, `states.path`의 pack에서 frame k의 **시작 상태**(선언 host 쓰기 적용 후)를 읽는다. 시작 상태는 RAM 64 KiB, D0~D7/A0~A7, PC, bank base, PVC page, palette bank 2개와 선택, 상태 byte를 모두 담는다.
- frame 0은 `run_animation_machine_pass`, frame ≥ 1은 `step_animation_machine_frame`(Execute + IRQ + palette)에 시작 상태와 `q`를 넣는다. 결과 상태를 `H.end`/`C.start`/`C.end`/`N.start`/`N.end`/`irq[].pre|post`와 다음 frame의 `start`(host 쓰기가 없는 frame이면 `N.end`와 같다)의 digest(위 상태 digest 정의)와 비교하거나, 필드별로 비교한다. 구간별 port는 개수와 SHA(`S.ports_digest`: `>BIBI` kind/address/size/value 순서 열)로 둔다.
- frontier 후보: `unr_first`(frame 안 실행 순서상 첫 미routing `[phase, pc]`)와 `tbs`(key frame의 실행 TB 목록)를 쓴다. `runs/*.json.gz`의 `unr_pcs`는 PC별 실행 횟수 전체이고, `unr_new`는 그 PC가 처음 나온 frame이다.
- native guard frame(`guard != null`)은 C++가 대응하는 checked 오류를 내야 하는 frame이다. 대응표는 IO-2가 정한다(`rom-write`, `undeclared-device-read`, `external-read-queue-empty`, `bios-boundary`, `irq:*`는 기존 `NATIVE_END_ERROR`에 없는 항목이다).

## 6. 결과

### 6.1 P0(대조: 게임 mode 선언, 입력 없음)

- 실행 137개(자연 seed 137, case 141 포함), 정지 분포 {'frame-limit': 136, 'odd-pc': 1}. 완료(frame-limit) 136개 = 136 × 600 frame. case 141은 frame 0 `odd-pc`(PC `47c05`)로 D1과 같다 [F].
- controller 종료 callback을 가진 seed 수: {'c79a': 136, 'c7fc': 128}. 곧 `c7fc`→`c79a` 대기 경로는 D9 (ii)와 같다 [F].
- 미routing PC 합집합(기준선): ['`3900`'] — D9에서 이미 알려진 실행부 끝 PC `3900` 하나뿐이다 [F].
- IRQ 전달 162928회(frame당 평균 2.00), 모두 `ef2`/H에서 `ok`, 복귀 검사 실패 0 [F]. 입력 소비 순서 위반 0.

### 6.2 P1(주 구성: 게임 mode + 선언 player start + `walkfire`)

- 실행 137개, 정지 분포 {'frame-limit': 136, 'odd-pc': 1}. 완료 136개, 비완료 [[141, 'odd-pc']] [F].
- 플레이어를 만든 seed: **12개**, 플레이어 frame 합계 4328 [F]. controller 종료 callback별 seed 수: {'c7fc': 128, 'c82e': 12, 'c8e8': 12, 'c90c': 12}.
- P0 기준선에 없는 새 미routing PC: **1864개**, 실행 1282870회, 닿은 seed 52개. 첫 새 미routing frame은 최소 2, 중앙 100, 최대 327이다 [F].
- 실행 순서상 첫 미routing PC(seed 수; 범위 문서 §6.3의 "첫 frontier PC"와 같은 정의): `de660` 12, `b3dbc` 11, `e5324` 11, `4b6f4` 2, `51602` 2, `5a376` 2, `b30f6` 2, `b7742` 2, `b975e` 2, `bc08c` 2, `d131a` 2, `eb9ba` 2 [F].
- 새 PC가 본 seed 수 분포(seed 수: PC 수): {'2': 559, '6': 2, '8': 138, '11': 176, '12': 744, '13': 1, '19': 94, '23': 150}.

IO-1의 `an5.py`(저장소 밖 scratch 집계기)를 이 관측의 P1·P0 결과에 그대로 적용한 출력(함수 root 묶음, [I]):

```text
seeds 137 stops {'frame-limit': 136, 'odd-pc': 1}
frames total 81601
seeds with unrouted 52 first-unrouted frame min/median/max 2 100 327
seeds with player spawned 12 player frames 4328
ctrl exits Counter({'c7fc': 128, 'c82e': 12, 'c8e8': 12, 'c90c': 12})
new unrouted PCs (TB instruction starts, minus baseline) 1864 execs 1282870 of which V1 pc_routed 0 baseline pcs 1
first unrouted PC per seed (top): [('de660', 12), ('b3dbc', 11), ('e5324', 11), ('5a376', 2), ('bc08c', 2), ('4b6f4', 2), ('b975e', 2), ('eb9ba', 2), ('d131a', 2), ('b30f6', 2), ('b7742', 2), ('51602', 2)]
function roots 328
by area (roots, execs, pcs): {'D': [226, 742798, 1211], 'C': [61, 350392, 395], 'E': [41, 189680, 258]}
root    A      execs   pcs seeds closure(direct) / with pointers
0768b6 D      91482    35    23  L47 I137 B640  ptr 3
0b4958 D      78991    15    23  L108 I298 B1064  ptr 5
04e94e C      70928    45    12  L502 I1226 B4654  ptr 31
01cd98 C      51616    18    12  L45 I106 B428  ptr 2
0c01a8 D      49392    17    23  L138 I375 B1386  ptr 5
0de8bc E      46140     3    12  L3 I3 B14  ptr 0
0b476a D      33987     7    23  L19 I43 B156  ptr 1
021688 C      30392    59    12  L1 I13 B46  ptr 0
076f98 D      28602    56    19  L1 I1 B4  ptr 0
07343a D      28160    18    11  L74 I190 B748  ptr 7
0df15e E      26540    16    12  L30 I77 B318  ptr 4
0dec8c E      25764    10    12  L12 I26 B116  ptr 2
04e732 C      25236    20    12  L502 I1226 B4654  ptr 31
0215e6 C      22856     5    12  L5 I10 B28  ptr 0
```

### 6.3 동치류와 P1b

P1 결과 서명이 같은 seed를 한 류로 묶었다. 서명 = (첫 새 미routing `[frame, phase, pc]`, 플레이어 frame 수, 새 미routing PC 수); 첫 새 미routing은 P0 합집합에 없는 PC 가운데 처음 나온 frame의 것이고 같은 frame에서는 가장 낮은 PC를 쓴다(실행 순서상 첫 PC와 다를 수 있다). 류 14개(범위 문서 §3.1의 14개와 같다). case 141(frame 0 `odd-pc`, 새 PC 0)은 "새 code 없음" 류에 들어가므로 그 류는 85 = 84 + 141이다.

| 대표 | 류 크기 | 첫 새 미routing `[frame, phase, pc]` | 플레이어 frame | 새 미routing PC | 실행 순서상 첫 미routing `[frame, phase, pc]` | 류의 case |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 85 | None | 0 | 0 | None | 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 18, 19, 20, 21, 24, 25, 26, 27, 28, 29, 30, 31, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 62, 63, 64, 65, 66, 67, 74, 75, 76, 77, 78, 79, 82, 83, 86, 87, 88, 89, 92, 93, 96, 97, 98, 99, 102, 103, 104, 105, 108, 109, 112, 113, 114, 115, 116, 117, 141 |
| 0 | 11 | [99, 'N', 'b3dbc'] | 0 | 343 | [99, 'N', 'b3dbc'] | 0, 1, 127, 128, 129, 130, 131, 132, 133, 134, 135 |
| 90 | 11 | [100, 'N', 'e52b2'] | 0 | 78 | [100, 'N', 'e5324'] | 90, 91, 118, 119, 120, 121, 122, 123, 124, 125, 126 |
| 94 | 8 | [2, 'N', 'ca50'] | 385 | 1126 | [2, 'N', 'de660'] | 94, 95, 100, 101, 106, 107, 110, 111 |
| 68 | 4 | [222, 'N', 'ca50'] | 312 | 894 | [222, 'N', 'de660'] | 68, 69, 70, 71 |
| 16 | 2 | [133, 'N', '5a376'] | 0 | 177 | [133, 'N', '5a376'] | 16, 17 |
| 22 | 2 | [167, 'N', 'bc08c'] | 0 | 237 | [167, 'N', 'bc08c'] | 22, 23 |
| 32 | 2 | [181, 'N', '4b6f4'] | 0 | 2 | [181, 'N', '4b6f4'] | 32, 33 |
| 44 | 2 | [120, 'N', 'b975e'] | 0 | 18 | [120, 'N', 'b975e'] | 44, 45 |
| 58 | 2 | [24, 'N', 'eb9ba'] | 0 | 4 | [24, 'N', 'eb9ba'] | 58, 59 |
| 60 | 2 | [327, 'N', 'd131a'] | 0 | 38 | [327, 'N', 'd131a'] | 60, 61 |
| 72 | 2 | [120, 'N', 'b30ba'] | 0 | 58 | [120, 'N', 'b30f6'] | 72, 73 |
| 80 | 2 | [273, 'N', 'b7742'] | 0 | 1 | [273, 'N', 'b7742'] | 80, 81 |
| 84 | 2 | [143, 'N', '515e0'] | 0 | 31 | [143, 'N', '51602'] | 84, 85 |

P1b(P1 + `10f006 |= 2`)는 대표에 대해 실행했다. 결과:

| 대표 | 정지 | P1 플레이어 frame | P1b P1 플레이어 | P1b P2 플레이어 | P1 미routing PC | P1b 미routing PC | controller 종료 callback frame 수 P1 / P1b |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | frame-limit | 0 | 0 | 0 | 0 | 0 | c7fc:599 / c7fc:599 |
| 0 | frame-limit | 0 | 0 | 0 | 343 | 343 | c7fc:599 / c7fc:599 |
| 90 | frame-limit | 0 | 0 | 0 | 78 | 86 | c7fc:599 / c7fc:599 |
| 94 | frame-limit | 385 | 528 | 0 | 1126 | 316 | c82e:1 c8e8:165 c90c:433 / c82e:1 c8e8:598 |
| 68 | frame-limit | 312 | 312 | 0 | 894 | 316 | c7fc:220 c82e:1 c8e8:161 c90c:217 / c7fc:220 c82e:1 c8e8:378 |
| 16 | frame-limit | 0 | 0 | 0 | 177 | 177 | c7fc:599 / c7fc:599 |
| 22 | frame-limit | 0 | 0 | 0 | 237 | 237 | c7fc:599 / c7fc:599 |
| 32 | frame-limit | 0 | 0 | 0 | 2 | 2 | c7fc:599 / c7fc:599 |
| 44 | frame-limit | 0 | 0 | 0 | 18 | 18 | c7fc:599 / c7fc:599 |
| 58 | frame-limit | 0 | 0 | 0 | 4 | 4 | c7fc:599 / c7fc:599 |
| 60 | frame-limit | 0 | 0 | 0 | 38 | 38 | c7fc:599 / c7fc:599 |
| 72 | frame-limit | 0 | 0 | 0 | 58 | 58 | c7fc:599 / c7fc:599 |
| 80 | frame-limit | 0 | 0 | 0 | 1 | 1 | c7fc:599 / c7fc:599 |
| 84 | frame-limit | 0 | 0 | 0 | 31 | 31 | c7fc:599 / c7fc:599 |

- [F] P1b에서 P2 node(`100da8`)는 모든 대표에서 idle(`270e`)을 유지했다(P2 플레이어 생성 0). 선언 `10f006 |= 2`는 `b68`이 `10fdb7` := 1로 바꾸지만, 600 frame 안에서 P2 플레이어 객체를 만드는 경로는 열리지 않았다. 새 게임이 시작되는 류(대표 94)는 P1b에서 캐릭터 선택 `c8e8`에 머물러 `c90c`로 진행하지 않았다(P1은 `c90c`) [F]. 원인(P2 선택 대기 등)은 [U].

### 6.4 B 계열(BIOS 없는 boot)

| 구성 | frame | 정지 / guard | 미routing PC | 플레이어(P1 node) frame | 플레이어 첫 frame | IRQ | controller 경로(진입→종료, 횟수) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `boot-demo-0` | 578 | invalid-memory-access → `rom-write`(frame 577) | 731 | 197 | 381 | 1154 | `c560` 1, `c5f4` 228, `c608` 149, `c654` 1, `c66a` 198 |
| `boot-title-start` | 907 | C:system-return → `system-return`(frame 906) | 1180 | 385 | 192 | 1812 | `c560` 1, `c6f4` 98, `c79a` 21, `c82e` 1, `c8e8` 165, `c90c` 512, `c940` 108 |
| `boot-title-idle` | 600 | frame-limit | 22 | 0 | None | 1198 | `c560` 1, `c6f4` 598 |

- `boot-demo-0`: `10fdae` = 2에서 [F] 원본 코드 `3162`가 frame 379에 replay 포인터 `104cc4` := `f07fe`, 입력 mode `104cd4` := 1를 설치했다. mission `10d680` = 7(frame 379), 플레이어 callback 첫 변화 frame 381. replay 커서 `104cce` 마지막 값 41. 입력 mode 별 frame 수 {'0': 380, '1': 198}. frame 577에서 N이 ROM에 쓴다(`rom-write`, 쓰기 주소 `aeaba`, PC `aea68`). 이 정지는 범위 문서 결정 2대로 v1에서 checked 정지로 둔다.
- `boot-title-start`: title 대기 `c6f4`→(frame 100 선언 `10fdaf := 2`)→`c79a`→`c82e`. 원본이 `10fdb6` := 1을 frame 121에 쓴다 [F]. 플레이어 callback 첫 변화 frame 192(`1d20c`), 사망 후 `10fdb6` = 3(frame 578). 마지막 정지는 C 구간 `c00444` BIOS 반환(`system-return`, frame 906, 총 907 frame) — 범위 문서 §3.3과 같은 지점이다. 입력 mode 분포 {'0': 907}.
- `boot-title-idle`: 600 frame 동안 title 대기 `c6f4`에 머문다(start bit가 없고 BIOS PLAYER_START 선언이 없으면 게임이 시작하지 않는다) [F]. 완료, 새 code 없음(미routing PC 22개는 title 객체 `de376..` 계열).

### 6.5 입력 소비 순서 검사

- frame마다 native 소비 목록(`q`)이 (a) H2 계약 순서 — mode 0: `3c0006 3c0006 380000 300000 340000 300000 340000`, 입력 mode 1(replay): `3c0006 3c0006 380000 300000 340000`(관측; recorder 경로 `349c`는 뒤에 `300000 340000`이 붙는다), mode ≥ 2: 같은 앞 3건 입력 읽기 — 이고 (b) 값이 입력 스크립트의 그 frame 값과 같은지 검사한다. 전체 296개 실행에서 검사 통과 frame 173676, 자연 실행(P0/P1/P1b/B)의 **위반 0**, 합성 fixture 3개의 정지 frame에서 3(소비가 정지로 중간에 끝난 frame이므로 예상된 결과) [F].
- 입력 mode(`104cd4`)별 frame 수: boot-demo-0 {'0': 380, '1': 198}.
- **범위 문서와의 차이**: 범위 문서 §5.2는 mode 1(replay) frame의 입력 port 소비를 0건으로 적었는데, 관측은 replay frame(`boot-demo-0`의 `c66a` 구간)에서도 앞 3건(`380000 300000 340000`)을 소비했다 [F]. 관측기는 이를 mode 1의 정상 패턴(앞 3건, 또는 recorder 5건)으로 받는다. H2 계약 문장("1이면 replay 또는 recorder 뒤 0건")과도 이 해석이 맞는다 [I]. C++ 쪽은 native 소비 목록을 그대로 받으므로 영향이 없다.
- N·C 구간의 입력 port 직접 읽기 `undeclared-device-read`: 모든 자연 실행에서 0건 [F]. 합성 fixture 2개(§8)로 검출을 확인했다.

### 6.6 선언 player start와 `a74` 교차 확인

범위 문서 결정 2대로 frame 1의 pre-state(선언 game-mode 쓰기 적용 후)에서 원본 `a74`를 native로 실행했다(`10fdb4 := 1`, `b0a` RTS까지, 레지스터 버림). 두 변형의 `10f006` 변화(실행 수):

| 변형 | 결과 | 실행 수 |
| --- | --- | --- |
| bios-enabled(f004=3,f007=ff,fd82=1) | `10f006` 증가분 1 | 150 |
| seed-pre-state | `10f006` 증가분 0 | 150 |

[F] seed pre-state(`10f004` = 0, `10f007` = 0, `10fd82` = 0)에서는 `a74`가 `10fdb4`만 지우고(`a2c`의 credit 검사와 `and.b` 마스크가 D0를 0으로 만든다) **`10f006`을 바꾸지 않는다**. `10f004` = 3, `10f007` = ff, `10fd82` = 1(AES식 credit 면제)일 때만 `10f006 |= 1`이 되어 선언과 같아진다. 곧 S 계열의 선언 `10f006 |= 1`은 "BIOS가 이미 enable 마스크와 credit를 갖춘 상태에서 PLAYER_START를 처리한 결과"의 선언이고 seed 상태에서 `a74`가 자연히 만드는 결과가 아니다 [I]. 이 차이는 범위 문서 §9-1과 같은 미확인 항목이며 선언의 이유 문장에 이미 포함했다.

## 7. IO-1 탐침 재현

IO-1 탐침(`ms5-scratch/io1`)과 같은 구성의 출력(`out/r3/all_P0.json`, `all_P1.json`)을 이 관측과 seed별로 비교했다(정지 종류·frame 수, 첫 미routing `[frame, phase, pc]`, 미routing PC별 실행 횟수 전체, 플레이어 frame, 카메라 이동량, H 외부 읽기 수).

```text
P0 compared 137 diffs {}
[]
P1 compared 137 diffs {}
[]
```

IO-1과 다르게 한 것: 선언 player start를 `set`이 아닌 `or`(`10f006 |= 1`)로 쓴다(seed의 `10f006`은 0이라 같은 결과); 입력은 monkeypatch 없이 하위 클래스 setter로 공급한다; frame별 상태 digest·port·IRQ 기록이 추가되었다. 위 비교에서 불일치가 0이면 이 변경은 관측 결과를 바꾸지 않았다.

| 항목 | IO-1 / 범위 문서 | 이 관측 |
| --- | --- | --- |
| P1: 완료 seed + case 141 | 136 + `odd-pc` | 136 + [[141, 'odd-pc']] |
| P1: 플레이어를 만든 seed | ≥ 12 (탐침 12, 합계 4,328 frame) | 12 (합계 4328 frame) |
| P1: 새 미routing PC | ≥ 1,500 (탐침 1,864) | 1864 (실행 1282870회; 탐침 1,282,870회) |
| P1: 미routing에 닿은 seed | 52 | 52 |
| P1: 첫 새 미routing frame 최소/중앙/최대 | 2 / 100 / 327 | 2 / 100 / 327 |
| P1: 동치류 | 14 | 14 |
| P0: 완료 / 새 미routing | 136 완료, `c7fc`→`c79a`, 새 0(`3900` 제외) | 136 완료, {'c79a': 136, 'c7fc': 128}, ['3900'] |
| B demo | frame 577 `rom-write`, 새 PC 731 | frame 577 `rom-write`, PC 731 |
| B title-start | frame 906 `c00444` 종단 | frame 906 `system-return`, PC 1180 |
| B title-idle | 600 frame 완주 | 600 frame, 정지 frame-limit |

함수 root 묶음은 IO-1의 `an5.py` 출력(위 §6.2)으로 비교한다. 범위 문서 §6.3의 값: 함수 root 328개(D 226, C 61, E 41).

## 8. guard와 typed fixture

guard는 checked 정지다(상태 보존, 이유 기록). `rec.guard = {kind, seg, reason, detail}`:

| kind | 구간 | 원천 | 비고 |
| --- | --- | --- | --- |
| `system-return` | C | controller가 BIOS `c00444`를 fetch | 정상 종료로 집계(C++ 대응 오류 `animation frame controller system return`) |
| `rom-write` | N/H/C | 고정 ROM·bank 창(`200000..2fdfff`)에 대한 쓰기(write-protected) | 결정 2: v1에서 checked 정지. B demo frame 577 `aea68`이 자연 사례 |
| `bios-boundary` | H/N/C | 선언 밖 BIOS fetch(`c00444`·`c00468` 외) | H/N에서는 `c00444`도 이 종류 |
| `undeclared-device-read` | N/C | 입력 port `300000`/`340000`/`380000`(BYTE), `3c0006`(WORD) 직접 읽기 | 관측기 hook `h_inguard` + FH의 `340000`/`380000` 읽기 거부. 자연 실행 0건 |
| `external-read-queue-empty` | H | 선언 queue보다 많이 읽음 | FH 기존 |
| `odd-pc`, `odd-data`, `unmapped-access`, `fetch-unmapped`, `cpu-exception` | 전 구간 | 기존 guard | case 141은 frame 0 `odd-pc` |
| `head-callback` | H | frame head 보조 callback `f3c`, menu callback `931a` | 기존 guard |
| `irq:<res>` | H/C/N | IRQ 실패(`bios-int1`, `internal-wait`, `regs-differ`, `undeclared-read`, …) | F6-D 기존 |
| `wait-not-released`, `step-limit`, `trap-boundary` | 전 구간 | 기존 guard | 자연 실행 0건 |

이 관측에서 실제로 나온 guard(구성, kind: 실행 수): P0 `odd-pc`: 1; P1 `odd-pc`: 1; boot-demo-0 `rom-write`: 1; boot-title-start `system-return`: 1; fx-bios-call `bios-boundary`: 1; fx-c-input-read `undeclared-device-read`: 1; fx-n-input-read `undeclared-device-read`: 1; fx-queue-short `external-read-queue-empty`: 1; fx-start-c79a `system-return`: 1.

typed fixture(`observation.json` `fixtures`). 자연 사례(B)와 합성 fixture(S, case 0)이다:

| 구성 | 종류 | 기대 | 관측 | 일치 |
| --- | --- | --- | --- | --- |
| `boot-demo-0` | 자연 | `rom-write` frame 577 | `rom-write` frame 577 (N) | 예 |
| `boot-title-start` | 자연 | `system-return` frame 906 | `system-return` frame 906 (C) | 예 |
| `fx-bios-call` | 합성 | `bios-boundary` frame 3 | `bios-boundary` frame 3 (H) | 예 |
| `fx-c-input-read` | 합성 | `undeclared-device-read` frame 3 | `undeclared-device-read` frame 3 (C) | 예 |
| `fx-n-input-read` | 합성 | `undeclared-device-read` frame 3 | `undeclared-device-read` frame 3 (N) | 예 |
| `fx-queue-short` | 합성 | `external-read-queue-empty` frame 1 | `external-read-queue-empty` frame 1 (H) | 예 |
| `fx-start-c79a` | 합성 | `system-return` frame 273 | `system-return` frame 273 (C) | 예 |

합성 fixture의 구성: `fx-start-c79a` = `walkfire-start`(start bit)로 `c79a` menu가 BIOS로 반환; `fx-queue-short` = `none-raster-short`(raster queue 1개); `fx-bios-call` = frame 3에 LONG `1008e4` := `c00450`; `fx-n-input-read` = frame 3에 LONG `100bf4`(N node callback) := `2634`(`MOVE.B 300000,D0 … RTS`); `fx-c-input-read` = frame 3에 LONG `1008e4` := `2634`. 이 선언 쓰기는 모두 `io-input-scripts.json`의 `host_write_sets`에 근거와 함께 있다.

## 9. 결정성: 반복 실행과 split

- **반복 실행**: 같은 명령을 서로 다른 디렉터리 두 곳(`runA`, `runB`)에 실행했다. `observation.json`의 `compared_sha256`: A `3cc9adbb2692267e840b7b3fbdfd24f61cf277a681db87241234be42741d9f4d`, B `3cc9adbb2692267e840b7b3fbdfd24f61cf277a681db87241234be42741d9f4d`. 같다.

```text
{
 "compared_sha256_a": "3cc9adbb2692267e840b7b3fbdfd24f61cf277a681db87241234be42741d9f4d",
 "compared_sha256_b": "3cc9adbb2692267e840b7b3fbdfd24f61cf277a681db87241234be42741d9f4d",
 "equal": true,
 "files_a": 597,
 "files_b": 597,
 "only_a": [],
 "only_b": [],
 "differ": [],
 "clean": true
}
```

  `diff -rq -x platform.json runA runB`: 출력 없음(깨끗, 각 597개 파일). run B는 `--workers 2`, run A는 `--workers 3`이므로 결과가 worker 수와 무관함도 확인했다.

- **split**(frame마다 기록된 frame 시작 상태에서 새 CPU(palette bank 포함 복원)로 실행) 대 continuous: 19개 실행(P0:0, P0:2, P0:16, P0:22, P0:32, P0:68, P0:90, P0:94, P1:0, P1:2, P1:16, P1:22, P1:32, P1:68, P1:90, P1:94, boot-demo-0, boot-title-idle, boot-title-start). frame별 비교 view(시작·H·C·N 상태 digest, port, IRQ 전후 digest, 소비 목록, 진행 필드, guard)가 모두 같은 실행: **19 / 19**. 정지 종류도 같다. 미routing PC 집합: 19 / 19 같고, TB 목록 SHA: 19 / 19 같다.
- **재실행 일치**: 대표 seed(P0·P1) 16개 실행은 두 번째(split을 붙인) 실행에서도 frame 기록 SHA와 `digest_chain`이 첫 실행과 같다 — 도구가 같음을 assert한다.
- **상태 pack 왕복**: 상태 pack을 가진 296개 실행 모두 pack을 다시 읽어 레코드의 digest가 frame 기록의 `start`와 같음을 확인했다(`roundtrip_ok`).
- split이 필요로 한 관측기 쪽 처리 [F]: `ControllerRun`은 C 실행 후의 상태를 `FH.run`의 split 재구성에 넘기지 못한다(D1의 split은 controller skip을 가정). 하위 클래스가 C 이후 상태를 반환하도록 했고, palette bank는 `Machine.state()` 래퍼와 `build`의 복원으로 상태에 포함시켰다. 이 처리 없이는 split과 continuous가 어긋난다.

## 10. 플랫폼 분리와 출력 크기

- `platform.json`(비교 제외): Unicorn 2.1.4, capstone 5.0.6, Python 3.14.3, macOS-26.4.1-arm64-arm-64bit-Mach-O arm64, worker run A 3 / run B 2(결과는 worker 수와 무관), 경과 1530초(run A) / 2202초(run B), 생성 시각, git HEAD, ROM mtime_ns, 출력 파일 목록·SHA. 라이브러리 파일은 `unicorn/lib/`의 모든 파일(SHA256)을 남긴다.
- 역사적 실패(보고서에 Unicorn 라이브러리 SHA를 넣어 다른 OS에서 재현이 안 됨)를 피했다: `observation.json`에는 파일 SHA(도구·routing·입력 스크립트·ROM 내용)와 결과만 있고, 다른 플랫폼에서는 `compared_sha256` 일치로 판정한다. 이 판정은 이 macOS arm64에서만 실행했다 [U: 다른 플랫폼].
- 출력 크기: run A 98,487,768 바이트(93.9 MB), run B 98,487,768 바이트. 상한 3 GB 이내이고 두 디렉터리 합계도 이내이다.

## 11. 범위 문서와의 차이

- 입력 mode 1(replay) frame의 입력 port 소비를 0건으로 적은 범위 문서 §5.2와 달리 관측은 앞 3건을 소비한다(§6.5). 검사기는 관측과 H2 계약 문장의 해석에 맞췄다.
- 선언 player start는 범위 문서의 "`a74` 효과" 설명과 달리 seed pre-state에서 `a74`가 만드는 결과가 아니다(§6.6). 선언 자체(`10f006 |= 1` @frame 1)는 범위 문서대로이다.
- 상태 pack은 범위 문서 §5.5의 "모든 frame 시작 상태"를 전 실행에 대해 만들었다(약 94 MB 안쪽이라 대표 8개 제한이 필요 없었다). 상태 pack 형식은 gzip된 page-delta 파일이며 범위 문서의 `blobs/` 대신 `states/`이다(`DIR/blobs/`는 만들지 않는다).
- `observation.json`은 frame별 기록을 직접 담지 않고 실행별 `runs/*.json.gz`(압축 전 SHA를 `records.sha256`에 둔다)에 둔다. 비교 필드 전체가 SHA로 `compared_sha256`에 묶인다. CLI에서 `--keep-all-states`, `--boot-frames`, `--cases`, `--p1b-cases`, `--no-split`, `--no-fixtures`, `--selftest`, `--compare`를 더했다.
- 미routing PC 판정은 IO-1과 같은 정의(TB 안 첫 미routing 명령 시작)를 유지했다. 모든 미routing 명령을 세는 정의로 바꾸지 않았다(TB 분할이 달라지는 split에서 집합이 달라질 수 있다). 실제 split에서 집합과 TB 목록이 같았다(§9).
- S 계열 split 대상은 P0·P1의 앞 8개 대표이다(P1b에는 split을 붙이지 않았다). B는 3개 모두 split을 붙였다.
- 번호 규약: 범위 문서의 "frame 274에 BIOS `c00444`로 끝난다"(S, start bit)는 **완료 frame 수** 274를 뜻하고 기록의 frame 번호(0부터)로는 273이다(`fx-start-c79a`). B title-start의 "frame 906"은 기록의 frame 번호이고 완료 frame은 907개이다.
- 입력 스크립트 확장 SHA(`pins.input_scripts.expanded`)는 port 값 표만 덮는다. `queue_limit`(`none-raster-short`)은 JSON 파일 SHA에만 반영된다(그래서 `none`과 `none-raster-short`의 확장 SHA가 같다).
- fixture를 5개 만들었다. 범위 문서 §7이 요구한 종류(start bit `c79a` 종단, N 입력 읽기 합성, queue 부족, ROM 쓰기(B demo 자연), BIOS 밖 호출)에 C 구간 입력 읽기를 더했다.

## 12. 미확인

- [U] 실제 BIOS의 PLAYER_START 호출 시점·횟수와 AES/MVS 차이. S 계열의 `10f006 |= 1` 선언이 실제 BIOS 동작과 같은지(§6.6).
- [U] boot 장치 응답(`3c0002` 읽기 값, Z80 응답 시점, calendar 값), SR `2700` 진입 가정, BIOS의 boot 전 RAM 초기화. 0 RAM을 가정했다.
- [U] IRQ 장치 값(`320000` = 0, `3c0006` = 0), 실제 raster·vblank 값과 시점. IRQ 전달 위치는 선언된 대기 지점뿐이다.
- [U] B demo frame 577의 ROM 쓰기(`aea68`, A0 = `aea38`)가 원본 bug인지 boot 선언 차이인지.
- [I] 미routing 판정은 단일 PC 실행부의 함수 내부 closure를 routed로 센 근사이고, 영역 C/D/E 분류는 주소 기준이다. IO-2는 `pc_routed`와 C++ stop 확정을 쓴다.
- [U] S의 새 code가 없는 seed가 600 frame 안에서 열리지 않는 이유(플레이어 없음 → 카메라 정지 [I])는 P1b로도 바뀌지 않았다(§6.3).
- [F/U] IRQ 전달은 모든 실행에서 H의 `ef2` 대기뿐이었다(P0·P1·P1b·B 합계 전부 `H:ef2`). C·N 구간의 IRQ 전달 경로(C 구간 wait tuple 보정 `release_wait` 포함)는 이 관측에서 한 번도 실행되지 않았다 [U].
- [U] Execute + IRQ 조합의 C++ 동작은 아직 원본 비교가 없다(IO-2가 처음 확인한다).
- [U] 다른 플랫폼에서의 `compared_sha256` 일치(이 관측은 macOS arm64 한 곳).
- [U] `platform.json`의 라이브러리 목록은 `unicorn/lib/` 전체이다(동적 라이브러리 `libunicorn.2.dylib`와 정적 `libunicorn.a`).

## 13. 재현 명령과 파일

작업 트리 루트에서(`.venv` 사용, `MS5_SEED_DIR=artifacts/stage_entry_body`):

```sh
.venv/bin/python tools/observe_animation_machine_io.py --family all --frames 600 --workers 3 --out DIR_A
.venv/bin/python tools/observe_animation_machine_io.py --family all --frames 600 --workers 2 --out DIR_B   # worker 수는 결과에 영향이 없다
.venv/bin/python tools/observe_animation_machine_io.py --compare DIR_A DIR_B   # compared_sha256 와 platform.json 외 파일 비교
diff -rq -x platform.json DIR_A DIR_B
.venv/bin/python tools/observe_animation_machine_io.py --selftest             # 짧은 자체 검사(출력 디렉터리 없음)
```

`--out` 기본값은 `artifacts/animation_machine_io_native`이다. 이 작업의 모든 실행은 공유 `artifacts/`가 아닌 scratch 경로를 썼다(`ms5-scratch/io2/runA`, `runB`).

| 파일 | SHA256 앞 16자리 |
| --- | --- |
| `tools/observe_animation_machine_io.py` | `c9f93abd75303ecd` |
| `docs/analysis/data/io-input-scripts.json` | `d8971c44441bca01` |
| `observation.json` (run A) | `0c251988d8b99e47` |
| `observation.json` (run B) | `0c251988d8b99e47` |

