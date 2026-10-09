# 맵 뒤 페이드·타이머·프레임 재진입과 BIOS 카드 경계의 실제 C++ 검증

Baseline `55606fa`, branch `codex/animation-machine-fade-card`. 계약 `animation-machine-fade-card-contract.md`의 `4804e..480b6`, `c364..c3be`, `28ae..2916`, `2a00/2a02/2a06`, `2ab8..2ac6`를 동결된 native 관측과 실제 공개 C++ API(`run_animation_machine`)로 비교한다. 이 문서는 컨트롤된 fixture에 대한 비교 기록이며 BIOS 실행, 자연 scheduler, 전체 게임 완료의 증거가 아니다.

Canonical BE ROM은 `extracted/program/maincpu.decrypted.be.bin`, 8MiB, SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. Fixed CPU 주소는 file offset과 같고, banked read는 당시 실제 ordered PVC를 독립 fold한 bank와 physical offset으로 원본 바이트와 대조한다. ROM은 수정하지 않으며 시작/종료 SHA·mtime을 재검사한다.

## 입력

- Native 관측 `artifacts/animation_machine_fade_card_native/observation.json` SHA256 `f53387b7122286eca94c55371a34a09f900489eb9ab2766f9c98e086da7f57fc`, 도구 `tools/observe_animation_machine_fade_card.py` SHA256 `01d932ba16a1ab16679b888d5b02b53b5ea071b194aaa1fcbd345f3a0672baf5`. 정상 25 조건(split 319, continuous 196), guard 7 조건. 검증기는 두 SHA를 pin한다. 관측 산출물은 해시와 trace 일관성으로 감사하며 이 검증기가 다시 실행하지 않는다(재현은 관측 도구의 reproduced_twice·continuous_split_equivalent 기록에 의존).
- Native 플래그 `original_program_modified`, `SR_read_at_any_phase`, `register_injection_after_begin`, `Cpp_comparison_performed`는 모두 false여야 한다. Unicorn 2.1.4 M68000 oracle 버전·라이브러리 해시를 대조한다.
- C++ 하네스는 기존 22-key strict 하네스이며 `fade_card.cpp`를 `verify_animation_machine.py`의 `SOURCES`에 추가해 링크한다.

## 비교 방법

- 비교 항목: full 64KiB RAM, 16R, PC, live A7, PVC device/bank, ordered ports, external reads, status. 재개 입력은 직전 실제 C++ 출력과 native 단계에 선언된 host 변경(RAM write, PC 변경, A7 가산)뿐이다. native incoming/ram_before는 단언에만 쓰며 기대 레지스터를 주입하지 않는다.
- Fresh 조건의 시작 상태는 연결 체인의 기록된 native 출력(RAM SHA로 식별)이며, 선언된 초기 변경은 `guard-odd-A6`의 A6, `guard-odd-A7-push`의 A7+1, `transition-frame-127-D3-high-word`의 D3뿐이다. 시작 carry는 Unknown으로 선언한다.
- Split 단계마다 C++ 한 번 호출, 그리고 각 단계에서 continuous 한 번 호출을 비교하고 둘의 최종 상태가 같은지 확인한다. 대표 fresh 프레임(1, 127, 158)은 연결 체인의 같은 프레임과 C++ 출력이 같다(PVC `1ff0..1ff3`의 raw native 저장과 mask된 device 저장 차이는 제외, 이는 기존 검증과 동일한 구분).
- Carry: native는 SR을 읽지 않는다. C++ carry는 native가 실행한 PC 열을 원본 opcode로 분류한 값과 비교한다(ORI CCR #1=Set, ANDI CCR #fe=Clear, LEA/MOVEA/JSR/JMP/BSR/BRA/RTS/MOVEM/BTST 계열/조건분기=보존, 그 밖=Unknown). 이는 source-opcode 분류이며 측정된 native C가 아니다. 결과 분포는 Unknown 312, Clear 2, Set 13 단계.
- Guard 7개는 native 부분효과와 별개로, checked API가 오류를 내고 입력 RAM/PVC/16R/PC/carry/bank/ports(marker)/reads/status를 전부 보존함을 확인한다. 원본 CPU fault rollback 동등성은 주장하지 않는다.
- 추가 검사: 묶인 분기 PC 직접 진입 7개 거부, `c00468`·`480bc`·`2aac` PC 거부, BIOS 호출에 다른 stop을 주면 전체 rollback, 홀수 A6·홀수 JSR 대상, ROM chunk 누락, 자기 재귀 callback(재귀 push가 mirror RAM에서 (A6)를 return2ac2로 덮은 뒤 unsupported PC로 나가는 정확한 오류)(합계 negatives 22 = 일반 15 + guard 7), zero-step 117(39 PC x carry 3), `2908`/`290e`의 source-classified Set/Clear 6.

## 결과 (`tools/verify_animation_machine_fade_card.py`)

- 32 조건(정상 25 + guard 7), split 327 단계 비교(정상 319 + guard 앞 단계 8), continuous 196 단계, 이전 실제 C++ 출력 재개 299회, ordered port 18389개, external read 0, 원본 program read 감사: fixed read 207, bank read 1296, PVC write 24(native 정상 구간의 ports는 이 값과 같은 사건에서 fold).
- 보고서 `artifacts/animation_machine_fade_card_execution/verification.json` SHA256 `ad6e83ea686fe864319ff6c288710a069f78734765ce61e2781a4666740058c5`, 검증기 SHA256 `bc438cd1cffe81d5d7d04db544146afa2a751773fcab35da50d16055ccf0e065`.
- 연결 체인 `47fe8 -> 4804e ... 4806a RTS -> 2ac2` 후 2ab8 재진입 158회로 `c00468` stop에 도달하고, BIOS 재개(응답 80, 0/1/7f/81/ff 할당 성공, 마지막 free, depth ffff, count 0 실패, 3개 alias, saved A6 교체)와 후속 `480ac` 프레임을 포함한다.

```sh
.venv/bin/python tools/observe_animation_machine_fade_card.py   # 관측(동결본 재생성 시)
.venv/bin/python tools/verify_animation_machine_fade_card.py
```

## 기존 검증의 경계 이동

`4804e`가 지원되므로 기존 검증기의 unsupported 경계를 `0xc00468`(BIOS, 실행부 없음)로 옮겼다(cleanup/palette_bind/scene/screen/map_transfer). 역사적 정상 stop은 유지한다. palette_bind·map_transfer의 whole fixture는 이제 4804e를 지나 첫 checked 실패가 `unsupported animation machine write device`로 바뀌었다(메인 확인: 레거시48042 whole fixture의 A6=0이므로 4805e의 7a(A6) WORD가 ROM 주소7a 쓰기가 된다). 재실행 결과: screen 31/128/97/14, cleanup 69/121/52/17, scene 79/225/146/20, palette_bind 58/140/82/21, map_transfer 50/131/81/18, 기본 verify_animation_machine 8/2/85/121/9 모두 통과.

## 한계 (미확인 포함)

- `c00468` BIOS는 실행하지 않는다. 재개는 선언된 host 변경(PC=`c37c`, A7+=4, BYTE `10fdc6`)이며 카드 RAM·레지스터 파괴 등 다른 BIOS 효과는 미모델·미확인이다. 응답 값의 실제 의미도 미확인이다.
- 프레임 재진입은 PC만 `2ab8`로 바꾸는 선언된 변경이며 자연 scheduler·IRQ·VBlank가 아니다. 다른 객체 callback은 실행하지 않는다.
- Cleanup 객체, `28ae` pool/parent, `104ca4` 기준 A7 등은 선언된 RAM fixture이며 원본 측정 준비가 아니다.
- 8c16/caf0 포트는 instruction 단위 기록이며 물리 bus cycle·VRAM 화면이 아니다. 일반 CCR·timing·직접플레이·`480bc` 이후 프레임 helper·자식 callback 본문은 범위 밖이다.
