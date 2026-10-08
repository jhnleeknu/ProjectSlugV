# Animation 0c/14의 fixed 데이터 읽기 범위

canonical BE ROM SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 주소는 fixed CPU=ROM 파일 오프셋이다. `load_verified_program`으로 원본을 확인한 뒤 `disassemble_range`의 padded decoder를 사용하고, 실제 원시 바이트와 기존 검토 계약을 함께 대조했다. 자동 decode만으로 code/data 판정이나 분석 완료를 선언하지 않는다. 원본을 변경하거나 resource를 새로 추출하지 않았으며 빌드/native 실행도 하지 않았다.

## 사실: opcode0c의 WORD selector와 signed wrap

Dispatch entry4a02e의 `60000388`은 handler4a3b8로 분기한다. 실제 명령은 다음과 같다.

| CPU/ROM | 원시 바이트 | 명령/읽기 |
| --- | --- | --- |
| 4a3b8 | 1219 | MOVE.B (A1)+,D1: desired BYTE |
| 4a3ba | 56c1 | SNE.B D1: desired zero/nonzero 정규화 |
| 4a3bc | 3019 | MOVE.W (A1)+,D0: selector는 전체 WORD |
| 4a3be | d040 | ADD.W D0,D0:16bit 두 배/wrap |
| 4a3c0 | 45f90004a76c | A2=4a76c |
| 4a3c6 | 30320000 | MOVE.W (A2,D0.W),D0: signed WORD index |
| 4a3ca | 2e19 | MOVE.L (A1)+,D7: branch target |
| 4a3cc | 4a360000 | TST.B (A6,D0.W): 조회 WORD를 다시 signed field offset으로 사용 |
| 4a3d0 / 4a3d2 | 56c0 / b001 | actual zero/nonzero 정규화와 desired 비교 |
| 4a3d4 / 4a3d8 | 6600fea0 / 2247 | 불일치는4a276, 일치하면 A1=D7 |

주소 계산은 `4a76c + sign16((selector*2)&ffff)`다. selector0..ffff의65536개 입력은32768개의 서로 다른 짝수 offset−8000..7ffe를 만들며 selector와 selector+8000(mod65536)은 같은 WORD를 읽는다. 완전한 WORD 읽기까지 포함한 **full-WORD-domain raw span은 [4276c,5276c)65536바이트**다. 처음·마지막 WORD 시작은4276c/5276a다.

| selector | doubled WORD | signed offset | WORD 읽기 CPU/ROM |
| --- | --- | --- | --- |
| 0000 | 0000 | 0 | 4a76c |
| 3fff | 7ffe | +32766 | 5276a |
| 4000 | 8000 | −32768 | 4276c |
| 7fff | fffe | −2 | 4a76a |
| 8000 | 0000 | 0 | 4a76c |
| c000 | 8000 | −32768 | 4276c |
| ffff | fffe | −2 | 4a76a |

조회한 WORD의 signed 해석은 이후 A6-relative BYTE 접근에도 적용된다. 따라서 raw 읽기 창을 보존하는 것과 모든 selector를 유효 object field로 인정하는 것은 다르다. 실제 object BYTE span은 별도로 checked 검사가 필요하다. full-domain span SHA256은 `00fd4b3f850678709eb4da84d61addd145491b9a6f0afc5637b8bd273ad32bd4`다. 이 범위 전체가 하나의 논리적 selector table이거나 모든 값이 자연 실행된다는 뜻은 아니다.

## 사실: opcode14의 BYTE callback selector

Dispatch entry4a036의 `600003d0`은4a408로 분기한다.0c의 WORD selector와 다르게 이 handler는 명시적으로 D0전체를0으로 만든 뒤 BYTE를 읽는다.

| CPU/ROM | 원시 바이트 | 명령/읽기 |
| --- | --- | --- |
| 4a408 | 2f08 | 원래 A0 LONG 저장 |
| 4a40a | 7000 | MOVEQ0 D0 |
| 4a40c | 1019 | MOVE.B (A1)+,D0 |
| 4a40e / 4a410 | d040 / d040 | ADD.W 두 번: BYTE×4 |
| 4a412 | 41f90004a500 | A0=4a500 |
| 4a418 | 2e300000 | MOVE.L (A0,D0.W),D7 |
| 4a41c | 2059 | MOVEA.L (A1)+,A0: command operand |
| 4a41e / 4a420 | 2f09 / 2247 | A1 저장, A1=D7 |
| 4a422..4a434 | 3f2d8010 / 3b7c00008010 / 33fc1000002ffff2 / 33fc0000002ffff0 | bank WORD 저장, shadow0과 PVC 두 WORD |
| 4a43c | 4e91 | 실제 JSR(A1) callback |

selector0..ff는 offset0..3fc가 되며 signedWORD 경계를 넘지 않는다. LONG 전체를 포함한 **full-BYTE-domain callback-dispatch raw span은 [4a500,4a900)1024바이트**다. SHA256은 `23f366a3513fd3941d44fac6b59ed6d713c84ae8c0bab40f6f126191e025c031`다.

이 범위를256개의 유효 함수 포인터 목록으로 단정하지 않는다. 실제1d 항목4a574는 `0002b3e8`,1e 항목4a578는 `0002b3fa`다. 반면ff 항목4a8fc의 원시 LONG은 `49542020`이다. raw bytes의 보존은 임의 callback의 의미/실행 지원을 뜻하지 않는다. checked callback 지원 목록은 원본 함수별 분석 뒤 정해야 하며 no-op으로 대체하지 않는다.

Callback 복귀는 bank shadow/PVC,4a460의 MOVEM.W D0/D7 signed16→32 복원, A1/A0 LONG 복원과4a276의 다음 pointer 저장을 포함한다. 기존1d/1e의 RAM 복사 의미만 재사용하여 이 전체 frame을 생략하면 full-register 계약과 달라진다. 세부 근거는 [전체 register 경계](animation-full-register-boundaries.md)에 있다. 별도 opcode3c의4a30c도4a500을 쓰지만 WORD selector를 두 번 ADD.W하므로14의 BYTE-domain으로 일반화하지 않는다.3c의 full 지원 범위는 이번 inventory에서 확정하지 않는다.

## 사실: 기존 resource와 지원 범위

| 기존 경로 | 확인한 실제 범위/역할 | 이번 full-domain과의 차이 |
| --- | --- | --- |
| tools/pack_animation_data.py → data_04a76c.ms5d | [4a76c,4a88e)290바이트/145WORD.4a88e는 별도 참조된 code entry라는 기존 경계 근거 | full0c signed-wrap span을 제공하지 않음 |
| 같은 packer → data_06431a.ms5d | [6431a,6471a)1024바이트, callback1e의 operand-base6431a에 대한 full BYTE-index LONG 창 | callback dispatch4a500 창이 아니며 다른 operand base까지 모두 덮지 않음 |
| tools/pack_animation_branch.py → branch_data_06431a.ms5d | [6431a,6447a)352바이트. 아래 목록의5/17항목별 bounded operand data | callback BYTE0..255의 일반적 상한을 제약하는 근거가 아님 |
| 같은 packer → animation_065f56.ms5a | [65f56,662c2)876바이트/34개 상위 명령과 list 내부04 | 알려진0c/14 script의 source-backed 재사용 가능 |
| engine/src/animation_step.cpp | RAM/carry with_data API의0c 및14/1d·1e 지원 | full15R/bank/PVC/pending 구현이 아님; 기타14 selector 미지원 |
| engine/src/animation_execution.cpp | 새 full-state API의00/04/08/28만 지원 | 현재0c/14는 명시적 미지원이며 MS5D 인자를 아직 받지 않음 |

145WORD 후보 범위의 payload SHA256은 `d96597f75f1630974f720a314c8ceb188e461ebe98c2780e18f8076b44d304cf`다.0c에서 WORDselector31은4a7aa의 `007e`를 읽는다. 기존 분석은 검토된145개 field WORD와 별도의 합성 fixture에 대한 증거이며 full65536selector 실행 검증이 아니다.

14/1d·1e 함수2b3e8/2b3fa는 각각 object+7c/+7d BYTE를 MOVEQ0으로 받은 뒤 WORD를 두 번 ADD.W하여 operand A0+BYTE×4의 LONG을 object+78에 쓴다. 이는 dispatch selector와 별개인 **callback 내부 BYTE-domain**이다. operand base6431a 하나에는1024바이트가 필요하다. 아래 마지막 base64436까지 각 base에fullBYTEdomain을 제공한다면 합집합은 [6431a,64836)1308바이트다. 이것은 알려진8operand에 대한 raw 읽기 합집합 계산이며 실제 game index 집합이나 하나의 논리 table extent가 아니다. 현재352바이트 bounded resource 또는6431a기준1024바이트만으로 이 일반적 합집합 전체가 제공된다고 주장하지 않는다.

## 사실: 기존 known inventory에서 확인한 fixed script

`pack_animation_branch.extract`를 **메모리에서만** 재실행해 checked caller/group bytes와 기존34명령 형식을 확인했다. caller2bb06의 `227c00065f56303c01004eb900049f8c`가 A1=65f56과 initializer 연결을 제공한다. 아래는 그 기존 inventory의0c/14 명령만이다. unconstrained opcode-byte 검색으로 새 script를 선언하지 않았다.

| 0c 주소 / raw8byte | 14 주소 / raw6byte | 14 selector / operand base |
| --- | --- | --- |
| 65f56 / 0c00001f0006604c | 65f5e / 141e0006431a | 1e / 6431a |
| 65f92 / 0c00001f0006604c | 65f9a / 141e0006432e | 1e / 6432e |
| 65fce / 0c00001f0006604c | 65fd6 / 141e00064342 | 1e / 64342 |
| 6600a / 0c00001f0006604c | 66012 / 141e00064356 | 1e / 64356 |
| 6604c / 0cff001f00065f56 | 66054 / 141d0006436a | 1d / 6436a |
| 660e8 / 0cff001f00065f56 | 660f0 / 141d000643ae | 1d / 643ae |
| 66184 / 0cff001f00065f56 | 6618c / 141d000643f2 | 1d / 643f2 |
| 66220 / 0cff001f00065f56 | 66228 / 141d00064436 | 1d / 64436 |

여덟0c의 selector는 모두001f이고 desired는00/ff이며, 기존 두 loop를 서로 연결한다.14 뒤에는 알려진 opcode10 indexed draw가 있으므로0c/14만의 구현을 이 script 전체 지원으로 선언하지 않는다. 기존6f1e2와48980/489c2 inventory에는0c/14가 없다. 다른 fixed script와 자연 도달성은 이 기존 inventory만으로 확인하지 않았다.

## 추론: resource 확장 선택지

기존 MS5D v1 kind1과 `load_fixed_data_resource`는 fixed CPU=ROM<100000, nonempty complete payload, CRC/length/reserved0을 검사한다.65536/1024/1308바이트는 기존 형식에 들어가므로 새 형식은 필요하지 않다. loader의 byte 검증과 callback 의미 구현은 별개다.

full0c의[4276c,5276c)는14dispatch[4a500,4a900)와 기존field window 전체를 포함한다. 현재 RAM/carry `animation_step.cpp::validate_regions`는 **실행 전 모든 window 간 overlap을 거부**한다. 따라서 full span을 추가하면서 옛290바이트나 별도1024 callback window를 동시에 전달하는 단순 추가는 실패한다. 선택지는 한 wide raw window를 여러 role의 metadata로 공유하거나, 겹치지 않는 window 분할로 교체하는 것이다. WORD/LONG이 두 window에 걸치지 않는 분할과 향후 full-state reader의 unique/complete 정책을 함께 검토해야 한다.

알려진 selector31과1d/1e만으로 첫 full-state 연결을 제한한다면 기존field resource를 재사용하고 실제 도달하는 callback dispatch와 operand data를 명시적으로 공급하는 작은 범위안도 가능하다. 다만 이는 제한된 계약이며 full selector domain 지원으로 표시하면 안 된다. 어느 안을 채택할지는 메인의 API/의미 계약 결정에 남긴다.

## 미확인

raw window의 산술 범위는 확정했으나 selector 전체의 자연 사용, 논리 table 경계,1d/1e 외 callback 의미, callback의 banked/data 의존·pending 필요성, 전체 register/PVC 저장복귀와 opcode10까지 포함한 script 전체의 새 API 연결은 미확인이다. 원본에 값이 있다는 이유만으로 실행 가능한 callback으로 인정하지 않는다. 전체17opcode 복원과 자연 scheduler/gameplay는 계속 GOAL에 포함된다.
