# Animation40의 C++ program bus와 isolated lookup 계약

Baseline `bfb1d7e`, branch `codex/animation-program-bus`. 원본 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 이전95조건 관측의 CPU/ROM offset `4a382..4a3ac` 본체를 추출된 MS5D 리소스에 연결한다. `4a276` publication·dispatch·whole49fc6·대기 재개와 자연 도달성은 이 함수의 완료 범위에 포함하지 않는다. 전체 Goal과 완료 기준은 유지한다.

## 버스와 소유권

`ProgramBusState`는 현재 physical bank base와 선택된 vector128BYTE/PVC8192BYTE에 대한 borrowed pointer를 가진다. 두 버퍼는 호출 동안 살아 있어야 하며 읽기 전용이다. null은 미확인 상태를 뜻하고 해당 영역에 실제 접근할 때만 오류다. 벡터를 cartridge ROM이라고 자동 가정하지 않는다. RAM은 정확히65536BYTE이며16개의 CPU mirror가 같은 bytes를 읽고 쓴다.

`read_program_bus`는 BYTE/WORD/LONG만 처리한다. WORD/LONG의 논리 주소는 짝수여야 한다. LONG은 두 WORD를 각각 분류하며 각 주소는 uint32 덧셈 후24비트 bus mask를 적용한다. 반환값은 big-endian 결합이고 두 번째 WORD 실패도 출력값을 보존한다. 32비트 주소 레지스터 자체를24비트로 줄이지 않는다.

| Bus 범위 | 읽는 원본 |
|---|---|
| 000000..00007f | 명시적으로 선택된128BYTE vector view |
| 000080..0fffff | kind1 fixed physical ROM window |
| 100000..1fffff | RAM index `bus & ffff` |
| 200000..2fdfff | physical `bank_base + bus - 200000`의 kind2 ROM window |
| 2fe000..2fffff | 선언된 PVC RAM snapshot |
| 나머지 | 장치 계약 미지원 오류 |

ROM physical 계산은 uint64로 검사하고8MiB 원본 범위를 넘으면 wrap하지 않는다. 현재 bank는 실제 bank 읽기에 도달했을 때만 검사한다. bank base는100000 이상이어야 하지만 정렬 제약을 추가하지 않는다. Pinned `prot_pvc.cpp:71..77`은 `100000+((ff8>>8)|(ff9<<8))`을 계산하므로 일반 입력은 바이트 단위 base도 만들 수 있다. Animation의 완전한 ff9/ff8 쌍 뒤256BYTE 정렬과 일반 PVC 장치 상태를 혼동하지 않는다.

`write_program_bus_ram`은 동일한 mirror와24비트 주소 선택을 쓰되 destination 전체가 RAM인지 먼저 확인한다. 마지막 WORD가 ROM/장치에 닿으면 첫 WORD도 쓰지 않는다. 이는 C++ API의 실패 시 보존 계약이며 원본 CPU bus fault의 부분 효과를 재현한다는 뜻이 아니다.

## 리소스 선택과 앞선 설계의 수정

기존 MS5D v1 kind1/2 loader·header·CRC 계약을 유지한다. API가 직접 받은 구조체도 기존 metadata의 주소/범위로 분류한다. Odd-start resource는 유효하다. 각 도달한 BYTE/WORD는 유효 리소스 하나가 전부 덮어야 하며, 부분 겹침 또는 중복 겹침도 모호한 입력으로 거절한다. 두 WORD 경계에 맞춰 인접한 리소스로 LONG을 읽는 것은 허용하지만 WORD를 여러 BYTE 조각에서 합치지는 않는다.

앞선 `animation-bus-read-design.md`의 active bank equality 제안은 physical 재사용 정책으로 수정한다. kind2의 CPU 주소는 추출 당시 mapping 근거이지 영구적인 runtime binding이 아니다. 현재 bank로 계산한 physical 주소를 리소스의 physical span에서 찾는다. 예를 들어 기존 primary_root는 CPU200004/physical300004의4BYTE다. bank2fff00일 때 CPU200104도 같은 physical300004를 읽어야 하므로 stored bank300000과 current bank가 같다는 검사를 추가하면 안 된다. 같은 CPU 창을 가진 서로 다른 physical bank들은 이 선택에서 충돌하지 않는다.

기존 scene/animation 실행기의 reader 동작은 이 단위에서 교체하지 않는다. 새 helper를 whole49fc6에 연결할 때 해당 호출의 stack·장치 상태 계약까지 검증해야 한다.

## 현재 리소스와 전체 표현 범위의 차이

`pack_animation_banked_reads.py`는 frozen native95조건에서 실제 읽힌 ROM unit을 원본 bytes와 다시 대조한다. 같은 kind/physical bank의 겹치거나 인접한 구간을 합쳐 MS5D37개(fixed14/banked23), payload170BYTE를 생성한다. RAM/PVC를 ROM 파일로 만들지 않으며 field와 vector의 bytes를 논리 table 전체나 자연 사용 증거로 해석하지 않는다. 고정 원본·관측기·보고서·실제 trace·추출기·기존 loader 해시가 metadata에 연결된다.

**아직 필요한 규격 확장:** v1 kind2의 CPU end 상한2ffff0과 aligned1MiB storage bank 조건 때문에 physical bank1..7의 끝16BYTE씩, 총112BYTE를 표현할 수 없다. 현재 bank202100의 CPU2fdef0은 실제 physical2ffff0을 읽지만 이 구간을 담을 유효 v1 kind2 header는 없다. 버스에서 유효한 읽기와 현재 공급된 리소스 범위를 구분하며 이 경우 누락 오류를 반환한다. 임의 padding이나 다른 원본 bytes로 대체하지 않는다.

전체 ROM 재사용을 위해서는 physical-ROM 전용 MS5D kind를 명시적으로 추가하거나 kind2의 새 version으로 byte-granular source mapping을 정의해야 한다. 기존 v1 의미를 조용히 넓히지 않는다. 후속 설계는 CPU mapping과 raw physical bytes를 분리하는 physical-ROM kind를 우선 검토하고, kind 식별을 loader·C++ 구조체·CLI·packer에 끝까지 보존해야 한다. 이 단위의37리소스 검증으로 전체 format coverage를 선언하지 않는다.

## Lookup 동작과 실패 의미

`execute_animation_banked_lookup`은 A1이 selector BYTE를 가리키는 상태에서 시작한다. D0를0으로 만든 뒤 selector와 실제 field WORD를 읽고, 첫 signed WORD offset으로200004에서 LONG pointer를 구한다. 다음 signed WORD offset으로 그 pointer가 가리키는 LONG을 읽어 D7에 넣고 A6+signed field에 쓴다. 모든 operand/lookup 읽기는 destination 쓰기보다 먼저 실행한다. WORD 갱신 시 상위16비트를 보존하고 주소 가산은32비트로 wrap한다.

상태는 기존 `SceneMapTransferState`의13레지스터(D0..D7/A0..A4)를 사용하며 A6는 별도 불변 입력이다. A5/A6와 A7의 변경이 없는 본체이므로 새 register 저장 형식을 만들지 않는다. D6 publication, stack, bank writes, CCR은 이 API가 처리하지 않는다. 실패는 RAM과 register를 보존하고 성공은 error를 비운다.

95 native조건 중73완료를 실제 C++ CLI의13레지스터·전체 RAM과 비교한다. Native guard는 하드웨어 예외 정답이 아니므로 따로 다룬다. 특히 high32bit3조건은 새 reader의24비트 mask와 원본 관측기의 명시적 제외 정책이 달라 단순 성공/실패 동등성 대상에서 분리한다. 나머지19guard도 C++의 transactional rejection 증거와 원본의 부분 실행 효과를 혼동하지 않는다.

## 다음 전체 호출 연결

Coherent RAM에서 stack도 동일한 bytes다. 기존 isolated-stack observer나 C++ continuation metadata를 그대로 재사용하면40의 음수 offset이 읽는 deadstack이 달라질 수 있다. 먼저 caller A7와 실제 frame 쓰기를 상태에 표현하고 whole49fc6를 동일한 mirror 환경에서 다시 관측해야 한다. 이 원칙은 전체 목표를 위한 필수 후속 작업이며 isolated 함수 성공으로 대체하지 않는다.
