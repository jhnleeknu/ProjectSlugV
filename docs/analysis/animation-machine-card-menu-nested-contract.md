# 카드 저장 결과 하위 메뉴 프레임과 중첩 복귀(`a698`/`a6da`)·부모 메뉴 닫기 계약

Baseline: 카드 저장 단위(리뷰0238) 통합 커밋. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 범위·경로를 확정했다. 명령 단위 정답은 원본 바이트다. 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `a698..a70a` | `1b7c0000ff1b2b4aff12156a00070008303c00072f0a4ebaf48e245fb5edff0e660000142b4aff12156a00070008303c00004ebaf472246dff126100000670004e752f0a247c00107f0e94fc001043faf920b5d7650000182b4aff126100f4626100f720246dff1294fc001060e4245f4e75` |

## 실행 경로(사실)

진입: 저장 단위 끝(`2ac2`, 결과 메뉴 `107eee` push 직후, -e5=1, -f2=`107eee`, -ee=`107efe`). 이후 자식 재진입(선언 PC=`2ab8`)마다 `a370`이 두 프레임을 모두 돈다(`a380` 루프, 아래 프레임은 `a396` f bit0·4(A2) 검사, hook A4=LONG a(desc)).

1. 결과 메뉴 열림(기존 열림 실행부): c(A2)=3이므로 높이 WORD가 c<<6=`00c0`씩 증가(바이트 5 잔여값 포함). 4≥c인 프레임에서 `a5ea`: 첫 callback 항목(`be84`/`be8f`, callback `bf94`)에 `9b3e` D0=6→`bf94` 7e(A6)←`001e`, D0=0→`a73e` 효과음 `1a6c`.
2. 결과 메뉴 입력 프레임(기존 입력 실행부): hook `bf2c`가 7e를 30프레임 감소, 0이 되는 프레임에서 e=3→`bf94` D0=3→80(A6)=ff, JMP `a70a`→`1a5b`→`a1ee` -e5=2.
3. 결과 메뉴 닫기(기존 닫기 실행부): 6(A2)=1이므로 감소량 `0040`. 높이 0 프레임에서 `a67a` `9e94`, -f2 += 10 → `107efe` < `107f0e` 이므로 `a690` BCS `a698`.
4. **`a698`(새 범위)** BYTE 0→-e5; -ee←A2(부모 프레임); 8(A2)←7(A2); D0.W=7; A2 push; JSR `9b3e`(복귀 `a6b2`, 부모 커서 항목 callback에 D0=7: `c1c4`는 효과 없음); `a6b2` A2 pop; CMPA.L -f2,A2; 같으면 `a6bc` -ee←A2, 8←7, D0.W=0, JSR `9b3e`(복귀 `a6ce`, D0=0→효과음 `1a6c`); `a6ce` A2=-ee; BSR `a6da`(복귀 `a6d6`); `a6d6` MOVEQ 0,D0 RTS.
5. **`a6da`** A2 push; A2=`107efe`; LEA `a008`,A1; 루프 `a6ea` CMPA.L (A7),A2, BCS `a706`(unsigned A2<push값); 아니면 -ee←A2, BSR `9b58`(복귀 `a6f8`), BSR `9e1a`(복귀 `a6fc`), A2=-ee-10, 반복; `a706` A2 pop, RTS. 아래(오래된) 프레임부터 현재 프레임까지 다시 그린다.
6. 다음 재진입: 부모 메뉴 -e5=0→`a406`→hook `bf2c`: 7e=0이면 감소 없음, 80(A6)≠0→`bf50` JSR `a70a`→-e5=2. 이후 부모 닫기 프레임(6(A2)=4, 감소 `0100`), 빈 stack→`c2c8` 페이드·7e=14 타이머→부모 62=ff·`2a00`(기존 닫기 단위 경로).

## 구현 범위와 규약

- 새 실행부 파일 `engine/src/animation_machine_card_menu_nested.cpp`(함수 `animation_card_menu_nested_block`): `a698..a708`.
- Block 시작 PC: `a698` `a6b2` `a6bc` `a6ce` `a6d6` `a6da` `a6ea` `a6f0` `a6f8` `a6fc` `a706`. 그 밖 내부 PC 직접 진입 거부(`unsupported animation card menu nested PC`). 묶음: `a6b4` CMPA.L+BNE, `a6ea` CMPA.L (A7)+BCS.
- 닫기 단위의 `a698` 경계와 열림 단위의 `a6da` 경계(`a3b4` BSR `a6da`)는 이번 실행부로 실행된다. 기존 테스트·검증기의 해당 unsupported 경계는 아직 실행부 없는 PC로 옮긴다.
- Carry: FLOW_ONLY-only block만 보존(구현자가 원본 opcode로 계산해 보고). 그 밖 Unknown.
- 모든 읽기·쓰기는 live bus, 원본 순서·크기. CMPA.L (A7) LONG 읽기는 live stack에서 한다.

## 검증 조건(최소)

- 연결: 저장 단위 C++ 마지막 출력(`10fdc6`=0, SAVE OK)에서 재진입 체인: 결과 메뉴 열림 프레임→`a5ea`(7e=1e)→30 입력 프레임→결과 메뉴 닫기 프레임→`a698` 중첩 복귀(`a6da` 재그리기)→부모 `bf2c` 80≠0→부모 닫기 프레임→`c2c8` 페이드·타이머→`2a00` 자식 제거→부모 객체 재진입→`2a00`→`2ac2`. NO SAVE(`c232`) 갈래도 최소 `a698`까지.
- 경계: 세 프레임 이상 stack(`a6da` 루프 3회), `a6b4` 불일치(`a6ce`로 바로), D0=7 callback이 효과를 내는 descriptor fixture, 홀수 A2/A7 오류 rollback, 내부 PC 거부, Unknown 진입 carry.
- 비교 항목은 기존과 같다.

## 미확인·범위 밖

부모·자식 제거 뒤 다음 객체·장면, BIOS 카드 처리 내부, video port 화면 의미, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
