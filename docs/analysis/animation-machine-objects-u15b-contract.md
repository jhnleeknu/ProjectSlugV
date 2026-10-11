# 객체 callback F4 U15b: 지형 이동 표 `4578a`/`45798`(96 entry 전체)와 대상 본문, `45afe` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U15 행과 U15 계약(`animation-machine-objects-u15-contract.md`, SHA256 `2f7e15b5f68973dd8113fb2eb2cce625c2a1926fb781a98554fef93da2c7294a`)의 "U15 분할" 제안(U15b = 144 block)이다. 단위 형식과 규약은 U08 계약(SHA256 `fd484c1cc1bcd87a87f69892451a1cfd36528db5797cca7298514c8c1f703d8d`, 표 `4483a`의 계산 PC 정책과 `447be` D7 상한), U08b 계약(SHA256 `a75aa7748c9acba9f9f16e97cefbed77308fe429d0103e8683f2f9bdd5c0d7a8`, 호출 site `463b8` `464ca`), U11 계약(SHA256 `ab51cd6d422c9a97fc9a705b4d11254716b69bebd4610a93c0cd58c656940d7d`, 표 `45176` 전체 이식)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, 점프 표 entry)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 4: 지형 점프 표는 index 상한을 정적으로 확정하고 표 전체를 옮긴다. 결정 5: 단위는 함수 본문 전체다.
- U01~U15a 수용 관례: 같은 flag를 쓰는 연속 Bcc는 앞 block에 묶는다. `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`EXT`/`NOT`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). `JMP`/`BRA`/`RTS`만인 block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U15b의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u15b`(HEAD `d38f7e0` = U15a까지의 WIP, `engine/src/animation_machine.cpp` SHA256 `ceaa6aedb3fab7366a9c2ce528e84174d80f7bfe1a4fe5548c7e2ef5dbb02eac`, routing 규칙 50개)을 참조했다. U16(`b0106..b02e6` `bbe12..bbf02` `f1a0e..f1a34`)은 다른 작업 트리다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u15b/u15b.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U15b는 **block 시작 144개**다(U15 계약 제안과 같다).
  - 진입 `4578a`(`D2|D3`=0이면 RTS) 1, 점프 표 block `45792`(`MOVE.W 54de(A5),D4; EXT.L D4; JMP 4579c(PC,D7.W)`) 1.
  - 표 entry 96(`4579c+4k`, k=`0..5f`, 모두 `BRA.W`, opcode `6000`).
  - 대상 본문 `4591c..45afe` 43: 짧은 꼬리 7(`4591c` `4591e` `45922` `45926` `45930` `45932` `45936`), 기울기 본문 12개 × 3 block(앞 block, `NOT.L D4` block, 뒤 block).
  - `45afe` 계열 3(`45afe` `45b06` `45b10`).
  - 코드 1 범위 `4578a..45b12`, 904바이트, 287명령이다. routing 짝수 PC는 452개, 내부 PC는 308개(표 displacement WORD 96 포함)다.
  - 묶인 Bcc 2개: `4592c BLT`는 `45926`(`TST.L D2; BGT`)에, `45b0c BLT`는 `45b06`(`TST.L D3; BGT`)에 묶는다(같은 TST의 N·Z·V를 쓴다).
  - 호출(JSR/BSR)·TRAP·SUBX/ADDX·MULx/DIVx·레지스터 간접 점프·`MOVE.L #imm,(A6)` 없음. PC 상대 점프 표는 `45798` 하나다.
- [F] **carry**: U15b 안에 block 경계를 건너는 C 소비 block과 known carry 생산 block이 없다. ROM의 정적 호출자 4곳 바로 뒤 명령(`463bc MOVEQ`, `464ce MOVE.L`, `46678 MOVEQ`, `46750 MOVE.L`)은 C를 읽지 않는다(`nextins.py`). block 안 flag(`OR.L`+`BEQ` Z, `ADD.L`/`SUB.L`+`BPL` N, `TST.L`+`BGT`/`BLT` N·Z·V, `CMPI.W`+`BNE` Z)는 같은 block 안에서 만들고 쓴다.
- [F] 읽는 자료: work RAM WORD `54de(A5)`(`45792`) 하나. 쓰기 없음. I/O port 쓰기와 bank 변경이 없다. 스택은 호출자의 BSR 복귀 LONG을 RTS로 꺼낼 뿐이다.
- [F] 경계 callee 없음. 범위 밖 출구는 RTS뿐이다. `45afe BNE.W 4578a`는 범위 안 분기다.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`) 22 seed, RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 28 seed가 `4578a`·`45afe`에 닿는다. 닿는 시작은 둘 다 8개(`4578a` `45792` `45900`(k=`59`) `45904`(k=`5a`) `4590c`(k=`5c`) `4591e` `45922` `45afe`)다. 범위 안 TB 시작은 모두 정적 시작이다.
- [F] **C++ 프레임 패스에서는 U15b에 닿지 않는다.** 두 호출 경로 모두 바로 앞에서 U15c 쪽 함수를 부른다: U08b `463b4`/`464c6 BSR 45b12` 뒤 `463b8`/`464ca BSR 4578a`, U15a `46670`/`46748 BSR 45b1a` 뒤 `46674`/`4674c BSR 45afe`. `45b12`·`45b1a`는 이 작업 트리에서 routing 밖이므로 기준 차분의 pass는 그 앞에서 멈춘다. 그래서 U15b 병합만으로는 새 완주 seed가 없을 것으로 본다([I], 검증 기록에서 확인).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **표 `45798`의 C++ 형태(U08 결정 2·U11 결정 4와 같음).** `45792`는 `MOVE.W 54de(A5),D4; EXT.L D4` 뒤 PC=`4579c`+sext(`D7.W`)로만 옮긴다(32bit 덧셈). 96 entry의 `BRA.W` 대상은 C++ 상수 배열로 옮겨 적는다(코드 바이트를 자료로 읽지 않음). 상한 밖 값은 routing이 정한다(아래 "점프 표"). 원본과의 의도된 차이: 계산 PC가 block 시작이 아닌 명령 시작이나 명령 중간 WORD이면 원본 CPU는 그 주소부터 실행하지만 C++는 `unsupported animation objects u15b PC`로 멈춘다(상한 밖 D7에서만 생김).
2. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u15b.cpp`의 `animation_objects_u15b_block`. 내부 PC는 `unsupported animation objects u15b PC`. U15b에는 carry 소비자가 없으므로 `objects u15b caller requires known carry`는 실행 경로에서 나오지 않는다(문자열은 지시대로 예약만 하고 쓰지 않는다; 쓰는 곳이 없으면 넣지 않는 것을 권고).
3. **`ASR.L #8/#4/#1`·`ASR.L #6`×2와 `LSL.L`.** 산술 shift는 부호 채움으로 명시 구현한다(C++ 부호 있는 shift에 기대지 않음). `LSL.L`/`ADD.L Dn,Dn`은 32bit 무부호 shift·덧셈(mod 2^32)이다.
4. **무효화 탐침 교체(아래 "회귀 탐침").** U08b test의 rollback 탐침 `4578a` 2곳을 `5ff40`·`5ff44`(어느 `docs/analysis` 문서에도 없고 routing 밖)로 바꾼다.
5. **U15c 범위 보고(U15b 밖).** [F] U08b의 경계 callee `45b12`(`463b4` `464c6 BSR 45b12`)는 `CMPI.W #174,D7; BEQ.W 45e6c`이고 `45b1a`로 fall-through한다. U15 계약의 U15c 제안 범위 `45b1a..461ec`에는 `45b12..45b1a`(block `45b12` 1개)가 없다. U15c 계약에서 `45b12`를 넣을지 메인이 정해야 한다. U15b는 `45b12`를 routing하지 않는다(범위 이웃).

## 원본 바이트 근거

[F] 코드 1 범위 904바이트.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `4578a..45b12` | 904 | `fb24e2261511d4b37e51cf9bade91ac8729be2aac954011edb81b90de5d32bf4` | 진입 `4578a`, `JMP` `45798`, 표 entry `4579c..4591c`, 대상 `4591c..45afe`, `45afe` |

- [F] 범위 밖 이웃(routing 밖 또는 다른 실행부): `45788`(U11 `45772` block의 `RTS`, U11 routing `45176..4578a` 끝), `45b12`(U08b 경계 callee, 위 결정 5), `45b1a`(U15c 제안).
- [F] 자료: work RAM WORD `54de(A5)`(live bus, A5 부호확장 d16). [I] U09 `469d8`이 0을, `46a32`가 `ffff`를 쓴다(U09 계약). 표 entry는 코드이며 자료로 읽지 않는다.

## 점프 표 `45798`과 index 상한(결정 4)

- [F] `45798`: `JMP 4579c(PC,D7.W)`(PC 상대 기준 `4579c`). 표 `4579c..4591c`는 96개 `BRA.W`이고 바로 뒤 `4591c`는 `RTS`(대상 본문 첫 block)다. index(16진 k, `D7.W`=4k)→대상:
  - `00..1f`: (`45aac` `45ad4` `45ad4` `45aac`) ×8.
  - `20..23`: `45932` `45936` `45932` `45936`.
  - `24..33`: (`4593a` `45960` `45960` `4593a`) ×4.
  - `34..3b`: (`45988` `459ae` `459ae` `45988`) ×2.
  - `3c..3f`: `459d6` `459f2` `459f2` `459d6`.
  - `40..47`: (`45a10` `45a36` `45a36` `45a10`) ×2.
  - `48..57`: (`45a5e` `45a84` `45a84` `45a5e`) ×4.
  - `58..5f`: `4591c` `4591e` `45922` `4591e` `4591e` `45926` `4591c` `4591c`(`58`=`D7` `160`, `5d`=`174`).
- [F] 정적 호출자 4곳(모두 `BSR.W`, `refs.py`): U08b `463b8` `464ca` → `4578a`, U15a `46674` `4674c` → `45afe`(`D7.W`≠`174`이면 `BNE 4578a`).
  - [F] 네 site 모두 바로 앞에서 `BSR 4483a` 뒤 `CMPI.W #160,D7; BEQ`로 `160`을 건너뛰고(`463ac` `464be` `46668` `46740`), 그 사이의 `BSR 45b12`/`BSR 45b1a`(범위 `45b12..461ec`)는 D7을 쓰지 않는다(그 범위 디코드에서 D7 목적지 명령 0개; `CMPI.W #174,D7`과 `JMP (PC,D7.W)` 읽기뿐).
  - [F] `4483a` 대상은 D7을 그대로 두거나 `449be`(`MOVE.W #160,D7`)로 간다(U08 계약). `4483a` 진입 D7은 U08 계약대로 `447be` 결과 `4k`(k<`60`) 또는 `160`, 또는 함수 진입 D7·`54b0(A5)`다.
  - 따라서 `D7.W` ∈ {`4k` | k<`60`} \ {`160`}이고 모두 표 안 entry다. [U] 함수 진입 D7 경로의 전 호출 closure는 U08/U11 계약과 같이 확인하지 않았다. 아래 계산 PC 정책이 그 밖의 값도 원본과 같이 옮기므로 실행 의미는 상한 확정에 의존하지 않는다.
  - [F] 자연 관측 index는 `59` `5a` `5c`(위 요약)다.
- [F] **상한 밖 D7(계산 PC 정책, F1 결정 3).** 대상 PC=`4579c`+sext(`D7.W`)는 `3d79c..4d79a`다.
  - `180` → `4591c`(block, RTS). 표 안 displacement WORD(`4579c+4k+2`) → `unsupported animation objects u15b PC`.
  - 범위 안 block 시작 → 그 block 실행(원본과 같음). 범위 안 block 시작이 아닌 명령 시작 143개와 명령 중간 WORD 69개(displacement WORD 제외) → `unsupported animation objects u15b PC`(의도된 차이, 결정 1).
  - `fff6` → `45792`(자기 block): 원본도 무한 반복, C++는 `animation machine block budget exceeded`. `ffee` → `4578a`: `D2|D3`≠0이면 같은 무한 반복(같은 budget 오류), =0이면 `4591c` RTS. `fffc`(`45798` 자신의 `JMP`)·`fffa`(`45796 EXT.L`)는 block 안 명령이라 `unsupported animation objects u15b PC`(원본은 무한 반복).
  - 홀수 → `unaligned animation machine PC`. 범위 밖 → `unsupported animation machine PC` 또는 그 PC의 다른 실행부(U11 `45176..4578a` 등).

## block 목록과 실행 의미

[F] 144 block. 각 줄은 block 안 명령 전체다. "(→x)"는 다음 block으로의 fall-through다. `BPL`은 N=0, `BGT`는 부호 LONG `>0`, `BLT`는 부호 LONG `<0`, `BEQ`/`BNE`는 Z다. `ASR`은 부호 채움, `LSL`은 0 채움이다. `.L` 연산은 mod 2^32다.

**진입·표 98**
- `4578a`: `MOVE.L D2,D5; OR.L D3,D5; BEQ.W 4591c` (`D5`=`D2|D3`)
- `45792`: `MOVE.W 54de(A5),D4; EXT.L D4; JMP 4579c(PC,D7.W)` (계산 PC, 결정 1)
- `4579c+4k`(k=`0..5f`, 96 block): `BRA.W` 위 표의 대상

**짧은 꼬리 7**
- `4591c` `45930` (와 `45b10`): `RTS`
- `4591e` `45922`: `MOVEQ #0,D3; RTS`
- `45926`: `TST.L D2; BGT.W 45932; BLT.W 45936` (묶인 `4592c`; `D2`=0이면 →`45930`)
- `45932` `45936`: `MOVEQ #0,D2; RTS`

**기울기 본문 12 × 3 = 36**
- 앞 block(p=주 성분, q=부 성분, s=q의 shift, ±): `q ← q<<s`(s=0이면 그대로; `ADD.L Dq,Dq`는 s=1, `LSL.L #s,Dq`); `p ← p ± q`(`ADD.L`/`SUB.L`); `BPL.W 뒤 block`(결과 p가 음이 아니면 뒤 block으로, 음이면 →NOT block).
- NOT block: `NOT.L D4` (→뒤 block)
- 뒤 block(m=곱 shift, M=마스크, a=ASR, f=마지막 shift, neg): [m>0: `MOVE.L Dp,Dq; LSL.L #m,Dp; SUB.L Dq,Dp`(p ← p·(2^m−1))]; `ANDI.L #M,D4; ADD.L D4,Dp; ANDI.L #~M,Dp; ASR.L #a,Dp`; `MOVE.L Dp,Dq; q ← q<<f`(`LSL.L #f`/`ADD.L Dq,Dq`); [neg: `NEG.L Dq`]; `RTS`.

| 앞 block | NOT | 뒤 block | p | q | s | ± | m | M | a | f | neg |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `4593a` | `45942` | `45944` | D2 | D3 | 2 | + | 4 | `7ffff` | 8 | 2 | |
| `45960` | `45968` | `4596a` | D2 | D3 | 2 | − | 4 | `7ffff` | 8 | 2 | NEG |
| `45988` | `45990` | `45992` | D2 | D3 | 1 | + | 2 | `7fff` | 4 | 1 | |
| `459ae` | `459b6` | `459b8` | D2 | D3 | 1 | − | 2 | `7fff` | 4 | 1 | NEG |
| `459d6` | `459dc` | `459de` | D3 | D2 | 0 | + | 0 | `3ff` | 1 | 0 | |
| `459f2` | `459f8` | `459fa` | D3 | D2 | 0 | − | 0 | `3ff` | 1 | 0 | NEG |
| `45a10` | `45a18` | `45a1a` | D3 | D2 | 1 | + | 2 | `7fff` | 4 | 1 | |
| `45a36` | `45a3e` | `45a40` | D3 | D2 | 1 | − | 2 | `7fff` | 4 | 1 | NEG |
| `45a5e` | `45a66` | `45a68` | D3 | D2 | 2 | + | 4 | `7ffff` | 8 | 2 | |
| `45a84` | `45a8c` | `45a8e` | D3 | D2 | 2 | − | 4 | `7ffff` | 8 | 2 | NEG |
| `45aac` | `45ab4` | `45ab6` | D3 | D2 | 3 | + | 6 | `3fffff` | 12(`ASR.L #6` 두 번) | 3 | |
| `45ad4` | `45adc` | `45ade` | D3 | D2 | 3 | − | 6 | `3fffff` | 12 | 3 | NEG |

- [F] 각 행의 원본 명령(예 `4593a`: `LSL.L #2,D3; ADD.L D3,D2; BPL.W 45944` / `45942`: `NOT.L D4` / `45944`: `MOVE.L D2,D3; LSL.L #4,D2; SUB.L D3,D2; ANDI.L #7ffff,D4; ADD.L D4,D2; ANDI.L #fff80000,D2; ASR.L #8,D2; MOVE.L D2,D3; LSL.L #2,D3; RTS`)은 scratch `u15dis.py 4578a..45b12` 출력과 같다. `459de`: `ANDI.L #3ff,D4; ADD.L D4,D3; ANDI.L #fffffc00,D3; ASR.L #1,D3; MOVE.L D3,D2; [NEG.L D2;] RTS`(곱 없음). `45ab6`: `... ANDI.L #ffc00000,D3; ASR.L #6,D3; ASR.L #6,D3; MOVE.L D3,D2; LSL.L #3,D2; [NEG.L D2;] RTS`.

**`45afe` 3**
- `45afe`: `CMPI.W #174,D7; BNE.W 4578a`
- `45b06`: `TST.L D3; BGT.W 45922; BLT.W 4591e` (묶인 `45b0c`; `D3`=0이면 →`45b10`)
- `45b10`: `RTS`

(수: 진입·표 98, 꼬리 7, 본문 36, `45afe` 계열 3; 합 144.)

## 구현 범위와 규약

- routing 1 범위: `4578a..45b12`. 짝수 PC 452개 중 block 시작 144, 내부 308(표 displacement WORD 96, block 시작이 아닌 명령 시작 143, 그 밖 명령 중간 WORD 69). 내부 PC 직접 진입은 `unsupported animation objects u15b PC`다. 범위 이웃은 routing 밖이거나 다른 실행부다.
- **FLOW_ONLY 99개**(C 보존): 표 entry 96(`BRA.W`), `RTS`만인 `4591c` `45930` `45b10`. 그 밖 45개(MOVE/OR/EXT/MOVEQ/TST/CMPI/LSL/ADD/SUB/NOT/ANDI/ASR/NEG block과 `45792`의 MOVE+EXT+JMP)는 Unknown이다. carry 소비 block·known 생산 block은 없다.
- 반환 N·Z·V: 본문 `NEG`/`MOVE`/`LSL`/`ADD` 뒤 RTS와 `MOVEQ` 뒤 RTS의 flag는 [F] 호출자 4곳 바로 뒤 명령(`MOVEQ`/`MOVE.L`)이 읽지 않는다. C++는 Unknown으로 둔다.
- 루프 없음(상한 밖 `D7`의 자기 반복만 있음). I/O port 쓰기 없음. bank 변경 없음. 홀수 A5 WORD 읽기, 미해결 읽기는 기존 checked 오류다.

## 의존·경계

- [F] U15b → 기존: 없음(호출 없음, RTS만).
- [F] 기존 → U15b: U08b `463b8`·`464ca BSR 4578a`(U08b 계약의 경계), U15a `46674`·`4674c BSR 45afe`(U15 계약의 경계).

## 자연 시작 상태(읽기 전용 기록)

- [F] F4 범위 scratch 재생(TB 기준): base 22 seed(6 7 18 19 22 23 36 37 42 43 68~71 80 81 96 97 102 103 116 117), RNG 변형 28 seed(그에 더해 2 3 12 13 26 27). 144 block 중 8개 자연 도달, 미도달 136개(나머지 표 entry 93, 본문 대상 전부, `4591c` `45926` `45930` `45932` `45936`, `45b06` `45b10`)는 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] 기준 C++ 차분(작업 트리 `d38f7e0`, F2 프레임 패스 142 seed): 일치 pass 10,498개·node 79,624개, 불일치 0, 자연 완주 89 seed. RNG 초기화 400 frame 차분: 완주 61 seed, 일치 pass 24,646개·node 168,981개, 불일치 0.

## 회귀 탐침(결정 4)

[F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U15b 범위 안 PC를 쓰는 곳(scratch `f4u15b/probes.py`; stop PC로만 쓰는 곳은 그대로 둔다):
- `engine/tests/animation_machine_objects_u08b_test.cpp`: `BOUNDARIES`의 `0x4578a`(stop 행 `463b8` `464ca`의 전체 rollback 재실행; U15b 뒤에는 RTS로 돌아와 성립하지 않음) → `0x5ff40`(stop과 일치하지 않음). `interior()` outside 목록의 `0x4578a`(rollback) → `0x5ff44`. stop 행 자체(`463b8` `464ca` → stop `4578a`)와 block 표 후계 `4578a`는 그대로 성립한다.
- `engine/tests/animation_machine_objects_u15_test.cpp`의 `45afe` stop 행·stop 확인과 `engine/tests/animation_machine_objects_u11_test.cpp`의 범위 끝 `0x4578a`, `engine/src`의 주석·호출 상수는 탐침이 아니다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 144 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 99 보존, 그 밖 Unknown), zero-step, 내부 308 PC 정확한 오류, 표 96 index × 3 carry가 옮겨 적은 대상에 닿음(`45792` 경유와 entry 직접), 표 96 index × 술어 결과(`BPL` 두 쪽, `TST` 세 쪽, `D2|D3`=0)의 끝 상태, 상한 밖 D7(`180`, displacement WORD, block 안 명령 시작, 명령 중간, 홀수, 범위 밖, `fff6`/`ffee` 무한 반복, `fffc`). rollback 탐침은 `5f6xx..5ffxx`만 쓴다. typed fixture는 원본 코드로 만든다(Unicorn, work RAM 입력; ROM 자료는 test에 넣지 않음).
- 실제 ROM 차분: `4578a`·`45afe`의 96 index 전체(D2·D3 부호·크기, `54de` 0/`ffff`/임의, `D7`=`174`의 `D3` 세 쪽, `D2|D3`=0)를 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed): 기준 일치 pass·node가 모두 그대로 일치하고 불일치 0. RNG 초기화 400 frame 차분: 기준 유지, 불일치 0.

## 미확인·범위 밖

1. [I] 표 `45798`은 `447be`의 지형 코드별 이동 성분 보정이다. `(D2,D3)`을 경사 방향으로 투영(`p ± q·2^s`)하고 `(2^m−1)/2^a` 배율(15/256, 3/16, 1/2, 63/4096)로 줄인 뒤 다른 성분을 `2^f`배로 다시 만드는 것으로 보인다. `54de(A5)`(0 또는 `ffff`)는 자르기 전 더하는 반올림 편향이고, 결과가 음이면 `NOT.L`로 뒤집는다. 게임 의미는 미확인이다.
2. [I] `45926`/`45b06`(`D7`=`174` 특례)은 한 성분만 남기고 다른 성분을 0으로 만든다(`45926`은 D2 부호로 D2를, `45b06`은 D3 부호로 D3을 지움). 의미는 미확인이다.
3. [U] 함수 진입 D7 경로의 전 호출 closure(표 상한의 나머지 근거, U08/U11 계약과 같음).
4. [U] `45b12`(U15c 쪽, 위 결정 5)와 U15c 본문의 실행 결과.

작업자 scratch: 세션 scratchpad `f4u15b/`(`u15b.py` block·범위·SHA 계산, `body.py` `trav.py` `hroute_u15.py` `u15dis.py`, `refs.py` `nextins.py` `probes.py` `reach.py`; 저장소 밖).
