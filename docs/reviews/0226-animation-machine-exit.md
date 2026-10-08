# 카운터 종료와 후속 콜백 연결 리뷰

대상 baseline `21d818c`, 브랜치 `codex/animation-machine-exit`. 최종 대상은 이 문서를 포함하는 통합 커밋이며 로컬 리뷰다. 기존 목표 범위·완료 기준·진행을 유지한다.

## 원본과 변경

메인은 canonical BE SHA `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`의47eac..47fca,1c63c,30f4,48398,8c16 및 작은 helper를 C++ source/routing과 대조했다. fixed CPU 주소는 같은 ROM 파일 offset이며 뱅크 주소와 구분한다. 종료 초기화→실제48980 script→애니메이션, timer·두 player flag→lookup·47c5a, 여러 사운드 호출→LONG 저장/복원→palette·flag clear를 기존 공유 RAM/A7 실행기에 연결한다.

47f74/47f82 MOVEM.L은 전체 D0를 live stack에 저장·복원한다.8c16은 내부 JSR가 없는 기존 full15R leaf를 재사용한 뒤 RAM의 실제 return을 pop한다.35개 새 C 보존 block은 실제 JSR/BSR/RTS/LEA/MOVEA/MOVEM/BRA/BCC로 확인했다. 다른 block은 보수적으로 Unknown이며 flag만 소비하는 임의 PC 진입은 제공하지 않는다. 최종47fca의 JSRcaf0는 실행 전 경계다.

MS5D v1 kind3 여덟 개와 실제 C++ loader/bus를 사용한다. 원본 ROM·추출물은 변경하거나 Git에 포함하지 않는다. PNG·오디오 확인본을 런타임 데이터로 대체하지 않는다.

## 발견 사항과 해결

- 독립 검증기 리뷰는47c5a의 지원 밖 쓰기에 대한 예상 오류 문자열을 지적했다. 일반 am_write와 program-stack writer의 오류 경로가 다르므로 실제 direct-write 오류를 확인하도록 수정했다.
- 첫 공식 대조는 원본 재실행과 정상 C++ 비교를 통과한 뒤 custom odd object-write 오류 문구에서 중단했다. 읽기/stack의 정렬 오류 문구를 direct am_write에 잘못 기대한 두 검사를 수정했다. 실패 당시 성공 보고서는 생성되지 않았다. 실제 runtime mismatch와 테스트 기대값 문제를 구분한다.
- 실행 문서 초안의 transition 계약 pin 표현은 실제 HUD+exit pin과 맞지 않아 문서를 수정했다. 실제 새 exit 계약은 첫 공식 실행 전부터 입력 해시에 포함되어 있다.
- 원본 odd-write guard 후보는 Unicorn의 pre-write hook 정지 뒤에도 쓰기가 반영될 수 있어 재현된 접근 기록의 완전성을 보장하지 못했다. 해당 후보를 원본 증거에서 제외했다. C++의 odd-write 원자성 검사는 별도로 유지하며 CPU fault rollback으로 해석하지 않는다.
-480bc에서 callback PC를 수동 설정한 실행을 자연적인 다음 frame으로 취급하지 않는다. 늦은47f0a/47fa8 조건은 fresh 통제 fixture이고, 동일 CPU에서 sound/animation 대기를 재개한 조건과 구분한다.

## 검증 기록

메인 `make -j4 all test` exit0: Python257개, C++157개 실행, 경고0. 로그 `/tmp/ms5-exit-main-make.log`. 신규 unit은 일반·UBSan 각각419회 API 호출을 통과했다. Source SHA `bfbdf82a95e234df06901d3ac732b491bcbfe1a005df80e94678ad620a316177`, unit SHA `5b6677e61288c769cba64d82f4610f60f98be44ed5fc0a70e0320b8305d24182`.

동결 원본 관측은 정상90조건252split/112continuous단계와 guard3조건이다. 전체257split/115continuous를 각각 두 번 실행해372freshCPU/744단계를 확보했다. 대기22단계, 정상PVC190포트·외부읽기0회다. 실제 JSR marker alias, saved LONG8123ab00/89abcdef의 마지막19dc flush 대기 뒤 pop, palette write가 RTS target을200으로 바꾸는 조건을 포함한다. lookup publication이 return을60fff000으로 바꾸는 조건은 backend fetch guard로 분류한다.

Observer source SHA `ed153a295259e691349b0cd5a13df48046a6c24b3eb6648f02702ca5c34967bc`, native report SHA `026585bc88057054d188978774aa8ce436ca7f97aaa6c2ffd459c5ca1a888bf3`. 최종 C++ 대조도 정상90조건252단계·직전 실제 출력162회 재개를 통과했다.22wait·190PVC포트·외부읽기0회, 실제 BCC의 known C44단계가 일치했다. 오류17조건(추가14+원본guard3)과 zero-step21조건도 통과했다. 메인은 현재4650개 고유 참조와 native2874개 참조의 해시를 직접 검사했다.

최종 비교기 SHA `6a60a33bd3b53682f780467e9cd494f45201527bd6015717c652b9b9e8105d91`, 보고서 SHA `12fae62c0c40ffd431435c5a550d935692f07192f05badab23ad1475f42be8e8`. 독립 최종 감사도 실제 exit 계약·동결 core/harness·원본을 포함한4650개 참조와 수정된 오류 검사를 확인했다. 일곱 기존 회귀 결과는 아래 최종 통합 기록을 따른다.

독립 native 감사는93fixture metadata와2874현재 참조 해시를 검사하고 대표65조건206split/87continuous를130freshCPU로 재실행했다. 모든22wait와3guard, 실제 두 BCC의 Clear/Set,48980 script,30ec raw8BYTE, live LONG·marker·palette RTS alias를 포함한다. 메인이 감사 기록 `/tmp/ms5-exit-audit.txt`를 읽고 재현 범위와 한계를 확인했다. 기록 SHA `bc83eaef22550fe7a112414c8e61c74dd8679f120b8f88e9f911a7cdf193201f`. 임시 파일의 존속을 재현 전제로 요구하지 않는다. 별도 core/비교기 검토도35개 C 보존 opcode와 live stack 순서를 직접 대조했다.


기존 일곱 공식 비교기도 모두 exit0이다. 기본94조건131단계37재개9오류, caller59/91/32재개6오류, carry60/160/100재개10오류+zero-step3, activation52/74/22재개9오류, readiness68/154/86재개14오류+zero-step3, HUD124/277/153재개15오류+zero-step9, transition107/224/117재개15오류+zero-step24를 유지했다. 메인은 최종 여덟 보고서의 고유 파일 합집합23250개를 현재 파일과 직접 해시 대조했다.

| 보고서 (`artifacts/*_execution/verification.json`) | SHA256 | 고유 참조 |
|---|---|---:|
| animation_machine | `d67af6c10244a4ecf1371d91b3d2fc61fba9058811b3d56449ecf0729a574914` | 1714 |
| animation_machine_callers | `a46d49695805c8de3ea6e07a82ea89de998d4ee35b69c5af6e538fc4d0ac42df` | 1240 |
| animation_machine_carry | `82904937e35041064d487981ec067f1ad034d213161551b38b4a13f34fb6099f` | 3049 |
| animation_machine_activation | `616a15898b8f64392537b5db1629661362a8634a951128175f307dee9bede1e1` | 1043 |
| animation_machine_readiness | `d47713e3063489e179638f6e7e711bb9d798fe9eb1b151f290be35a7b8b7adf3` | 2982 |
| animation_machine_hud | `d543edf2fb0989b7f02d5c842c811598df4e7d41777ab80c3789a8e11fc7a0ad` | 4995 |
| animation_machine_transition | `6f425c6736e2b2b97a6a7d67a04ab7ec65c49a49abb01d6c1d1319aad30f9678` | 4203 |
| animation_machine_exit | `12fae62c0c40ffd431435c5a550d935692f07192f05badab23ad1475f42be8e8` | 4650 |

## 운영과 미완료 범위

Sol6.1/medium3명이 core/unit, 원본 관측, 비교기/문서화를 분담하고 교차 리뷰했다. 메인은 복잡한 원본 의미·계약·실제diff·통합·검증 기록을 담당한다. 독립 작업 세 개에 맞춰 내부 세 명을 사용하며 작업자 수를 채우려고 외부 작업을 만들지 않는다. 동결 후 기존 회귀는 base/callers/carry,readiness/activation,HUD/transition으로 나누어 서로 다른 출력 폴더에서 실행한다.

자연 scheduler·IRQ/timing·일반CCR·caf0/477ee/47da4/480bc body·직접플레이·전체스테이지/적/보스·미사용자료 전체 의미는 미완료다. 애니메이션17종 중14종(약82%)+14/3c 일부는 해당 명령 집계이며 전체게임 복원율은 미산정이다. 전체 Goal은 active로 유지한다.
