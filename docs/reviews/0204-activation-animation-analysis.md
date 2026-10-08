# 활성화 animation 원본 분석 리뷰

Baseline `9f14f98`, branch `codex/animation-full-analysis`. 메인은 원본49fc6/4a10c 제어흐름·기존 API를 읽고 전체register/pending 계약을 작성했다. Sol6.1/medium 세 작업자는 native observer, static resource 범위, API/17opcode 목록을 분담했다. 이후 별도 Sol이 native 보고서를 읽기 전용으로 감사했다.

기존RAM/carry interpreter는일부효과가검증됐지만skip시이미읽은operand와부분register, MOVEM.W복원, PVC순서와pending을표현하지못한다. 기존API를전체register필드만추가해감싸는것으로이간극이해결되지않는다. animation-draw-full-contract.md와animation-execution-initial-contract.md는실제00/04/08/28부터전체상태로연결하고다른13opcode의미완료를유지하는후속계약이다.

## 실제 script 범위

원본caller와명령바이트를대조했다.48980은8draw와opcode28의65byte이며그뒤489c1은별도00byte다. padding이라는용도는추론으로표시했다.489c2는9draw、wait1、jumpback의80byte다.48a12의fullBYTE domain LONG조회창은1024byte이며논리적전체표로단정하지않는다.48980직전caller에는EA설정이있지만489c2의livegroup은확정하지않았다. 메인이도구와문서를읽었다.

## Native 실행 관측

- 실제수정없는49fc6/두fixedscript/defaultcd50을90조건/98단계로실행했다. 원본명령을patch하거나hostcallback으로대체하지않았다.
- source SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. fixed CPU주소=ROM offset이다.
- Native SHA256 `18d25c677ab35698a7662142ce730422c67abcb2df58e7eea8592e141d5e39e6`. 현재입력6개/phase산출물392개해시를메인과독립Sol이확인했다. 초기11f826...보고서는objectpoison보강으로대체됐다.
- RAM쓰기7,384、stack쓰기10,573、orderedPVC WORD3,280회. 실제draw복귀731회에서MOVEM.W부호확장과A0/A1복원을확인했다.
- 90반환의carry true46/false44、대기8단계carry null. 원본SR은RTS후에만읽었고hook중읽거나변경하지않았다.
- 실제관측opcode는00=560、04=5,456、08=512、28=52다. 조건분기27곳중19곳양쪽을관측했다. 가장긴단계29,646명령은500,000cap보다작다. 나머지opcode나분기의검증을주장하지않는다.
- 네sameCPU대기연쇄는SP=STACK-18、return4a200、savedA0=102026/A1=script+8/bank0、drawreturn4a108을확인했다. hold에shadowbeef와object X/Y/flag/group을바꿔도현재draw는캡처된D0/D1/D7으로완료한다. 그이후draw는새live값을읽고clip한다. 현재drawprefix와후속draw진입을구분하는검사를추가했다.
- 독립Sol은26조건/34단계(네연쇄전부포함)를메모리에서재실행하고전체trace/RAM/register/carry/ports/pending과대조했다. 모든98단계의RAM/PVC재생도확인했다.

재현은 `tools/inspect_activation_animation_scripts.py`, `tools/observe_activation_animation_scripts.py`다. 이단위는분석/native준비이며새animation C++빌드나통과보고가아니다. 모든fixture는canonicalA5/A6와기본callback을쓰고savedbank는0이다. duration0、ID sentinel、다른palette분기의추가검증은후속작업이다. 자연scheduler/IRQ·직접플레이·전체17opcode·전체게임은미완료다.
