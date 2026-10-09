# 카드 자식 callback c250의 페이드·장면 준비·타이머 계약

Baseline `e25f276`, branch `codex/animation-machine-card-menu`. 메인(Claude Opus 5.5)이 canonical BE ROM(SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, fixed CPU 주소=file offset)을 직접 디코드해 확정했다. 구현·원본 동등성 완료 보고가 아니다.

## 원본 바이트 근거

| CPU 범위 | 원본 바이트 |
| --- | --- |
| `c250..c2a8` | `70e172e174e176004eb900008c162cbc0000c2664e754eb9000de42470007200740076144eb900008c163d7c0014007e2cbc0000c286536e007e650000044e751d7c00000080206e0076302e007a322e007c4eb90000a29c` |
| `de424..de48c` | `4eb9000e7c16303c00493b7c0000801033fc1000002ffff233fc0000002ffff020790020000ce548207000004eb900008da241faffb44eb900043ffc41f9001091564eb900016fac43faffae347c00007000721f4eb900016ff84eb90001861a4eb9000170124e75` |
| `de40c..de424` (데이터) | `000400000008000200109156000000030049000000140010` |
| `e7c16..e7c36` | `4ebaffdc41faffa44eb900008da2303c00fe323c0001343c000c4ef900008cda` |
| `e7bc0..e7bf4` (데이터) | `000b01b40200000c01bd020000fd03e8020000fe03e80200ffff000b025f0200000c00650200000d00670200000e006a0200ffff` |

## 실행 의미(사실)

1. 자연 연결: 부모 `480ac`가 62=0으로 `480b4` RTS→`2ac2` MOVEA.L 8(A6),A6. `28ae`가 자식을 부모 바로 뒤에 넣었으므로 A6=자식, `2ac6` BRA→`2ab8`→`2abe` (A6)=`c250`→`2ac0` JSR (A0). host 변경 없이 이어진다.
2. `c250` MOVEQ e1→D0/D1/D2, MOVEQ 0→D3(32bit), JSR `8c16` 복귀 `c25e`; `c25e` LONG c266→(A6); `c264` RTS.
3. `c266` JSR `de424` 복귀 `c26c`. `de424`: JSR `e7c16` 복귀 `de42a`; `de42a` D0.W=0049; `de42e` WORD 0→A5-7ff0(live A5), WORD 1000→`2ffff2`, WORD 0→`2ffff0`; `de444` A0=LONG `20000c`(현재 bank), D0.W<<=2, A0=LONG (A0+sign D0.W); JSR `8da2` 복귀 `de456`; A0=`de40c` JSR `43ffc` 복귀 `de460`; A0=`109156` JSR `16fac` 복귀 `de46c`; A1=`de41c`, A2=0(MOVEA.W 부호확장), D0=0, D1=1f, JSR `16ff8` 복귀 `de47e`; JSR `1861a` 복귀 `de484`; JSR `17012` 복귀 `de48a`; RTS. 이는 부모 `47fe8..4804e`와 같은 helper이며 descriptor/node/palette/map header만 다르다.
4. `e7c16`: BSR형 JSR `e7bf4`(기존) 복귀 `e7c1a`; A0=`e7bc0` JSR `8da2` 복귀 `e7c24`; D0.W=fe, D1.W=1, D2.W=c; JMP `8cda`(기존, 그 RTS가 `de42a`로 돌아감).
5. `c26c` MOVEQ 0→D0/D1/D2, MOVEQ 14→D3, JSR `8c16` 복귀 `c27a`; `c27a` WORD 14→7e(A6); `c280` LONG c286→(A6); 같은 실행에서 `c286`.
6. `c286` SUBQ.W #1,7e(A6), `c28a` BCS `c290`. C는 SUBQ의 unsigned borrow(이전 WORD가 0)이며 같은 block에서 소비한다. borrow가 없으면 `c28e` RTS. 첫 SUBQ는 같은 실행에서 14→13이며 이후 재진입마다 감소해 0에서 한 번 더 감소할 때(ffff) `c290`으로 간다.
7. `c290` BYTE 0→80(A6), A0=LONG 76(A6), D0.W=7a(A6), D1.W=7c(A6), `c2a2` JSR `a29c` 복귀 `c2a8`. `a29c`(메뉴 초기화 `a0a0` 경유)·`a2b8`·`a370` 메뉴 프레임은 이번 범위 밖이며 `a29c`가 stop 경계다.

## 구현 범위와 규약

- 새 실행부(파일 `engine/src/animation_machine_card_child.cpp`): `c250..c2a2`, `de424..de48a`, `e7c16..e7c30`. 기존 `8c16`, `e7bf4`, `8da2`, `8cda`, `43ffc`, `16fac`, `16ff8`, `1861a`, `17012`, 디스패처 실행부를 그대로 호출 경로로 쓴다. 기존 범위를 가리지 않는다.
- 묶음: `c286`+`c28a`(BCS). `c28a` 직접 진입 거부. `de444..de44c`는 같은 block로 처리할 수 있다.
- Carry 보존 block: 전체가 JSR/JMP/BSR/BRA/RTS/LEA/MOVEA인 block만(`c258`,`c264`,`c266`,`c274`,`c28e`,`c2a2`,`de424`,`de450`,`de456`,`de45a`,`de460`,`de466`,`de46c`,`de478`,`de47e`,`de484`,`de48a`,`e7c16`,`e7c1a`,`e7c1e`,`e7c30` 등; MOVEA.W #0 포함 block은 MOVEA이므로 보존). MOVE/MOVEQ/SUBQ/LSL 포함 block은 Unknown. `c286`의 borrow는 내부 분기에서 소비하고 이후 C는 Unknown으로 둔다(원본은 known이지만 기존 SUBQ timer 처리와 일관되게 노출하지 않는다).
- `a29c`는 실행부가 없다. stop을 `a29c`로 주면 return `c2a8`이 stack에 남은 상태로 멈추고, 다른 stop은 checked 오류·전체 rollback이다.
- 프레임 재진입: 자연 연결 단계(부모 RTS→2ac2→자식) 이후 자식 프레임은 직전 출력(stop `2ac2`, A6=자식)에서 PC=`2ab8`만 바꾸는 선언 변경이다. 부모 `480ac`와 다른 객체의 매 프레임 실행은 생략한 fixture이며 자연 scheduler가 아니다.
- 모든 descriptor·node·palette·map 읽기는 실제 접근 시점 live bus로 하고 미리 decode하지 않는다. 리소스 형식(MS5D v1 kind3)·loader/bus는 바꾸지 않는다.

## 검증 조건(최소)

- 연결: fade_card native의 BIOS 재개 할당 성공 출력(자식 생성)에서 부모 `2ab8` 프레임→`480b4` RTS→`2ac2` stop, 그 실제 출력에서 host 변경 없이 `2ac2`→`2ab8` stop, 다시 `2ab8`→자식 `c250` 실행→RTS→`2ac2` stop.
- 자식 프레임 체인: `c266` 프레임(de424 전체: e7c16 palette, 8da2 palette49, 43ffc scene, 16fac/16ff8 node, 1861a map 전송, 17012), 타이머 재진입, `c290`→`a29c` stop. 대표 프레임 fresh split/continuous.
- 경계: 7e=0 진입(즉시 borrow→c290), 7e=1, 7e=8000(BCS는 부호와 무관하게 이전 WORD가 0일 때만 borrow이므로 7fff로 감소하고 `c28e` RTS), 76/7a/7c(A6) live 읽기, `20000c`의 현재 bank 읽기, a29c 이외 stop rollback, `c28a` 직접 진입 거부, 홀수 A6.
- 비교 항목은 기존과 같다. 기존 회귀의 unsupported 경계로 쓰인 PC가 새로 지원되면 아직 미지원인 PC(`a29c`)로 옮긴다.

## 미확인·범위 밖

`a29c/a0a0/a2b8/a370` 카드 메뉴, descriptor `c188`의 callback `c1c4`(a73e/bd26/9f36/a71a/a216)와 BIOS 재호출 여부, `c2c8` 이후 페이드·부모 62=ff·`2a00`, BIOS 내부, 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체 Goal.
