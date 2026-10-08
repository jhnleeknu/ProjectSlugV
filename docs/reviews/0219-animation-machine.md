# 0219 — 실제 PC/A7와 공유 RAM을 사용하는 animation 실행기

대상은 baseline `e526370` 위 `codex/animation-machine`의 새 실행기·원본 관측·검증기·단위 검사와 Makefile 변경이다. 이전 stack 기반 통합은 progress로 승계했다. 기존 실행기 ABI와 완료 기준은 유지한다.

## 변경과 메인 리뷰

새 `run_animation_machine`은 호출자가 제공한 PC/A7와 RAM 속 return LONG으로 실행한다. Saved A0/A1/bank/list end/low BYTE를 host continuation metadata에 따로 보관하지 않는다. 실제 push/pop과 JSR/RTS가 공유 RAM을 읽고 쓰므로 반환 뒤 남은 stack bytes도 후속40 조회의 입력이 된다. 원본 명령을 범용 CPU decoder로 실행하는 구현이 아니라 의미를 확인한 C++11 블록이다.

메인은 public/internal header, interpreter·sprite·sound·장치 공통부 전체와 두 unit, 원본 관측·검증 소스를 읽었다. MOVEM predecrement 순서와 WORD sign extension, live bank shadow 재읽기, indexed PEA 복귀, sound high/low 대기 재개와 실제 return 주소, PVC 쓰기 후 mask 순서 및 후보 상태 수명을 검토했다. 새 동작 결함은 발견되지 않았다. 검증 작성 중 잘못된 negative fixture 두 개는 unsupported PC와 late publication 실패를 실제로 겨냥하도록 수정되었으며, 최종 검증기는 해당 오류 문구까지 확인한다.

실패하면 RAM/16register/PC/PVC/bank/ports/status/external reads가 보존된다. 대기와 정상 반환은 수행한 효과를 commit한다. 원본 CPU fault의 부분 실행이나 rollback을 모사한다는 뜻은 아니다. 일반 CCR은 상태에 없고, 조건 분기는 확인된 블록 안에서 계산한다. 임의의 중간 PC, IRQ, cycle timing과 미지원 callback에는 동등성을 주장하지 않는다.

## 원본과 C++ 비교

- Canonical program SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 여기서 다루는 원본 코드 CPU 주소는 fixed ROM의 파일 오프셋과 같다. Banked data는 현재 physical bank로 별도 해석한다.
- 기존 기본군8조건과 별도 same-CPU chain2단계를 보존했다. 확장군85조건/121단계는 fresh CPU 두 번씩170회/242단계로 재현했다. 합계94 fixture/131단계이며 실제 이전 C++ 출력으로37회 재개했다.
- 확장군에는 정상·deferred·clipped·full sprite, indexed live PEA, 실제 callback4종, field7종, direct sound와 high→low 대기가 포함된다. Script prefix를 이미 소비한 뒤 바꿔도 재실행하지 않으며 live stack과 callback source 변화는 원본 pop/read에서 소비한다.
- 전체64KiB RAM, 16register/PC, ordered PVC ports, 모델이 계산한 PVC8192BYTE/bank, 실제 외부 읽기 수를 비교했다. Stack 차이 masking, ROM patch, 실행 도중 expected register 주입, host SR 읽기는 없다.
- Native 관측은 fixed ROM과 bank2를 매핑하며 bank ROM read마다 실제 port fold의 bank2 조건을 확인한다. PVC native 메모리는 raw write만 저장하므로 C++ 예상 장치 상태는 별도로 port를 pinned PVC 모델에 적용한다. 이 fixture군에는 PVC read가 없다. 물리 기판 측정·자연 caller 도달성·모든 bank 경로의 증거가 아니다.
- C++은 실제8개 MS5D kind3 파일과 typed loader를 사용한다. PNG/확인용 오디오를 런타임 데이터로 쓰지 않는다. Generated harness는 API 검사 도구이며 사용자용 production CLI가 아니다.

메인이 확장 native 보고서의772개 참조와 C++ 보고서의 정규화된 고유 파일1707개 해시를 모두 확인했다. C++ 보고서의24 input/1697 artifact 항목을 문자열 key로 병합하면1717개이며, 절대·상대 경로 중복10개를 해소하면1707개다.

독립 Sol은 native 대표19조건/37단계의 전체 payload와 trace를 재실행하고 guard3개를 확인했다. 이 중 field7종은 alias 없는 조건이며 callback14/+7a의 overlap과 구분한다. 별도 Sol은 기본8조건+2단계 및 확장85조건/121단계를 독립 재실행하고 실제 C++ harness·37재개·9오류도 전부 재확인했다.

Native 감사에서 재실행 실패 뒤 이전 성공 보고서가 남을 수 있음을 발견했다. `main()` 첫 줄에서 기존 보고서를 삭제하도록 수정했으며, 임시 출력 폴더에 성공 보고서를 둔 뒤 source 검증 실패를 강제한 시험에서 삭제를 확인했다. CPU 실행이나 fixture를 바꾸지 않은 재현성 보강이다. 이후 native 전체·C++ 전체를 재실행하고 아래 최종 해시와 모든 참조를 다시 확인했다.

## 검증 결과와 재현

```
.venv/bin/python tools/observe_animation_machine_extended.py
.venv/bin/python tools/verify_animation_machine.py
make all test
```

최종 verifier는 원본 전체를 다시 실행하고 실제 C++ 결과를 비교했다. Checked API 실패9조건의 모든 출력 보존도 통과했다. 두 새 unit의 normal/UBSan 실행이 통과했고, 메인의 `make all test`는 Python257/C++ test 실행150개, 경고0, exit0이다.

장치 unit은 pinned PVC 공식과 독립적인 channel bit 배치로65,536개 pen unpack/pack 왕복, bank 쓰기 순서162조건, BYTE merge·mask·홀수 bank base·최종 PVC WORD/BYTE, LONG의 두 WORD 포트 순서, live bank read, 외부 읽기 counter를 확인했다. 이는 하드웨어 실측과 구분한다.

| 산출물 | SHA256 |
| --- | --- |
| 확장 native source | `336d4637f95cea6bcbf75d98627953ee51f2a52da4a641ea3db943f3433d2d36` |
| 확장 native report | `5ca26b65cb413860fab9fb5b488023665f2a5ec7dd27a729d6e71734c7262029` |
| C++ verifier source | `3b63ef82f54a4e3a308e1c501140256e17145bddd06ffb97fe14fcbbeaa70c9b` |
| C++ verification report | `5462fac8893d9c614888e52476eaffdfaa2afbcd785b2591266bd87b519cb0e2` |

## 남은 범위

일반 CCR과 caller가 사용하는 반환 carry, 자연 상위 활성화/scheduler/IRQ 연결, stack/script/queue/shadow alias의 더 넓은 원본 조건, 다른 callback 및 bank 경로는 남아 있다. 이번 좁은 원본 비교를 근거로 애니메이션 완료 수를17중17로 올리지 않는다. 기존17중14종과14/3c의 일부 callback 검증 집계를 유지한다. 전체 게임 복원율의 분모는 미확정이며 전체 Goal은 active다.
