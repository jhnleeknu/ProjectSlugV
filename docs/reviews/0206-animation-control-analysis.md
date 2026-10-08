# Animation 0c/14 원본 계약·리소스 리뷰

Baseline `c8595e0`, branch `codex/animation-control-analysis`. 이전 목표 턴은 새 C++ 구현과 검증을 커밋한 실제 진전이었다. 이 단위에서는 메인이 원본 의미·구현 계약을 맡고 Sol6.1/medium 세 작업자가 native observer, 리소스 범위/패커, 중첩 continuation 조사/독립 감사를 맡았다. 전체 목표와 기존 완료 기준은 유지한다.

## 확정한 의미

원본 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 고정 CPU 주소=ROM 파일 오프셋이다. 메인이0c의4a3b8..3da,14의4a408..468,1d/1e callback2b3e8..2b40a 원본 명령을 읽었다.0c는 WORD×2 wrap 뒤 signed index로 조회하고, 그 결과 signed field BYTE를 검사한다. SNE.B는 상위24bit를 보존한다. 분기 target은 조건과 무관하게 먼저 읽고4a276에서 포인터를 저장한다.

14는 callback table→operand LONG 읽기→외부 A0/A1/bank 저장→실제 callback→bank/PVC→MOVEM.W 부호확장→A1/A0 복원→pointer 저장을 유지해야 한다.1d/1e의 index BYTE와 source LONG은 live다.1f의 sound 내부 saved A0는 외부 interpreter saved A0와 다르며, 현재 sprite 대기 상태 하나로 대신할 수 없다.1f의 중첩 stack 배치는 정적 합성 추론이고 전체 native pending 증거는 아직 없다.

## 실제 검증

- `tools/observe_animation_control_commands.py`가 수정 없는49fc6에서 합성 RAM script178조건을 실행했다.0c128조건은8selector/desired4/live4 조합,14의1d/1e50조건은5index와RAM/fixed/세overlap이다. 모든65,536selector의 동적 검증은 아니다.
- 전체64KiB RAM/15regs/carry/A7와 reads/writes/trace를 보존했다. PVC912회, RAM쓰기1040회, stack쓰기300회, carrytrue80/false98이다.50callback 모두 실제MOVEM.W와A0/A1 복원을 검사했다.10overlap조건은 setup이 index를 바꿨으므로 최종 live index로 source를 검증했다.
- 메인이178조건을 별도 메모리 실행으로 다시 비교했다. 독립 Sol은 대표19조건을 재실행하고 입력6/산출물712개 해시, 전체RAM쓰기/PVC replay를 감사했다. 정상관측7분기 중1개만 양쪽이므로 전체분기 coverage로 확대하지 않는다. out-of-RAM fixture2개는 미실행 제외이며 성공조건에 넣지 않았다.
- Native report SHA256 `0590de05828d8639340843f06a33417aa32e0370196512bf5a4d17e97165a885`.
- 새 packer는 MS5D v1kind1 두 창 `[4276c,5276c)`65536byte, `[6431a,64836)`1308byte를 만든다. 첫 창은0c 전체 산술 domain과14dispatch 및 기존1f lookup을 포함한다. 겹치는 이전 resource를 동시에 공급하지 않는다. 둘째 창은 알려진8operand 각각의 fullBYTEdomain 합집합이다. 논리적 table extent나 자연 사용을 주장하지 않는다.
- 실제 재생성/container 검증과10개 합성 패커 테스트 통과. 메인의 전체 Python discovery225테스트 통과. 제품 C++ 변경은 없으며 새 C++ 명령 소비나 전체 빌드 재실행을 주장하지 않는다.
- Manifest SHA256 `5a525496309a42ef3deba162bdffe47e6df276c8b6d2d6a8a172407ced331191`. 총payload66844/container66908bytes. container SHA는 control `0e110324fa9a7d039c91f3c9a44b11a9ea60e0bbd7a73376166f91983beef0c2`, operand `832681dcfe9f037a2e1fa069c8327b9c1d15a144e5132fbfced8ada668e773b2`다.

재현 명령은 `.venv/bin/python tools/observe_animation_control_commands.py`, `.venv/bin/python tools/pack_animation_control.py`, `.venv/bin/python -m unittest discover -s tools/tests`다. ROM/생성 데이터는 Git 밖에 둔다. 후속은 MS5D 인자를 받는 full-state API 확장과 실제 native 비교이며,14/1f 중첩 sound·10 indexed draw·나머지opcode·상위callback·자연scheduler/IRQ·전체게임 목표도 미완료로 유지한다.
