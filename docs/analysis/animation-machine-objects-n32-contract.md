# 객체 callback F4 N32(N32a): 함수 `39cda` 본문 중 `39b72` 아래 — 상태 `38dd4` `38e20` `38ff4` `39076` `39156` `395dc`/`395f8` `3973c` `3976a` `39834` `398be` `3990c` `3995e`, 설치 callback 16개와 공유 꼬리 `3999a` 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N32 행(310 block, `38dd4..38e86` `38ff4..391e8` `395dc..39a1a` `39b72..39f9c` `3a34c..3a4a4`, 함수 `39cda` 하나, 경계 callee 21, 표 `39e76`:9 `39f4a`:9, 미실행 설치 28(+229), 옛 U44 310)과 표 아래 주석(권고 분할 N32a = `<39b72` 174 block, N32b = `≥39b72` 157 block, 표 2개는 N32b)이다. 단위 형식과 규약은 N30 계약(`animation-machine-objects-n30-contract.md`, SHA256 `dbbb15d8768f53f7cee0cbdedd4cdb5c189ed7cfd11db83ec7744475af894139`, N30a 분할 선례)과 N27 계약을 따른다. 메인 작업 지시:
- N32a만 구현한다. block 시작은 `MOVE.L #imm,(A6)` 설치 callback, DBRA 대상, JSR 복귀점을 포함한 정적 디코드로 정하고 재범위 수치와 다르면 보고한다. 자료 표는 routing하지 않는다.
- 함수 내부 주소 분할이므로 N32a에서 `≥39b72` 부분으로 나가는 곳은 stop 전용 경계다. 그 PC를 모두 적어 N32b가 block 시작으로 두게 한다(두 번째 진입 patch가 필요 없도록).
- 병행 N31 작업자(범위 `34750..34752` `38ba0..38d56` `3a2f4..3a4a4`; `3a2f4..3a4a4`와 N32/N33 겹침 귀속도 정함)와 겹치므로 `38ba0..38d56` `3a2f4..3a4a4` `34750`은 routing하지 않고 stop 전용 경계로 둔다.
- 범위 안 PC를 "routing 밖" 탐침으로 쓰는 기존 test는 RAM `10fe00..10fefe`로 옮긴다(해당 없음, 결정 9). 다른 단위 실행부의 두 번째 진입이 필요하면 고치지 않고 scratch patch와 결정으로 보고한다(해당 없음).

- 결정 관례(N30과 같음): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치, 범위 밖에서 참조하는 범위 안 진입)로 정한다. Unicorn TB 분할은 시작이 아니다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다.
- U01~N30 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMPI`/`CLR`/`ANDI`/`EOR`/`SUBQ`/`ADDI`/`SWAP` 등은 C를 바꾼다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`MOVEM`(메모리→레지스터)/`JSR`/`BRA`/Bcc/`BTST`/`BSET`/`BCLR`)만인 block과 callee C를 소비하는 Bcc block은 FLOW_ONLY다. 다른 단위 범위는 다시 routing하지 않는다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. N32 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n32`(HEAD `ea27f57` = N01~N28, N29a, N30a, N27 통합, `engine/src/animation_machine.cpp` SHA256 `d81f394d4bc36042315581087577ca85327142334da5c211580bb00eb5021cf5`, routing 규칙 87개, `engine/src/animation_machine_interpreter.cpp` SHA256 `97abb2e1de42cf322e35fa3a66eea3ab633170143ea79e0d525e5ad4e317882f`, `engine/src/animation_machine_objects_n30.cpp` SHA256 `aeed39270b8f25b4a62a08458d45249eea9260270b2dbaa2804bb6438142f115`)을 참조했다. 재범위 N32 행 5 범위의 짝수 PC는 모두 기존 routing에 없다. N32a routing 3 범위의 양끝 이웃 `38dd2` `38e86` `38ff2` `391e8` `395da` `39a1a`도 routing 밖이다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n32/n32.py`(정적 디코드, SHA256 `ff8e796d5ac9837069ed9f6754e55cc725e228328798763f82e7035f14f5d5f3`; 전체 closure `starts.txt` SHA256 `3b85e629e21c9e7e0de688a650a24487636e6aacb0210062fe7e82d27c29ca3b`, N32a `startsA.txt` SHA256 `7ee268c43525676ee9566eefa809aec83f4dd37bd8233dbb42b09d8a8f356197`)와 `cls32.py`(분류, SHA256 `e61542111333bb7aa22d849bb65851d5a268752f50ab1527316600c4ae7a2439`)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **N32 전체 정적 closure = 365 block**(재범위 행 5 범위에서 자료 `39ca6..39cb0`(BYTE 표, `39c74`가 읽음; N32b)을 뺀 코드 695 명령 전부 도달). 진입 15개(`39cda`, 범위 밖에서 들어오는 `38dd4` `38ff4` `39076` `39156` `395dc` `395f8` `3976a` `398be` `39b72` `39eb2` `3a34c` `3a350` `3a41c`, 정적 참조가 없는 `3995e`(결정 2))에서 분기·fall-through·JSR 복귀점·범위 안 설치·BRA.W 표 2개(`39e76` 9 slot, `39f4a` 9 slot; N32b)를 끝까지 따라갔다. DBRA·`JMP (An)`·TRAP은 없다.
- [F] **N32a = 203 block**(3 routing 범위, 코드 1,764바이트, 짝수 PC 882, 내부 679) = 전체 closure 중 `<39b72`. N32b = 162 block(`39b72..39f9c` `3a34c..3a4a4`, 표 2개 포함). 재범위 권고 174/157과의 차이는 결정 3.
- [F] 진입(모두 block 시작):
  - 상태 진입(분기 대상): `38dd4`(`391ae`; 범위 밖 `3921c` `39310` `39488` `3958e`), `38e20`(`38dda`), `38ff4`(`390d6` `391a6`; 범위 밖 `38f52` `39214` `39308` `39480` `39586`), `39076`(`3912c` `396ca`; N32b `39c34` `39d54`; 범위 밖 `38fb8` `39b40`), `39156`(`39042` `390bc` `39678`; N32b `39bde` `39cfe`; 범위 밖 `38f38` `39aea`), `395dc` `395f8`(N32a 4곳, N32b 4곳, 범위 밖 `38f62` `38f6a` `39b48` `39b50`), `3973c`(`395ea` `39606` `396e8` `39710`), `3976a`(`390de` `39680`; N32b `39be6` `39d06`; 범위 밖 `38f5a` `39af2`), `39834`(`3981e` `39904` `39956` `39992`), `398be`(BEQ 12곳, 위 목록), `3990c`(`3987e` `399e4`), `3999a`(`39830` `39908` `3995a` `39996`).
  - 범위 안 설치 callback(`MOVE.L #imm,(A6)`): `38dfc`(`38df6`), `38e20`(`38e16`), `38e4e`(`38e48`), `39028`(`39022`), `39090`(`3908a`), `3917a`(`39174`), `39654`(`3964e`), `39754`(`3974e`), `3979e`(`39798`), `397d2`(`397c8`), `397fa`(`397f4`), `39848`(`39842`), `398ca`(`398a4`), `398d0`(`3982a`), `398e0`(`398da`), `39932`(`3992c`), `3996e`(`39968`). `38e20`(`38e16`→`38e1c`), `397d2`(`397c8`→`397ce`), `398ca`(`398a4`→`398aa`), `398d0`(`3982a`→`39830`)은 설치 뒤 다른 곳으로 가고(`38e20` `398ca`는 분기 대상이기도 함), 나머지 13개는 설치 직후 fall-through로 이어진다.
  - JSR 복귀점과 조건분기 fall-through는 block 목록 그대로다.
- [F] **N32a에서 N32b로 나가는 stop 전용 경계 3개(N32b block 시작이어야 함)**: `39b72`(`39108` `396aa BNE.W`), `39db4`(`39030` `390aa` `39666` `397b0 BNE.W`), `39eb2`(`3918c BNE.W`). 셋 다 전체 closure의 block 시작이다. 그 밖 N32a 출구 `3a350`(`BRA.W` 10곳: `38e1c` `38e7a` `39072` `39152` `391e4` `39738` `39766` `397ce` `398ba` `39a16`)과 `3a34c`(`38e68 BRA.W`)는 N31/N32b 겹침 `3a2f4..3a4a4` 안이라 stop 전용이다(결정 4).
- [F] **N32b → N32a 진입**: `39076`(`39c34` `39d54`), `39156`(`39bde` `39cfe`), `395dc`(`39c3c` `39d5c`), `395f8`(`39c44` `39d64`), `3976a`(`39be6` `39d06`), `398be`(`39bb8` `39ce0`). 모두 이미 N32a block 시작이라 **N32b가 N32a 실행부의 두 번째 진입을 요구하지 않는다**(patch 없음).
- [F] **경계(실행부 없음, 현재 routing 밖) callee 11개**: `39a1a`(`39886` `399ec`), `3a4da`(`39124` `396c6` `39816` `398fc` `3994e` `3998a`; C 반환, 6 소비자), `3a5be`(6곳, A0 = LONG `82(A6)`), `3a5d2`(5곳), `3b288`(7곳), `3b2a0`(`39898` `399fe`), `3b2a6`(`397bc`), `3b302`(13곳, A0 = 애니메이션 목록), `3b334`(10곳; C 반환, 8 소비자), `3b424`(13곳; D0 반환), `4d4b4`(`38e62`). `3a5d2` `3b288` `3b2a0` `3b2a6` `3b302` `3b334`는 재범위 N33(`3a5d2..3a60a` `3b118..3b424`), 나머지(`39a1a` `3a4da` `3a5be` `3b424` `4d4b4`)는 재범위 어느 단위에도 없다. `unsupported animation machine PC`(stop이면 그 PC에서 멈춤, 아니면 rollback)다.
- [F] **다른 실행부로 가는 callee**: `3af8`(sound; `38e30` `38ff8` `3915a` `397d6` `39926`), `4ae4a`(N08; `390fc` `3969e`, A0 = `3b756`), `496c2`(U11; `3978c`).
- [F] **범위 밖 설치 값(실행 PC가 아님)**: `38bac`(N31, `38e68`), `38e86`(`39760`), `38e92`(`3906c` `3914c` `39722`), `39366`(`391de`), `39a76`(`398b4` `39a10`). `38e86` `38e92` `39366` `39a76`은 재범위 어느 단위에도 없는 설치 대상 코드다(결정 7).
- [F] **carry**(아래 "carry" 절): 소비 14 block(모두 FLOW), known 생산 0, FLOW_ONLY 134개(소비 14 포함), Unknown 69개. 134 + 69 = 203.
- [F] X·DIVx/MULx·TRAP·I/O port 쓰기·bank 변경·고정 ROM 자료 읽기·banked 읽기·PC 상대 계산 점프·레지스터 간접 제어 이동이 없다. N/Z 재계산이 없다(모든 비교와 그 Bcc가 한 block 안에 있다).
- [F] 스택: JSR 복귀 LONG, `MOVE.L D0,-(A7)`(LONG push; `390f6` `39698` `JSR 4ae4a` 앞, `39116` `396b8` `39808` `398ee` `39940` `3997c` `JSR 3a4da` 앞)과 `MOVEM.L (A7)+,D0`(LONG pop; `39102` `396a4` `39128` `396ca` `3981a` `39900` `39952` `3998e`). 같은 함수 안 짝이다(결정 6).
- [F] 자연 도달(재범위 scratch 재생 `rescope/dyn_rng`·`dyn_base`, TB 시작 기준; scratch `seen32.py`): RNG·base 두 기록 모두 **N32a 범위 PC는 한 번도 실행되지 않는다**. `38ba0..3b600` 안에서 실행되는 것은 seed 116 117의 N31 `38ba0..38d54`, `3a34c..3a4a2`(N31 `38c8a BRA 3a34c`), N33 `3a5d2` `3b118..3b5a4`뿐이다.
- [F] 기준(`ea27f57`)에서 seed 116 117은 frame 0 `38ba0`(N31)에서 먼저 멈춘다. [I] N32a만으로는 새 완주 seed가 없다(브리프 예상과 같음).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **분할: N32a 203 block 구현, N32b 162 block 미룸.** [F] 재범위 N32 5 범위의 정적 closure는 365 block이라 ~230을 넘는다. 재범위 권고대로 주소 `39b72`에서 나눈다: N32a = `38dd4..38e86` `38ff4..391e8` `395dc..39a1a`(203), N32b = `39b72..39f9c` `3a34c..3a4a4`(162, BRA.W 표 `39e76` `39f4a`와 BYTE 표 `39ca6` 포함).
   - N32a → N32b 출구 3개 `39b72` `39db4` `39eb2`는 stop 전용 경계다. N32b는 이 셋을 block 시작으로 둬야 한다(전체 closure에서 이미 시작).
   - N32b → N32a 진입 6개(`39076` `39156` `395dc` `395f8` `3976a` `398be`)는 이미 N32a 시작이다. 두 번째 진입 patch는 필요 없다.
   - N32b의 경계 callee(전체 closure 기준, N32a와 겹치는 것 포함): `39f9c`(`39e7e` `39e82` slot, `39ea8` 설치) `3a242`(`39f94`) `3a4a4`(`3a380`, N31 겹침) `3a4be` `3a4da` `3a5be` `3a5d2` `3b282` `3b288` `3b2b8` `3b2ee` `3b302` `3b334` `3b424` `4d734` `4d9ba` `d0fec`; 다른 실행부 `1ab02` `28ae` `3af8` `3c44` `4970a` `4ae4a` `4b54e` `4d766` `4d7a6`. 재범위 bound 21개(`39a1a` `39f9c` `3a242` `3a4a4` `3a4be` `3a4da` `3a5be` `3a5d2` `3b282` `3b288` `3b2a0` `3b2a6` `3b2b8` `3b2ee` `3b302` `3b334` `3b424` `4d4b4` `4d734` `4d9ba` `d0fec`)와 정확히 같다(scratch `n32.py` "calls out").
   - 대안: 없음(재범위 권고와 같은 주소 분할; N32a 203은 상한 ~230 안).
2. **정적 참조가 없는 `3995e..3999a`(7 block)를 N32a에 넣음.** [F] `3995e MOVEA.L #3b948,A0; JSR 3b302(PC)`부터 `39996 BRA.W 3999a`까지(`3995e` `39968` `3996e` `39972` `3997c` `3998e` `39996`)는 ROM 전체(고정 `<100000`) 어느 분기·`JSR`/`LEA`/`PEA d16(PC)`·짝수 LONG도 `3995e`를 가리키지 않는다(scratch `xref32.py`). 앞 명령 `3995a BRA.W 3999a`라 fall-through도 없다. 안의 설치 값 `3996e`는 `39968`에서만 쓰인다. 재범위 leader에도 없다(재범위 N32a 174에 빠짐).
   - **권고(구현함)**: 재범위 범위 `395dc..39a1a`를 구멍 없이 routing하려고 `3995e`를 진입으로 두고 7 block을 N32a에 넣는다. [I] 다른 상태(`39834` 계열 `3b978`, `398d0` 계열 `3b92a`)와 같은 꼴의 미사용 상태(애니메이션 `3b948`)다.
   - 대안: `3995e..3999a`를 routing에서 빼고(N32a 196 block, 범위 `395dc..3995e` `3999a..39a1a`) 고아 정리 단계로 넘긴다.
3. **재범위 수치와 다른 점.** [F] 재범위 N32 행은 331 block(신규 310; leader는 scratch `rescope/build.pkl` `BODY[39cda]`)이고 N32a 174 / N32b 157이다. 이 계약은 N32a 203 / N32b 162다.
   - 재범위에만 있는 시작: 없다.
   - 이 계약에만 있는 N32a 시작 29개: 범위 안 설치 값 `38dfc` `38e4e` `39028` `39090` `3917a` `39654` `39754` `3979e` `397d2` `397fa` `39848` `398d0` `398e0` `39932`(재범위는 설치 직후 fall-through를 시작으로 나누지 않았다), 설치 `397d2`에서만 닿는 사슬 `397dc` `397e6` `397fe` `39808` `3981a` `39822` `3982a` `39830`, 결정 2의 `3995e` `39968` `3996e` `39972` `3997c` `3998e` `39996`. N32b에만 있는 시작 5개: `39bb2` `39cb0` `39cba` `39e24` `39ef4`(설치 값과 그 JSR 복귀점).
   - **표·경계 callee**: 표 `39e76`:9 `39f4a`:9와 경계 21개는 재범위와 같다(결정 1). N32a만은 경계 callee 11개 + N32b 출구 3개 + `3a34c` `3a350`이다.
   - **미실행 설치 28(+229)**: 이 계약에서 따로 세지 않았다([U]). N32a의 범위 밖 설치 값은 5개다(결정 7).
   - **새 완주 seed**: 재범위·브리프와 같이 없다(아래 검증 기록).
4. **`3a34c..3a4a4` 겹침: stop 전용.** [F] 재범위는 `3a34c..3a4a4`를 N32 범위에 넣었고 N31 범위 `3a2f4..3a4a4`와 겹친다(`3a41c..3a4a4`는 N33 범위와도 겹친다). N32a의 모든 상태 끝은 `BRA.W 3a350`(10곳) 또는 `BRA.W 3a34c`(`38e68`)다. 지시대로 routing하지 않고 stop 전용 경계로 둔다. 겹침의 귀속은 N31 작업자의 결정이다. 어느 쪽이 routing해도 N32a 실행부·test는 바뀌지 않는다(stop은 routing 전에 판정; test는 이 PC를 rollback 기대에 쓰지 않는다).
5. **경계 callee C 소비 14 block.** [F] `38e12` `38e56` `39056` `39148` `391c8` `3975c` `397c4` `398a0`(`BCC.W`)는 `JSR 3b334`의 C를, `39128` `396ca` `3981a` `39900` `39952` `3998e`(`MOVEM.L (A7)+,D0; BCS.W`)는 `JSR 3a4da`의 C를 읽는다. 두 callee 모두 실행부가 없으므로 N32a 안에서는 typed fixture(진입 C 선언)로만 실행하고, Unknown C면 `objects n32 caller requires known carry`다. [U] `3b334`(N33)·`3a4da`(미배정)의 C 생산은 그 단위가 정한다(N30 결정 6과 같음).
6. **`MOVEM.L (A7)+,D0`과 C·Z 통과.** [F] 68000 `MOVEM`(메모리→레지스터)은 CCR을 바꾸지 않는다. 따라서 `39128` 등 6 block은 `3a4da`의 C를 `BCS`가 그대로 읽는 FLOW 소비자이고, `39102` `396a4`(`TST.W D0; MOVEM.L (A7)+,D0; BNE.W 39b72`)는 `4ae4a`가 돌려준 `D0.W`의 Z를 pop 뒤에 읽는다(같은 block 안 계산, Unknown). 실행부는 원본 순서대로 pop(A7 += 4, `D0` = LONG) 뒤 C 검사를 한다(pop 실패가 먼저 checked 오류). `MOVEM`이 끝 주소 뒤 WORD를 한 번 더 읽는 68000 특성은 work RAM 스택이라 관찰 차이가 없고 모델하지 않는다([I]).
7. **범위 밖 설치 값.** [F] `38bac`(N31 범위 `38ba0..38d56`의 callback; `38e68`), `38e86`(`39760`), `38e92`(`3906c` `3914c` `39722`), `39366`(`391de`), `39a76`(`398b4` `39a10`)는 노드 LONG에 쓰는 자료다. `38e86..38ff4` `391e8..395dc` `39a1a..39b72`(설치 대상 코드와 helper `39a1a`)는 재범위 어느 단위에도 없다(N30 결정 7과 같은 꼴). routing하지 않는다. [I] 고아 정리 단계 몫이다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n32.cpp`의 `animation_objects_n32_block`. 오류는 `unsupported animation objects n32 PC`(내부 PC), `objects n32 caller requires known carry`(소비 14 block). N30a와 같은 꼴이다. N32b는 [I] 같은 파일에 case를 더하거나 별도 파일(`n32b`)로 둘 수 있다(메인 결정).
9. **무효화 탐침 없음(탐침 이동 없음).** [F] `engine/tests`·`engine/src`·`tools/*.py`의 16진 토큰(`0x` 접두 또는 맨 5~6자리) 중 N32a 3 범위의 값은 `animation_machine_motion_walk_test.cpp` 287행 레지스터 값 `0x3981c`, `animation_machine_objects_n04_test.cpp` 85행 `0x38e58`·167행 `0x39618`(레지스터 값)뿐이다. "routing 밖" 탐침이나 rollback 기대로 쓰는 곳은 없다.
10. **`2986` caller-X 제한 해당 없음.** [F] N32a는 `2986`을 부르지 않는다.

## 원본 바이트 근거

[F] N32a 코드 3 범위 합계 1,764바이트(짝수 PC 882개, 시작 203, 내부 679). 범위 순서로 이어 붙인 SHA256 `fd0266adac756e9f9e8c9aa4c98df620c2cd56787a3ab20bcbc0b3ca44a65077`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `38dd4..38e86` | 178 | `2ecb43fb579a521e4d274e9d9f36b5afea92a620fb7614ae31f2431de1d60ebc` | 20 |
| `38ff4..391e8` | 500 | `a7fb31c13d18ec1ecdb387df903d8a2fa870209f4b1883bf4e00ed19bca6de9b` | 58 |
| `395dc..39a1a` | 1086 | `80c32a5c4de913ffb44e40fbf10905470fd84399dbd43645c8b459e81da6f42c` | 125 |

- [F] 범위 이웃: `38dd4` 앞 `38d56..38dd4`(N31 범위 `38ba0..38d56` 뒤, 설치 대상 코드 `38d56` `38d80` `38db6`; 재범위 어느 단위에도 없음), `38e86..38ff4`(설치 대상 코드 `38e86` `38e92` `38eb4` `38ece` `38ee2` `38f08`; 결정 7), `391e8..395dc`(설치 대상 코드 `39292` `392b0` `39366` `39380` `39454` `3951e` `3955a`; 결정 7), `39a1a..39b72`(경계 helper `39a1a..39a76`, 설치 대상 코드 `39a76` `39ab6`; 결정 7), `39b72..`(N32b, 결정 1).
- [F] 우연 일치(실행 진입 아님): 고정 ROM의 LONG `00039000`(`2488a` 등 14곳)·`00039800`(`24882` 등 14곳)·`0003916e`(`215ca`)·`00038e38`(`424d4` 등 4곳)은 명령 중간(`38ffe` `397fe` `3916a` `38e36`의 확장어)이고, `38e07` `38e1f` `38e57`을 가리키는 `389c4` `389dc` `38a14`의 WORD는 홀수 대상이다([I] 좌표·수치 상수).

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "C 소비"(Unknown이면 checked 오류), "FLOW"(C 보존). 태그 없는 block은 Unknown이다. d16(An)은 부호 확장한다. `.B`/`.W` 연산은 나머지 bit를 보존한다. 비교·`TST`·`BTST`와 그 Bcc는 같은 block 안에 있다.

**`38dd4`(`391ae BNE`, 범위 밖 `3921c` `39310` `39488` `3958e BNE`; BYTE `9f` ≥ `11`이면 `38e20`, 애니메이션 `3b8d6`(`3b302`), `3a5d2`, 설치 callback `38dfc`(fall-through): BYTE `94` bit 3, `3a5be`(LONG `82`), `3b288`, `3b334` C → 설치 `38e20`, 끝 `BRA 3a350`) 10**
- `38dd4`: `CMPI.B #11, 9f(a6); BCC.W 38e20` (→`38dde`)
- `38dde`: `MOVEA.L #3b8d6, a0; JSR 3b302(pc)` — FLOW
- `38de8`: `JSR 3a5d2(pc)` — FLOW
- `38dec`: `MOVE.B #4, 95(a6); CLR.L 64(a6); MOVE.L #38dfc, (a6)` (→`38dfc`)
- `38dfc`: `BSET.B #3, 94(a6); MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `38e0a`: `JSR 3b288(pc)` — FLOW
- `38e0e`: `JSR 3b334(pc)` — FLOW
- `38e12`: `BCC.W 38e1c` (→`38e16`) — C 소비, FLOW
- `38e16`: `MOVE.L #38e20, (a6)` (→`38e1c`)
- `38e1c`: `BRA.W 3a350` — FLOW

**`38e20`(`38dda BCC`, 설치 값; WORD `8a` = 0, BYTE `9f` = `11`, 소리 `1a62`, 애니메이션 `3b8ac`, `3a5d2`, 설치 callback `38e4e`(fall-through): `3b288`, `3b334` C → `4d4b4` + 설치 `38bac`(N31 값) + `BRA 3a34c` / `BRA 3a350`) 10**
- `38e20`: `MOVE.W #0, 8a(a6); MOVE.B #11, 9f(a6); MOVE.W #1a62, d0; JSR 3af8.l`
- `38e36`: `MOVEA.L #3b8ac, a0; JSR 3b302(pc)` — FLOW
- `38e40`: `JSR 3a5d2(pc)` — FLOW
- `38e44`: `CLR.L 64(a6); MOVE.L #38e4e, (a6)` (→`38e4e`)
- `38e4e`: `JSR 3b288(pc)` — FLOW
- `38e52`: `JSR 3b334(pc)` — FLOW
- `38e56`: `BCC.W 38e7a` (→`38e5a`) — C 소비, FLOW
- `38e5a`: `MOVE.W 86(a6), d0; MOVE.B #1, d1; JSR 4d4b4.l`
- `38e68`: `MOVE.L #38bac, (a6); MOVE.L #0, 56(a6); BRA.W 3a34c`
- `38e7a`: `MOVE.L #0, 56(a6); BRA.W 3a350`

**`38ff4`(`390d6` `391a6 BNE`, 범위 밖 `38f52` `39214` `39308` `39480` `39586`; 소리 `1a62`, BYTE `9f` 상한 `11`, 애니메이션 `3b8d0`, 설치 callback `39028`(fall-through): `3b424` 입력 bit, `3a5be` `3b288`, `3b334` C → 설치 `38e92`(범위 밖 값), 끝 `BRA 3a350`) 15**
- `38ff4`: `MOVE.W #1a62, d0; JSR 3af8.l`
- `38ffe`: `CMPI.B #11, 9f(a6); BLS.W 3900e` (→`39008`)
- `39008`: `MOVE.B #11, 9f(a6)` (→`3900e`)
- `3900e`: `MOVEA.L #3b8d0, a0; JSR 3b302(pc)` — FLOW
- `39018`: `MOVE.B #2, 95(a6); CLR.L 64(a6); MOVE.L #39028, (a6)` (→`39028`)
- `39028`: `JSR 3b424(pc)` — FLOW
- `3902c`: `BTST.B #7, d0; BNE.W 39db4` (→`39034`) — FLOW
- `39034`: `BTST.B #1, d0; BEQ.W 39046` (→`3903c`) — FLOW
- `3903c`: `BTST.B #7, 15(a6); BNE.W 39156` (→`39046`) — FLOW
- `39046`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `3904e`: `JSR 3b288(pc)` — FLOW
- `39052`: `JSR 3b334(pc)` — FLOW
- `39056`: `BCC.W 39072` (→`3905a`) — C 소비, FLOW
- `3905a`: `ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); MOVE.B #0, 9f(a6); MOVE.L #38e92, (a6)` (→`39072`)
- `39072`: `BRA.W 3a350` — FLOW

**`39076`(`3912c` `396ca BCS`, N32b `39c34` `39d54`, 범위 밖 `38fb8` `39b40`; BYTE `98` = `ff`, 애니메이션 `3b972`, `3a5d2`, 설치 callback `39090`(fall-through): 입력 `3b424` bit 7/1/5/2/3, `4ae4a`(`3b756`) → N32b `39b72`, `3a4da` C, `3b288` `3b334` C → 설치 `38e92`, 끝 `BRA 3a350`) 27**
- `39076`: `MOVE.B #ff, 98(a6); MOVEA.L #3b972, a0; JSR 3b302(pc)`
- `39086`: `JSR 3a5d2(pc)` — FLOW
- `3908a`: `MOVE.L #39090, (a6)` (→`39090`)
- `39090`: `BTST.B #7, 15(a6); BEQ.W 398be` (→`3909a`) — FLOW
- `3909a`: `TST.B 98(a6); BNE.W 39140` (→`390a2`)
- `390a2`: `JSR 3b424(pc)` — FLOW
- `390a6`: `BTST.B #7, d0; BNE.W 39db4` (→`390ae`) — FLOW
- `390ae`: `BTST.B #1, d0; BEQ.W 390c0` (→`390b6`) — FLOW
- `390b6`: `BTST.B #7, 15(a6); BNE.W 39156` (→`390c0`) — FLOW
- `390c0`: `BTST.B #1, d0; BNE.W 390da` (→`390c8`) — FLOW
- `390c8`: `TST.B 9f(a6); BEQ.W 390da` (→`390d0`)
- `390d0`: `BTST.B #7, 15(a6); BNE.W 38ff4` (→`390da`) — FLOW
- `390da`: `BTST.B #5, d0; BNE.W 3976a` (→`390e2`) — FLOW
- `390e2`: `BTST.B #2, 94(a6); BNE.W 3910c` (→`390ec`) — FLOW
- `390ec`: `BTST.B #4, 9d(a6); BEQ.W 3910c` (→`390f6`) — FLOW
- `390f6`: `MOVE.L d0, -(a7); LEA.L 3b756(pc), a0; JSR 4ae4a.l`
- `39102`: `TST.W d0; MOVEM.L (a7)+, d0; BNE.W 39b72` (→`3910c`)
- `3910c`: `BTST.B #6, 9d(a6); BEQ.W 39130` (→`39116`) — FLOW
- `39116`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `39128`: `MOVEM.L (a7)+, d0; BCS.W 39076` (→`39130`) — C 소비, FLOW
- `39130`: `BTST.B #2, d0; BNE.W 395dc` (→`39138`) — FLOW
- `39138`: `BTST.B #3, d0; BNE.W 395f8` (→`39140`) — FLOW
- `39140`: `JSR 3b288(pc)` — FLOW
- `39144`: `JSR 3b334(pc)` — FLOW
- `39148`: `BCC.W 39152` (→`3914c`) — C 소비, FLOW
- `3914c`: `MOVE.L #38e92, (a6)` (→`39152`)
- `39152`: `BRA.W 3a350` — FLOW

**`39156`(`3903c` `390b6` `39672 BNE`, N32b `39bde` `39cfe`, 범위 밖 `38f38` `39aea`; 소리 `1a5f`, 애니메이션 `3b8d6`, 설치 callback `3917a`(fall-through): 입력 `3b424` → N32b `39eb2` / `38ff4` / `38dd4`, BYTE `94` bit 3, `3a5be` `3b288`, `3b334` C → 설치 `39366`(범위 밖 값), 끝 `BRA 3a350`) 16**
- `39156`: `MOVE.W #1a5f, d0; JSR 3af8.l`
- `39160`: `MOVEA.L #3b8d6, a0; JSR 3b302(pc)` — FLOW
- `3916a`: `MOVE.B #2, 95(a6); CLR.L 64(a6); MOVE.L #3917a, (a6)` (→`3917a`)
- `3917a`: `BTST.B #7, 15(a6); BEQ.W 398be` (→`39184`) — FLOW
- `39184`: `JSR 3b424(pc)` — FLOW
- `39188`: `BTST.B #7, d0; BNE.W 39eb2` (→`39190`) — FLOW
- `39190`: `BTST.B #1, d0; BNE.W 391aa` (→`39198`) — FLOW
- `39198`: `TST.B 9f(a6); BEQ.W 391aa` (→`391a0`)
- `391a0`: `BTST.B #7, 15(a6); BNE.W 38ff4` (→`391aa`) — FLOW
- `391aa`: `BTST.B #5, d0; BNE.W 38dd4` (→`391b2`) — FLOW
- `391b2`: `BSET.B #3, 94(a6); MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `391c0`: `JSR 3b288(pc)` — FLOW
- `391c4`: `JSR 3b334(pc)` — FLOW
- `391c8`: `BCC.W 391e4` (→`391cc`) — C 소비, FLOW
- `391cc`: `ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); MOVE.B #11, 9f(a6); MOVE.L #39366, (a6)` (→`391e4`)
- `391e4`: `BRA.W 3a350` — FLOW

**`395dc` / `395f8`(`39134` `3913c` `396f2` `3971a`, N32b `39c3c` `39c44` `39d5c` `39d64`, 범위 밖 `38f62` `38f6a` `39b48` `39b50`; BYTE `94` bit 5 방향, 애니메이션 `3b912`/`3b918`, WORD `2c` = `aa`, 설치 callback `39654`(fall-through): 입력 `3b424`, `4ae4a`, `3a4da` C, 설치 `38e92`, `3a5be` `3b288` `3b334`, 끝 `BRA 3a350`) 39**
- `395dc`: `BTST.B #0, 15(a6); BNE.W 395ee` (→`395e6`) — FLOW
- `395e6`: `TST.B a3(a6); BEQ.W 3973c` (→`395ee`)
- `395ee`: `BSET.B #5, 94(a6); BRA.W 39610` — FLOW
- `395f8`: `BTST.B #0, 15(a6); BEQ.W 3960a` (→`39602`) — FLOW
- `39602`: `TST.B a3(a6); BEQ.W 3973c` (→`3960a`)
- `3960a`: `BCLR.B #5, 94(a6)` (→`39610`) — FLOW
- `39610`: `BTST.B #5, 94(a6); SNE.B d0; BTST.B #0, 15(a6); SNE.B d1; EOR.B d1, d0; BNE.W 39634` (→`39626`)
- `39626`: `MOVEA.L #3b912, a0; JSR 3b302(pc)` — FLOW
- `39630`: `BRA.W 3963e` — FLOW
- `39634`: `MOVEA.L #3b918, a0; JSR 3b302(pc)` — FLOW
- `3963e`: `MOVE.W #aa, 2c(a6); MOVE.B #1, 95(a6); CLR.L 64(a6); MOVE.L #39654, (a6)` (→`39654`)
- `39654`: `BTST.B #7, 15(a6); BEQ.W 398be` (→`3965e`) — FLOW
- `3965e`: `JSR 3b424(pc)` — FLOW
- `39662`: `BTST.B #7, d0; BNE.W 39db4` (→`3966a`) — FLOW
- `3966a`: `BTST.B #1, d0; BEQ.W 3967c` (→`39672`) — FLOW
- `39672`: `BTST.B #7, 15(a6); BNE.W 39156` (→`3967c`) — FLOW
- `3967c`: `BTST.B #5, d0; BNE.W 3976a` (→`39684`) — FLOW
- `39684`: `BTST.B #2, 94(a6); BNE.W 396ae` (→`3968e`) — FLOW
- `3968e`: `BTST.B #4, 9d(a6); BEQ.W 396ae` (→`39698`) — FLOW
- `39698`: `MOVE.L d0, -(a7); LEA.L 3b756(pc), a0; JSR 4ae4a.l`
- `396a4`: `TST.W d0; MOVEM.L (a7)+, d0; BNE.W 39b72` (→`396ae`)
- `396ae`: `BTST.B #6, 9d(a6); BEQ.W 396d2` (→`396b8`) — FLOW
- `396b8`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `396ca`: `MOVEM.L (a7)+, d0; BCS.W 39076` (→`396d2`) — C 소비, FLOW
- `396d2`: `BTST.B #3, d0; BEQ.W 396fa` (→`396da`) — FLOW
- `396da`: `BTST.B #0, 15(a6); BEQ.W 396ec` (→`396e4`) — FLOW
- `396e4`: `TST.B a3(a6); BEQ.W 3973c` (→`396ec`)
- `396ec`: `BTST.B #5, 94(a6); BNE.W 395f8` (→`396f6`) — FLOW
- `396f6`: `BRA.W 39728` — FLOW
- `396fa`: `BTST.B #2, d0; BEQ.W 39722` (→`39702`) — FLOW
- `39702`: `BTST.B #0, 15(a6); BNE.W 39714` (→`3970c`) — FLOW
- `3970c`: `TST.B a3(a6); BEQ.W 3973c` (→`39714`)
- `39714`: `BTST.B #5, 94(a6); BEQ.W 395dc` (→`3971e`) — FLOW
- `3971e`: `BRA.W 39728` — FLOW
- `39722`: `MOVE.L #38e92, (a6)` (→`39728`)
- `39728`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `39730`: `JSR 3b288(pc)` — FLOW
- `39734`: `JSR 3b334(pc)` — FLOW
- `39738`: `BRA.W 3a350` — FLOW

**`3973c`(`395ea` `39606` `396e8` `39710 BEQ`; 애니메이션 `3b95a`, `3a5d2`, 설치 callback `39754`(fall-through): `3b288`, `3b334` C → 설치 `38e86`(범위 밖 값), 끝 `BRA 3a350`) 8**
- `3973c`: `MOVEA.L #3b95a, a0; JSR 3b302(pc)` — FLOW
- `39746`: `JSR 3a5d2(pc)` — FLOW
- `3974a`: `CLR.L 64(a6); MOVE.L #39754, (a6)` (→`39754`)
- `39754`: `JSR 3b288(pc)` — FLOW
- `39758`: `JSR 3b334(pc)` — FLOW
- `3975c`: `BCC.W 39766` (→`39760`) — C 소비, FLOW
- `39760`: `MOVE.L #38e86, (a6)` (→`39766`)
- `39766`: `BRA.W 3a350` — FLOW

**`3976a`(`390de` `39680 BNE`, N32b `39be6` `39d06`, 범위 밖 `38f5a` `39af2`; 애니메이션 `3b91e`, BYTE `95` = 3, `9a` = 0, `9d`/`9e` bit 4 지움, `496c2`, 설치 callback `3979e`(fall-through): 입력 bit 7 → N32b `39db4`, `3a5be` `3b2a6`, `3b334` C → 설치 `397d2`, 끝 `BRA 3a350`) 12**
- `3976a`: `MOVEA.L #3b91e, a0; JSR 3b302(pc)` — FLOW
- `39774`: `MOVE.B #3, 95(a6); MOVE.B #0, 9a(a6); ANDI.B #ef, 9d(a6); ANDI.B #ef, 9e(a6); JSR 496c2.l`
- `39792`: `MOVE.B #0, 9f(a6); MOVE.L #3979e, (a6)` (→`3979e`)
- `3979e`: `BTST.B #7, 15(a6); BEQ.W 398be` (→`397a8`) — FLOW
- `397a8`: `JSR 3b424(pc)` — FLOW
- `397ac`: `BTST.B #7, d0; BNE.W 39db4` (→`397b4`) — FLOW
- `397b4`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `397bc`: `JSR 3b2a6(pc)` — FLOW
- `397c0`: `JSR 3b334(pc)` — FLOW
- `397c4`: `BCC.W 397ce` (→`397c8`) — C 소비, FLOW
- `397c8`: `MOVE.L #397d2, (a6)` (→`397ce`)
- `397ce`: `BRA.W 3a350` — FLOW

**설치 callback `397d2`(`397c8`; 소리 `1a61`, 애니메이션 `3b924`, LONG `3a` = `8fc4e`, 설치 callback `397fa`(fall-through): `3b424`, `3a4da` C → `39834`, WORD `3a` 부호 → 설치 `398d0`, 끝 `BRA 3999a`) 10**
- `397d2`: `MOVE.W #1a61, d0; JSR 3af8.l`
- `397dc`: `MOVEA.L #3b924, a0; JSR 3b302(pc)` — FLOW
- `397e6`: `MOVE.B #0, 95(a6); MOVE.L #8fc4e, 3a(a6); MOVE.L #397fa, (a6)` (→`397fa`)
- `397fa`: `JSR 3b424(pc)` — FLOW
- `397fe`: `BTST.B #6, 9d(a6); BEQ.W 39822` (→`39808`) — FLOW
- `39808`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `3981a`: `MOVEM.L (a7)+, d0; BCS.W 39834` (→`39822`) — C 소비, FLOW
- `39822`: `TST.W 3a(a6); BPL.W 39830` (→`3982a`)
- `3982a`: `MOVE.L #398d0, (a6)` (→`39830`)
- `39830`: `BRA.W 3999a` — FLOW

**`39834`(`3981a` `39900` `39952` `3998e BCS`; `3a5d2`, 애니메이션 `3b978`, 설치 callback `39848`(fall-through): 입력 `3b424` 상위 WORD bit 5, BYTE `a4`/`9d`/`9e`, BYTE `9c` → `3990c`, `3b424` `39a1a`, LONG `3a` −= `a000`, `3b2a0`, `3b334` C → 설치 `398ca`, BYTE `15` bit 7 → 설치 `39a76`(범위 밖 값), 끝 `BRA 3a350`) 18**
- `39834`: `JSR 3a5d2(pc)` — FLOW
- `39838`: `MOVEA.L #3b978, a0; JSR 3b302(pc)` — FLOW
- `39842`: `MOVE.L #39848, (a6)` (→`39848`)
- `39848`: `JSR 3b424(pc)` — FLOW
- `3984c`: `MOVE.L d0, d1; SWAP d1; BTST.B #5, d1; BNE.W 39868` (→`39858`)
- `39858`: `CLR.B a4(a6); ANDI.B #df, 9d(a6); ANDI.B #df, 9e(a6)` (→`39868`)
- `39868`: `BTST.B #5, 9d(a6); BEQ.W 39882` (→`39872`) — FLOW
- `39872`: `TST.W 3a(a6); BGT.W 39882` (→`3987a`)
- `3987a`: `TST.B 9c(a6); BNE.W 3990c` (→`39882`)
- `39882`: `JSR 3b424(pc)` — FLOW
- `39886`: `JSR 39a1a(pc)` — FLOW
- `3988a`: `MOVE.L 3a(a6), d7; ADDI.L #ffff6000, d7; MOVE.L d7, 3a(a6); JSR 3b2a0(pc)`
- `3989c`: `JSR 3b334(pc)` — FLOW
- `398a0`: `BCC.W 398aa` (→`398a4`) — C 소비, FLOW
- `398a4`: `MOVE.L #398ca, (a6)` (→`398aa`)
- `398aa`: `BTST.B #7, 15(a6); BEQ.W 398ba` (→`398b4`) — FLOW
- `398b4`: `MOVE.L #39a76, (a6)` (→`398ba`)
- `398ba`: `BRA.W 3a350` — FLOW

**`398be`(BYTE `15` bit 7 = 0인 `BEQ`: N32a `39096` `39180` `3965a` `397a4`·N32b `39bb8` `39ce0`·범위 밖 `38f1a` `391ee` `392b6` `3945a` `39560` `39abc`) / `398ca`(설치 값, `399aa BEQ`) / 설치 callback `398d0`(`3982a`) / 설치 callback `398e0` / `3990c`(`3987e` `399e4 BNE`; BYTE `9c` −1, BYTE `a4` = `a`, 소리 `1aa7`, 설치 callback `39932`), 끝 `BRA 3999a`) 16**
- `398be`: `ANDI.B #df, 9d(a6); ANDI.B #df, 9e(a6)` (→`398ca`)
- `398ca`: `MOVE.B #0, 95(a6)` (→`398d0`)
- `398d0`: `MOVEA.L #3b92a, a0; JSR 3b302(pc)` — FLOW
- `398da`: `MOVE.L #398e0, (a6)` (→`398e0`)
- `398e0`: `JSR 3b424(pc)` — FLOW
- `398e4`: `BTST.B #6, 9d(a6); BEQ.W 39908` (→`398ee`) — FLOW
- `398ee`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `39900`: `MOVEM.L (a7)+, d0; BCS.W 39834` (→`39908`) — C 소비, FLOW
- `39908`: `BRA.W 3999a` — FLOW
- `3990c`: `ANDI.B #df, 9d(a6); ANDI.B #df, 9e(a6); SUBQ.B #1, 9c(a6); MOVE.B #a, a4(a6); MOVE.W #1aa7, d0; JSR 3af8.l`
- `3992c`: `MOVE.L #39932, (a6)` (→`39932`)
- `39932`: `JSR 3b424(pc)` — FLOW
- `39936`: `BTST.B #6, 9d(a6); BEQ.W 3995a` (→`39940`) — FLOW
- `39940`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `39952`: `MOVEM.L (a7)+, d0; BCS.W 39834` (→`3995a`) — C 소비, FLOW
- `3995a`: `BRA.W 3999a` — FLOW

**`3995e`(정적 참조 없음, 결정 2; 애니메이션 `3b948`, 설치 callback `3996e`(fall-through): `3b424`, `3a4da` C → `39834`, 끝 `BRA 3999a`) 7**
- `3995e`: `MOVEA.L #3b948, a0; JSR 3b302(pc)` — FLOW
- `39968`: `MOVE.L #3996e, (a6)` (→`3996e`)
- `3996e`: `JSR 3b424(pc)` — FLOW
- `39972`: `BTST.B #6, 9d(a6); BEQ.W 39996` (→`3997c`) — FLOW
- `3997c`: `MOVE.L d0, -(a7); ANDI.B #bf, 9d(a6); ANDI.B #bf, 9e(a6); JSR 3a4da(pc)`
- `3998e`: `MOVEM.L (a7)+, d0; BCS.W 39834` (→`39996`) — C 소비, FLOW
- `39996`: `BRA.W 3999a` — FLOW

**공유 꼬리 `3999a`(`39830` `39908` `3995a` `39996 BRA`; `3a5be`(LONG `82`), BYTE `97` = 4 → `398ca`, 입력 `3b424` 상위 WORD bit 5, BYTE `9c` → `3990c`, `3b424` `39a1a`, LONG `3a` −= `a000`, `3b2a0` `3b334`, BYTE `15` bit 7 → 설치 `39a76`, 끝 `BRA 3a350`) 15**
- `3999a`: `MOVEA.L 82(a6), a0; JSR 3a5be(pc)` — FLOW
- `399a2`: `MOVE.B 97(a6), d0; CMPI.B #4, d0; BEQ.W 398ca` (→`399ae`)
- `399ae`: `JSR 3b424(pc)` — FLOW
- `399b2`: `MOVE.L d0, d1; SWAP d1; BTST.B #5, d1; BNE.W 399ce` (→`399be`)
- `399be`: `CLR.B a4(a6); ANDI.B #df, 9d(a6); ANDI.B #df, 9e(a6)` (→`399ce`)
- `399ce`: `BTST.B #5, 9d(a6); BEQ.W 399e8` (→`399d8`) — FLOW
- `399d8`: `TST.W 3a(a6); BGT.W 399e8` (→`399e0`)
- `399e0`: `TST.B 9c(a6); BNE.W 3990c` (→`399e8`)
- `399e8`: `JSR 3b424(pc)` — FLOW
- `399ec`: `JSR 39a1a(pc)` — FLOW
- `399f0`: `MOVE.L 3a(a6), d7; ADDI.L #ffff6000, d7; MOVE.L d7, 3a(a6); JSR 3b2a0(pc)`
- `39a02`: `JSR 3b334(pc)` — FLOW
- `39a06`: `BTST.B #7, 15(a6); BEQ.W 39a16` (→`39a10`) — FLOW
- `39a10`: `MOVE.L #39a76, (a6)` (→`39a16`)
- `39a16`: `BRA.W 3a350` — FLOW

- [F] 실행 의미 보충(명령 순서대로; 읽기·쓰기 순서는 원본과 같다. "애니메이션 x"는 `MOVEA.L #x,A0; JSR 3b302(PC)`, "partner"는 `MOVEA.L 82(A6),A0; JSR 3a5be(PC)`, "소리 x"는 `MOVE.W #x,D0; JSR 3af8.l`이다):
  - `38dd4`: BYTE `9f` ≥ `11`(무부호)이면 `38e20`, 아니면 애니메이션 `3b8d6`(`38dde`), `JSR 3a5d2`(`38de8`), `38dec`: BYTE `95` = 4, LONG `64` = 0(`CLR.L`), `(A6)` = `38dfc`, fall-through. `38dfc`: BYTE `94` bit 3 = 1(`BSET`), partner. `38e0a`: `JSR 3b288`. `38e0e`: `JSR 3b334`. `38e12`: Set이면 `(A6)` = `38e20`(`38e16`). `38e1c`: `BRA 3a350`.
  - `38e20`: WORD `8a` = 0, BYTE `9f` = `11`, 소리 `1a62`. `38e36`: 애니메이션 `3b8ac`. `38e40`: `JSR 3a5d2`. `38e44`: LONG `64` = 0, `(A6)` = `38e4e`, fall-through. `38e4e`: `JSR 3b288`. `38e52`: `JSR 3b334`. `38e56`: Clear면 `38e7a`: LONG `56` = 0, `BRA 3a350`. Set이면 `38e5a`: `D0.W` = WORD `86`, `D1.B` = 1, `JSR 4d4b4`(경계); `38e68`: `(A6)` = `38bac`(N31 값), LONG `56` = 0, `BRA 3a34c`.
  - `38ff4`: 소리 `1a62`. `38ffe`: BYTE `9f` > `11`(무부호, `BLS` 불성립)이면 `39008`: BYTE `9f` = `11`. `3900e`: 애니메이션 `3b8d0`. `39018`: BYTE `95` = 2, LONG `64` = 0, `(A6)` = `39028`, fall-through. `39028`: `JSR 3b424`(D0 반환). `3902c`: `D0` bit 7 = 1이면 `39db4`(N32b). `39034`: `D0` bit 1 = 1이고(`3903c`) BYTE `15` bit 7 = 1이면 `39156`. `39046`: partner. `3904e`: `JSR 3b288`. `39052`: `JSR 3b334`. `39056`: Set이면 `3905a`: BYTE `9d` &= `bf`, BYTE `9e` &= `bf`, BYTE `9f` = 0, `(A6)` = `38e92`(범위 밖 값). `39072`: `BRA 3a350`.
  - `39076`: BYTE `98` = `ff`, 애니메이션 `3b972`. `39086`: `JSR 3a5d2`. `3908a`: `(A6)` = `39090`, fall-through. `39090`: BYTE `15` bit 7 = 0이면 `398be`. `3909a`: BYTE `98` ≠ 0이면 `39140`. `390a2`: `JSR 3b424`. `390a6`: `D0` bit 7 → `39db4`. `390ae`/`390b6`: `D0` bit 1 = 1이고 BYTE `15` bit 7 = 1이면 `39156`. `390c0`: `D0` bit 1 = 0이고(`390c8`) BYTE `9f` ≠ 0이고(`390d0`) BYTE `15` bit 7 = 1이면 `38ff4`. `390da`: `D0` bit 5 → `3976a`. `390e2`: BYTE `94` bit 2 = 0이고(`390ec`) BYTE `9d` bit 4 = 1이면 `390f6`: push LONG `D0`(A7 −= 4), A0 = `3b756`, `JSR 4ae4a`(N08). `39102`: `D0.W` = 0 여부를 보고 pop LONG `D0`(A7 += 4); `D0.W` ≠ 0이었으면 `39b72`(N32b). `3910c`: BYTE `9d` bit 6 = 1이면 `39116`: push LONG `D0`, BYTE `9d` &= `bf`, BYTE `9e` &= `bf`, `JSR 3a4da`(경계). `39128`: pop LONG `D0`; Set이면 `39076`. `39130`: `D0` bit 2 → `395dc`. `39138`: `D0` bit 3 → `395f8`. `39140`: `JSR 3b288`. `39144`: `JSR 3b334`. `39148`: Set이면 `(A6)` = `38e92`(`3914c`). `39152`: `BRA 3a350`.
  - `39156`: 소리 `1a5f`. `39160`: 애니메이션 `3b8d6`. `3916a`: BYTE `95` = 2, LONG `64` = 0, `(A6)` = `3917a`, fall-through. `3917a`: BYTE `15` bit 7 = 0이면 `398be`. `39184`: `JSR 3b424`. `39188`: `D0` bit 7 → `39eb2`(N32b). `39190`: `D0` bit 1 = 0이고(`39198`) BYTE `9f` ≠ 0이고(`391a0`) BYTE `15` bit 7 = 1이면 `38ff4`. `391aa`: `D0` bit 5 → `38dd4`. `391b2`: BYTE `94` bit 3 = 1, partner. `391c0`: `JSR 3b288`. `391c4`: `JSR 3b334`. `391c8`: Set이면 `391cc`: BYTE `9d`/`9e` &= `bf`, BYTE `9f` = `11`, `(A6)` = `39366`(범위 밖 값). `391e4`: `BRA 3a350`.
  - `395dc`: BYTE `15` bit 0 = 0이고 BYTE `a3` = 0이면 `3973c`, 아니면 `395ee`: BYTE `94` bit 5 = 1, `BRA 39610`. `395f8`: BYTE `15` bit 0 = 1이고 BYTE `a3` = 0이면 `3973c`, 아니면 `3960a`: BYTE `94` bit 5 = 0. `39610`: `D0.B` = (BYTE `94` bit 5 ? `ff` : 0)(`SNE`), `D1.B` = (BYTE `15` bit 0 ? `ff` : 0), `D0.B` ^= `D1.B`; ≠ 0이면 애니메이션 `3b918`(`39634`), 0이면 애니메이션 `3b912`(`39626`) 뒤 `BRA 3963e`(`39630`). `3963e`: WORD `2c` = `aa`, BYTE `95` = 1, LONG `64` = 0, `(A6)` = `39654`, fall-through. `39654`: BYTE `15` bit 7 = 0이면 `398be`. `3965e`..`396ca`: `39090` 계열과 같은 입력 검사(`D0` bit 7 → `39db4`, bit 1 + `15` bit 7 → `39156`, bit 5 → `3976a`, `94` bit 2 / `9d` bit 4 → push + `4ae4a` → `396a4`(Z, pop, ≠ 0 → `39b72`), `9d` bit 6 → push + `9d`/`9e` &= `bf` + `3a4da` → `396ca`(pop, Set → `39076`)). `396d2`: `D0` bit 3 = 1이면 `396da`: BYTE `15` bit 0 = 1이고 BYTE `a3` = 0이면 `3973c`; BYTE `94` bit 5 = 1이면 `395f8`, 아니면 `39728`. `D0` bit 3 = 0이고 bit 2 = 1이면 `39702`: BYTE `15` bit 0 = 0이고 BYTE `a3` = 0이면 `3973c`; BYTE `94` bit 5 = 0이면 `395dc`, 아니면 `39728`. 둘 다 0이면 `39722`: `(A6)` = `38e92`. `39728`: partner. `39730`: `JSR 3b288`. `39734`: `JSR 3b334`. `39738`: `BRA 3a350`(C를 읽지 않음).
  - `3973c`: 애니메이션 `3b95a`. `39746`: `JSR 3a5d2`. `3974a`: LONG `64` = 0, `(A6)` = `39754`, fall-through. `39754`: `JSR 3b288`. `39758`: `JSR 3b334`. `3975c`: Set이면 `(A6)` = `38e86`(`39760`). `39766`: `BRA 3a350`.
  - `3976a`: 애니메이션 `3b91e`. `39774`: BYTE `95` = 3, BYTE `9a` = 0, BYTE `9d`/`9e` &= `ef`, `JSR 496c2`(U11). `39792`: BYTE `9f` = 0, `(A6)` = `3979e`, fall-through. `3979e`: BYTE `15` bit 7 = 0이면 `398be`. `397a8`: `JSR 3b424`. `397ac`: `D0` bit 7 → `39db4`. `397b4`: partner. `397bc`: `JSR 3b2a6`. `397c0`: `JSR 3b334`. `397c4`: Set이면 `(A6)` = `397d2`(`397c8`). `397ce`: `BRA 3a350`.
  - `397d2`(설치): 소리 `1a61`. `397dc`: 애니메이션 `3b924`. `397e6`: BYTE `95` = 0, LONG `3a` = `8fc4e`, `(A6)` = `397fa`, fall-through. `397fa`: `JSR 3b424`. `397fe`: BYTE `9d` bit 6 = 1이면 `39808`: push + `9d`/`9e` &= `bf` + `JSR 3a4da`; `3981a`: pop, Set이면 `39834`. `39822`: WORD `3a` < 0(`BPL` 불성립)이면 `(A6)` = `398d0`(`3982a`). `39830`: `BRA 3999a`.
  - `39834`: `JSR 3a5d2`. `39838`: 애니메이션 `3b978`. `39842`: `(A6)` = `39848`, fall-through. `39848`: `JSR 3b424`. `3984c`: `D1` = `D0`, `SWAP D1`; `D1` bit 5(= `D0` bit 21) = 0이면 `39858`: BYTE `a4` = 0(`CLR.B`), BYTE `9d`/`9e` &= `df`. `39868`: BYTE `9d` bit 5 = 1이고(`39872`) WORD `3a` ≤ 0(부호 있음, `BGT` 불성립)이고(`3987a`) BYTE `9c` ≠ 0이면 `3990c`. `39882`: `JSR 3b424`. `39886`: `JSR 39a1a`(경계). `3988a`: `D7` = LONG `3a` + `ffff6000`(32 bit), LONG `3a` = `D7`, `JSR 3b2a0`. `3989c`: `JSR 3b334`. `398a0`: Set이면 `(A6)` = `398ca`(`398a4`). `398aa`: BYTE `15` bit 7 = 1이면 `(A6)` = `39a76`(`398b4`, 범위 밖 값). `398ba`: `BRA 3a350`.
  - `398be`: BYTE `9d`/`9e` &= `df`, fall-through `398ca`: BYTE `95` = 0, fall-through `398d0`: 애니메이션 `3b92a`. `398da`: `(A6)` = `398e0`, fall-through. `398e0`: `JSR 3b424`. `398e4`: BYTE `9d` bit 6 = 1이면 `398ee`(push + `3a4da`) → `39900`(pop, Set → `39834`). `39908`: `BRA 3999a`.
  - `3990c`: BYTE `9d`/`9e` &= `df`, BYTE `9c` −= 1(`SUBQ.B`, 8 bit), BYTE `a4` = `a`, 소리 `1aa7`. `3992c`: `(A6)` = `39932`, fall-through. `39932`: `JSR 3b424`. `39936`: BYTE `9d` bit 6 = 1이면 `39940`(push + `3a4da`) → `39952`(pop, Set → `39834`). `3995a`: `BRA 3999a`.
  - `3995e`(결정 2): 애니메이션 `3b948`. `39968`: `(A6)` = `3996e`, fall-through. `3996e`: `JSR 3b424`. `39972`: BYTE `9d` bit 6 = 1이면 `3997c`(push + `3a4da`) → `3998e`(pop, Set → `39834`). `39996`: `BRA 3999a`.
  - `3999a`: partner. `399a2`: `D0.B` = BYTE `97`; = 4면 `398ca`. `399ae`: `JSR 3b424`. `399b2`..`399e0`: `3984c`..`3987a`와 같다(`399be` = `39858`, → `3990c`). `399e8`: `JSR 3b424`. `399ec`: `JSR 39a1a`. `399f0`: `3988a`와 같다(`JSR 3b2a0`). `39a02`: `JSR 3b334`. `39a06`: BYTE `15` bit 7 = 1이면 `(A6)` = `39a76`(`39a10`). `39a16`: `BRA 3a350`(C를 읽지 않음).
- [I] 의미 추정(미확인): `3b424`는 입력 bit(7 = 상태 전환, 1/5 = 버튼, 2/3 = 좌우)를, `3b334`는 이동·충돌 결과 C를, `3a4da`는 피격 판정 C를 돌려주는 것으로 보인다. 실행부는 이 추정에 기대지 않는다.

## carry

- [F] **소비 14 block**(모두 FLOW). Unknown C로 들어오면 `objects n32 caller requires known carry`(상태 보존)다.
  - `BCC.W`(Clear면 분기 대상, Set이면 fall-through) — 경계 `3b334`의 C: `38e12 BCC.W 38e1c`, `38e56 BCC.W 38e7a`, `39056 BCC.W 39072`, `39148 BCC.W 39152`, `391c8 BCC.W 391e4`, `3975c BCC.W 39766`, `397c4 BCC.W 397ce`, `398a0 BCC.W 398aa`.
  - `MOVEM.L (A7)+,D0; BCS.W`(pop 뒤 Set이면 분기 대상, Clear면 fall-through; 결정 6) — 경계 `3a4da`의 C: `39128 BCS.W 39076`, `396ca BCS.W 39076`, `3981a BCS.W 39834`, `39900 BCS.W 39834`, `39952 BCS.W 39834`, `3998e BCS.W 39834`.
- [F] **known 생산 0 block.** `ORI`/`ANDI` CCR이 없다. `39610 EOR.B`, `3988a ADDI.L` 등은 C를 바꾸지만 같은 block의 Bcc나 다음 소비자가 C를 읽지 않는다(Unknown).
- [F] **FLOW_ONLY 134 block**(C 보존): JSR만인 block, `MOVEA.L`(+`JSR`) block(애니메이션·partner 호출), `BSET`/`BCLR`(+`MOVEA`+`JSR` / +`BRA`) block `38dfc` `391b2` `395ee` `3960a`, `BTST`(+Bcc) block, `BRA` block, 소비 14개. 목록: `38dde` `38de8` `38dfc` `38e0a` `38e0e` `38e12` `38e1c` `38e36` `38e40` `38e4e` `38e52` `38e56` `3900e` `39028` `3902c` `39034` `3903c` `39046` `3904e` `39052` `39056` `39072` `39086` `39090` `390a2` `390a6` `390ae` `390b6` `390c0` `390d0` `390da` `390e2` `390ec` `3910c` `39128` `39130` `39138` `39140` `39144` `39148` `39152` `39160` `3917a` `39184` `39188` `39190` `391a0` `391aa` `391b2` `391c0` `391c4` `391c8` `391e4` `395dc` `395ee` `395f8` `3960a` `39626` `39630` `39634` `39654` `3965e` `39662` `3966a` `39672` `3967c` `39684` `3968e` `396ae` `396ca` `396d2` `396da` `396ec` `396f6` `396fa` `39702` `39714` `3971e` `39728` `39730` `39734` `39738` `3973c` `39746` `39754` `39758` `3975c` `39766` `3976a` `3979e` `397a8` `397ac` `397b4` `397bc` `397c0` `397c4` `397ce` `397dc` `397fa` `397fe` `3981a` `39830` `39834` `39838` `39848` `39868` `39882` `39886` `3989c` `398a0` `398aa` `398ba` `398d0` `398e0` `398e4` `39900` `39908` `39932` `39936` `39952` `3995a` `3995e` `3996e` `39972` `3998e` `39996` `3999a` `399ae` `399ce` `399e8` `399ec` `39a02` `39a06` `39a16`.
- [F] **carry 보존 목록 134 PC** = FLOW_ONLY 134.
- [F] **Unknown 69 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMPI`/`ANDI`/`EOR`/`SUBQ`/`ADDI`/`SWAP` 포함 block, 설치 block, `MOVE.L D0,-(A7)` push block, `TST.W D0; MOVEM; BNE` block `39102` `396a4`).
- [F] N32a에는 RTS가 없다. 모든 경로는 경계 callee·다른 실행부 호출, N32b 출구, `BRA 3a350`/`3a34c`에서 이 단위를 떠난다.

## 구현 범위와 규약

- routing 3 범위(위 표). 짝수 PC 882개 중 block 시작 203, 내부 679. 내부 PC 직접 진입은 `unsupported animation objects n32 PC`다. 범위 이웃(N32b, `3a34c..3a4a4`, 설치 대상 코드 `38d56..38dd4` `38e86..38ff4` `391e8..395dc` `39a1a..39b72`)은 routing 밖 PC(`unsupported animation machine PC`; stop이면 직전 상태로 멈춤, 아니면 rollback)다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVE.L`·`MOVEA`·`LEA`·`MOVEM.L`은 LONG 전체). 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow에 기대지 않는다(`ADDI.L #ffff6000`·`SUBQ.B #1`). 결과 flag는 같은 block 안의 Bcc만 쓴다. 명령 순서대로 읽기·쓰기를 한다(홀수 주소 등 checked 오류의 순서가 원본과 같다). `BTST.B #n,Dn`은 `Dn` bit n(n < 8)을 본다. `CLR`은 쓰기만 한다(기존 단위와 같음).
- carry: 위 "carry" 절. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석이 붙은 case group 하나)에 134 PC를 넣는다.
- 제어 이동: 모두 정적이다. 범위 안 설치 대상이 fall-through로 이어지면 같은 실행으로 계속한다(13곳, 위 진입 목록). 설치 값은 노드 LONG에 쓰는 자료이고 실행 PC가 아니다.
- 스택: JSR 복귀 LONG, `MOVE.L D0,-(A7)` push와 `MOVEM.L (A7)+,D0` pop(LONG, A7 ∓4, `am_push`/`am_pop` 크기 4). work RAM 밖 스택 쓰기·읽기는 기존 checked 오류다.
- I/O port 쓰기 없음. bank 변경 없음. 자료 읽기는 모두 work RAM(live bus `am_read`)이다. work RAM 밖 쓰기, 홀수 주소 WORD/LONG, 미해결 읽기는 기존 checked 오류다.

## 자료

- [F] 고정 ROM·banked 자료 읽기: 없음. 주소만 넘기는 자료: 애니메이션 목록 `3b8d6` `3b8ac` `3b8d0` `3b972` `3b912` `3b918` `3b95a` `3b91e` `3b924` `3b978` `3b92a` `3b948`(A0 → `3b302`), 충돌 목록 `3b756`(A0 → `4ae4a`), 소리 id `1a62` `1a5f` `1a61` `1aa7`(`D0.W` → `3af8`), LONG `3a` 값 `8fc4e`(`397e6`).
- [F] work RAM 노드 A6: BYTE `15`(bit 0, 7) `94`(bit 2, 3, 5) `95` `97` `98` `9a` `9c` `9d`(bit 4, 5, 6) `9e` `9f` `a3` `a4`; WORD `2c` `3a`(상위 WORD, `TST.W`) `86` `8a`; LONG `(A6)`(설치) `3a` `56` `64` `82`(partner 포인터, A0로만 넘김).
- [F] 상수 인자: `4d4b4` `D0.W` = WORD `86`, `D1.B` = 1; `3a5be` A0 = LONG `82`.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_objects_n32.cpp` `e0c8d0df1663fe53`, `engine/tests/animation_machine_objects_n32_test.cpp` `dd5d3a44f9bc1bdd`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나(3 범위), carry 보존 case group 하나(134 PC); `a65efec3dd0604d4`), `engine/src/animation_machine_internal.h`(선언 하나; `3cb7dda444c5c902`), `Makefile`(source 목록·test target·실행 줄; `4e3ff048a79a563f`), `tools/verify_animation_machine.py` SOURCES(`8d5e3ed4b3c36234`). `animation_machine_interpreter.cpp`와 다른 단위 실행부는 바꾸지 않았다. 다른 단위의 두 번째 진입 patch는 필요 없다.
- [F] 실행부 case 집합 = scratch `startsA.txt`(203). 내부 PC 679개는 모두 `unsupported animation objects n32 PC`, 소비 14 block은 Unknown C에서 `objects n32 caller requires known carry`(상태 보존)다.
- [F] `make -j3 all test`: exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`). N32 test 출력: `animation machine objects n32: 751 fixtures (29 checked errors, 38 kept C), 203 blocks, 2657 calls`. N30(166 block)·N27(162 block) test는 그대로 통과.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_ubsan.sh`): N32 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만, scratch `gen/gen32.py` Unicorn 생성(표 SHA256 앞 16자리 `51c41e0d168ff8f7`), `gen/assemble32.py` 조립): 751 fixture(성공 722, checked 오류 29), 203 시작 모두 Unicorn fixture로 덮음, block 표(203 시작 × incoming C 3: 성공 후속·digest·C 분류; 소비 14는 Unknown에서 거부), zero-step 203 × 3, 내부 PC 679 전수, 홀수 PC(범위 양끝 6), RAM rollback 탐침 `10fe60` `10fe70` `10fe80`, 경계·다른 단위 진입 stop 19개(stop만; `39b72` `39db4` `39eb2` `3a34c` `3a350` 포함), 여러 block을 실행한 뒤 스택 checked 오류로 끝나는 rollback 행 7개(N32a에는 RTS가 없어 N30의 RTS 복귀 탐침 대신). 입력 bit 사슬(`D0` bit 7/1/5/2/3 × BYTE `15` `9f` `94` `9d` `98` `a3`), 경계값(`9f` = `10`/`11`/`12`, WORD `3a` = 0/1/`7fff`/`8000`/`ffff`, LONG `3a` 랩, BYTE `9c` 랩, `D0` bit 21), MOVEM pop(Z·C) 행. 다른 실행부를 따라간 행: `3af8`(5곳)·`496c2`(`39774`)·`4ae4a`(`390f6` `39698`, 합성 목록 `3b756` + BYTE `4a9eb` → `D0.W` = 0). 합성 물리 바이트(ROM 자료 아님): `3b756..3b75a`, `4a9ea..4a9ec`. 소비자 C는 생산자가 경계라 선언 C로만 실행했다(Unicorn SR을 생산자 사실로 쓰지 않음).
- [F] 돌연변이 검사(scratch `mut/mut32.py`, 실행부 33곳 + carry 목록 2곳 + routing 2곳, 37개): 35/37을 test가 잡았다(`mut/mut.log`, `mut_extra.log`). 살아남은 `m2`(`38ffe` `<= 11` → `< 11`)는 `9f` = `11`일 때 `39008`이 같은 값 `11`을 다시 쓰는 동치 돌연변이다(경계를 `12`로 옮긴 `m2b`는 잡힘). `m35`(routing 끝 `39a1a` → `39a1c`)는 test가 범위 밖 이웃 `39a1a`(다른 단위 몫 코드)를 rollback 탐침으로 쓰지 않는 F4 관례 때문에 잡히지 않는다(범위를 줄인 `m35b`는 잡힘; 범위 양끝 이웃이 routing 밖임은 정적 `hroute32.py`로 확인).
- [F] 실제 ROM 차분(scratch `realrom/real32.py` SHA256 앞 16자리 `f00e310fe24fbd3f`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM; native는 STOP·C++ routing 밖 첫 PC(N32a 경계 11, N32b 출구 3, `3a34c` `3a350`; 나중 단위가 routing해도 선언 stop으로 유지)·`2a00`·`2a24`·interpreter `49f8c`/`49f96`(선언 stop)에서 멈춤; 실제 `3af8` `4ae4a`(실제 목록 `3b756`) `496c2`는 양쪽에서 실행): 3 seed × 1,500 case 불일치 0/0/0, 시작 199/200/198(합집합 203), native skip 0, port 0, 홀수 주소·Unknown C 진입 소비 거부·`2986` 0건. N32a 소비자의 생산자는 모두 경계라 "실제 생산자 뒤 소비자" 비교는 없다.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `ea27f57` 일치 pass 14,648·node 126,688, 불일치 0 → N32a 뒤 같음(`diff_results.json` SHA256 앞 16자리 `ad8c6c0a8680d6e6`, 기준과 동일).
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 134·pass 53,600·node 403,677·불일치 0(`verification.json` `7cab878c…`) → N32a 뒤 같은 수치·불일치 0(`301cb3c1…`; 차이는 기록된 `animation_machine.cpp` SHA(seed 116 117의 `current_router_sha256` 포함)와 새 원본 목록뿐). **새 완주 seed 없음**(예상과 같음), 잃은 seed 0. seed 116 117은 그대로 frame 0 `38ba0`(N31)에서 멈춘다.
- [F] 탐침 이동: 없음(결정 9). 이 test의 새 RAM 탐침은 `10fe60` `10fe70` `10fe80`이다.
- [U] 남은 미확인: N32a 범위는 자연 400 frame에서 실행되지 않아 frame pass 비교가 없다(실제 ROM 차분·fixture로만 덮음). 경계 `3b334`·`3a4da`의 C 생산과 `3b424`·`4ae4a`의 반환 의미는 그 단위가 정한다. 결정 2의 `3995e` 진입은 정적 참조가 없다. 결정 1의 N32b(`39b72..39f9c` `3a34c..3a4a4`)와 결정 7의 설치 대상 코드는 routing하지 않았다. 재범위 "미실행 설치 28(+229)"의 정확한 대응은 확인하지 않았다.
