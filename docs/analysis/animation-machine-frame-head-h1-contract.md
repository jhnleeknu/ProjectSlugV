# F5 frame head H1: head 본문 `e4a`/`e74`와 flush·배경·기타 helper 계약 초안

**상태: 계약 초안(원본 바이트 근거, 메인 결정 전). 아래 "작업자 검증 기록"만 구현 뒤 scratch 기록이다.**

범위 근거는 F5 범위 문서(`animation-machine-frame-head-f5-scope.md`, 작업 트리 사본 SHA256 `642e2cc5e52db3f27bb532a4fc66d3ce13e990fdf299bf6d07229fe305a00f60`, `metalslug-f4` 작업본(관측 정정 절 포함) SHA256 `b37ce2ca8bf151b43c5823d694161b67ba804e80b801b9c5017cdbc071d48924`)의 §4 H1 행이다: `e4a..1000` `b68..bb4` `3c08..3c40` `16bba..16cf8` `166bc..16bb8` `1ae56..1aeb2` `1879c..187d6` `903a..9054` `9546..955c` `8bc8..8bde` `8be0..8c14` `3db2..3dca` `43dbc..43dca`, 약 120 block, 위험 pause 루프·TRAP·raster clamp·`SUBX`. 메인 결정 D1~D10(범위 문서 머리)이 구속한다. native 관측은 `animation-machine-frame-head-observation.md`(SHA256 `c03587b582edf384c7a96a98d2087af5ba6f5ad59b11e1de0ea45894f5e511ab`)와 그 도구(`tools/observe_animation_machine_frame_head.py`, `metalslug-f4` 작업본 SHA256 `1b6cd5bddbd55ce685ce96c888b0facc74070c09ab42cdfff1e7ebe644c4df59`), 산출 `observation.json` SHA256 `dbb631a8008a6da7ea6055dc9db7ea12aaeda01d557f471f1f0e8dc41ff915a0`(scratch `ms5-scratch/f5obs/out/…`, 읽기 전용)이다. 단위 형식과 규약은 F4 N26 계약(`animation-machine-objects-n26-contract.md`)과 F2 계약(`animation-machine-scheduler-shell-f2-contract.md`)을 따른다.

메인 작업 지시(요약):
- 계약을 먼저 쓴다. block 목록은 F4와 같은 정적 leader 규칙으로 정한다. H2~H7이 맡을 곳(writer 표 `ce62`/`11792`, palette `5728`, 입력 sampler `31d6`, pause/menu `9136`)은 stop-only 경계다.
- Waiting·external read·port 모델은 기존 Waiting/status 어휘와 맞춰 최소로 넣는다. public header 변경은 피하고, 피할 수 없으면 바꾸지 말고 결정으로 보고한다.
- TRAP·guard는 checked 오류다. D1 frame driver(H → skip → N)는 작고 시험에 필요할 때만 넣는다.

- 결정 3(관례): block 시작은 정적 디코드(진입, 분기 대상, 조건분기 fall-through, JSR/BSR 복귀점, 범위 안 `MOVE.L #imm,(A6)` 설치점)로 정한다. Unicorn TB 분할은 시작이 아니다. 연속 Bcc 묶음은 H1에 없다.
- 결정 5(관례): 단위는 함수 본문 전체다. 다른 단위의 PC와 범위 밖 callee는 그 단위 실행부로 간다(이미 routing된 callee는 기존 실행부, 미routing callee는 경계).
- U01~N29 수용 관례: CCR을 바꾸지 않는 명령(`LEA`/`MOVEA`/`ADDA`/`JSR`/`BSR`/`BRA`/`RTS`/Bcc)과 Z만 바꾸는 `BTST`/`BSET`/`BCLR`만인 block은 FLOW_ONLY다. 그 밖의 block은 Unknown이다.

Claude Opus 5.5 / high 작업자가 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, `extracted/program/maincpu.decrypted.be.bin`, 8 MiB, mtime `1791291625`)을 capstone M68000으로 디코드했다. H1 코드는 모두 fixed `<100000`이라 CPU 주소와 file offset이 같다. 기존 routing은 작업 트리 `/Users/start/Workspce/metalslug-h1`(base `77e5485` = F4 continuation, `engine/src/animation_machine.cpp` SHA256 `2c38c9ca8db177eb83bf0c6177f253c028f5b7d3fe84758ad99abf1db703637e`, routing 규칙 85개, `engine/include/ms5/animation_machine.h` SHA256 `16092fb9479f1f72f883816e0c9f3e25914d1d56a071208ba800d0ed5b732734`)을 참조했다. H1 범위의 짝수 PC는 기존 routing에 없다. [F]=원본 바이트, 기록 산출물 또는 작업자 scratch 재생에서 확인한 사실, [I]=추론, [U]=미확인. block 목록은 scratch `ms5-scratch/h1/h1dec.py`(정적 디코드, `starts.txt` SHA256 `6986d31107c545da63a03d52853d380d38b2fd3ee99eb721f71379d9468629be`)가 원본 opcode에서 독립 계산했다.

## 요약

- [F] **정적 leader 121개 = routing block 120 + TRAP 경계 1(`fee`).** 진입 14개(아래)에서 분기·fall-through를 끝까지 따라간 closure이고, 범위 안 명령 889개 중 888개를 덮는다. 미도달은 `fb8 BRA.W fe2`(4바이트, 참조 없음) 하나다. 범위 문서의 "120"과 같다(`fee` 제외).
- [F] 진입: head callback `e4a`(scheduler 설치 `268e`의 LONG, 첫 frame), `e74`(`e6e MOVE.L #e74,(A6)` 설치점이며 이후 frame), 그리고 head 안 호출 대상 `b68`(`f2a`) `3c08`(`e86`) `16bba`(`e8c`) `166bc`(`16bc8 JSR d(PC)`) `1ae56`(`e92`) `1879c`(`1ae72` 외 3) `903a`(`e68`) `9546`(`9050 BSR`) `8bc8`(`f94`) `8be0`(`fd6`) `3db2`(`f70`) `43dbc`(`ffa`). [F] fixed ROM 전체의 분기·JSR·LONG 참조 탐색(scratch `h1xref.py`)에서 H1 함수로 들어오는 범위 밖 호출은 없다(LONG `e4a`/`e74` 설치값과 우연 자료 일치뿐). 따라서 H1 RTS 앞 C를 읽는 외부 소비자도 없다.
- [F] **경계(H1이 실행하지 않는 곳, stop-only):** `31d6`(H2 입력 sampler, `f24`), `9136`(H2 pause/menu, `f54`), `5728`(H3 palette, `e9e` `f46` `fae`), writer 표 JSR `16c48 JSR (A3,D7.W)`(A3=`ce62`, H8)·`16cc8 JSR (A3,D7.W)`(A3=`11792`, H4)의 live 대상, `fee TRAP #15`, controller 진입 `JSR (A0)` 대상 LONG `(1008e4)`(`c52a`, D1/D9). 이미 routing된 callee 9개: `e7bf4`(palette_bind) `9056`(area_clear) `3ac8`(sound, `BSR`) `ce02`(objects U04) `3a70`(objects U02) `3d7e`(script_placement) `8bbc`(cleanup) `8c16`(exit), 그리고 head RTS 뒤 dispatcher `2ac2..2ac6`/`2ab8..2ac0`(fade_card).
- [F] **자연 H에서 H1이 닿는 곳:** frame 1은 `e4a`→`e7bf4`→`e50`→`903a`(→`9056` `9546`)→`e6e`→`e74`, 이후 frame은 `e74`→`3c08`(→`3ac8`)→`16bba`(→`ce02` `166bc`)→`16bd0`(대기)→`16bd6`→(sprite 큐가 비지 않으면) 역방향 writer 표 `11792+4k`(H4) 또는 (비면) `16cce`→`16ce6`→`e92`→`1ae56`(→`1879c` ×4)→`e98`→`5728`(H3). [I] 따라서 H1만으로는 자연 H가 끝나지 않는다. 첫 경계는 writer 표 또는 `5728`이다. `ea4` 이후(raster 읽기, vblank 대기, `31d6`/`9136` 호출, pause, TRAP, `ff0`..`1000`, controller 진입)는 typed fixture와 실제 ROM 차분으로만 덮는다.
- [F] **carry:** 소비 block 0, known 생산 0, FLOW_ONLY 34, guard 4, Unknown 82. 34 + 4 + 82 = 120. X를 읽는 `SUBX.W`(`187ac` `187b0`)의 X는 같은 block의 `LSR.B`(`187aa` `187ae`)가 만든다. N/Z 재계산 없음.
- [F] I/O: port 쓰기 `3c0004` WORD·`3c0000` LONG(`e74`), PVC `2ffff2`/`2ffff0`(`1ae56` `1ae9c` `16c4e` `16cce`, bank 변경). device 읽기는 raster `3c0006` WORD 2곳(`eaa`, `efc`)뿐이다(입력 `300000`/`340000`/`380000`은 H2 `31d6` 안).
- [F] 대기 2곳: `ef2`(vblank, D2)와 `16bd0`(sprite flush, D5). 기존 sound 대기 `3aea`(D6)는 `3c22`/`3c2c`가 부르는 `3ac8` 안에서 기존 실행부가 낸다.
- [F] 기준(`77e5485`)에서 H1 함수는 frame head(`100820`)에서만 불리고, F2 pass는 그 callback 진입에서 멈춘다. [I] 따라서 H1 routing은 기존 N pass(F2~F4 frame pass·RNG 400)의 결과를 바꾸지 않는다(검증 기록에서 확인).

## 메인 결정 필요 항목 (MAIN DECISION NEEDED)

1. **범위 120 block, routing 13 범위, `fee`·`fb8` 제외.** [F] routing은 `b68..bb6` `e4a..fb8` `fbc..fee` `ff0..1002` `3c08..3c42` `3db2..3dcc` `8bc8..8c16` `903a..9056` `9546..955e` `166bc..16cfa` `1879c..187d8` `1ae56..1aeb4` `43dbc..43dcc`다. `fee TRAP #15`는 F3 TRAP(`stage_event_ops_trap`)과 같은 실행부 없는 경계(D8)라 routing 밖(`unsupported animation machine PC`, stop이면 직전 상태로 멈춤)이다. `fb8 BRA.W fe2`는 참조 없는 코드라 routing하지 않는다(N26 관례). 범위 이웃 `3dcc RTS`(참조 없음)도 routing 밖이다.
2. **external read queue(D3/D4)는 현재 public API로 표현할 수 없다 → public header 변경 제안(미적용).** [F] `run_animation_machine`의 입력 채널은 RAM, 레지스터·PC·C, PVC·bank, stop PC, BYTE `external_status`(`d00046` 전용)뿐이다. raster `3c0006`은 WORD이고 D3은 H당 2회의 선언 값 순서를 요구하므로 기존 채널로 값을 넣을 수 없다(RAM·상태에 값을 숨기면 원본에 없는 상태를 만든다).
   - 제안(메인 승인 시 적용): `ms5/animation_machine.h`에
     `struct AnimationMachineExternalRead {std::uint32_t address; std::uint32_t size; std::uint32_t value;};`를 두고 `AnimationMachineDevice`에 `std::vector<AnimationMachineExternalRead> reads;`(선언 queue, 앞에서부터 소비)를 더한다. 기본 생성은 빈 queue라 기존 호출자는 그대로 컴파일·동작한다. `am_read`는 `3c0006`/2, `300000`/1, `340000`/1, `380000`/1 읽기에서 queue 머리를 꺼낸다. 머리가 없으면 `animation machine external read queue empty`, 주소·크기가 다르면 `animation machine external read queue mismatch`(둘 다 상태 보존). 소비된 항목은 성공 commit 때만 queue에서 빠지고(`device` 교체), 수는 기존 `external_reads`에 더해진다. 실패하면 queue도 그대로다.
   - **이번 단위의 잠정 구현(헤더 변경 없음):** `ea4`·`efc` block은 원본 순서대로 실행하다가 `3c0006` 읽기에서 `animation machine external read queue empty`(checked 오류, 상태 보존)를 낸다. 이는 "빈 queue = checked 오류"(D3/D4)를 queue가 항상 빈 경우로 적용한 것이다. 제안이 승인되면 같은 문자열을 유지한 채 queue가 있을 때 값을 읽는다. `ebc` `f0e` 등 읽기 뒤 block은 지금도 구현·시험한다.
3. **Waiting 표현(새 status 없음).** [F] 기존 `AnimationMachineWaiting` + 대기 PC로 종류를 구분한다(기존 `cda4` sprite, `3aea` sound, `47af0`/`478de` gate와 같은 어휘).
   - `ef2`(D2 vblank): BYTE `-7fea(A5)`(=`100016`) < BYTE `-7fe9(A5)`(=`100017`)(부호 없는 BYTE)이면 **아무것도 바꾸지 않고** PC=`ef2` Waiting이다(native 관측의 "명령 전 정지"와 같다. D0은 아직 읽지 않은 값 그대로). 선언 해제는 host가 BYTE `100016` := BYTE `100017`을 쓰고 같은 PC에서 다시 부른다. 조건이 거짓이면 `D0.B` := BYTE `-7fea(A5)`, `efc`.
   - `16bd0`(D5 sprite flush): WORD `d34(A5)` ≠ `D0.W`이면 아무것도 바꾸지 않고 PC=`16bd0` Waiting이다. 선언 해제는 WORD `108d34` := `D0.W`(관측 도구와 같음; 자연 H에서 A5=`108000`). 같으면 `16bd6`.
   - Waiting으로 끝난 run은 성공 commit이다(그때까지의 RAM·port·bank 효과 포함). 대기 PC block은 FLOW가 아니므로 C는 Unknown이 된다.
4. **aux callback guard(D8).** [F] `f3c`(`MOVE.L A6,-(A7); MOVEA.L 7a(A6),A6; JSR (A0)`, `100896` ≠ 0일 때만)와 그 뒤 aux 경로 leader `f44`(`JSR (A0)` 복귀점) `f4c`(`TST.B 100016; BEQ f4c` 신호 대기) `f52`(`BRA f12`)는 실행하지 않고 `unsupported animation frame head aux callback`(상태 보존)이다. [F] `f44`~`f52`는 `f3c`의 레지스터 간접 호출을 거쳐야만 닿는다. [I] `100896`의 writer는 참조 없는 `e40`뿐이다(범위 문서 1.1).
5. **writer 표 JSR은 live 대상.** [F] `16c30`/`16cb2`: `D7.W` = ((BYTE `sne` & 4) | `D1.B`) × 4(16 bit), `D1` = WORD `6(A2)`의 bit 2를 지운 값. 대상 = A3 + sext(`D7.W`)(A3 = `ce62` 또는 `11792`), 복귀 `16c4c`/`16ccc`. `D1.B` ≥ 4이면 8항목 표를 넘는다. 표 항목·표 밖 착지의 routing은 표를 가진 H4/H8 계약이 정한다. H1은 JSR(복귀 LONG push, PC 설정)까지만 하고, 대상이 routing 밖이면 기존 `unsupported animation machine PC`(rollback)이다.
6. **D1 frame driver는 이번 단위에 넣지 않는다.** [I] 자연 H는 H1만으로 끝나지 않으므로(writer 표·`5728`에서 경계) C++ driver를 넣어도 자연 frame을 시험할 수 없다. H의 끝 규약(head `1000 RTS` → dispatcher `2ac2..2ac0` → `JSR (A0)`이 LONG `(1008e4)`로 옮기는 순간 stop)은 `run_animation_machine`의 stop PC = LONG `(1008e4)`(자연 `c52a`)로 표현되고 단위 시험에서 확인한다. 선언 skip(PC := `2ac2`, A7 += 4)과 N 연결은 H 단위가 다 모인 뒤(H3·H4 이후) driver 단위에서 계약한다.
7. **무효화 탐침(값만 교체).** [F] 기존 test가 "routing 밖"으로 쓴 H1 PC: `animation_machine_area_clear_test.cpp` outside `9054`(→ `10fe40`), `animation_machine_script_placement_test.cpp` outside `3db2`(→ `10fe42`). 각 test의 기존 `10fexx`와 겹치지 않는 work RAM PC로 바꾼다(주석 포함, 논리 변경 없음). `animation_machine_scheduler_test.cpp` `host()`의 마지막 행(head `e4a`, stop `e74`: "frame head는 실행부가 없다")은 H1 뒤 e4a가 실행되므로 head LONG을 RAM PC `10fe40`으로 바꾼다(같은 rollback 의미). `animation_machine_scene_update_test.cpp` `path_policy`의 opcode `1000`(계산 점프 대상 `19e8a+1000` = `1ae8a`, 이제 H1 내부 PC)은 대상이 계산값이라 RAM PC로 옮길 수 없으므로 같은 의미의 opcode `7ffc`(대상 `21e86`, routing 밖; 기존 `7ffe` 대상 `21e88`의 이웃)로 바꾼다. [F] Python 검증기 `tools/verify_animation_machine_script_placement.py`(ROUTED 끝 `3db2`, outside `3db2` `3db4`)는 수정하지 않고 무효화 목록으로 보고한다.
8. **실행부 파일·오류 문자열.** `engine/src/animation_machine_frame_head_h1.cpp`의 `animation_frame_head_h1_block`. 오류: `unsupported animation frame head h1 PC`(내부 PC), `unsupported animation frame head aux callback`(guard 4 block), `animation machine external read queue empty`(raster 읽기, 결정 2). carry 소비자가 없으므로 carry 오류 문자열은 없다.

## 원본 바이트 근거

[F] H1 코드 13 범위 2,494바이트(짝수 PC 1,247개, 시작 120, 내부 1,127). 연결 SHA256 `0627bee285b107fcae1aa2c5d58e0a90e6c100993c70aec460e50f57aa599adb`.

| CPU 범위 | 바이트 | SHA256 | 시작 |
| --- | --- | --- | --- |
| `b68..bb6` | 78 | `c6afaff86eb40180496f81ab15e88def01ab2a9a8907e8d460c093c2e6264e08` | 7 |
| `e4a..fb8` | 366 | `944abd83fc6ee6591ad6ac4eff2d89ab8384774373804ce187fa8f37b1eca666` | 36 |
| `fbc..fee` | 50 | `8549ada9f1a70d9e7cc69c7fe00d68a4cdee01c207f1de87383d4ae64758255c` | 6 |
| `ff0..1002` | 18 | `07f6afb48bc4414b663c3150be355619778b57423a215dff71c7b3232d492743` | 2 |
| `3c08..3c42` | 58 | `02db4a7f1258471d9fab89a69bb68d7f4c17c34ff00581f497f1774df6bd74e5` | 8 |
| `3db2..3dcc` | 26 | `ebff6b3b9dab1d2032ba74d7af535d209c24e5b42c8b6db327d6952570294788` | 3 |
| `8bc8..8c16` | 78 | `7d33d041088a02e3082c38d672b35ae8acee602e6785c03e9b8cf3ff0e411d0b` | 8 |
| `903a..9056` | 28 | `be0cfd85b9f845a98b99149a309541d4f33cc8157b7bf01796d4fd6579e04a87` | 3 |
| `9546..955e` | 24 | `a2ff9a8c47238dd25f025cb368550f1f10a4362476a90392d2533222df06c9da` | 3 |
| `166bc..16cfa` | 1598 | `7e1348605f9419b12d83e1fab70ee8eb2ade690e47aed1d4fac96481b6c68c6d` | 33 |
| `1879c..187d8` | 60 | `1d6e17c55df01f223a2539936ff2d9c6a1c5b55a7aec40f8d67201e9c4faa951` | 5 |
| `1ae56..1aeb4` | 94 | `1acdb5ea5058a5debadf5cb1cbb6867c514729fb5e53b2c82bbaaa8f121556a4` | 5 |
| `43dbc..43dcc` | 16 | `f97238e55cdf01fd572f18d33045b6bd3efad3070a8a44ef1a81dbf5b5b4b7e1` | 1 |

- [F] 범위 이웃: `fb8..fbc`(`60000028`, 미도달), `fee..ff0`(TRAP), `3dcc RTS`(참조 없음), 앞뒤 `b66` `bb6` `e48` `1002` `8bc6` `9038` `9544` `955e` `166ba` `16cfa` `187d8` `1ae54` `1aeb4` `43dba`는 routing 밖, `3c06`(sound 실행부 범위 `3ac8..3c08`) `3db0`(script_placement) `8c16`(exit) `9056`(area_clear) `1879a`(map_transfer) `43dcc`(cleanup)는 다른 실행부다.
- [F] 자료: `b58..c58`(`b78 LEA b58(PC),A1`의 BYTE 표; `TST.B (A1,D6.W)`의 색인 = (4 + BYTE(`10fdb6`+`D0.W`)) & `ff`, 0..255). 첫 16바이트 `00000001010001000001000000010100`. 색인 ≥ 16은 뒤의 `b68` 코드 바이트를 그대로 읽는다(원본과 같음, live bus). `d56`/`df0`은 `eda`가 `3a70` 인자로 넘기는 주소일 뿐 H1은 읽지 않는다.

## block 목록과 실행 의미

표기: `(→x)`는 조건 거짓(또는 직선) fall-through 시작. 태그: "FLOW"(C 보존), "guard", "Waiting", "raster 읽기"(결정 2). 태그 없는 block은 Unknown이다. d16(An)·`(An,Dn.W)`는 부호 확장한다. 긴 unrolled block은 처음·끝 명령만 적는다.

**BIOS mode·player mod `b68`(`f2a JSR`) 7**
- `b68`: `MOVE.B 10fdaf.l, 100012.l; LEA.L 10fdb6.l, a0; LEA.L b58(pc), a1; MOVEQ #0, d7; MOVE.B d7, 10f007.l; MOVE.W #3, d0` (→`b88`)
- `b88`: `BCLR.B d0, 10f006.l; BEQ.W b98` (→`b92`) — FLOW
- `b92`: `MOVE.B #1, (a0, d0.w)` (→`b98`)
- `b98`: `MOVE.W #4, d6; ADD.B (a0, d0.w), d6; TST.B (a1, d6.w); BEQ.W baa` (→`ba8`)
- `ba8`: `BSET.B d0, d7` (→`baa`) — FLOW
- `baa`: `SUBQ.W #1, d0; BCC.B b88` (→`bae`)
- `bae`: `MOVE.B d7, 10f007.l; RTS`

**head 본문 `e4a`..`1000` 44(+TRAP `fee`)**
- `e4a`: `JSR e7bf4.l` — FLOW
- `e50`: `MOVEQ #0, d0; MOVE.W d0, -7ff2(a5); MOVE.W d0, 7e(a6); MOVE.B #1, 84(a6); MOVE.L #0, 76(a6); JSR 903a.l`
- `e6e`: `MOVE.L #e74, (a6)` (→`e74`)
- `e74`: `MOVE.W #0, 3c0004.l; MOVE.L #82000000, 3c0000.l; JSR 3c08.l`
- `e8c`: `JSR 16bba.l` — FLOW
- `e92`: `JSR 1ae56.l` — FLOW
- `e98`: `BCLR.B #7, -7fe5(a5); JSR 5728.l` — FLOW
- `ea4`: `BSET.B #7, -7fe5(a5); MOVE.W 3c0006.l, d0; LSR.W #7, d0; SUBI.W #100, d0; BCC.W ebc` (→`eba`) — raster 읽기
- `eba`: `MOVEQ #0, d0` (→`ebc`)
- `ebc`: `SUB.B -7fe8(a5), d0; MOVE.B d0, -7fe8(a5)` (→`ec4`)
- `ec4`: `BTST.B #0, 10f000.l; BEQ.W ef2` (→`ed0`) — FLOW
- `ed0`: `CMPI.B #0, 84(a6); BEQ.W ef2` (→`eda`)
- `eda`: `MOVE.W #7066, d0; LEA.L d56(pc), a0; LEA.L 3650.l, a1; LEA.L df0(pc), a2; JSR 3a70.l`
- `ef2`: `MOVE.B -7fea(a5), d0; CMP.B -7fe9(a5), d0; BCS.B ef2` (→`efc`) — Waiting(vblank, D2)
- `efc`: `MOVE.W 3c0006.l, d0; LSR.W #7, d0; SUBI.W #100, d0; BCC.W f0e` (→`f0c`) — raster 읽기
- `f0c`: `MOVEQ #0, d0` (→`f0e`)
- `f0e`: `MOVE.B d0, -7fe8(a5)` (→`f12`)
- `f12`: `MOVE.B -7fea(a5), -7fe6(a5); MOVE.B #0, -7fea(a5); MOVE.W #0, -335e(a5); JSR 31d6.l`
- `f2a`: `JSR b68.l` — FLOW
- `f30`: `MOVEA.L 76(a6), a0; CMPA.W #0, a0; BEQ.W f54` (→`f3c`)
- `f3c`: `MOVE.L a6, -(a7); MOVEA.L 7a(a6), a6; JSR (a0)` — guard
- `f44`: `MOVEA.L (a7)+, a6; JSR 5728.l` — guard
- `f4c`: `TST.B -7fea(a5); BEQ.B f4c` (→`f52`) — guard
- `f52`: `BRA.B f12` — guard
- `f54`: `JSR 9136.l` — FLOW
- `f5a`: `MOVE.B 84(a6), d1; MOVE.B d0, 84(a6); BNE.W fbc` (→`f66`)
- `f66`: `CMPI.B #0, d1; BEQ.W f84` (→`f6e`)
- `f6e`: `MOVE.W d1, -(a7); JSR 3db2.l`
- `f76`: `MOVE.W d0, 82(a6); MOVEQ #0, d0; JSR 3d7e.l`
- `f82`: `MOVE.W (a7)+, d1` (→`f84`)
- `f84`: `CMPI.B #1, d1; BNE.W fae` (→`f8c`)
- `f8c`: `MOVEQ #0, d0; JSR 8bbc.l`
- `f94`: `JSR 8bc8.l` — FLOW
- `f9a`: `MOVE.B #ff, 80(a6); MOVEQ #fc, d0; MOVEQ #fc, d1; MOVEQ #fc, d2; MOVEQ #4, d3; JSR 8c16.l`
- `fae`: `JSR 5728.l` — FLOW
- `fb4`: `BRA.W ec4` — FLOW
- `fbc`: `CMPI.B #0, d1; BNE.W fe2` (→`fc4`)
- `fc4`: `MOVE.W 82(a6), d0; JSR 3d7e.l`
- `fce`: `TST.B 80(a6); BEQ.W fe2` (→`fd6`)
- `fd6`: `JSR 8be0.l` — FLOW
- `fdc`: `MOVE.B #0, 80(a6)` (→`fe2`)
- `fe2`: `MOVE.W 7e(a6), d0; CMP.W -7ff2(a5), d0; BEQ.W ff0` (→`fee`)
- (`fee`: `TRAP #f` — 경계, routing 밖)
- `ff0`: `ADDQ.W #1, d0; MOVE.W d0, -7ff2(a5); MOVE.W d0, 7e(a6); JSR 43dbc.l`
- `1000`: `RTS` — FLOW

**sound word flush `3c08`(`e86 JSR`) 8**
- `3c08`: `MOVE.W -3276(a5), d1` (→`3c0c`)
- `3c0c`: `CMP.W -3274(a5), d1; BEQ.W 3c3c` (→`3c14`)
- `3c14`: `LEA.L -327e(a5), a0; LEA.L (a0, d1.w), a0; TST.W (a0); BEQ.W 3c34` (→`3c22`)
- `3c22`: `MOVE.W d1, -(a7); MOVE.B (a0)+, d0; MOVE.B (a0)+, -(a7); BSR.W 3ac8`
- `3c2c`: `MOVE.B (a7)+, d0; BSR.W 3ac8`
- `3c32`: `MOVE.W (a7)+, d1` (→`3c34`)
- `3c34`: `ADDQ.W #2, d1; ANDI.W #6, d1; BRA.B 3c0c`
- `3c3c`: `MOVE.W d1, -3276(a5); RTS`

**`3db2`(`f70 JSR`) 3**
- `3db2`: `MOVEQ #0, d0; BTST.B #3, 104d91.l; BEQ.W 3dc2` (→`3dc0`)
- `3dc0`: `RTS` — FLOW
- `3dc2`: `MOVE.B 104d90.l, d0; ADDQ.W #1, d0; RTS`

**palette 사본 `8bc8`/`8be0`(`f94` `fd6`) 8**
- `8bc8`: `LEA.L 107dc2.l, a1; LEA.L 107dd6.l, a0` (→`8bd4`) — FLOW
- `8bd4`: `MOVE.W #14, d7` (→`8bd8`)
- `8bd8`: `MOVE.B (a1)+, (a0)+; SUBQ.W #1, d7; BNE.B 8bd8` (→`8bde`)
- `8bde`: `RTS` — FLOW
- `8be0`: `MOVE.B -23e(a5), d0; MOVE.B -23c(a5), d1; MOVE.B -23a(a5), d2; LEA.L 107dc2.l, a0; LEA.L 107dd6.l, a1; BSR.B 8bd4`
- `8bfa`: `TST.B -22c(a5); BNE.W 8c14` (→`8c02`)
- `8c02`: `MOVE.B #1, -22c(a5); MOVE.B d0, -23e(a5); MOVE.B d1, -23c(a5); MOVE.B d2, -23a(a5)` (→`8c14`)
- `8c14`: `RTS` — FLOW

**첫 frame 초기화 `903a`/`9546`(`e68` `9050`) 6**
- `903a`: `BSR.W 9056` — FLOW
- `903e`: `CLR.B 107dee.l; CLR.B 107df0.l; CLR.B 107df1.l; BSR.W 9546`
- `9054`: `RTS` — FLOW
- `9546`: `MOVE.B #0, -202(a5); MOVE.W #7, d7; MOVEQ #0, d0; LEA.L -201(a5), a0` (→`9556`)
- `9556`: `MOVE.B d0, (a0)+; DBRA d7, 9556` (→`955c`)
- `955c`: `RTS` — FLOW

**sprite 정렬 `166bc`(`16bc8 JSR`) 9**
- `166bc`: `MOVE.W d3a(a5), d0; SUB.W d36(a5), d0; BNE.W 166ca` (→`166c8`)
- `166c8`: `RTS` — FLOW
- `166ca`: `LEA.L f4e(a5), a4; MOVEQ #0, d0; … MOVEQ #0, d7; MOVEM.L d0-d7, -(a4)` ×16`; MOVE.W #1fe, d5; LEA.L -cc(a5), a0; LEA.L b34(a5), a1; MOVE.W d36(a5), d6; MOVE.W d3a(a5), d7` (명령 30개, →`16732`)
- `16732`: `MOVEQ #0, d0; MOVEQ #0, d1; MOVE.W (a1, d6.w), d2; MOVE.B (a0, d2.w), d0; MOVE.B 1(a0, d2.w), d1; ADD.W d0, d0; ADD.W d1, d1; ADDQ.B #1, (a4, d0.w); ADDQ.B #1, 1(a4, d1.w); ADDQ.W #2, d6; AND.W d5, d6; CMP.W d7, d6; BNE.B 16732` (→`16756`)
- `16756`: `MOVEA.L a4, a2; MOVE.W (a2)+, d7; (ADD.W (a2), d7; MOVE.W d7, (a2)+)` ×255`; ANDI.W #ff, d7; LEA.L f4e(a5), a2; MOVE.W d3a(a5), d6; MOVE.W d7, d4; SUBQ.W #1, d4` (명령 517개, →`16b66`)
- `16b66`: `SUBQ.W #2, d6; AND.W d5, d6; MOVE.W (a1, d6.w), d0; MOVEQ #0, d1; MOVE.B 1(a0, d0.w), d1; ADD.W d1, d1; SUBQ.B #1, 1(a4, d1.w); MOVEQ #0, d2; MOVE.B 1(a4, d1.w), d2; ADD.W d2, d2; MOVE.W d0, (a2, d2.w); DBRA d4, 16b66` (→`16b8a`)
- `16b8a`: `MOVE.W d7, d4; SUBQ.W #1, d4; ADD.W d7, d7; ADDA.W d7, a2; MOVE.W d36(a5), d6` (→`16b96`)
- `16b96`: `MOVE.W -(a2), d0; MOVEQ #0, d1; MOVE.B (a0, d0.w), d1; ADD.W d1, d1; SUBQ.B #1, (a4, d1.w); MOVEQ #0, d2; MOVE.B (a4, d1.w), d2; ADD.W d2, d2; ADD.W d6, d2; AND.W d5, d2; MOVE.W d0, (a1, d2.w); DBRA d4, 16b96` (→`16bb8`)
- `16bb8`: `RTS` — FLOW

**sprite flush `16bba`(`e8c JSR`) 24**
- `16bba`: `LEA.L 108000.l, a5; MOVEQ #0, d0; JSR ce02.l`
- `16bc8`: `JSR 166bc(pc)` — FLOW
- `16bcc`: `MOVE.W d36(a5), d0` (→`16bd0`)
- `16bd0`: `CMP.W d34(a5), d0; BNE.B 16bd0` (→`16bd6`) — Waiting(sprite flush, D5)
- `16bd6`: `LEA.L b34(a5), a0; MOVEA.L a0, a1; ADDA.W d36(a5), a0; ADDA.W d3a(a5), a1; TST.B d3c(a5); BPL.W 16c6a` (→`16bec`)
- `16bec`: `MOVE.L a6, -(a7); LEA.L 3c0000.l, a6; LEA.L d3e(a5), a4; MOVE.W (a4), 4(a4); LEA.L d46(a5), a4; MOVE.W (a4), 4(a4)` (→`16c04`)
- `16c04`: `CMPA.L a0, a1; BEQ.W 16c4e` (→`16c0a`)
- `16c0a`: `LEA.L -cc(a5), a2; ADDA.W (a0)+, a2; CMPA.L #108d34, a0; BNE.B 16c1c` (→`16c18`)
- `16c18`: `LEA.L b34(a5), a0` (→`16c1c`) — FLOW
- `16c1c`: `MOVE.W 6(a2), d1; LEA.L d3e(a5), a4; BCLR.B #2, d1; BEQ.W 16c30` (→`16c2c`)
- `16c2c`: `LEA.L d46(a5), a4` (→`16c30`) — FLOW
- `16c30`: `CMPI.W #ffff, 4(a2); SNE.B d7; ANDI.W #4, d7; OR.B d1, d7; ADD.W d7, d7; ADD.W d7, d7; LEA.L ce62.l, a3; JSR (a3, d7.w)`
- `16c4c`: `BRA.B 16c04` — FLOW
- `16c4e`: `MOVEA.L (a7)+, a6; MOVE.W #0, -7ff0(a5); MOVE.W #1000, 2ffff2.l; MOVE.W #0, 2ffff0.l; BRA.W 16ce6`
- `16c6a`: `MOVE.L a6, -(a7); LEA.L 3c0000.l, a6; LEA.L d3e(a5), a4; MOVE.W 2(a4), 6(a4); LEA.L d46(a5), a4; MOVE.W 2(a4), 6(a4)` (→`16c86`)
- `16c86`: `CMPA.L a0, a1; BEQ.W 16cce` (→`16c8c`)
- `16c8c`: `LEA.L -cc(a5), a2; CMPA.L #108b34, a1; BNE.B 16c9c` (→`16c98`)
- `16c98`: `LEA.L d34(a5), a1` (→`16c9c`) — FLOW
- `16c9c`: `ADDA.W -(a1), a2; MOVE.W 6(a2), d1; LEA.L d3e(a5), a4; BCLR.B #2, d1; BEQ.W 16cb2` (→`16cae`)
- `16cae`: `LEA.L d46(a5), a4` (→`16cb2`) — FLOW
- `16cb2`: `CMPI.W #ffff, 4(a2); SNE.B d7; ANDI.W #4, d7; OR.B d1, d7; ADD.W d7, d7; ADD.W d7, d7; LEA.L 11792(pc), a3; JSR (a3, d7.w)`
- `16ccc`: `BRA.B 16c86` — FLOW
- `16cce`: `MOVEA.L (a7)+, a6; MOVE.W #0, -7ff0(a5); MOVE.W #1000, 2ffff2.l; MOVE.W #0, 2ffff0.l` (→`16ce6`)
- `16ce6`: `MOVE.W d3a(a5), d0; MOVE.W d0, d36(a5); MOVE.W d0, d38(a5); MOVE.B #ff, d3d(a5); RTS`

**배경 좌표 snapshot `1ae56`(`e92 JSR`)·`1879c` 10**
- `1879c`: `MOVE.W 14(a0), d0; MOVE.W 18(a0), d1; MOVE.B 25(a0), d2; MOVEQ #0, d3; LSR.B #1, d2; SUBX.W d3, d0; LSR.B #1, d2; SUBX.W d3, d1; CMP.W 7c(a0), d0; BEQ.W 187c4` (→`187ba`)
- `187ba`: `MOVE.W d0, 7c(a0); BSET.B #7, 7a(a0)` (→`187c4`)
- `187c4`: `CMP.W 7e(a0), d1; BEQ.W 187d6` (→`187cc`)
- `187cc`: `MOVE.W d1, 7e(a0); BSET.B #7, 7a(a0)` (→`187d6`)
- `187d6`: `RTS` — FLOW
- `1ae56`: `MOVE.W #1, -7ff0(a5); MOVE.W #2000, 2ffff2.l; MOVE.W #0, 2ffff0.l; LEA.L 109156.l, a0; JSR 1879c.l`
- `1ae78`: `LEA.L 10b1d6.l, a0; JSR 1879c.l` — FLOW
- `1ae84`: `LEA.L 10d256.l, a0; JSR 1879c.l` — FLOW
- `1ae90`: `LEA.L 10d2d6.l, a0; JSR 1879c.l` — FLOW
- `1ae9c`: `MOVE.W #0, -7ff0(a5); MOVE.W #1000, 2ffff2.l; MOVE.W #0, 2ffff0.l; RTS`

**frame parity `43dbc`(`ffa JSR`) 1**
- `43dbc`: `MOVE.B 5494(a5), d0; ANDI.B #1, d0; ADDQ.B #1, d0; MOVE.B d0, 5494(a5); RTS`

- [F] 실행 의미 보충(명령 순서대로 읽기·쓰기; `.W`/`.B`는 나머지 bit 보존; 산술은 원래 폭의 2의 보수로 명시 계산하고 C++ 부호 있는 overflow·shift에 기대지 않는다; 메모리 RMW(`BSET`/`BCLR`/`ADDQ.B`/`SUBQ.B`/`ADD`)는 읽은 뒤 쓴다; `CLR.B`는 쓰기만 모델한다(68000의 선행 읽기는 RAM에서 관측 효과가 없다)):
  - `b68`: BYTE `100012` = BYTE `10fdaf`(읽고 쓰기), A0 = `10fdb6`, A1 = `b58`, `D7` = 0, BYTE `10f007` = 0, `D0.W` = 3. `b88`: BYTE `10f006`의 bit (`D0` mod 8) 검사·clear(읽고 쓰기); 원래 0이면 `b98`. `b92`: BYTE(A0 + sext(`D0.W`)) = 1. `b98`: `D6.W` = 4, `D6.B` = (4 + BYTE(A0 + sext(`D0.W`))) & `ff`, BYTE(A1 + sext(`D6.W`)) = 0이면 `baa`. `ba8`: `D7` bit (`D0` mod 32) set. `baa`: `D0.W` −= 1; 빌림 없으면(이전 `D0.W` ≠ 0) `b88`. `bae`: BYTE `10f007` = `D7.B`, RTS.
  - `e50`: `D0` = 0, WORD `-7ff2(A5)` = 0, WORD `7e(A6)` = 0, BYTE `84(A6)` = 1, LONG `76(A6)` = 0, `JSR 903a`. `e6e`: LONG `(A6)` = `e74`. `e74`: port `3c0004`/2 = 0, port `3c0000`/4 = `82000000`(각 1건, 이 순서), `JSR 3c08`.
  - `e98`: BYTE `-7fe5(A5)` bit 7 clear, `JSR 5728`(경계). `ea4`: BYTE `-7fe5(A5)` bit 7 set, raster 읽기(결정 2: 지금은 checked 오류). 승인 뒤 의미: `D0.W` = v, `D0.W` = `D0.W` >> 7(논리), `D0.W` −= `100`; 빌림 없으면(`v>>7` ≥ `100`) `ebc`, 있으면 `eba`(`D0` = 0). `ebc`: `D0.B` = (`D0.B` − BYTE `-7fe8(A5)`) & `ff`, BYTE `-7fe8(A5)` = `D0.B`.
  - `ec4`: BYTE `10f000` bit 0 = 0이면 `ef2`. `ed0`: BYTE `84(A6)` = 0이면 `ef2`. `eda`: `D0.W` = `7066`, A0 = `d56`, A1 = `3650`, A2 = `df0`, `JSR 3a70`(U02).
  - `ef2`: 결정 3. `efc`: raster 읽기(결정 2); 승인 뒤 `ea4`와 같은 계산으로 `f0e`/`f0c`(`D0` = 0). `f0e`: BYTE `-7fe8(A5)` = `D0.B`. `f12`: BYTE `-7fe6(A5)` = BYTE `-7fea(A5)`(읽고 쓰기), BYTE `-7fea(A5)` = 0, WORD `-335e(A5)` = 0, `JSR 31d6`(경계).
  - `f30`: A0 = LONG `76(A6)`; A0 = 0(32 bit; `CMPA.W #0`은 부호 확장 0과 비교)이면 `f54`, 아니면 `f3c` guard(결정 4).
  - `f5a`: `D1.B` = BYTE `84(A6)`, BYTE `84(A6)` = `D0.B`(`9136`의 결과); `D0.B` ≠ 0이면 `fbc`. `f66`: `D1.B` = 0이면 `f84`. `f6e`: WORD push `D1.W`, `JSR 3db2`. `f76`: WORD `82(A6)` = `D0.W`, `D0` = 0, `JSR 3d7e`(script_placement). `f82`: `D1.W` = WORD pop. `f84`: `D1.B` ≠ 1이면 `fae`. `f8c`: `D0` = 0, `JSR 8bbc`(cleanup). `f94`: `JSR 8bc8`. `f9a`: BYTE `80(A6)` = `ff`, `D0` = `D1` = `D2` = `fffffffc`, `D3` = 4, `JSR 8c16`(exit). `fae`: `JSR 5728`(경계), 복귀 `fb4 BRA ec4`(head 안 pause 루프; 매 반복이 `9136`·`5728` 경계를 지난다).
  - `fbc`: `D1.B` ≠ 0이면 `fe2`. `fc4`: `D0.W` = WORD `82(A6)`, `JSR 3d7e`. `fce`: BYTE `80(A6)` = 0이면 `fe2`. `fd6`: `JSR 8be0`. `fdc`: BYTE `80(A6)` = 0. `fe2`: `D0.W` = WORD `7e(A6)`; = WORD `-7ff2(A5)`이면 `ff0`, 아니면 `fee`(TRAP 경계). `ff0`: `D0.W` += 1, WORD `-7ff2(A5)` = WORD `7e(A6)` = `D0.W`, `JSR 43dbc`. `1000`: RTS(자연 복귀 `2ac2` dispatcher).
  - `3c08`: `D1.W` = WORD `-3276(A5)`. `3c0c`: `D1.W` = WORD `-3274(A5)`이면 `3c3c`. `3c14`: A0 = A5 − `327e` + sext(`D1.W`); WORD(A0) = 0이면 `3c34`. `3c22`: WORD push `D1.W`, `D0.B` = BYTE(A0), A0 += 1, BYTE push BYTE(A0)(A7 −= 2, 바이트 하나만 씀), A0 += 1, `BSR 3ac8`(복귀 `3c2c`). `3c2c`: `D0.B` = BYTE pop(A7 += 2), `BSR 3ac8`(복귀 `3c32`). `3c32`: `D1.W` = WORD pop. `3c34`: `D1.W` = ((`D1.W` + 2) & 6), `BRA 3c0c`. `3c3c`: WORD `-3276(A5)` = `D1.W`, RTS.
  - `3db2`: `D0` = 0; BYTE `104d91` bit 3 = 0이면 `3dc2`, 아니면 `3dc0 RTS`. `3dc2`: `D0.B` = BYTE `104d90`, `D0.W` += 1, RTS.
  - `8bc8`: A1 = `107dc2`, A0 = `107dd6`. `8bd4`: `D7.W` = `14`. `8bd8`(한 번에 한 바이트): BYTE(A0) = BYTE(A1), A0 += 1, A1 += 1, `D7.W` −= 1; ≠ 0이면 `8bd8`. `8be0`: `D0.B`/`D1.B`/`D2.B` = BYTE `-23e`/`-23c`/`-23a(A5)`, A0 = `107dc2`, A1 = `107dd6`, `BSR 8bd4`(복귀 `8bfa`). `8bfa`: BYTE `-22c(A5)` ≠ 0이면 `8c14`. `8c02`: BYTE `-22c(A5)` = 1, BYTE `-23e`/`-23c`/`-23a(A5)` = `D0.B`/`D1.B`/`D2.B`.
  - `903a`: `BSR 9056`(area_clear). `903e`: BYTE `107dee` `107df0` `107df1` = 0, `BSR 9546`. `9546`: BYTE `-202(A5)` = 0, `D7.W` = 7, `D0` = 0, A0 = A5 − `201`. `9556`(한 바이트씩): BYTE(A0) = `D0.B`, A0 += 1, `DBRA D7`(`D7.W` −= 1; `ffff`가 아니면 `9556`).
  - `166bc`: `D0.W` = WORD `d3a(A5)` − WORD `d36(A5)`; ≠ 0이면 `166ca`. `166ca`: A4 = A5 + `f4e`, `D0`..`D7` = 0, LONG 0 쓰기 128회(A4 − 4부터 A4 − `200`까지 내림차순; A4 = A5 + `d4e`), `D5.W` = `1fe`, A0 = A5 − `cc`, A1 = A5 + `b34`, `D6.W` = WORD `d36(A5)`, `D7.W` = WORD `d3a(A5)`. `16732`(한 반복): `D0` = `D1` = 0, `D2.W` = WORD(A1 + sext(`D6.W`)), `D0.B` = BYTE(A0 + sext(`D2.W`)), `D1.B` = BYTE(A0 + sext(`D2.W`) + 1), `D0.W` ×= 2, `D1.W` ×= 2, BYTE(A4 + sext(`D0.W`)) += 1, BYTE(A4 + sext(`D1.W`) + 1) += 1, `D6.W` = (`D6.W` + 2) & `D5.W`; ≠ `D7.W`이면 `16732`. `16756`: A2 = A4, `D7.W` = WORD(A2), A2 += 2, 255회 { `D7.W` += WORD(A2); WORD(A2) = `D7.W`; A2 += 2 }, `D7.W` &= `ff`, A2 = A5 + `f4e`, `D6.W` = WORD `d3a(A5)`, `D4.W` = `D7.W` − 1. `16b66`(한 반복): `D6.W` = (`D6.W` − 2) & `D5.W`, `D0.W` = WORD(A1 + sext(`D6.W`)), `D1` = 0, `D1.B` = BYTE(A0 + sext(`D0.W`) + 1), `D1.W` ×= 2, BYTE(A4 + sext(`D1.W`) + 1) −= 1, `D2` = 0, `D2.B` = 그 BYTE, `D2.W` ×= 2, WORD(A2 + sext(`D2.W`)) = `D0.W`, `DBRA D4`. `16b8a`: `D4.W` = `D7.W` − 1, `D7.W` ×= 2, A2 += sext(`D7.W`), `D6.W` = WORD `d36(A5)`. `16b96`(한 반복): A2 −= 2, `D0.W` = WORD(A2), `D1` = 0, `D1.B` = BYTE(A0 + sext(`D0.W`)), `D1.W` ×= 2, BYTE(A4 + sext(`D1.W`)) −= 1, `D2` = 0, `D2.B` = 그 BYTE, `D2.W` = ((`D2.W` × 2) + `D6.W`) & `D5.W`, WORD(A1 + sext(`D2.W`)) = `D0.W`, `DBRA D4`.
  - `16bba`: A5 = `108000`, `D0` = 0, `JSR ce02`(U04). `16bc8`: `JSR 166bc`. `16bcc`: `D0.W` = WORD `d36(A5)`. `16bd0`: 결정 3. `16bd6`: A0 = A1 = A5 + `b34`, A0 += sext(WORD `d36(A5)`), A1 += sext(WORD `d3a(A5)`); BYTE `d3c(A5)` bit 7 = 0이면 `16c6a`(역방향), 아니면 `16bec`(정방향).
  - `16bec`: LONG push A6, A6 = `3c0000`, WORD `d42(A5)` = WORD `d3e(A5)`, WORD `d4a(A5)` = WORD `d46(A5)`(A4 = A5 + `d46`). `16c04`: A1 = A0(32 bit)이면 `16c4e`. `16c0a`: A2 = A5 − `cc` + sext(WORD(A0)), A0 += 2; A0 ≠ `108d34`(고정 상수)이면 `16c1c`, 아니면 `16c18`(A0 = A5 + `b34`). `16c1c`: `D1.W` = WORD `6(A2)`, A4 = A5 + `d3e`, `D1` bit 2 검사·clear; 원래 0이면 `16c30`, 아니면 `16c2c`(A4 = A5 + `d46`). `16c30`: `D7.B` = (WORD `4(A2)` ≠ `ffff`) ? `ff` : 0, `D7.W` &= 4, `D7.B` |= `D1.B`, `D7.W` = (`D7.W` × 4) & `ffff`, A3 = `ce62`, `JSR` A3 + sext(`D7.W`)(복귀 `16c4c`; 결정 5). `16c4c`: `BRA 16c04`. `16c4e`: A6 = LONG pop, WORD `-7ff0(A5)` = 0, PVC `2ffff2` = `1000`, `2ffff0` = 0, `BRA 16ce6`.
  - `16c6a`: LONG push A6, A6 = `3c0000`, WORD `d44(A5)` = WORD `d40(A5)`, WORD `d4c(A5)` = WORD `d48(A5)`(A4 = A5 + `d46`). `16c86`: A1 = A0이면 `16cce`. `16c8c`: A2 = A5 − `cc`; A1 ≠ `108b34`(고정 상수)이면 `16c9c`, 아니면 `16c98`(A1 = A5 + `d34`). `16c9c`: A1 −= 2, A2 += sext(WORD(A1)), 이하 `16c1c`와 같은 `D1`·A4(→`16cb2`/`16cae`). `16cb2`: `16c30`과 같고 A3 = `11792`(복귀 `16ccc`). `16cce`: `16c4e`와 같은 pop·bank 0 뒤 `16ce6`. `16ce6`: `D0.W` = WORD `d3a(A5)`, WORD `d36(A5)` = WORD `d38(A5)` = `D0.W`, BYTE `d3d(A5)` = `ff`, RTS.
  - `1879c`: `D0.W` = WORD `14(A0)`, `D1.W` = WORD `18(A0)`, `D2.B` = BYTE `25(A0)`, `D3` = 0, X = bit 0 of `D2.B`, `D2.B` >>= 1, `D0.W` −= X, X = (새 `D2.B`) bit 0, `D2.B` >>= 1, `D1.W` −= X; `D0.W` = WORD `7c(A0)`이면 `187c4`. `187ba`: WORD `7c(A0)` = `D0.W`, BYTE `7a(A0)` bit 7 set. `187c4`/`187cc`: `D1.W`와 WORD `7e(A0)`로 같은 일. `1ae56`: WORD `-7ff0(A5)` = 1, PVC `2ffff2` = `2000`, `2ffff0` = 0(bank 갱신), A0 = `109156`, `JSR 1879c`. `1ae78`/`1ae84`/`1ae90`: A0 = `10b1d6`/`10d256`/`10d2d6`, `JSR 1879c`. `1ae9c`: WORD `-7ff0(A5)` = 0, PVC `2ffff2` = `1000`, `2ffff0` = 0, RTS.
  - `43dbc`: BYTE `5494(A5)` = ((BYTE `5494(A5)` & 1) + 1) & `ff`, `D0.B` = 그 값, RTS.

## carry

- [F] **소비 0, known 생산 0.** H1 안의 모든 Bcc·`SUBX`는 같은 block에서 만든 flag를 읽는다. callee 복귀점 block(`e50` `e6e` 등)은 모두 자기 flag를 먼저 만든다. H1 함수를 부르는 범위 밖 호출자가 없으므로 H1 RTS 앞 C의 소비자도 없다. 따라서 carry 오류 문자열은 두지 않는다.
- [F] **FLOW_ONLY 34 block**(C 보존): `b88` `ba8` `e4a` `e8c` `e92` `e98` `ec4` `f2a` `f54` `f94` `fae` `fb4` `fd6` `1000` `3dc0` `8bc8` `8bde` `8c14` `903a` `9054` `955c` `166c8` `16bb8` `16bc8` `16c18` `16c2c` `16c4c` `16c98` `16cae` `16ccc` `187d6` `1ae78` `1ae84` `1ae90`. carry 보존 목록(`animation_machine.cpp` `carry_preserving_pc`, 주석 붙은 case group 하나)에 34 PC를 넣는다.
- [F] **guard 4 block**(`f3c` `f44` `f4c` `f52`): 실행하지 않으므로 C 분류가 없다(보존 목록에 넣지 않는다).
- [F] **Unknown 82 block**: 나머지(`MOVE`/`MOVEQ`/`CLR`/`CMP`/`CMPI`/`CMPA`/`TST`/`ADD`/`ADDQ`/`SUB`/`SUBQ`/`SUBI`/`SUBX`/`AND`/`ANDI`/`OR`/`LSR`/`SNE`+`ANDI`, `MOVE` stack, port·PVC 쓰기, 대기 block). raster 읽기 block 2개 포함.
- [F] X: `SUBX.W D3,D0`/`D3,D1`(`1879c`)의 X는 바로 앞 `LSR.B #1,D2`가 둔다(같은 block). 다른 X 소비는 없다.

## 경계와 Waiting·external read·port 모델

- [F] **stop-only 경계(H1이 실행하지 않음):** `31d6`(H2), `9136`(H2), `5728`(H3), writer 표 live 대상(`ce62+…` H8, `11792+…` H4; 결정 5), `fee`(TRAP, D8), controller 진입 LONG `(1008e4)`(D1/D9; 자연 `c52a`). 단위 시험은 이 PC들을 stop으로만 쓰고(stop 성공) "routing 밖" rollback 탐침으로 쓰지 않는다(F4 시험 경계 관례). rollback 탐침은 work RAM PC `10fe00..10fefe`를 쓴다. 예외: `fee`는 D8이 정한 H1 자신의 TRAP 경계이므로 stop이 아니면 `unsupported animation machine PC`임도 시험한다.
- [F] **D1 H 끝:** head `1000 RTS`가 LONG(A7) = `2ac2`로 돌아가면 dispatcher(`2ac2` A6 = LONG `8(A6)` → `2ac6` → `2ab8` A5 = `108000` → `2abe` A0 = LONG `(A6)` → `2ac0 JSR (A0)`)가 기존 fade_card 실행부로 이어진다. stop PC = LONG `(1008e4)`이면 `JSR (A0)` 직후(복귀 LONG `2ac2` push 뒤) 멈춘다. 이것이 D1의 H stop이다. 선언 skip·N 연결은 결정 6.
- [F] **Waiting:** 결정 3(`ef2`, `16bd0`). `3c22`/`3c2c` → `3ac8`의 sound ring 대기 `3aea`(D6)는 기존 sound 실행부와 해제 어휘(WORD `104d74` := `ffff`) 그대로다.
- [F] **external read:** 결정 2.
- [F] **port(D7):** `e74`의 `MOVE.W #0,3c0004`와 `MOVE.L #82000000,3c0000`은 각각 원본 쓰기 1건 = `VideoPortWrite` 1건(크기 2·4, 기존 map_transfer·scene 관례). PVC `2ffff2`/`2ffff0` WORD 쓰기는 `am_write`(PVC 기억·bank 공식·port 기록)로, `1ae9c` `16c4e` `16cce`의 세 쓰기는 기존 `am_zero_bank`와 같은 순서다. watchdog `300001`과 writer의 `3c0000` 쓰기는 H1 밖(H3·H4)이다.
- [F] **스택:** JSR/BSR 복귀 LONG, `3c22`의 WORD push·BYTE push(±2), `3c2c`/`3c32` pop, `f6e`/`f82` WORD push/pop, `16bec`/`16c6a` LONG push A6와 `16c4e`/`16cce` pop. work RAM 밖 스택은 기존 checked 오류다.

## 구현 범위와 규약

- routing 13 범위(결정 1). 짝수 PC 1,247개 중 block 시작 120, 내부 1,127. 내부 PC 직접 진입은 `unsupported animation frame head h1 PC`다.
- 레지스터 의미: `.W`/`.B` 연산은 하위 WORD/BYTE만 바꾼다(`MOVEQ`·`MOVEA`·`LEA`·`MOVE.L`·`ADDA`는 LONG 전체). 비교는 폭별 부호 없는/있는 정의를 명시 계산한다(`BCC`/`BCS` 빌림, `BPL` bit 7, `BNE`/`BEQ`). 반복 block(`16732` `16b66` `16b96` `8bd8` `9556` `b88`..`baa` `3c0c`..`3c34`)은 원본처럼 block 실행 한 번이 한 반복이다. unrolled block(`166ca` `16756`)은 같은 순서의 반복문으로 쓴다.
- 기존 실행부(`animation_machine_interpreter.cpp` 등)는 고치지 않는다. 공유 최소 수정: `animation_machine.cpp` routing `else if` 하나와 carry 보존 case group 하나, `animation_machine_internal.h` 선언 하나, `Makefile`(source 목록·test target·실행 줄), `tools/verify_animation_machine.py` SOURCES. 결정 7의 탐침 값 교체 3곳.

## 자료

- [F] fixed ROM(live bus): `b58..c58` BYTE 표(`b98`).
- [F] work RAM(A5 = `108000` 기준 자연 주소): `10000e`(`-7ff2`) `100010`(`-7ff0`, bank 사본) `100012` `100016` `100017` `100018` `10001a` `10001b`, `104ca2`(`-335e`), `104d82..104d8c`(sound word 큐 `-327e..-3274`), `104d90` `104d91`, `107dc2..107dea`(palette 사본 `-23e..-216`), `107dee` `107df0` `107df1`, `107dfe..107e06`(`-202..-1fa`), `107f34..`(`-cc`, sprite 항목 표), `108b34..108d34`(`b34`, sprite 큐 ring), `108d34` `108d36` `108d38` `108d3a` `108d3c` `108d3d` `108d3e..108d4d`, `108d4e..108f4e`(정렬 계수 `d4e..f4e`), `10d494`(`5494`), `10f000` `10f006` `10f007`, `10fdaf` `10fdb6..10fdb9`, 배경 node `109156` `10b1d6` `10d256` `10d2d6`(+`14` `18` `25` `7a` `7c` `7e`), head node A6(자연 `100820`: `+76` `+7a` `+7e` `+80` `+82` `+84`, LONG `(A6)`).
- [F] device: port `3c0004` `3c0000`, PVC `2ffff0` `2ffff2`, 읽기 `3c0006`(결정 2).

## 시험 계획

- 단위 시험(`engine/tests/animation_machine_frame_head_h1_test.cpp`, `run_animation_machine`만): Unicorn 생성 fixture(scratch 생성기, 원본 ROM + 합성 없음; 읽기는 work RAM과 `b58` 표뿐), 120 시작 전부, block 표(시작 × 들어오는 C clear/set: native 후속·digest·C 분류), zero-step(120 × C 3), 내부 PC 1,127 전수(정확한 오류), 홀수 PC, guard 4, raster 읽기 2 block(결정 2 오류, 상태 보존), Waiting `ef2`/`16bd0`와 선언 해제 뒤 재개, 경계 stop(`31d6` `9136` `5728` writer 표 대상 `fee` `c52a`), RAM rollback 탐침 `10fexx`.
- 실제 ROM 차분(Unicorn vs C++ + 8 `program_rom_*.ms5d`), native F5 관측의 자연 H 시작 상태에서 H1 경계까지의 차분(H 구간이 어느 H2~H7 경계에서 멈추는지 보고), 돌연변이 검사, UBSan, base frame pass·RNG 400 무변화.

## 작업자 검증 기록 (구현 뒤 scratch 기록, Claude Opus 5.5 / high)

- [F] ROM SHA256 `29112a94…860f`, mtime `1791291625`가 작업 전후 같다. 커밋하지 않았다. 작업 트리 `metalslug-h1`(base `77e5485`), scratch `ms5-scratch/h1/`.
- [F] 산출 파일(SHA256 앞 16자리): `engine/src/animation_machine_frame_head_h1.cpp` `59855db02b96fc89`, `engine/tests/animation_machine_frame_head_h1_test.cpp` `1a81a58a023f0618`. 공유 최소 수정: `engine/src/animation_machine.cpp`(routing `else if` 하나, carry 보존 case group 하나(34 PC); `adc6e788e4584c9b`), `engine/src/animation_machine_internal.h`(선언 하나; `b6652f94a8c7e383`), `Makefile`(source 목록·test target·실행 줄; `4fed18c6ff20beaf`), `tools/verify_animation_machine.py` SOURCES(`434f67c98e88f300`). 결정 7 탐침 교체: `animation_machine_area_clear_test.cpp`(`6080f88e916b7948`), `animation_machine_script_placement_test.cpp`(`2aaf213901f8b9c4`), `animation_machine_scheduler_test.cpp`(`2776fcbdbabf913e`), `animation_machine_scene_update_test.cpp`(`47f21a4cf11bac48`). public header는 바꾸지 않았다(결정 2는 제안만).
- [F] 실행부 case 집합 = scratch `starts.txt`(120, SHA256 `6986d31107c545da…`). 내부 PC 1,127개는 모두 `unsupported animation frame head h1 PC`, `fee` `fb8` `fba`는 `unsupported animation machine PC`, guard 4 block은 들어오는 C 3가지 모두 aux 오류, raster 2 block은 queue 오류다(상태 보존).
- [F] `make -j3 all test`(작업 지시의 동시 3 process 상한): exit 0, 경고 0, `Assert` 줄 0(scratch `make_all.log`), `tools/tests` unittest 257개 OK. H1 test 출력: `animation machine frame head h1: 365 fixtures (31 checked errors, 11 waiting, 11 resumed, 16 kept C), 114 blocks, 2266 calls`.
- [F] UBSan(`-fsanitize=undefined -fno-sanitize-recover`, scratch `build_test.sh ubsan`): H1 test 통과(`ubsan.log`).
- [F] 단위 test(run_animation_machine만; scratch `gen/gen_h1.py` Unicorn 생성, 두 번 생성해 표 SHA 동일, 최종 `tables_h1.inc` SHA256 `fedebba7cc16de69…`): 365 fixture(성공 334, checked 오류 31). 입력은 선언 LCG 채움 + puts, 합성 바이트는 `b58..b68` 16바이트뿐(ROM 자료 아님). 시작 120개 = block 표 114(× 들어오는 C clear/set: native 후속·digest·port 수·C 분류) + guard 4 + raster 2(오류 행). zero-step 120 × 3, 내부 PC 1,127 전수, 범위마다 홀수 양끝, RAM rollback 탐침 `10fe10` `10fe20` `10fe30` 및 fixture의 `10fe40` `10fe42` `10fe44` `10fe46`(RTS·controller LONG). Waiting 11행(`ef2` 6: BYTE `100016` < BYTE `100017`; `16bd0` 5)은 대기 상태가 입력과 같음(D0 포함), 해제 없이 재실행하면 다시 같은 Waiting, 선언 해제 뒤 재개가 native와 같음을 확인했다. 경계 stop: `e7bf4` `9056` `3ac8` `ce02` `3a70` `3d7e` `8bbc` `8c16` `31d6` `9136` `5728` `fee` `c52a` `c66a`, writer 표 정방향·역방향 항목과 표 밖 착지(`cffa` `d062` `11806` `11b2a` 등). D1 행(`ff0`/`fbc` → `43dbc` → `1000 RTS` → dispatcher → LONG `(1008e4)` stop)에서 A6 = `1008e4`, A0 = 대상, LONG(A7) = `2ac2`를 확인했다. checked 오류 31: aux guard 6(`f30` 2 포함), raster 7(stop을 block 뒤에 둔 3행 포함), rollback 4, block budget 1(`3c08` 홀수 cursor), 홀수·ROM·장치 주소와 스택·pop 장치 13.
- [F] 돌연변이 검사(scratch `mut/mut_h1.py`, scratch 사본만 변형, 72개 + identity): 72/72를 test가 잡았다. 첫 실행에서 살아남은 3개(`f5a` BYTE→WORD 판정, `16bd6` `ADDA.W` 부호 확장 제거, `ea4` raster 오류 대신 진행)는 fixture `f5a-1200-1`, `16bd6-negative`, `error-ea4-stop-eba`/`-ebc`/`error-efc-stop-f0e`를 더해 잡혔다. 잡힌 항목: 모든 분기 뒤바꿈, 비교 폭(BYTE/WORD/LONG `CMPA.W`), 부호(`ef2` 부호 없는 BYTE), 대기 조건·대기 전 D0 보존, port 값·순서, PVC bank 값, RAM 변위(`-7ff2` `-7fe6` `-335e` `82` `-23c`), 반복 수(128 LONG, 255 WORD, `14`, DBRA 끝), 정렬 key 위치·계수 증감·mask, ring 끝 상수, writer 색인(`SNE` 반전, `ANDI.W`→`.B`, 표 선택), `BCLR #2` bit, `SUBX` X(제거·bit 위치), `BSET` bit, 배경 node 주소, parity mask, 오류 문자열 2개, carry 보존 목록(빼기·더하기), routing 범위(`fee`·`fb8` 포함 시).
- [F] 실제 ROM 차분(scratch `realrom/real_h1.py`, Unicorn vs C++ `run_animation_machine` + 8 `program_rom_*.ms5d`, bank `200000`/`300000`, 무작위 work RAM + 구조 필드, routing된 callee는 양쪽에서 따라가고 대기 `ef2` `16bd0` `3aea` `cda4`는 같은 선언 해제, native는 C++ routing 밖 첫 PC·STOP·raster/guard block에서 멈춤): 3 seed × 1,500 case 불일치 0/0/0. 시작 120개 모두 진입(116 native 실행 + guard 3·`ea4`는 진입 즉시 오류 비교). 대기 해제 native: seed 1 `16bd0` 54·`ef2` 20, seed 2 50·13, seed 3 70·13·`3aea` 1. 기대 checked 오류 비교: raster 145/124/127, aux 40/41/42. C++ stop C(Unknown/Clear/Set) seed 1 1,173/36/29. native가 깨끗이 멈추지 않은 case는 건너뜀(26/38/35: `e4a`→`e7bf4` 무작위 상태, `3c2c`/`8bd4` 무작위 stack·포인터). native 홀수 주소(Unicorn은 68000 address error를 내지 않음; C++는 정렬 checked 오류) 77/75/78. 다른 실행부의 직선 내부 PC(`8c16` palette effect leaf의 `8c1c..8cc8`)는 dispatch 지점이 아니므로 통과시켰다.
- [F] native F5 관측 차분(scratch `realrom/nat_h1.py`, 관측 `observation.json` SHA256 `dbb631a8…`, 읽기 전용): 자연 seed 136개의 기록 pass-end dump 4,975개(= 다음 frame H의 시작 상태)에서 (a) 시작 digest = 기록 `h.start` 4,975/4,975, (b) 같은 선언 규약(queue 기본값, 대기 해제, controller 진입 직후 stop; PvcMachine)으로 H 전체를 native 재실행해 기록 `h.end`·port digest·대기 목록 재현 4,975/4,975, (c) H1 경계까지 native vs C++ 불일치 0. **H 구간이 처음 닿는 경계**: `5728`(H3) 3,332, 역방향 writer 표 `11792` 842 · `117a2` 651 · `11796` 107 · `117a6` 43(H4, 합 1,643). 정방향 writer(H8)·`31d6`(H2)에는 자연 H가 H1 안에서 먼저 닿지 않는다. H1 구간 안의 `16bd0` 선언 해제 1,543회. C++ stop C는 모두 Unknown.
- [F] base frame pass 차분(`verify_animation_machine_scheduler_f4.py` 사본, 출력 scratch `fp/`): 기준 `77e5485` pass 14,408·node 122,462 일치, 불일치 0 → H1 뒤 `diff_results.json` 바이트 동일.
- [F] RNG 400 frame 차분(`verify_animation_machine_scheduler_rng_f4.py` 사본): 기준 complete 132·pass 52,800·node 396,091·불일치 0(`verification.json` SHA256 `67a1a03e…`) → H1 뒤 같은 값(`3fb40a39…`; 차이는 `engine_source_sha256`의 `animation_machine.cpp`·새 파일 항목과 seed 4개 기록의 `current_router_sha256`뿐). 새 완주 0, 잃은 seed 0(frame head는 여전히 F2 pass의 stop이다).
- [F] 무효화 목록(수정하지 않음): `tools/verify_animation_machine_script_placement.py`(ROUTED 끝 `3db2`, outside `3db2` `3db4`)는 H1 routing 뒤 outside 기대가 틀린다. F5 범위 문서 4절의 `pass-controller`(scheduler test)·`pass-head-ring-unchecked`는 controller(`c52a`) 미routing을 기대하므로 C1/C3 전까지 유효하다(이번 실행에서 통과).
- [U] 남은 미확인: 결정 2(external read queue API)가 정해지기 전까지 `ea4`·`efc` 뒤 경로의 실제 raster 값 처리는 구현되지 않았다(그 뒤 block `eba` `ebc` `f0c` `f0e`는 fixture로 구현·검증). aux 경로 `f44` `f4c` `f52`와 TRAP `fee`의 의미는 guard/경계로만 둔다. writer 표 밖 착지(`D1.B` ≥ 4)는 H4/H8 계약이 정한다. D1 driver(skip·N 연결)는 결정 6대로 미구현이다.
