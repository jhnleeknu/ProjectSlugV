# Stage controller F1c2(area·player 초기화 `479b0..47a94`)의 실제 C++ 실행 검증

Baseline `2aae52f`(U1–U7 + F1a + F1b + F1c1 + F1c2, detached). [F1c 계약](animation-machine-stage-catalog-f1c-contract.md)의 F1c2 24개 code range(1,580바이트, 명령 381개 + 경계 TRAP `4d824`)와 153개 block 시작을 공개 animation-machine API(`engine/src/animation_machine_stage_area.cpp`, SHA256 `dd273339b0a98d71bdf4f1b492e9354079c399f99eea0c7ad4ad078e43eb8d10`)에 연결한 구현을 native 관측과 대조했다. 입력은 통제된 fixture이며 자연 scheduler·자연 IRQ·BIOS 실행·실제 플레이 도달을 뜻하지 않는다. [F] 확정, [I] 추론, [U] 미확인으로 구분한다.

Canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다(fixed CPU 주소 = ROM 파일 offset, bank 영역은 modeled bank로 구분). 원본 ROM은 실행 전후 해시·mtime이 같다.

## 입력 고정

| 항목 | SHA256 |
| --- | --- |
| 계약 `docs/analysis/animation-machine-stage-catalog-f1c-contract.md` | `f374c80f3528d5200aaa870bd66e8a58d09b400db7a84c8ee3a89fddd474a575` |
| native 관측 `artifacts/animation_machine_stage_area_native/observation.json` | `851281ab5037a7daac6d1831d814406057245839271ed3591df225e4ce2b44ca` |
| observer `tools/observe_animation_machine_stage_area.py` | `80f890edced7d875607f9dfbd924ce302e3db12703db1df4e03f1c41bb4bb82a` |
| C++ 실행부 `engine/src/animation_machine_stage_area.cpp` | `dd273339b0a98d71bdf4f1b492e9354079c399f99eea0c7ad4ad078e43eb8d10` |
| 검증기 `tools/verify_animation_machine_stage_area.py` | `80b760b0ee6a1de578ebfc816b51180b7b8bacdae38d430be0509c50d3bbe8c6` |

[F] observer가 고정한 계약 SHA256과 worktree 사본이 같다(수정 사본 없음). 검증기는 이 파일들, observation이 기록한 입력 458개의 SHA256, native blob 5,928개의 파일명=내용 SHA256을 모두 확인한다(비교에 실제로 읽은 blob 5,913개). 계약의 F1c2 바이트 표(24 range)를 원본 ROM과 맞추고, 명령 382개(관측이 해독한 381 + 경계 TRAP `4d824`)에서 block 153개를 capstone 재해독으로 다시 유도해 계약의 시작 153개, 묶인 분기 24개(조건분기 23 + DBRA `4aa72`), FLOW_ONLY 77개와 맞춘다(짝수 PC 790개 = 시작 153 + TRAP 1 + 내부 636). 계약 본문에는 block 바이트 표가 없으므로 block은 명령 흐름에서 직접 만들었다(시작 → 첫 종결 명령·다음 시작·range 끝, 겹침 0, 합 381 명령).

## 실제 대조 범위

[F] Native는 753조건(자연 137 = 129 + 8, release guard 5, runtime 236, area 18, music 16, players 20, players-direct 48, rng 10, rng-guard 14, rng-difference 10, effect 15, trap-boundary 6, trap-guard 2, lookup 10, alloc 4, area-direct 26, sound 16, guard 7, zero-step 153), frame 3,735개(전부 dump), split 단계 63,558개, continuous 단계 3,735개다. 검증기(`tools/verify_animation_machine_stage_area.py`)는 observer를 import·실행하지 않고 동결된 관측만 읽는다.

한 번의 machine 실행 = 한 frame이다(stop `2ac2`, F1a 본문 `47a94`, 경계 `4d824`/`4d7f0`). 각 frame은 직전 **실제 C++ 출력**과 native step에 기록된 선언 host 변경(RAM 쓰기, 선언된 직접 재진입의 PC redirect·A7 delta·`1feffc` 반환 LONG `2ac2`·`104ca4`=`1ff000`, `10dd44`=`ff`, 소리 해제 쓰기)만으로 재개한다. native 입력·기대 레지스터를 넣지 않고, dump 입력이 C++ 쪽 재개 입력과 같은지만 단언한다(3,735/3,735).

| 항목 | 값 |
| --- | --- |
| 조건 | 753 (정상 713 + native guard 행 34 + 차이 행 6) |
| 실제 C++로 재생한 frame | 3,695 정상 + 34 native guard + 6 차이(`rng-original-completes-*`) = 3,735 (전부) |
| continuous 실행 | 3,735 |
| split 단계 | 63,538 (native 63,558; 차이 20 = 아래 의도된 차이 행들의 거부 지점 앞당김, 나머지 조건은 단계 수까지 일치) |
| split 최종 상태 = continuous = native frame | 3,695/3,695 |
| 선언된 직접 재진입(frame 사이) | 2,968 |
| ordered port | 1,386,546 (external read 0) |
| 대기(Waiting) frame | 12 (`sound-wait-*`) |
| zero-step 상태 불변 | 153/153 |
| 실행된 block 시작 | 153/153 (`476ec`, `49a7c`는 typed fixture로 도달) |

Frame마다 비교한 것: native 전체 상태 SHA256(`F1C2-FRAME-STATE-v1` ‖ 64KiB RAM ‖ D0–D7·A0–A7 ‖ PC ‖ bank 번호 ‖ port 수 ‖ ordered port; 같은 식을 C++ 출력에서 다시 계산), RAM·ports SHA256, port 개수, external read 수, PC·A7·16 레지스터, bank, status. 모든 frame이 dump라 저장된 RAM·ports 바이트와 직접 비교했다(3,695). [F] native PVC 이미지는 Unicorn 원시 메모리다. PVC 쓰기가 있는 frame(2,970)은 native 순서 PVC 쓰기 이벤트를 `common.fold_device`로 독립 접어 C++ PVC·bank와 비교했고, PVC 쓰기가 없는 frame(725)은 “입력 PVC에서 `FF8/FF9`만 native 값으로 바뀐다”로 비교했다. 후자에서 native 원시 `FF8/FF9`(예 `a0`/`1000`)는 C++ 이미지(정규화된 레지스터)에 없다. 이전 단계가 쓴 값을 이어 받은 값이라 이 단위의 차이가 아니다(검증기는 frame 사이 이어진 native 값과 같음을 단언한다).

[F] 자연 seed 129개는 기록된 F1c1 관측의 frame 236 출력 상태(`state_sha256`이 기록과 같음)에서 시작하는 한 frame이다. `478de` 재진입이 F1c1 꼬리(`479b0` 도달)를 지나 F1c2 전체(`47a94`)까지 실행한다. 완전 chain seed 8개(`natural-000` 등)는 `47da4`부터 238 frame을 모두 재생한다. runtime fixture 236건(원본 `2790/3ef2/49a1a`로 만든 RAM)은 2–17 frame이다.

### 부분 실행과 체크포인트

[F] native split은 step마다 체크포인트(블록 시작과 black-box 진입 `289e` `28ae` `2a28` `2a48` `3af8` `3c84` `3d44` `3dce` `43dda` `477c2` `49c32` `4ab88` `4d7a6` `6f1c2` `b483e` `e7c36` `e89fa`)의 첫 도달에서 순서대로 멈춘다. 검증기는 같은 순서·같은 정지 PC로 C++ chain을 만들고 모든 단계가 직전 C++ 출력에서 재개한다. 정지는 변환 명령 직후이며 정지 PC 명령은 실행하지 않는다.

- split 최종 상태가 continuous 실행과 같고, continuous가 native frame과 같다(3,695/3,695). port는 단계 출력의 이어 붙임이 continuous와 같고, external read 합도 같다.
- 정지 상태의 레지스터가 native leader 레지스터와 같다: 46,428곳. 첫 도달이 callee 안쪽 호출이라 observer가 leader를 기록하지 않은 13,323곳은 비교 대상이 아니다(수만 센다).
- [F] zero-step(정지 PC = 진입 PC) 153개 native 조건은 상태·RAM·PVC 불변, ports 없음.
- [F] 자기 loop block(`4aa50` 16회, `4aa6e` 256회)은 시작 PC가 정지 PC가 될 수 없으므로 loop 탈출 PC까지의 한 번 실행으로 carry를 관찰한다(874회).

## 대기(Waiting)

[F] 이 fixture 집합에서 native Waiting은 sound ring 가득 참 12건(`sound-wait-*`, `3af8`→`3aea`)이다. C++도 같은 PC·같은 A7에서 `AnimationMachineWaiting`(status 1)이었고 carry는 Unknown(API wait 규약), 선언된 해제 쓰기 뒤 같은 chain에서 재개해 종료 지점에 도달했다. `478de` 게이트 대기와 sprite 대기 `cda4`는 이 fixture 집합에 없다([U], F1a·U 단위 검증이 다룬다).

## Carry

[F] Native는 SR을 읽지 않는다. C는 block 분류로만 확인한다.

- **소비자 5개**(`47716` `47732` `4776c` `1bd34` `1bd96`, 모두 `289e` 복귀 직후 첫 명령이 Bcc): 정지 상태의 Known C는 callee가 만든 값이다. 998곳에서 (1) C++ RAM에서 `289e` 공식(`LONG (A0)`=`270e`이면 Clear, 아니면 Set)으로 다시 유도한 값과 같고, (2) dump된 native PC trace의 실제 분기(`4771a`/`47724`, `47736`/`47740`, `47770`/`47788`, `1bd38`/`1bd3a`, `1bd9a`/`1bd9c`)가 C와 같다. 뒤집은 C가 반대 목적지를 고르는 flip control 998회(`47716` Clear 61·Set 4, `47732` Clear 61·Set 4, `4776c` Clear 89·Set 8, `1bd34` Clear 197·Set 94, `1bd96` Clear 384·Set 96; RAM 변경 없음), 같은 지점의 Unknown C는 정확한 오류 `stage area caller requires known carry`와 전체 보존(998회).
- **FLOW_ONLY 77개**: 모든 시작 block의 단일 block 단계에서 incoming C 1/2를 넣어(probe 80,756회, 쌍 40,378개는 carry 외 모든 출력이 같음) 보존 여부를 실제 C++로 관찰했다. 보존 관찰 77개가 계약 목록과 정확히 같고 나머지 76개는 두 incoming C에서 모두 보존되지 않는다. 소비자 5개는 flip control에서 보존을 관찰했다.
- 정지 지점의 carry 분포(`carry_at_stops`)는 `verification.json`에 있다: Unknown 58,646·Clear 3,501·Set 1,146. `2ac2`/`47a94` 정지는 대부분 Unknown이다.
- 정적: C++ `case` 라벨 = 계약 153 시작, C++ 라우팅 범위 = 24 range(`next.pc!=0x4d824` 제외 1건), `carry_preserving_pc`의 F1c2 항목 = 77. 어긋남 0.

## Native guard 40개(실제 C++ 결과)

모두 전체 출력을 보존한다(입력 RAM·PVC·bank·레지스터·PC·carry 불변, port marker·status 1). continuous 실행·split chain·다른 incoming C 세 가지 모두 같은 오류 문자열이다. 기대 문자열은 C++ bus·dispatch 규칙과 소스 읽기로 먼저 정하고(검증기 안의 명시 표) 실행으로 확인했다.

| guard(native) | C++ error |
| --- | --- |
| `release-guard-136/137/138`(`3c60`), `release-guard-139/140`(`3bb2`, frame 29): 홀수 WORD 읽기 | `program bus requires even WORD/LONG address` |
| `rng-odd`(홀수 RNG 포인터 `10d6b5`), `guard-odd-a6-479b0`, `guard-odd-record-47a1c`, `guard-odd-a0-1bd2e`, `guard-odd-a1-pointer-47724`, `guard-odd-a7-476dc`(LONG push) | `program bus requires even WORD/LONG address` |
| `guard-odd-a5-1bd12`(홀수 WORD **쓰기**) | `invalid animation machine write size/alignment` |
| RNG 정책 행 12개(아래) + `rng-original-outside-*` 4 + `rng-original-completes-*` 6 | `stage area RNG pointer outside work RAM` |
| `481de-trap-no-stop`(`4d824`), `48180-u6-trap-undeclared`(`4d7f0`) | `unsupported animation machine PC` |
| `d760a-28ae-empty-list`, `475ca-players-alive-null-8c`(NULL 자식 포인터, ROM 주소 2) | `unsupported animation machine write device` |
| `guard-node-depth-47770`(`2a28` 비영 object type) | `animation cleanup original TRAP15: nonzero object type` |
| `rng-outside-high-ff10d720` | **오류 없음: C++는 완료한다**(아래) |

[F] `481de-trap-no-stop`은 native `unsupported_code_target`(대상 `4d824`)이고, `4d824`를 stop으로 주면 C++가 성공하며 그 PC에 도달함을 확인했다(선언 stop이 없으면 거부하는 것과 같은 전이). 거부 단계는 native와 같은 split 단계(C++ 성공 단계 수 + 1 = native 단계 수)이며 `rng-original-*` 10행과 high-byte 행만 예외다.

## RNG 포인터 정책(`49a58`, 계약 결정 9)

C++는 `49a58` 진입에서 LONG `10d722`(RNG 포인터)의 **24비트 주소**가 `100000..1fffff`가 아니면 `stage area RNG pointer outside work RAM`으로 거부한다(접근 전, 상태 보존). native 관측은 정책 행과 정책을 끈 원본 행을 짝지어 기록한다.

- **정책 행 12개**(native guard `rng_pointer_outside_ram`, C++ 오류와 같은 검사·같은 단계): 포인터 `0` `30` `fffc0` `200000` `2ffffe` `fffffffe`, 및 `fffd0` `fffd2` `fffe0` `ffff0` `ffffc` `ffffe`(`rng-policy-rejects-*`). 모두 C++ 오류 일치, 입력 상태 보존.
- **의도된 차이 A, 6행**(`rng-original-completes-fffd0/fffd2/fffe0/ffff0/ffffc/ffffe`): 정책을 끈 원본은 RAM 아래 `fffd0..fffff`의 포인터에서도 **frame을 정상 완료**한다(native `2ac2`). C++는 같은 입력을 `49a58` 진입에서 거부한다. 거부 전 단계의 레지스터는 native leader와 같고, 거부는 정확한 오류 문자열과 전체 보존을 가진다. 원본 동작이 아니라 계약 결정 9의 보수적 정책이다.
- **의도된 차이 B, 4행**(`rng-original-outside-zero/rom-30/rom-fffc0/rom-fffce`): 정책을 끈 원본은 ROM·미매핑 주소 `0x30` `0x60` `ffff0` `ffffe`에 `SUB.W`를 써 `unmapped_or_protected`(`49a80`)로 멈춘다. C++는 `49a58` 진입에서 RNG 검사로 거부한다(다른 검사, 더 이른 단계).
- **`rng-outside-high-ff10d720`(상위 바이트 비영)**: native는 Unicorn이 상위 바이트를 마스크하지 않아 관측 불가로 `rng_pointer_high_byte`를 기록했다. **C++는 거부하지 않고 완료한다**: 범위 검사와 bus 접근이 24비트 주소 `10d720`을 쓰고, 레지스터 비교·산술은 32비트라 `A3=ff10d722`는 `A4=0010d722`보다 작지 않아 두 감산(`-6e`)이 모두 적용되어 `A3=ff10d674`로 끝난다. 독립 Python 모델(RAM·D0·A3·A4)과 일치한다(RAM 변경 `10d674..10d676`, `10d724..10d726`). [I] 이 동작은 24개 주소선의 M68000 bus와 같다. native 관측의 뒷받침은 없다([U]).
- API-only 포인터 검사 14건(모델 대조): 완료 9건(`100000` `10d6b4` `10d6b6` `10d71e` `10d720` `10d722` `1ffffe` `010d6b4`형 상위 바이트 `01100000|10d6b4` `ff10d720`), 거부 5건(`0fffff` `fffffe` `200000` `000000`는 RNG 오류, `1fffff`는 홀수 읽기 오류).

## 의도된 차이(수와 규칙)

native 이유와 C++ 결과가 같은 검사가 아닌 행 17건이다. 어느 것도 원본 CPU 예외 rollback과의 동등성을 주장하지 않는다.

1. [F] 정책 끈 원본이 완료하고 C++가 거부: 6행(`rng-original-completes-*`, `fffd0..ffffe`).
2. [F] 정책 끈 원본이 ROM 쓰기로 fault, C++는 RNG 검사로 이른 거부: 4행(`rng-original-outside-*`).
3. [F] native 관측 없음, C++ 24비트 마스크로 완료: 1행(`rng-outside-high-ff10d720`).
4. [F] `481de-trap-no-stop`, `48180-u6-trap-undeclared`: native 이유 `unsupported_code_target` / `unsupported_TRAP`, C++는 경계 PC가 stop 전용이라 `unsupported animation machine PC`(2행).
5. [F] `d760a-28ae-empty-list`, `475ca-players-alive-null-8c`: native ROM 쓰기(`unmapped_or_protected`, 주소 `c`·`2`), C++ write device 거부(2행). [I] 실제 하드웨어에서 ROM 쓰기는 무시되므로 보수적 거부다. 이 경로의 원본 의미는 [U].
6. [F] `guard-odd-a7-476dc`: native 홀수 A7 LONG push 쓰기 주소 오류, C++ 스택 홀수 검사(같은 부류, 메시지 층이 다름).
7. [F] `guard-node-depth-47770`: native 원본 `TRAP #15`, C++ cleanup 단위의 TRAP15 검사.

계약 불일치(observer `contract_discrepancies` 1건): 계약 “자연·runtime 조건은 계약 데이터 창만 읽는다”에 반해 `47a20`(`MOVEA.L 76(A6),A0; MOVE.W 10(A0),D0`)이 창 밖 `dd4be..dd4bf`를 읽는다(자연 4회). 계약 본문의 seed 수 142는 137 + release guard 5로 정정된다(observer 정책).

## API-only 부정·경계 검사

총 719개의 checked 부정(전체 출력 보존), 소비자 정상 control 10개, zero-step 462회, RNG 포인터 14건.

- 계약 범위의 모든 내부 PC 636개: 직접 진입이 `unsupported animation stage area PC`.
- 홀수 PC 53개(range별 첫·끝 홀수 48 + `1` `ffffff` `deadbeef` `479b1` `49a59`): `unaligned animation machine PC`.
- 라우팅되지 않는 PC 25개: 죽은 코드·range 밖 이웃 `47a54` `47a56` `47a5c` `47a62` `49a84` `49a86` `49a8c` `b7a28` `b7a2a` `b7a2c` `4d84e` `4ddde` `4e68e` `b481e` `b4a2a` `46f52` `1bdde` `2eff4` `4aa86`, 경계 `4d824`·`4d7f0`의 stop 없는 직접 진입, 범위 밖 짝수 4개(`0` `ffffffe` `1000000` `deadbee`): `unsupported animation machine PC`.
- 소비자 5개 Unknown C 직접 진입: `stage area caller requires known carry`.
- 소비자 양성 control 10개(5 × C Clear/Set): 목적지로 진행, C 보존, RAM 불변.
- 153개 시작(+ stop 전용 `4d824`) × carry 3종 zero-step 462회 성공(상태·RAM·PVC 불변, port·external read 없음).

## 이전 검증기·시험 중 경계가 바뀌는 항목 [목록만, 수정하지 않음]

F1c2가 24 range를 라우팅하므로 이전에 “지원 밖”이던 기대가 달라질 수 있다. 주 작업 트리 `tools/verify_animation_machine*.py`와 이 worktree의 C++ 시험에서 F1c2 짝수 PC 리터럴을 모두 찾았다(21곳).

- **기대가 깨지는 곳(2곳, 수정 필요)**: `tools/verify_animation_machine_frame_helpers.py` 541행 `reject` 목록의 `0x2efdc`(이제 block 시작 `LEA 10d480.L,A1`; `0x2eff4` 같은 미연결 PC로 이동), `tools/verify_animation_machine_input.py` 861행 `outside_entry` 목록의 `0x4d81c`(이제 block 시작 `CMPI.W #14,D1`; `0x4d84e`로 이동). 두 파일은 이 worktree에 없고 주 작업 트리에 있다.
- 영향 없음: `frame_helpers.py` 39행(`NEW_RANGES`의 배타 끝 `2efdc`), `animation_machine_input_test.cpp` 582행(`49a80`은 레지스터 데이터), 691행(`{0x4d7a6,0x4d81c}` 배타 끝), `animation_machine_stage_catalog_test.cpp`의 `0x479b0` 17곳(F1c1의 stop·callback 값; stop은 라우팅보다 먼저 검사됨).
- [U] 이전 검증기의 전체 재실행은 하지 않았다.

## 재현과 한계

```sh
.venv/bin/python tools/verify_animation_machine_stage_area.py   # artifacts/animation_machine_stage_area_execution/verification.json
make -j4 all test
```

- [F] 검증기를 같은 입력으로 두 번 실행한 `verification.json` SHA256이 같다: `4adc09552dcb22edce8e54783802390c0037395f9eb230fe21707212b53c3656`(바이트 동일, 각 약 6–7분, `STAGE_AREA_WORKERS=3`).
- [F] `make -j4 all test`는 종료 코드 0이다(`FAILED` 0건).
- [F] 검증기는 frame마다 프로세스를 새로 띄우지 않고 ROM 자원을 한 번만 읽는 batch harness(`harness_batch.cpp`, 본체는 `common.HARNESS`와 같고 요청을 stdin으로 받음)를 쓴다. 같은 요청 9건(frame 0, 부분 실행, zero-step, 내부 PC·Unknown carry·홀수 PC·미연결 PC 오류, `4d824` zero-step, 소리 대기)을 one-shot harness와 batch harness로 모두 실행해 JSON·RAM·PVC·ports·오류 문자열이 같음을 매번 확인한다.
- [U] Controlled fixture이며 자연 scheduler, 자연 IRQ, BIOS 실행은 확인하지 않았다. native 시작 SR은 선언 값이고 모든 fixture는 C++에서 Unknown carry로 시작한다. 자식 `4fcb8`/`4fd0a`/`4ff4c`/`d764a` 코드, `4d824`·`4d7f0` TRAP의 실행, 상위 바이트가 비영인 RNG 포인터의 native 동작, 실제 하드웨어의 ROM 쓰기 결과는 미확인이다. native split 중간 RAM은 저장되지 않아(frame 단위 digest와 전체 dump만) 중간 정지 상태는 dump된 leader 레지스터로만 비교한다. 기존 executor는 결과 전체로만 비교하고 내부는 모델링하지 않는다. Checked failure는 API 출력 보존을 뜻하고 원본 CPU fault rollback 동등성은 아니다.
