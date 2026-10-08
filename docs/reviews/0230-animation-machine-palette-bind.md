# 팔레트 연결·노드 준비의 실제 공유 스택 리뷰

대상 baseline `5cb6256`, 브랜치 `codex/animation-machine-palette-bind`. 최종 대상은 이 문서를 포함하는 로컬 통합 커밋이다. 기존 전체 목표·완료 기준·진행을 승계한다.

## 원본 의미와 구현

Canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Fixed CPU 주소는 같은 파일 offset이다. 메인은 실제 명령과 리소스 경로를 읽고8da2/8e82/e7bf4/e7c36/16fac/16ff8 및47ff2→48042의 접근 순서·폭·호출 규약을 확정했다. 기존8e4a/8cda/43dda를 공유 RAM/A7 실행부로 재사용한다. 과거3R/9R API의 지역 변수나 사전 해석 테이블로 스택·live operand를 대체하지 않는다.

8da2는 unlink 쓰기 후 bucket tail을 다시 읽고, reference/ID 게시 후 flags BYTE를 읽는다. WORD slot shift의 wrap과 signed index를 그대로 적용한다. 실제 BSR/JSR/RTS와 tail JMP를 구분한다. 16ff8의 signed12 계산은 unsigned mask와 명시적인 sign bit 확장으로 구현해 음수 shift에 의존하지 않는다. 노드+26은16fac가 지우지 않는다.

실제 bank2 경로는 CPU20000c→2003d0, CPU2004c0→201ec0이다. 각 upper fixture는 LONG 두 번과 WORD/WORD/BYTE/WORD를 읽는다. 원시 창16byte와 실제 접근15byte를 구분한다. 기존 MS5D v1 kind3 여덟 개와 실제 C++ loader/bus를 사용한다. 480f2는 이 범위에서 주소만 전달하며 header payload를 읽었다고 주장하지 않는다. 48042의 JSR1861a는 실행 전 경계다.

## 원본 비교와 경계조건

Native 정상58조건140split/58continuous와5guard를 두 번씩 실행해252freshCPU/416단계를 확보했다. 실제 C++58조건140단계·직전 출력82회 재개가 full64KiB RAM/16R/PC/A7·장치PVC/bank·77포트와 일치했다. 정상 포트는watchdog69/PVC8이며 대기·외부status읽기·native C 측정은0이다. 독립 ordered PVC 계산으로24bank read와680fixed read를 확인했다.

Live flags operand가 선행ID 쓰기로12가 된 뒤92가 게시되는 사례는8e36까지만 검증한다. 변경된 terminator 뒤의 정상 복귀를 가정하지 않는다. unlink가 바꾼 bucket head를 실제로 다시 읽는 경우와, 실제 RTS 값이0004f080 또는40000으로 바뀌는 경우도 검증한다. 후자는 도달한 stop 경계이지 자연 게임 실행의 증거가 아니다.

실패21조건(추가16+nativeguard5)과zero-step33조건이 모든 API 출력 보존을 확인했다. 원본의 부분 fault 효과와 checked API rollback은 별개다. 초기3ef2/선택적e7bf4 실행은 선언된 새 fixture 준비이며 실행 도중 예상값을 주입하지 않는다. SR은 초기화 이후 읽지 않는다.

Native source SHA `74cabb1c2fa0acc922a8f3d5ff2a1a56cb979b6ea4d0e6b99f695d1d11b3b90a`, report SHA `0ce478765207df8625a9a8065fb0f75ce68604b6df7a822bd8ac0d0ec5648afb`. C++ verifier SHA `d7a3856837d7a402408255c887bb0b2346be93e1889c23462a828e8cf890a959`, report SHA `fda00cf15928f1b1f34598aabe6b1f036ef3a46b4f4b5950066a9b39489cf5d0`.

## 기존 경계 검사 수정

기존screen/cleanup/scene의 명시적 unsupported PC 검사는 새 미지원 경계48042로 이동했다. 역사적 정상stop47ff2와 원본 관측은 유지했다. 기존 whole scene fixture의 난수 팔레트 RAM 및 cleanup의 독립 self-linked slot은 binding bucket 초기화 조건이 아니다. 새 경로까지 계속 실행하면 각각 write-device/alignment 오류가 발생함을 메인이 실제 새 harness로 확인했다. 초기 입력을 바꾸지 않고 해당 검사명·예상 오류를 실제 guard에 맞췄다. 이 두 검사를48042까지의 성공 도달 증거로 계산하지 않는다. 새 관측기의 네 upper fixture가 적절한 원본 초기화 후48042 도달을 별도로 검증한다.

## 빌드·독립 검토

메인 `make -j4 all test` exit0: Python257개/C++161개 실행, 경고0. 로그 `/tmp/ms5-palette-bind-main-make.log`. 신규 unit 일반/UBSan 각각65 API 호출, 별도 실제kind3 loader 연결66회 통과. Core SHA `5e8af3b674998e31ee95e09241ad3f5620974ad415a00187f0b939c932994190`, unit SHA `10a02be99c613911cd241cf153220fed66ca790bbb6ee7245fe3e72316b67ac6`.

Sol6.1/medium3명이 구현, 원본 관측, 비교기·문서를 분담한 뒤 교차 검토했다. 독립 원본 감사는29조건73split/29continuous와 모든5guard·1654현재 참조를 재검사했다. 별도 core/비교기 리뷰는 새25개 C 보존 block을7LEA/4RTS/1BSR/8JSR/2JMP/2MOVEA.L/1MOVEA.W로 확인하고2855현재 참조를 검사했다. 이 분류는 native 일반CCR 측정이 아니다. 메인은 실제 소스·리뷰 기록·접근 순서·명시적인 정수 연산과 빌드 결과를 확인했다.

독립 감사 기록 SHA는 native `cbdf05ddefdbdb66a7c0bd5704d2b5700cbf28c5eb454d7bd5985079fda04fe1`, core `6b0ebaa2e09f1b363026a702f5034b3c074764073f3452fabf4f2af1d79b9580`이다. 임시 파일의 존속은 재현 전제가 아니며 정식 도구·계약·검증 명령을 저장한다.

## 남은 범위

다음은48042의 map update와 후속 frame 연결이다. 자연 scheduler·입력·IRQ/timing·일반CCR·직접플레이·전체스테이지/적/보스·미사용자료 전체 의미는 미완료다. 부분 애니메이션14/17(약82%)+14/3c 일부를 전체 게임 복원율로 확대하지 않는다. 전체 Goal은 active다.

다음 맵 구간의 초기 조건도 점검했다. 현재 새 upper 네 fixture의 node10d256+26은ffff이며16fac가 이를 보존한다. 이 입력을 그대로 연장하면183c6의 primary tile 전송을 건너뛴다. 메인이 실제 fixture RAM을 재확인했다. 다음 검증은 앞선43ffc 실행으로 준비한 유효 slot 또는 명시적인 별도 초기 조건에서 실제 tile 전송을 확인해야 한다. 현재 팔레트 검증을 화면 그리기 성공으로 확대하지 않는다.


## 최종 회귀와 참조 감사

기존11개 공식 회귀가 모두 통과했다. 메인은 새 palette binding을 포함한12개 보고서의 현재 입력·산출물 SHA와 중복 경로 일관성을 직접 확인했다. 고유 합집합35106개가 일치했다. 각 담당자의 현재 참조 감사도 통과했다.

| 보고서 | SHA256 | 고유 참조 |
| --- | --- | ---: |
| `animation_machine` | `3b404114f697594bc4ecb556208a411cb3b88a88f05a50fb70562cd5d5f048ed` | 1718 |
| `animation_machine_callers` | `ca9cc122d2f0004e843a4641fe87ba4cfd24f04265da621ba3f6fc8d3434dea4` | 1244 |
| `animation_machine_carry` | `5da07311ac9b8a1c8352a9f92302971de698ef6a177e19b3f76df0fb413420a9` | 3053 |
| `animation_machine_activation` | `4de8c9ff9e3db56e154cbc0171afa777d4a22f2c8afa67fe12def099cae22286` | 1047 |
| `animation_machine_readiness` | `685c804d1f7e32a7f028d7c6afcd8505fc64c304cf92bda8848b432a74b2c866` | 2986 |
| `animation_machine_hud` | `1b6320161a2c42e0f19beeb7e5d97cfefc888d6f8dbab44312d312130413c22c` | 4999 |
| `animation_machine_transition` | `8f3804391e345ba5707aeb9694171a2f76534364adf265441880797e1eeeb8b3` | 4207 |
| `animation_machine_exit` | `eb2c63f17f11f8525b69cc828af55d807fc7619d3148677f438b093848a6797d` | 4654 |
| `animation_machine_screen` | `a869563968a8b3fecb14a6ece074296851dd858a1697ea29509c5267da0dfb65` | 2586 |
| `animation_machine_cleanup` | `803607c650095d0d05e66e81694f41da266b854a19881bebffddbe7a57776d9a` | 2546 |
| `animation_machine_scene` | `150248a63dc57282b1b2d75ecb4912eb4512e2e17bb787dd1f385cc2106a2140` | 4280 |
| `animation_machine_palette_bind` | `fda00cf15928f1b1f34598aabe6b1f036ef3a46b4f4b5950066a9b39489cf5d0` | 2855 |

원본·추출 데이터는 포함하지 않고 소스·도구·규격·검증 문서만 커밋한다. 실제diff와 신규 파일을 포함한 staged whitespace 검사도 통과했다. 원격이 없어 로컬 리뷰·커밋으로 통합하며 PR이라고 부르지 않는다.
