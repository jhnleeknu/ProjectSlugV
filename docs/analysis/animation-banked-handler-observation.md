# Animation40 banked handler의 제한된 원본 관측

Baseline `e40334b`. canonical big-endian program SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. `tools/observe_animation_banked_handler.py`는 수정하지 않은 원본 `4a382..4a3ac`를 실행하고 **`4a276` 실행 전에 중단**한다. 이 고정 코드의 CPU 주소와 ROM 파일 offset은 같다. handler raw SHA256은 `25ba0fc048cf7394c4e87c564766f4c980d113e18ef17aeb056a9356b54d530d`이다.

이 관측은 opcode40의 조회·store 본체에 대한 근거다. `49fc6` 전체 진입, PVC bank 선택, `4a276`의 script pointer publication, 다음 dispatch와 RTS는 실행하지 않는다. C++ 비교·새 리소스 소비·opcode40 전체 완료나 자연 게임 도달성을 뜻하지 않는다.

## 실제 실행한 명령

A1은 opcode BYTE를 이미 소비한 위치, 즉 selector BYTE를 가리키도록 준비한다. 아래 operand들은 합성 RAM fixture이며 field table과 ROM pointer bytes는 원본이다.

| 원본 PC | 동작과 비트 폭 |
| --- | --- |
| `4a382..4a38e` | D0=0; BYTE `(A1)+`를 읽고 `ADD.W`로 두 배. A2=`4a76c`; `WORD(A2+signed16(D0.low))`를 D0.low에 읽는다. D0.high16은 0이다. |
| `4a392..4a39a` | 첫 WORD `(A1)+`를 D7.low에 읽으며 high16은 보존한다. A2=`200004`; `LONG(A2+signed16(D7.low))`를 A2에 읽는다. root LONG을 먼저 읽거나 displacement를 네 배 하지 않는다. |
| `4a39e..4a3a0` | 둘째 WORD `(A1)+`를 D7.low에 읽으며 high16을 보존한다. `LONG(A2+signed16(D7.low))`를 D7 전체에 읽는다. 둘째 주소는 banked ROM에 한정되지 않는다. |
| `4a3a4..4a3a8` | D7 LONG을 `A6+signed16(D0.low)`에 쓴 뒤 `4a276`으로 분기한다. 분기 목적지 명령은 관측 범위 밖이다. |

완료 사례는 A1이 정확히 5바이트 진행하고 D0/D7/A1/A2의 효과를 포함한 15레지스터와 A7, 전체64KiB RAM을 비교한다. D6는 `4a276`을 실행하지 않아 incoming 값을 유지한다. 두 조회와 operand 읽기가 destination store보다 먼저 일어나며, operand·첫 pointer·둘째 source와 destination이 겹치는 fixture도 이 순서를 검사한다. guard 사례는 중단 PC까지의 부분 register/RAM 효과를 비교하며 전체 명령 완료로 세지 않는다.

## 주소와 bus 모델

원본 CPU 명령 실행과 host가 제공한 bus mapping을 구분한다. pinned MAME revision `df09546b783c419889a2386bec9402883574b881`의 `neogeo.cpp`와 `prot_pvc.cpp` 원문·해시·행을 `source.json`과 observation에 기록했다.

- fixed `000000..0fffff`는 canonical cartridge ROM view다. `000000..00007f`도 cartridge vector로 제공하며 실제 BIOS/cart vector 선택은 검증하지 않는다.
- `100000..1fffff`는 동일한64KiB backing을 16번 매핑한다. pinned MVS/AES RAM mirror 근거와 대응하며 mirror 사이 store, 내부64KiB 경계와 alias를 검사한다.
- bank CPU `200000..2fdfff`는 선언한 `bank_base + CPU - 200000`의 원본 bytes다. 이 관측에서는 whole-MiB bank1..8만 선택한다. bank window 전체를 원본이 뒷받침하지 못하면 매핑하지 않는다. bank8이어도 실제 읽기가 RAM에만 도달하면 선행 거부하지 않는다.
- `2fe000..2fffff`는 선언한 PVC cart RAM이며 ROM이 아니다. incoming bytes는 fixture가 제공한다. handler는 이 영역을 읽을 수 있지만 PVC store나 실제 장치 bank 선택을 관측하지 않는다.
- LONG 경계 사례는 fixed→RAM, RAM mirror→bank, bank→PVC를 포함한다. trace는 Unicorn의 논리 접근이며 실제 두 WORD bus cycle이나 timing을 측정한 것이 아니다.

주소 연산의32-bit wrap과24-bit bus masking을 혼동하지 않는다. backend의 실제32-bit 연산 결과를 관측하되 `1000000` 이상 유효 주소와 `300000..ffffff` 장치 영역은 접근 전에 guard로 제외한다. 실제68000의24-bit 주소선 masking은 이번 관측기에 구현하지 않았다. 홀수 WORD/LONG도 Unicorn의 address-error 동작을 신뢰하지 않고 실행 전에 guard로 중단한다.

## 관측 결과와 독립 감사

소유권 수명 수정 후 동결 결과는 **95사례=완료73+guard/제외22**다. 각 사례는 새 Unicorn CPU와 RAM backing으로 두 번 실행되어 일치했다. guard/제외22는 홀수 주소10,32-bit high 주소3, 미지원 장치5, bank 원본 범위 부족2, fixed ROM destination1, bank ROM destination1이다. 이들은 원본 하드웨어 예외를 실제 실행한 결과가 아니다.

bank2/3/4/5의 원본 첫 pointer, signed offset 경계, RAM-first 및 혼합 LONG, PVC overlay, field selector BYTE 경계, destination alias와 operand mirror를 포함한다. 별도 guard-disabled8사례는 backend가 guard 없이 보이는 동작을 기록한다. 이를68000 하드웨어 정답으로 취급하지 않는다.

원본 고정 코드와 bank bytes는 읽기/실행 또는 읽기 전용으로 매핑하고 실행 뒤 변경 없음을 검사했다. hook은 live 주소·접근·register를 읽거나 guard로 중단하며 expected 값을 CPU에 주입하지 않는다. SR은 준비 때 A7보다 먼저 쓰고 실행 중 hook에서 읽거나 쓰지 않는다. A7은 보존하며 가짜 stack/dispatch/RTS를 추가하지 않는다.

Unicorn `reg_read(SR)`가 lazy N/Z/V/C를 모두 반영하지 않는다는 별도 합성 probe4종을 기록했다. 따라서 비교한 native SR은 system BYTE뿐이다. `model_ccr_not_natively_observed`는 Python 모델의 값이며 native CCR 검증으로 세지 않는다.

원본 관측 작업자는 Claude Opus5.5였고 요청 effort는 high였다. 반환된 실행 정보에는 적용 effort 필드가 없어 실제 적용값을 별도로 확정하지 않는다. 독립 gpt-6.1-sol/medium은 `main()`을 호출하지 않고95개 `run_case`와8개 guard control, SR probe를 메모리에서 재실행했다. 모든 summary·15레지스터/A7·RAM·trace와380개 payload가 일치했고 입력5개/산출물380개의 해시, manifest, pinned 참조와 oracle library/wrapper 해시를 확인했다. canonical ROM hash/stat은 보존됐다.

## 소유권 수명 수정과 최종 해시

독립 실행 감사 뒤 메인 리뷰에서 P1 owner-lifetime 문제가 확인됐다. hook callback의 순환 참조가 Unicorn CPU의 해제를 지연할 수 있으므로 외부 ctypes backing 참조를 먼저 해제하는 것만으로 mapping 수명을 보장할 수 없었다. 수정은 `mem_map_ptr` 전에 `cpu._ram_backing=self.backing`을 설정하여 CPU가 mapping의 backing 소유자를 함께 보존하도록 한다. 원본 명령이나 fixture 의미를 바꾸지 않았다.

메인은 수정본95사례를 다시 생성했다. 독립 Sol도 수정본95사례/380payload, guard control8개와 SR probe를 다시 메모리에서 실행하고 모든 row·bytes·해시 일치를 확인했다. 별도 Sol의 실제 수정본 수명 검사도 메인이 확인했다. GC를 비활성화한 상태에서 close 후 CPU·backing이 함께 유지됐고 명시적 GC 후 모두 회수됐다. 해제된 pointer를 역참조하지 않고 소유권만 검사했다. 최종 합성 bus probe27개도 각각 별도 process로 재실행해 통과했다.

- 최종 observer SHA256: `66a156cd73be2a10cfb91413396a8fa9379f6ee09cea48c17f3d561d3e9daed3`.
- 최종 observation SHA256: `a6b075d468e015c8fde64129abf6003964bd1f1669ef8c6538545cc0aa3d39a5`.
- 수정 후 독립 감사 `/tmp/ms5-banked-handler-independent-audit.txt` SHA256: `4f6b666b6d3dc6d47b96dc156aee6711f4449f1a34e8b32f77cc9324ca979a47`.

수정 전 observer `34e92c169a862c061b38fbe3bb39616b4f0e7f21fc53adc3fe8d944982a60616` 및 observation `c15a224ccce2add5e63a0fee73bf6f72876573ca6c4c36f7b9c430cde041e5ff`는 위 최종본으로 대체됐다. 최종 pin으로 사용하지 않는다.

## 재현

프로젝트 root에서 실행한다. 관측 명령은 ignored `artifacts/animation_banked_handler_native/`를 재생성하므로 보존해야 할 기존 보고서는 먼저 구분한다. 공유 C++ build는 필요하지 않다.

```sh
cd tools
../.venv/bin/python observe_animation_banked_handler.py
```

재생성 결과의 `source.json`은 handler·field512BYTE·bank roots·pinned 참조를, `observation.json`은95개 결과·guard controls·SR probe·oracle provenance·입력/산출물 해시를 제공한다. 입력 ROM과 추출된 bytes는 Git에 추가하지 않는다. 합성 operand와 선언된 bank/PVC/vector 환경을 실제 script·자연 플레이 증거로 바꾸어 해석하지 않는다. whole49fc6→40 연결, C++ loader/API 대조, arbitrary PVC bank base, 실제24-bit bus·장치·CCR와 전체 Goal은 별도 검증 대상이다.
