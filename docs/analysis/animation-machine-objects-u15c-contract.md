# 객체 callback F4 U15c: 지형 기울기 표 `45b12`/`45b1a`/`45b28`(96 entry 전체)와 대상 본문 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 `animation-machine-object-callbacks-f4-scope.md`(SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U15 행과 U15 계약(`animation-machine-objects-u15-contract.md`, SHA256 `2f7e15b5f68973dd8113fb2eb2cce625c2a1926fb781a98554fef93da2c7294a`)의 "U15 분할" 제안(U15c = 195 block, 범위 `45b1a..461ec`)이다. 단위 형식과 규약은 U08 계약(SHA256 `fd484c1cc1bcd87a87f69892451a1cfd36528db5797cca7298514c8c1f703d8d`, 표 `4483a`의 계산 PC 정책과 `447be` D7 상한), U11 계약(SHA256 `ab51cd6d422c9a97fc9a705b4d11254716b69bebd4610a93c0cd58c656940d7d`, 표 `45176` 전체 이식)을 따른다. U15b 계약 초안(`animation-machine-objects-u15b-contract.md`, 같은 시기 다른 작업 트리)의 결정 5(`45b12` 보고)를 이 계약에서 다룬다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, 점프 표 entry)로 정한다. Unicorn TB 분할은 쓰지 않는다.
- 결정 4: 지형 점프 표는 index 상한을 정적으로 확정하고 표 전체를 옮긴다. 결정 5: 단위는 함수 본문 전체다.
- U01~U16 수용 관례: `MOVE.x`/`TST`/`CMP`/`CMPI`/`ORI`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). `JMP`/`BRA`/`RTS`만인 block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 기존 실행부 block 안의 코드와 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. U15c의 코드는 모두 fixed `<100000`이므로 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-u15c`(HEAD `1aa80c8` = U15a + U16까지의 WIP, `engine/src/animation_machine.cpp` SHA256 `fb9eb6f75c5cebe0eb5a8b747083e8a337d6115aa068f325e57af01df5dae5ed`, routing 규칙 51개)을 참조했다. U15b(`4578a..45b12`)는 다른 작업 트리(`metalslug-u15b`)이고 이 작업 트리에서 routing 밖이다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `f4u15c/u15c.py`가 원본 opcode에서 독립 계산했고 아래 목록과 같음을 assert했다.

## 요약

- [F] U15c는 **block 시작 196개**다(U15 계약 제안 195 + `45b12` 1, 아래 결정 1).
  - 진입 `45b12`(`CMPI.W #174,D7; BEQ.W 45e6c`, U08b의 경계 callee) 1, 진입 `45b1a`(`CMPI.W #174,D7; BNE.W 45b28`, U15a의 경계 callee) 1, `45b22`(`TST.L D3; BGT.W 46198`) 1, 점프 표 block `45b28`(`JMP 45b2c(PC,D7.W)`) 1.
  - 표 entry 96(`45b2c+4k`, k=`0..5f`, 모두 `BRA.W`, opcode `6000`). 대상 96개가 모두 다르고 `45cac+e·k`다.
  - 대상 본문 96(`45cac+e·k`): 각 block이 `ORI.W #m,54aa(A5); MOVE.W #v,54ac(A5); RTS`다.
  - 코드 1 범위 `45b12..461ec`, 1,754바이트, 391명령이다. routing 짝수 PC는 877개, 내부 PC는 681개(표 displacement WORD 96, block 시작이 아닌 명령 시작 195, 명령 중간 WORD 390)다.
  - 묶인 Bcc 없음. 호출(JSR/BSR)·TRAP·SUBX/ADDX·MULx/DIVx·레지스터 간접 점프·`MOVE.L #imm,(A6)` 없음. PC 상대 점프 표는 `45b28` 하나다.
- [F] **carry**: U15c 안에 block 경계를 건너는 C 소비 block과 known carry 생산 block이 없다. ROM의 정적 호출자 4곳 바로 뒤 명령(`463b8`/`464ca BSR 4578a`, `46674`/`4674c BSR 45afe`)은 C를 읽지 않는다(`nextins.py`). block 안 flag(`CMPI.W`+`BEQ`/`BNE` Z, `TST.L`+`BGT` N·Z·V)는 같은 block 안에서 만들고 쓴다.
- [F] 읽고 쓰는 자료: work RAM WORD `54aa(A5)`(읽기+쓰기, `ORI.W`)와 WORD `54ac(A5)`(쓰기). I/O port 쓰기와 bank 변경이 없다. 스택은 호출자의 BSR 복귀 LONG을 RTS로 꺼낼 뿐이다.
- [F] 경계 callee 없음. 범위 밖 출구는 RTS뿐이다.
- [F] 자연 도달(F4 범위 scratch 재생, TB 기준): base(`f4scope/dyn`) 22 seed(6 7 18 19 22 23 36 37 42 43 68~71 80 81 96 97 102 103 116 117), RNG 초기화+응답 `80` 변형(`dyn_rng1_resp80_f400`) 28 seed(위 + 2 3 12 13 26 27)가 `45b1a`에 닿는다. 닿는 시작은 둘 다 8개(`45b1a` `45b28` `45c90`(k=`59`) `45c94`(k=`5a`) `45c9c`(k=`5c`) `4618a` `46198` `461b4`)다. `45b12` `45b22`는 자연 도달하지 않는다. 범위 안 TB 시작은 모두 정적 시작이다.

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **`45b12` 포함(195 → 196).** [F] U08b의 경계 callee `45b12`(`463b4` `464c6 BSR.W 45b12`)는 `CMPI.W #174,D7; BEQ.W 45e6c`(표 대상 k=`20`)이고 `45b1a`로 fall-through한다. U15 계약의 U15c 제안 범위 `45b1a..461ec`와 U15b 범위 `4578a..45b12`가 모두 이 8바이트를 뺐다(U15b 계약 결정 5가 먼저 보고). 범위 문서·U15 계약 어느 단위에도 소유가 없다.
   - 권고: U15c에 넣는다(범위 `45b12..461ec`, 196 block, 지시 상한 ~220 안). 같은 표의 두 번째 진입이고 다른 단위에 넣을 곳이 없다. U08b 경로 `46372`/`4683c`의 `463b4`/`464c6`이 U15c를 지나 U15b `4578a` 경계까지 이어진다.
   - 대안: U15c를 제안대로 `45b1a..461ec`로 두고 `45b12`를 별도 단위로 미룬다(비권고: 1 block 단위).
   - 영향: U08b test의 `45b12` 탐침 2곳이 깨진다(아래 결정 4). U15b 작업 트리도 같은 두 줄(`4578a` 교체)을 바꾸므로 병합 때 같은 줄 충돌이 난다(두 교체를 합치면 된다).
2. **표 `45b28`의 C++ 형태(U08 결정 2·U11 결정 4와 같음).** `45b28`은 PC=`45b2c`+sext(`D7.W`)로만 옮긴다(32bit 덧셈). 96 entry의 `BRA.W` 대상은 C++ 상수 배열로 옮겨 적고, 96 본문의 (`ORI.W` 마스크, `MOVE.W` 값) 쌍도 C++ 상수 배열로 옮겨 적는다(코드 바이트를 자료로 읽지 않음). 상한 밖 값은 routing이 정한다(아래 "점프 표"). 원본과의 의도된 차이: 계산 PC가 block 시작이 아닌 명령 시작이나 명령 중간 WORD이면 원본 CPU는 그 주소부터 실행하지만 C++는 `unsupported animation objects u15c PC`로 멈춘다(상한 밖 D7에서만 생김).
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_u15c.cpp`의 `animation_objects_u15c_block`. 내부 PC는 `unsupported animation objects u15c PC`. U15c에는 carry 소비자가 없으므로 `objects u15c caller requires known carry`는 실행 경로에서 나오지 않는다. U08a·U15b 권고와 같이 쓰는 곳이 없는 문자열은 넣지 않는다(권고).
4. **무효화 탐침 교체(아래 "회귀 탐침").** U08b test의 `45b12` 2곳(`BOUNDARIES`의 stop 행 rollback, `outside[]` rollback)과 `461ea`(U15c 본문 k=`5f`의 `RTS`, 이제 내부 PC) 1곳을 work RAM PC `10fe00..10fefe`(짝수; 코드가 실행되지 않으므로 계속 `unsupported animation machine PC`)로 바꾼다. `5f6xx..5ffxx`는 뒤 단위(U36/U37) 범위라 쓰지 않는다(메인 지시). 정확한 값은 test 주석에만 둔다.

## 원본 바이트 근거

[F] 코드 1 범위 1,754바이트.

| CPU 범위 | 바이트 | SHA256 | 내용 |
| --- | --- | --- | --- |
| `45b12..461ec` | 1754 | `ecf58e2c996c070817c0caac6aff763df7b2d437a282428382d00b6943fbc497` | 진입 `45b12` `45b1a` `45b22`, `JMP` `45b28`, 표 entry `45b2c..45cac`, 대상 `45cac..461ec` |
| `45b12..45b2c` | 26 | `5c0ff241a68b40f54559bb0d499326f8da50547fe2fe71f7758c44b5e8d319f6` | 진입 4 block (`0c470174 6700032e 0c470174 66000008 4a83 6e00066e 4efb7002`) |
| `45b2c..45cac` | 384 | `eb7303363c3e200d1aab6a443efa8c7f911bc2c62ce6752458f2c92c1f61e826` | 표 entry 96 |
| `45cac..461ec` | 1344 | `a50f4ca4abf2e313fdc0e55e2a76f631bea883c432759039870a3cc9b118d491` | 대상 본문 96 (각 14바이트 `006d mmmm 54aa 3b7c vvvv 54ac 4e75`) |

- [F] 범위 밖 이웃(routing 밖 또는 다른 실행부): `45b10`(U15b `45b06` 계열의 `RTS`, U15b 범위 `4578a..45b12` 끝), `461ec`(U08b `MOVE.W 461f2(PC,D7.W),D7` block, U08b routing).
- [F] 정적 참조: `45b12`는 `463b4` `464c6`(U08b, `BSR.W`)에서만, `45b1a`는 `46670` `46748`(U15a, `BSR.W`)에서만 불린다. `45b22` `45b28`과 표 entry로 가는 정적 분기·호출은 범위 밖에 없다(`refs.py`). `46198`은 `45b24 BGT.W`와 표 entry `45c94`(k=`5a`)가 같이 쓴다. [I] ROM의 LONG 상수 중 `45b12..461ec` 안 값(`46000` `46100` 등 70여 곳)은 정렬·위치로 보아 수치 자료이고 코드 포인터가 아니다(정적 분기 0건과 일치).

## 점프 표 `45b28`과 index 상한(결정 4)

- [F] `45b28`: `JMP 45b2c(PC,D7.W)`(PC 상대 기준 `45b2c`). 표 `45b2c..45cac`는 96개 `BRA.W`이고 바로 뒤 `45cac`가 첫 대상이다. index k(`D7.W`=4k) → 대상 `45cac+e·k`:
  - `00..0f`: `45cac` `45cba` `45cc8` `45cd6` `45ce4` `45cf2` `45d00` `45d0e` `45d1c` `45d2a` `45d38` `45d46` `45d54` `45d62` `45d70` `45d7e`
  - `10..1f`: `45d8c` `45d9a` `45da8` `45db6` `45dc4` `45dd2` `45de0` `45dee` `45dfc` `45e0a` `45e18` `45e26` `45e34` `45e42` `45e50` `45e5e`
  - `20..2f`: `45e6c` `45e7a` `45e88` `45e96` `45ea4` `45eb2` `45ec0` `45ece` `45edc` `45eea` `45ef8` `45f06` `45f14` `45f22` `45f30` `45f3e`
  - `30..3f`: `45f4c` `45f5a` `45f68` `45f76` `45f84` `45f92` `45fa0` `45fae` `45fbc` `45fca` `45fd8` `45fe6` `45ff4` `46002` `46010` `4601e`
  - `40..4f`: `4602c` `4603a` `46048` `46056` `46064` `46072` `46080` `4608e` `4609c` `460aa` `460b8` `460c6` `460d4` `460e2` `460f0` `460fe`
  - `50..5f`: `4610c` `4611a` `46128` `46136` `46144` `46152` `46160` `4616e` `4617c` `4618a` `46198` `461a6` `461b4` `461c2` `461d0` `461de`
- [F] 대상 본문 k의 (`ORI.W` 마스크 m / `MOVE.W` 값 v), `m/vvvv`:
  - `00..0f`: `2/4500` `2/3b00` `a/bb00` `a/c500` `2/4500` `2/3b00` `a/bb00` `a/c500` `2/4500` `2/3b00` `a/bb00` `a/c500` `2/4500` `2/3b00` `a/bb00` `a/c500`
  - `10..1f`: `2/4500` `2/3b00` `a/bb00` `a/c500` `2/4500` `2/3b00` `a/bb00` `a/c500` `2/4500` `2/3b00` `a/bb00` `a/c500` `2/4500` `2/3b00` `a/bb00` `a/c500`
  - `20..2f`: `6/8000` `6/0000` `6/8000` `6/0000` `2/7600` `2/0a00` `a/8a00` `a/f600` `2/7600` `2/0a00` `a/8a00` `a/f600` `2/7600` `2/0a00` `a/8a00` `a/f600`
  - `30..3f`: `2/7600` `2/0a00` `a/8a00` `a/f600` `2/6b00` `2/1500` `a/9500` `a/eb00` `2/6b00` `2/1500` `a/9500` `a/eb00` `2/6000` `2/2000` `a/a000` `a/e000`
  - `40..4f`: `2/5300` `2/2d00` `a/ad00` `a/d300` `2/5300` `2/2d00` `a/ad00` `a/d300` `2/4a00` `2/3600` `a/b600` `a/ca00` `2/4a00` `2/3600` `a/b600` `a/ca00`
  - `50..5f`: `2/4a00` `2/3600` `a/b600` `a/ca00` `2/4a00` `2/3600` `a/b600` `a/ca00` `2/4000` `2/4000` `a/c000` `2/4000` `2/4000` `2/4000` `2/4000` `2/4000`
- [F] 정적 호출자 4곳(모두 `BSR.W`): `463b4` `464c6`(U08b → `45b12`), `46670` `46748`(U15a → `45b1a`). 네 site 모두 바로 앞 block이 `BSR 4483a`(U08a, `46654` `4672e` 등) 뒤 `CMPI.W #160,D7; BEQ`(`463ac` `464be` `46668` `46740`)로 `160`을 건너뛴다. `4483a` 대상은 D7을 그대로 두거나 `449be`(`MOVE.W #160,D7`)로 간다. 그 D7은 `447be` 결과 또는 그것을 쓴 `54b0(A5)`, 곧 `4k`(k<`60`) 또는 `160`이다(U08 계약 "점프 표 `4483a`와 index 상한"). 따라서 `45b28`의 `D7.W`는 `4k`(k<`60`, `160` 제외)이고 모두 표 안 entry다. `174`(k=`5d`)는 `45b12`/`45b1a`의 특례 비교 뒤에도 표 안이다.
  - [U] `4483a` 앞 D7의 진입 경로 전 호출 closure(U08 계약 미확인 2와 같은 범위). 결정 2의 계산 PC 정책이 그 밖 값도 원본과 같이 옮기므로 실행 의미는 상한 확정에 의존하지 않는다.
- [F] 상한 밖 `D7.W`(계산 PC `45b2c+sext(D7.W)`, `3db2c..4db2a`): 홀수 → `unaligned animation machine PC`; 표 displacement WORD(`45b2e+4k`)·본문 내부(`45cac+e·k+2..+c`)·진입 내부(`45b14..45b26`의 비시작 PC) → `unsupported animation objects u15c PC`; `45b28`(`D7.W`=`fffc`) → 자기 자신(원본도 무한 반복, C++는 `animation machine block budget exceeded`); `45b1a`(`ffee`)·`45b22`(`fff6`, D3≤0)·`45b12`(`ffe6`)도 D7이 그대로라 같은 반복; `461ec`(`6c0`) → U08b block; 그 밖 → routing 밖이면 `unsupported animation machine PC`, 다른 실행부 범위면 그 실행부.

## block 목록과 실행 의미

[F] 196 block. 각 줄은 block 안 명령 전체다. `CMPI.W` 뒤 `BEQ`/`BNE`는 `D7.W` Z, `TST.L` 뒤 `BGT`는 부호 있는 LONG `D3 > 0`(TST는 V=0이므로 N=0이고 Z=0)이다. `ORI.W #m,54aa(A5)`는 WORD 읽기-OR-쓰기, `MOVE.W #v,54ac(A5)`는 WORD 쓰기다.

**진입 4**
- `45b12`: `CMPI.W #174,D7; BEQ.W 45e6c` (→`45b1a`; U08b `463b4`/`464c6 BSR`)
- `45b1a`: `CMPI.W #174,D7; BNE.W 45b28` (U15a `46670`/`46748 BSR`)
- `45b22`: `TST.L D3; BGT.W 46198` (→`45b28`)
- `45b28`: `JMP 45b2c(PC,D7.W)` (계산 PC, 결정 2)

**표 entry 96**
- `45b2c+4k`(k=`0..5f`): `BRA.W 45cac+e·k`

**대상 본문 96**
- `45cac+e·k`(k=`0..5f`): `ORI.W #m_k,54aa(A5); MOVE.W #v_k,54ac(A5); RTS` (m_k/v_k는 위 표)

(수: 진입 4, entry 96, 본문 96; 합 196.)

## 구현 범위와 규약

- routing 1 범위: `45b12..461ec`. 짝수 PC 877개 중 block 시작 196, 내부 681. 내부 PC 직접 진입은 `unsupported animation objects u15c PC`다. 범위 이웃은 routing 밖이거나 다른 실행부다.
- **FLOW_ONLY 97개**(C 보존): `45b28`(JMP), 표 entry 96(`BRA.W`). 그 밖 99개(`45b12` `45b1a` CMPI+Bcc, `45b22` TST+Bcc, 본문 96 ORI+MOVE+RTS)는 Unknown이다. [F] 원본은 `45b12`/`45b1a`/`45b22` 뒤 C=0, 본문 뒤 C=0(`MOVE.W`)이지만 소비자가 없으므로 관례대로 Unknown으로 둔다.
- 반환 Z·N(본문의 `MOVE.W #v` 결과)은 [F] 호출자 다음 명령(`BSR`)이 읽지 않는다. C++는 Unknown으로 둔다.
- 루프 없음. I/O port 쓰기 없음. bank 변경 없음. 홀수 A5(WORD 읽기·쓰기), work RAM 밖 쓰기, 장치 주소 쓰기, RTS 스택 장치 읽기는 기존 checked 오류다.
- C++ 구현: `45b12` `45b1a` `45b22` `45b28`은 개별 case, 표 entry 96과 본문 96은 상수 배열(대상, 마스크·값) 색인으로 처리한다(U11 표 entry와 같은 방식). `TST.L D3; BGT`는 비트 연산으로 판정한다(부호 있는 변환 없음).

## 의존·경계

- [F] U15c → 기존: 없음(RTS만).
- [F] 기존 → U15c: U08b `463b4`/`464c6 BSR 45b12`(U08b 계약의 경계 callee), U15a `46670`/`46748 BSR 45b1a`(U15 계약의 경계). 각 호출 뒤 다음 명령은 U15b `4578a`/`45afe`(이 작업 트리에서 routing 밖)이다.
- [I] 그래서 U15c 병합 뒤 C++ 프레임 패스는 `45b1a`/`45b12` 대신 `46674`/`4674c BSR 45afe`·`463b8`/`464ca BSR 4578a`(U15b)에서 멈춘다. U15b와 U15c가 모두 병합되어야 `4662e`/`46372` 경로가 지나간다(검증 기록에서 확인).

## 자연 시작 상태(읽기 전용 기록)

[F] 위 "요약"의 자연 도달. 196 block 중 TB 시작 기준 8개만 자연 도달한다. 미도달 188개(`45b12` `45b22`, 나머지 표 entry 93, 나머지 본문 93)는 typed fixture와 실제 ROM 차분으로 덮는다.

## 회귀 탐침(결정 4)

[F] `engine/tests`·`tools`·`engine/src`·`docs/analysis`에서 U15c 범위 `45b12..461ec` 안 PC를 쓰는 곳(stop PC로만 쓰는 곳은 그대로 둔다):
- `engine/tests/animation_machine_objects_u08b_test.cpp` `BOUNDARIES`의 `0x45b12`(그 PC에서 멈춘 fixture 행을 STOP으로 다시 실행해 rollback 확인; U15c가 실행하면 성립하지 않음) → 멈추지 않는 미사용 PC.
- 같은 파일 `interior()`의 `outside[]` rollback 탐침 `0x45b12`(이제 U15c block 시작)와 `0x461ea`(본문 `461de`의 `RTS`, 이제 내부 PC → `unsupported animation objects u15c PC`) → 미사용 PC 2개.
- U15a test(`animation_machine_objects_u15_test.cpp`)의 `45b1a`는 stop 확인뿐이라 유지된다. U08b test의 `45b12` stop fixture 행과 block 표 행(`463b4`/`464c6` → `45b12`)도 stop이라 유지된다.
- `tools`·`engine/src`의 언급(U15a 실행부 주석의 경계 표기)은 탐침이 아니다.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 196 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류(FLOW_ONLY 보존, 그 밖 Unknown), zero-step, 내부 681 PC 정확한 오류, 표 96 index × 3 carry가 옮겨 적은 대상에 닿음(`45b28`과 entry 직접 진입 둘 다), 본문 96 × `54aa` 입력(0, 전체 1)의 결과, 진입 `45b12`/`45b1a`/`45b22`의 술어 결과(`D7.W`=`174`/아님 × `D3` 양수/0/음수, `D7` 상위 WORD 무시), 표 상한 밖 D7(displacement WORD, 본문 내부, 진입 내부, 홀수, 범위 밖, 자기 자신, `461ec`), 홀수 PC. rollback 탐침은 work RAM PC `10fe00..10fefe`만 쓴다. 자연에 없는 길은 원본 코드로 만든 typed fixture(Unicorn, work RAM 입력)로 비교한다.
- 실제 ROM 차분: 진입 3곳 × 표 96 index 전체 × (`D3` 부호, `54aa` 입력)을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다.
- 차분(F2 프레임 패스, 142 seed, `MS5-SCHED-STATE-1`/`MS5-SCHED-PORTS-1`, seed 58·59는 `animation_machine_pvc_banks_native`): 기준(`1aa80c8`)의 일치 pass·node가 모두 그대로 일치해야 하고 불일치 0. RNG 초기화 400 frame 차분: 기준 유지, 불일치 0. 새 완주 seed는 U15b까지 필요하다([I], 위 "의존·경계").

## 미확인·범위 밖

1. [I] `45b12`/`45b1a` 표는 지형 코드(`447be`의 D7 index)별 표면 기울기를 `54ac(A5)` 상위 BYTE(256 단위 각도로 보임: `40`=수직 방향 기준의 평지, `45`/`3b`는 ±경사)와 `54aa(A5)` flag bit(1: 지면 접촉, 3: 반대 면/천장 쪽, 2: k=`20..23`의 특수 면)로 남기는 함수로 보인다. 게임 의미는 미확인이다.
2. [I] `D7.W`=`174`(빈 지형 코드의 다른 형태로 보임)는 `45b12`에서 k=`20` 본문(`6/8000`)으로, `45b1a`에서 `D3>0`이면 k=`5a` 본문(`a/c000`), 아니면 표 k=`5d`(`2/4000`)로 간다. 의미는 미확인이다.
3. [U] `4483a` 앞 D7의 진입 경로 전 호출 closure(표 상한의 나머지 근거, U08 계약과 같은 범위).
4. [U] U15b(`4578a` `45afe`)의 실행 결과와 두 단위 병합 뒤의 완주 seed.

작업자 scratch: 세션 scratchpad `f4u15c/`(`u15c.py` block·범위·SHA·표 계산, `body.py` `trav.py` `hroute_u15c.py` `u15dis.py`, `refs.py` `nextins.py` `reach.py`; 저장소 밖).
