# `480bc` 프레임 helper 묶음 범위 분석(구현 전 계획)

Canonical BE ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 주소는 fixed CPU 주소=file offset이며 `200000+`는 banked window CPU 주소다. Claude Opus 5.5 / high 읽기 전용 분석 작업자가 capstone M68000으로 디코드했고 메인(Claude Opus 5.5)이 검토해 기록했다. [F]=원본 바이트·기록 산출물 사실, [I]=추론, [U]=미확인. **구현·검증 기록이 아니다.**

## 핵심 사실

- [F] `480bc`는 JSR이 아니라 BRA/Bcc 16곳(`478da 4790e 47992 479ac 47aec 47b60 47c00 47da0 47de8 47e26 47e66 47e74 47e96 47f3e 47fac 47fe0`)에서만 들어온다. 본문은 JSR `47642`(pc), JSR.L `1a73c 49b0c 4aa88 b4a2a 6f1c2 4701e e8a48 2efa6`, `480f0` RTS(호출자 복귀 LONG, chain fixture에서는 `2ac2`)다.
- [F] 정적 closure: jump table 대상 제외 62 routine/1474 명령, 포함 시 214 entry/2649 명령, 입력 callback(JSR (A1)) 22 routine 약 289 명령 추가. BIOS 호출 없음.
- [F] 기존 실행부에서 멈추는 지점: `289e 28ae 3ac8 3af8 cd58 43e38 caf0 18702 1861a 17012 16ff8 8da2 43ffc 1701a`. `cd58`은 LONG(A5+1152)=`cd50`일 때만 받는다.
- [F] I/O: PVC `2ffff2`(2000/1000)·`2ffff0`, `3c0000` LONG(디버그 격자), `3c0006` WORD(script opcode 40→`3d7e`), banked `20000c`(opcode 04), 디버그 `10f000`/`10f001`, 입력 RAM `104caa/ab/b0/b1`, 사용자 mask `10f01c`/`10f020`. watchdog·사운드 port·입력 port 직접 접근 없음.
- [F] 간접 분기: motion type WORD 2(a1) 5개 dispatcher(`18c0a 18cae 18efe 18fd6 192c8`, 36/4 대상), path opcode(`19e86`, 8), script opcode(`1a0b8`, 20), 조건 opcode(`1a2c2`, 3), 입력 callback LONG `d734`/`d738`. 어느 곳도 index 범위 검사를 하지 않는다.

## 자연 경로 근거

- [F] screen/fade/card chain fixture의 `480bc` 시점 RAM은 의사난수(`d412`, `d3b4`, `d734`, `d40e`, `10f000` 등)이므로 `480bc` 시작 상태로 쓰지 않는다. [I] 그대로 실행하면 쓰레기 포인터를 따라간다.
- [F] 일관된 시작 상태 후보: `artifacts/stage_frame/verification.json`(96 case, input.bin·host write·register·native pcs), `artifacts/stage_entry_body/native_*.trace.json.gz`(152 중 142가 `47aec`로 `480bc` 도달), `artifacts/scene_frame_execution`(`1a73c` 진입 594 frame).
- [F] 첫 자연 frame(stage_entry_body): 입력 callback null(기본 mask), slot loop 없음(`10f001`=0), script gate true(122)이나 opcode dispatch 미실행, path 비null(`19e70→18656→18702`, 122), motion 조각 일부, `3c44`(3), `3af8`(2). 약 323 block leader.

## 제안 단위(의존 순서, leader 수는 근사)

| 단위 | 범위 | leader | 경계 |
| --- | --- | --- | --- |
| U1 shell·가벼운 helper | `480bc`, `47642/47656`, `6f1c2`, `b4a2a` 묶음, `4701e/46f52`, `2efa6/3c44` | ~107 | `1a73c 49b0c 4aa88 e8a48`, TRAP #15 guard |
| U2 scene core | `1a73c`, `1a2b4`+조건, `1a26a` gate, `1a526`, 카메라 `19b96/19a40/19ac8`, `19d08/19d98`, `19978`, `1a3d6`, `1a442` gate, motion null 경로 | ~170 | `1a0b6 1a470 1a7a8`, 비null motion dispatch |
| U3 motion walk | `1972a 196ac 196de 19710 1971c`+5 dispatcher | ~126(관측 11 type)/~201(36) | 미지원 type guard |
| U4 scene update | `1a7a8`, `1724c/1726c`, `1728c/43ea8`, `43e08/43e22`, `1afda`(비디버그), `19e64`+8 path handler, `18656` | ~110(+디버그 ~25) | 기존 `18702 1861a 16ff8 caf0` |
| U5 script·배치 | `1a0b6`+20 handler, `19772`, `1a086/1a09e/19e60`, `3d7e`, `e89fa`, `1a470` | ~80 | 기존 `8da2 43ffc 17012/1701a 28ae` |
| U6 입력 | `49b0c` core(~31)+알려진 callback(~132) | ~163(2분할) | 미지 JSR (A1) guard |
| U7 buffer·cue | `4aa88/4b784`, `e8a48/e8ad0/e8af4/2986` | ~61 | `cd58` 대기(callback `cd50`만) |

통합은 마지막: stage_frame seed에서 실제 대기(`cd58` sprite, `3ac8/3af8` sound)를 포함한 전체 `480bc` frame. `4aa88`은 `cd58`을 넘어 A6/A4/D7을 live stack에 유지한다. [I] 기존 step_* API는 14-register 관점·host pending 상태를 쓰므로 live-A7 동작(stack의 A6, `3c44`의 MOVE.B (A7))을 보존하려면 block 단위 재구현이 일관된다.

## 주의 패턴

- carry 반환 생산자: `289e`, `18c06` dispatch, `19710`, `1971c`, `196ac`, `1935c/19564`, `1a2b4`, `1a2e0`(EORI로 반전), `1a2f2/1a334/1a34c`, `49392`, `2986` 경유 `28ae`.
- 한 block 안 X flag 의존: `1724c/1726c` ADD.B→SUBX, `1b056/1b072` SUB.L→SUBX.L.
- BSR과 fall-through가 공유하는 코드: `47656`, `49bb4`, `1a34c`.
- BVC(`19d6e/19d8a`), SLT/SGT BYTE 조합(`1935c/19564`), 메모리 LSR.W (A0)+, Dn bit 번호 BTST/BSET 메모리(mod 8), NOT.W 유래 DBRA 횟수.

## 미확인·결정 필요

1. TRAP #15(`49392` A5≠108000, callback `4d7a6`): checked 오류 guard로 둘지.
2. `2986`의 MOVE to/from SR: 기계에 SR이 없으므로 "C 보존만" 모델로 충분한지.
3. 범위 밖 jump table index 정책(type>8c, path>1c, script>4c, 조건>08).
4. 입력 callback 대상 집합(알려진 18개 외).
5. 스테이지 종료 `47fdc/47fac/47f3e→480bc` 진입 시 실제 RAM(일관된 fixture 없음).
6. `cd58` 비기본 sprite callback.
7. port `3c0006`·`104d90` 의미와 am_write MMIO 지원.
8. 디버그 경로(`10f000` bit3/4, `10f001` bit7/0/1) 구현 또는 guard.
9. `e8a48`·`1a470`이 `28ae` 실패를 무시하고 fallback A0=`100e98`로 쓰는 경로.
10. `4d9d6`이 A6 상위 WORD로 A0를 만드는 경로의 A6 범위.
11. `480bc` 진입 bank 상태(2/3)와 `1a192`의 bank 1000 아래 banked 읽기.
12. ROM 자료 읽기의 MS5D window: `49ab0`, `1a08e/1a0a6`, `e8a0c`, `e89e4/e89ec`, `1af12/1afd2`, `46f52`의 26(a0) rect 자료, 56(a0)/8(a4) region box.

작업자 scratch: 세션 scratchpad `scope480bc/`(저장소 밖).
