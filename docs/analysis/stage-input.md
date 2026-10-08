# 스테이지 입력 보조 함수

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Fixed 첫1MiB CPU 주소=ROM offset, RAM CPU100000..10ffff, A5=108000이다. 원본의 상세 연산 계약과 미구현 상위 호출은 `stage-frame-followup.md`를 따른다.

## 지원 범위

C++11 `ms5::step_stage_input`은49ab4 버튼 마스크 매핑,49afe 이전 입력에서 새 눌림 계산,49bb4 일회성 입력 mask 적용·결과 게시,49c20 callback 지정,49c32 해제,49c66 기본 callback 주소 설치를 지원한다. Callback 주소를 쓰는 것과 그 callback을 실행하는 것은 구분한다. 전체49b0c와 동적 callback 실행은 후속 작업이다.

State는 D0..D7/A0..A4 13개 LONG이다. BYTE/WORD 연산은 나머지 상위 비트를 보존하고 MOVEQ는 전체를 덮어쓴다. 49ab4의 겹치는 mask에 따른 bit5 제거,0 mask의 조건 충족,49bb4의 mask 읽기→ffff 소모→held→edge 쓰기 순서를 유지한다. A4의 byte mask는 홀수 RAM 주소도 가능하다. WORD/LONG 접근은 정렬과 전체 범위를 검사한다. 실패 시64KiB RAM과 전체 state를 보존한다.

## 실제 리소스와 실행

기본 mask는 ROM49ab0..49ab4의 데이터 `10 20 40 80`이다. `tools/pack_stage_input.py`로 기존 MS5D v1 kind1 컨테이너에 저장한다. Payload4/container36바이트이며 CPU=ROM49ab0이다. C++가 실제 생성 파일을 읽는다. 엔진 코드에 기본 mask 배열을 넣지 않는다. 사용자 mask는 live RAM에서 읽으며 확인용 이미지나 오디오는 필요 없다.

```sh
.venv/bin/python tools/pack_stage_input.py
make -j3 all test
.venv/bin/python tools/observe_stage_input.py
.venv/bin/python tools/verify_stage_input.py
```

```text
build/step_stage_input ENTRY D0 D1 D2 D3 D4 D5 D6 D7 A0 A1 A2 A3 A4 INPUT_RAM OUTPUT_RAM [MS5D_OR_DIRECTORY ...]
```

Default mask 리소스 경로는 `extracted/runtime/stage_input/default_masks.ms5d`다. RAM은64KiB이며 JSON은13register를 반환한다. 리소스가 필요한 접근만 실제 창을 조회하며 입력·출력·리소스의 경로/inode 중복은 거절한다.

## 검증 결과와 한계

Pinned Musashi M68000으로 원본 여섯 진입을 RTS까지 중단 없이 실행하고 실제 CLI와 전체 RAM·13register를 비교했다. 2,694조건과 오류42조건이 통과했다. 기본 mask는 held256가지×edge5종, 사용자 mask는 zero/duplicate/overlap/allones 및 홀수/짝수 RAM을 포함한다. WORD 경계값/상위 비트, RAM 마지막 구간, callback slot index와 A0 값도 검사한다. 두 sequence12호출 중10호출은 직전 RAM·13register를 외부 재작성 없이 소비한다.

Native49bb4 쓰기 hook은 WORD(A1+4),WORD(A1+2),WORD(A1) 순서를 관찰했다. CLI 비교는 최종 상태 비교이며 C++의 모든 중간 쓰기 trace를 직접 비교했다고 표현하지 않는다. ROM을 수정하거나 합성 mask를 ROM에 덮어쓰지 않는다. Source/resource/oracle/library/core/CLI/도구 해시를 앞뒤로 확인한다. 전체 재실행에서도 보고서가 바이트 단위로 동일했다. 메인이 실제 저장 RAM2,694개·입력승계·쓰기 기록·현재 provenance를 직접 대조했다.

| 산출물 | SHA256 |
| --- | --- |
| MS5D | `8427d9127faaaa008b053363f39a5e8e758ac9fb00827fcc25e42d842620522d` |
| Manifest | `8ad20ed4f8b4d37792841903528c0d681d61739e04ed125450404b456510a696` |
| Native observation | `987ac8dca989d70198c636e1d0f1713d2a8f84d112b686e5a488125efc089ac2` |
| Verification | `6b8e948dbef5e6eed8ff8cdc35f94179c664cc58382dab4e4e0864a424c9b7b6` |
| CLI | `abde01169423f2098df0a960bc52e35af0bbedf64a695edcd4b3ffd3bbcc0bdb` |

이 함수의 일반 입력 공간 전체, CCR/사이클, 자연 플레이어 입력의 도달성이나 전체 게임 프레임 완료를 주장하지 않는다. 현재 runtime 오류 검사는 지원 범위를 벗어난 자료를 안전하게 거절하는 계약이며 원본의 잘못된 메모리 접근 동작을 재현하는 것이 아니다.
