# Animation40 원본 조회와 남은 bank 상태 설계

기준 `cc5750b`. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 메인과 Sol의 읽기 전용 조사 결과다. 아래4a382..4a3ac는 고정 CPU 주소와 ROM 파일 오프셋이 같지만 CPU200004의 물리 ROM 위치는 현재 bank에 달려 있다. C++40 구현이나 원본 whole49fc6 실행 완료를 뜻하지 않는다.

## 확정한 명령 순서

- 4a382 MOVEQ0 D0, BYTE selector를 읽고 ADD.W 한 번. A2=4a76c의 signed WORD index에서 field WORD→D0.low를 읽는다.
- 4a392 첫 WORD→D7.low. 4a394는 **LEA200004,A2**다. root LONG을 먼저 읽는 명령이 아니다. A2+sign16(D7)의 LONG→A2를 읽는다.
- 4a39e 두 번째 WORD→D7.low. A2+sign16(D7)의 LONG→D7을 읽어 A6+sign16(D0)의 LONG에 쓴다.
- 4a3a8→4a276에서 D6=A1, LONG(A0)=D6를 쓰고 dispatch한다. 첫·둘째 offset에 추가 x4 scaling은 없다. 두 번째 읽기가 반드시 banked 주소라는 보장도 없다.

## 현재 상태에서 bank를 단순 추정할 수 없는 이유

fresh49fc6의 bank shadow0 및 PVC1000/0 쓰기는 실제 bank_base200000을 선택한다. 반면 RAM100010은 bank shadow일 뿐 하드웨어 bank 레지스터가 아니다. 기존 field 명령은 alias를 통해 shadow를 바꿀 수 있으며, 이는 그 자체로 PVC를 바꾸지 않는다.

draw/callback 복귀는 saved shadow를 RAM에 복원하고 재독출한 WORD에서 ((value+1)<<12)&ffff를 계산해 PVC에 쓴다. 두-port 패턴의 각 쓰기는 PVC get_bank_base를 호출한다. 첫 쓰기가 저장 ff9의 bit15를 지우므로, 두 번째 쓰기까지 끝난 bank_base는 100000+(((value+1)&7)<<20)이다. 초기 조사에서 &15로 적었던 식은 중간 ff9 부수효과를 누락하여 정정했다. animation-bank-state-contract.md의 순차 쓰기 근거를 따른다. 새 callback→40 실행 비교는 여전히 필요하다. ROM 밖 bank를 크기로 wrap하면 안 된다.

특히 직접30은 bank 복귀가 없다. 앞선 명령이 실제 bank를 바꾼 뒤30에서 대기하면, phase4 이후40이 사용할 bank는 대기 전 실제 선택값이다. phase4의 saved_bank는0이어야 하므로 이를 현재 bank 저장소로 재활용할 수 없다. poison된 shadow를 재독출해 현재 bank를 추정하거나 재개 시 무조건 bank2로 초기화하면 원본과 다른 실행을 만들 수 있다.

따라서40 연결 전 실제 PVC 쓰기로 갱신되는 current bank를 saved shadow와 구분하는 설계가 필요하다. 대기를 넘는 current bank 표현을 state/API/CLI에 추가할지, 장치 상태 계층을 공유할지 메인이 원본 관측과 함께 결정한다. 기존17명령 지원 수를 늘리기 위해 bank2 전용으로 의미를 축소하지 않는다.

## 기존 규격의 재사용 범위와 주의점

`FixedDataResource`와 MS5D v1 kind2는 source_cpu_address/source_rom_offset/raw bytes로 정렬된1MiB bank window를 표현한다. `load_banked_data_resource`를 기존 loader와 함께 사용할 수 있다. 현재 animation CLI는 kind1만 읽고, animation read_data도 fixed/RAM만 처리하므로 loader routing과 active bank에 따른 window 선택이 필요하다. 같은 CPU span이라도 서로 다른 ROM bank는 별개 리소스다. bank로 먼저 필터한 뒤 완전한 유일 읽기인지 검증해야 한다.

기존 scene reader의 검사·transaction 패턴을 참고할 수 있지만 map root scaling 의미를40에 가져오면 안 된다. 또한 현재 kind2/scene reader의 상한2ffff0과 pinned hardware resolver의 PVC overlay 시작2fe000 사이에 계약 차이가 있다. 일반화된40 reader에서2fe000..2fffef를 조용히 ROM으로 읽어서는 안 된다. 기존 실제 리소스가 해당 영역에 닿는지 별도 조사하고 새 reader의 경계를 근거로 확정한다. 임의로 전체 기존 규격을 변경하지 않는다.

이 조사에서 자연 script 도달성·임의 callback의 PVC 변경·비정렬 bank·physical CPU timing·IRQ는 미확인이다. 다음 작업은 실제 bank 변화가 포함된40 원본 trace와 continuation 상태 계약 확정이다.

## 후속 읽기 설계에 필요한 RAM mirror와 bus 경계

메인의 추가 원본 모델 대조에서 pinned `neogeo.cpp:1727`의 MVS 및 `:1763`의 AES는 `100000..10ffff` RAM에 `0f0000` mirror를 적용한다. 따라서 첫 signed offset이 음수여서 `200004` 아래로 내려가는 경우를 하드웨어의 unmapped 주소라고 부를 수 없다. 예를 들어 `1f8004`는 RAM `108004`의 mirror다. 현재 API가 canonical RAM만 지원한다는 제한과 실제 하드웨어 주소 분류를 구분한다.

첫 offset `fffa`는 LONG 주소 `1ffffe`를 만든다. 첫 WORD는 RAM mirror `10fffe`, 다음 WORD는 bank CPU `200000`에 걸친다. 이 경계는 단일 contiguous ROM resource 검사만으로 처리할 수 없다. 후속40 reader/원본 관측은 두 WORD 버스 접근, RAM alias와 bank 선택을 함께 다뤄야 한다. 둘째 LONG의 RAM mirror·PVC 경계도 실제 읽기 순서와 장치 의미를 기준으로 분류해야 한다.

기존 bounded native 관측은 stack `1feffc`를 별도 scratch 메모리에 둔다. 실제 기판에서는 RAM mirror이므로40의 음수 offset이나 둘째 포인터가 이 주소를 읽을 때 기존 관측기를 그대로 재사용하면 잘못된 oracle이 된다. 기존 증거의 한정된 범위를 보존하되, 새40 관측기는 이 alias와 24-bit bus 주소 동작을 명시적으로 검증해야 한다. 새 bank-state 기반 구현 자체는 아직 이40 읽기를 수행하지 않는다.
