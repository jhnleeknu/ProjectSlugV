# 맵 뒤 페이드·타이머·프레임 재진입과 BIOS 카드 경계 계약

Baseline `55606fa`, branch `codex/animation-machine-fade-card`. 이번 세션은 Claude Opus 5.5가 메인 분석·리뷰·통합을 맡는다. 메인이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)의 원본 바이트를 직접 디코드해 아래 순서·폭·분기를 확정했다. 이 문서는 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `4804e..480bc` | `700072007400363c00404eb900008c163d7c0080007a2cbc0004806a536e007a670000044e7570e172e174e1363c00204eb900008c163d7c0020007a2cbc00048090536e007a670000044e754eb90000caf04eb90000c3642cbc000480ac4a2e0062660000044e754ef900002a00` |
| `c364..c3c0` | `2f0e13fc00010010fdc433fc02680010fdce4eb900c004682c5f4bf9001080000c2d00807dc66700002c422e0062207c0000c250303c00004eb9000028ae217c0000c1880076317c0004007a317c0004007c4e751d7c00ff00624e75` |
| `28ae..2918` | `4bf900108000b07900104ca064000052b0fc00006700004a2f08206dcc9c2b680008cc9cb0fc000067000006536dcca0214e000c302e0010524031400010226e0008214e000421490008234800042d480008209f116e006a006a003c00014e7541ed8e98023c00fe4e75` |
| `2a00..2a0a` | `619a2e6dcca4600000ba` |
| `2aac..2ac8` | `4df90010082023cf00104ca44bf90010800020564e902c6e000860f0` |

## 실행 의미(사실)

1. `4804e` MOVEQ 0→D0/D1/D2, `48054` MOVE.W #40→D3(상위WORD 보존), `48058` JSR `8c16`(기존 페이드 leaf, A5=108000 자체 설정) 복귀 `4805e`.
2. `4805e` MOVE.W #0080→7a(A6), `48064` MOVE.L #4806a→(A6). 같은 실행에서 `4806a`로 떨어진다.
3. `4806a` SUBQ.W #1,7a(A6) 다음 `4806e` BEQ.W `48074`. Z는 SUBQ 결과 WORD가 0인지로만 결정한다. 0이 아니면 `48072` RTS가 현재 A7의 LONG을 pop한다(디스패처에서는 `2ac2`). 최초 진입 직후 7a=7f이므로 첫 RTS는 항상 발생한다. 이후 `4806a`는 디스패처 재진입으로만 도달한다.
4. `48074` MOVEQ e1→D0/D1/D2(32bit ffffffe1), `4807a` MOVE.W #20→D3, `4807e` JSR `8c16` 복귀 `48084`. `48084` 7a=0020, `4808a` (A6)=48090, `48090` SUBQ.W/BEQ `4809a`, `48098` RTS.
5. `4809a` JSR `caf0`(기존 화면 reset) 복귀 `480a0`, `480a0` JSR `c364` 복귀 `480a6`, `480a6` (A6)=480ac, `480ac` TST.B 62(A6)/BNE `480b6`, 0이면 `480b4` RTS. `480b6` JMP `2a00`.
6. `c364` MOVE.L A6,-(A7); `c366` BYTE 01→`10fdc4`; `c36e` WORD 0268→`10fdce`; `c376` JSR `c00468` 복귀 `c37c`. `c00468`은 BIOS 영역이며 이번 구현은 이 PC를 실행하지 않는 경계로 둔다. 임의 stub이나 가상 RTS로 BIOS 완료를 만들지 않는다.
7. BIOS 뒤 `c37c` MOVEA.L (A7)+,A6(live pop), `c37e` LEA 108000,A5, `c384` CMPI.B #80,7dc6(A5)=`10fdc6`, BEQ `c3b8`. 같으면 `c3b8` BYTE ff→62(A6), RTS. 다르면 `c38e` CLR.B 62(A6), A0=c250, D0.W=0, JSR `28ae` 복귀 `c3a2`; `c3a2` LONG c188→76(A0), WORD 4→7a(A0), WORD 4→7c(A0), RTS. CLR.B는 read-modify-write를 하지 않는 단일 BYTE write로 기록한다(68000의 dummy read는 이 계층에서 관측하지 않는다).
8. `28ae` 자식 할당: A5=108000; CMP.W `104ca0`,D0 다음 BCC `290e`(unsigned D0.W ≥ count이면 실패); CMPA.W #0,A0(부호확장 비교=32bit A0==0) BEQ `290e`; A0 push; A0=LONG -3364(A5)=`104c9c`; LONG 8(A0)→`104c9c`; CMPA.W #0,A0가 0이면 SUBQ 생략, 아니면 SUBQ.W #1,`104ca0`; 0이어도 이후 쓰기를 계속한다(주소 c 등 ROM 쓰기는 원본 fault, C++는 checked 오류). 이후 c(A0)=A6, D0.W=10(A6)+1→10(A0), A1=8(A6), 4(A0)=A6, 8(A0)=A1, 4(A1)=A0, 8(A6)=A0, (A0)=pop LONG, 6a(A0)=BYTE 6a(A6), ORI CCR #1, RTS(known Set). 실패 경로 `290e` A0=108000-7168=`100e98`, ANDI CCR #fe, RTS(known Clear). 모든 operand는 실제 접근 시점의 live RAM에서 읽는다(앞선 쓰기 alias 포함).
9. `2a00` BSR `299c`(기존 cleanup 실행부) 복귀 `2a02`; `2a02` MOVEA.L -335c(A5)=`104ca4`→A7; `2a06` BRA `2ac2`.
10. 디스패처 `2ab8` LEA 108000,A5; `2abe` MOVEA.L (A6),A0; `2ac0` JSR (A0) 복귀 `2ac2`; `2ac2` MOVEA.L 8(A6),A6; `2ac6` BRA `2ab8`. `2aac`/`2ab2`(A6=100820, SP 저장)는 이번 범위의 진입이 아니다.

## 구현 범위와 규약

- 새 C++11 실행부 `engine/src/animation_machine_fade_card.cpp`: `4804e..480b6`, `c364..c3be`, `28ae..2916`, `2a00/2a02/2a06`, `2ab8/2abe/2ac0/2ac2/2ac6`. 기존 `8c16`/`caf0`/`299c` 실행부를 그대로 호출 경로로 사용하고 가리지 않는다. 기존 AnimationMachineContext/am_read/am_write/am_push/am_pop/am_call/am_return만 쓴다.
- Z/N 소비 분기는 writer와 같은 block에 묶는다: `4806a`+`4806e`, `48090`+`48094`, `480ac`+`480b0`, `c384`+`c38a`, `28b4`+`28ba`, `28be`+`28c2`, `28d2`+`28d6`. 묶인 분기 PC(`4806e`,`48094`,`480b0`,`c38a`,`28ba`,`28c2`,`28d6`)의 직접 진입은 거부한다.
- 실제 checkpoint로 노출하는 PC: `4804e`,`4805e`,`4806a`,`48074`,`48084`,`48090`,`4809a`,`480a0`,`480a6`,`480ac`,`480b6`,`c364`,`c37c`,`c38e`,`c3a2`,`c3b8`,`28ae`,`290e`,`2a00`,`2a02`,`2ab8`,`2ac2` 및 RTS PC. 그 밖의 내부 PC는 원본 block 경계에 맞춰 정한다.
- Carry: `28ae` 성공 RTS 앞 ORI CCR #1은 known Set, 실패 ANDI CCR #fe는 known Clear다. 전체 block이 LEA/MOVEA/JSR/JMP/BSR/BRA/RTS/MOVEM만인 block(`2a00`,`2a02`,`2a06`,`2ab8`,`2abe`,`2ac0`,`2ac2`,`2ac6`,`c37c`,`c37e`,`480a0`,`4809a`,`480b6` 등)만 C를 보존한다. MOVE/MOVEQ/CLR/SUBQ/TST/CMP를 포함하는 block은 Unknown으로 만든다. 이는 원본 opcode 분류이며 native C 측정이 아니다.
- `c00468`은 실행부가 없다. 호출자가 stop을 `c00468`로 주면 JSR이 실제 return `c37c`와 저장 A6을 stack에 남긴 상태로 멈춘다. stop이 다르면 checked 오류와 전체 rollback이다.
- BIOS 뒤 재개는 실제 BIOS 실행이 아니다. 선언된 host 변경은 (a) PC=`c37c`, (b) A7+=4(BIOS RTS가 `c37c`를 pop한 효과), (c) `10fdc6` 응답 BYTE 하나뿐이며 다른 BIOS 효과(카드 RAM, 레지스터 파괴)는 미모델·미확인으로 기록한다. BIOS가 CCR에 주는 효과도 미확인이므로 재개 carry는 Unknown으로 둔다(`c00468` stop 시점의 C도 `c364` block 때문에 Unknown이다).
- 프레임 재진입은 자연 scheduler가 아니다. 선언된 host 변경은 직전 출력에서 PC=`2ab8`만 바꾸는 것이다(A6는 실제 직전 출력에 남은 객체, A7은 직전 RTS 뒤 값). 다른 객체 callback·IRQ·VBlank 효과는 없다고 선언한 fixture이며 그렇게 표시한다.
- 8c16 페이드, caf0 화면 reset의 port/RAM 출력은 instruction-unit port 기록이며 물리 bus cycle·VRAM 화면 완성이 아니다.
- 리소스 형식(MS5D v1 kind3)·loader/bus는 변경하지 않는다. ROM·추출물은 수정하거나 Git에 추가하지 않는다.

## 검증 조건(최소)

- Connected: 기존 map_transfer connected fixture(47fe8 시작)를 4804e 너머로 이어서 `48072` RTS→`2ac2` stop까지.
- 타이머1: 최초 같은 실행의 SUBQ 1회 뒤 2ab8 재진입 127회째에 `48074` 진입, 두 번째 페이드와 같은 실행의 SUBQ(7a=1f), 재진입 31회째(전체 재진입158회째)에 `caf0`, `c364`→`c00468` stop. 전체 프레임 체인을 직전 실제 C++ 출력 재개로 이어 붙이고, 대표 프레임은 fresh native split/continuous로도 비교한다.
- BIOS 재개: 응답 `80`(62=ff→480ac→2a00→299c→2a02 A7 load→2ac2), 응답≠80(자식 할당 성공·free count 0 실패·head 0 fault 각각), 이후 `480ac` 재진입 RTS.
- 경계: 7a=0 진입 WORD wrap(ffff, RTS), 7a=1 진입(즉시 다음 단계), 28ae live alias(앞선 쓰기가 이후 operand를 바꿈), pushed A0/A6 stack이 RAM 쓰기로 바뀌는 live pop, odd A6/A0·JSR (A0) odd target 오류, 묶인 분기 PC 직접 진입 거부, `c00468` 이외 stop 시 rollback.
- 비교 항목은 기존과 같다: full64KiB RAM/16R/PC/A7/carry 분류/PVC-device/bank/ordered ports/external reads/status, 현재 입력·산출물 SHA, ROM stat 불변.
- 기존 회귀의 `4804e` unsupported 경계는 실제로 아직 실행부가 없는 PC로 옮긴다(`c00468` 또는 `480bc`). 역사적 정상 stop은 유지한다.

## 미확인·범위 밖

- BIOS `c00468` 내부, 카드 응답 값의 실제 의미, 자식 `c250`/`c188` callback 본문, `480bc` 프레임 helper 묶음(47642/1a73c/49b0c/4aa88/b4a2a/6f1c2/4701e/e8a48/2efa6), `2ac2` 이후 다른 객체 callback, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal 완료.
