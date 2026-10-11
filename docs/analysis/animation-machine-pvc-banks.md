# PVC bank 레지스터와 banked window 전체 매핑: 관측기와 U06 `eb7b6` 객체 (시드 58·59)

**상태: 네이티브 관측 기록(분석 근거). C++ 구현이나 검증 기록이 아니다.** [F]=원본 소스·ROM 바이트 또는 이 관측기 실행에서 확인한 사실, [I]=추론, [U]=미확인.

고정 입력: ROM canonical BE `extracted/program/maincpu.decrypted.be.bin`(8,388,608바이트), SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`(관측 전후 SHA·mtime 동일을 assert). MAME 기준 리비전 `df09546b783c419889a2386bec9402883574b881`(`artifacts/reference/neogeo.cpp` SHA256 `77324df687d4cf49c6874a9f83d6253a69f7db59404b878a51685850207afc97`, `prot_pvc.cpp` `3bf2b2e1e57395abb04c2c42dc724b6792f09177e11c9fdff99b825f36ba9dd0`). 대상 계약: `animation-machine-objects-u06-contract.md`(SHA256 `0a4da066786e1db47158753dbe24ba0449b0af37394cb77c9695c2bbf99f31aa`). C++ 기준 트리: `/Users/start/Workspce/metalslug-input`(HEAD `a4e9253`, U01..U06 병합 WIP) `engine/src/animation_machine.cpp` `e7bebbad077b391175a4f64434c6862a91859a08e33eadd517e4e9cc5dd74cdb`, `program_bus.cpp` `0398a818d478185209d25ff417d21d8c60cc947e91947b32d1ed95ed2732164b`, `animation_machine_objects_u06.cpp` `1d07cbe2269f56a2c101b1dd1fe970ee1e41b9f97899a1083689079662b0080f`.

## 1. bank 식과 ROM 배치 (근거)

### 1.1 bank 식

- [F] MAME `prot_pvc.cpp:71..77` `pvc_prot_device::get_bank_base()`: `bankaddress=((ff8>>8)|(ff9<<8)); ff8=(ff8&0xfe00)|0x00a0; ff9&=0x7fff; return bankaddress+0x100000;` (`ff8`/`ff9`은 PVC RAM WORD 인덱스 `0xff8`/`0xff9`, 즉 CPU `2ffff0`/`2ffff2`). 식은 **원래** WORD로 base를 계산한 뒤 두 레지스터 부수효과를 적용한다. ROM 크기로 wrap하지 않고 정렬 제한도 없다(`tools/address_map.py` `pvc_bank_update`, `address-map.md`).
- [F] MAME `neogeo.cpp:1231..1241` `write_bankprot_pvc`: PVC 영역(`2fe000..2fffff`, `neogeo.cpp:1483..1484`) 쓰기에서 cart RAM에 쓴 뒤 **word offset >= 0xff8**(CPU `2ffff0..2fffff` 모든 WORD)이면 `m_bank_base=get_bank_base(data)`, `m_bank_cartridge->set_base(rom_base + m_bank_base)`. 읽기 bank는 `2000000..2fffff`에 설치되고(`:1412`) PVC overlay `2fe000..2fffff`가 위를 덮는다. 데이터는 base 계산에 쓰이지 않는다(WORD 레지스터 상태만 쓴다).
- [F] ROM 영역 정의 `neogeo.cpp:9838` `ROM_REGION(0x800000,"cslot1:maincpu",...)`, `p1`@0·`p2`@2 32비트 워드 인터리브 (`pvc-program.md`). 이 8 MiB 영역이 `set_base`의 대상이다.
- [F] C++ 기준 트리: `animation_machine.cpp` `pvc_effects`가 `index>=0xff8`에서 `device.bank_base=0x100000U+((ff8>>8)|(ff9<<8)); ff8=(ff8&fe00)|a0; ff9&=7fff`를 수행하고 `am_write`가 쓰기마다 `c.bus.bank_base`를 갱신한다. `program_bus.cpp` 읽기: `physical=bank_base+(address-200000)`, `bank_base<100000 || physical+size>800000`이면 `reached program bank physical span outside ROM`, 아니면 legacy kind2 창 또는 kind3 물리 창으로 읽는다. 식은 MAME와 같다(문자열을 관측기가 파싱·assert).
- [F] 관측기는 같은 식을 독립 구현(`pvc_pair`)하여 `address_map.pvc_bank_update`와 1,722점 격자(ff8 7값 × ff9 246값)에서 일치함을 assert했다(불일치 0).

### 1.2 ROM 파일 배치 ("bank 0..7")

- [F] CPU `0..fffff` ↔ 파일 오프셋 `0..fffff`(고정 카트리지 ROM, `cpu_to_rom_offset`). CPU `100000..10ffff` work RAM(16 mirror), `2fe000..2fffff` PVC RAM(ROM이 아님).
- [F] CPU `200000..2fdfff` ↔ 파일 오프셋 `bank_base + (cpu - 200000)`. `bank_base`는 **BYTE 오프셋**이다(1 MiB 배수가 아니어도 됨). 아래 `k=bank_base/100000`은 정렬된 경우의 번호이며, 8 MiB 이미지는 1 MiB 구간 `k=0..7`으로 나뉜다.
- [F] 식이 만드는 bank는 `k>=1`이다(식이 `+100000`). `k=0`(base 0)은 만들 수 없다. 한 번의 `ff9` WORD 쓰기(`ff8` 상위 바이트 0)로 `k=(ff9>>12)+1`: `ff9=0x1000*(k-1)`. 전창(`fe000`바이트)이 이미지 안인 최대 base는 `701fff`; `k=7`(`700000`)은 전체 창이 이미지 안, `k>=8`(`800000` 이상)은 창이 이미지 밖이다.
- [F] `ff9` bit15를 쓰는 값(`(n+1)<<12`에서 `n=7`)은 그 쓰기에서 base `900000`을 만들고 곧 `ff9&=7fff`로 bit15를 지운다. 다음 `ff8` 쓰기의 base는 `100000`(`k=1`)이 된다.
- [I] 따라서 "bank 4/5"는 `k=4`(`400000`)/`k=5`(`500000`)이다. 코드에서는 `n=(80(A6) AND 7)`, 첫 쓰기 `ff9=(n+1)<<12`로 `base=(n+2)·100000`(`n<=6`).

### 1.3 `eba3e`가 만드는 bank 순서

[F] `eba3e`는 `ff9=(n+1)<<12`(2ffff2) → `ff8=0`(2ffff0) → 읽기 → `ff9=1000`(2ffff2) → `ff8=0`(2ffff0)을 쓴다(WORD 4건, port 이벤트 4건). 읽기에 쓰는 base는 두 번째 쓰기 후의 값이다(첫 쓰기 `ff9`에 `ff8=a0`이 섞여도 `a0>>8=0`). 마지막 쓰기 후 base는 `200000`, `ff8=00a0`, `ff9=1000`으로 복귀한다.

| n | 쓰기1 후 base | 읽기 base(쓰기2 후) | 창 `base..base+fe000`이 이미지 안 | 관측기 sweep(`80(A6)=n`, D2=0) |
| --- | --- | --- | --- | --- |
| 0 | `200000` | `200000` | 예 | 포인터 `22bd12`, 목록 읽기 성공 |
| 1 | `300000` | `300000` | 예 | 포인터 `200008`, 목록 59,788건 성공 |
| 2 | `400000` | `400000` | 예 | 포인터 `205704`, 목록 2,723건 성공(`eba9e` 36 entry) |
| 3 | `500000` | `500000` | 예 | 포인터 `20011c`, 목록 439건 성공(57 entry) |
| 4 | `600000` | `600000` | 예 | `base+4`의 LONG이 `ffffffff`(포인터), 이어서 주소 `00000003`의 LONG 읽기가 홀수 접근 가드 |
| 5 | `700000` | `700000` | 예(`7fe000`까지) | 위와 같음(`ffffffff`) |
| 6 | `800000` | `800000` | **아니오** | 첫 banked LONG 읽기가 `bank-read-outside-rom` 가드 |
| 7 | `900000`(bit15) | `100000` | 예 | `100004`의 LONG `ffffffff` → 홀수 접근 가드 |

[F] `eba9e` 표 93 entry는 모두 `n=2`(36)·`n=3`(57)이다(U06 계약과 같음). 다른 n 줄은 관측기 sweep 고정값(`80(A6)=n`, `n|7ffc<<1` 두 점)이며 게임이 쓰는 값이 아니다.

## 2. 관측기

`tools/observe_animation_machine_pvc_banks.py`(SHA256 `86ebf962e3b83eef6882c1f96845c117edfa735c3137960b1cbda6623768d3a0`). `observe_animation_machine_scheduler.py`(SHA256 `62bb23ff6d2f61a5e47af71b8e1308d50c99b85d95f3278b8d825b7ee327c01c`, 수정 없음)를 import하고 `Machine` 클래스만 `PvcMachine`으로 바꾼다.

- [F] 동일한 것: 고정 ROM `0..fffff` 읽기 전용(쓰기는 가드), work RAM 16 mirror, PVC 페이지(`2ffff0`/`2ffff2` WORD 쓰기만 허용, 나머지 PVC 쓰기는 가드), 장치 창, F2 프레임 패스 선언 프로토콜, 선언 대기, 상태 SHA(`MS5-SCHED-STATE-1`: RAM 64 KiB·레지스터 16·PC·bank base·ff8·ff9).
- [F] 달라진 것: 스케줄러 Machine은 base `200000`/`300000`만 허용하고 그 밖의 `2ffff0/2` 쓰기를 `unsupported-bank-mapping` 가드로 멈췄다. `PvcMachine`은 쓰기마다 식으로 base를 구해 창을 `program[base:base+fe000]`로 다시 채운다. **쓰기 시점 가드는 없다.** 가드는 읽기 시점에 창이 이미지 밖(`base+offset+size>800000`)을 읽을 때만(`bank-read-outside-rom`, C++ `program_bus`와 같은 판단 지점). 홀수 PC·홀수 data 접근·24비트 밖 주소·미매핑 읽기는 기존 가드다.
- [F] 독립 모델(Unicorn·capstone·C++ 비공유): `pvc_pair`(식), `eba3e_model`(`eba3e` 전체: D2·bank 순서·첫 LONG·목록 길이·최종 레지스터·RAM·port·읽기 순서). 목록 포인터는 고정 ROM·work RAM·banked 창만 해석하고 그 밖은 가드로 분류한다. D3 카운터는 16비트(`ADDQ.W`)로 wrap한다.

## 3. 결과 (`artifacts/animation_machine_pvc_banks_native/`, 21 MB, `observation.json` SHA256 `613bd4648d7ed3035620ad1949e1be4c94e4e866635a788a423df6c9650a65fe`)

### 3.1 bank 4/5 읽기는 ROM 안이며 의미 있는 값이다

- [F] 93 entry 전부: 읽기 base `400000`(36)·`500000`(57), 첫 LONG(`base+4+D2`)이 창 안 포인터(`2000b0..2cc3f8`), 목록은 LONG 0으로 끝나며 길이(`7a(A6)`)는 7..8,248, 목록 원소는 모두 `200820..2d6274`(banked 창 안, 짝수), 읽기는 전부 물리 `<=5fdfff`(이미지 안). 모델이 계산한 LONG 읽기 총합 37,109건. 목록은 entry 1·3을 뺀 91개에서 단조 증가하고, entry 1·3은 각각 4·3개 오름차순 구간이다.
- [I] 각 entry는 (bank 선택값, 목록 포인터 표 인덱스 `D2`)이고 목록은 banked 데이터의 포인터 배열(애니메이션/스프라이트 자료로 보이나 의미는 미확인 [U]). U06 계약이 "설명 불가"로 둔 bank 4/5는 **모양이 정상**이다(포인터 표 → 오름차순 포인터 목록 → 0 종결).
- [F] 직접 `eba3e` fixture 93×2 seed와 객체 fixture 93×2 seed 모두 독립 모델과 일치: 최종 레지스터 16개, RAM 전체 64 KiB(스택에 남는 WORD·`7a(A6)`·`100010` 포함), port 4건(`2ffff2=n+1<<12`, `2ffff0=0`, `2ffff2=1000`, `2ffff0=0`), bank 기록(`bank_writes` 베이스 순서), 최종 bank `(200000,a0,1000)`, 읽기 순서·bank 번호. fresh-CPU 분할(`eba78` 첫 도착에서 상태를 캡처해 새 CPU로 이어 실행)과 연속 실행, 각 2회가 모두 같다.
- [F] 일반 sweep(n=0..7 × D2 {0,7ffc}, 16건×2 seed)도 모델과 일치한다(`n=6`은 창이 이미지 밖이라 `bank-read-outside-rom`, `n=4/5/7`은 `ffffffff` 포인터 후 홀수 PC 읽기 가드 등).

### 3.2 `eb7b6` 객체가 하는 일

- [F] `eb7b6`(프레임 0, 노드 `101020`): 표 entry 수 93을 세어 `78(A6)=93`, `7c/7e/88(A6)=0`, `8a(A6)=2`, `c6a96`(U05) 호출 후 entry 0을 `80/84/86(A6)=00000002/0c00/0009`로 적재하고 `eba3e`를 호출한다. `eba3e`는 PVC 쓰기 4건, bank 4(`400000`)의 `400004`에서 포인터(`205704`)를 읽고 목록 2,724 LONG을 걸어 `7a(A6)=2723`을 둔 뒤 bank를 `200000`으로 되돌린다(`100010`=0). 이 1회 실행이 banked 읽기 2,725건(명령 11,541개)이다. 이어 `eb818`에서 콜백을 `eb81e`로 설치하고 같은 호출에서 `eb81e` 본체(fall-through)를 한 번 실행한 뒤 반환한다(TB `eb832..eb9b8`).
- [F] 이후 frame 1..85: `eb81e` 본체만 실행(입력 BYTE 전부 0이므로 노드마다 port 0건, bank 읽기 0건). frame 86에서 이벤트 노드 `e9176`과 함께 목록에서 사라진다(86 frame 생존) [I: 이벤트 쪽이 객체를 정리].
- [F] 입력 fixture(`eb81e` 노드, `76(A6)=0`, BYTE 하나씩): `-3346(A5)=104cba`의 bit6(오른쪽)/bit7(왼쪽)은 `7c(A6)`를 ±1하고 `eb9e4`(U06 경계 callee, executor 없음)가 표 entry를 다시 적재해 `eba3e`로 새 bank를 쓴다(오른쪽 entry 1: `2ffff2=3000`; 왼쪽 entry 92: `2ffff2=4000`, bank 5). bit4/5는 `7e(A6)±1`, `eb9ba`(경계). `104cbe` bit0..3은 `46/42(A6)`를 ±1, `104cc0` bit4/5는 `88(A6)`(`8ff4`·`8ebe`), `104cbf` bit6은 `8a(A6)` 토글과 `101c`(경계).
- [F] 93 entry **전부**를 객체가 도달하는 경로는 `eb9e4`를 거친다(entry 0만 `eb7f2`에서 U06 안 호출). 입력 이동이 없는 자연 경로는 entry 0(bank 4) 하나뿐이다.

### 3.3 시드 58·59 (F2 프레임 패스 120 frame)

- [F] 두 시드의 begin 출력 RAM은 SHA256 `a00cb39f07d9feedf13fde94d9f8695cc435a7a903282d8c0e500c27c82fdefe`로 **동일**하다(family `actual59-catalog-records`, record 891782, profile 0/1만 다름). 따라서 pass별 상태 SHA·node digest가 두 시드에서 모두 같다(실행 SHA256 `7a7b198e77bd85f3a63e6e1fe4b3d49ff90efe014290c70fc354ea093109ebaa`).
- [F] 두 시드 모두 120 frame 완주(`frame-limit`, 모든 pass가 `frame-head`에서 종료, `a7_bad=0`, `head_bad=0`, 대기 0, 모델 불일치 0). 연속 2회·분할 2회의 digest가 모두 일치. pass별 전체 상태 SHA·node 진입/탈출 digest는 `seeds/seed_00{58,59}.json.gz`, 120 pass-end 전체 덤프 + seed-start는 `blobs/<sha>.bin`(124개).
- [F] 실행된 콜백 12종: `270e`(514) `47af0` `47bfc`(24) `47fa8`(31) `47fdc`(31) `4806a`(33) `4fcce` `4fcda`(23) `e9150` `e9176`(85) `eb7b6`(1) `eb81e`(85).
- [F] **다음 누락 콜백은 없다.** 병합 트리(`metalslug-input`, U01..U06) 라우팅 기준 120 frame의 모든 콜백이 진입 PC로 라우팅된다(`first_uncovered=null`). 메인 트리(`engine/src/animation_machine.cpp`) 레벨 A 기준 첫 누락은 frame 0 순서 5의 `eb7b6`(`964534`)다. `eb7b6`·`eb81e` 노드의 실행 TB 시작 전부가 병합 트리 executor 안이고 U06 구간의 TB 시작은 전부 계약 block 시작이다(`tb_not_contract_start`·`unrouted` 모두 비어 있음; owner: U06 29/21, U05 13, U02 17, 스프라이트 9, fade-card 1).
- [F] 완주를 막던 것은 `eba5c`의 native 가드 하나뿐이었다. 시드 58·59는 frame 0에서 멈추지 않는다.

### 3.4 검증 합계

[F] fixture 426건(시드당 213: 직접 `eba3e` 93 + 객체 `eb81e` 93 + sweep 16 + 입력 11)이 전부 통과. 두 번의 전체 실행의 출력 디렉터리가 `diff -rq` 동일(`observation.json` SHA 동일), 크기 20.9 MB(<3 GB). 자연 `eb7b6` 노드를 새 CPU로 재실행한 결과가 시드 run의 node 종료 SHA·port SHA와 같고 모델과 일치한다(2/2).

## 4. U06 가드 제거 권고

[F] 가드는 `animation_machine_objects_u06.cpp` `ou6_pvc`(PVC 쓰기 4곳 `eba5c` `eba62` `eba8c` `eba94`가 모두 이 helper를 통과)의 `bank!=200000 && bank!=300000 → "objects u06 PVC bank outside model"` 한 줄이다. C++ 공용 경로(`am_write`→`pvc_effects`→`c.bus.bank_base`, `program_bus`)는 이미 모든 bank를 처리한다.

필요한 C++ 변경(최소):
1. `ou6_pvc`의 base 계산·검사를 지우고 `return am_write(c,address,2,value&65535U);`만 둔다. 공용 `am_write`/`pvc_effects`는 바꾸지 않는다(U06 결정 2가 공용 경로를 보존하라고 한 방향과 같다).
2. 오류 문자열 `objects u06 PVC bank outside model`과 관련 주석·계약 결정 7·검증 조건의 가드 항목을 삭제한다(U06 단위 test의 해당 negative는 "쓰기 성공 + bank_base 갱신"으로 바뀐다).
3. 하네스는 8개 물리 창(`extracted/runtime/program_rom/program_rom_*.ms5d`, kind3)을 `ProgramBusState::physical_rom`에 공급해야 한다(최신 F2 verifier는 이미 그렇게 한다). `400004..5fffff`는 legacy kind2 창에 없으므로 물리 창이 없으면 `missing program bus ROM unit`로 실패한다.
4. 새 test/차분 기대치: 시드 58·59 pass는 frame 0 가드 일치에서 **120 frame 완주 일치**로 바뀐다(U06 계약의 "완주 seed 52→56(58·59는 frame 0 guard 일치)" 중 58·59 행의 기대가 "120 frame 일치"로 바뀐다 — 계약 문서의 해당 문장은 이 작업이 수정하지 않았다). 경계 callee `eb9e4` `eb9ba` `101c`는 U06 밖이므로 입력 이동(`eb81e` 입력 fixture)은 여전히 executor가 필요하다. 자연 시드는 입력이 없어 영향이 없다.
5. 영향 받는 기존 verifier/기대치(수정하지 않음): U06 verifier의 PVC 가드 negative 행들, `observe_animation_machine_scheduler.py`의 `unsupported-bank-mapping` 분류·한계 문구(58·59 두 행), 스케줄러 verifier의 58·59 기대 pass 수.

[I] 가드를 제거해도 관측 가능한 부작용은 `eb7b6`의 port 4건과 읽기뿐이며 모두 모델·native와 일치했다.

## 5. 한계와 미확인

- [U] 목록 원소(포인터)가 가리키는 자료의 의미, 객체의 게임 내 역할(디버그 viewer 후보), `eb9e4` 등 경계 callee의 동작은 이 문서의 범위 밖이다.
- [F/한계] PVC 페이지는 쓴 raw WORD를 보존하고 `ff8=(ff8&fe00)|a0`, `ff9&=7fff` 부수효과는 레지스터 필드와 상태 SHA에만 반영된다(CPU가 `2ffff0/2`를 다시 읽으면 MAME 값과 다르다). `2ffff4..2fffff` 쓰기는 관측기에서 가드(MAME·C++는 base를 재계산).
- [U] 홀수 bank base(비정렬)의 실제 CPU 동작은 검증하지 않았다(관측기 슬라이스는 지원, `eba3e`는 만들지 않음). bank `k>=8`(base `>=800000`)의 창은 이미지 밖이라 읽기 가드다.
- [U] 입력 fixture는 `76(A6)=0`에서 한 비트씩만 확인했다. `76(A6)!=0`(두 번째 입력 쌍)과 `8a(A6)==1`의 `eb980`/`eb98e` 등 8개 U06 block 시작(`eb83a eb8aa eb8ee eb90a eb942 eb96a eb980 eb98e`)은 도달하지 못했다(eb7b6 계열 block 시작 59개 중 자연 도달 30, fixture 도달 45, 합집합 51).
- 전체 구간은 선언된 F2 모델이다. BIOS 실행, 자연 IRQ, 자연 scheduler를 주장하지 않는다.

## 6. 재생성

```
.venv/bin/python tools/observe_animation_machine_pvc_banks.py --out artifacts/animation_machine_pvc_banks_native
```

두 번 실행해 `diff -rq`로 비교한다(약 30초, 기본 3 worker). 입력 SHA와 도구 SHA는 `observation.json`의 `inputs`에 기록된다.
