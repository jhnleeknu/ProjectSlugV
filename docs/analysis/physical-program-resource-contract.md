# 전체 프로그램 ROM을 위한 MS5D physical resource 계약

Baseline `48465d6`, branch `codex/physical-program-resources`. Canonical8MiB 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 기존 kind2로 표현하지 못하는 각 bank 끝16BYTE를 포함하여 모든 bytes를 C++가 직접 읽는 공통 리소스에 보존한다. 모든 bytes의 의미나 모든 코드의 C++ 복원이 완료됐다는 뜻은 아니다.

## 형식 선택

기존 MS5D v1의32BYTE header를 유지하고 **kind3**을 physical program ROM window로 추가한다. Kind1/2의 의미나 loader 검증 규칙은 변경하지 않는다. 현재 runtime 파일683개를 inventory한 결과kind1은389개,kind2는294개이며kind3은 없었다. Kind 값은 magic별로 구분하므로 다른 형식의 kind3과 충돌하지 않는다.

| Offset | 필드 | kind3 조건 |
|---|---|---|
| 0 | 4BYTE magic | ASCII MS5D |
| 4 | LE32 version | 1 |
| 8 | LE32 kind | 3 |
| 12 | LE32 source CPU field | ffffffff, CPU binding 없음의 sentinel |
| 16 | LE32 physical ROM offset | 0 이상800000 미만 |
| 20 | LE32 payload size | 1..100000, physical end≤800000 |
| 24 | LE32 payload CRC32 | 기존 MS5D와 동일한 CRC |
| 28 | LE32 reserved | 0 |
| 32 | raw payload | 원본 bytes 그대로, 정확한 파일 길이는32+size |

CPU sentinel은 runtime 주소가 아니며24비트로 mask해서 사용하지 않는다. Source ROM offset과 payload만 가진 별도 C++ 타입 `PhysicalRomResource`가 kind3의 의미를 보존한다. `load_physical_rom_resource`는kind3만 받고 기존 `FixedDataResource`나 kind1/2 loader에 몰래 새 의미를 넣지 않는다. 실패 시 기존 리소스를 보존한다. 범용 kind3 window는 정렬 제약 없이 홀수 physical 시작·길이를 지원한다.

## 전체 추출과 미사용 bytes

`pack_physical_program.py`는 프로그램을8개의 인접한1MiB kind3 창으로 보존한다. `program_rom_%06x.ms5d`와 stable ID `physical-program:%08x`의 숫자는 physical 시작 offset이다. 출력은 `extracted/runtime/program_rom/`이며 manifest에 원본 hash, CPU binding 없음, physical 시작/끝, payload/container hash와 CRC, 생성 도구를 기록한다.

8개 payload의 연결은 원본8MiB와 byte 단위로 같아야 한다. 코드·데이터·미사용 여부를 추측해서 제외하지 않는다. 이 보존은 의미 분석과 분리한다. 기존 bank1..7의 마지막16BYTE씩112BYTE도 coverage에 들어가며 padding이나 대체값이 아니다. ROM·산출물은 Git에 추가하지 않고 도구·규격·검증 근거만 관리한다.

## 버스의 kind3 소비

`ProgramBusState.physical_rom`은 `vector<PhysicalRomResource>`에 대한 borrowed pointer이며 소유자는 호출 동안 살아 있어야 한다. 기존 함수 signature와 kind1/2 목록을 유지한다. Fixed 또는 bank ROM 접근에서 계산한 physical 주소로 kind3을 읽는다. Vector/PVC 영역은 장치 상태가 우선하며 raw ROM 리소스가 있어도 자동 fallback하지 않는다.

일반 PVC base는 홀수일 수 있으므로 짝수 CPU WORD가 홀수 physical offset에 대응할 수 있다. 예를 들어 physical2fffff에서 시작하는 WORD는 인접한1MiB 파일 두 개에 걸친다. 따라서 kind3은 **byte 단위의 유일한 physical coverage**를 제공하며 같은 WORD가 인접한 비중첩 kind3 창을 이어 읽는 것을 허용한다. 한 byte라도 빠지거나 둘 이상이 덮으면 실패한다. LONG은 여전히 두 CPU WORD이고 각각 주소/장치 선택을 거친다.

기존 kind1/2의 WORD 단위 완전한 창 요구는 유지한다. 해당 WORD에 legacy 창이 하나라도 겹치면 기존처럼 유일한 완전한 legacy 창이어야 하고, 같은 unit에 kind3까지 겹치면 모호한 입력으로 실패한다. Legacy의 부분 BYTE와 kind3을 조합하거나 같은 bytes라는 이유로 우선순위를 정하지 않는다. 둘이 서로 겹치지 않는 ROM 구간을 맡는 구성은 가능하다. 실패는 출력값을 보존한다.

이 규칙으로8개 kind3 파일만 제공하면 fixed ROM과 모든 유효 bank physical bytes를 읽을 수 있다. Cart/BIOS vector의 실제 선택, PVC 상태·쓰기, 다른 MMIO, CPU timing과 natural execution은 별도 계약이다.

## 검증 범위

형식 검증은 header/version/kind/sentinel/reserved,범위,정확한 길이,CRC,실패 보존 및kind1/2와의 상호 거절을 포함한다. 버스 검증은 전체 physical bytes의 C++ 소비,종전112BYTE gap,홀수 physical WORD의 파일 경계,8MiB 마지막 byte,범위 밖 주소,중첩/빈틈,device override를 포함한다.

기존 animation40 본체의73개 원본 완료 사례를 kind3으로도 소비할 수 있어야 하며, 기존 kind1/2 경로의 회귀 검증은 유지한다. 전체 파일 덤프를 C++ 로더가 읽었다는 사실만으로 이 동작 대조를 대체하지 않는다. Full49fc6의 stack/frame 연결과 명령 완료 집계는 별도다.
