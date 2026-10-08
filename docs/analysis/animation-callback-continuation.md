# Opcode14 / callback1f의 중첩 continuation

## 기준과 증거 범위

기준 commit은 `c8595e0`이다. canonical BE 프로그램은 `extracted/program/maincpu.decrypted.be.bin`, 8,388,608 bytes, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 고정영역 CPU 주소=ROM 파일 오프셋이다. `load_verified_program`으로 원본 해시를 확인하고 `4a408..4a46b`, `4a57c`, `47672..476bb`, `ca70..ca75`, sound의 stack 명령을 메모리에서 읽었다. ROM·소스·기존 artifact를 수정하거나 빌드하지 않았다.

이 문서의 원본 명령·table 값은 정적 사실이다. **opcode14→callback1f→sound wait 전체 경로는 아직 새 native 실행으로 입증하지 않았다.** 중첩 stack 위치는 아래 실제 명령과 검증된 단독47672 stack의 합성 추론이며, 다음 구현 전 전체 원본 실행으로 확인해야 한다. 다른 callback의 의미는 이 분석에서 확정하지 않는다.

기존 구성요소 근거는 다음과 같다.

- `tools/observe_object_sound_lookup.py`, `artifacts/object_sound_lookup/observation.json` SHA256 `42f093ee7d31dbd3e70b986dd7d7edd7fc409eeb543892ff5c3c6d4494e99f5d`: unpatched47672/ca70/3af8, 277 cases/291 phases, 6 same-CPU chains, 14 resume phases, 실제 high/low wait stack·15R·RAM·live raw lookup. 관찰된 port writes는0이다.
- `tools/verify_object_sound_lookup.py`, `artifacts/object_sound_lookup_execution/verification.json` SHA256 `785bc6249e24f89fc96fa69fabe5365d1cbe2871948a33b07f5e9d58eec2d0b5`: 단독wrapper의 실제 C++277/291 및 이전 실제 출력 기반14회 재개. 이 보고서를 외부 animation frame의 검증으로 확대하지 않는다.
- `tools/observe_animation_word_restore.py`, `artifacts/animation_word_restore/observation.json` SHA256 `f562ac986b13474b7886bf84c4bf5a8fee998239d432a44aa800a2dda12dd8ef`: 원본 `4a222/4a376/4a460 MOVEM.W` 각25조건, 총75조건의 signed16→32 복원. 합성 incoming stack을 둔 단일 명령 증거다.
- 관련 계약: `animation-full-register-boundaries.md`, `animation-execution-initial-contract.md`, `stage-object-output-wrappers-contract.md`. 전체 목표·완료 기준은 `docs/GOAL.md`를 유지한다.

## 원본14의 순서

dispatch가 opcode14를 읽은 직후 A0는 interpreter 상태 주소, A1은 selector BYTE 주소다. 현재 script 위치를 P라 하면 정상 opcode14는 `14 selector BE32operand` 6 bytes이며 저장되는 다음 명령 주소는 P+6이다.

| PC | 명령·효과 |
|---|---|
| 4a408 | `MOVE.L A0,-(A7)` — **interpreter A0** 저장 |
| 4a40a..410 | MOVEQ0 D0, selector BYTE→D0, ADD.W 두 번. selector1f이면 D0=0000007c |
| 4a412..418 | A0=4a500, `MOVE.L (A0,D0.W),D7`. `[4a57c,4a580)` 원본 BE32는 **00047672** |
| 4a41c | `MOVEA.L (A1)+,A0` — operand LONG을 실제로 읽고 A1을4 증가 |
| 4a41e..420 | 다음 명령 A1 LONG 저장, A1=D7(callback 주소) |
| 4a422 | live WORD(A5−7ff0)를 stack에 저장 |
| 4a426..434 | live shadow WORD=0, PVC WORD1000→2ffff2, WORD0→2ffff0 |
| 4a43c | `JSR (A1)` — callback return PC=**4a43e** |
| 4a43e | stack의 bank WORD를 **복귀 시 live A5−7ff0**에 씀 |
| 4a442..458 | callback 반환 D0/D7의 low WORD 저장; live shadow를 다시 읽어 `(WORD+1)<<12`의 low WORD→2ffff2, WORD0→2ffff0 |
| 4a460 | `MOVEM.W (A7)+,D0/D7` — 각각 saved WORD를 full32bit로 **부호 확장** |
| 4a464..466 | saved 다음명령 A1, saved interpreter A0를 LONG 복원 |
| 4a468→4a276 | A1→D6 LONG, `(A0)=D6` LONG으로 상태 포인터 저장 후49ffe dispatch |

selector×4는 BYTE0..255를 MOVEQ0 뒤 두 번 ADD.W하므로0..3fc이며 signed WORD 음수로 넘어가지 않는다. table 선택과 operand LONG 읽기는 서로 다른 접근이다. callback1f는 operand로 받은 A0를 곧 ca70에서 덮지만, **operand fetch 자체를 생략할 근거는 없다**. 잘린/홀수 LONG fetch는 callback 이전 실패다.

1f에서 D7은 callback 주소00047672다. 현재47672/3af8/3ac8 명령은 D7을 변경하지 않으므로 **4a460 직후 D7=00007672**가 된다. 다음 dispatch는 D7을 다시0으로 만들 수 있으므로 이것을 전체49fc6의 최종 D7이라고 일반화하지 않는다. D0 역시 callback 반환 low WORD를 부호 확장하며 high WORD를 보존하는 단순 대입으로 대체하면 안 된다. D1..D6/A2..A4는 callee의 실제 효과를 유지하고, callback의 A0/A1은 위 외부 복원으로 가려진다. 이후4a276은 D6을 다음 script 주소로 다시 덮는다.

## 두 겹의 saved A0와 native stack

S를 **14 handler 진입 시 A7**로 정의한다. 정상49fc6 호출에서는 caller return LONG이 `[S,S+4)`에 있고14는 별도 BSR 없이 dispatch JMP로 진입한다. 아래 배치는 big-endian이며 BYTE predecrement의 A7 보폭은2다.

| 주소 범위 | 저장값 | 보존되는 시점 |
|---|---|---|
| S−4 .. S−1 | outer saved interpreter A0 | 4a408부터4a466까지 |
| S−8 .. S−5 | outer saved 다음 script A1 | 4a41e부터4a464까지 |
| S−10 .. S−9 | outer saved bank WORD | 4a422부터4a43e까지 |
| S−14 .. S−11 | callback return LONG=4a43e | 4a43c JSR부터476ba RTS까지 |
| S−18 .. S−15 | **inner47672 saved source A0=A5−76a4** | sound 경로47682부터4768e까지 |
| S−22 .. S−19 | sound return LONG=4768e | 47688 JSR부터3af8 완료까지 |
| S−24 | sound saved low BYTE | high-byte 단계의3bfa부터3c00까지 |
| S−23 | BYTE push의 미사용 gap | 값은 새 상태 데이터로 해석하지 않음 |
| S−28 .. S−25 | high-byte BSR return LONG=3c00 | high-byte wait 동안 |

따라서 다음 위치가 예상된다.

- callback 진입 A7=S−14. ca70의 임시 JSR return47678은 S−18에 쓰였다가 즉시 복귀한다. 이 위치는 뒤의 inner saved A0로 재사용된다.
- high-byte actual wait `3aea`: A7=S−28, top LONG=3c00, saved low BYTE at A7+4=S−24, sound return4768e atS−22, inner saved source A0 atS−18. outer frame은 그 위에서 그대로 유지된다.
- low-byte actual wait `3aea`: A7=S−22, top LONG=4768e, low BYTE는 **현재 D0.byte**다. high saved BYTE는 이미3c00에서 pop되어 유효 stack 값이 아니다.
- sound 완료 후4768e에서 inner source A0 복원,47690 이후 live BYTE/WORD/lookup 실행.476ba RTS 후4a43e에서 A7=S−10. outer bank pop 후S−8, 임시 MOVEM.W 저장으로S−12, 복원 후S−8, A1/A0 pop 후S, 다음 dispatch로 진행한다.

단독47672 native report는 진입 A7=K일 때 high wait K−14/low wait K−8, inner A0 atK−4, sound return atK−8을 실제로 assert한다. 위 S 배치는 **K=S−14를 대입한 추론**이다. standalone의 captured source A0=10095c와 outer interpreter A0(예:102026)를 혼동해서는 안 된다. standalone incoming D7도 callback 진입의00047672로 자동 대체되는 것이 아니므로, standalone 최종register snapshot을 새 전체 경로의 expected로 붙여 넣어서는 안 된다.

## 재사용 가능한 wrapper와 CLI

`engine/include/ms5/object_sound_lookup.h`의 현재 상태는 다음과 같다.

```cpp
struct ObjectSoundLookupState {
    SoundWordExecutionState sound; // sound.byte.registers = D0..D7/A0..A4
    std::uint32_t a5, a6;
    unsigned int phase;             // 0 idle, 1 sound pending
    std::uint32_t saved_a0;         // inner source A0
};
bool execute_object_sound_lookup(std::vector<std::uint8_t>& ram,
    const std::vector<FixedDataResource>& windows, ObjectSoundLookupState& state,
    std::uint8_t external_status, std::uint8_t& external_reads,
    std::string& error);
```

sound continuation은 `SoundWordExecutionState { byte, saved_low, phase }`의 phase1(high)/2(low)와 `byte.waiting=true`다. wrapper phase1은 saved source A0와 이를 함께 보존한다. phase0에는 saved A0/sound phase/saved low/waiting이 모두0이어야 한다.

`engine/tools/execute_object_sound_lookup.cpp`는 D0..D7 A0..A6 PHASE SAVED_A0 SOUND_PHASE SAVED_LOW WAITING EXTERNAL INPUT_RAM OUTPUT_RAM [FIXED_MS5D...] 순서다. JSON은15R와 phase/saved_a0/sound_phase/saved_low/waiting(bool)/external_reads의21개 key다. 이 CLI는 outer animation stack/PVC/return cursor를 받거나 돌려주지 않는다.

wrapper 재개는 sound만 실행하고 대기가 풀린 뒤 saved source A0를 복원한다. 이어 **live BYTE(A0)→BYTE(A6+7e)**, 그 쓰기 뒤의 **live WORD(A0)**, `[4411e,4421e)` raw WORD lookup, BYTE(A6+12) 쓰기를 실행한다. queue write나 object destination이 source와 alias할 때 prefix에서 cache한 값을 쓰면 틀린다. 기존 same-CPU poisoning/native source-low/queue alias 근거를 재사용할 수 있지만 outer14 전체 증거는 추가해야 한다.

## 제안: 단일 레지스터 상태와 별도 callback metadata

다음은 메인 확정 전 구현 제안이다. 기존 `AnimationExecutionState.sprite.registers`를15R 중13R의 **유일한 canonical storage**로 유지하고 a5/a6도 기존 필드를 사용한다. `ObjectSoundLookupState`를 영속적으로 통째로 추가하여 같은 레지스터 배열을 두 벌 보관하지 않는다.

1. animation phase에 **2=opcode14/selector1f 내부 sound pending**을 추가한다. 기존0=fresh/완료,1=direct04 sprite pending은 유지한다. 다른 callback이나 opcode30 pending으로 재사용하지 않는다.
2. 기존 outer `saved_a0/saved_a1/saved_bank`는14 frame에도 사용하되 의미를 outer interpreter A0/다음 script A1/bank로 고정한다. phase2는 별도 `callback_saved_a0`(inner source), `callback_sound_phase`(1/2), `callback_saved_low`(BYTE), `callback_waiting`을 갖는다. sprite.waiting은 phase2에서false여야 한다.
3. callback invocation/resume 시에만 local `ObjectSoundLookupState`를 구성하여 canonical13R/a5/a6와 inner metadata를 전달한다. 성공한 결과의13R/a5/a6·inner metadata를 다시 canonical state에 반영한다. outer saved fields는 callee가 변경하지 않는다. callback이 완료되면 inner metadata를0으로 지우고4a43e..468 및4a276을 정확히 실행한 뒤 다음 dispatch로 간다.
4. API를 `step_animation_execution(ram, scripts, fixed_windows, state, external_status, external_reads, carry, ports, error)` 형태로 확장하는 안을 제안한다. fixed_windows는 메인이 선택한 단일 wide MS5D 창 **`[4276c,5276c)` 65,536 bytes**를 공급한다. 이 창은0c signed selector의 전체 raw WORD 접근 범위뿐 아니라1f dispatch LONG `[4a57c,4a580)`과 callback raw lookup `[4411e,4421e)`도 포함하며, 각각 필요한 시점에 원본 주소로 읽는다. 기존 object-sound lookup의 작은 MS5D를 추가로 공급하면 겹치므로 이 조합에서는 요구하지 않는다. caller는 기존 fixed MS5D loader를 사용한다. wide window packer/CLI 연결은 별도 담당 작업이며, 이 문서는 그 소비·검증 완료를 주장하지 않는다. scripts는 기존MS5A다.
5. selector1f 및 table value47672만 지원하는 checked subset으로 시작한다. selector BYTE→dispatch LONG→operand LONG의 실제 순서를 지키고 다른 선택자를 성공 no-op로 처리하지 않는다. selector와 table target은 pending 중 재조회하지 않는다. phase2 자체가 복귀 종류4a43e를 식별하므로 일반적인 임의 callback 주소 필드를 새로 만들 필요는 없다.

성공한 pending은 현재까지 RAM/15R/outer+inner metadata/ordered ports를 commit하고 반환carry는 입력값을 보존하며 CLI에서는null로 표시한다. phase2 hold에서는 기존wrapper처럼 `external_reads=0`, callback prefix/lookup/table/operand/outer bank writes가 없어야 한다. high→low에서 다시 기다리면 outer·inner saved A0는 유지하고 sound phase/saved_low/13R만 실제 값으로 바뀐다. 완료 후 필요한 fixed lookup이나 다음 script가 없으면 그 invocation 전체를 되돌려 **입력 phase2와 captured state를 그대로 유지**해야 한다.

## A5/A6와 실패·검증 조건

실제sound 호출/재개만 기존 callee 제약 때문에 A5=108000이 필요하다. source BYTE와 object+7e가 같아 sound를 건너뛴 경로는 actual checked A5-relative 접근을 허용한다. outer bank 접근 역시 reached span/WORD 정렬 검사다. 임의A5를 모든14 진입에서 선제 거절하거나, 반대로 기존sound API를 임의A5 지원이라고 선언하지 않는다.

A6는 callback 완료 시 object+7e/+12의 live destination이며 기다리는 동안에는 읽지 않는다. phase2 hold에 새 A6 range 조건을 만들면 원본 대기와 달라진다. ready 이후 필요한 source WORD 정렬, object destination 또는 lookup 오류는 transaction 실패로 처리한다. resume가 high byte를 commit한 뒤 low byte/finish/outer restore/다음 명령에서 실패해도 호출 전 RAM/15R/phase/saved fields/carry/ports/external_reads를 전부 보존해야 한다. 외부 상태값은 조건부d00046 read에만 사용하고 sound resume에서는 gate를 재평가하지 않는다.

필수 새 native 증거는 전체 unpatched49fc6에서14/1f를 실제 통과한 반환·high hold/release·low hold/release·high→low 두 단계 wait다. 같은 CPU/CCR/A7를 유지하며 위 S 상대 stack을 직접 캡처하고, 현재 callback의 source/object/gates/outer shadow와 live RAM script의 operand를 wait 밖에서 바꾸어 prefix 무재실행과 완료 후 live source 읽기를 구분해야 한다. outer A0/A1/bank 복원,4a460의 signed WORD 복원,4a276 pointer 저장, 이후 script의 live fetch도 비교한다. fixed dispatch table/ROM script는 poisoning 대상으로 수정하지 않으며 원본 불변을 유지한다. 기존단독277/291 결과를 새 whole14 oracle로 합성하지 않는다.

메인 결정이 필요한 사항은 phase2 metadata 이름·CLI 인자 확장, 선택한 wide MS5D의 실제 연결·검증, first1f fixture의 coherent script/object/sound seed, unsupported callback의 오류 범위다. 다른14 callback,3c callback,opcode30 자체의 continuation·전체17 opcode·자연IRQ/scheduler·물리stack mirror/전체CCR는 별도 미완료 범위로 유지한다.
