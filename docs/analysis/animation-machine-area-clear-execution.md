# Stage controller F1b(area clear `47da4`)의 실제 C++ 실행 검증

Baseline `e79f95c`(U1–U7 + F1a + F1b, detached). [F1b 계약](animation-machine-area-clear-f1b-contract.md)의 6개 code range(376바이트, 81명령)와 39개 block 시작을 공개 animation-machine API(`engine/src/animation_machine_area_clear.cpp`, SHA256 `30333c627a4fee5babf1fbf32a3400faa1f4819646d032f6c3e444cbd2ff10a7`)에 연결한 구현을 native 관측과 대조했다. 입력은 통제된 fixture이며 자연 scheduler·자연 IRQ·BIOS 실행·실제 플레이 도달을 뜻하지 않는다. [F] 확정, [I] 추론, [U] 미확인으로 구분한다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다(fixed CPU 주소 = ROM 파일 offset, bank 영역은 modeled bank로 구분). 원본 ROM은 실행 전후 해시·mtime이 같다.

## 입력 고정

| 항목 | SHA256 |
| --- | --- |
| 계약 `docs/analysis/animation-machine-area-clear-f1b-contract.md` | `6bd2e96395e73814b7d4308f03d027eb1fb7be3c17ef8019491512340f66d4f2` |
| native 관측 `artifacts/animation_machine_area_clear_native/observation.json` | `88b6b075fb184b37d59cbf454dd4a9cb4eec7f9b4d4dddc2586b993a1e4fc73e` |
| observer `tools/observe_animation_machine_area_clear.py` | `afeb5669e119d6c65776e3c36f58f99443d0c7a41ccfd2e085651ccbb3f20201` |
| C++ 실행부 `engine/src/animation_machine_area_clear.cpp` | `30333c627a4fee5babf1fbf32a3400faa1f4819646d032f6c3e444cbd2ff10a7` |

[F] observer가 고정한 계약 SHA256과 worktree 사본이 같다(수정 사본 없음). 검증기는 이 네 파일, observation이 기록한 입력 252개의 SHA256, native blob 8,882개의 파일명=내용 SHA256을 모두 확인한다. 계약 문서의 바이트 표(6 range)·block 표(39)·묶인 분기(6)·FLOW_ONLY(16)·block 시작(39)을 원본 ROM과 capstone 재해독으로 다시 맞춘다(명령 81개, TRAP·X 소비·CCR 생산 명령 없음, 짝수 PC 188개 = 시작 39 + 내부 149).

## 실제 대조 범위

[F] Native는 256조건(자연 137, release guard 5, 변형 17, callback 18, player 8, direct 6, transition 5, sound 3, zero-step 39, guard 18), frame 37,444개, split 단계 117,537개, continuous 단계 37,444개, 전체 dump frame 7,516개다. 검증기(`tools/verify_animation_machine_area_clear.py`)는 observer를 import하거나 실행하지 않고 동결된 관측만 읽는다.

한 번의 machine 실행 = 한 frame이다(stop `2ac2` 또는 마지막 frame의 `477ee`). 각 frame은 직전 **실제 C++ 출력**과 native step에 기록된 선언 host 변경(RAM 쓰기, 선언된 직접 재진입의 PC redirect·A7 delta·`1feffc` 반환 LONG `2ac2`, `10dd44`=`ff` 같은 외부 생산자 쓰기, 소리·sprite 해제 쓰기)만으로 재개한다. native 입력·기대 레지스터를 넣지 않고, dump가 있는 frame에서만 C++ 쪽 재개 입력이 native 입력 바이트와 같은지 단언한다(7,516/7,516).

| 항목 | 값 |
| --- | --- |
| 조건 | 256 (정상 230 + guard 행 26) |
| 실제 C++로 재생한 frame | 37,418 정상 + 26 guard = 37,444 (전부) |
| continuous 실행 | 37,444 |
| split 단계(체크포인트마다 정지) | 117,537 (native와 단계 수 완전 일치, frame별로도 일치) |
| split 최종 상태 = continuous = native frame | 37,418/37,418 |
| 선언된 직접 재진입(frame 사이) | 37,183 |
| ordered port | 8,995,253 |
| 대기(Waiting) frame | 1 (`sound-ring-full-0`, `3aea`) |
| 실행된 block 시작(첫 PC 또는 정지 PC) | 39/39 |

Frame마다 비교한 것: native 전체 상태 SHA256(`F1B-FRAME-STATE-v1` ‖ 64KiB RAM ‖ D0–D7·A0–A7 ‖ PC ‖ bank 번호 ‖ port 수 ‖ ordered port; 같은 식을 C++ 출력에서 다시 계산), RAM·ports SHA256, port 개수, external read 수, PC·A7·16 레지스터, bank, `FF8/FF9` 값, status. dump가 있는 7,490개 정상 frame은 저장된 RAM·ports 바이트와 직접 비교한다. [F] native PVC 이미지는 Unicorn 원시 메모리라 마지막에 쓴 `2ffff0/2ffff2` 값 그대로이고 C++ 이미지는 정규화된 `FF8/FF9`다. dump frame은 native 순서 PVC 쓰기 이벤트를 `common.fold_device`로 독립 접어 C++ PVC·bank와 비교했고(7,490), dump가 없는 29,928 frame은 “입력 PVC에서 `FF8/FF9`만 native 값으로 바뀐다”로 비교했다.

[F] 자연 seed 137개는 각 237 frame(`477ee`)이고 선언 write는 frame 188 뒤 `10dd44`=`ff` 한 건이다. 변형은 계약 “typed 변형”(alive 238, fail 237, half 238, 대기 3 frame 추가 241, dfail/dhalf/dgood 237, dd44-early 236 …)과 같은 길이다. 5개 callback 직접 재진입, player node 변형, `1c5bc`/`1c5d8`/`47e0a` 직접 진입(선언 SR 2000/2001), `8c16`·`3af8` 경로, transition case 77은 모두 같은 방식으로 재생했다.

### 부분 실행과 체크포인트

[F] native split은 step마다 체크포인트(블록 시작과 `289e` `28ae` `2a48` `3af8` `8c16` `9060` `480bc` `49c20`)의 첫 도달에서 순서대로 멈춘다. 검증기는 같은 순서·같은 정지 PC로 C++ chain을 만들고 모든 단계가 직전 C++ 출력에서 재개한다. 정지는 변환 명령 직후이며 정지 PC 명령은 실행하지 않는다.

- split 최종 상태가 continuous 실행과 같고, continuous가 native frame과 같다(37,418/37,418). port는 단계 출력의 이어 붙임이 continuous와 같고, external read 합도 같다.
- 정지 상태의 레지스터가 native leader 레지스터와 같다: 12,984곳(dump frame, 체크포인트 첫 도달이 observer가 기록한 leader일 때). 첫 도달이 `480bc` 안쪽 호출(예: U1 안의 `289e`)이라 observer가 leader를 기록하지 않은 7,116곳은 비교 대상이 아니다(수만 센다).
- [F] zero-step(정지 PC = 진입 PC) 39개 native 조건은 상태·RAM·PVC 불변, ports 없음.

## 대기(Waiting)

[F] 이 fixture 집합에서 native Waiting은 `sound-ring-full-0`의 `3aea` 1건뿐이다(ring이 가득 차서 `3af8`→`3aea`). C++도 같은 PC·같은 A7에서 `AnimationMachineWaiting`(status 1)이었고 carry는 Unknown(API wait 규약), 선언된 해제 쓰기(WORD `104d74`=`ffff`) 뒤 같은 chain에서 재개해 `2ac2`에 도달했다. [F] 다섯 callback 대기(`47de4` `47e22` `47e62` `47e70` `47e92`)는 Waiting이 아니라 `480bc`→`480f0 RTS`→`2ac2` 정지이고 모두 이 방식으로 재생됐다. [U] sprite 대기 `cda4`는 이 fixture 집합에 없다(기존 U 단위 검증이 다룬다).

## Carry

[F] Native는 SR을 읽지 않는다. C는 block 분류로만 확인한다.

- **소비자 3개**(`1c5bc` `1c5d8` `47e0a`): 정지 상태의 Known C가 callee가 만든 값이다. 358곳에서 (1) `1c5bc`/`1c5d8` 340곳은 `289e` 공식(`LONG (A0)`=`270e`이면 Clear)으로 C++ RAM에서 다시 유도한 값과 같고, (2) 358곳 모두 dump된 native PC trace의 실제 분기(`1c5cc`/`1c5c0`, `1c5e8`/`1c5dc`, `47e1c`/`47e12`)가 C와 같다. 뒤집은 C가 반대 목적지를 고르는 flip control 358회(`1c5bc` Clear 163·Set 8, `1c5d8` Clear 168·Set 5, `47e0a` Clear 4·Set 10; `47e0a`는 `SCC.B 62(A6)` 한 바이트만 달라짐 확인), 같은 지점의 Unknown C는 정확한 오류 `area clear caller requires known carry`와 전체 보존(358회).
- **FLOW_ONLY 16개**: dump frame의 단일 block 단계에서 incoming C 1/2를 넣어(probe 9,068회, 쌍 4,534개는 carry 외 모든 출력이 같음) 보존 여부를 실제 C++로 관찰했다. 보존 관찰 16개가 계약 목록과 정확히 같고 나머지 23개는 두 incoming C에서 모두 보존되지 않는다(Unknown 또는 callee가 known 생산). 소비자 3개는 flip control에서 보존을 관찰했다.
- 직접 정지에서의 carry 분포(`carry_at_stops`)는 `verification.json`에 있다: `289e` 안쪽 정지 Unknown 37,213·Clear 1·Set 1, `2ac2` 정지 Unknown 37,207, `47e40`(28ae 복귀 직후) Set 156·Clear 8, `1bee4` Clear 162·Set 1 등.
- 정적: C++ `case` 라벨 = 계약 39 시작, C++ 라우팅 범위 = 6 range, `carry_preserving_pc`의 F1b 항목 = 16(FLOW_ONLY + Scc). 어긋남 0.

## Native guard 26개(실제 C++ 결과)

모두 전체 출력을 보존한다(입력 RAM·PVC·bank·레지스터·PC·carry 불변, port marker·status 1). continuous 실행·split chain·다른 incoming C 세 가지 모두 같은 오류 문자열이다. 오류가 나는 split 단계도 native와 같다(C++ 성공 단계 수 + 1 = native split 단계 수, 26/26). 기대 문자열은 C++ bus·dispatch 규칙에서 먼저 정하고(검증기 안의 명시 표), 네 가지 접근 규칙만 첫 실행 뒤 확인했다(★: 홀수 WORD **쓰기**는 `invalid animation machine write size/alignment`, 읽기는 `program bus requires even WORD/LONG address`).

| guard(native) | C++ error |
| --- | --- |
| `release-guard-136/137/138`(`3c60` 홀수 WORD 읽기, frame 0), `release-guard-139/140`(`3bb2`, frame 29) | `program bus requires even WORD/LONG address` |
| `transition-case77-partial`, `transition-case77-full`, `guard-trap15-cleanup-47da4`(`2a52 TRAP #15`) | `animation cleanup original TRAP15: nonzero object type` |
| `guard-odd-a6-47dd8`, `guard-odd-a6-47e1c`, `guard-odd-a6-47e56`(★쓰기), `guard-odd-child-a0-47e12`, `guard-odd-child-a0-47e40`(★쓰기) | `invalid animation machine write size/alignment` |
| `guard-odd-a6-47de4`(읽기), `guard-odd-a7-47da4`(JSR push), `transition-case77-full-type0` | `program bus requires even WORD/LONG address` |
| `guard-rom-a6-47dd8`, `guard-rom-child-a0-47e12`, `guard-a5-zero-47da4`, `a6-102000-seed0`, `guard-28ae-pool-null-47e30` | `unsupported animation machine write device` |
| `guard-stop-not-477ee`, `guard-no-2ac2-stop-d72fe`, `guard-no-2ac2-stop-e4234`, `guard-bad-return-long`, `observe-odd-a6-byte-47e22` | `unsupported animation machine PC` |

[F] `unsupported_code_target` 4건(`guard-stop-not-477ee` `guard-no-2ac2-stop-d72fe` `guard-no-2ac2-stop-e4234` `guard-bad-return-long`)과 `observe-odd-a6-byte-47e22`는 native가 멈춘 이동 목적지(`477ee` `d72fe` `e4234` `4939c` `047af000`)를 stop으로 주면 C++가 성공하며 그 PC에 도달함을 확인했다(선언 stop이 없으면 거부하는 것과 같은 전이).

## 의도된 차이(수와 규칙)

native 이유와 C++ 오류가 같은 검사가 아닌 guard 7건이다. 어느 것도 원본 CPU 예외 rollback과의 동등성을 주장하지 않으며, 모두 같은 split 단계에서 거부된다.

1. [F] **계약 주장 반박**(2건, `transition-case77-partial`, `transition-case77-full`): 계약 결정 6의 “transition case 77을 `47de4`까지 부분 실행으로 연결”은 성립하지 않는다. 기록된 case 77 RAM의 WORD `100c04`=`f2ee`(≠0)라 `47db0`→`2a48`이 `2a52 TRAP #15`에 닿는다(native guard `unsupported_TRAP`). C++는 같은 지점에서 `animation cleanup original TRAP15: nonzero object type`로 거부한다(5단계 성공 + 1). 선언 `100c04`:=0을 더한 `transition-case77-partial-type0`는 `47de4`에서 정상 종료하고 native와 같다. 같은 분류의 [F]로 observer의 `contract_discrepancies` 1건과 같은 내용이다.
2. [F] `transition-case77-full-type0`: 합성 case 77 RAM(대부분 0)에서 native Unicorn은 `1a2c0`의 WORD 쓰기가 32비트 주소 `80a902e9`(홀수·미매핑)에서 fault한다. C++는 주소를 24비트로 마스크하고 같은 split 단계(21 + 1)에서 홀수 WORD/LONG 접근 검사로 거부한다.
3. [F] `a6-102000-seed0`: 선언 A6=`102000` 문맥에서 29 frame 뒤 `28ae`가 주소 `4`(ROM)에 LONG을 쓴다. native는 `unmapped_or_protected`, C++는 write device 거부(3 + 1단계).
4. [F] `guard-28ae-pool-null-47e30`: observer 발견 사항(계약 본문에 없음). `28ae`가 개수 검사(D0=`14` < 개수)를 통과하지만 free list 머리 `104c9c`=0이면 원본은 `0 + c`(ROM 벡터 영역)에 쓴다. native는 `unmapped_or_protected`, C++는 write device 거부. [I] 실제 하드웨어에서 ROM 쓰기는 무시되므로 보수적 거부다. 이 경로의 원본 의미는 [U](계약에 없다).
5. [F] `observe-odd-a6-byte-47e22`: 홀수 A6(`100b31`)에서 native Unicorn은 홀수 LONG 읽기를 허용해 `047af000`으로 전이한 뒤 fetch가 fault한다. C++는 같은 PC `047af000`에 도달하며(stop 확인) 선언 stop이 아니므로 `unsupported animation machine PC`로 거부한다.
6. [F] `guard-odd-a7-47da4`: native는 홀수 A7의 LONG push 쓰기 주소 오류, C++는 스택 접근의 홀수 검사(같은 부류, 메시지 층이 다름).

## API-only 부정·경계 검사

총 179개의 checked 부정(전체 출력 보존), 정상 control 6개, zero-step 117회.

- 계약 범위의 모든 내부 PC 149개(`47e0e`·묶인 분기 6개 포함): 직접 진입이 `unsupported animation area clear PC`.
- 홀수 PC 17개(range별 첫·끝 홀수 12 + `1` `ffffff` `deadbeef` `47e0b` `47e0f`): `unaligned animation machine PC`.
- 라우팅되지 않는 이웃 PC `4b6f4` `1c5ea` `1bef8` `ca50` `477ee`, 범위 밖 짝수 4개(`0` `ffffffe` `1000000` `deadbee`), `47e9a` 직접 진입의 `477ee`(선언 stop 없음): `unsupported animation machine PC`(10개).
- 소비자 3개 Unknown C 직접 진입: `area clear caller requires known carry`.
- 소비자 양성 control 6개(3 × C Clear/Set): 목적지로 진행, C 보존, `47e0a`는 `62(A6)` 한 바이트만 변경.
- 39개 시작 × carry 3종 zero-step 117회 성공(상태·RAM·PVC 불변, port·external read 없음).

## 이전 검증기·시험 중 경계가 바뀌는 항목 [목록만, 수정하지 않음]

F1b가 `47da4..47eac`, `4b6e4..4b6f4`, `1c5b0..1c5ea`, `1bee4..1bef8`, `ca48..ca50`, `9056..9060`을 라우팅하므로 이전에 “지원 밖”이던 기대가 달라질 수 있다.

- C++ 시험은 이 baseline에서 이미 갱신됐다: motion_walk `outside[]`의 `47da4`→`5f002`(주석 771행), input의 `outside[]`의 `1bee4`→`1bef8`(주석 883행).
- Python 검증기: **U6 `tools/verify_animation_machine_input.py` 861행** `outside_entry` 순회에 `0x1bee4`가 있다. 이제 F1b block 시작(`JSR 49c20`)이라 직접 진입이 실행되어 기대 `unsupported animation machine PC`가 깨진다(수정 필요, `0x1bef8` 같은 미연결 PC로 이동). 이 worktree에는 해당 파일이 없고 주 작업 트리에 있다.
- 영향 없음: `verify_animation_machine_transition.py` 322행과 `animation_machine_transition_test.cpp` 72행은 `47da4`를 **stop**으로 쓴다(stop 검사가 라우팅보다 앞선다). `animation_machine_input_test.cpp` 690행의 `{0x1bec0,0x1bee4}`는 U6 range의 끝(배타)이라 영향 없음.
- [U] 위 목록은 주 작업 트리 `tools/verify_animation_machine*.py`와 이 worktree의 C++ 시험에서 F1b 짝수 PC 리터럴을 찾은 결과다. 이전 검증기의 전체 재실행은 하지 않았다.

## 재현과 한계

```sh
.venv/bin/python tools/verify_animation_machine_area_clear.py   # artifacts/animation_machine_area_clear_execution/verification.json
make -j4 all test
```

- [F] 검증기를 같은 입력으로 두 번 실행한 `verification.json` SHA256이 같다: `fe0de167ad0d036609b33f627e594461f5632bfef96de60faa7cf0431052be0f`(바이트 동일).
- [F] `make -j4 all test`는 종료 코드 0이다(오류·FAILED 없음).
- [F] 검증기는 frame마다 프로세스를 새로 띄우지 않고 ROM 자원을 한 번만 읽는 batch harness(`harness_batch.cpp`, 본체는 `common.HARNESS`와 같고 요청을 stdin으로 받음)를 쓴다. 같은 요청 8건(frame 0, 부분 실행, zero-step, 내부 PC·Unknown carry·홀수 PC·미연결 PC 오류, 소리 대기)을 one-shot harness와 batch harness로 모두 실행해 JSON·RAM·PVC·ports·오류 문자열이 같음을 매번 확인한다.
- [U] Controlled fixture이며 자연 scheduler, 자연 IRQ, BIOS 실행은 확인하지 않았다. 자식 `e4234`/`d72fe`(`2ac2` stop이 막음), frame 사이 IRQ 효과, `10db85/87` `100967` `107def` `10dd44` 및 player node bit의 의미는 미확인이다. native split 중간 RAM은 저장되지 않아(frame 단위 digest만) 중간 정지 상태는 dump된 leader 레지스터로만 비교한다. 기존 executor(U1–U7, cleanup, fade_card, F1a `9060`, sound, exit, input)는 결과 전체로만 비교하고 내부는 모델링하지 않는다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다.
- 계약 `2abe` 재진입 변형(선택 C)은 검증하지 않았다(채택 여부가 열려 있고 native에 기록이 없다).
