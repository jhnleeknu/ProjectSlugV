# 0216 — 추출 MS5D를 사용하는 program bus와 animation40 조회 본체

Baseline `bfb1d7e`, branch `codex/animation-program-bus`. 새 C++11 program bus, isolated lookup, CLI, MS5D 추출기와 원본 비교기를 추가한다. 기존 full49fc6 실행기의 명령 지원 수는 바꾸지 않는다.

## 문제와 최종 변경

원본40의 두 LONG은 현재 bank ROM뿐 아니라 RAM mirror·fixed ROM·PVC와 영역 경계를 읽을 수 있다. 기존 fixed reader와 별도 scratchstack 가정으로는 이 의미를 그대로 연결할 수 없다. 새 reader는32비트 논리 주소를 보존하며 각 BYTE/WORD의24비트 bus 주소를 분류한다. 선택한 physical ROM span에서 기존 MS5D bytes를 읽고 명시적인 vector/PVC view와 현재 RAM을 사용한다. LONG은 독립적인 두 WORD다.

`execute_animation_banked_lookup`은 원본 CPU/ROM `4a382..4a3ac`의 selector→field→pointer→value→store를 구현한다. D0/D7의 부분 WORD와 A1/A2의32비트 값을 보존하며 destination 쓰기는 모든 읽기 이후다. 실패 시 RAM/13레지스터를 보존한다. 실제 원본에서도 변경하지 않는 A5/A6/A7을 가짜 register 결과로 만들지 않는다. A6는 불변 입력이며 `4a276`의 D6 갱신·script publication 이전에 끝난다.

## 검토에서 확정·수정한 사항

- **현재 bank의 정렬 제한 제거.** Pinned PVC 식은 ff8 상위 BYTE까지 사용하므로 일반 bank base는 바이트 단위일 수 있다. Animation 완전한 WORD 쌍의256BYTE 정렬을 일반 reader에 강제하지 않는다. 물리 주소는 uint64 범위 검사하고 ROM 크기로 wrap하지 않는다.
- **추출 CPU 창과 현재 CPU 창 분리.** 같은 ROM bytes는 다른 current bank에서도 읽힌다. 예를 들어 physical300004의 기존 리소스를 bank2fff00/CPU200104에서 재사용해야 한다. 새 reader는 physical coverage로 선택한다. 기존 reader의 제한된 동작을 조용히 바꾸지 않는다.
- **규격의 전체 표현 공백 명시.** v1 kind2는 aligned storage bank와2ffff0 상한 때문에 physical bank1..7의 끝16BYTE씩을 담지 못한다. 유효한 shifted bank 읽기에서 이 bytes가 필요할 수 있으므로112BYTE를 불필요하다고 선언하지 않는다. 이번37개 리소스의 실제 읽기 구간에는 해당 bytes가 없고, 전체 표현을 위한 별도 kind/version 확장이 필요하다.
- `docs/resource-format.md`에서 v1 컨테이너 상한2ffff0과 실제 PVC overlay 시작2fe000을 구분하도록 설명을 수정했다. Loader binary 검증 계약은 변경하지 않았다.
- **P3, 검증기 JSON 중복 key, 수정 완료.** 독립 리뷰가 기본 json.loads의 중복 key 덮어쓰기를 지적했다. strict13개 register 출력 계약에 맞게 중복 key를 거절하도록 보강하고 검증기를 재실행했다. 현재 CLI가 중복 key를 출력한 결함은 아니다.

## 검증 근거

- 패커는 canonical ROM SHA `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`와 frozen native95조건을 재검사한다. 336개 ROM read unit의 중복 없는 합170BYTE를 MS5D37개(fixed14/banked23)에 저장했다. RAM363/PVC12 unit은 ROM 추출에서 제외한다. Manifest SHA `366b8f89dc46705fc765ca2b331c69b206b9633fc80f0b7c8fb9fdb3a484cb82`.
- 독립 Sol은 패커를 메모리에서 두 번 재생성하고 기존 파일과 byte 단위로 대조했다. 15합성 검사,390provenance 해시,별도 C++ harness의37정상 loader 및37wrong-kind 거절/보존 검사가 통과했다. 파일 CPU/ROM offset과 payload를 실제 원본과 비교했고 ROM hash/stat은 유지됐다.
- 실제 CLI는37리소스를 함께 load하여 원본 완료73조건의13레지스터·전체64KiB RAM과 일치했다. 원본 관측95조건을 다시 실행하고380payload를 확인했다. 19guard 조건은 CLI 오류/출력 보존으로 검증하고,24비트 mask 범위가 다른 high32bit3조건은 미비교로 명시했다.
- 추가 CLI negative22조건에서 크기·정수·kind·CRC·누락/중복/부분 WORD·input/output alias·FIFO를 검사했다. 별도 CLI 작업자의34호출(성공7/거절27)도 실제 bank3,shifted physical reuse,base0 정수와 파일 보호를 검사했다. 검증/실행 오류의 파일 보존을 OS 쓰기 실패의 원자성 보장으로 확대하지 않는다.
- Core unit은 mixed LONG,16mirror,physical resource 선택,odd physical bank base,device view,32bit wrap/high24 alias,source/destination alias와 늦은 실패 보존을 검사했다. 구현 작업자의 normal·UBSan 빌드/실행이 통과했고 다른 Sol이 원본 opcode 순서와 실제 source를 독립 검토했다. 추가 확정 결함은 없었다.
- 메인의 `make all test` exit0: C++ test 실행146개, Python243개, 경고0. 기존 일곱 full49fc6 verifier를 다시 실행했다고 주장하지 않는다. 기존 구현 파일과 ABI는 변경하지 않았다.
- 최종 verifier source SHA `337b7289a85bcbaf03c4b176ec7ad05700c4c880322471aae261392a773d63eb`, report SHA `c84d8cd8989040831acd12503c40171a5325ad0d1e070ca36de4874cfca701cb`. 입력16개와 native/resource/C++ 산출물779참조,고유793파일 해시를 작업자와 메인이 모두 재확인했다. 이전 report `a2cc2807...`는 parser 보강 전 결과로 대체됐다. CLI binary SHA `4e67bf53faedb04795c479cb7e7841609499f64044f10931cc97c666212e4072`.

## 재현과 제한

```sh
.venv/bin/python tools/pack_animation_banked_reads.py --self-test
.venv/bin/python tools/pack_animation_banked_reads.py
make all test
.venv/bin/python tools/verify_animation_banked_lookup.py
```

CLI의15개 숫자는 bank, A6, D0..D7, A0..A4 순서이며 그 뒤 RAM input/output, vector128/PVC8192(없으면 `-`), MS5D 경로들을 받는다. 숫자는 부호 없는 base0이며 leading0은 octal이다. Output JSON은 D0..D7/A0..A4의13필드다. 디바이스 버퍼는 생존 기간이 보장된 borrowed input이다.

메인이 설계·주소/장치 의미·실제 diff·결과를 리뷰하고 Sol6.1/medium 세 작업자가 core/unit,추출/검증기,CLI/독립 계약 감사를 분담했다. 이후 서로 다른 파일의 독립 리뷰와 실제 loader 검증을 교차 배정했다. 작업자3개 한도를 지켰으며 별도 작업 없이 숫자를 채우기 위한 외부 작업자는 실행하지 않았다.

**이번 구현 단위 수용.** 패커·CLI·core·unit·verifier의 실제 source를 메인이 읽었고, 각 독립 리뷰와 위 검증 범위 안에서 결과를 수용했다.

이 함수는 전체40 명령 완료가 아니다. 원본 whole49fc6와 C++ continuation을 연결하려면 caller A7와 실제 frame 쓰기를 coherent RAM에 반영해야 한다. Natural script binding,high-address 원본 대조3건,전체 physical ROM 규격,일반 PVC 쓰기/장치/IRQ/timing도 남았다. 기존17명령 중14종과14/3c일부라는 집계 및 전체 Goal을 유지한다.
