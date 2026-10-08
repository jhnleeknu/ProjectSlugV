# 활성화 animation의 확인된 resource 범위

canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 주소는 모두 fixed CPU 주소=ROM 파일 오프셋이다. 이 문서는 caller 바이트와 기존 명령 형식으로 확인한 정적 inventory이며 native 실행·새 C++ 연결·자연 gameplay 도달성을 뜻하지 않는다. 원본은 수정하지 않았으며 composition을 추출하지 않았다.

재현은 `.venv/bin/python tools/inspect_activation_animation_scripts.py`다. `load_verified_program`으로 canonical 원본을 확인하고, 검토한 caller 원시 바이트를 assert한 뒤 명령별 주소/원시 바이트/operand와 raw lookup 전체 BYTE-domain을 기록한다. 산출물은 ignored `artifacts/activation_animation_static/inventory.json`이며 SHA256은 `dd55b3a4fd54f9da260d90f116a0915305886340b149f055fb650516c1f19985`다. inventory의 이름/ID는 재생성용 이름이며 원본 개발자의 식별자가 아니다.

## Caller와 index 폭의 직접 근거

| 주소 | 원시 바이트 | 확인한 효과 |
| --- | --- | --- |
| 47cd0 | 7000 | MOVEQ0 D0, 전체32bit clear |
| 47cd2 | 102e007e | MOVE.B object+7e,D0 |
| 47cd6 / 47cd8 | d040 / d040 | ADD.W D0,D0 두 번 |
| 47cda | 41f900048a12 | A0=48a12 |
| 47ce0 | 2e300000 | MOVE.L (A0,D0.W),D7 |
| 47d0a | 227c000489c2 | A1=489c2 |
| 47d10 / 47d14 | 303c0100 / 4eb900049f8c | D0.low=0100, animation initializer 호출 |
| 47d1a | 4eb900049fc6 | animation interpreter 호출 |
| 47ed0 | 3d7c00ea0020 | object+20 WORD=00ea |
| 47ed6 | 227c00048980 | A1=48980 |
| 47edc / 47ee0 | 303c0100 / 4eb900049f8c | D0.low=0100, initializer 호출 |
| 4a118 | 2e19 | draw의 BE32 operand를 D7에 읽음 |
| 4a126 | 8e6e0020 | OR.W object+20,D7 |

첫 다섯 명령에서 BYTE0..255는 D0.W의0..3fc가 된다. 최대값도 signedWORD 양수이며 LONG4바이트를 읽으므로 full-BYTE-domain 지원에 필요한 raw window는 **[48a12,48e12)1024바이트**다. 해당 caller 자체가 index를 더 좁히지 않는다. 특정 gameplay에서256개 값이 모두 실제 도달한다거나 이 범위가 하나의 논리적 테이블 전체라는 주장은 하지 않는다. 앞서47672가 object+12에 쓴 값과 이 lookup이 읽는 object+7e는 서로 다른 필드다.

전체 원본에서 BE32 바이트값48980은47ed8,489c2는47d0c/48a0e,48a12는47cdc에 나온다. 앞 두 caller의 immediate와 script jump target은 각각 위 명령/형식으로 확인했다. 단순 BE32 검색 자체를 완전한 code-reference 분석으로 취급하지 않는다.

## Script48980: 여덟 draw와 한 BYTE28

실제 명령 범위는 **[48980,489c1)65바이트**다. opcode04는8바이트(`04 control x y BE32operand`)이며 아래 여덟 명령 뒤489c0의 opcode28 한 BYTE가 온다. **489c1=00은 consumed stream 밖의 별도 BYTE**다. 다음 script가489c2에서 시작하므로 이 BYTE는 inter-stream alignment padding으로 분류하는 추론이며 opcode28의 operand라고 기록하지 않는다.

| 명령 CPU/ROM | control | X raw BYTE | Y raw BYTE | BE32 identifier operand |
| --- | --- | --- | --- | --- |
| 48980 | 42 | e2 | 00 | 00070000 |
| 48988 | 40 | ea | 00 | 0006d800 |
| 48990 | 42 | f1 | 00 | 0006e000 |
| 48998 | 40 | fa | 00 | 0006d000 |
| 489a0 | 40 | 04 | 00 | 0006f000 |
| 489a8 | 42 | 0c | 00 | 00071000 |
| 489b0 | 40 | 15 | 00 | 0006d000 |
| 489b8 | 42 | 1d | 00 | 0006f800 |
| 489c0 | opcode28 | — | — | operand 없음 |

Caller47ed0은 이 setup에서 object+20=00ea를 명시한다. 따라서 이후 draw까지 그 WORD가 유지되는 조건에서 operand|00ea가 된다. 이는 해당 setup의 지역적 근거이며 다른 caller나 이후 object 변경까지 EA가 고정된다는 주장은 아니다. 이 문서에서는 MS5C를 생성하지 않는다.

## Script489c2: 아홉 draw, wait1, jumpback

실제 명령 범위는 **[489c2,48a12)80바이트**다. 아홉 draw72바이트 뒤48a0a의 `0001`(opcode00/duration1),48a0c의 `0800000489c2`가 온다. 기존 opcode08 형식은 opcode 뒤 한 BYTE를 건너뛰고 BE32 target489c2를 읽는다.48a0d=00은 jump 명령 내부의 skipped BYTE이며 script 바깥 padding과 구분한다. jump가 exact start를 가리키므로 이 정적 stream은 반복 구조이며 뒤48a12 raw lookup은 명령에 포함되지 않는다.

| 명령 CPU/ROM | control | X raw BYTE | Y raw BYTE | BE32 identifier operand |
| --- | --- | --- | --- | --- |
| 489c2 | 42 | e1 | 18 | 0006c800 |
| 489ca | 42 | e9 | 18 | 0006f000 |
| 489d2 | 42 | f1 | 18 | 0006e800 |
| 489da | 42 | f9 | 18 | 00070000 |
| 489e2 | 40 | 00 | 18 | 0006d800 |
| 489ea | 40 | 06 | 18 | 0006e800 |
| 489f2 | 40 | 0e | 18 | 00070800 |
| 489fa | 40 | 16 | 18 | 0006d000 |
| 48a02 | 40 | 1e | 18 | 00071800 |
| 48a0a | opcode00 | duration1 | — | — |
| 48a0c | opcode08 | skipped00 | — | target000489c2 |

47d0a 부근의 setup은 object+20을 설정하지 않는다. 원본4a126은 **live WORD(object+20)를 D7.low에 OR**하므로 위 operand를 완성된 composition ID로 단정하거나 EA/CA 같은 group을 임의로 선택하면 안 된다. 이전 object 초기화·다른 callback의 쓰기·실제 native fixture의 object+20이 추가 확인 대상이다. 기존 `decode_animation_draw`의 변환 규칙은 이 OR를 지원하지만 해당 상태의 group/palette/자연 도달성을 확정하지 않는다.

## 기존 loader와 다음 연결의 경계

`engine/src/animation_resource.cpp`의 `load_animation_resource`는32바이트 little-endian header `<4s7I>`의 MS5A v1 kind1을 읽는다. fixed CPU=ROM offset<100000, nonempty payload, fixed영역 안의 완전한 크기, reserved0, CRC32와 trailing-byte 부재를 확인한다. 짝수 payload 길이를 요구하지 않으므로48980의65바이트 consumed span을 그대로 포장할 수 있다. loader는 명령 의미를 검증하지 않으며 interpreter가 담당한다. 별도 padding을 보존하려면 metadata에서 consumed span과 container payload span을 구분해야 한다.

`engine/src/fixed_data_resource.cpp`의 `load_fixed_data_resource`는 같은32바이트 header 형태의 MS5D v1 kind1이며 동일 fixed mapping/length/CRC/reserved 검사를 한다.48a12의 full-BYTE-domain raw1024바이트를 기존 형식으로 제공할 수 있다. 여기서는 새 resource를 publish하거나 C++loader 소비를 검증하지 않았다.

기존 `animation_step.cpp`는04/00/08/28의 RAM/carry subset을 처리하지만 전체49fc6의15레지스터·PVC bank 저장/복원·sprite pending을 제공하지 않는다. 자세한 경계는 [전체 register 후속 경계](animation-full-register-boundaries.md)를 따른다. 다른 script의 기존 성공을 이 두 script의 실행 검증으로 대체하지 않는다.

확인한 사실은 바이트/명령경계·caller immediate·index폭·live OR와 loader 요구다. 별도 padding의 용도는 위와 같이 추론으로 표시했다.489c2 composition group과 필요한 실제 MS5C 집합, palette와 natural reachability, 전체49fc6 연결은 미확인이다. 이 미확인을 해결하기 전에 모든 group 조합의 거대한 composition 집합을 추출하지 않는다.
