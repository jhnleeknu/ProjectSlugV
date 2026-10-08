# Stage counter 4843c 계약

canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 주소는 fixed CPU 주소이며 ROM 파일 오프셋과 같다. 메인이 immutable 원본4843c..4847a 명령을 읽고 두 oracle 및 독립 BCD 기준을 대조했다. 원본 개발자의 변수명이나 의도는 복원했다고 주장하지 않는다.

## 원본 순서

1. BYTE(A5+5683)의 bit4가0이면 즉시RTS이며 모든15레지스터/RAM을 보존한다.
2. BYTE(A5+7db6)==1의 결과를 D0.byte에ff/00으로 쓰고, BYTE(A5+7db7)==1의 결과를 D1.byte에ff/00으로 쓴다. OR.B D0,D1을 수행한다. 결과0이면RTS한다. 이 경로에서도 D0/D1 하위BYTE는 변경되며 상위24bit는 보존된다. 두 status 읽기는 short circuit하지 않는다.
3. D0.byte=BYTE(A5+567f), D1.byte=BYTE(A5+567e), D2=0(MOVEQ 전체32bit)을 순서대로 수행한다.
4. SUBQ.B2 D0은 일반 binary BYTE 뺄셈이다. 결과 low BYTE=(기존BYTE−2) modulo256이며 X는 기존BYTE<2인 경우1이다.
5. SBCD.B D2,D1은 source0과 직전 X를 사용한다. 유효 BCD만 가정하지 않는다. 아래 독립 기준과 일치한 Unicorn에서 원본 실행을 검증한다. incoming SR의 X는 SUBQ가 덮어쓰므로 입력 상태로 필요하지 않다.
6. SBCD carry가1이면 MOVEQ0 D0, MOVEQ0 D1으로 **두 레지스터 전체32bit**를 지운다. carry0이면 D0/D1의 상위24bit는 유지된다.
7. D1.byte를 A5+567e, 다음 D0.byte를 A5+567f에 쓴 뒤RTS한다. RAM 쓰기는 정확히 이 두 BYTE다. D3..D7/A0..A6는 보존된다.

## raw BYTE SBCD 보정과 oracle 불일치 해결

처음 조사한 pinned Musashi는 비BCD nibble을 정상화하는 보정을 적용했다. 원본을 SBCD 직후4846a에서 멈추는 독립 비교에서 Unicorn과 다르다는 것을 발견했고, 그대로 수용하지 않았다. [Flamewing의 BCD verifier](https://github.com/flamewing/68k-bcd-verifier/tree/39a01be528b0744302bf1dc9b3463fc22a3fc45f)는 모든 BCD 입력 조합에 대한 기준과 Genesis Model1/Model3VA2 실기 검증을 보고한다. 이것은 저자의 실기 보고이며 이 프로젝트에서 직접 기판을 측정한 결과는 아니다.

고정 revision의 generator를 별도 artifact 디렉터리에서 빌드한1,050,624byte table SHA256은 `8432868c9aa93c92574bae48bebd4efb2834e298340eb09530625365b80147e5`다. table의 순서는 source,destination,X,Z이며 flags/result BYTE를 저장한다. source0/destination256/X2의512조건에서 원본 Unicorn의 결과BYTE와 C/X는 모두 일치했지만 pinned Musashi는301조건이 달랐다. `tools/check_stage_counter_bcd.py`로 다운로드 hash 확인·독립 generator 빌드·원본 실행 비교를 재현한다. GPL 기준 구현은 LICENSE와 함께 ignored artifacts에 두며 engine에 복사하지 않는다.

이 helper에서 실제 필요한 source0 규칙은 다음과 같다. 이는 decimal 변환이 아니라 실제 raw BYTE 입력의 동작을 나타낸다.

```
X = low_input < 2;
X가0: D1.byte 보존, carry0.
X가1이고 D1.byte가0: raw SBCD는99/carry1, caller가 D0/D1 전체를0으로 지움.
나머지 X1: D1.byte에서 low nibble이0이면7, 아니면1을 뺌, carry0.
```

예: dst=a0/X0은a0/carry0, dst=a0/X1은99/carry0, dst=9f/X0은9f/carry0이다. 이전 Musashi 관측의 비BCD 전체register clamp는 수용하지 않는다. caller는 SBCD carry만 소비한다. API는 최종CCR/cycles를 노출하지 않으며 N/V까지 검증했다고 주장하지 않는다.

## C++ 경계와 검증 계획

`execute_stage_counter(vector<uint8_t>& ram, ObjectRestartState& state, string& error)`를 제공한다. 정확히64KiB RAM과 실제로 도달하는 BYTE 주소만 검사한다. A5는 강제108000으로 바꾸지 않으며 홀수도 BYTE 접근이 유효하면 허용한다. 24bit mirror를 임의 구현하지 않는다. 실패는 RAM/전체15레지스터를 보존한다. 새 runtime 리소스는 필요하지 않은 RAM 연산이다.

원본 전체65536 counter WORD에 대해 실제 Unicorn 실행을 관찰하고, gate bit4와 두 player status 분기·비zero register 상위bit·shifted A5·실제 쓰기 순서를 확인한다. Musashi 결과는 oracle 차이를 설명하는 별도 진단으로 보존한다. 자동 역어셈블이나 수식만을 검증으로 취급하지 않는다. C++ 비교가 확정되기 전에는 관측 완료와 구현 완료를 구분한다. 이 helper만으로47c6c/자연 scheduler/직접 플레이 완료를 선언하지 않는다.
