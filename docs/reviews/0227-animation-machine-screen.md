# 화면 초기화·후속 timer 공유 스택 리뷰

대상 baseline `c776ed8`, 브랜치 `codex/animation-machine-screen`. 최종 대상은 이 문서를 포함하는 통합 커밋이며 로컬 리뷰다. 직전 종료 콜백 통합을 진척으로 승계했고 전체 Goal 범위·완료 기준을 유지한다.

## 원본과 구현

메인은 canonical BE SHA `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`의ca9e..cb62와47fca..47fe4 raw bytes를 다시 읽었다. fixed CPU 주소와 동일 ROM 파일 offset으로 기록했다. ca9e의 DBRA loop/tail, caf0의 BSRca9e와 다섯 JSR35a2, late BYTE clear/live RTS,47fca caller와 timer를 실제 RAM/A7 실행기에 연결한다.

DBRA는 low WORD만 감소하며 시작ffff도65536회 body를 실행한다. ca9e의 정상773개 LONG 출력과 caf0의2072개 ordered outputs(워치독5/비디오2067)를 유지한다. WORD/MOVEQ 폭을 구분하고 live A4가 RAM/stack이면 실제 메모리에 쓴다. 기존 부분 register API로 실제 stack을 대신하지 않는다. video helper는 제한된 LONG3c0000만 포트로 기록하고 일반 MMIO를 넓히지 않는다.

새12개 C 보존 PC는2LEA,7JSR/BSR,2RTS,1DBRA-only다. main과 독립 리뷰가 실제 opcode와 대조했다. flag-only47fe0 BNE는 임의 진입을 거부하고 SUBQ와 합친47fdc block이 실제 zero 의미를 처리한다. 최종47fe4의 BSR477c2와480bc body는 아직 실행하지 않는다. fresh late callback과 자연적인 다음 frame 실행을 구분한다.

## 검증과 관측의 구분

메인의 `make -j4 all test` exit0: Python257개·C++158개 실행·compiler warning0. 로그 `/tmp/ms5-screen-main-make.log`. 새 unit은 일반·UBSan 각각66회 API 호출을 통과했다. DBRA ffff의65536개 cell+tail5, full caf0의 모든 포트 순서, 반환 주소 alias, PVC fallback, timer0/1/2/ffff, 오류 출력 보존을 포함한다. PVC fallback은 C++ 장치 모델 검사이며 이번 native 관측 범위로 확대하지 않는다.

Core SHA `8948a0e8164eaf97f9f16d6b6af8f452e07b3f47a8dd0657e657ae1dbb550a1f`, unit SHA `b6c831ce9349d182a203ce484808e27ceea08f19209588ac63d54db3a4f68a03`. 기존 리소스 형식·원본 ROM은 변경하지 않는다.

원본은 정상31조건128split/37continuous와 guard3조건을 관측했다. 전체138split/40continuous를 두 번씩 실행해136freshCPU/356단계를 확보했다.6wait, 정상 video92167/watchdog55/PVC0·외부읽기0회다.31정상 중에는 실제65536반복, 직접cab8, 상위WORD·RAM mirror·nested return, caf0의 마지막 CLR.B가 outer return000ff000을0000f000으로 바꾸는 조건, fresh47fa8→palette/clear/caf0가 포함된다. 별도 사운드 pipeline 대기는 동일 CPU에서 재개하며 다음 frame으로 포장하지 않는다.

Guard는 모든 포트 뒤 cb5e의 bank ROM BYTE 쓰기, live A4=stack의 caee return7580ff02 fetch,47fd0의 timer WORD 쓰기 뒤47fd6의 fixed ROM LONG 쓰기를 구분한다. 부분 효과가 남는 native fault와 C++ checked API 전체 출력 보존을 같은 현상으로 취급하지 않는다.

Observer SHA `3df8c3aa322d1ac96d3edeeb03dc672929ec25c405e96cee752a2d5707ae40ec`, native report SHA `89e5f3867d416ac611565f46b0f4c0590ee1bb53d7be28a65572c0f018614d9a`. 관측자의72input/1461artifact,1533개 현재 참조를 동결했다. 최종 C++31조건128단계·이전 실제 출력97회 재개가 full64KiB RAM/16R/PC·장치/bank·92222포트·외부읽기0회와 일치했다.6wait와 오류14조건(추가11+원본guard3),zero-step24조건을 통과했다. Native C는 미관측이며 register에서 추측하지 않는다.

비교기 SHA `c154e119718375f2c834360032a9f59c8ee625366837c577c5af6e6c78cc219f`, 보고서 SHA `7fbbe6ec7902e064cca0c8e9471fab787981a8e00f668fb3388781e5c9b5d15d`. 메인은 현재2565개 고유 참조와 native1533개 참조의 해시를 직접 검사했고, 독립 최종 source/참조 감사도 일치했다. 기존 회귀 수치는 최종 통합 기록을 따른다.

독립 native 감사는34개 fixture metadata와1533개 참조를 검사하고 대표21조건102split/27continuous를42freshCPU로 재실행했다. 모든6wait/3guard,65536회 loop, 직접cab8, shared stack/RAM A4, late CLR return alias를 포함한다. 저장된 RAM/16R/PC/PVC와 포트·접근 trace·checkpoint snapshot이 일치했다. 메인은 `/tmp/ms5-screen-audit.txt`를 읽고 실제29번 guard가 cb5e checkpoint와 동일 PC에서 실패한다는 점도 fixture 목록으로 확인했다. 감사 기록 SHA `ddfed3144155125c60146755cc9fc50f591d3be85cc54f85f2fd2ca6cd669ef4`. 임시 파일의 존속을 재현 전제로 요구하지 않는다.

## 검토 사항

cb5e에서 먼저 정상 checkpoint를 멈춘 뒤 같은 PC의 쓰기가 guard될 수 있다. split의 최종 PC와 같다는 이유로 앞선 checkpoint를 제외하면 continuous snapshot을 잘못 누락한다. 새 observer/비교기는 최종 terminal phase만 제외한 `split[:-1]`에서 정상 checkpoint를 모으도록 작성했고, 실제 guard와 fresh continuous 비교로 확인한다. 이전 관측 파일은 수정하지 않는다.

Main은 실제 core·routing·unit과 원본 순서, unsigned wrap·live return·stop 경계를 검토했다. 독립 source 리뷰에서도 현재 남은 의미상 결함을 발견하지 못했다. 전체 게임 완료를 국소 비교로 추론하지 않는다.


기존 여덟 공식 verifier도 모두 exit0이다. 기본94조건131단계37재개9오류, caller59/91/32재개6오류, carry60/160/100재개10오류+zero-step3, activation52/74/22재개9오류, readiness68/154/86재개14오류+zero-step3, HUD124/277/153재개15오류+zero-step9, transition107/224/117재개15오류+zero-step24, exit90/252/162재개17오류+zero-step21를 유지했다. 메인이 최종 아홉 보고서의 현재 고유 파일 합집합25717개를 직접 해시 대조했고 독립 감사도 일치했다.

| 보고서 (`artifacts/*_execution/verification.json`) | SHA256 | 고유 참조 |
|---|---|---:|
| animation_machine | `4b4221048af32b411179130bee630b6de2e5ec037ff34830ddc948d23c4ec3a8` | 1715 |
| animation_machine_callers | `ea196ebf4f1d3a825f6796744d7623a9f2a83e2bfab44e4d3f9bd1de88f7fd11` | 1241 |
| animation_machine_carry | `1bac7a761ff5dc6f9df825ab5df7442c1ca2b334fd36ccaf89fadd7d5ea184ec` | 3050 |
| animation_machine_activation | `6b2b147f05b6b60476bc75648f715f6f4fe9734e3066c936f829a1b86155216b` | 1044 |
| animation_machine_readiness | `7f9d671d8bde86d9534b451b284f4f98a205d275bb55db3a93ae1825f0d3656b` | 2983 |
| animation_machine_hud | `b1c7e0fa00d16be9501135a8422a600f49435b84daede1913f512864a590a4e6` | 4996 |
| animation_machine_transition | `68fc003b6ceff9bf8dee0f8da2f71dc02285e9f520db957c58c3bbb836f5f9ab` | 4204 |
| animation_machine_exit | `f9b223b1239ef8e283e2710f6353c37b5aa78b86c3645f6b82dcb54ea16fa3c8` | 4651 |
| animation_machine_screen | `7fbbe6ec7902e064cca0c8e9471fab787981a8e00f668fb3388781e5c9b5d15d` | 2565 |

## 운영과 남은 범위

Sol6.1/medium3명은 core/unit, native, 비교기/문서를 담당하고 교차 검토했다. 메인은 원본 의미·계약·Makefile·전체 테스트·실제diff·최종 통합을 맡는다. 동결 후 기존 여덟 회귀는 base/callers/carry,HUD/transition/exit,readiness/activation으로 나누어 서로 다른 출력 폴더에서 실행한다.

다음은477c2와47fe4 후속,477ee/47da4 및480bc frame의 실제 stack 연결이다. 자연 scheduler·IRQ/timing·일반CCR·직접플레이·전체스테이지/적/보스·미사용자료 전체 의미는 미완료다. 전체 Goal은 active이며 애니메이션17중14종+14/3c 일부와 전체복원율 미산정을 유지한다.
