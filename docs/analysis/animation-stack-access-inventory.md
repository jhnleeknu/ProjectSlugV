# Animation stack 접근 기계적 목록

기준 HEAD `68bd083`. canonical BE `extracted/program/maincpu.decrypted.be.bin`, 8,388,608 bytes, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 고정 CPU 주소는 같은 ROM 파일 offset이다. `load_verified_program`과 `disassemble_range`로 원본 bytes를 확인했다. **정적 명령 목록이며 전체 stack 의미·alias 지원·새 C++ 통합 계약을 확정하지 않는다.**

## 범위와 증거 구분

`49fc6..4a46b`와 지원 callee `cd50..ce01`, `3ac8..3c07`, `47672..476bb`, `ca70..ca75`, `2b3e8..2b40b`, `3679e..3679f`를 조사했다. 요청한 마지막 `4a468`은 복귀 후 분기 명령이므로 raw4바이트까지 확인했다. 명시적 A7 operand, PEA, JSR/BSR, RTS를 수집했다. 이 범위에서 LINK/UNLK는 발견되지 않았다.

`4a00c..4a01d`와 `4a25a..4a267`은 TRAP 뒤 inline 오류 문자열로 제외했다. `4a022..4a065`는 실제 BRA.W dispatch 슬롯이며 data로 지우지 않았다. 전체 선형 decode를 실행 증거로 취급하지 않는다. 아래 “PC 관측”은 기존 trace의 pcs에 해당 원본 PC가 등장한다는 최소 의미이며, stack byte 값·순서·모든 조건까지 새로 검증했다는 뜻은 아니다. “정적만”은 이번에 읽은 7개 관측군에서 PC witness를 찾지 못했다는 뜻이며 원본 도달 불가능을 뜻하지 않는다.

## Stack 명령 목록

| PC / ROM offset | raw opcode | 명령 | stack 메모리 폭 / A7 변화 | 호출·복귀 | PC 관측 |
|---|---|---|---|---|---|
| `049fea` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | A `case_088_begin_trace.json` |
| `04a0e2` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | A `case_000_begin_trace.json` |
| `04a104` | `61000006` | `bsr.w $4a10c` | return LONG 4B write / −4 | $4a10c; return `04a108` | A `case_000_begin_trace.json` |
| `04a124` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | B `case_773_begin_trace.json` |
| `04a132` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | A `case_020_begin_trace.json` |
| `04a148` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | A `case_068_begin_trace.json` |
| `04a1dc` | `48e700c0` | `movem.l a0-a1, -(a7)` | A0/A1 LONG 8B write / −8 | — | A `case_000_begin_trace.json` |
| `04a1e0` | `3f2d8010` | `move.w -$7ff0(a5), -(a7)` | WORD 2B write / −2 | — | A `case_000_begin_trace.json` |
| `04a1fa` | `4eb90000cd58` | `jsr $cd58.l` | return LONG 4B write / −4 | $cd58.l; return `04a200` | A `case_000_begin_trace.json` |
| `04a200` | `3b5f8010` | `move.w (a7)+, -$7ff0(a5)` | WORD 2B read / +2 | — | A `case_000_begin_trace.json` |
| `04a204` | `48a78100` | `movem.w d0/d7, -(a7)` | D0/D7 WORD 4B write / −4 | — | A `case_000_begin_trace.json` |
| `04a222` | `4c9f0081` | `movem.w (a7)+, d0/d7` | D0/D7 WORD 4B read / +4; signed16→32 | — | A `case_000_begin_trace.json` |
| `04a226` | `4cdf0300` | `movem.l (a7)+, a0-a1` | A0/A1 LONG 8B read / +8 | — | A `case_000_begin_trace.json` |
| `04a22a` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | A `case_000_begin_trace.json` |
| `04a23e` | `48711000` | `pea.l (a1, d1.w)` | effective-address LONG 4B write / −4 | — | B `case_000_begin_trace.json` |
| `04a26c` | `6100fe9e` | `bsr.w $4a10c` | return LONG 4B write / −4 | $4a10c; return `04a270` | B `case_000_begin_trace.json` |
| `04a270` | `225f` | `movea.l (a7)+, a1` | LONG 4B read / +4 | — | B `case_000_begin_trace.json` |
| `04a2e2` | `48e700c0` | `movem.l a0-a1, -(a7)` | A0/A1 LONG 8B write / −8 | — | D `case_0000_begin_trace.json` |
| `04a2e6` | `4eb900003af8` | `jsr $3af8.l` | return LONG 4B write / −4 | $3af8.l; return `04a2ec` | D `case_0000_begin_trace.json` |
| `04a2ec` | `4cdf0300` | `movem.l (a7)+, a0-a1` | A0/A1 LONG 8B read / +8 | — | D `case_0000_begin_trace.json` |
| `04a30c` | `2f08` | `move.l a0, -(a7)` | LONG 4B write / −4 | — | F `case_0000_begin_trace.json` |
| `04a332` | `2f09` | `move.l a1, -(a7)` | LONG 4B write / −4 | — | F `case_0000_begin_trace.json` |
| `04a338` | `3f2d8010` | `move.w -$7ff0(a5), -(a7)` | WORD 2B write / −2 | — | F `case_0000_begin_trace.json` |
| `04a352` | `4e91` | `jsr (a1)` | return LONG 4B write / −4 | (a1); return `04a354` | F `case_0000_begin_trace.json` |
| `04a354` | `3b5f8010` | `move.w (a7)+, -$7ff0(a5)` | WORD 2B read / +2 | — | F `case_0000_begin_trace.json` |
| `04a358` | `48a78100` | `movem.w d0/d7, -(a7)` | D0/D7 WORD 4B write / −4 | — | F `case_0000_begin_trace.json` |
| `04a376` | `4c9f0081` | `movem.w (a7)+, d0/d7` | D0/D7 WORD 4B read / +4; signed16→32 | — | F `case_0000_begin_trace.json` |
| `04a37a` | `225f` | `movea.l (a7)+, a1` | LONG 4B read / +4 | — | F `case_0000_begin_trace.json` |
| `04a37c` | `205f` | `movea.l (a7)+, a0` | LONG 4B read / +4 | — | F `case_0000_begin_trace.json` |
| `04a408` | `2f08` | `move.l a0, -(a7)` | LONG 4B write / −4 | — | C `case_000_begin_trace.json` |
| `04a41e` | `2f09` | `move.l a1, -(a7)` | LONG 4B write / −4 | — | C `case_000_begin_trace.json` |
| `04a422` | `3f2d8010` | `move.w -$7ff0(a5), -(a7)` | WORD 2B write / −2 | — | C `case_000_begin_trace.json` |
| `04a43c` | `4e91` | `jsr (a1)` | return LONG 4B write / −4 | (a1); return `04a43e` | C `case_000_begin_trace.json` |
| `04a43e` | `3b5f8010` | `move.w (a7)+, -$7ff0(a5)` | WORD 2B read / +2 | — | C `case_000_begin_trace.json` |
| `04a442` | `48a78100` | `movem.w d0/d7, -(a7)` | D0/D7 WORD 4B write / −4 | — | C `case_000_begin_trace.json` |
| `04a460` | `4c9f0081` | `movem.w (a7)+, d0/d7` | D0/D7 WORD 4B read / +4; signed16→32 | — | C `case_000_begin_trace.json` |
| `04a464` | `225f` | `movea.l (a7)+, a1` | LONG 4B read / +4 | — | C `case_000_begin_trace.json` |
| `04a466` | `205f` | `movea.l (a7)+, a0` | LONG 4B read / +4 | — | C `case_000_begin_trace.json` |
| `00cd50` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | A `case_000_begin_trace.json` |
| `00cd56` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | 정적만 |
| `00cd5c` | `4e90` | `jsr (a0)` | return LONG 4B write / −4 | (a0); return `00cd5e` | A `case_000_begin_trace.json` |
| `00ce00` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | A `case_000_begin_trace.json` |
| `003ad6` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0168_begin_trace.json` |
| `003af6` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_016_ready_trace.json` |
| `003b06` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0000_begin_trace.json` |
| `003b14` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0006_begin_trace.json` |
| `003b1e` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0012_begin_trace.json` |
| `003b28` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0009_begin_trace.json` |
| `003b3e` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0135_begin_trace.json` |
| `003b5e` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_012_begin_trace.json` |
| `003b6c` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_010_begin_trace.json` |
| `003b80` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_009_begin_trace.json` |
| `003b96` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0123_begin_trace.json` |
| `003bc8` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_015_begin_trace.json` |
| `003be2` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_008_begin_trace.json` |
| `003bfa` | `1f18` | `move.b (a0)+, -(a7)` | BYTE 1B write / −2; gap1B | — | C `case_016_begin_trace.json` |
| `003bfc` | `6100feca` | `bsr.w $3ac8` | return LONG 4B write / −4 | $3ac8; return `003c00` | C `case_016_begin_trace.json` |
| `003c00` | `101f` | `move.b (a7)+, d0` | BYTE 1B read / +2; gap1B skip | — | C `case_016_ready_trace.json` |
| `003c06` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | D `case_0166_begin_trace.json` |
| `047672` | `4eb90000ca70` | `jsr $ca70.l` | return LONG 4B write / −4 | $ca70.l; return `047678` | C `case_000_begin_trace.json` |
| `047682` | `2f08` | `move.l a0, -(a7)` | LONG 4B write / −4 | — | C `case_008_begin_trace.json` |
| `047688` | `4eb900003af8` | `jsr $3af8.l` | return LONG 4B write / −4 | $3af8.l; return `04768e` | C `case_008_begin_trace.json` |
| `04768e` | `205f` | `movea.l (a7)+, a0` | LONG 4B read / +4 | — | C `case_008_begin_trace.json` |
| `0476ba` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_000_begin_trace.json` |
| `00ca74` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | C `case_000_begin_trace.json` |
| `02b3f8` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | E `case_128_trace.json` |
| `02b40a` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | E `case_153_trace.json` |
| `03679e` | `4e75` | `rts ` | return LONG 4B read / +4 | stack LONG→PC | G `case_0000_begin_trace.json` |

## Stack 복원 뒤의 주요 분기

아래 분기는 stack에 새 return LONG을 쓰지 않는다. raw bytes와 target을 별도 정적 확인했으며, 이 표 자체를 새 실행 증거로 취급하지 않는다.

| PC | raw opcode | 분기 target | A7 변화 |
|---|---|---|---|
| `04a108` | `6000fef4` | `bra.w $49ffe` | 0 |
| `04a272` | `6000fd8a` | `bra.w $49ffe` | 0 |
| `04a2f0` | `6084` | `bra.b $4a276` | 0 |
| `04a37e` | `6000fef6` | `bra.w $4a276` | 0 |
| `04a468` | `6000fe0c` | `bra.w $4a276` | 0 |
| `003c02` | `6000fec4` | `bra.w $3ac8` | 0 |

## Frame과 이어지는 분기 위치

다음은 원본 push/pop 명령이 직접 정하는 frame 슬롯 목록이다. S는 각 handler에 들어올 때의 A7이며, outer caller의 반환 LONG은 fixture가 제공한 값이다. 자연 게임 caller의 stack 배치는 여기서 확정하지 않는다.

- direct04: `4a104 BSR→4a10c`가 return4a108 LONG을 쓴다. draw routine 안에서 `4a1dc`가 A0/A1 LONG, `4a1e0`가 bank WORD, `4a1fa`가 return4a200 LONG을 추가한다. wait 시 저장 범위와 stack 원문은 A 관측에 있으며, native stack 포인터와 실제 memory restore는 기존 animation-full-register-boundaries.md를 따른다.
- indexed10: `4a23e PEA(A1+D1.W)`가 list end LONG을 보관하고 `4a26c BSR→4a10c`가 return4a270을 쓴다. draw 복귀 뒤 `4a270`은 memory LONG을 A1으로 복원한다. 이 경로는 `4a272 BRA49ffe`이며 `4a276`의 D6/상태포인터 쓰기를 거치지 않는다.
- direct30: `4a2e2 MOVEM.L A0/A1` 후 `4a2e6 JSR3af8` return4a2ec. `4a2ec`는 memory LONG A0/A1만 복원한다. bank push/pop 또는 D0/D7 MOVEM.W가 없다. `4a2f0 BRA4a276` 뒤 publication.
- callback3c: `4a30c` A0 LONG, `4a332` A1 LONG, `4a338` bank WORD, `4a352 JSR(A1)` return4a354. `4a354` bank pop, `4a358` D0/D7 WORD 임시 저장, `4a376` signed WORD 복원, `4a37a/37c` A1/A0 LONG pop. `4a37e BRA4a276`.
- callback14: 같은 폭의 frame이 `4a408/41e/422/43c`에서 만들어지고 return4a43e. bank pop4a43e, WORD 임시저장4a442/복원4a460, LONG A1/A0 pop4a464/466. `4a468 BRA4a276`. 실제 callback target 중 3679e/2b3e8/2b3fa/47672가 현재 지원 범위다.
- nested47672: `47672 JSRca70` return47678은 임시 slot을 쓰고 ca74 RTS로 제거된다. sound branch에서 `47682`가 source A0 LONG을 저장하고 `47688 JSR3af8` return4768e를 쓴다. `4768e`는 stack memory에서 A0 LONG을 복원한 뒤 live source BYTE/WORD를 다시 읽는다. outer interpreter saved A0와 다른 슬롯이다.
- spritecd58: `cd5c JSR(A0)` returncd5e는 현재 defaultcd50 RTS fixture로 관측됐다. arbitrary callback의 내부 stack은 이 목록의 지원 범위 밖이다. `ce00 RTS`는 draw caller4a200으로 돌아가며 queue waitcda4 자체는 A7을 바꾸지 않는다.
- soundword high-byte: `3bfa MOVE.B(A0)+,-(A7)`는 **1 BYTE를 쓰되 A7은2 감소**한다. 낮은 주소에 saved low BYTE가 있고 나머지1 BYTE padding은 이 명령으로 쓰지 않는다. `3bfc BSR3ac8` return3c00 LONG을 추가한다. `3c00 MOVE.B(A7)+,D0`는 1 BYTE만 읽고 A7은2 증가한다. 이어 `3c02 BRA3ac8`는 tailcall이므로 return LONG을 새로 push하지 않는다. low-byte wait는 high-byte BSR frame을 이미 제거한 뒤 outer sound return을 top으로 사용한다.

중첩 stack offset과 high/low wait 관측은 animation-callback-continuation.md, animation-direct-sound-contract.md 및 최신 실행 문서에 있다. BYTE padding이 관측에 남아 있어도 새 metadata나 유효 값으로 추론하지 않는다.

## 현재 C++가 stack 메모리 대신 사용하는 지점

| 원본 메모리 동작 | 현재 구현 위치 / metadata | 차이와 검토 대상 |
|---|---|---|
| 4a1dc/1e0, 4a226 / callback A0·A1·bank 저장/복원 | engine/src/animation_execution.cpp `draw`, `callback`, `draw_return`; `saved_a0`, `saved_a1`, `saved_bank` | RAM stack slot을 쓰거나 다시 읽지 않고 host state를 보존·대입 |
| 4a23e PEA / 4a270 list end pop | `indexed_draw`, phase3 resume; `saved_list_end` | list-end LONG memory를 별도 uint32로 대체 |
| 4a204/222, 4a358/376, 4a442/460 MOVEM.W | `draw_return` local low WORD와 `extend_word` | memory4B 쓰기/읽기를 local 값으로 대체; signed restore는 구현하지만 stack alias는 별도 문제 |
| 4a2e2/2ec direct30 MOVEM.L | `direct_sound`; phase4 `saved_a0/saved_a1` | host metadata 복원; callback_return을 쓰지 않음 |
| 47682/4768e source A0 | engine/src/object_sound_lookup.cpp state `saved_a0`; animation phase2 `callback_saved_a0` | stack source LONG 대신 typed continuation; 완료 후 source를 live 재읽음 |
| 3bfa/3c00 saved low BYTE | engine/src/sound_word_execution.cpp `saved_low`; animation `callback_saved_low` + `callback_sound_phase` | stack BYTE/padding 대신 capture BYTE; high/low phase로 제어 |
| JSR/BSR/RTS return LONG와 cd58 wait | C++ 일반 함수복귀, `sprite.waiting`, phase1/2/3/4 | emulated A7/return PC가 state에 없으며 original return stack bytes와 alias 효과는 소비하지 않음 |

이 차이는 현재 isolated/native 대조 범위에서 이미 선택한 표현이며, 향후 whole memory alias 지원의 충분조건이라고 주장하지 않는다. `current_bank_base`는 실제 PVC 쌍에 따른 장치 상태이며 stack WORD saved_bank와 별개다.

## 확인되지 않은 질문 — 메인 의미 판단 필요

1. A7 및 active stack slot과 A5-relative shadow, object/script, queue/source가 겹칠 때 원본의 실제 pop은 변경된 memory를 읽을 수 있다. 현재 metadata와 local WORD 복원은 그 alias를 표현하지 않는다. 어떤 alias를 지원할지, checked 제한을 둘지, 실제 stack bus를 모델링할지는 메인 결정 사항이다.
2. callback이 A7 또는 저장 frame을 변경하는 경우와 미지원 callback의 내부 stack은 조사하지 않았다. 현재 지원 callback 4개/defaultcd50에서 관측한 내용을 모든 callback으로 확대할 수 없다.
3. A7 mirror 내부 경계·mirror→bank 경계, raw32-bit logical SP와24-bit masking 및 BYTE stride2의 조합은 이 목록으로 검증되지 않는다. 최근 program_bus primitive/handler 증거가 whole stack write/return path의 직접 증거는 아니다.
4. 이 목록의 PC witness는 실행 위치 확인이다. caller A7 입력과 RTS가 실제로 읽는 return LONG을 포함하여 모든 caller return 값, 모든 callee branch, padding 초기값과 모든 restore source를 새로 감사한 것은 아니다. 실제 stack 변경 순서가 필요한 통합 계약에서는 해당 trace write/read를 별도로 검토해야 한다.

## 사용한 관측 파일

| 표식 | report | 현재 SHA256 |
|---|---|---|
| A | `artifacts/activation_animation_scripts/observation.json` | `18d25c677ab35698a7662142ce730422c67abcb2df58e7eea8592e141d5e39e6` |
| B | `artifacts/animation_indexed_execution_native/observation.json` | `db3247ceba5327719b84882b7d1abe006f0e30c87d28642ed7c2f9a9f75a6508` |
| C | `artifacts/animation_sound_callback/observation.json` | `5f8b3d3a71532bd3c99d930ad4e61d9c490cc90036669cd872f9169294043108` |
| D | `artifacts/animation_direct_sound_native/observation.json` | `4ef6c7dd0ea871f98dacf1145e1a57fabdffb3ef587cfe3ec8cf55c7871c9386` |
| E | `artifacts/animation_control_commands/observation.json` | `0590de05828d8639340843f06a33417aa32e0370196512bf5a4d17e97165a885` |
| F | `artifacts/animation_word_callback_native/observation.json` | `22e757ea1e727cfed50eaf3ad593b0cf6d2d9115c0beadf3a864220531c3495d` |
| G | `artifacts/animation_rts_callback_native/observation.json` | `b6064ba9908ac25b3d137cadf2dc3914e8df539edee104671b05c5760d8488dd` |

PC witness로 사용한 각 trace의 현재 해시는 다음과 같다. 관측 artifact는 이 문서에 bytes로 복사하지 않았다.

- `003ad6`: D `case_0168_begin_trace.json` SHA256 `84d55e319280727200b3ff1b9cf43d30f1e014128de94d4d3dd0243e3723e4e4`
- `003af6`: C `case_016_ready_trace.json` SHA256 `0c8c099bc9d5cf36527654f91de8c8e21069ce4e7ab8ffda1866bb4a8d441384`
- `003b06`: D `case_0000_begin_trace.json` SHA256 `77239bfc6f0b0cb4783d8b7e8dea50f00d52b47f351dc94a7019afa40424e6fc`
- `003b14`: D `case_0006_begin_trace.json` SHA256 `12f9c782011463c5c07f855754a6b371fb18c117de1d85fe69285b13f7a74ebe`
- `003b1e`: D `case_0012_begin_trace.json` SHA256 `94e1b1f88ad330b51751c065cc35eb3e1c12ce91c99542c60b384b87a4c66776`
- `003b28`: D `case_0009_begin_trace.json` SHA256 `c70ffceb681d2520b6e591a24559574cdd4f93038836f45f3ed9c37f9cad17f1`
- `003b3e`: D `case_0135_begin_trace.json` SHA256 `b4b0a0b6fb0f69840b8b77c2c1ae699922cc553464c15866868b7a3b53303b35`
- `003b5e`: C `case_012_begin_trace.json` SHA256 `9a3e9fb1237c82e7e464b40eb152ed1206c765cdc1274ef932af43bbc16fed8c`
- `003b6c`: C `case_010_begin_trace.json` SHA256 `62b010d1e1d52ee812e5baf8a859606951605b18dfdeb99e761350d5aa690e64`
- `003b80`: C `case_009_begin_trace.json` SHA256 `531da0524616e6d0a1c058dc3dc44e3b8c23b4ce92999b7037a2762c559f3681`
- `003b96`: D `case_0123_begin_trace.json` SHA256 `3a667243e0e309403fdd01281a9fd07303a99a13b31dc989010b55b653801f05`
- `003bc8`: C `case_015_begin_trace.json` SHA256 `607add2dd1224d3a017227d14ed06c61e50788bd93b7a8d79b973502845521db`
- `003be2`: C `case_008_begin_trace.json` SHA256 `e396716d1619b32061ba7656bea534ff322e3a3a5a5aa515ca2eb240101d929b`
- `003bfa`: C `case_016_begin_trace.json` SHA256 `d00a96962c72ef1ba7c7bfd20b8c4137d51723bfbd5a070ee3a13ef552ca7a9e`
- `003bfc`: C `case_016_begin_trace.json` SHA256 `d00a96962c72ef1ba7c7bfd20b8c4137d51723bfbd5a070ee3a13ef552ca7a9e`
- `003c00`: C `case_016_ready_trace.json` SHA256 `0c8c099bc9d5cf36527654f91de8c8e21069ce4e7ab8ffda1866bb4a8d441384`
- `003c06`: D `case_0166_begin_trace.json` SHA256 `2c57d16776ae9a73937b61d81ca028c3d76894b3f1066040a4e180e71b797286`
- `00ca74`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `00cd50`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `00cd5c`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `00ce00`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `02b3f8`: E `case_128_trace.json` SHA256 `c1d712bbec673d6e4289bbf9af401afc63d4f792c40a47a3619aea7164c11538`
- `02b40a`: E `case_153_trace.json` SHA256 `0d6213605f74be30b97347ed07c5e348c9e629d321e0c76e6354c96c6e6ed8d1`
- `03679e`: G `case_0000_begin_trace.json` SHA256 `bde10435f5860f7e8e1285c729b8e2c8ebd19632f8408246d6237ff4135cd9a7`
- `047672`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `047682`: C `case_008_begin_trace.json` SHA256 `e396716d1619b32061ba7656bea534ff322e3a3a5a5aa515ca2eb240101d929b`
- `047688`: C `case_008_begin_trace.json` SHA256 `e396716d1619b32061ba7656bea534ff322e3a3a5a5aa515ca2eb240101d929b`
- `04768e`: C `case_008_begin_trace.json` SHA256 `e396716d1619b32061ba7656bea534ff322e3a3a5a5aa515ca2eb240101d929b`
- `0476ba`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `049fea`: A `case_088_begin_trace.json` SHA256 `6d1419134edf7df111f8905a38996ed9228a4107745255bd78db603f0360cd16`
- `04a0e2`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a104`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a124`: B `case_773_begin_trace.json` SHA256 `0f942a13446fcfb02ecc3356535840a7365d31b2f952ca90d1796aa4b203db0e`
- `04a132`: A `case_020_begin_trace.json` SHA256 `bb87f52a7437c32c0cdf719d0efdf36099ed7f0e0e56246f5296b6a0865ef283`
- `04a148`: A `case_068_begin_trace.json` SHA256 `ce7a7d69eab50be0083bb0b625e812317787eeb0885ab06155d5ced9295dfb06`
- `04a1dc`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a1e0`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a1fa`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a200`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a204`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a222`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a226`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a22a`: A `case_000_begin_trace.json` SHA256 `658ce5bf8a17696a0e7ed33fe13c05c6b3d75a4af8686a49e3d71271b48d28cc`
- `04a23e`: B `case_000_begin_trace.json` SHA256 `569767712ffc8a5f91c602d6a37272c504230a722e9a3ab68b796ff736e426c6`
- `04a26c`: B `case_000_begin_trace.json` SHA256 `569767712ffc8a5f91c602d6a37272c504230a722e9a3ab68b796ff736e426c6`
- `04a270`: B `case_000_begin_trace.json` SHA256 `569767712ffc8a5f91c602d6a37272c504230a722e9a3ab68b796ff736e426c6`
- `04a2e2`: D `case_0000_begin_trace.json` SHA256 `77239bfc6f0b0cb4783d8b7e8dea50f00d52b47f351dc94a7019afa40424e6fc`
- `04a2e6`: D `case_0000_begin_trace.json` SHA256 `77239bfc6f0b0cb4783d8b7e8dea50f00d52b47f351dc94a7019afa40424e6fc`
- `04a2ec`: D `case_0000_begin_trace.json` SHA256 `77239bfc6f0b0cb4783d8b7e8dea50f00d52b47f351dc94a7019afa40424e6fc`
- `04a30c`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a332`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a338`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a352`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a354`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a358`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a376`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a37a`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a37c`: F `case_0000_begin_trace.json` SHA256 `b39570639b027ee9058959a8e4724bb37d84967491a68ac5666bbbab0776818b`
- `04a408`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a41e`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a422`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a43c`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a43e`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a442`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a460`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a464`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`
- `04a466`: C `case_000_begin_trace.json` SHA256 `83094c402052e72c9e96420c8554e85847bd2f4aa91d623919489330d0586971`

원본 ROM과 기존 artifacts는 수정하지 않았으며 새 native 실행·C++ build·커밋은 하지 않았다.
