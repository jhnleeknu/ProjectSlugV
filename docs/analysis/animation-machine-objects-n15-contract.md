# 객체 callback F4 N15(옛 R12 일부·R13 일부): 노드 callback `708a6`, `7090a` 상태기계의 설치 callback `71032`(설치 `710e4`)·`71a80` `71bc0` `71d48` `71dd6`, 공용 꼬리 `72d66`, helper `493bc`(TRAP 경계) `7028e` `7054c` `705ca`, 노드 callback `76d18`(설치 `76d56` `76d66` `76d94` `76e2a` `76e90`)·helper `76f98`·interpreter 명령 callback `76f1e` 계약 초안

**상태: 계약 초안(작업자 Claude Opus 5.5 / high). 메인 결정 전이다. 아래 "작업자 검증 기록"은 이 초안대로 구현한 scratch 기록이다(커밋하지 않음).**

범위 근거는 재범위 문서 `animation-machine-object-callbacks-f4-rescope.md`(SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 메인 결정 1~5와 N15 행(191 block, `493bc..493fc` `7028e..702cc` `7054c..70606` `708a6..708ba` `71032..7120e` `71a80..71e8c` `72d66..72e8e` `76d18..76ff2`, callback `708a6` `71032` `71bc0` `71c90` `71d0a` `76d18` `76d94`, 경계 callee `70302` `70594` `cc778` `cc8b4` `e9112`, TRAP `493c6`, bank 2, 새 seed 없음, 미실행 설치 14(+170), 옛 R12 177·R13 57)이다. 메인 지시: N04가 가진 `71c90..71d48`과 공유 꼬리 `72dd2..72e8e`는 다시 routing하지 않는다. 경계 `70302` `70594` `cc778`(실행되지 않는 표 루틴으로 가는 tail). 이 단위만으로 완주 seed는 늘지 않는다(N17의 선행; seed 76 77 98 99 104 105가 `708a6`에서 멈춘다). 재범위 scratch `final.out`의 N15 함수 진입은 `493bc` `7028e` `7054c` `705ca` `708a6` `71032` `710e4` `71bc0` `71c90` `71d0a` `76d18` `76d56` `76d66` `76d94` `76e90` `76f98`(16개; `71c90` `71d0a`은 N04 범위)다. 단위 형식과 규약은 N13 계약(SHA256 `e93eeddb8701c3e90216ae1f1c55a047726e3242b3e82959c0d21edc9e29d632`; interpreter 명령 callback 포함), N09 계약(BRA 대상 Bcc를 선행 block에 묶음 `af7a0`), N04 계약(SHA256 `3a87155a37c93679aae5f849b1deac3ec766a32f2142a5a1e21743ad6ef6c813`; `71c90..71d48`·`72dd2..72e8e` 소유, 선행이 여럿인 Bcc는 각 선행에 묶음), N06 계약(TRAP은 실행부 없는 checked 경계)과 N11 계약(PC 상대 자료 표 읽기·표 값 설치는 자료 읽기)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 JSR/BSR 대상, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback, 범위 안의 interpreter 명령 callback 표 값)로 정한다. Unicorn TB 분할은 쓰지 않는다. 같은 flag를 쓰는 연속 Bcc 1곳(`71c4e BEQ`+`71c52 BCS`)을 묶는다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC는 경계다. 범위 안의 참조되지 않는 코드는 routing하지 않는다(`71b42..71bc0`, `72da6..72dac`, `72dcc`, `76f14` `76f16`; 아래 결정 2). 참조되는 범위 안 설치 callback과 interpreter 명령 callback(`76f1e`)은 넣는다.
- 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`/`NEG`/`EXT`/`SWAP` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다; `MOVE`는 C를 0으로 만든다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc/`ST`)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block, callee C를 소비하는 단독 Bcc는 FLOW_ONLY다. block 사이 N/Z 재계산은 predecessor가 하나일 때만 쓴다(N15에는 없다). 다른 block의 Bcc를 쓰려면 선행에 묶는다(결정 3·4). 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다. known C는 실제 ROM 소비자를 복귀 주소로 둔 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N15의 코드와 고정 자료는 모두 `<100000`이라 CPU 주소와 file offset이 같다. banked window 자료는 LONG `2000d0` `2000d4`(animation 자료 포인터)와 그 포인터가 가리키는 bank 안 LONG(`4(A1)` `1c(A1)` `20(A1)` `24(A1)` `28(A1)` `3c(A1)` `40(A1)` `44(A1)`)이다("자료"). 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n15`(HEAD `89f8fec` = N13까지 통합, `engine/src/animation_machine.cpp` SHA256 `365a2dc54dda4feddea0c51ac094514b2c85e2f6655a92d1f2ac050d3734804a`, routing 규칙 70개; `engine/src/animation_machine_interpreter.cpp` SHA256 `3b91b9fae2a93a820c6de9b276bbb9b2cbe9b6bb859d607e7f977cc02095e540`)을 참조했다. N15 routing 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N14(`4970a..4976e` `4b702..4b70a` `a5cf6..a6172` `a6914..a6ac6` `a6dd4..a6eea` `a7256..a725c` `be0c4..be13c`, 작업 트리 `metalslug-n14`)와 겹치지 않는다. N15는 N14의 `4970a`를 부른다(`76f42` `76f88`; 이 트리에서는 실행부 없는 경계, 시험은 stop만). [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n15/n15blocks.py`가 원본 opcode에서 독립 계산했다(`starts.txt`).

## 요약

- [F] **N15 = 217 block**, 코드 16 범위 2,272바이트, 493명령이다. 진입: 노드 callback `708a6`(LONG `e8d0c`), `76d18`(LONG `e8d48`); 범위 밖에서 설치되는 callback `71032`(U13 `70a64`, N04 `72d38`, 미연결 `70cce` `714f8`)·`71a80`(미연결 `70cfc` `717de` `73128`)·`71bc0`(미연결 `70ce0`)·`71d48`(미연결 `718e2`, N04 `71d40`)·`71dd6`(미연결 `70d0a` `71002`); 범위 안 `MOVE.L #imm,(A6)` 설치 callback `710e4`(`710de`) `71a80`(`71156`) `71b04`(`71afe`) `71bc0`(`711b6`) `71d48`(`71b38`) `71db2`(`71dac`) `71dd6`(`711a6`) `71e4e`(`71e48`) `76d56`(`76eb4`) `76d66`(`76e58`) `76d94`(`76d8e`) `76e2a`(`76e24`) `76e90`(`76e8a`); LONG 표 `7117e` 설치 값 `71a80` `71bc0`(그리고 범위 밖 `71468` `713d8`); 범위 밖에서 부르는 helper `493bc`(JSR 29곳, 그중 routing된 N09 `b0232`) `7028e`(7곳) `7054c`(이 단위 `7114e`, 미연결 `70cf4` `73120`) `705ca`(이 단위 `7119e`, 미연결 3곳) `76f98`(이 단위 `76db6`, 미연결 `770b8`); interpreter 명령 callback 표 `4a500`의 LONG `4a6a8` 값 `76f1e`; 공용 꼬리 `72d66`(이 단위 `71e88`, 미연결 `71f28` `7203c` `721b4` `72248`).
- [F] 묶인 Bcc 1곳(`71c48 BTST; BEQ 71c56; BCS 71a80`). BRA 대상 다른 단위 block 내부 명령을 선행에 묶은 곳 1곳(`71c86`+N04 `71c98 TST.W 9c(A6); BNE.W 71ccc`, 결정 3). 계산 PC(JMP/JSR 표, 레지스터 간접)·X 명령(SUBX/ADDX)·나눗셈·곱셈·I/O port 쓰기·bank 변경은 없다. PC 상대 자료 읽기 2곳: `7116c MOVE.L 7117e(PC,D0.W),D0`(index `D0.W & 1c`, LONG 8개, 정적 상한), `711e6 MOVEA.L (A0,D0.W),A0`(A0 = `70d72`, index는 경계 `70302`가 돌려준 `D0`×4; 자료 읽기라 bus 규칙만 적용). TRAP 경계 1곳: `493c6 TRAP #f`(`493bc`에서 `A5` ≠ `108000`일 때의 fall-through).
- [F] **경계(실행부 없음)**: `70302`(`711e2 BSR`), `70594`(`711b6 BSR`), `cc8b4`(`72d86` `72dac` `JMP`), `cc778`(`76ef4 JMP`), `e9112`(`76eee JSR`), TRAP `493c6`, N14 `4970a`(`76f42` `76f88`; 동시 진행 단위). 범위 밖 설치 값 `712a0` `713d8` `71468` `7120e` `72978` `72f8a` `70c0c` `71e8c`와 범위 밖 `28ae` 자식 `7706a` `76ff2`는 node LONG/A0에 쓰는 값일 뿐 이 단위는 그 PC로 가지 않는다.
- [F] **flag**:
  - C 소비 block **16개**: 단독 Bcc 15개(FLOW_ONLY) `71152`(`BCC`, 이 단위 `7054c`) `711a2`(`BCC`, `705ca`) `711c0`(`BCC`, 경계 `70594`) `711ce`(`BCC`, `7028e`) `71dc8` `76e4a` `76eb0`(`BCC`, interpreter `49fc6`) `76daa`(`BCS`, N08 `4983e`) `76dba`(`BCS`, 이 단위 `76f98`) `76ed4`(`BCC`, U05 `1ab02`) `76f28`(`BCC`, N05 `1ab80`) `76f3e` `76f84`(`BCC`, fade_card `28ae`) `76fbc` `76fe2`(`BCC`, frame_helpers `49392`)와 묶인 `71c48`(`BTST`+`BEQ`+`BCS`; `BCS`는 `710e4`로 들어온 C를 읽는다, 결정 4). Unknown C로 들어오면 `objects n15 caller requires known carry`(`71c48`은 `82(A6)` bit 1이 1이라 `BCS`가 평가될 때만).
  - known carry 생산 block **15개**: Clear `493ee` `70298` `702c6` `70588` `705fe` `76fc0` `76fe6`(`ANDI.B #fe,CCR`), `710d2`(끝 `MOVE.L #710e4,(A6)`; 소비자 `71c48`); Set `493e8` `702c0` `7058e` `705f8`(`ORI.B #1,CCR`); 계산 `493c8` `493d4`(`CMPA.L`의 무부호 빌림) `7029e`(`CMPI.W #e0,D0`의 무부호 빌림). 소비자: `493bc` 호출자(N09 `b0238 BCC`와 미연결 28곳), 이 단위 `71152` `711a2` `711ce` `76dba` `71c48`.
  - N/Z 재계산 block 없음.
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `n15reach.py`): RNG 기록에서 seed 76 77 98 99 104 105만 N15 PC를 실행한다(TB 시작 74개, 모두 block 시작). base 기록은 0개다. 정적 재생 예측: 완주 수 변화 없음(RNG 그 6 seed의 첫 미연결 지점이 `708a6` f0 → `7a53c`(N17) f0). 자연 미도달 시작 143개(`71a80` `71d48` `71dd6` 계열, `71c48` 분기, `76e2a` `76e62` `76e90`, `76f1e`, 경계로 가는 block 등)는 typed fixture와 실제 ROM 차분으로 덮는다.

## 메인 결정 (초안 권고)

1. **block 수 217(재범위 191과 +26).**
   - [F] 이 계약의 decoder에 재범위 함수 진입(N04 소유 `71c90` `71d0a` 제외)만 주고 설치 대상을 따라가지 않으면 188 block이다(재범위 191과의 3 차이는 재범위 decoder가 TRAP `493c6`과 묶인 `71c52` 등을 따로 센 것으로 보인다; [I]).
   - +14 범위 안 설치 사슬(재범위 결정 2, N09/N13 선례): `71b38 MOVE.L #71d48,(A6)`의 설치 callback 본문 `71d48..71dd6` 11 block(재범위 "미실행 설치"), fall-through로 이어지는 설치 진입 `71b04` `71e4e` `76e2a`(N11 `aef18` 관례로 block 시작).
   - +15 interpreter 명령 callback `76f1e`(`76f1e..76f98`): fixed ROM LONG `4a6a8`(interpreter 명령 callback 표 `4a500` + 4×`6a`)의 값이고 행 범위 `76d18..76ff2` 안에 있다. 재범위 함수 진입에는 없다(400 frame 안에 실행되지 않음). 권고: N13(`5ab22` `5ab3a`) 관례대로 넣는다. 넣지 않으면 행 범위 안에 참조되는 미연결 조각이 남는다.
2. **routing 범위는 코드만(16 범위).** `493bc..493c6` `493c8..493fc` `7028e..702cc` `7054c..70594` `705ca..70606` `708a6..708ba` `71032..7117e` `7119e..7120e` `71a80..71b42` `71bc0..71c90` `71d48..71e8c` `72d66..72da6` `72dac..72dcc` `72dce..72dd2` `76d18..76f14` `76f18..76ff2`(짝수 PC 1,136개, block 시작 217, 내부 919).
   - 범위 안 routing 안 함: TRAP `493c6..493c8`(결정 6), `70594..705ca`(경계 함수 `70594`), LONG 표 `7117e..7119e`(8 entry: `71468` `71a80` `71bc0` `713d8` 0 0 0 0), `71b42..71bc0`(설치 값 `71d0a`로 끝나는 상태 본문 `71b42`; 어떤 분기·LONG·설치도 가리키지 않는다), `71c90..71d48`(N04), `72da6..72dac`(`RTS`, `BRA.W 72dce`; 참조 없음), `72dcc`(`RTS`; 참조 없음), `72dd2..72e8e`(N04), `76f14` `76f16`(`RTS` 2개; 참조 없음).
   - 이웃: `493ba`(미연결), `493fc..`(미연결), `7028c`(U12 `70054..7028e` 끝), `702cc..70302`(미연결 `702cc` `702f0`), `70302..70418`(경계 함수 `70302`), `70418..7054c`(U12), `70606..`(미연결), `708a4`(미연결), `708ba..7090a`(미연결), `7090a..`(U13), `71030`(미연결), `7120e..71a80`(설치 대상 `7120e` `712a0` `713d8` `71468` 등의 상태 본문; 미연결), `71e8c..72a18`(설치 대상 `71e8c` 등; 미연결), `72a18..72d56`(N04), `72d56..72d66`(미연결), `76d16`(미연결), `76ff2..`(`28ae` 자식 `76ff2`, 미연결). 겹침 없음.
3. **`71c86`에 N04 내부 `71c98`을 묶는다.** [F] `71c86 MOVE.L 64(A6),36(A6); BRA.W 71c98`의 대상 `71c98 TST.W 9c(A6); BNE.W 71ccc`는 N04 block `71c90`(`MOVE.L #0,36(A6); TST.W 9c(A6); BNE.W 71ccc`)의 내부 PC다. N04 실행부는 `71c98`을 block 시작으로 두지 않으므로 그대로 넘기면 `unsupported animation objects n04 PC`가 된다. N04 범위를 다시 routing하지 않기 위해 N09 `af7a0`(`BTST; BRA.W af7b0; BNE.W af7ba`) 선례대로 `71c86` block이 `MOVE.L 64(A6),36(A6); BRA.W 71c98; TST.W 9c(A6); BNE.W 71ccc`를 한 block으로 실행하고 `71ccc`(WORD `9c(A6)` ≠ 0) 또는 `71ca0`(= 0)으로 간다. 둘 다 N04 block 시작이다. `71c86`은 Unknown(`TST`가 C를 0으로 만들지만 소비자가 없다). 권고 대안: N04가 `71c98`을 block 시작으로 나누면 이 묶음을 풀 수 있다(N04 계약 변경 필요).
4. **`71c48` 묶인 `BCS`의 C(조건부 소비자).** [F] `71c48 BTST.B #1,82(A6); BEQ.W 71c56; BCS.W 71a80`의 `BCS`는 `BTST`가 바꾸지 않은 들어온 C를 읽는다. `71c48`의 선행은 `710e4 BEQ.W 71c48`(그리고 미연결 `70f44 BEQ.W 71c48`)뿐이고 `710e4`는 FLOW_ONLY(`BTST`+`BEQ`)다. `710e4`로 들어오는 경로는 `710d2` fall-through(끝 `MOVE.L #710e4,(A6)` → C = 0, known Clear 생산)와 node dispatcher(`2abe MOVEA.L (A6),A0; JSR (A0)`; 앞 callback이 남긴 C)다. 규칙: bit 1 = 0이면 C와 무관하게 `71c56`; bit 1 = 1이면 C Set → `71a80`, Clear → `71c56`, Unknown → `objects n15 caller requires known carry`(상태 보존). [F] 400 frame 자연 기록에서 `710e4`는 dispatcher로 실행되지 않고(`710e4` TB 시작 없음) `71c48`도 실행되지 않는다.
5. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n15.cpp`의 `animation_objects_n15_block`. 오류는 `unsupported animation objects n15 PC`(내부 PC), `objects n15 caller requires known carry`(소비 16 block). 나눗셈이 없으므로 제수 0 오류는 없다.
6. **TRAP `493c6`.** [F] `493bc CMPA.L #108000,A5; BEQ.W 493c8`의 fall-through `493c6`은 `4e4f`(`TRAP #f`)다. N06 관례(원 범위 결정 6)대로 routing하지 않는 checked 경계다. `493c8`은 `BEQ` 대상(코드)이라 TRAP 뒤 문자열은 없다. 자연 400 frame에서 실행되지 않는다(`A5` = `108000`).
7. **무효화 탐침 1곳.** [F] `engine/tests/animation_machine_frame_helpers_test.cpp`의 routing 밖 탐침 목록 `outside[]`에 `0x493bc`가 있다(`unsupported animation machine PC` 기대). N15 뒤 `493bc`는 실행되므로 F4 시험 경계 관례대로 RAM 탐침 `0x10fe90`으로 바꾼다(이 계약이 허용하는 공유 수정). `tools/verify_animation_machine_frame_helpers.py`의 `outside_range_entry_0493bc`(기대 `unsupported animation machine PC`)도 N15 뒤 성립하지 않는다(도구는 고치지 않고 보고; 메인 결정). N09 test의 `493bc` 경계 행(`af74a-*` `b0228-*` `b0230` `b041c-*`)은 stop PC `493bc`에서 멈추는 것만 보므로 계속 성립한다. U12/U13/N04 test의 N15 주소(`7028e` `7054c` 범위 끝, 설치 값 `71032` `71d48`)는 자료 값이라 무관하다.
8. **interpreter callback.** `animation_machine_interpreter.cpp`는 바꾸지 않는다. [F] `89f8fec`의 interpreter는 명령 callback 대상을 live routing으로 보낸다(허용 목록 없음). `76f1e`는 N15 routing으로 실행된다. [F] interpreter 복귀점 `4a354`/`4a43e`는 `MOVE.W (A7)+,-7ff0(A5)`라 callback의 C를 읽지 않으므로 `76f1e`의 `ORI CCR`(`76f50` `76f92`)은 소비자가 없는 Unknown이다.

## 원본 바이트 근거

[F] 코드 16 범위 합계 2,272바이트. 범위 순서로 이어 붙인 SHA256 `88bd28f4f885d617f1435175c316848190b9993b59a1e8d889ccea450d6e5458`.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `493bc..493c6` | 10 | `f4d10bb51083579ac78165c28416bb513de037635484221583996bb0016be83b` | `493bc`(A5 확인, TRAP 앞) |
| `493c8..493fc` | 52 | `a198f46847caaa602baceb6d7316c68e034d81eaded7a4444f4406d245a01e5c` | `493bc` 본문(선수 node 판정, C 반환) |
| `7028e..702cc` | 62 | `f1bfa0ca95b7c96720c405bfe22719f45ab240a6edce0bfd27831567acf9f2d1` | helper `7028e` |
| `7054c..70594` | 72 | `bb24b429df7cacc89818d9d8193127fecca987ffac0bcdd65c40bbb7dff34a8c` | helper `7054c` |
| `705ca..70606` | 60 | `21337fc155237511c05335f7b323a5d3c1c3ad4cec28437cb656bfe86571b943` | helper `705ca` |
| `708a6..708ba` | 20 | `96e031b2016e129cb10cab9ec4a187cc128664e30f7e34d3cea5274c42b60463` | 노드 callback `708a6` |
| `71032..7117e` | 332 | `4592f8f259aae750e339508817642cd7284e734a70a9fc15164540d51be160ec` | `71032`, `710e4` 앞부분 |
| `7119e..7120e` | 112 | `9103d1061f7fde54ac93793cfc989f38dbb1d11f9345bed9885199112b4011e2` | `710e4` 뒷부분 |
| `71a80..71b42` | 194 | `e0736bce0633a8b33dc7bb3453c9630aca89f16b56c9fc3f2ff955c1869280b7` | `71a80`(설치 `71b04`) |
| `71bc0..71c90` | 208 | `aa422b5b719c13a94d0d4c1ad97d5c41a5babff276419c5f5ffd4dce8c544852` | `71bc0`, `71c48` 분기 |
| `71d48..71e8c` | 324 | `9f60de6d4d8bd97be2acc7638ca97111ac417f520da7da456c70c73a3ebfa879` | `71d48`(설치 `71db2`), `71dd6`(설치 `71e4e`) |
| `72d66..72da6` | 64 | `b57b8b19b84f33a17b90e2d420291c3b740adb9f9aea75a74d83d5a4228b167c` | 공용 꼬리 `72d66` |
| `72dac..72dcc` | 32 | `dd5b3eabae055b905156ef42fe42e6d654d84f341819f5fe2314bb501e5f4077` | `72dac`(`JMP cc8b4`) |
| `72dce..72dd2` | 4 | `38a126f5b8ed6f5c24df24db58ae1aa2ece856346cedd5ac829bc3e3cf8e4273` | `BRA.W 72e3e` |
| `76d18..76f14` | 508 | `88d93e0473d4609f759d2d252509192ba49b3d0358ea1e0859af14feb1fd90de` | `76d18`과 설치 callback, 공용 꼬리 `76ebe` |
| `76f18..76ff2` | 218 | `4393e43207a2f7f89f6f3cb4722604ee946a76bd04d91f0c4cd9a6cb3de53432` | `76f18`, interpreter callback `76f1e`, helper `76f98` |

- [F] 참조(raw LONG 검색 scratch `n15raw.py`; JSR/BSR/Bcc/`MOVE.L #` 검색 `n15refs.py`): `708a6` ← LONG `e8d0c`, `76d18` ← LONG `e8d48`([I] N11 `e8eb4`·N13 `e9044`와 같은 stage event 표 영역). `76f1e` ← LONG `4a6a8`(interpreter 명령 callback 표; 이웃 `4a6a4` = `703f6`, `4a6ac` = `7ef84`). `493bc` ← `JSR` 29곳(N09 `b0232`, 미연결 `49416` `775b6` `77bfc` `79682` `7f18c` `807f8` `83822` `846a0` `8b6c0` `8bbee` `9028e` `92d6c` `92d74` `94f3a` `94f76` `99a3a` `9aca0` `9db6a` `9ebdc` `9f048` `9f116` `a1306` `a3112` `a9990` `aa522` `b245c` `b346a` `b5588`; `92d6c` 뒤는 `RTS`, 나머지는 바로 `BCC`/`BCS`). `7028e` ← `6fa32` `6fac0`(`JSR`), `70d10` `70fd2` `75cf8` `75e2e` `75f32`(`BSR`)와 이 단위 `711ca`; 모두 바로 `BCC`. `7054c` ← 이 단위 `7114e`, 미연결 `70cf4` `73120`(바로 `BCC`). `705ca` ← 이 단위 `7119e`, 미연결 `70d02` `70ffa` `71f2c`(바로 `BCC`). `76f98` ← 이 단위 `76db6`, 미연결 `770b8`(바로 `BCC`). `71032` ← `MOVE.L #` U13 `70a64`, N04 `72d38`, 미연결 `70cce` `714f8`. `71a80` ← 이 단위 `71156`·표 `71182`, 미연결 `70cfc` `717de` `73128`(`MOVE.L #`)·`730dc BEQ.W`. `71bc0` ← 이 단위 `711b6`·표 `71186`, 미연결 `70ce0`. `71c48` ← 이 단위 `710e4`, 미연결 `70f44`(`BEQ.W`). `71d48` ← 이 단위 `71b38`, N04 `71d40`, 미연결 `718e2`. `71dd6` ← 이 단위 `711a6`, 미연결 `70d0a` `71002`. `72d66` ← 이 단위 `71e88`, 미연결 `71f28` `7203c` `721b4` `72248`(`BRA.W`). `710e4` `71b04` `71db2` `71e4e` `76d56` `76d66` `76d94` `76e2a` `76e90`은 각자의 `MOVE.L #imm,(A6)`(위 요약)뿐이다. `71b42` `72da6` `72da8` `72dcc` `76f14` `76f16`을 가리키는 분기·LONG은 없다(`7700e`의 `BPL.B 76fa6` 디코드는 `7700a JSR c6a96.L`의 operand라 명령이 아니다).
- [F] 경계 함수: `70302`(`TST.W 78(A6); BNE.W 703f0; …`, `D0` = 0..7을 돌려주는 것으로 보이는 ADDX/SUBX 루프; [I]), `70594`(`MOVE.W #1,D7; AND.W 80(A6),D7; …; ORI/ANDI CCR; RTS`, C 반환), `cc8b4`/`cc778`(표 `cc7a8` `cc82a` `cc8da`의 animation 루틴; 재범위 결정상 400 frame 안에 실행되지 않음), `e9112`(미연결).

## block 목록과 실행 의미

[F] 217 block. "(→x)"는 다음 block으로의 fall-through다. d16(An)은 부호확장한다. `.W` 연산은 하위 WORD만, `.B`는 하위 BYTE만 바꾼다. `MOVEQ`는 LONG 전체를 부호확장 값으로 쓴다. `MOVEA.L`/`LEA`는 주소 레지스터 32비트 전체를 바꾸고 CCR을 바꾸지 않는다. `JSR`/`BSR`은 복귀 LONG을 쌓고 대상으로 간다. "FLOW"는 C 보존 block, "C 소비"는 C 소비 block, "생산"은 known C 생산 block이다(표시 없는 block은 Unknown). `493e0`의 `BTST D0,568e(A5)`는 메모리 대상이라 BYTE이고 bit 번호는 `D0` mod 8이다(capstone 표기 `btst.l`).

**helper `493bc`(선수 node `A0` 판정, C 반환; TRAP 경계 `493c6`) 7**
- `493bc`: `CMPA.L #108000,a5; BEQ.W 493c8` (→`493c6`)
- `493c8`: `MOVEQ #0,d0; CMPA.L #100cb8,a0; BEQ.W 493e0` (→`493d4`) — 생산 계산
- `493d4`: `MOVEQ #1,d0; CMPA.L #100da8,a0; BNE.W 493ee` (→`493e0`) — 생산 계산
- `493e0`: `BTST.B d0,568e(a5); BEQ.W 493ec` (→`493e8`) — FLOW
- `493e8`: `ORI.B #1,ccr` (→`493ec`) — 생산 Set
- `493ec`: `RTS` — FLOW
- `493ee`: `MOVEQ #0,d0; CMPA.L #100cb8,a0; ANDI.B #fe,ccr; RTS` — 생산 Clear

**helper `7028e`(C 반환) 8**
- `7028e`: `BTST.B #3,15(a6); BEQ.W 7029e` (→`70298`) — FLOW
- `70298`: `ANDI.B #fe,ccr; RTS` — 생산 Clear
- `7029e`: `MOVE.W 42(a6),d0; SUBI.W #30,d0; CMPI.W #e0,d0; BCS.W 702b0` (→`702ae`) — 생산 계산
- `702ae`: `RTS` — FLOW
- `702b0`: `LEA.L 6fe3c(pc),a0; JSR 4ae4a.l` (→`702ba`) — FLOW
- `702ba`: `TST.B d0; BEQ.W 702c6` (→`702c0`)
- `702c0`: `ORI.B #1,ccr; RTS` — 생산 Set
- `702c6`: `ANDI.B #fe,ccr; RTS` — 생산 Clear

**helper `7054c`(C 반환) 8**
- `7054c`: `BTST.B #5,61(a6); BEQ.W 7056a` (→`70556`) — FLOW
- `70556`: `BTST.B #4,82(a6); BEQ.W 7056a` (→`70560`) — FLOW
- `70560`: `CMPI.B #40,6f(a6); BEQ.W 7058e` (→`7056a`)
- `7056a`: `BTST.B #5,82(a6); BNE.W 70588` (→`70574`) — FLOW
- `70574`: `BTST.B #6,82(a6); BNE.W 70588` (→`7057e`) — FLOW
- `7057e`: `BTST.B #2,82(a6); BNE.W 7058e` (→`70588`) — FLOW
- `70588`: `ANDI.B #fe,ccr; RTS` — 생산 Clear
- `7058e`: `ORI.B #1,ccr; RTS` — 생산 Set

**helper `705ca`(C 반환) 6**
- `705ca`: `BTST.B #1,82(a6); BEQ.W 705fe` (→`705d4`) — FLOW
- `705d4`: `CMPI.B #40,6f(a6); BNE.W 705fe` (→`705de`)
- `705de`: `MOVE.W 42(a6),d0; MOVE.W 46(a6),d1; ADDI.W #20,d1; JSR 4bc04.l` (→`705f0`)
- `705f0`: `CMPI.W #40,d0; BCS.W 705fe` (→`705f8`)
- `705f8`: `ORI.B #1,ccr; RTS` — 생산 Set
- `705fe`: `MOVEQ #0,d0; ANDI.B #fe,ccr; RTS` — 생산 Clear

**노드 callback `708a6` 2**
- `708a6`: `MOVE.W #0,9c(a6); JSR 70418(pc)` (→`708b0`)
- `708b0`: `MOVE.B #e0,87(a6); BRA.W 70932`

**설치 callback `71032`(초기화, 설치 `710e4`) 13**
- `71032`: `TST.W 9c(a6); BNE.W 71066` (→`7103a`)
- `7103a`: `LEA.L 26(a6),a0; MOVE.W #3,20(a6); MOVE.L 2000d0.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 4(a1),a1; JSR 49f8c.l` (→`71062`)
- `71062`: `BRA.W 7108e` — FLOW
- `71066`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 4(a1),a1; JSR 49f8c.l` (→`7108e`)
- `7108e`: `JSR 49a58.l` (→`71094`) — FLOW
- `71094`: `EXT.L d0; MOVE.L d0,64(a6); JSR 49a58.l` (→`710a0`)
- `710a0`: `EXT.L d0; ADDI.L #28000,d0; ADD.L 64(a6),d0; TST.W 9a(a6); BEQ.W 710ba` (→`710b4`)
- `710b4`: `ADDI.L #10000,d0` (→`710ba`)
- `710ba`: `BTST.B #0,15(a6); BNE.W 710c6` (→`710c4`) — FLOW
- `710c4`: `NEG.L d0` (→`710c6`)
- `710c6`: `MOVE.L d0,64(a6); TST.L d0; BPL.W 710d2` (→`710d0`)
- `710d0`: `NEG.L d0` (→`710d2`)
- `710d2`: `LSL.L #6,d0; SWAP d0; ADDI.W #80,d0; MOVE.W d0,2c(a6); MOVE.L #710e4,(a6)` (→`710e4`) — 생산 Clear

**설치 callback `710e4`(상태 선택, 표 `7117e`·`70d72`) 36**
- `710e4`: `BTST.B #7,15(a6); BEQ.W 71c48` (→`710ee`) — FLOW
- `710ee`: `JSR 4bfa4.l` (→`710f4`) — FLOW
- `710f4`: `ANDI.W #20,d6; BEQ.W 7110e` (→`710fc`)
- `710fc`: `MOVE.W #1,d6; AND.W 80(a6),d6; BEQ.W 7110e` (→`71108`)
- `71108`: `MOVE.L #712a0,(a6)` (→`7110e`)
- `7110e`: `JSR 49fc6.l` (→`71114`) — FLOW
- `71114`: `MOVE.W 8e(a6),d0; SUB.W 42(a6),d0; MOVE.W 64(a6),d1; EOR.W d0,d1; BPL.W 7113c` (→`71126`)
- `71126`: `MOVE.L #713d8,(a6); BTST.B #1,82(a6); BEQ.W 7113c` (→`71136`)
- `71136`: `MOVE.L #71468,(a6)` (→`7113c`)
- `7113c`: `MOVE.B 6e(a6),d0; CMPI.B #3,d0; BNE.W 7114e` (→`71148`)
- `71148`: `MOVE.L #713d8,(a6)` (→`7114e`)
- `7114e`: `BSR.W 7054c` (→`71152`) — FLOW
- `71152`: `BCC.W 7115c` (→`71156`) — C 소비
- `71156`: `MOVE.L #71a80,(a6)` (→`7115c`)
- `7115c`: `BTST.B #7,82(a6); BEQ.W 7119e` (→`71166`) — FLOW
- `71166`: `JSR 49a58.l` (→`7116c`) — FLOW
- `7116c`: `ANDI.W #1c,d0; MOVE.L 7117e(pc,d0.w),d0; BEQ.W 7117a` (→`71178`)
- `71178`: `MOVE.L d0,(a6)` (→`7117a`)
- `7117a`: `BRA.W 7119e` — FLOW
- `7119e`: `BSR.W 705ca` (→`711a2`) — FLOW
- `711a2`: `BCC.W 711ac` (→`711a6`) — C 소비
- `711a6`: `MOVE.L #71dd6,(a6)` (→`711ac`)
- `711ac`: `BTST.B #0,61(a6); BEQ.W 711ca` (→`711b6`) — FLOW
- `711b6`: `MOVE.L #71bc0,(a6); BSR.W 70594` (→`711c0`)
- `711c0`: `BCC.W 711ca` (→`711c4`) — C 소비
- `711c4`: `MOVE.L #7120e,(a6)` (→`711ca`)
- `711ca`: `BSR.W 7028e` (→`711ce`) — FLOW
- `711ce`: `BCC.W 711d8` (→`711d2`) — C 소비
- `711d2`: `MOVE.L #72978,(a6)` (→`711d8`)
- `711d8`: `BTST.B #0,82(a6); BEQ.W 711fc` (→`711e2`) — FLOW
- `711e2`: `BSR.W 70302` (→`711e6`) — FLOW
- `711e6`: `LEA.L 70d72(pc),a0; ADD.W d0,d0; ADD.W d0,d0; MOVEA.L (a0,d0.w),a0; CMPA.W #0,a0; BEQ.W 711fc` (→`711fa`)
- `711fa`: `MOVE.L a0,(a6)` (→`711fc`)
- `711fc`: `TST.W 7c(a6); BNE.W 7120a` (→`71204`)
- `71204`: `MOVE.L #72f8a,(a6)` (→`7120a`)
- `7120a`: `BRA.W 72dd2` — FLOW

**설치 callback `71a80`(설치 `71b04`) 12**
- `71a80`: `MOVE.L #8a000,3a(a6); MOVE.L #28000,d0; BTST.B #0,15(a6); BNE.W 71a9a` (→`71a98`)
- `71a98`: `NEG.L d0` (→`71a9a`)
- `71a9a`: `MOVE.L d0,64(a6); MOVE.L d0,36(a6); TST.W 9c(a6); BNE.W 71ad6` (→`71aaa`)
- `71aaa`: `LEA.L 26(a6),a0; MOVE.W #3,20(a6); MOVE.L 2000d0.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 28(a1),a1; JSR 49f8c.l` (→`71ad2`)
- `71ad2`: `BRA.W 71afe` — FLOW
- `71ad6`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 28(a1),a1; JSR 49f8c.l` (→`71afe`)
- `71afe`: `MOVE.L #71b04,(a6)` (→`71b04`)
- `71b04`: `MOVE.L 64(a6),d0; SUB.L 36(a6),d0; ASR.L #5,d0; ADD.L d0,36(a6); MOVE.L #fff00000,d0; SUB.L 3a(a6),d0; ASR.L #5,d0; ADD.L d0,3a(a6); JSR 4be34.l` (→`71b28`)
- `71b28`: `JSR 49fc6.l` (→`71b2e`) — FLOW
- `71b2e`: `BTST.B #7,15(a6); BEQ.W 71b3e` (→`71b38`) — FLOW
- `71b38`: `MOVE.L #71d48,(a6)` (→`71b3e`)
- `71b3e`: `BRA.W 72dd2` — FLOW

**설치 callback `71bc0` 7**
- `71bc0`: `TST.W 9c(a6); BNE.W 71bf4` (→`71bc8`)
- `71bc8`: `LEA.L 26(a6),a0; MOVE.W #3,20(a6); MOVE.L 2000d0.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 1c(a1),a1; JSR 49f8c.l` (→`71bf0`)
- `71bf0`: `BRA.W 71c1c` — FLOW
- `71bf4`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 1c(a1),a1; JSR 49f8c.l` (→`71c1c`)
- `71c1c`: `MOVE.L #30000,d0; BTST.B #0,15(a6); BEQ.W 71c2e` (→`71c2c`)
- `71c2c`: `NEG.L d0` (→`71c2e`)
- `71c2e`: `MOVE.L d0,64(a6); MOVE.L d0,36(a6); MOVE.L #20000,3a(a6); MOVE.L #71d0a,(a6); BRA.W 71d0a`

**`710e4`의 분기 `71c48`(묶인 `BCS`) 9**
- `71c48`: `BTST.B #1,82(a6); BEQ.W 71c56; BCS.W 71a80` (→`71c56`; 묶인 BCS는 들어온 C를 읽는다) — C 소비(조건부, 결정 4)
- `71c56`: `JSR 49a58.l` (→`71c5c`) — FLOW
- `71c5c`: `CMPI.W #160,46(a6); BCC.W 71c72` (→`71c66`)
- `71c66`: `ANDI.W #1,d0; BEQ.W 71a80` (→`71c6e`)
- `71c6e`: `BRA.W 71c86` — FLOW
- `71c72`: `ANDI.W #3,d0; BEQ.W 71dd6` (→`71c7a`)
- `71c7a`: `SUBQ.W #1,d0; BEQ.W 71a80` (→`71c80`)
- `71c80`: `SUBQ.W #1,d0; BEQ.W 71dd6` (→`71c86`)
- `71c86`: `MOVE.L 64(a6),36(a6); BRA.W 71c98;` [`71c98`, N04 block `71c90`의 내부 PC] `TST.W 9c(a6); BNE.W 71ccc` (→`71ca0`; 묶음, 결정 3)

**설치 callback `71d48`(설치 `71db2`) 11**
- `71d48`: `TST.W 9c(a6); BNE.W 71d7c` (→`71d50`)
- `71d50`: `LEA.L 26(a6),a0; MOVE.W #3,20(a6); MOVE.L 2000d0.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 24(a1),a1; JSR 49f8c.l` (→`71d78`)
- `71d78`: `BRA.W 71da4` — FLOW
- `71d7c`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 24(a1),a1; JSR 49f8c.l` (→`71da4`)
- `71da4`: `MOVE.L #0,64(a6); MOVE.L #71db2,(a6)` (→`71db2`)
- `71db2`: `BTST.B #7,15(a6); BEQ.W 71c90` (→`71dbc`) — FLOW
- `71dbc`: `JSR 4bfa4.l` (→`71dc2`) — FLOW
- `71dc2`: `JSR 49fc6.l` (→`71dc8`) — FLOW
- `71dc8`: `BCC.W 71dd2` (→`71dcc`) — C 소비
- `71dcc`: `MOVE.L #70c0c,(a6)` (→`71dd2`)
- `71dd2`: `BRA.W 72dd2` — FLOW

**설치 callback `71dd6`(설치 `71e4e`) 10**
- `71dd6`: `TST.W 9c(a6); BNE.W 71e0a` (→`71dde`)
- `71dde`: `LEA.L 26(a6),a0; MOVE.W #3,20(a6); MOVE.L 2000d0.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 20(a1),a1; JSR 49f8c.l` (→`71e06`)
- `71e06`: `BRA.W 71e32` — FLOW
- `71e0a`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 20(a1),a1; JSR 49f8c.l` (→`71e32`)
- `71e32`: `MOVE.L 64(a6),36(a6); MOVE.L #10000,3a(a6); MOVE.L #0,64(a6); MOVE.L #71e4e,(a6)` (→`71e4e`)
- `71e4e`: `MOVE.L 64(a6),d0; SUB.L 36(a6),d0; ASR.L #5,d0; ADD.L d0,36(a6); MOVE.L #fff00000,d0; SUB.L 3a(a6),d0; ASR.L #5,d0; ADD.L d0,3a(a6); JSR 4be34.l` (→`71e72`)
- `71e72`: `JSR 49fc6.l` (→`71e78`) — FLOW
- `71e78`: `BTST.B #7,15(a6); BEQ.W 71e88` (→`71e82`) — FLOW
- `71e82`: `MOVE.L #71e8c,(a6)` (→`71e88`)
- `71e88`: `BRA.W 72d66` — FLOW

**공용 꼬리 `72d66` 6**
- `72d66`: `JSR 4b54e.l` (→`72d6c`) — FLOW
- `72d6c`: `BTST.B #7,61(a6); BEQ.W 72dce` (→`72d76`) — FLOW
- `72d76`: `MOVEA.L c(a6),a0; ST.B 62(a0); TST.W 9c(a6); BNE.W 72dac` (→`72d86`)
- `72d86`: `MOVE.B #ff,17(a6); LEA.L cdeea.l,a0; MOVEA.L 2000d0.l,a1; MOVE.W #3,d1; MOVE.W #0,d2; JMP cc8b4.l`
- `72dac`: `MOVE.B #ff,17(a6); LEA.L cdef8.l,a0; MOVEA.L 2000d4.l,a1; MOVE.W #b,d1; MOVE.W #1,d2; JMP cc8b4.l`
- `72dce`: `BRA.W 72e3e` — FLOW

**노드 callback `76d18`(설치 `76d56` `76d66` `76d94`) 9**
- `76d18`: `MOVE.W #8820,68(a6); MOVE.W #8820,1e(a6); MOVE.W #34,d0; MOVE.W #f,d1; MOVE.B #0,d2; JSR c6a96.l` (→`76d36`)
- `76d36`: `BCLR.B #0,15(a6); TST.W 76(a6); BNE.W 76d4a` (→`76d44`)
- `76d44`: `BSET.B #0,15(a6)` (→`76d4a`) — FLOW
- `76d4a`: `JSR 4c0ac.l` (→`76d50`) — FLOW
- `76d50`: `MOVE.W #1,54(a6)` (→`76d56`)
- `76d56`: `LEA.L c88ee.l,a0; JSR 490ba.l` (→`76d62`) — FLOW
- `76d62`: `MOVE.W d0,86(a6)` (→`76d66`)
- `76d66`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 3c(a1),a1; JSR 49f8c.l` (→`76d8e`)
- `76d8e`: `MOVE.L #76d94,(a6)` (→`76d94`)

**설치 callback `76d94` 17**
- `76d94`: `TST.W 86(a6); BNE.W 76dae` (→`76d9c`)
- `76d9c`: `MOVE.W #ffe8,d0; MOVE.W #1a,d1; JSR 4983e.l` (→`76daa`)
- `76daa`: `BCS.W 76e62` (→`76dae`) — C 소비
- `76dae`: `TST.W 78(a6); BNE.W 76dd8` (→`76db6`)
- `76db6`: `JSR 76f98(pc)` (→`76dba`) — FLOW
- `76dba`: `BCS.W 76dd8` (→`76dbe`) — C 소비
- `76dbe`: `MOVE.W 42(a0),d0; SUB.W 42(a6),d0; BTST.B #0,15(a6); BNE.W 76dd2` (→`76dd0`)
- `76dd0`: `NEG.W d0` (→`76dd2`)
- `76dd2`: `TST.W d0; BMI.W 76dfc` (→`76dd8`)
- `76dd8`: `BTST.B #7,15(a6); BNE.W 76dec` (→`76de2`) — FLOW
- `76de2`: `JSR 4be2c.l` (→`76de8`) — FLOW
- `76de8`: `BRA.W 76df2` — FLOW
- `76dec`: `JSR 4be06.l` (→`76df2`) — FLOW
- `76df2`: `JSR 49fc6.l` (→`76df8`) — FLOW
- `76df8`: `BRA.W 76ebe` — FLOW
- `76dfc`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 44(a1),a1; JSR 49f8c.l` (→`76e24`)
- `76e24`: `MOVE.L #76e2a,(a6)` (→`76e2a`)

**설치 callback `76e2a` 9**
- `76e2a`: `BTST.B #7,15(a6); BNE.W 76e3e` (→`76e34`) — FLOW
- `76e34`: `JSR 4be2c.l` (→`76e3a`) — FLOW
- `76e3a`: `BRA.W 76e44` — FLOW
- `76e3e`: `JSR 4be06.l` (→`76e44`) — FLOW
- `76e44`: `JSR 49fc6.l` (→`76e4a`) — FLOW
- `76e4a`: `BCC.W 76e5e` (→`76e4e`) — C 소비
- `76e4e`: `LEA.L 26(a6),a0; JSR 492d0.l` (→`76e58`) — FLOW
- `76e58`: `MOVE.L #76d66,(a6)` (→`76e5e`)
- `76e5e`: `BRA.W 76ebe` — FLOW

**`76d94`의 분기 `76e62`(설치 `76e90`) 2**
- `76e62`: `LEA.L 26(a6),a0; MOVE.W #b,20(a6); MOVE.L 2000d4.l,22(a6); MOVE.W #100,d0; LEA.L 26(a6),a0; MOVEA.L 22(a6),a1; MOVEA.L 40(a1),a1; JSR 49f8c.l` (→`76e8a`)
- `76e8a`: `MOVE.L #76e90,(a6)` (→`76e90`)

**설치 callback `76e90` 8**
- `76e90`: `BTST.B #7,15(a6); BNE.W 76ea4` (→`76e9a`) — FLOW
- `76e9a`: `JSR 4be2c.l` (→`76ea0`) — FLOW
- `76ea0`: `BRA.W 76eaa` — FLOW
- `76ea4`: `JSR 4be06.l` (→`76eaa`) — FLOW
- `76eaa`: `JSR 49fc6.l` (→`76eb0`) — FLOW
- `76eb0`: `BCC.W 76eba` (→`76eb4`) — C 소비
- `76eb4`: `MOVE.L #76d56,(a6)` (→`76eba`)
- `76eba`: `BRA.W 76ebe` — FLOW

**공용 꼬리 `76ebe` 10**
- `76ebe`: `TST.W 86(a6); BEQ.W 76eca` (→`76ec6`)
- `76ec6`: `SUBQ.W #1,86(a6)` (→`76eca`)
- `76eca`: `LEA.L 772be(pc),a0; JSR 1ab02.l` (→`76ed4`) — FLOW
- `76ed4`: `BCC.W 76ede` (→`76ed8`) — C 소비
- `76ed8`: `JMP 2a00.l` — FLOW
- `76ede`: `JSR 4b54e.l` (→`76ee4`) — FLOW
- `76ee4`: `BTST.B #7,61(a6); BEQ.W 76f18` (→`76eee`) — FLOW
- `76eee`: `JSR e9112.l` (→`76ef4`) — FLOW
- `76ef4`: `MOVE.B #ff,17(a6); LEA.L cdef8.l,a0; MOVEA.L 2000d4.l,a1; MOVE.W #b,d1; MOVE.W #1,d2; JMP cc778.l`
- `76f18`: `CLR.B 5e(a6); RTS`

**interpreter 명령 callback `76f1e` 15**
- `76f1e`: `LEA.L 772be(pc),a0; JSR 1ab80.l` (→`76f28`) — FLOW
- `76f28`: `BCC.W 76f2e` (→`76f2c`) — C 소비
- `76f2c`: `RTS` — FLOW
- `76f2e`: `MOVEA.L #7706a,a0; MOVE.W #14,d0; JSR 28ae.l` (→`76f3e`)
- `76f3e`: `BCC.W 76f54` (→`76f42`) — C 소비
- `76f42`: `MOVE.W #ffe8,d0; MOVE.W #1a,d1; JSR 4970a.l` (→`76f50`)
- `76f50`: `ORI.B #1,ccr` (→`76f54`)
- `76f54`: `CMPI.W #a,7a(a6); BCC.W 76f68` (→`76f5e`)
- `76f5e`: `MOVE.W #28,7a(a0); BRA.W 76f6e`
- `76f68`: `MOVE.W 7a(a6),7a(a0)` (→`76f6e`)
- `76f6e`: `MOVE.W 7c(a6),7c(a0); MOVEA.L #76ff2,a0; MOVE.W #14,d0; JSR 28ae.l` (→`76f84`)
- `76f84`: `BCC.W 76f96` (→`76f88`) — C 소비
- `76f88`: `CLR.W d0; CLR.W d1; JSR 4970a.l` (→`76f92`)
- `76f92`: `ORI.B #1,ccr` (→`76f96`)
- `76f96`: `RTS` — FLOW

**helper `76f98`(C 반환) 12**
- `76f98`: `TST.W 7c(a6); BEQ.W 76fec` (→`76fa0`)
- `76fa0`: `MOVE.W #0,d0; JSR 4d7a6.l` (→`76faa`)
- `76faa`: `CMPI.B #0,d0; BEQ.W 76fc6` (→`76fb2`)
- `76fb2`: `MOVE.W #0,d0; JSR 49392.l` (→`76fbc`)
- `76fbc`: `BCC.W 76fc6` (→`76fc0`) — C 소비
- `76fc0`: `ANDI.B #fe,ccr; RTS` — 생산 Clear
- `76fc6`: `MOVE.W #1,d0; JSR 4d7a6.l` (→`76fd0`)
- `76fd0`: `CMPI.B #0,d0; BEQ.W 76fec` (→`76fd8`)
- `76fd8`: `MOVE.W #1,d0; JSR 49392.l` (→`76fe2`)
- `76fe2`: `BCC.W 76fec` (→`76fe6`) — C 소비
- `76fe6`: `ANDI.B #fe,ccr; RTS` — 생산 Clear
- `76fec`: `JMP 4945e.l` — FLOW

수: `493bc` 7 + `7028e` 8 + `7054c` 8 + `705ca` 6 + `708a6` 2 + `71032` 13 + `710e4` 36 + `71a80` 12 + `71bc0` 7 + `71c48` 9 + `71d48` 11 + `71dd6` 10 + `72d66` 6 + `76d18` 9 + `76d94` 17 + `76e2a` 9 + `76e62` 2 + `76e90` 8 + `76ebe` 10 + `76f1e` 15 + `76f98` 12 = 217(`starts.txt`와 같다). 분류 합계: FLOW_ONLY 94(소비자 16 포함) + 생산 15 + Unknown 108 = 217.

### 의미 세부

- 비교·분기(같은 block 안의 flag; 예외는 결정 3·4):
  - `493bc`: 32비트 `A5` = `108000`이면 `493c8`, 아니면 TRAP `493c6`. `493c8`: `D0` = 0; `A0` = `100cb8`이면 `493e0`, 아니면 `493d4`; C = (`A0` <u `100cb8`). `493d4`: `D0` = 1; `A0` ≠ `100da8`이면 `493ee`, 아니면 `493e0`; C = (`A0` <u `100da8`). 두 block 모두 `493e0`으로 갈 때는 같음이라 C = 0이다. `493e0`: BYTE `568e(A5)`의 bit (`D0` & 7)이 0이면 `493ec`(RTS, C 그대로), 1이면 `493e8`(`ORI` → C = 1) → `493ec`. `493ee`: `D0` = 0, `CMPA.L #100cb8,A0`(Z/N/V는 그 결과, CCR의 나머지 bit는 [U] 호출자가 읽지 않음), `ANDI.B #fe,CCR` → C = 0, `RTS`.
  - `7029e`: `D0.W` = WORD `42(A6)` − `30`; `D0.W` <u `e0`이면(C = 1) `702b0`, 아니면 C = 0으로 `702ae RTS`. `702ba TST.B D0; BEQ`: `D0.B` = 0이면 `702c6`(C = 0), 아니면 `702c0`(C = 1).
  - `70560`/`705d4 CMPI.B #40,6f(A6)`: BYTE 같음. `705f0 CMPI.W #40,D0; BCS`: `D0.W` <u `40`이면 `705fe`(C = 0), 아니면 `705f8`(C = 1). `705fe`는 `MOVEQ #0,D0`도 한다.
  - `710a0`/`710c6`: `TST.W 9a(A6); BEQ`, `TST.L D0; BPL`(LONG bit 31). `710f4 ANDI.W #20,D6; BEQ`(WORD 결과 0), `710fc MOVE.W #1,D6; AND.W 80(A6),D6; BEQ`. `71114`: `D0.W` = `8e(A6)` − `42(A6)`, `D1.W` = WORD `64(A6)`(LONG `64`의 상위 WORD), `D1.W` ^= `D0.W`; bit 15 = 0이면 `7113c`. `7113c`: `D0.B` = BYTE `6e(A6)`, ≠ 3이면 `7114e`. `711fc TST.W 7c(A6); BNE`. `71c5c CMPI.W #160,46(A6); BCC`: WORD `46(A6)` ≥u `160`이면 `71c72`. `71c66 ANDI.W #1,D0; BEQ 71a80`, `71c72 ANDI.W #3,D0; BEQ 71dd6`, `71c7a`/`71c80 SUBQ.W #1,D0; BEQ`(WORD 결과 0). `72d76 TST.W 9c(A6); BNE`. `76d36 TST.W 76(A6); BNE`. `76d94`/`76ebe TST.W 86(A6)`, `76dae TST.W 78(A6)`, `76f98 TST.W 7c(A6)`. `76dd2 TST.W D0; BMI`(WORD bit 15). `76f54 CMPI.W #a,7a(A6); BCC`: WORD `7a(A6)` ≥u `a`이면 `76f68`. `76faa`/`76fd0 CMPI.B #0,D0; BEQ`.
  - `BTST`(Z만): `7028e` `7054c` `70556` `7056a` `70574` `7057e` `705ca` `710ba` `710e4` `71126` `7115c` `711ac` `711d8` `71a80` `71b2e` `71c1c` `71c48` `71db2` `71e78` `72d6c` `76dbe` `76dd8` `76e2a` `76e90` `76ee4`. `76d36 BCLR.B #0,15(A6)`·`76d44 BSET.B #0,15(A6)`는 BYTE read-modify-write다.
  - `7116c`: `D0.W` &= `1c`(WORD), `D0` = LONG [`7117e` + `D0.W`](자료 읽기), 0이면 `7117a`, 아니면 `71178`에서 node LONG `(A6)` = `D0`.
  - `711e6`: `A0` = `70d72`; `D0.W` = (`D0.W` × 4) & `ffff`(두 `ADD.W`); `A0` = LONG [`70d72` + sext(`D0.W`)]; `CMPA.W #0,A0`(sext 0과 32비트 비교) → 0이면 `711fc`, 아니면 `711fa`에서 `(A6)` = `A0`.
  - `72d76`: `A0` = LONG `c(A6)`(부모 node), BYTE `62(A0)` = `ff`.
  - `76dbe`: `D0.W` = WORD `42(A0)` − WORD `42(A6)`(`A0`는 `76f98`이 돌려준 node); `15(A6)` bit 0 = 0이면 `76dd0 NEG.W D0`; `76dd2`: `D0.W` bit 15 = 1이면 `76dfc`.
- 산술:
  - `71094`: `EXT.L D0`(WORD → LONG 부호확장), LONG `64(A6)` = `D0`. `710a0`: `EXT.L D0`; `D0` += `00028000`; `D0` += LONG `64(A6)`; `9a(A6)` ≠ 0이면 `710b4`에서 `D0` += `00010000`. `710c4`/`710d0`/`71a98`/`71c2c NEG.L D0`. `710d2`: `D0` <<= 6(LONG), `SWAP`, `D0.W` += `80`(WORD), WORD `2c(A6)` = `D0.W`, `(A6)` = `710e4`(C = 0).
  - `71b04`/`71e4e`(N04 `71d0a`과 같은 식): `D0` = (LONG `64(A6)` − LONG `36(A6)`) ASR 5(부호 bit 채움), `36(A6)` += `D0`; `D0` = (`fff00000` − LONG `3a(A6)`) ASR 5, `3a(A6)` += `D0`; `JSR 4be34`.
  - `71a80`: LONG `3a(A6)` = `0008a000`, `D0` = `00028000`(`15(A6)` bit 0 = 0이면 부호 반전), `64(A6)` = `36(A6)` = `D0`. `71c1c`: `D0` = `00030000`(`15(A6)` bit 0 = 1이면 `NEG`), `64` = `36` = `D0`, `3a` = `00020000`, `(A6)` = `71d0a`, `BRA.W 71d0a`(N04). `71da4`: `64` = 0, `(A6)` = `71db2`. `71e32`: `36` = `64`, `3a` = `00010000`, `64` = 0, `(A6)` = `71e4e`. `71c86`: LONG `36(A6)` = LONG `64(A6)`, 그 뒤 결정 3.
  - `76ec6 SUBQ.W #1,86(A6)`(WORD).
- 반복되는 animation block(`7103a` `71066` `71aaa` `71ad6` `71bc8` `71bf4` `71d50` `71d7c` `71dde` `71e0a` `76d66` `76dfc` `76e62`): `LEA 26(A6),A0`; WORD `20(A6)` = K(`3` 또는 `b`); LONG `22(A6)` = banked LONG `2000d0`(K = 3) 또는 `2000d4`(K = b)(live bus); `D0.W` = `100`; `A1` = LONG `22(A6)`(방금 쓴 값을 다시 읽음); `A1` = LONG [`A1` + off](off = `4` `28` `1c` `24` `20` `3c` `44` `40`, live bus); `JSR 49f8c`.
- 호출 인자: `705de`: `D0.W` = `42(A6)`, `D1.W` = `46(A6)` + `20`(WORD), `JSR 4bc04`. `708a6`: WORD `9c(A6)` = 0, `JSR 70418`; `708b0`: BYTE `87(A6)` = `e0`, `BRA.W 70932`(U13). `76d18`: WORD `68` = `1e` = `8820`, `D0.W` = `34`, `D1.W` = `f`, `D2.B` = 0, `JSR c6a96`. `76d50`: WORD `54(A6)` = 1. `76d56`: `A0` = `c88ee`, `JSR 490ba`; `76d62`: WORD `86(A6)` = `D0.W`. `76d9c`/`76f42`: `D0.W` = `ffe8`, `D1.W` = `1a`, `JSR 4983e`/`4970a`. `76e4e`: `A0` = node + `26`, `JSR 492d0`. `76eca`/`76f1e`: `A0` = `772be`(fixed ROM 사각형 자료; callee만 읽음), `JSR 1ab02`/`1ab80`. `76f2e`/`76f6e`: `A0` = `7706a`/`76ff2`, `D0.W` = `14`, `JSR 28ae`. `76f5e`: WORD `7a(A0)` = `28`(`A0` = `28ae` 자식), `76f68`: WORD `7a(A0)` = `7a(A6)`, `76f6e`: WORD `7c(A0)` = `7c(A6)`. `76f88`: `CLR.W D0; CLR.W D1; JSR 4970a`. `76fa0`/`76fb2`/`76fc6`/`76fd8`: `D0.W` = 0/0/1/1, `JSR 4d7a6`/`49392`. `72d86`/`72dac`/`76ef4`: BYTE `17(A6)` = `ff`, `A0` = `cdeea`/`cdef8`/`cdef8`, `A1` = banked LONG `2000d0`/`2000d4`/`2000d4`, `D1.W` = `3`/`b`/`b`, `D2.W` = `0`/`1`/`1`, `JMP cc8b4`/`cc8b4`/`cc778`(경계). `76f18`: `CLR.B 5e(A6); RTS`.
- 호출·설치: `71108` `71126` `71136` `71148` `71156` `71178` `711a6` `711b6` `711c4` `711d2` `711fa` `71204` `71afe` `71b38` `71c2e` `71da4` `71dcc` `71e32` `71e82` `76d8e` `76e24` `76e58` `76e8a` `76eb4`은 node LONG `(A6)` 쓰기다(`MOVE.L`이라 C = 0).

## 구현 범위와 규약

- routing 16 범위(결정 2). 짝수 PC 1,136개 중 block 시작 217, 내부 919(묶인 `71c52` 포함). 내부 PC 직접 진입은 `unsupported animation objects n15 PC`다. 범위 이웃과 TRAP·표·참조 없는 코드는 기존 실행부 또는 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다. `NEG`/`SUB`/`ADD`/`CMP`/`CMPA`는 원래 폭의 무부호 산술로 계산하고 C++ 부호 있는 overflow나 부호 있는 shift에 기대지 않는다(`ASR.L`은 부호 bit 채움을 명시, `LSL.L`은 32비트 mask). flag는 같은 block 안의 Bcc만 쓴다(예외: 결정 3의 묶음, 결정 4의 들어온 C).
- **FLOW_ONLY 94개**(C 보존): `493e0` `493ec` `7028e` `702ae` `702b0` `7054c` `70556` `7056a` `70574` `7057e` `705ca` `71062` `7108e` `710ba` `710e4` `710ee` `7110e` `7114e` `71152` `7115c` `71166` `7117a` `7119e` `711a2` `711ac` `711c0` `711ca` `711ce` `711d8` `711e2` `7120a` `71ad2` `71b28` `71b2e` `71b3e` `71bf0` `71c48` `71c56` `71c6e` `71d78` `71db2` `71dbc` `71dc2` `71dc8` `71dd2` `71e06` `71e72` `71e78` `71e88` `72d66` `72d6c` `72dce` `76d44` `76d4a` `76d56` `76daa` `76db6` `76dba` `76dd8` `76de2` `76de8` `76dec` `76df2` `76df8` `76e2a` `76e34` `76e3a` `76e3e` `76e44` `76e4a` `76e4e` `76e5e` `76e90` `76e9a` `76ea0` `76ea4` `76eaa` `76eb0` `76eba` `76eca` `76ed4` `76ed8` `76ede` `76ee4` `76eee` `76f1e` `76f28` `76f2c` `76f3e` `76f84` `76f96` `76fbc` `76fe2` `76fec`.
- **소비자 16개**(FLOW_ONLY 안): `71152` `711a2` `711c0` `711ce` `71dc8` `76e4a` `76eb0` `76ed4` `76f28` `76f3e` `76f84` `76fbc` `76fe2`(BCC: Clear면 분기), `76daa` `76dba`(BCS: Set이면 분기), `71c48`(결정 4). Unknown C면 `objects n15 caller requires known carry`(상태 보존).
- **known carry 생산 15개**(요약). 그 밖 108 block(`MOVE`/`MOVEQ`/`TST`/`CMP`/`CMPI`/`CLR`/`NEG`/`ADD`/`ADDI`/`SUB`/`SUBI`/`SUBQ`/`AND`/`ANDI`/`EOR`/`ASR`/`LSL`/`EXT`/`SWAP` block, `MOVE.L #imm,(A6)` 설치 block(`710d2` 제외), `MOVE`+`JSR` block, banked animation block, 표 block `7116c` `711e6`, 묶음 `71c86`, 소비자 없는 `ORI CCR` `76f50` `76f92`, `CLR.B; RTS` `76f18`)은 Unknown이다.
- 제어 이동은 모두 정적이다(계산 PC 없음). 스택: `JSR`/`BSR` 복귀 LONG만.
- I/O port 쓰기 없음. bank 변경 없음. work RAM 밖 쓰기, 미해결·홀수 읽기는 기존 checked 오류다(예: A6/A0 홀수, `22(A6)` bank 포인터 홀수일 때의 LONG 읽기, `711e6`의 `70d72` + sext(`D0.W`×4)가 물리 자료 밖일 때).

## 자료

- [F] banked window LONG `2000d0`(`7103a` `71aaa` `71bc8` `71d50` `71dde` `72d86`), `2000d4`(`71066` `71ad6` `71bf4` `71d7c` `71e0a` `76d66` `76dfc` `76e62` `72dac` `76ef4`). 그 값(bank 안 animation 자료 표)에서 LONG `4` `1c` `20` `24` `28` `3c` `40` `44`를 읽어 `A1`로 `49f8c`에 넘긴다. C++는 주소를 고정하지 않고 현재 bank base로 읽는다(PVC bank 모델).
- [F] fixed ROM 자료(이 단위가 직접 읽음): LONG 표 `7117e`(8 entry, `7116c`), LONG 표 `70d72`(`711e6`; index는 경계 `70302`의 `D0`; [F] 처음 8 LONG `0` `71502` `71562` `715c2` `71622` `716ca` `716ca` `716ca`, 그 뒤는 코드 바이트). 표 값은 node LONG에 쓰기만 한다.
- [F] 이 단위가 직접 읽지 않고 주소만 넘기는 fixed ROM 자료: `6fe3c`(`4ae4a` 히트박스 표), `c88ee`(`490ba`), `772be`(`1ab02`/`1ab80` 사각형), `cdeea` `cdef8`(경계 `cc8b4`/`cc778`).
- [F] work RAM: node(A6) WORD `1e` `20` `2c` `42` `46` `54` `68` `76` `78` `7a` `7c` `80` `86` `8e` `9a` `9c`, LONG `(A6)` `c` `22` `36` `3a` `64`, BYTE `15` `17` `5e` `61` `6e` `6f` `82` `87`; 부모 node(`c(A6)`) BYTE `62`; `76f98`이 돌려준 node(`A0`) WORD `42`; `28ae` 자식(`A0`) WORD `7a` `7c`; A5 BYTE `568e`.
- [I] `708a6`은 `7090a` 계열(U13 `70932` 상태 선택)의 객체 생성 callback이고 `71032`/`710e4`는 걷기 상태(속도 `64(A6)`, `49a58` 난수로 방향·속도, `7117e` 표로 다음 상태 무작위 선택), `71a80`/`71dd6`은 뛰기·점프 상태(`36`/`3a` 속도를 `64`/`fff00000` 쪽으로 1/32씩 접근), `72d66`은 공용 피격 꼬리(`61(A6)` bit 7이면 부모에 `62` 표시 후 `cc8b4` 사망 animation)로 보인다. `493bc`는 `A0`가 선수 1/2 node(`100cb8`/`100da8`)인지와 `568e(A5)`의 그 선수 bit를 돌려준다. `76d18`은 다른 객체(사각형 `772be` 안 선수 판정 `1ab02`, `76f98` 선수 선택)이고 `76f1e`는 interpreter 명령으로 `28ae` 자식 둘을 만든다. 게임 의미는 미확인이다.

## 의존·경계

- [F] N15 → 기존(모두 routing됨): U12 `70418`(`708a6`)·`490ba`(`76d56`)·`4c0ac`(`76d4a`), U13 `70932`(`708b0` BRA), N08 `4ae4a`(`702b0`)·`4983e`(`76d9c`; C 반환)·`4945e`(`76fec` JMP; C 반환), N04 `4bc04`(`705de`)·`71c90`(`71db2` BEQ)·`71d0a`(`71c2e` BRA)·`71ca0`/`71ccc`(`71c86` 묶음 뒤)·`72dd2`(`7120a` `71b3e` `71dd2` BRA)·`72e3e`(`72dce` BRA), interpreter `49f8c`(animation 13곳)·`49fc6`(`7110e` `71b28` `71dc2` `71e72` `76df2` `76e44` `76eaa`; C 반환), stage area `49a58`(`7108e` `71094` `71166` `71c56`), U17 `4bfa4`(`710ee` `71dbc`), U08b `4be34`(`71b04` `71e4e`), U18 `4be2c`, U11 `4be06`, U01 `4b54e`(`72d66` `76ede`), U05 `c6a96`(`76d18`)·`1ab02`(`76eca`; C 반환), N05 `1ab80`(`76f1e`; C 반환), U20 `492d0`(`76e4e`), fade_card `28ae`(`76f2e` `76f6e`; C 반환)·`2a00`(`76ed8` JMP), input `4d7a6`(`76fa0` `76fc6`), frame_helpers `49392`(`76fb2` `76fd8`; C 반환). 이 callee들은 대기(waiting)를 돌려줄 수 있다(기존 동작).
- [F] 실행부 없는 경계: `70302`(`711e2`), `70594`(`711b6`), `cc8b4`(`72d86` `72dac`), `cc778`(`76ef4`), `e9112`(`76eee`), TRAP `493c6`, N14 `4970a`(`76f42` `76f88`). 시험은 그 PC의 stop 성립만 확인한다(F4 시험 경계 관례). rollback 탐침은 RAM `10fe00..10fefe`만 쓴다.
- [F] 다른 단위 → N15: stage event 표(`708a6` `76d18`), U13 `70a64`·N04 `72d38`(`71032` 설치), N04 `71d40`(`71d48` 설치), N09 `b0232`(`493bc`), interpreter 명령 callback(`76f1e`), 미연결 `7090a` 상태들(`7028e` `7054c` `705ca` `72d66`, 설치 `71032` `71a80` `71bc0` `71d48` `71dd6`, 분기 `71c48`), 미연결 `770b8`(`76f98`).

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 217 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 생산 15개, 그 밖 Unknown), 소비자 16개의 Unknown C checked 오류(상태 보존; `71c48`은 bit 1 = 0이면 Unknown이어도 통과), zero-step, 내부 919 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 경계 `70302` `70594` `cc8b4` `cc778` `e9112` `4970a` TRAP `493c6`과 다른 단위 callee는 stop만. 생산 C는 실제 ROM 소비자(`493bc` → N09 `b0238 BCC`, `7028e` → `711ce`, `7054c` → `71152`, `705ca` → `711a2`, `76f98` → `76dba`, `710d2` → `71c48`)의 native 분기로 확인한다. bank LONG과 bank 자료, 표 `7117e` `70d72`는 합성 물리 바이트(ROM 자료 아님)로 주고 원본 코드로 만든 Unicorn typed fixture와 비교한다. 외부 소비자 C는 실제 생산자(`28ae` `49fc6` `1ab02` `1ab80` `49392` `4983e` `4945e`)를 지나는 Unicorn fixture로도 확인한다.
- 실제 ROM 차분: 8개 `program_rom_*.ms5d` window를 physical ROM으로 써서 typed 입력에서 C++와 Unicorn이 같은 결과를 낸다(모든 진입, 실제 callee 생산 C를 거친 소비자 분기, 실제 표 `7117e` `70d72`).
- 차분(F2 프레임 패스, 142 seed): 기준 이상, 불일치 0, 회귀 0, 완주 변화 없음 기대. RNG 초기화 400 frame 차분: 불일치 0, `other` 없음, 완주 변화 없음 기대(seed 76 77 98 99 104 105의 첫 미연결 지점이 `708a6` → `7a53c`).
- 무효화 탐침 정리(결정 7): `engine/tests/animation_machine_frame_helpers_test.cpp`의 routing 밖 탐침 `0x493bc`를 RAM 탐침으로 바꾼다. `tools/verify_animation_machine_frame_helpers.py`의 `outside_range_entry_0493bc`(기대 `unsupported animation machine PC`)는 N15 뒤 성립하지 않는다(도구는 고치지 않고 보고).

## 작업자 검증 기록 (scratch)

- [F] 공유 수정(브리프 허용 범위): `animation_machine.cpp` routing `else if` 1개(N13 뒤, 16 범위)와 carry 보존 case 묶음 1개(`// BTST/BEQ changes only Z` 앞, 94개), `animation_machine_internal.h` 선언 1줄, `Makefile`(source 목록·test target·실행 줄, Codex 공용 object 구조 유지), `tools/verify_animation_machine.py` SOURCES, 무효화 탐침 1곳(`engine/tests/animation_machine_frame_helpers_test.cpp`의 `0x493bc` → RAM `0x10fe90`, 결정 7). `animation_machine_interpreter.cpp`는 바꾸지 않았다.
- [F] `make -j4 all test` 종료 0, 경고 0, Assert 0(기존 test 모두 통과; frame_helpers test `PASS 1065 API invocations`). 새 test: `animation machine objects n15: 650 fixtures (25 checked errors, 283 known C), 217 blocks, 2922 calls`. UBSan(`-fsanitize=undefined -fno-sanitize-recover=undefined`) 같은 출력, 종료 0.
- [F] typed fixture(scratch `gen/gen_n15.py`): 217 시작 모두 native fixture로 덮임. 소비자 16개 Unknown C 오류(`71c48`은 `82(A6)` bit 1 = 1), `71c48` bit 1 = 0이면 Unknown C로도 `71c56`(오류 없음), 시작마다 3 carry 한 block 후계·carry 분류(생산 15개: 고정 12, 계산 3), zero-step, 내부 919 PC(묶인 `71c52` 포함), 홀수 PC 32개, RAM rollback 탐침(`10fe50` `10fe60` `10fe70`, RTS 끝 16 fixture의 복귀 LONG `10fe80`), 경계·다른 단위 callee stop 38종(`70302` `70594` `cc8b4` `cc778` `e9112` `4970a` TRAP `493c6` 포함). 실제 소비자 확인(Unicorn SR 미사용): `493bc` 계열 RTS를 N09 `b0238 BCC`로 돌려 C Clear·Set 양쪽, `7028e`/`7054c`/`705ca` 계열을 `711ce`/`71152`/`711a2`로, `76fc0`/`76fe6`을 `76dba`로, `710d2` Clear를 `71c48` 묶인 `BCS`로 확인했다. 외부 생산자를 따라간 행: `4bc04`(N04), `4983e`(N08 `49876`; `4985e` BCC 분기 또는 `CMP.W D3,D1` 빌림을 진입 레지스터로 계산), `1ab02`(U05 `1ab7a` Clear / U01 `1aafc` Set), `1ab80`(N05 `1abd4` / `1aafc`), `28ae`(`2908` Set / `290e` Clear), `49392`(`4939e`..`493a2` Clear / `493b6` Set). 소비자 16개 모두 C Clear·Set 양쪽에서 native 분기가 계약 carry와 같았다(확인 205건). 경계값: `7029e`(`42` = `30`/`10f`/`110`/`2f`/`8030`), `705f0`(`3f`/`40`/`ffff`), `71c5c`(`15f`/`160`/`8000`/`ffff`), `76f54`(`9`/`a`/`ffff`), `71b04`/`71e4e` ASR(`80000000`/`7fffffff` 쌍), `711e6` index(`ffff` `fffe` → 음수, `4000` `4001` → wrap), `493e0` bit(`D0` = 9 → bit 1).
- [F] 돌연변이 12개 모두 test에서 실패했다(`493c8` 계산 C 반전, `7029e` 부호 비교, `71c48` 무조건 소비, `71c86` 묶음 분기 교환, `ASR.L`을 `LSR.L`로, `711e6` index 부호확장 누락, `7116c` mask `3c`, `710d2` Clear 누락, `493e0` bit mod 8 누락, `71c5c`·`76f54` 부호 비교, `71114` EOR 누락).
- [F] 실제 ROM 차분(`realrom/real_n15.py`, 8개 `program_rom_*.ms5d`, bank 200000/300000, seed 1·2·3 각 1,500건; native stop은 STOP, `2a00`, sprite 대기 `cd58`, 이 트리 routing 밖 PC(경계 포함), 실제 소비자 `b0238` `711ce` `71152` `711a2` `76dba` 분기 뒤): 불일치 0/0/0, carry 불일치 0, 비교된 사례만으로 217 시작 모두 도달(seed마다 217/217). native port 쓰기(3,688/3,798/3,670건)도 순서까지 같다. 실제 소비자 native 분기 = C++ carry: seed 1 `b0238` C1 17·C2 12, `711ce` 41·9, `71152` 23·14, `711a2` 26·7, `76dba` C1 62(seed 2·3도 같은 형태, 모두 일치). 의도된 차이: `710e4`를 Unknown C로 진입해 `71c48`에서 `BCS`가 평가된 2/3/2건은 C++ `objects n15 caller requires known carry`(결정 4). Unknown C로 진입해 FLOW RTS(`493e0` `493ec` `702ae`)로 소비자에 닿은 3/3/2건은 C++가 C를 주장하지 않는다(Unknown; 불일치로 세지 않음). native가 6,000,000 명령 안에 멈추지 않은 149/171/164건은 제외했다. harness는 기존 실행부 block 내부 PC(재범위 15개 + exit `3d50` + cleanup `46ef4`/`46f08`/`8e4a` block 내부)를 routing된 것으로 본다.
- [F] 기준(`89f8fec` 사본 `ms5-scratch/n15/basetree`) F2 프레임 패스 차분(base, 142 seed): 일치 pass 13,688·node 112,576, 불일치 0, 자연 완주 125. N15 뒤: 같은 값(pass 13,688·node 112,576), 불일치 0, 자연 완주 125, 회귀 0, 변화 seed 0(base 기록은 N15 PC를 실행하지 않는다).
- [F] RNG 초기화 400 frame 차분: 기준 일치 pass 46,400·node 343,657, complete 116. N15 뒤 pass 46,400·node 343,669, 불일치 0, `other` 없음, complete 116(변화 없음), 회귀 0. 변화는 seed 76 77 98 99 104 105뿐: 첫 미연결 callback이 frame 0의 `708a6`(node index 8/9) → `7a53c`(N17; node index 10/11), seed마다 일치 node +2. 응답 `00` 변형 6 seed: complete 6 → 6, 불일치 0. 정적 재생 예측과 같다.
- [F] ROM SHA256·mtime 작업 전후 같음.

## 미확인·범위 밖

1. [U] 게임 의미(위 "자료"의 [I]).
2. [U] 경계 `70302`(상태 번호 계산)·`70594`(C 반환)·`cc8b4`/`cc778`(사망 animation 표 루틴)·`e9112`와 범위 밖 설치 대상(`712a0` `713d8` `71468` `7120e` `72978` `72f8a` `70c0c` `71e8c`)·`28ae` 자식(`7706a` `76ff2`)은 이 단위 밖이다(재범위 "미실행 설치 14(+170)"). 400 frame 자연 기록에서 실행되지 않는다.
3. [U] `70d72` 표의 정적 상한: index는 경계 `70302`의 `D0`이다. [I] `70302`의 끝(`7039c MOVE.W #7,D0`부터 `SUBQ`/`BCS` 사슬)으로 보아 0..7이고 처음 8 LONG(`0` … `716ca`)만 쓰인다. 자료 읽기라 C++는 bus 규칙만 적용한다.
4. [U] `71c48` 묶인 `BCS`가 dispatcher(앞 callback이 남긴 C)로 들어올 때의 원본 의도. C++는 known이면 정확히, Unknown이면 checked 오류다(결정 4).
5. [U] `71c86`의 N04 내부 `71c98` 묶음(결정 3)은 N04가 `71c98`을 block 시작으로 나누면 풀 수 있다(메인 결정).
6. [U] `tools/verify_animation_machine_frame_helpers.py`의 `outside_range_entry_0493bc`는 N15 뒤 기대와 다르다(결정 7; 도구 미수정).

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n15/`(`n15blocks.py` block·범위 계산, `cls15.py` 분류, `fmt15.py` 목록, `n15refs.py`/`n15raw.py` 참조, `n15reach.py` 자연 도달·기대 완주, `n15route.py` routing 확인, `gen/` fixture 생성, `realrom/` 실제 ROM 차분, `fp/` 프레임 패스 차분, `mut/` 돌연변이, `basetree/` 기준 사본; 저장소 밖).
