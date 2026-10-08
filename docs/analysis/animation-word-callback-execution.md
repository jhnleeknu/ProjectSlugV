# Animation3c WORD callback 실행 연결

## 현재 bank-state CLI schema

[실제 bank 상태 계약](animation-bank-state-contract.md)에 따라 공통 `SAVED_LIST_END` 바로 뒤 argv22에 unsigned32 `CURRENT_BANK_BASE`를 전달한다. 일반 CLI는22숫자/23JSON, RAM/output/ports argv23/24/25 및 resource26+이며, sound CLI는27숫자/28JSON, callback4개 argv23..26, EXTERNAL argv27, RAM/output/ports argv28/29/30 및 resource31+다. 두 출력 JSON은 숫자 `current_bank_base`를 항상 포함한다. 임의 uint32 bank 입력을 허용하며 saved_bank와 구분한다. 이전 schema 자동 추정이나 기본값 보충은 없다. 아래 원본 관측·검증 수치와 해시는 해당 단위 당시의 완료 기록이며, 이 schema 이행의 재검증 결과를 대신하지 않는다.


Baseline `cc5750b`, branch `codex/animation-word-callback`. 원본 canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 CPU4a30c..4a382와 callback3679e/2b3e8/2b3fa/47672는 같은 ROM 파일 오프셋이다. 계약은 `animation-word-callback-contract.md`를 따른다. 전체3c callback이나 전체게임 완료를 의미하지 않는다.

## 구현과 리뷰 수정

C++11의 기존 callback 경로에3c prefix를 연결했다. 첫 WORD selector는 두 번 ADD.W 후 signed WORD LONG 조회, 둘째 WORD selector는 한 번 ADD.W 후 WORD 조회를 수행한다. D1.high를 유지하고 operand LONG을 D0 전체와 A0에 넣은 뒤 실제 읽은 target을 호출한다. 둘째 lookup은 callback에서D1을덮어쓰더라도 먼저 수행한다.

지원 target은 이미 복원한2b3e8/2b3fa/47672와 실제4e75(RTS)인3679e다. 원본 dispatch의 각 슬롯은 WORD selector의4개 alias가 공유한다. 기존14는 실제selector03→3679e 지원만 추가하며 다른 selector를 무조건 같은target으로 간주하지 않는다. 나머지 target은 checked 미지원이다.

복귀는 기존 callback의 bank/PVC와 MOVEM.W D0/D7 sign확장, A0/A1 LONG 복원 및 D6/script pointer 저장을 재사용한다. 사운드 대기는 기존phase2와metadata를 사용하므로 API/state/CLI 규격은 변경하지 않았다. nonexternal API는47672를 거부한다.

메인 리뷰에서 첫 구현이4a326의 LEA 대상 A0를 A2로 잘못 옮긴 문제를 발견했다. A0로 수정하고 잘못된 unit 기대값도 교정했으며 nonzero A2 보존 검사를 추가했다. 수정 뒤 normal/UBSan 및 전체 검사를 다시 수행했다. 성공한 unit만으로 원본 동등성을 판단하지 않았다.

## 리소스와 목록

전체 first WORD domain65536은16384 LONG 슬롯을4개씩 공유한다. second WORD domain65536은32768 WORD 슬롯을2개씩 공유한다. inventory는131072개 주소 계산을 확인한다. raw target 일치와 함수 지원·자연 script 도달성을 구분한다.

새prefix[42500,4276c)는 **620BYTE**이며 기존[4276c,5276c)와 비중복이다. 초기 정적 문서의624 산술 표기를 수정했다. payload SHA `d418ddaba698d044f4b0d570a5da75db9869ea074d357650105520295e4477e6`, MS5D container652BYTE SHA `3d5d1bd37897a4cfaa69482c01aaf40c06fafb07877be018db7db4f7c9cb0082`. 고유 슬롯155개 중 현재 지원target은 없다. 따라서 이 prefix 소비는 실제 table 읽기 후 unsupportedtarget으로 거부되는 것을 검증하며 성공 callback으로 주장하지 않는다.

추가 경계 operand[0,400),[ffc00,100000)는 원본 BYTE index 전체 범위의 raw LONG을 같은 MS5D 규격으로 보존한다. 첫[0,80)는 canonical cartridge ROM view로 비교하며 BIOS/cart vector선택 장치 검증은 아니다. 기존6431a operand와 넓은control 리소스는 재사용한다. 넓은control이sound4411e lookup도 포함하므로 중복되는 narrowlookup을 성공 실행에 함께 제공하지 않는다.

## 독립 원본 관측

- RTS 관측:438조건/438단계,3504PVC.3c432조건과14의6조건이며4개 firstalias,18종 secondselector,6종operand를 비교한다. 원본3679e는 실제 RTS이며 다른callback을 stub 처리하지 않는다. native SHA `b6064ba9908ac25b3d137cadf2dc3914e8df539edee104671b05c5760d8488dd`.
- 다른 세 callback 관측:122조건/138단계,6대기연쇄/16재개,984PVC/3external읽기. terminal28 carrytrue89조건과00,00 carryfalse33조건. 실제fixed/RAMoperand,callee가다음opcode를덮는alias,WORDqueue와sourcealias,poison후live source/terminal재독출을 포함한다. native SHA `22e757ea1e727cfed50eaf3ad593b0cf6d2d9115c0beadf3a864220531c3495d`.
- 별도 미지원target5개는 prefix까지만 실행하고 callee 첫 명령 전에 멈춘다. 홀수target1개는 실행하지 않았다. 이6개를 성공 검증 수에 포함하지 않는다.

두 관측기는 수정하지 않은 ROM과 stack/read/write/PC 범위를 확인한다. SR은 초기화 때 A7보다 먼저 쓰고 RTS 뒤 carry만 읽는다. 대기는 동일 CPU 문맥에서 유지·재개하며 예상 register를 주입하지 않는다. 독립 재현 감사도 같은 Unicorn 엔진을 사용하므로 물리 CPU와 독립적인 에뮬레이터 간 교차 검증은 아니다.

## 통합 검증 현황

수정 core에서 `make all test` Python241/C++145 및 기존6종 회귀가 통과했다. 이후 패커 검사 확장 뒤 최종 Python discover243개도 통과했다. C++ 소스는 그 사이 바뀌지 않았다.

공식 검증기는 원본576성공단계와 별도unsupported prefix5개를 재실행했다. sound CLI576단계, non-sound ordinary CLI515단계의 전체RAM15R/state/carry/PVC/외부읽기가 일치했다. 16회 재개는 직전 실제 C++ 출력을 사용했고10개pending호출은리소스없이성공했다. 오류·파일 보존383조건과합성MS5A padding유무2조건도통과했다. 최종report SHA `c7d47dd00019aeec066cf13ac5b563990e6377cb31a745f5e0be59b7bc70b055`. 메인이 입력56개/산출물6196항목, 고유6243개 참조 해시를 확인했다. 리뷰0213에 발견·수정·검증의 범위를 기록했다.

추가리소스3개와manifest를재build하여게시파일4개와byte일치를확인했다. manifest SHA `a40315a2bf9e76dcda685a797dbc3c70701874bbd03ed2933cd2d546672b807c`, operands_000000.ms5d SHA `b79f39fbba5302aeb07e898ef93d6d5f45a92206f3ea700a741d46b2f0cde2c3`, operands_0ffc00.ms5d SHA `6b50440c0606e84fdc42cf9d4b4922416c8e1412b6eb07fd9e1f772dcf36580d`. 이fixture창에서는주소wrap이없어임의32bitpointer의24bitmask지원검증으로일반화하지않는다.

## 재현

```sh
.venv/bin/python tools/inventory_animation_word_callbacks.py
.venv/bin/python tools/pack_animation_word_callback.py
make all test
.venv/bin/python tools/observe_animation_rts_callback.py
.venv/bin/python tools/observe_animation_word_callback.py
.venv/bin/python tools/verify_animation_word_callback.py
```

자연 게임의 script/group 도달성·전체callback·40 bank 조회·자연IRQ/Z80·사이클·fullCCR·전체Goal은 미완료다. bankshadow와실제bank상태 문제는 `animation-banked-lookup-design.md`에 별도로 기록했다.
