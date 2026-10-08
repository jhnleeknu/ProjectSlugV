# Animation 전체 상태 실행의 첫 연결

## 현재 bank-state CLI schema

[실제 bank 상태 계약](animation-bank-state-contract.md)에 따라 공통 `SAVED_LIST_END` 바로 뒤 argv22에 unsigned32 `CURRENT_BANK_BASE`를 전달한다. 일반 CLI는22숫자/23JSON, RAM/output/ports argv23/24/25 및 resource26+이며, sound CLI는27숫자/28JSON, callback4개 argv23..26, EXTERNAL argv27, RAM/output/ports argv28/29/30 및 resource31+다. 두 출력 JSON은 숫자 `current_bank_base`를 항상 포함한다. 임의 uint32 bank 입력을 허용하며 saved_bank와 구분한다. 이전 schema 자동 추정이나 기본값 보충은 없다. 아래 원본 관측·검증 수치와 해시는 해당 단위 당시의 완료 기록이며, 이 schema 이행의 재검증 결과를 대신하지 않는다.


이 문서는 최초4opcode 연결의 기록이다. 이후0c/14와 MS5D 확장 및 최신 회귀 결과는 [control 실행 문서](animation-control-execution.md)를 따른다. 아래 최초 검증 해시는 당시 구현의 증거다. 현재CLI schema는아래에갱신했으며opcode10/phase3 확장은 [indexed 실행 문서](animation-indexed-execution.md)를따른다. 최초20숫자/21key 검증기록은현행21숫자/22key의검증결과와구분한다.

[초기 실행 계약](animation-execution-initial-contract.md)과 [draw 전체 상태 계약](animation-draw-full-contract.md)의 원본49fc6을 새 API로 연결한다. canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이며 아래 fixed CPU 주소는 ROM 파일 오프셋과 같다. 이번 새 full-state 경로는 **00/04/08/28 네 opcode**다. 전체17opcode 목표 중 나머지13개와 callback/sound/banked 동작은 미완료로 유지하며, 기존 RAM/carry API의 구현과 지원 범위를 제거하지 않는다.

```cpp
struct AnimationExecutionState {
    SpriteSubmitExecutionState sprite;
    std::uint32_t a5, a6;
    unsigned int phase;
    std::uint32_t saved_a0, saved_a1;
    std::uint16_t saved_bank;
};
bool step_animation_execution(std::vector<std::uint8_t>& ram,
    const std::vector<AnimationResource>& scripts,
    AnimationExecutionState& state, bool& carry,
    std::vector<VideoPortWrite>& ports, std::string& error);
```

RAM은 CPU100000..10ffff의 정확히65536바이트다. `sprite.registers`의 D[8]/A[5]가 D0..D7/A0..A4의 유일한 상태이며 별도 A5/A6를 함께 전달한다. phase0은 fresh/완료이며 waiting=false와 저장필드0을 요구한다. phase1은 직접 opcode04의 cd58 captured wait이며 waiting=true와 saved A0/A1/bank를 유지한다. 오류는 RAM·15레지스터·metadata·carry·기존 ports를 보존한다. 성공한 wait는 그 시점까지 효과를 commit하며 API carry 입력을 보존한다. RTS 완료에서만 실제 반환 carry를 설정한다. 성공 ports는 이번 호출의 ordered writes로 교체한다.

## 현재 CLI

```text
build/step_animation_execution \
  D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 A5 A6 \
  PHASE SAVED_A0 SAVED_A1 SAVED_BANK SPRITE_WAITING SAVED_LIST_END CURRENT_BANK_BASE \
  INPUT_RAM OUTPUT_RAM OUTPUT_PORTS [RESOURCE_MS5A_OR_MS5D ...]
```

숫자는22개, argc는 최소26다. RAM input/output/port output은 argv23/24/25, resource는 argv26 이후다. ENTRY/carry 입력은 없다. register와 saved pointer는 unsigned32bit, PHASE0/1/3(2거절), SAVED_BANK0..65535, SPRITE_WAITING0..1, SAVED_LIST_END와 CURRENT_BANK_BASE는 unsigned32bit을 받는다. 숫자는10진수 또는 `0x`/`0X`16진수이며 부호·공백·빈 숫자·후행 문자·overflow를 거부한다. core가 metadata의 조합을 검사한다.

성공 stdout은 정확히23개 key의 한 줄 JSON이다. `d0..d7`, `a0..a6`, `phase`, `saved_a0`, `saved_a1`, `saved_bank`, `saved_list_end`, `current_bank_base`는 숫자, `waiting`은 boolean이다. `carry`는 phase1/3 대기 시null, phase0 완료 시boolean이다. CLI 내부 API carry 초기값은false이며 대기의 보존된 bool을 반환CCR처럼 표시하지 않는다. OUTPUT_RAM은65536바이트, OUTPUT_PORTS는 ordered9바이트 `>BII`(size BYTE, address/value BE32)다. 오류는 stderr와 실패 종료 코드로 보고하며 성공 JSON을 출력하지 않는다.

phase3은indexed sprite대기이며waiting=true,callback metadata비활성이다. phase0/1/2에서는saved_list_end=0이며phase3의saved_list_end는draw saved_a1과별개의복귀주소다. saved_list_end가 없던 이전 직접04 명령에는 SPRITE_WAITING 뒤0을 삽입하고, 현재 schema에서는 그 뒤 CURRENT_BANK_BASE도 명시해야 한다. pending 재개는 실제 장치 bank를 별도로 전달하며 RAM shadow에서 추정하지 않는다.

## 실제 순서와 continuation

fresh49fc6은 A0=A6+26, WORD(A5-7ff0)=0, PVC WORD1000→2ffff2/WORD0→2ffff0을 실행한다. D7=LONG(A0)가0이면 carry1로 즉시 완료하며 script/object+17을 더 읽지 않는다. active pointer이면 A1=D7, BYTE(A5+5742)=0이며 signed양수 object+17만1 감소시킨다. dispatch마다 D7전체를0으로 하고 BYTE(A1)를 읽어 A1을 증가시킨다.

00은 duration을 D1.byte로 읽고 live timer/state pointer를 계약의 순서대로 처리한다. timer 상위BYTE 더하기, WORD 감소 및 D0/D5/D6 scratch를 보존하며 host시간이나 추정 frame duration으로 바꾸지 않는다.28은 operand 없는 한 BYTE terminal이며 timer가음수면 reset/restart하고 그 외 timer 상위BYTE를0으로 한 뒤 반환한다.08은 한 skipped BYTE 뒤 BE32 target을 읽어 A1과 live state pointer를 갱신하고 dispatch한다. skip된 BYTE와489c1의 별도 alignment padding을 구분한다.

04는7byte operand를 읽고 실제 skip/좌표/flag/palette 변환을 수행한다. 특수ID·음수timer·깜박임 skip도 실제 register/A1 효과를 유지하며 다음 명령으로 진행한다. draw가 sprite-submit에 실제 진입할 때만 기존 callee 지원 한계에 따라 A5=108000을 요구한다. skip/null/wait/terminal 경로에 canonical A5 제한을 추가하지 않는다. 임의 callback은 지원하지 않으며 기존 default cd50 callee의 실제 clip/full/normal/deferred/wait 결과를 사용한다.

submit 전 saved A0/A1과 live bank WORD를 캡처하고 shadow0/PVC를 출력한다. phase1 resume는 현재 draw의 operand/object 전처리를 반복하지 않고 cd58 wait만 이어간다. 완료 후 live A5-relative bank shadow를 복원하고 PVC를 재설정한다. D0/D7의 MOVEM.W 복원은 signed16→32 부호확장이며 일반 MOVE.W의 상위WORD 보존과 다르다. A0/A1 LONG을 복원한 뒤 다음 dispatch로 간다. **후속 draw는 바뀐 object를 새로 읽을 수 있다.** 이전 C++ 출력 RAM·15레지스터·captured metadata를 다음 호출에 그대로 전달해야 한다.

active epilogue는 shadow0과 PVC두WORD를 다시 출력하며 ASR.W1 D7의 이동 전 bit0을 반환 carry로 제공한다. unsupported opcode·banked fetch·다른 resume 종류와 실행 cap 초과는 checked 실패이며 정상 완료로 바꾸지 않는다. 실제 reached BYTE/정렬WORD/LONG만 검사한다.

## MS5A와 live RAM

scripts는 기존 `load_animation_resource`가 읽는 MS5A v1 kind1이다. loader가 fixed CPU=ROM<100000, nonempty 완전한 payload/길이, reserved0와 CRC를 검사한다. CLI는 모든 공급 script를 일반 파일 확인 후 loader로 읽는다. 미실행 파일도 공급했다면 오류를 무시하지 않는다. 같은 canonical 경로/inode의 script aliases는 한 번만 로드하며 서로 다른 파일의 overlap은 실제 reached fetch의 core uniqueness 검사 대상이다.

fixed fetch는 유일한 완전한 script window를 요구하며 live CPU RAM100000..10ffff의 script는 실제 현재 RAM에서 읽는다. null pointer나 계속 대기하는 captured 상태처럼 script를 읽지 않는 호출은 script0개가 가능하다. 이후 dispatch가 도달하면 해당 fetch를 제공해야 한다. source 기반48980/489c2의 실제 consumed span은 [resource inventory](activation-animation-resource-spans.md)를 따른다. 새 `pack_activation_animation.py`가 기존 MS5A/metadata를 제공하며 composition group을 임의로 바인딩하지 않는다.48980 caller의 지역적 groupEA 설정과 달리489c2의 live object+20 group은 아직 확정하지 않았다.

실제 CLI가 소비한 `animation_048980.ms5a`는65바이트 payload/97바이트 container이며 SHA256은 `585e124a195c69867d877362b0b7928940fa556cd8ece500e8cdabe997e46821`다. `animation_0489c2.ms5a`는80/112바이트이며 SHA256은 `7dfd0875267b16598e8bac6600f144e0f4e34096cf540e8504b219fdeee90b1d`다. 동일 packer의 `lookup_048a12.ms5d`는1024/1056바이트이며 SHA256은 `f5f305c606593a19b7bf4d5eebe684cf683357c289e48486f7439a3360d9acbd`다. 이 raw lookup은 상위 caller47ce0을 위한 별도 보존 resource로, **이번 animation API가 소비하지 않는다**. MS5D를 이 CLI의 SCRIPT_MS5A 자리에 공급하지 않는다.

## 파일 보호와 한계

RAM과 모든 script는 열기 전에 stat/S_ISREG로 일반 파일임을 확인하여 FIFO 등 특수 입력을 거부한다. input/outputs 또는 script/outputs의 canonical 경로·inode alias를 거부한다. parser·입력·loader·core 오류 시 output을 열지 않는다.

core 성공 후 두 output을 truncate 없이 O_NONBLOCK으로 예약한다. fstat으로 일반 파일 여부와 두 descriptor의 서로 다른 device/inode를 확인하고 모든 RAM/script의 저장된 identity 및 현재 inode와 대조한 뒤에만 truncate/쓰기한다. 실제 case alias도 이 검사로 거부한다. 예약/검사 실패 시 기존 파일을 보존하고 새 placeholder는 현재 lstat identity가 예약 inode와 같을 때만 제거한다. write/close를 검사하지만 실제 I/O 실패에 두 파일의 원자적 교체나 rollback을 보장하지 않는다.

## 재현과 검증 상태

Makefile all/test에 CLI와 `animation_execution_test`를 등록한다. core는 `animation_execution.cpp`와 기존 `sprite_submit_execution.cpp`이며 CLI에는 `animation_resource.cpp`를 추가한다. 관련 header union을 의존성으로 사용한다. runtime-resources는 새 activation-animation packer를 호출한다.

```sh
.venv/bin/python tools/pack_activation_animation.py
make build/step_animation_execution build/animation_execution_test
./build/animation_execution_test
.venv/bin/python tools/observe_activation_animation_scripts.py
.venv/bin/python tools/verify_animation_execution.py
```

최종 `artifacts/animation_execution/verification.json` SHA256은 `60a5594afb637884eaf51d61cf5ff5ddd9f6af32869ea6a9775ec7b627160082`다. 실제 MS5A 두 script를 로드한90조건·98phase에서 원본을 다시 실행하고 전체64KiB RAM·15레지스터·pending·carry·ordered ports를 CLI와 비교했다. primary ordered port 쓰기는3280개다.8개 resume는 직전 실제 C++ 출력 RAM·15레지스터·metadata와 명시된 host 변경만을 다음 호출에 전달했다. pending carry는null, 완료 carry는boolean으로 비교했다.

별도 live RAM script15조건도 원본 코드 수정 없이 실행했다. duration0의 timer0/8000, draw control/palette 조합, sentinel/flash skip 및 entry의 RAM shadow clear가 script 자체를 바꾸는 경우를 포함한다. 이 RAM script는 합성 입력 데이터이며 원본 gameplay script나 자연 도달성의 증거라고 기록하지 않는다.157개 negative 검사는 unsupported opcode/metadata·fetch·callback·span 오류와 parser, FIFO/alias 및 output 예약 실패의 입력·기존 출력 보존을 확인했다. checked 실패를 원본 TRAP의 정상 완료 동등성으로 취급하지 않는다.

보고서의 구현·도구·resource 입력22개와 native/C++ artifact670개의 현재 SHA256을 대조했으며 모두 일치했다. 비교 CLI 바이너리 SHA256은 `3661de51195a29a01a13d5e38040d18d735bffcd5817bf60b60aaf1d407d7541`이다. CLI 단독 C++11 경고 옵션 빌드는 exit0/경고0으로 완료했다. core의 별도 normal/UBSan 단위 실행도 통과했다. 전체 `make all test`도 exit0으로 완료했다. `artifacts/animation_execution/make-all-test.log`에는 Python215 tests, C++ 실행145개와 경고0개가 기록되어 있다.

A7/stack·CCR전체·cycles, 나머지13opcode와 indexed/sound/callback resume, banked script/data, 임의 callback, 물리mirror, 자연IRQ/scheduler, composition group/palette 바인딩, 화면 전체·직접 플레이와 전체 복원 완료는 이 첫 연결의 증거 범위 밖이다. 이 범위 밖 항목도 전체 GOAL에서 제외하지 않는다.

## saved_list_end 추가 후 현행 schema 회귀

현재21숫자/22key schema로 `tools/verify_animation_execution.py`를재실행한보고서 `artifacts/animation_execution/verification.json` SHA256은 `77a5ecbd0092e4dcb33d27976b1668d190ef76b15967f428773f978dfb1f9fc0`이다. primary90case/98phase,이전실제C++출력재개8회,별도liveRAM15건,negative164건이통과했다. 입력29개와native/C++artifact670개의현재hash를모두대조했다. 위최초검증해시를대체하는현행schema회귀기록이며새opcode10검증과는별도다.
