# 객체 callback F4 U20: 지형 점프 표 `44ade`(96 entry 전체와 대상 leaf `44c62..45174`), C3 `492d0`·`497a6` 계약 초안 — U20 분할 제안과 첫 부분 U20a

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U20 행과 그 "메인 결정"이다. 단위 형식과 규약은 U08 계약(`animation-machine-objects-u08-contract.md`, SHA256 `fd484c1cc1bcd87a87f69892451a1cfd36528db5797cca7298514c8c1f703d8d`, 같은 꼴의 점프 표 `4483a`와 그 계산 PC 정책), U08b 계약(SHA256 `a75aa7748c9acba9f9f16e97cefbed77308fe429d0103e8683f2f9bdd5c0d7a8`, `44ade` 호출자 `46384` `46498`), U05 계약(SHA256 `77fd4062f3935d0e8b2989ad65bed395f43fa7bd37f33309c7a29fa9f512dafc`, `497a6` 반환 C 소비자 `c6ad6` `c6b20` `c6b7a`), U11 계약(SHA256 `ab51cd6d422c9a97fc9a705b4d11254716b69bebd4610a93c0cd58c656940d7d`, `45302 BNE 44c62`)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기·DBcc fall-through, JSR/BSR 복귀점, 범위 안의 `MOVE.L #imm,(A6)` callback 진입)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 4: 지형 `JMP d(PC,D7.W)` 표는 index 상한을 정적으로 확정하고 표 전체를 옮긴다.
- 결정 5: 단위는 함수 본문 전체다. 실행되지 않는 callee, 다른 단위의 PC는 실행부 없는 경계(`unsupported animation machine PC`)다.
- U01~U18 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`Scc`/`MOVEM`/`DBcc`, Z만 바꾸는 `BTST`/`BSET`/`BCLR`/`BCHG`)만인 block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C를 소비자에서 쓰려면 native 분기 결과로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U20의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u20`(HEAD `a3e0cdc` = U18까지 통합, `engine/src/animation_machine.cpp` SHA256 `a56a8f46c588482a75bcc6bc22504d9ac728e6a10e7c54a8d2d18ff784929218`, routing 규칙 55개)을 참조했다. 동시에 진행하는 U19(작업 트리 `metalslug-u19`)의 PC는 경계로만 둔다(U20a는 U19 PC를 부르지 않는다). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/u20/u20.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **U20 전체는 표를 옮기면 269 block이다.** 범위 문서 U20 행(함수 14개 `449a2` `44ade` `44b6e` `44c46` `44c52` `452de` `492d0` `497a6` `858d8` `85b6c` `85b9e` `85bcc` `85c04` `85c48`, "91 block")을 지금 routing으로 다시 계산했다.
  - `449a2`(U08a 표 `4483a` 범위 `447be..44ade` 안)와 `452de..45330`(U11 범위 `45176..4578a` 안)은 이미 routing되어 새 block이 아니다(다시 routing하지 않는다).
  - `44b6e` `44c46` `44c52`는 표 `44ade`의 entry다. 범위 문서는 표의 자연 관측 entry와 그 대상만 셌다. 결정 4대로 표 96 entry와 대상 본문 전체를 옮기면 `44ade..45176`이 173 block이다.
  - 나머지는 C3 `492d0` 1, `497a6` 3, 객체 callback `849f4` 4 + `858d8` 계열 88(설치 callback `859b2` `85aa4` `85af8` `85b6c` `85b9e` `85bcc` `85c04` `85c48` 포함)이다.
  - 합계 173 + 4 + 92 = **269**. 지시 상한(~220)을 넘으므로 아래처럼 나누고 **첫 부분 U20a만 구현**한다(결정 1).
- [F] **U20a = 177 block**: 지형 점프 표 함수 `44ade`(JMP 1, 표 entry 96, 대상 leaf 76)와 C3 `492d0` 1, `497a6` 3. 코드 3 범위 1,712바이트, 504명령이다. 미해독·TRAP·묶인 분기·SUBX/ADDX/DIVx/MULx·I/O port·bank 읽기는 없다. routing 짝수 PC는 856개, 내부 PC는 679개다.
- [F] **U20b(제안, 미구현) = 92 block**: 객체 callback `849f4` `858d8` 계열(아래 "U20b 제안"). bank window LONG `2000e0` 읽기 5곳, carry 소비 3곳(`849fe` `8592c` `85bec`), U20a `492d0` `497a6`을 부른다.
- [F] **표 index 상한(결정 4).** `44ade JMP 44ae2(PC,D7.W)`의 D7 산출은 U08 계약의 `447be`와 같다: `D7.W ∈ {4k | 0≤k<60(hex)} ∪ {160}`. 호출 site 2곳(U08b `46384` `46498`, 모두 BSR.W)은 바로 앞에서 `CMPI.W #160,D7; BEQ`로 `160`을 거른다. 표 `44ae2..44c62`는 정확히 96(=`60`) entry(`BRA.W`, opcode `6000`, 4바이트)이고 `44ae2+160`=`44c42`(`BRA.W 44c62`)도 그 안이다. 표 바로 뒤 `44c62`(`MOVE.L #80000000,D6; RTS`)는 대상 공통 "높이 없음" 경로다.
- [F] U20a 자체로는 base 프레임 패스의 새 완주 seed가 없다(RNG 초기화 400 frame 변형에서는 표 entry `44b62`→`44c70`을 쓰는 seed 0 1 127~135가 이 단위의 막힘이었다; 아래 "자연 시작 상태"). 범위 문서의 새 seed 36·37은 `858d8` 계열(U20b)이 첫 미연결 callback이고, 그 실행 중 `44ade`(entry `44b6e`)·`492d0`·`497a6`도 쓴다. U20a+U20b가 함께 있어야 풀린다.
- [F] **carry**: U20a 안에 C 소비 block은 없다. `44ade` 호출 2곳의 다음 명령은 `SUBI.L #80000000,D6`(C를 덮음)이라 표 대상 leaf의 C는 소비되지 않는다(Unknown). known 생산 block은 `497a6`(`TST.B`: Clear)과 `497b0`(`ORI.B #1,CCR`: Set) 2개다. ROM의 `JSR 497a6.L` 23곳 다음 명령은 모두 `BCC.W`/`BCS.W`(소비자)이고, 그중 이미 routing된 소비자는 U05 `c6ad6` `c6b20` `c6b7a`다.
- [F] 읽는 자료: work RAM BYTE `549e(A5)`(`44c70` `44c80`), BYTE `10fd92`(`497a6`, 절대 주소), node BYTE `15(A6)`(`492d0` 읽기·쓰기). ROM 자료 읽기·bank window 읽기·I/O port 쓰기·bank 변경은 없다. 표 entry는 코드이며 자료로 읽지 않는다.
- [F] 자연 도달(F4 범위 scratch 재생 `f4scope`, TB 기준): base(`dyn`)에서 `44ade` `44b6e` `44c62` `44c70` `44c76`은 seed 36·37, `492d0`은 36 37 42 43, `497a6` `497b0`은 30 31 36 37이다. RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`)에서는 `44ade`가 25 seed(0 1 18 19 36 37 76 77 96~99 102~105 127~135), entry `44b62` `44b6e` `44c46` `44c4a` `44c52`와 대상 `44c62` `44c70` `44c76`, `497a6`/`497b0`이 18 seed다. 나머지 대상 leaf는 자연 미도달이며 typed fixture로 덮는다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **U20 분할(269→177+92).** 권고: U20a(core: 표 `44ade` 전체와 C3 `492d0` `497a6`)를 먼저 이 작업 트리에서, U20b(객체 callback `849f4`·`858d8` 계열)를 다음 단위로 한다. 경계는 U08a/U08b와 같은 core 대 callback이고 둘 다 ≤~220이다. U20b는 U20a의 `492d0` `497a6`을 부르고 `43ea4`(U04)→…→`46372`(U08b)→`44ade` 경로로 표를 쓰므로 U20a 뒤가 자연스럽다. 대안: 269 block을 한 단위로(비권고: 상한 초과), 또는 callback 쪽을 먼저(비권고: seed 36·37은 어느 쪽만으로도 풀리지 않고, callback 쪽은 `44ade`·`497a6`이 경계라 typed fixture가 그 앞에서 멈춘다).
2. **표 `44ade`의 C++ 형태.** 권고: U08 결정 2(F1 결정 3의 계산 PC 정책)를 그대로 쓴다. `44ade`는 PC=`44ae2`+sext(`D7.W`)로만 옮긴다(32bit 덧셈, 대상 범위 `3cae2..4cae0`). 표 96 entry의 `BRA.W` 대상은 C++ 상수 배열로 옮겨 적고(코드 바이트를 자료로 읽지 않음), entry PC는 모두 block 시작이다. 상한 안 index(`0..17c`, 4의 배수)는 모두 구현된 entry이고, `180`은 `44c62` block, 그 밖의 값은 routing이 정한다: 표 안 displacement WORD(`44ae2+4k+2`)와 대상 본문 내부는 `unsupported animation objects u20 PC`, 홀수는 `unaligned animation machine PC`, U08 범위(`447be..44ade`)면 U08 실행부, 범위 밖은 `unsupported animation machine PC`다. 원본은 index 검사가 없으므로 원본 동작과 같은 이동이다. 단 대상이 명령 중간 WORD이면 원본 CPU는 그 WORD부터 디코드해 계속 가지만 C++는 checked 오류로 멈춘다(의도된 차이, 상한 밖 D7에서만 생김). `D7.W`=`fffc`이면 원본과 C++ 모두 `44ade`로 되돌아가 끝없이 돈다(C++는 기존 block 한도 오류 `animation machine block budget exceeded`).
3. **`497a6` known C.** 권고: `497a6` block(`TST.B 10fd92.L; BNE.W 497b4`)을 Clear 생산자, `497b0`(`ORI.B #1,CCR`)을 Set 생산자로 둔다. 이제 U05 `c6ad6` `c6b20` `c6b7a`는 실제 반환 C를 받는다(BYTE `10fd92`≠0이면 C=0, 0이면 C=1). typed fixture는 반환 LONG을 U05 소비자 PC로 두고 native 분기로 C를 확인한다.
4. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u20.cpp`의 `animation_objects_u20_block`. 오류는 `unsupported animation objects u20 PC`(내부 PC)다. U20a에는 carry 소비자가 없으므로 `objects u20 caller requires known carry` 문자열은 쓰지 않는다(소비자 없는 오류 문자열을 두지 않는 관례; U20b가 소비자 3곳과 함께 도입한다).
5. **무효화 탐침**(F4 test 경계 관례대로 수정한다).
   - `engine/tests/animation_machine_objects_u05_test.cpp`: `interior()`의 `outside[]` `0x497a6`(이제 U20 block 시작) → RAM 탐침. `boundaries()`의 "497a6 경계가 stop이 아니면 rollback" 6행 → stop만 확인(rollback 삭제).
   - `engine/tests/animation_machine_objects_u08_test.cpp`: `interior()`의 `outside[]` `0x44ade` `0x44ae0`(U20 block 시작·내부) → RAM 탐침. 오류 fixture `error-table-boundary`(`4483a`, `D7.W`=`2a0` → `4483e+2a0`=`44ade` 경계 기대; 이제 `44ade`가 다시 `44ae2+2a0`=`44d82`(U20 내부)로 간다) → `44ade` stop만 확인.
   - `engine/tests/animation_machine_objects_u11_test.cpp`: 오류 fixture `error-table-before`(`45176`, `D7.W`=`fffa` → `4517a-6`=`45174`, 이제 U20 내부) → `45174` stop만 확인.
   - `engine/tests/animation_machine_objects_u08b_test.cpp`: fixture `error-boundary-44ade`(`46384`에서 `44ade` 경계 rollback 기대), `BOUNDARIES[]`의 `0x44ade`(stop이 `44ade`인 fixture의 rollback 재실행), `interior()`의 `outside[]` `0x44ade` → RAM 탐침 rollback 또는 stop만 확인.
   - 공유 관측 도구 `tools/observe_animation_machine_objects_g1.py` 67행 `BOUNDARY` 5번 `0x497a6`은 이제 routing된다. 공유 도구는 이 단위에서 고치지 않고 보고한다.
   - U11 test의 `44c62` stop(`t5d-1` `45302-set`, 794~801행)은 이미 stop만 확인하므로 그대로 유효하다.

## 원본 바이트 근거

[F] U20a 코드 3 범위 합계 1,712바이트. 범위 순서로 이어 붙인 SHA256 `daabc6cf62f4f62a0b819aa7887346bf634b54af9e7800dbbcea7570e28f96be`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `44ade..45176` | 1,688 | `ca97bcbf2f82d1ff120ae2f81bb04a53ffa6e2cb9efb956866198328a50c5ea2` | `44ade` JMP, 표 `44ae2..44c62`(SHA256 `d2c554cda779e03e141775d99262eb0c36fdad505b9be6b71dd5edd0bc29dd8a`), 대상 `44c62..45176` |
| `492d0..492d8` | 8 | `5bc331ed9e7f36f75e8eddb1fffdc5e9b6e0e0d4fb046517484557c49703e045` | C3 `492d0` |
| `497a6..497b6` | 16 | `2db7512f1c9c6f21b1646b488143abc2dab4772990f558580d6a28dbe2288c2c` | C3 `497a6` |

- [F] 범위 밖 이웃: `44ade` 앞 `447be..44ade`(U08a, 앞 표 `4483a`의 대상 `44ad2` 꼬리 `RTS`), `45176..`(U11 표 함수 `45176`), `492c8..492d0`(U12 `492ae..492d0`), `492d8`(다른 함수 `BCHG #1,15(A6); RTS`, 범위 문서 어느 단위에도 없음), `49794..497a6`(다른 함수 꼬리), `497b6..`(U11 `497b6..497f0`).
- [F] 참조: `44ade`는 U08b `46384` `46498`(BSR.W) 2곳, `44c62`는 표 entry 7곳과 대상 leaf의 `BCC`/`BCS` 28곳, `44c70`/`44c80`의 `BNE.B` 2곳, U11 `45306 BNE.W`. `492d0`은 fixed ROM `JSR 492d0.L` 56곳(다음 명령 `MOVE.L` 52, `MOVE.B` 2, `MOVE.W` 1, `JSR` 1; C 소비 없음), `497a6`은 `JSR 497a6.L` 23곳(다음 명령 `BCS.W` 13, `BCC.W` 10; 전부 C 소비. routing된 것은 U05 `c6ad6` `c6b20` `c6b7a`).

## 점프 표 `44ade`와 index 상한(결정 4)

- [F] `44ade`: `JMP 44ae2(PC,D7.W)`(`4efb 7002`: brief extension, base = 확장 WORD 주소 `44ae0` + 2). 이동 PC = `44ae2`+sext(`D7.W`).
- [F] 호출자 D7: `46384`(U08b `46372` 본문, `4637c CMPI.W #160,D7; BEQ 463d8` 뒤)와 `46498`(`46490 CMPI.W #160,D7; BEQ 46624` 뒤). U08b 계약대로 그 D7은 `447be` 결과(`4k`, k<`60`, 또는 `160`) 또는 그것을 저장한 `54b0(A5)`이고 `+5a..+68`에서 `174`/`178`/`17c`는 그대로이거나 `160`이 된다. 따라서 `44ade`에 들어오는 `D7.W`는 `4k`(k<`60`, k≠`58`)이다. [U] U08 계약과 같이 진입 D7 경로의 전 호출 closure는 확인하지 않았다(결정 2의 계산 PC 정책이 그 밖의 값도 원본과 같이 옮긴다).
- [F] 표 `44ae2..44c62`: 96개 `BRA.W`. index→대상(16진 k):
  - `00..0f`: `44f5c` `45154` `45066` `45044` `44f78` `45132` `45088` `45022` `44f9a` `45110` `450aa` `45000` `44fbc` `450ee` `450cc` `44fde`
  - `10..1f`: `44fde` `450cc` `450ee` `44fbc` `45000` `450aa` `45110` `44f9a` `45022` `45088` `45132` `44f78` `45044` `45066` `45154` `44f5c`
  - `20..2f`: `44c70` `44c80` `44c80` `44c70` `44cde` `44d38` `44cf0` `44c96` `44cc6` `44d20` `44d08` `44cae` `44cae` `44d08` `44d20` `44cc6`
  - `30..3f`: `44c96` `44cf0` `44d38` `44cde` `44d68` `44d92` `44d7a` `44d50` `44d50` `44d7a` `44d92` `44d68` `44daa` `44dba` `44dba` `44daa`
  - `40..4f`: `44dd0` `44e30` `44e0e` `44dec` `44dec` `44e0e` `44e30` `44dd0` `44e52` `44f3a` `44ed4` `44eb2` `44e6e` `44f18` `44ef6` `44e90`
  - `50..5f`: `44e90` `44ef6` `44f18` `44e6e` `44eb2` `44ed4` `44f3a` `44e52` `44c62` `44c62` `44c62` `44c62` `44c62` `44c6a` `44c62` `44c62`
  - 서로 다른 대상 46개.
- [F] 대상은 D0·D1 LONG에서 D6(높이)을 내는 leaf다. D4는 scratch로 남는다(값도 비교 대상). 범위 판정에서 벗어나면 `44c62`(D6=`80000000`)로 간다. [I] U11 계약의 표 `45176` 대상과 같은 꼴(하위 19bit 소수부 마스크 `7ffff`)이고, 호출자는 `SUBI.L #80000000,D6; BEQ`로 "높이 없음"을 거른다.

## block 목록과 실행 의미

[F] 177 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. LONG 연산은 32bit wrap이다. `ASR.L #n`은 부호 bit를 채우는 산술 이동, `LSL.L #n`은 논리 이동이다. `CMPI.L #lim,D4; BCC`는 무부호 D4≥lim이면, `BCS`는 무부호 D4<lim이면 분기한다.

**`44ade` 1 + 표 entry 96**
- `44ade`: `JMP 44ae2(PC,D7.W)` (계산 PC, 결정 2)
- `44ae2+4k`(k=`0..5f`): `BRA.W` 위 표의 대상 (각 1 block, FLOW_ONLY)

**공통·특수 대상 6**
- `44c62`: `MOVE.L #80000000,D6; RTS` ("높이 없음")
- `44c6a`: `TST.L D2; BLT.W 44c80` (→`44c70`; LONG 부호 음수면 `44c80`)
- `44c70`: `TST.B 549e(A5); BNE.B 44c62` (→`44c76`)
- `44c76`: `MOVE.L D0,D6; ANDI.L #7ffff,D6; RTS`
- `44c80`: `TST.B 549e(A5); BNE.B 44c62` (→`44c86`)
- `44c86`: `MOVE.L #7ffff,D4; MOVE.L D0,D6; AND.L D4,D6; NOT.L D4; ADD.L D4,D6; RTS` (D4=`fff80000`, D6=(D0 AND `7ffff`)+`fff80000`)

**범위 판정 없는 기울기 leaf 14** — 모두 `MOVE.L #7ffff,D6; MOVE.L D6,D4; AND.L D1,D4; [SUBI.L #k,D4;] [ASR.L #s,D4;] AND.L D0,D6; ADD.L/SUB.L D4,D6; RTS`

| 진입 | `SUBI.L #k` | `ASR.L #s` | 결합 |
| --- | --- | --- | --- |
| `44c96` | `ffe80000` | 2 | SUB |
| `44cae` | `fff00000` | 2 | SUB |
| `44cc6` | `fff80000` | 2 | SUB |
| `44cde` | 없음 | 2 | SUB |
| `44cf0` | `80000` | 2 | ADD |
| `44d08` | `100000` | 2 | ADD |
| `44d20` | `180000` | 2 | ADD |
| `44d38` | `200000` | 2 | ADD |
| `44d50` | `fff80000` | 1 | SUB |
| `44d68` | 없음 | 1 | SUB |
| `44d7a` | `80000` | 1 | ADD |
| `44d92` | `100000` | 1 | ADD |
| `44daa` | 없음 | 없음 | SUB |
| `44dba` | `80000` | 없음 | ADD |

**범위 판정 leaf 28 × 2 block = 56** — 머리 block `MOVE.L #7ffff,D6; MOVE.L D6,D4; AND.L D1,D4; [SUBI.L #k,D4;] CMPI.L #lim,D4; BCC.W/BCS.W 44c62`(→꼬리), 꼬리 block `LSL.L #s,D4; AND.L D0,D6; SUB.L/ADD.L D4,D6; RTS`. `BCC`(무부호 D4≥lim이면 `44c62`)인 것은 꼬리가 SUB, `BCS`(무부호 D4<lim이면 `44c62`)인 것은 꼬리가 ADD다. 꼬리의 `AND.L D0,D6`은 들어온 D6(머리에서 온 경우 `7ffff`)을 쓴다.

| 머리 | `SUBI.L #k` | `CMPI.L #lim` | 분기 | 꼬리 | `LSL.L #s` | 결합 |
| --- | --- | --- | --- | --- | --- | --- |
| `44dd0` | 없음 | `40000` | BCC | `44de4` | 1 | SUB |
| `44dec` | `40000` | `40000` | BCC | `44e06` | 1 | SUB |
| `44e0e` | `80000` | `fffc0000` | BCS | `44e28` | 1 | ADD |
| `44e30` | `40000` | `fffc0000` | BCS | `44e4a` | 1 | ADD |
| `44e52` | 없음 | `20000` | BCC | `44e66` | 2 | SUB |
| `44e6e` | `20000` | `20000` | BCC | `44e88` | 2 | SUB |
| `44e90` | `40000` | `20000` | BCC | `44eaa` | 2 | SUB |
| `44eb2` | `60000` | `20000` | BCC | `44ecc` | 2 | SUB |
| `44ed4` | `80000` | `fffe0000` | BCS | `44eee` | 2 | ADD |
| `44ef6` | `60000` | `fffe0000` | BCS | `44f10` | 2 | ADD |
| `44f18` | `40000` | `fffe0000` | BCS | `44f32` | 2 | ADD |
| `44f3a` | `20000` | `fffe0000` | BCS | `44f54` | 2 | ADD |
| `44f5c` | 없음 | `10000` | BCC | `44f70` | 3 | SUB |
| `44f78` | `10000` | `10000` | BCC | `44f92` | 3 | SUB |
| `44f9a` | `20000` | `10000` | BCC | `44fb4` | 3 | SUB |
| `44fbc` | `30000` | `10000` | BCC | `44fd6` | 3 | SUB |
| `44fde` | `40000` | `10000` | BCC | `44ff8` | 3 | SUB |
| `45000` | `50000` | `10000` | BCC | `4501a` | 3 | SUB |
| `45022` | `60000` | `10000` | BCC | `4503c` | 3 | SUB |
| `45044` | `70000` | `10000` | BCC | `4505e` | 3 | SUB |
| `45066` | `80000` | `ffff0000` | BCS | `45080` | 3 | ADD |
| `45088` | `70000` | `ffff0000` | BCS | `450a2` | 3 | ADD |
| `450aa` | `60000` | `ffff0000` | BCS | `450c4` | 3 | ADD |
| `450cc` | `50000` | `ffff0000` | BCS | `450e6` | 3 | ADD |
| `450ee` | `40000` | `ffff0000` | BCS | `45108` | 3 | ADD |
| `45110` | `30000` | `ffff0000` | BCS | `4512a` | 3 | ADD |
| `45132` | `20000` | `ffff0000` | BCS | `4514c` | 3 | ADD |
| `45154` | `10000` | `ffff0000` | BCS | `4516e` | 3 | ADD |

**C3 `492d0` 1, `497a6` 3**
- `492d0`: `BCHG.B #0,15(A6); RTS` (BYTE 읽기·쓰기, bit 0 반전, Z만 바뀜)
- `497a6`: `TST.B 10fd92.L; BNE.W 497b4` (→`497b0`; C=0 생산)
- `497b0`: `ORI.B #1,CCR` (→`497b4`; C=1 생산)
- `497b4`: `RTS`

(수: 1 + 96 + 6 + 14 + 56 + 1 + 3 = 177.)

## 구현 범위와 규약

- routing 3 범위(위 표): `44ade..45176`, `492d0..492d8`, `497a6..497b6`. 짝수 PC 856개 중 block 시작 177, 내부 679. 내부 PC 직접 진입은 `unsupported animation objects u20 PC`다. 범위 이웃은 기존 실행부(U08·U11·U12) 또는 routing 밖(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)이다.
- **FLOW_ONLY 99개**(C 보존): `44ade`(JMP), 표 entry 96(`BRA.W`), `492d0`(BCHG+RTS), `497b4`(RTS).
- **known carry 생산 2개**: `497a6` Clear, `497b0` Set. 그 밖 76개(대상 leaf 전부; `MOVE`/`AND`/`SUBI`/`ASR`/`LSL`/`ADD`/`SUB`/`NOT`/`TST`/`CMPI` block)는 Unknown이다.
- **소비자 없음.** U20a는 `objects u20 caller requires known carry`를 내지 않는다.
- 계산 PC: `44ade`는 결정 2. 그 밖의 제어 이동은 정적이다.
- 스택: RTS 복귀 LONG만 읽는다. 쓰기 없음.
- I/O port 쓰기 없음. bank 변경·bank 읽기 없음. work RAM 밖 쓰기(`492d0`의 A6), 미해결 읽기는 기존 checked 오류다.

## U20b 제안(미구현, 다음 단위)

[F] 92 block, 코드 3 범위 944바이트(SHA256 이어 붙임 `fe0e7e83f2c53270dfed54d37011a924517d470a33bf762a2fc1bf2db2bc15b7`): `849f4..84a14`(공유 꼬리 `849f4`: `LEA 84982(PC),A0; JSR 1ab02` → `849fe BCC` → `84a02 BSET #7,61(A6); CLR.W 54(A6); JMP 2a00` / `84a12 RTS`), `858d8..8597c`, `85980..85c6c`. 범위 문서 callback `858d8`과 설치 callback `859b2` `85aa4` `85af8` `85b6c` `85b9e` `85bcc` `85c04` `85c48`.
- 출구 호출(모두 routing됨): U05 `1ab02`, fade_card `28ae`(자식 callback `85c6c`, 쓰기만) `2a00`, U04 `43ea4`, interpreter `49f8c` `49fc6`, U18 `4be2c`, U11 `4be06`, U17 `4bfa4`, U02 `8ebe`, U20a `492d0` `497a6`.
- carry 소비 3곳: `849fe BCC`(`1ab02` 반환: U05 `1ab7a` Clear / U01 `1aafc` Set), `8592c BCC`(`497a6`), `85bec BCC`(`49fc6` 반환).
- 자료: bank window LONG `2000e0`(`85984` `85ac2` `85b3e` `85b9e` `85c04`, `MOVE.L 2000e0.L,22(A6)` 뒤 `MOVEA.L d(A1),A1`로 `5c`/`c`/`18`/`4` LONG), fixed ROM WORD 표 `84976+2·7a(A6)`(`85936`).
- seed 36·37의 첫 미연결 callback이 `858d8`이다(base 기준선). U20a+U20b로 두 seed가 풀릴지는 U20b에서 다시 잰다.

## 의존·경계

- [F] U20a → 기존: 없음(U20a는 다른 실행부를 부르지 않는다. 모든 경로가 `RTS`로 끝난다).
- [F] 다른 단위 → U20a: U08b `46384` `46498`(`BSR 44ade`), U11 `45306`(`BNE 44c62`), U05 `c6ad0` `c6b1a` `c6b74`(`JSR 497a6`), 그 밖 routing 밖 호출자(위 "참조").
- [F] 경계: 없음. U19 PC는 U20a 안에서 나오지 않는다.

## 자연 시작 상태(읽기 전용 기록)

- [F] 기준 C++ 차분(이 작업 트리 `a3e0cdc`, `tools/verify_animation_machine_scheduler_f4.py`를 scratch 출력으로 실행): 일치 pass 11,458개·node 89,558개, 불일치 0, 자연 완주 103 seed. seed 36·37의 첫 미연결 callback은 `858d8`, seed 30·31은 `be0c4`, 42·43은 `b6338`이다. RNG 초기화 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py`): 일치 pass 27,846개·node 192,355개, 불일치 0, complete 69.
- [I] U20a만으로 base 완주 seed 수는 늘지 않는다(위 "요약"). 차분은 불일치 0·회귀 0과 node 일치 수 비감소로 확인한다.
- [F] 작업자 scratch 측정(구현 후, 같은 도구): base 일치 pass 11,458·node 89,558, 불일치 0, 자연 완주 103(변화 0). RNG 초기화 400 frame: 일치 pass 32,004·node 232,659, 불일치 0, complete 80(새 complete 0 1 127 128 129 130 131 132 133 134 135, 잃은 것 0).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 177 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산자 known, 그 밖 Unknown), zero-step, 내부 679 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만. 표 96 index × 3 carry가 옮겨 적은 대상에 닿는다. 상한 밖 D7(표 내부 WORD, 홀수, U08 범위, 자기 자신 `fffc`)의 결과. 생산자 C는 U05 소비자 `c6ad6`(반환 LONG)의 native 분기로 확인한다. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력)로 비교한다.
- 실제 ROM 차분: U08b `46372`/`46384`/`46488`/`46498` 경로와 U18 `b631c`/`b6764`/`4be2c` 경로(→`4be34`→`46372`)에서 실제 `44ade` 표, U05 `c6aa6`→`c6ad0`→`497a6`→`c6ad6`, `492d0`을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0. RNG 초기화 400 frame 차분: 불일치 0, complete 69 이상.

## 미확인·범위 밖

1. [I] `44ade` 대상은 지형 칸 안의 기울기(1/8~2 비율)로 D0 축 위치에서 높이 D6을 낸다. BYTE `549e(A5)`≠0이면 특수 대상 `44c70`/`44c80`이 "높이 없음"을 돌려준다. 게임 의미는 미확인이다.
2. [U] BYTE `10fd92`의 의미와 쓰는 곳(`497a6`이 0이면 C=1)은 확인하지 않았다.
3. [U] 진입 D7의 전 호출 closure(위 "점프 표")는 확인하지 않았다.
4. [U] U20b의 본문 의미와 실행 결과는 U20a 밖이다.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/u20/`(`u20.py` block·범위·SHA 계산, `u20b.py` U20b 제안 계산, `leaves.py` leaf 변수 추출, `scope.py` `scope2.py` `body.py` `trav.py` `hroute.py` `owner.py` `u20dis.py`, `refs.py` `nextins.py` `probes.py` `dynreach.py`; 저장소 밖).
