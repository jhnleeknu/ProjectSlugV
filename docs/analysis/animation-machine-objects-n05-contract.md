# 객체 callback F4 N05(옛 U21·R04): `dceca`·`bdcc6`·`c5fd8`·`c5e6c` 객체 callback과 공용 helper `49214`·`1ab80`·`1a3ae`·`d3c2a` 계약 초안

**상태: 계약 초안(구현 전 원본 바이트 근거). 구현·검증 기록이 아니다.**

범위 근거는 재범위 문서(`animation-machine-object-callbacks-f4-rescope.md`, SHA256 `86910070d60642d057fbb8313d9a06414d2ff01c185827fc02bcf2f2deb9cd75`)의 N05 행(`1a3ae..1a3c8` `1ab80..1abda` `49214..49260` `bdcc6..bdf82` `c5e6c..c5e7c` `c5fd8..c6012` `d1cd8..d1e6e` `d22e6..d23d8` `d3c2a..d3c40` `dceca..dcf42`, callback `bdcc6` `bdd8a` `bdec4` `bdedc` `bdf40` `c5e6c` `c5fd8` `d1cd8` `d1d38` `d22e6` `d23b2` `dceca` `dcef8`, 경계 callee 없음, bank 3, 새 seed 28 29)과 메인 결정 1·2(이름 `objects-n05`, 범위 안 설치 callback 포함, 범위 밖 설치 사슬은 경계)다. 원 범위(`animation-machine-object-callbacks-f4-scope.md`, SHA256 `e0c19088159adaa9f2eb6e0f38ce41a4e3f2e20a9f79f53fd900bc1ed5851253`)의 U21 행과 R04 일부다. 단위 형식과 규약은 N03 계약(SHA256 `b3305fc97d9e37ca8f7e3f0de8ae82204e70c79c3e6e3f7bc4a31a5fc25f38f8`)과 U05 계약(SHA256 `77fd4062f3935d0e8b2989ad65bed395f43fa7bd37f33309c7a29fa9f512dafc`, `1ab02` 반환 C)을 따른다.
- 결정 3: block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 JSR 대상, 범위 안의 `MOVE.L #imm,(A6)` 설치 callback, 범위 안의 `MOVEA.L #imm,A0`+`JSR 28ae` 자식, 범위 안을 가리키는 `c6012` LONG 표 자식)로 정한다.
- 결정 5: 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 실행부 없는 경계다.
- U01~N03 수용 관례: `MOVE.x`/`MOVEQ`/`TST`/`CMP`/`CLR`는 C를 지운다(소비자가 있을 때만 known 생산으로 둔다). CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`SUBA`/`JSR`/`BSR`/`JMP`/`BRA`/`RTS`/Bcc, Z만 바꾸는 `BCHG`)만인 block과 callee C를 소비하는 block은 FLOW_ONLY다. checked 오류는 경계에서 낸다. 다른 단위 범위는 다시 routing하지 않는다. known C는 소비자에서 native 분기로 확인한다(Unicorn SR로 C를 단정하지 않는다).

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB)을 capstone M68000으로 디코드했다. N05 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. banked window 자료(`2001dc`, `20008c`, `200094`)는 "자료"에 따로 적는다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-n05`(HEAD `20a3574` = N01·N03까지 통합, `engine/src/animation_machine.cpp` SHA256 `2b1becdd8ec7cdbcc4bc25efc5f56efec551632b40685df9ae72b3e532448829`, routing 규칙 60개)을 참조했다. N05 범위의 짝수 PC는 기존 routing에 하나도 없다. 동시에 진행하는 N04(`4a46c..4a496` `4bc04..4bc44` `6feb4..70054` `71c90..71d48` `72a18..72e8e` `aa93e..aaa18` `ab02a..ab226` `eb752..eb774`)와 겹치지 않고 N04 PC는 N05에서 나오지 않는다. [F]=원본 바이트 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/n05/n05.py`가 원본 opcode에서 독립 계산했다.

## 요약

- [F] N05는 **block 시작 128개**다. 코드 13 범위, 1,500바이트, 332명령이다. 미해독·PC 상대 점프 표·레지스터 간접 점프·TRAP·묶인 Bcc·SUBX/ADDX/DIVx/MULx·I/O port 쓰기·bank 변경은 없다. routing 짝수 PC는 750개, 내부 PC는 622개다.
  - 재범위 N05 행의 114와 다르다. 재범위 함수 본문 디코더(`rescope/sdec.py`)를 이 13 범위의 실행 진입에 다시 돌리면 111 시작이다. 차이 17은 (a) 400 frame 안에 실행되지 않는 범위 안 설치·자식 진입의 본문(`c6012` 표 자식 `d1d08` `d1d98` `d1dc8`과 복귀점 `d1d30` `d1dc0` `d1df0` 6, `MOVE.L #bde50,(A6)` 설치 callback 본문 `bde50` `bde5a` `bde9a` `bdea0` `bdea6` `bdeac` `bdeb8` `bdebc` `bdec2` 9)과 (b) fall-through로 이어지는 `MOVE.L #imm,(A6)` 설치 대상 `bdd3e` `dcf22` 2(결정 3은 설치 대상을 block 시작으로 센다)다. 메인 결정 2(범위 안 설치 callback 포함)로 넣는다(결정 1).
  - 범위 표기의 구멍: 재범위의 `d1cd8..d1e6e` `d22e6..d23d8`은 hull이다. 그 안의 `d1d68..d1d98`(48바이트, 함수 `d1d68`), `d1df8..d1e58`(96바이트, 함수 `d1df8` `d1e28`), `d232c..d239c`(112바이트, 함수 `d232c`)는 ROM 8 MiB 어디에서도 LONG·분기·PC 상대 참조가 없다(정적 도달 불가). N03 `c644a`와 같이 routing 밖(`unsupported animation machine PC`)에 둔다(결정 2).
  - 범위에서 빼는 이웃: `1a3a6..1a3ae`(다른 진입 `1a3a6` `1a3ac`, `MOVEQ`+`BRA`/fall-through로 `1a3ae`에 들어옴), `1a3c8..`(stage entry), `1ab7a..1ab80`(U05), `1abda..`(U12), `4920c..49214`, `49260..`(U14), `bdcc4`, `bdf82..`(자료 `bdf82`), `c5e7c..`(다른 callback `c5e7c`), `c6012..c603a`(LONG 표 10개), `d1e6e..d22e6`(표 자식 `d216a` `d21b8` `d2206` `d224c`의 함수들, 이 단위 밖), `d23d8..`, `d3c40..`, `dcf42`(미도달 `RTS`).
- [F] 함수: 노드 callback `dceca`(LONG `dcf50`, 뒤 WORD `ffff`), `bdcc6`(stage event 표 LONG `e8f98`), `c5e6c`(LONG `e9018` `e901c`), `c5fd8`(LONG `e9028`); `MOVE.L #imm,(A6)` 설치 callback `bdd3e` `bdd8a` `bde50` `bdea0` `bdf40` `d23b2` `dcef8` `dcf22`; `28ae` 자식 `bdec4` `bdedc`(`bdcc6`)와 `c6012` 표 자식 `d22e6` `d1cd8` `d1d08` `d1d38` `d1d98` `d1dc8`(`c5fd8`); 공용 helper `49214`(169곳 호출, 그중 routing된 U15 `af25a`, U16 `bbebe` `bbeec`), `1ab80`(85곳, routing된 호출자는 이 단위 `d23c6`뿐), `1a3ae`(`c5e70`와 routing 밖 4곳·`1a3a8 BRA.W`), `d3c2a`(8곳, routing된 U15 `af402`와 이 단위 `d239c`).
- [F] **경계 callee(실행부 없음)**: 없다. 나가는 호출은 모두 routing됨(아래). 설치만 하고 실행하지 않는 범위 밖 대상: `c6012` 표 entry 6~9의 `d216a` `d21b8` `d2206` `d224c`(76(A6)=6~9일 때 `28ae` 자식), `dcf2c`의 `28ae` 자식 `4841a`. 이 단위는 그 PC로 제어를 넘기지 않는다(노드 LONG에 저장만).
- [F] **나가는 호출(routing됨)**: fade_card `28ae`(`bdcc6` `bdcd6` `c5fd8` `dcf2c`, C 반환)·`2a00`(`JMP`), sound `3af8`(`bdd62` `bde50` `dced6`), U05 `c6a96`(`bdce6` `bdef4` `d22e6`)·`1ab02`(`bdd72` `bde38` `bdeac`, C 반환), interpreter `49f8c`(7곳)·`49fc6`(`bdd44` `bde32` `bdea6` `bdf58` `d23b8`, `d23b8`만 C 소비), cleanup `43e34`(`bdd3e` `bdea0` `bdf40` `d23b2`)·`43e38`(`49214`), U04 `43ea4`(`bde2c`), U08 `49290`(`bdec4` `bdedc`), stage event ops `288c`(`bdf5e`, C 반환), U09 `4706c`(`bdf7a`), U02 `8ebe`(`d1e58`), stage area `49a58`(`d3c2a`), U01 `48296`(`dcee0`)·`1aafc`(`1ab80` 계열 `BGT`/`BLT` 대상, ORI CCR Set), area clear `1c5b0`(`dcee6`), input `49c66`(`dceec`)·`49c32`(`dcf0a`), U17 `482c0`(`dcf04`).
- [F] **flag**:
  - 블록 경계를 건너는 C 소비 block **7개**: `bdd7e` `bde44` `bdeb8`(`BCC`, `1ab02` 반환: U05 `1ab7a` Clear / U01 `1aafc` Set), `bdf64`(`BCS`, `288c` 반환), `c5ff2`(`BCC`, `28ae` 반환: `290c` 앞 ORI Set / `2912` ANDI Clear), `d23be`(`BCS`, `49fc6` 반환), `d23cc`(`BCS`, 이 단위 `1ab80` 반환).
  - known carry 생산 block **1개**: `1abd4`(`ANDI.B #fe,CCR; RTS` → Clear). `1ab80` 계열의 나머지 반환은 U01 `1aafc`(Set)다. 소비자는 이 단위 `d23cc`(routing 밖 호출자 84곳은 이 단위와 무관).
  - N 재계산 block **1개**: `bddb4 BPL.W bddf6`는 앞 block `bdd8a`의 `SUB.W D0,D2` N을 쓴다. `bddb4`의 선행은 `bdd9c BNE.W`(taken) 하나뿐이고 그 결과가 D2 하위 WORD에 그대로 있으므로 N = D2 bit 15로 정확히 재계산한다(결정 3). C는 쓰지 않는다(FLOW_ONLY).
  - block 안에서 만들고 쓰는 flag: `CMPI.W #8,D0; BCS`(무부호, `1a3ae`), `TST.W 5408(A5); BPL`(`1a3b8`), `BTST #1/#0,15(A6); BEQ`(`1ab80` `1abaa`), `CMPI.W #k,D2; BGT/BLT`(부호, `1ab92` `1aba0` `1abbc` `1abca`), `TST.L c(A1); BEQ`(`bdd4a`), `CMPI.W #270/#32a/#198,5418(A5); BLT/BGE`(부호, `bdd58` `bdda0` `dcef8`), `SUB.W D0,D2; BNE`(`bdd8a`), `NEG.W D2; CMPI.W #1,D2; BGT`(`bddb8`), `CMPI.W #1,D2; BGT`(`bddf6`), `SUB.W 7a(A6),D2; BPL`(`bddd6` `bde12`), `CMPI.L #80000,c(A1); BLT`(부호 LONG, `bdf46`), `CMPA.W #0,A0; BEQ`(32bit, `bdf6e`), `ANDI.B #2,D0; BNE`(`d3c30`), `CMPI.B #1,100012.L; BEQ`(`dceca`), `SUBQ.W #1,76(A6); BCS`(borrow, `dcf22`).
- [F] 읽는 자료(모두 live bus):
  - bank window LONG: `2001dc`(`bdd10` `bde5a` `bdf06` → `22(A6)`), `20008c`(`d1cd8` 계열 5곳), `200094`(`d22f8`). 각 LONG이 가리키는 주소 + `5c`/`60`(`2001dc` 계열), + `4`/`8`/`c`/`40`(`20008c` 계열), + `18`(`200094`)의 LONG을 다시 읽어 A1(interpreter 목록)에 둔다.
  - fixed ROM LONG 표 `c6012`(10 LONG, SHA256 `a65599b5c4ec659d8f3912c7a8a5f471d0f796b992ca8d6f45aa6b33b37019ca`: `d22e6` `d1cd8` `d1d08` `d1d38` `d1d98` `d1dc8` `d216a` `d21b8` `d2206` `d224c`). index는 WORD `76(A6)`×4(`ADD.W` 두 번, `(A1,D0.W)` 부호확장)이고 원본에 상한 검사가 없다. 10 이상이나 음수 index는 표 밖 바이트(`c603a` 코드 등)를 LONG으로 읽어 `28ae`에 넘긴다. 이 단위는 그 LONG으로 제어를 넘기지 않으므로 live bus로 읽기만 한다(표 전사 불필요).
  - 사각형(`1ab02`/`1ab80`에 A0로 넘기는 fixed 8바이트): `be1dc`(`fef0 ff00 0260 0200`), `92(A6)`에 저장하는 `d3e54` `d3e5c` `d3e64` `d3e8c`. 주소만 저장하는 상수: `bdfdc` `bdf82`(`7e(A6)`, `4706c`가 읽음), 자식·callback 주소.
  - work RAM: node WORD `1e` `20` `42` `46` `68` `76` `78` `7a`, LONG `22` `32` `36` `3a` `42` `46` `4a` `4e` `7a` `7e` `92` `(A6)`, BYTE `15` `17`; 자식 node(28ae 반환 A0) WORD `68` `1e`, LONG `2e..42`(`49214` MOVEM); A5 WORD `5408`(`1a3ae`), `5418`, LONG `538e+14..+20`(`49214`); 절대 `10b1e2` LONG(`LEA 10b1d6.L,A1; c(A1)`), `100012` BYTE.
- [F] 자연 도달(재범위 scratch 재생, TB 기준): RNG 초기화+응답 `80` 400 frame에서 N05 시작 95개(TB 분할 산물 `c5fe0`~`c6002` 7개 제외), base에서 62개. callback 13개는 RNG·base 모두 seed 28 29만 진입한다. 공용 helper(`49214` `1ab80` `1a3ae` `d3c2a`)와 일부 블록은 다른 seed(6 7 12~15 18 19 30 31 76 77 96~99 102~105)도 닿는다. 나머지 33 시작(`1a3b6` `1a3c0` `1ab8e` `bdd3e` `bdd62` `bdd72` `bdd82` `bddaa` `bde48`, `bde50` 계열 9, `bdf68`, `d1d08` 계열 6, `dcf04`~`dcf3c` 9 등)은 TB 안 fall-through이거나 자연 미도달이며 typed fixture와 실제 ROM 차분으로 덮는다.
- [F] seed 28·29의 기준 첫 미연결 callback은 `dceca`(frame 0)다. [I] N05로 두 seed가 base·RNG 모두 완주할 것으로 본다(검증에서 확인).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **block 수 128(재범위 N05 행 114와 차이).** 범위 안 설치·자식 진입 중 400 frame 안에 실행되지 않는 것(`d1d08` `d1d98` `d1dc8` 표 자식, `bde50` 설치 callback)과 fall-through 설치 대상(`bdd3e` `dcf22`)을 넣는다(메인 결정 2).
2. **참조 없는 코드 `d1d68..d1d98` `d1df8..d1e58` `d232c..d239c`는 routing 밖**(N03 `c644a` 선례). 범위가 13개로 쪼개진다. 넣으면 실행 경로 없는 block 20개(`d1d68` `d1d90` `d1df8` `d1e20` `d1e28` `d1e50` `d232c` `d2360` `d2366` `d236a` `d237c` `d238a` 등)를 typed fixture로만 검증하게 된다.
3. **실행부 파일·오류 문자열.** `engine/src/animation_machine_objects_n05.cpp`의 `animation_objects_n05_block`. 오류는 `unsupported animation objects n05 PC`(내부 PC), `objects n05 caller requires known carry`(소비 7 block). 메인 지시와 같다.
4. **`bddb4` N 재계산**(유일 선행, D2 bit 15). Unicorn typed fixture에서 `bddb4`를 직접 진입할 때는 SR N을 D2 bit 15와 같게 둔다.
5. **`c6012` 표 index 무상한.** live bus LONG 읽기로 두고 표 밖 index도 원본처럼 읽는다(점프가 아니므로 F1 결정 3 대상 아님).
6. **bank·fixed 자료.** bank LONG(`2001dc` `20008c` `200094`와 그 + offset LONG)과 fixed 표·사각형은 live bus로 읽는다(U18 결정 6, N03 결정 4와 같음). test는 합성 bank·fixed 바이트를 쓴다(ROM 자료를 test에 넣지 않음).
7. **무효화 탐침.** [F] N05가 routing하는 PC를 routing 밖(`unsupported animation machine PC`) 기대로 쓰는 test 3곳: `engine/tests/animation_machine_objects_u05_test.cpp`의 `outside[]` `0x1ab80` `0x1ab82`, `engine/tests/animation_machine_scene_core_test.cpp`의 `outside[]` `0x1a3c6`, `engine/tests/animation_machine_stage_entry_test.cpp`의 `outside[]` `0x1a3c6`. RAM 탐침 `0x10fe52` `0x10fe54`, `0x10fe56`, `0x10fe58`로 바꾼다(F4 test 경계 관례). U15·U16 test의 `49214`/`d3c2a` 멈춤 기대는 멈춤만 확인하므로 그대로 유효하다. `tools/*.py`에서 N05 PC를 경계 기대로 쓰는 곳은 없다(scratch `probes.py`).

## 원본 바이트 근거

[F] 코드 13 범위 합계 1,500바이트. 범위 순서로 이어 붙인 SHA256 `eede3b67da872ace22b5ffebc5e0a0da7dfef83acb07bd91e746014f973606a4`.

| CPU 범위 | 바이트 | SHA256 | 시작 | 내용 |
| --- | --- | --- | --- | --- |
| `1a3ae..1a3c8` | 26 | `372b1270b909ba04e81f386fa44850a5c34f06743308d323743fedd4c2e752a5` | 5 | helper `1a3ae` |
| `1ab80..1abda` | 90 | `7448406d7847782d72893afe01fb57a25b734b8aa7ad56ca61361373e05accaf` | 9 | 화면 범위 검사 `1ab80` |
| `49214..49260` | 76 | `11ceccd43678e13d92774bbe7f4fa1c5163ae8b909d6da305622d5b885e1531e` | 2 | helper `49214` |
| `bdcc6..bdf82` | 700 | `abf8ec055de67581980fe080df98bd6409816b5a89584d23a6ccbf60f8b25dd7` | 62 | callback `bdcc6`, 설치·자식 |
| `c5e6c..c5e7c` | 16 | `3eac5234126eb8cade770d821d610d5950ea0dffed73a069459d8452f422c8f5` | 2 | callback `c5e6c` |
| `c5fd8..c6012` | 58 | `dd17c93c9857df32cb7e754674476e0db4c18b40ce1c8d3d32f138eb6af57950` | 4 | callback `c5fd8` |
| `d1cd8..d1d68` | 144 | `1eb853278559de001deb155f1ae9d2cc858622a8fe991f65c2d355d4e0f3de5d` | 6 | 표 자식 `d1cd8` `d1d08` `d1d38` |
| `d1d98..d1df8` | 96 | `7f3e2bdeb3b04a1ac6b30887b14a028b91aeacb4be747394c976042980d85097` | 4 | 표 자식 `d1d98` `d1dc8` |
| `d1e58..d1e6e` | 22 | `8a08615d702ab294c75ed7f7e58ca706657fcdc4b5914d60aadb119dbac1d03f` | 2 | 공통 꼬리 |
| `d22e6..d232c` | 70 | `b5698907e85862a81429acc6464a4f50f9692e94f1d5a8ad0892358aa56b9f93` | 3 | 표 자식 `d22e6` |
| `d239c..d23d8` | 60 | `c1c532aa7ec2e5402779a7a0a37638eb5b427b17337ef709957c759403faaaf8` | 9 | 공통 꼬리, 설치 callback `d23b2` |
| `d3c2a..d3c40` | 22 | `47978cf129f85e0baa3ff47cd06753e206c09fe86bb3456bfc7531dc016265eb` | 4 | helper `d3c2a` |
| `dceca..dcf42` | 120 | `dd3377b96218c93df25e9424e83b63a5ca99e8e17d74a8a47c3df620e3030698` | 16 | callback `dceca` |

- [F] 참조: `bdcc6` LONG `e8f98`(stage event 표, 앞뒤 `bdb56` `be03e`), `c5e6c` LONG `e9018` `e901c`, `c5fd8` LONG `e9028`(뒤 `c6a90`), `dceca` LONG `dcf50`(뒤 WORD `ffff`). 설치 대상(`bdd3e` `bdd8a` `bde50` `bdea0` `bdf40` `d23b2` `dcef8` `dcf22`)은 이 단위 안의 `MOVE.L #imm,(A6)`만 참조한다. `d1cd8`은 LONG 표 `c6012`와 다른 단위의 `MOVEA.L #d1cd8,A0` 등(`54414` `60620` …)이, `d1d38`은 U16 `bbea2`(2986 자식) 등이 참조한다.

## block 목록과 실행 의미

[F] 128 block. 각 줄은 block 안 명령 전체다. "(→x)"는 fall-through다. d16(An)은 부호확장한다. `.W`/`.B` 연산은 나머지 bit를 보존한다. `(An,Dn.W)`의 index WORD는 부호확장한다. `CMPA.W #0,An`은 32bit 비교다. `MOVEM.L D0-D3/A1,(A0)`은 A0부터 D0 D1 D2 D3 A1 순서로 LONG 5개를 쓰고 A0를 바꾸지 않는다.

**helper `1a3ae` 5**
- `1a3ae`: `CMPI.W #8,D0; BCS.W 1a3b8` / `1a3b6`: `MOVEQ #8,D0` (→`1a3b8`)
- `1a3b8`: `TST.W 5408(A5); BPL.W 1a3c2` / `1a3c0`: `NEG.W D0` (→`1a3c2`)
- `1a3c2`: `MOVE.W D0,5408(A5); RTS`

**화면 범위 검사 `1ab80` 9** (U05 `1ab02`와 같은 꼴, 경계는 A6 WORD `46`/`42` 단독)
- `1ab80`: `MOVE.L (A0)+,D0; MOVE.L (A0)+,D1; BTST.B #1,15(A6); BEQ.W 1ab92` / `1ab8e`: `ADD.W D1,D0; NEG.W D0` (→`1ab92`)
- `1ab92`: `MOVE.W 46(A6),D2; ADD.W D0,D2; CMPI.W #200,D2; BGT.W 1aafc` / `1aba0`: `ADD.W D1,D2; CMPI.W #100,D2; BLT.W 1aafc`
- `1abaa`: `SWAP D0; SWAP D1; BTST.B #0,15(A6); BEQ.W 1abbc` / `1abb8`: `ADD.W D1,D0; NEG.W D0` (→`1abbc`)
- `1abbc`: `MOVE.W 42(A6),D2; ADD.W D0,D2; CMPI.W #140,D2; BGT.W 1aafc` / `1abca`: `ADD.W D1,D2; CMPI.W #0,D2; BLT.W 1aafc`
- `1abd4`: `ANDI.B #fe,CCR; RTS` (C Clear 생산)

**helper `49214` 2**
- `49214`: `SWAP D0; CLR.W D0; SWAP D1; CLR.W D1; MOVE.L D0,D2; MOVE.L D1,D3; ADD.L 42(A6),D0; ADD.L 46(A6),D1; ADD.L 4a(A6),D2; ADD.L 4e(A6),D3; LEA 538e(A5),A1; SUB.L 14(A1),D0; SUB.L 18(A1),D1; SUB.L 1c(A1),D2; SUB.L 20(A1),D3; SUB.L D0,D2; SUB.L D1,D3; NEG.L D2; NEG.L D3; LEA 2e(A0),A0; MOVEM.L D0-D3/A1,(A0); JSR 43e38.L`
- `4925a`: `SUBA.W #2e,A0; RTS`

**callback `bdcc6` 62**
- `bdcc6`: `MOVEA.L #bdec4,A0; MOVE.W #a,D0; JSR 28ae.L` / `bdcd6`: `MOVEA.L #bdedc,A0; MOVE.W #a,D0; JSR 28ae.L`
- `bdce6`: `MOVE.W 76(A6),D0; EXT.L D0; LSL.L #8,D0; MOVE.L D0,7a(A6); MOVE.W #1,68(A6); MOVE.W #1,1e(A6); MOVE.W #76,D0; MOVE.W #17,D1; MOVE.B #0,D2; JSR c6a96.L`
- `bdd10`: `LEA 26(A6),A0; MOVE.W #21b,20(A6); MOVE.L 2001dc.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 5c(A1),A1; JSR 49f8c.L` (bank)
- `bdd38`: `MOVE.L #bdd3e,(A6)` (→`bdd3e`) / `bdd3e`: `JSR 43e34.L` / `bdd44`: `JSR 49fc6.L`
- `bdd4a`: `LEA 10b1d6.L,A1; TST.L c(A1); BEQ.W bdd72` / `bdd58`: `CMPI.W #270,5418(A5); BLT.W bdd6c` / `bdd62`: `MOVE.W #732,D0; JSR 3af8.L`
- `bdd6c`: `MOVE.L #bdd8a,(A6)` (→`bdd72`) / `bdd72`: `LEA be1dc.L,A0; JSR 1ab02.L` / `bdd7e`: `BCC.W bdd88`(C 소비) / `bdd82`: `JMP 2a00.L` / `bdd88`: `RTS`
- `bdd8a`(설치): `MOVE.W 46(A6),D0; MOVE.L 7a(A6),D1; MOVE.W 78(A6),D2; ADDI.W #100,D2; SUB.W D0,D2; BNE.W bddb4`
- `bdda0`: `CMPI.W #32a,5418(A5); BLT.W bddb0` / `bddaa`: `MOVE.L #bde50,(A6)` (→`bddb0`) / `bddb0`: `BRA.W bde2c`
- `bddb4`: `BPL.W bddf6`(N 재계산) / `bddb8`: `NEG.W D2; CMPI.W #1,D2; BGT.W bddd6`
- `bddc2`: `MOVE.L #0,3a(A6); ANDI.L #ffff0000,32(A6); BRA.W bddf2`
- `bddd6`: `SUB.W 7a(A6),D2; BPL.W bddec` / `bddde`: `MOVE.L 3a(A6),D3; ASR.L #3,D3; SUB.L D3,3a(A6); BRA.W bddf2` / `bddec`: `NEG.L D1; MOVE.L D1,3a(A6)` (→`bddf2`) / `bddf2`: `BRA.W bde2c`
- `bddf6`: `CMPI.W #1,D2; BGT.W bde12` / `bddfe`: `MOVE.L #0,3a(A6); ANDI.L #ffff0000,32(A6); BRA.W bde2c`
- `bde12`: `SUB.W 7a(A6),D2; BPL.W bde28` / `bde1a`: `MOVE.L 3a(A6),D3; ASR.L #3,D3; SUB.L D3,3a(A6); BRA.W bde2c` / `bde28`: `MOVE.L D1,3a(A6)` (→`bde2c`)
- `bde2c`: `JSR 43ea4.L` / `bde32`: `JSR 49fc6.L` / `bde38`: `LEA be1dc.L,A0; JSR 1ab02.L` / `bde44`: `BCC.W bde4e`(C 소비) / `bde48`: `JMP 2a00.L` / `bde4e`: `RTS`
- `bde50`(설치): `MOVE.W #733,D0; JSR 3af8.L`
- `bde5a`: `MOVE.L #0,36(A6); MOVE.L #0,3a(A6); ANDI.L #ffff0000,32(A6); LEA 26(A6),A0; MOVE.W #21b,20(A6); MOVE.L 2001dc.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 5c(A1),A1; JSR 49f8c.L` (bank)
- `bde9a`: `MOVE.L #bdea0,(A6)` (→`bdea0`) / `bdea0`: `JSR 43e34.L` / `bdea6`: `JSR 49fc6.L` / `bdeac`: `LEA be1dc.L,A0; JSR 1ab02.L` / `bdeb8`: `BCC.W bdec2`(C 소비) / `bdebc`: `JMP 2a00.L` / `bdec2`: `RTS`
- `bdec4`(자식): `LEA bdfdc(PC),A0; MOVE.L A0,7e(A6); MOVE.W #88,D0; MOVEQ #10,D1; JSR 49290.L` / `bded8`: `BRA.W bdef4`
- `bdedc`(자식): `LEA bdf82(PC),A0; MOVE.L A0,7e(A6); MOVE.W #ff78,D0; MOVEQ #10,D1; JSR 49290.L` / `bdef0`: `BRA.W bdef4`
- `bdef4`: `MOVE.W #76,D0; MOVE.W #18,D1; MOVE.B #0,D2; JSR c6a96.L`
- `bdf06`: `MOVE.W #0,68(A6); MOVE.W #0,1e(A6); LEA 26(A6),A0; MOVE.W #21b,20(A6); MOVE.L 2001dc.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 60(A1),A1; JSR 49f8c.L` (bank)
- `bdf3a`: `MOVE.L #bdf40,(A6)` (→`bdf40`) / `bdf40`: `JSR 43e34.L`
- `bdf46`: `LEA 10b1d6.L,A1; CMPI.L #80000,c(A1); BLT.W bdf5e` / `bdf58`: `JSR 49fc6.L` / `bdf5e`: `JSR 288c.L` / `bdf64`: `BCS.W bdf6e`(C 소비) / `bdf68`: `JMP 2a00.L`
- `bdf6e`: `MOVEA.L 7e(A6),A0; CMPA.W #0,A0; BEQ.W bdf80` / `bdf7a`: `JSR 4706c.L` / `bdf80`: `RTS`

**callback `c5e6c` 2 / `c5fd8` 4**
- `c5e6c`: `MOVE.W 76(A6),D0; JSR 1a3ae.L` / `c5e76`: `JMP 2a00.L`
- `c5fd8`: `LEA c6012(PC),A1; MOVE.W 76(A6),D0; ADD.W D0,D0; ADD.W D0,D0; MOVEA.L (A1,D0.W),A0; MOVE.W #1e,D0; JSR 28ae.L` / `c5ff2`: `BCC.W c600c`(C 소비)
- `c5ff6`: `MOVE.W 78(A6),68(A0); MOVE.W 78(A6),1e(A0); MOVEQ #0,D0; MOVEQ #0,D1; JSR 49214.L` / `c600c`: `JMP 2a00.L`

**표 자식 `d1cd8` `d1d08` `d1d38` `d1d98` `d1dc8`(각 2)와 공통 꼬리 `d1e58` 2**
- `d1cd8`/`d1d08`/`d1d38`/`d1d98`/`d1dc8`: `LEA 26(A6),A0; MOVE.W #d2,20(A6); MOVE.L 20008c.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L k(A1),A1; JSR 49f8c.L`(k = `4` `8` `c` `40` `40`; bank)
- `d1d00`/`d1d30`/`d1d60`/`d1dc0`/`d1df0`: `LEA r(PC),A0; BRA.W d1e58`(r = `d3e5c` `d3e54` `d3e64` `d3e5c` `d3e5c`)
- `d1e58`: `MOVE.L A0,92(A6); MOVE.W #cec,D0; MOVE.B #0,D1; JSR 8ebe.L` / `d1e6a`: `BRA.W d239c`

**표 자식 `d22e6` 3과 공통 꼬리 `d239c` 9**
- `d22e6`: `MOVE.W #24,D0; MOVE.W #6,D1; MOVE.B #0,D2; JSR c6a96.L`
- `d22f8`: `LEA 26(A6),A0; MOVE.W #e2,20(A6); MOVE.L 200094.L,22(A6); MOVE.W #100,D0; LEA 26(A6),A0; MOVEA.L 22(A6),A1; MOVEA.L 18(A1),A1; JSR 49f8c.L` (bank)
- `d2320`: `MOVE.L #d3e8c,92(A6); BRA.W d23a0`
- `d239c`: `JSR d3c2a(PC)`
- `d23a0`: `BCLR.B #1,15(A6); MOVE.B #ff,17(A6); MOVE.L #d23b2,(A6)` (→`d23b2`)
- `d23b2`(설치): `JSR 43e34.L` / `d23b8`: `JSR 49fc6.L` / `d23be`: `BCS.W d23d2`(C 소비)
- `d23c2`: `MOVEA.L 92(A6),A0; JSR 1ab80.L` / `d23cc`: `BCS.W d23d2`(C 소비) / `d23d0`: `RTS` / `d23d2`: `JMP 2a00.L`

**helper `d3c2a` 4**
- `d3c2a`: `JSR 49a58.L` / `d3c30`: `ANDI.B #2,D0; BNE.W d3c3e` / `d3c38`: `BCHG.B #0,15(A6)` (→`d3c3e`) / `d3c3e`: `RTS`

**callback `dceca` 16**
- `dceca`: `CMPI.B #1,100012.L; BEQ.W dcf16`
- `dced6`: `MOVE.W #73a,D0; JSR 3af8.L` / `dcee0`: `JSR 48296.L` / `dcee6`: `JSR 1c5b0.L` / `dceec`: `JSR 49c66.L`
- `dcef2`: `MOVE.L #dcef8,(A6)` (→`dcef8`) / `dcef8`(설치): `CMPI.W #198,5418(A5); BGE.W dcf04` / `dcf02`: `RTS`
- `dcf04`: `JSR 482c0.L` / `dcf0a`: `JSR 49c32.L` / `dcf10`: `JMP 2a00.L`
- `dcf16`: `MOVE.W #294,76(A6); MOVE.L #dcf22,(A6)` (→`dcf22`) / `dcf22`(설치): `SUBQ.W #1,76(A6); BCS.W dcf2c` / `dcf2a`: `RTS`
- `dcf2c`: `MOVEA.L #4841a,A0; MOVE.W #a,D0; JSR 28ae.L` / `dcf3c`: `JMP 2a00.L`

(수: 5 + 9 + 2 + 62 + 2 + 4 + 12 + 12 + 4 + 16 = 128.)

## 구현 범위와 규약

- routing 13 범위(위 표). 짝수 PC 750개 중 block 시작 128, 내부 622. 내부 PC 직접 진입은 `unsupported animation objects n05 PC`다.
- **FLOW_ONLY 60개**(C 보존): `4925a` `bdd3e` `bdd44` `bdd72` `bdd7e` `bdd82` `bdd88` `bddb0` `bddb4` `bddf2` `bde2c` `bde32` `bde38` `bde44` `bde48` `bde4e` `bdea0` `bdea6` `bdeac` `bdeb8` `bdebc` `bdec2` `bded8` `bdef0` `bdf40` `bdf58` `bdf5e` `bdf64` `bdf68` `bdf7a` `bdf80` `c5e76` `c5ff2` `c600c` `d1d00` `d1d30` `d1d60` `d1dc0` `d1df0` `d1e6a` `d239c` `d23b2` `d23b8` `d23be` `d23c2` `d23cc` `d23d0` `d23d2` `d3c2a` `d3c38` `d3c3e` `dcee0` `dcee6` `dceec` `dcf02` `dcf04` `dcf0a` `dcf10` `dcf2a` `dcf3c`.
- **known carry 생산 1개**: `1abd4` Clear.
- 그 밖 67개는 Unknown(`MOVE`/`MOVEQ`/`CLR`/`TST`/`CMP`/`CMPI`/`CMPA`/`ADD`/`ADDI`/`SUB`/`SUBQ`/`NEG`/`ASR`/`LSL`/`EXT`/`SWAP`/`ANDI`/`BCLR`+`MOVE` block, `MOVE.L #imm,(A6)` block, `MOVEA`+`MOVE.W`+`JSR 28ae` block).
- **소비자 7개**(`bdd7e` `bde44` `bdeb8` `bdf64` `c5ff2` `d23be` `d23cc`). Unknown이면 `objects n05 caller requires known carry`(상태 보존).
- 스택: JSR 복귀 LONG만. I/O port 쓰기·bank 변경 없음. 홀수 주소 WORD/LONG(예: 홀수 A6/A0, 홀수 표 LONG), work RAM 밖 쓰기(예: `28ae` 실패 node `100e98`는 work RAM이라 허용), 미해결 ROM/bank 읽기는 기존 checked 오류다.

## 의존·경계

- [F] N05 → 기존: 위 "나가는 호출" 목록. 실행부 없는 경계 없음.
- [F] 다른 단위 → N05: stage event 표·LONG 목록(`e8f98` `e9018` `e901c` `e9028` `dcf50`), U15 `af25a`·U16 `bbebe` `bbeec`(`49214`), U15 `af402`(`d3c2a`). 그 test는 `49214`/`d3c2a`에서 멈춤만 확인하므로 N05 뒤에도 같다.

## 자연 시작 상태(읽기 전용 기록)

- [F] 기준 C++ 차분(이 작업 트리 `20a3574`, 현재 `tools/verify_animation_machine_scheduler_f4.py`·`_rng_f4.py`를 scratch 출력으로 실행): base 일치 pass 12,418·node 96,490, 불일치 0, 자연 완주 113 seed(seed 28·29의 첫 미연결 callback `dceca`, frame 0). RNG 초기화 400 frame: 일치 pass 36,800·node 264,687, 불일치 0, complete 92(SHA256 `810d0f687e1665564fa5c2283a50992f181e8ed4e46a7071c217daf0f5ab840c`).

- [F] 작업자 scratch 측정(구현 후, 같은 도구): base 일치 pass 12,488·node 97,198, 불일치 0, 자연 완주 115(새 완주 28 29, 회귀 0; 두 seed는 native 끝 frame 35의 guard `stage area RNG pointer outside work RAM`에서 C++도 같은 checked 오류). RNG 초기화 400 frame: 일치 pass 37,600·node 271,361, 불일치 0, complete 94(새 complete 28 29, 잃은 것 0; SHA256 `5160e714b7d23e1171afc6d966d1ece50fa7f62b23f7385d4f0b7264bdc82348`).
- [F] 실제 ROM 차분(scratch `realrom/real.py`, 시드 1·2·3 각 1,000 case, bank `200000`/`300000`): 불일치 0, 128/128 시작 도달, 실제 생산자 뒤 소비자 native 분기 비교 `bdd7e` 209 `bde44` 530 `bdeb8` 59 `bdf64` 415 `c5ff2` 194 `d23be` 349 `d23cc` 27. native가 깨끗이 멈추지 않은 case(무작위 RAM의 interpreter 경로가 `<400` PC로 가거나 멈추지 않음)는 건너뛰고 셌다(시드별 355~412). `bddb4` 직접 진입은 SR N = D2 bit 15로 선언한다(결정 4).
- [F] 단위 test `animation_machine_objects_n05_test`: 337 fixture(checked 오류 16, known C 유지 133), 128 block × 3 carry, 내부 622 PC, `make -j4 all test` 종료 0·경고 0, UBSan 통과.

## 검증 조건(최소)

- `make -j4 all test` 종료 0, 경고 0, Assert 없음. 새 test의 UBSan 실행.
- 단위 test(`run_animation_machine`만): 128 시작 모두 도달, 시작마다 3 carry로 한 block 후계와 carry 분류, zero-step, 내부 622 PC 정확한 오류, 홀수 PC, rollback 탐침은 RAM `10fe00..10fefe`만, 범위 밖 이웃(`1a3ac` `1abda`… 중 routing 밖인 것, `d1d68` `d1df8` `d232c` `c6012` `bdf82` `dcf42`)은 `unsupported animation machine PC`, 소비자 7개 Unknown 오류, 생산자 `1abd4` Clear, `d23cc`가 실제 생산자 `1ab80`을 지나는 typed fixture, 소비자 C는 실제 생산자(`1ab02` `288c` `28ae` `49fc6` `1ab80`)를 지나는 실제 ROM 차분의 native 분기로 확인. 자연에 없는 길은 typed fixture(Unicorn, work RAM 입력과 합성 bank·fixed 바이트)로 비교한다.
- 실제 ROM 차분: callback과 모든 시작을 실제 program ROM resource로 C++와 Unicorn에서 같은 결과로 실행한다(bank `200000`/`300000`).
- 차분(F2 프레임 패스, 142 seed): 불일치 0, 회귀 0, seed 28·29 완주. RNG 초기화 400 frame 차분: 불일치 0, seed 28·29 complete.

## 미확인·범위 밖

1. [I] `dceca`는 `100012`가 1이 아니면 효과음 `73a`와 U01/area clear/input 준비 뒤 `5418(A5)` ≥ `198`을 기다려 정리하는 진행 객체, 1이면 `294` frame 뒤 `4841a` 자식을 만드는 객체로 보인다. `bdcc6`은 좌우 자식 두 개(`bdec4` `bdedc`, `49290` 오프셋 ±`88`)를 둔 이동 객체로 `78`+`100`(목표 Y)에 다가간다(`3a` 속도, `ASR.L #3` 감쇠). 게임 의미는 미확인이다.
2. [I] `c5fd8`은 `76(A6)`로 고른 표 자식(`c6012`)을 하나 만들고 `78`을 팔레트(`68` `1e`)로 넘긴 뒤 `49214`로 위치를 복사한다. `49214`는 D0/D1 WORD 오프셋을 더한 node 좌표(`42` `46` `4a` `4e`)에서 카메라(`538e(A5)+14..+20`)를 뺀 값을 자식 `2e..42`에 둔다. [U] 표 entry 6~9 자식(`d216a` 등)과 `4841a`는 이 단위 밖이다.
3. [U] 참조 없는 `d1d68` `d1df8` `d1e28` `d232c`의 목적.

작업자 scratch: `/Users/start/Workspce/ms5-scratch/n05/`(`n05.py` block·범위·SHA 계산, `n05dis.py` `hroute.py` `owner.py` `refs.py` `probes.py` `dynreach.py`, `fp/` 기준·새 프레임 패스 차분; 저장소 밖).
