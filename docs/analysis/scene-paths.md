# Scene path 원본 구문 후보 목록

## Source와 범위

Canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 이 문서의 interpreter·path 주소는 첫 1MiB 고정 ROM CPU 주소이며 파일 offset과 같다. 아래 주소·opcode·상수는 16진수, 건수는 10진수다. RAM pointer와 banked data는 고정 ROM offset으로 바꾸어 해석하지 않는다.

`tools/inventory_scene_paths.py`는 source SHA를 검증하고 현행 scene script manifest의 원본 payload SHA와 span을 대조한다. 모든 opcode24의 selector WORD/pointer LONG과 원시 operand를 수집하여 nonzero pointer를 root로 삼는다. 기존 MS5D 추출 규격이나 파일을 변경하지 않는다. 출력은 19e64 interpreter의 메인 확정 구문 계약에 따른 **CFG 후보 목록**이며 실제 실행·분기 가능성·frame scheduler·후속 tile/frame 갱신 완료를 주장하지 않는다.

## 구문 walk

각 cursor에서 BE16 opcode를 읽는다. 음수 word는 2bytes terminal이다. Nonterminal은 00..1c 중 4의 배수만 허용하며 operand bytes는 다음과 같다.

| Opcode | Operand bytes | 후보 successor |
| --- | --- | --- |
| 00/1c | 4 | Sequential |
| 04 | 12 | Sequential |
| 08/0c/10/14 | 12 | Sequential와 branch pointer 양쪽 |
| 18 | 6 | Sequential |

08/0c/10/14의 12bytes는 condition offset WORD, flags WORD, +4 WORD, +6 WORD, +8 branch pointer LONG으로 보존한다. 조건의 참/거짓을 추론하지 않고 두 edge를 모두 따른다. 각 root에서 visited cursor와 현재 DFS 경로를 구분하여 cycle edge를 기록하고 재방문을 종료한다. 첫 1MiB의 정렬·완전 operand bounds, 명령 byte overlap, bounded graph/scan guard를 검사하며 이상값은 raw bytes와 unsupported error로 남긴다. Root별 reachable row/edge/terminal 및 opcode04 descriptor 주소를 보존한다.

## Canonical 결과

재생성 exit0으로 opcode24 72회에서 nonzero unique root 72개를 수집했다. Root마다 3개 또는 4개 row가 있으며 전체 unique row는 218개다.

| Opcode | Unique row count |
| --- | --- |
| 00 | 72 |
| 04 | 72 |
| 18 | 2 |
| ffff terminal | 72 |

Unknown opcode, bounds, overlap 오류와 cycle edge는 모두 0이다. Canonical에서 조건 opcode08/0c/10/14가 없으므로 이 자료가 조건 branch의 실제 실행이나 양쪽 edge의 도달성을 검증한 것은 아니다. Script reference별 selector와 command 주소, root별 후보 row 및 raw operand를 JSON에 기록한다.

## Opcode04 descriptor의 원시 필드

72개 descriptor의 12bytes를 아래 field로 보존한다. Descriptor 주소는 opcode 주소+2이며 width/height는 WORD다.

| Operand offset | Field |
| --- | --- |
| +0 WORD | map_selector_word |
| +2 WORD | secondary_selector_word, 원시 word_at_2도 함께 보존 |
| +4 WORD | width_word |
| +6 WORD | height_word |
| +8 LONG | column_pointer_long |

Primary selector는 69개 값이 있고 secondary selector가 nonzero인 descriptor는 40개다. Column pointer는 72개 모두 0이다. Selector/secondary/width/height/column pointer 조합별 분포와 해당 source 주소를 보고서에 보존한다.

메인이 원본 183c6..1844e에서 확인한 primary 참조는 bank3(물리 ROM300000→CPU200000), CPU200004의 root→200008, selector의 LSL.W2 결과를 signed offset으로 사용한 lookup이다. 선택한 record의 +4 이후에는 셀당 4bytes source와 height×4 column stride가 있다. Secondary 참조는 1854a에서 +2 word가 0이면 생략하며, nonzero이면 bank2 CPU200010 root에 같은 word shift/signed offset lookup을 한다. 값 ffffffff이면 node+80 buffer를 지우고 그 외에는 column offset을 통해 long을 복사한다. 이 두 참조가 있다는 원본 근거만 기록하며 secondary를 collision 데이터라고 명명하지 않는다. 해당 banked table/data 추출 범위와 runtime resource 계약은 아직 결정하지 않았다.

## 명시 disassembly 창과 재현

`disassemble_range`로 아래 창 전체를 보존한다. 첫 RTS에서 자동 중단하지 않으며 불완전 명령은 helper의 dc.w 구분을 유지한다. 자동 decode는 callee 전체 분석 완료가 아니다.

| Start | End exclusive |
| --- | --- |
| 19e64 | 1a07a |
| 16ff8 | 17012 |
| 1861a | 1879c |
| 16f0e | 16f9a |
| 183c6 | 185fa |

마지막 창은 메인이 확인한 185f4 ANDI.B와 185f8 RTS까지 포함한다.

```text
.venv/bin/python tools/inventory_scene_paths.py
.venv/bin/python -m unittest discover -s tools/tests -p test_scene_paths.py
```

- `artifacts/scene_paths/inventory.json` SHA256: `0bb2ed9b1c73335e983b72290187eed473e1229f0b3db47df5402d81ebc91a07`
- `artifacts/scene_paths/disassembly.json` SHA256: `1ef0f7ebf676047ce8c3f4b57189eef6e1b401be881bf1a71e3597cf4a7294ce`

원본 ROM과 추출 데이터는 Git에 추가하지 않는다. 이 단계는 구문·참조 inventory이며 C++ interpreter equivalence, descriptor 실행 완료, 자연 scene path 실행을 주장하지 않는다.

합성 bytearray 구문 unit 7개가 exit0으로 통과했다. 조건 4종의 두 edge, cycle 재방문 종료, operand 내부 branch overlap, 각 payload 길이/descriptor 필드, 잘린 opcode·operand와 고정 ROM 끝, odd/outside/unknown opcode, 1500개 sequential 명령+terminal을 검사한다. Walk는 iterative DFS여서 긴 경로가 Python recursion 한도에 의존하지 않는다. 이 테스트는 원본 ROM을 patch하여 실행한 검증이 아니다.


## 원본 dispatch 경계 검증

`tools/verify_scene_path_dispatch.py`는 원본19e7e에서 시작해각canonical handler 진입직전까지만실행한다. 음수terminal은19e84 RTS를거쳐sentinel까지실행한다. 고유218주소×D7high3=654조건이통과했다. Nonnegative146주소438조건,terminal72주소216조건이며실제handler진입은00/04/18만관찰했다. 다른5개handler목적지는8entry BRA원시바이트의상대주소를대조한정적근거다.

D7상위word보존/opcodeword,A2=cursor+2와D/Aregister,전체RAM,stack불변을확인했다. 양수dispatch의A7은초기값,terminal은+4다. 메모리쓰기0/ROM불변이며handler본문효과나C++동등성은검증하지않았다. Root/각후보successor와원시명령byte closure도독립적으로재계산해목록과대조했다.

```text
.venv/bin/python tools/verify_scene_path_dispatch.py
```

보고서 `artifacts/scene_paths/dispatch_verification.json` SHA256 `f50925f4e467cf4fda90309e3cf2cab58bf9ba07cb746fdc273fea5795204e11`. 전체Python단위검사146개가통과했고로그는 `artifacts/scene_paths/python_tests.log`다.
