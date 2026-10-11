# Stage controller F1a(진입 본체·팔레트 gate·dispatcher table·활성화·scene 초기화)의 실제 C++ 실행 검증

Baseline `543a3a4`(U1–U7 + F1a, detached). [F1 계약](animation-machine-stage-controller-f1-contract.md)의 22개 code range(5,608바이트)와 145개 block 시작을 공개 animation-machine API(`engine/src/animation_machine_stage_entry.cpp`, SHA256 `3e0d3fd26cba985708bc2f75dfcb3c404b867b5c0001e4f3d9d6fa3c6e37862d`)에 연결한 구현을 native 관측과 대조했다. 입력은 통제된 fixture이며 자연 scheduler·자연 IRQ·BIOS 실행·실제 플레이 도달을 뜻하지 않는다. [F] 확정, [I] 추론, [U] 미확인으로 구분한다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다(fixed CPU 주소 = ROM 파일 offset, bank 영역은 modeled bank로 구분). 원본 ROM은 실행 전후 해시·mtime이 같다.

## 계약 사본

- [F] observer가 고정한 계약 SHA256은 `e66e9a2127167e332f8595941f90b456696380cd4bdd4b06fda3ab60bea5d12f`(git `cc28e6f`)이고 worktree 사본은 `82c6d30fdfe9e9f973e98663f4fc678c63f0f184c26b210eee9dc0a413b5791c`다. 검증기가 `git show cc28e6f:...`로 옛 판을 복원해 줄 단위로 비교한다: 다른 줄은 정확히 1개(decision 7(c)의 dispatcher 재진입 선언)이고 그 줄 끝에 `(F1a native 관측 보정)` 문장 하나가 덧붙었을 뿐이다. 문장은 `104ca4`=`1ff000`(index `18` 경로 `47b1e`→`480b6`→`2a00`의 `2a02 MOVEA.L -335c(A5),A7`이 읽는 dispatcher 기준 LONG)을 재진입 선언에 포함한다. native observer의 `contract_discrepancies`(contract-understated) 1건과 같은 내용이다.

## 실제 대조 범위

[F] Native는 정상 310조건·guard 25조건, split 23,893단계·continuous 1,427단계다(`artifacts/animation_machine_stage_entry_native/observation.json` SHA256 `c35d0baae047784a3ed3ea7da4d5a758e5a984b5e1c29e461fe594088ced6395`, observer `tools/observe_animation_machine_stage_entry.py` `9735595c447619285e052f003efcf76ceca823c9bfef8799579b3a33a5ef8c90`). 검증기(`tools/verify_animation_machine_stage_entry.py`)는 observer를 import하거나 실행하지 않고 동결된 관측만 읽는다. 저장된 split 단계 payload 파일은 없으므로 continuous payload와 checkpoint snapshot에서 split 단계(RAM before/after, PVC, ports, `trace.json.gz`)를 재구성하고 23,893개 모두 기록된 SHA256과 일치함을 확인했다. native artifact 53,495개(control·snapshot·`source.json`)를 읽어 해시를 검사했다.

단계마다 실제 C++ 출력의 64KiB RAM, 16 register, PC, A7, PVC, bank, ordered port, external read, status를 native와 대조했다. 각 단계는 직전 실제 C++ 출력과 선언된 host 변경(RAM 쓰기, dispatcher 재진입 PC redirect 1,070회·A7 delta 1,070회, sound 해제 write, gate의 선언 IRQ 효과, 총 RAM write 2,734회)만으로 재개한다(재개 22,344회). 재개 입력에 native 기대값 주입은 없다.

| 항목 | 값 |
| --- | --- |
| 조건(정상 310 + guard 25) | 335 (정상 310) |
| 실제 C++로 재생한 split 단계 | 23,761 |
| 첫 checked error에서 멈춘 행의 단계(재생 안 함) | 102 + 오류 단계 5 + guard 단계 25 = 23,893 − 23,761 |
| continuous control 재생 | 1,396 (오류·guard 단계 제외 31) |
| ordered port | 1,708,073 |
| 대기(Waiting) | 23: `3aea` 10, `47af0` gate 13, `cda4` 0 |
| 실행된 block 시작(첫 PC) | 145/145 |

[F] Native 관측은 sprite 대기 `cda4`를 만든 행이 없다(관측 13/10/0). `cda4` 경로는 기존 U 단위 검증이 다룬다. [U] 이 fixture 집합에서의 F1a와 `cda4`의 결합은 미확인.

## 대기와 재개

[F] 대기 23건 모두 C++가 `AnimationMachineWaiting`(status 1)으로 native와 같은 PC와 A7에서 멈췄고(A7 일치 확인), 선언된 변경 뒤 정상 재개했다. `3aea` 대기의 carry는 Unknown(API wait 규약), `47af0` gate 대기의 carry는 `72f4 SUBI.B`가 만든 Clear다(C++가 대기 상태에서 Clear를 유지, 13건). [I] gate의 Clear는 의미 없는 값이므로 소비자는 없다. 재개 시 `47af0`은 FLOW_ONLY block이라 값이 보존된 뒤 `72f0`이 다시 덮어쓴다.

## Carry

- [F] Native는 SR을 읽지 않는다. C는 원본 opcode로 분류한다: `ORI #1,CCR` Set, `ANDI #fe,CCR` Clear, 1a2e8 `CMP.W` 뒤 `EORI #1,CCR`는 native가 읽은 두 WORD의 역 borrow, `72f4 SUBI.B #80,D0`은 native가 읽은 BYTE의 borrow(BYTE<80이면 Set), U3 return-C 루틴의 논리 연산 Clear(`19710`/`1971c` TST, `1938e`/`19596` AND.W)와 이어지는 ORI Set, `289e` 동일 비교 분기 Clear, FLOW_ONLY opcode는 보존, 그 밖은 Unknown. 단계마다 C++ carry가 분류와 같았다(Unknown 21,829, Clear 100, Set 1,832).
- [F] 단계 안에서 C를 만든 BCC/BCS 6,702곳에서 분류 C가 실제 native 다음 PC와 같았다. 소비자가 단계 첫 block이면 직전 실제 C++ 출력의 C(또는 선언 SR 2000/2001)가 실제 native 분기와 같고, 뒤집은 C가 다른 목적지를 고르는 control을 442회 실행했다. 소비자별 flip 횟수: `47af6` 193, `47b86` 104, `47b9c` 4, `47bd4` 8, `1a670` 9, `1996e` 124.
- [F] 6개 소비자(`47af6` `47b86` `47b9c` `47bd4` `1a670` `1996e`) 직접 진입에서 C=Unknown이면 `stage entry caller requires known carry`로 거부하고 전체 출력을 보존한다. Known C 양성 control 12개(`47af6`+Clear는 `47af0`에서 Waiting, 나머지는 분기 목적지로 진행, C 보존·상태 불변).
- [F] FLOW_ONLY 63개: 단일 block 단계에 incoming C 1/2를 넣어(32,118회 probe) 보존 여부를 실제 C++로 관찰했고, probe된 132개 시작에서 결과가 계약 목록과 일치한다(보존 관찰 53개, 나머지 79개는 Unknown 또는 known 생산). 소비자 6개는 flip으로 확인한다. 경로가 incoming C에 의존하는 단계는 probe하지 않는다.
- [F] 정적: C++ `case` 라벨 = 계약 145 시작, C++ 라우팅 범위 = 22개 code range(`e909c` 제외), `carry_preserving_pc`의 F1a 항목 = 63개. 어긋남 0.

## Native guard 25개

실제 C++의 checked error 문자열은 아래와 같고 모두 상태·RAM·PVC·bank·port를 보존한다(continuous 단계 시작에서 돌려도, 다른 incoming C에서도 같은 오류). 기대 문자열은 C++ dispatch·bus 규칙에서 먼저 유도했고, 아래 2건만 실행 뒤에 근거를 확인했다(표시).

| guard | C++ error |
| --- | --- |
| `body-141-live-RAM-record-reread`, `table-index-01/03/ff-odd-pc`, `guard-odd-return-long` | `unaligned animation machine PC` |
| `table-index-22/24/30/32-internal-pc` | `unsupported animation stage entry PC` |
| `event-tag-55-trap-undeclared`, `guard-bad-stop-return-4939c` | `unsupported animation machine PC` |
| `event-odd-table-pointer`, `guard-odd-a7-gate-entry`, `guard-odd-a6-record-pointer`, `guard-odd-record-pointer`, `guard-odd-a4-at-47aca`, `guard-odd-a0-1a422`, `guard-odd-a1-199e4` | `program bus requires even WORD/LONG address` |
| `guard-clear-17292-rom`, `guard-clear-17292-past-ram`, `guard-rom-write-a5` | `unsupported animation machine write device` |
| `guard-clear-17292-odd` | `invalid animation machine write size/alignment` |
| `event-loop-forever-00-limit0-step0` | `animation machine block budget exceeded` |
| `guard-banked-script-b3-zero-f788c` (확인 후) | `unsupported animation script placement PC` |
| `guard-banked-script-b3-nonzero-3c96a` (확인 후) | `unsupported animation stage entry PC` |

## 의도된 차이(수와 규칙)

1. [F] 소비자에 Unknown C로 닿는 계산 JMP: `47b02 JMP 47b06(PC,D0.W)`에서 index `80`/`96`/`ce`는 `47b86`/`47b9c`/`47bd4`로 가고, C++는 C가 Unknown이라 `stage entry caller requires known carry`로 거부한다. native는 `MOVEQ #0,D0`가 C를 지워 BCC를 그대로 진행한다. 3행(오류 단계 4번째, 각 22단계 미재생). continuous 실행도 같은 오류.
2. [F] block 시작이 아닌 계산 JMP 목적지: index `fa`→`47c00`(묶인 BEQ), `28`→`47b2e`(명령 중간). native는 그대로 실행하고 C++는 `unsupported animation stage entry PC`(같은 이유로 index `22/24/30/32`는 native도 guard 처리). 2행, 미재생 17 + 19단계.
3. [F] `47af6`(C Clear 선언 SR 2000)이 BCC로 `47af0`에 닿고 그곳이 요청 stop일 때, native split은 일반 stop이고 C++는 Waiting(status 1)을 보고한다(PC·register·RAM 동일). 1행, continuous 실행도 Waiting.
4. [F] Guard 3건은 native 이유가 달라 C++ 오류가 다르다: 관측기 watchdog(60,000 명령, 원본에 상한 없음) vs C++ 1,000,000 block 상한(2건 중 하나) 또는 U5 checked script PC 거부(1건), native Unicorn의 32비트 주소 `01000006` 읽기 fault vs C++의 24비트 마스크(ROM 벡터 영역 읽기 뒤 비시작 PC에서 거부)(1건). [I] 24비트 마스크는 원 68000 bus에 가깝다.
5. [F] 홀수 PC, 계약 밖 PC, odd 주소 접근은 native fault와 같은 부류의 checked error이며 원본 CPU rollback과의 동등성은 주장하지 않는다.
6. [I] e909c TRAP: native는 stop-only 경계, C++는 executor 없음. 선언 stop에서 멈추는 행(`event-tag-55-trap-boundary` 등)은 성공, 선언 없이 닿으면 `unsupported animation machine PC`(guard).

## API-only 부정·경계 검사

- 계약 범위의 모든 내부 PC 2,658개(명령 시작 2,282 + 피연산자 WORD 376): 직접 진입이 `unsupported animation stage entry PC`, 전체 출력 보존.
- Range 밖 PC 11개(`ddf98` `ddfa4` `ddfdc` `ddf90` `72fa` `7300` `e8a3a` `e8a46` `9068` `4e26c` `ca5c`): `unsupported animation machine PC`. Range마다 첫·끝 홀수 PC 44개와 임의 홀수 5개(`unaligned animation machine PC`), 범위 밖 짝수 PC 4개. `e909c` 직접 진입 2개(`unsupported animation machine PC`).
- 145개 시작 × carry 3종 zero-step 435회 성공(상태·RAM·PVC 불변).
- 총 checked 부정 2,755 (guard 25 포함).

## 이전 검증기·시험 중 경계가 바뀌는 항목 [목록만, 수정하지 않음]

F1a가 `47a94..47c5a`, `72f0`, `1a5a4..1a73c`, `17292..1829a`, `19768`, `19938..19978`, `199d4`, `19b50`, `19dee..19e60`, `1a07a`, `1a3c8`, `1a414..1a442`, `e8a1c..e8a3a`, `e905c..e90ca`, `477a2`, `ddf9a`, `362a..3650`, `9060`, `4e254`, `ca56`, `ca76`, `c3c0`을 라우팅하므로 이전에 “지원 밖”이던 아래 기대가 달라진다.

- C++ 시험은 F1a 커밋에서 이미 갱신됐다(buffer_cue `e8a1c`→`e8a1a`, card_menu_open `364e`, motion_walk `19768/19938`, scene_core 6개 PC, scene_update `17292/1a07a/19e5e`, script_placement `19770 19e5e 1a084 1a440` 등).
- Python 검증기(수정 필요, 각 worktree의 해당 파일):
  - U7 `verify_animation_machine_buffer_cue.py` 824행 `outside_entry`의 `0xe8a1c`(F1a 블록 시작이 되어 실행됨, 기대 `unsupported animation machine PC`가 깨짐).
  - U3 `verify_animation_machine_motion_walk.py` 10·655·968·1189·1205행: `19938..19978`의 4개 “extra range” 행이 expected-unsupported였으나 `19938/19944/19956..`는 F1a 시작이라 실행되고(비시작은 stage entry 오류), 968행 `outside`의 `19768 19772 19938 19944 19976`도 같은 이유.
  - U2 `verify_animation_machine_scene_core.py` 785행 `outside`의 `199d4 19b50 19dee 1a3c8`(시작), 같은 줄의 `199d6`(내부 PC → stage entry 오류), `19b94`(시작).
  - U4 `verify_animation_machine_scene_update.py`: 78–79행 `guard-bad-stop-1a78c-on-init-entry`(기대 `unsupported animation machine PC`, “RTS to 1a6a2 (no executor)”). 같은 상태를 호스트 측 BSR 뒤 `1a7a8`에서 돌려 보니 이제 `1a78c`에 도달해 성공한다(경계가 오류에서 성공으로 이동). 717행 `outside`의 `1a07a` `1a6a2`(시작), `1a6a2`·`1a69e`.
  - U5 `verify_animation_machine_script_placement.py` 840행 `outside`의 `19768 1a07a 1a414 1a5a4`(시작), `1a43c` stop 기반 guard `guard-bad-stop-never-reached-init`: 오류 문자열은 그대로 `unsupported animation machine PC`이나 실패 PC가 `1a43c`에서 뒤로 이동.
  - 정지 경계 stop을 쓰는 U4 40행(`1a6a2`)·U5 114행(`1a43c`)은 stop 검사가 라우팅보다 앞서 영향 없음.
- [U] 위 목록은 소스 문자열·native guard target·재생 3건(U4/U5)에서 얻었다. U1·U6 검증기는 F1a PC를 negative로 쓰지 않는다고 확인했으나(grep), 전체 재실행은 하지 않았다.

## 재현과 한계

```sh
.venv/bin/python tools/verify_animation_machine_stage_entry.py   # artifacts/animation_machine_stage_entry_execution/verification.json
make -j4 all test
```

- [F] 검증기를 같은 입력으로 두 번 실행한 `verification.json` SHA256이 같다(값은 최종 보고에 기록).
- [F] `make -j4 all test`는 오류·경고·FAILED 문자열 없이 끝났다(종료 코드는 캡처하지 못함).
- [U] Controlled fixture이며 자연 scheduler, 자연 IRQ, BIOS 실행, `cda4` 결합은 확인하지 않았다. gate의 IRQ palette 효과는 `107ded` bit7 최소 효과의 선언이다. 기존 executor(U1–U7, cleanup, palette_bind, exit, screen, fade_card, hud, sound)는 결과 전체로만 비교하며 내부는 모델링하지 않는다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다. C 분류의 U3 논리 clear 4곳(`19710 1971c 1938e 19596`)은 68000 규칙(TST/AND는 C를 지움)에서 온 [I]이며 모든 경로가 실제 native 분기로 교차 확인됐다.
