# F5 frame-head 실행 수용 검증

`tools/verify_animation_machine_frame_head.py`와 전용 `engine/tools/frame_head_acceptance.cpp`는 원본 H 실행을 공용 C++ machine API와 비교한다. 하네스는 길이 접두어가 있는 BE 패킷으로 RAM/PVC/레지스터/큐를 읽고 실제 API 결과를 돌려주는 검증용 배관이다. 별도의 게임 엔진이나 컨트롤러 구현이 아니다.

## 원본과 경계

원본 복호화 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 기존 F5 native observation SHA256은 `4fe4f796879af90df1c1fd4c753485a9bf0a04d2667b14b8c00dbab23879b16b`이며 입력·관찰 파일을 수정하지 않는다. CPU fixed-ROM 주소 `000e4a`, `000e74`, `00c52a`, `0031d6`는 bank 없는 고정 매핑으로 같은 프로그램 파일 오프셋에 대응한다. RAM 주소는 파일 오프셋이 아니다. banked CPU `200000..2fdfff`의 원본 파일 오프셋은 `bank_base + CPU - 200000`이다.

자연/선언 variant의 기록된 pass-end 덤프를 다음 frame의 H 시작으로 사용한다. 원래 N0 뒤 첫 H인 seed 0 frame 1의 `e4a`도 포함한다. PC `e4a/e74`, A6 `100820`, A7 `1feffc`, LONG `1feffc`=`2ac2`를 확인한다. 원본 덤프와 H start SHA를 확인한 뒤 기록된 host writes를 그 before 값과 함께 검증해 적용한다. Unicorn M68000의 새 CPU에서 순서가 있는 external-read 큐와 명시된 wait release를 사용하여 H 전체를 재실행하고 기록된 H end state digest, ordered ports digest, wait 기록을 검증한다.

자연/variant의 실행 경계는 controller 첫 명령 `c52a`이다. 이 명령은 실행하지 않는다. H8 forward는 별도 선언 파생 입력으로 BYTE `108d3c` bit7을 세우고 원본에서 `31d6`에 처음 도달하면 멈춘다. 이를 자연 실행의 결과로 주장하지 않는다. 자연 paired dump 4,975개와 `path-sprite-forward` fixture의 frame 6/7 두 개를 비교한다. 새 D1이나 controller 영역을 추가 구현하지 않는다.

## 비교 계약과 모델

64 KiB RAM, 8,192-byte PVC page, D0..D7/A0..A7, PC, bank base, API status, 모든 ordered ports, wait PC/address/size/before/release value, 소비한 external-read 수와 실제 소비/잔여 큐 내용이 같아야 한다. SR은 읽지 않는다. carry tag는 허용 범위를 검사하지만 native carry 동등성의 증거로 삼지 않는다.

PVC 초기 page는 0으로 선언하고 보존된 ff8/ff9 pair 네 바이트만 설정한다. 역사적 native observer는 PVC word CPU 쓰기를 mapped page에 남기고 ff8/ff9의 하드웨어 부작용을 별도 변수로 추적한다. 최종 page의 pair 네 바이트만 그 추적된 값으로 정규화한 뒤 전체 page를 C++과 비교한다. 나머지 8,188바이트를 무시하거나 비교 마스크로 제거하지 않는다. 이는 원본 관찰 모델의 표현 차이를 명시한 것으로 실제 장치의 전체 동작을 검증했다고 주장하지 않는다.

wait는 `ef2`의 BYTE A5-7fea := BYTE A5-7fe9, `16bd0`의 WORD A5+d34 := D0.W, `3aea`의 WORD 104d74 := ffff, `cda4`의 WORD A5+d34 := D4.W만 허용한다. 최대 64회를 넘거나 다른 wait에 도달하면 실패한다. C++ resume에는 이전 실제 C++ API 결과를 그대로 사용한다.

## 재생성과 실패 조건

```sh
.venv/bin/python tools/verify_animation_machine_frame_head.py --max-seeds 1 --mode all
.venv/bin/python tools/verify_animation_machine_frame_head.py
```

첫 명령은 가족별 sample이며 전체 acceptance가 아니다. 두 번째 명령은 모든 retained pair를 비교하고 natural 4,975 / variants 976 / declared-derived 4,977 cardinality를 강제한다. `.ms5d` 8개는 기존 packer가 원본 ROM으로 재생성한 container와 byte 단위로 같아야 한다. 원본 도구와 imports, 관찰 및 native dump/blob, ROM·manifest, MS5D, 모든 C++ source와 내부·공개 recursive header, compiler/interpreter/oracle 및 실제 하네스 binary를 SHA256으로 실행 전후 고정한다. 관련 입력이 실행 중 바뀌면 실패한다. 빌드·출력 경로 및 기존 출력 파일의 symlink를 먼저 거부하고 checkout 바깥 출력을 허용하지 않는다. optimized Python 실행도 거부하여 dependency audit의 assertions가 비활성화되지 않도록 한다.

결과는 ignored `artifacts/animation_machine_frame_head_execution/verification.json`에 compact row와 pin 목록으로 남긴다. 빌드는 ignored `build/frame_head_acceptance`를 사용한다. 상태를 매번 대용량 파일로 저장하지 않고 persistent harness와 메모리 패킷으로 비교한다. 불완전/오류 패킷, status, count, RAM/PVC/PC/register/bank/ordered port 변조를 수용하지 않는 부정 테스트와 불완전 결과를 읽는 독립 Python 프로세스의 nonzero exit를 확인한다.

기존 54,264 natural H 관찰 모두가 full dump를 보존한 것은 아니다. 이번 비교는 보존된 paired start의 최소 표본에만 해당하며 전체 자연 실행 54,264개의 새 C++ differential로 확대해 부르지 않는다. 화면 pixels/오디오 장치 및 controller 이후의 동작은 이 수용 단위의 검증 결과에 포함되지 않는다.

## 검증 기록

초기 natural smoke는 seed 0의 H 399개를 비교하여 399개 일치했다. `e4a` 1개와 `e74` 398개, 경계 `c52a` 399개, `16bd0` wait release 85개를 확인했다. 확장 smoke는 1,080개 전부 일치했다. 전체 retained-pair 실행은 10,928개 전부 일치했다: 자연 4,975 + variant 976 + 별도 declared-derived 4,977. 자연 입력의 첫 `e4a`는 136개, 나머지 `e74`는 4,839개다. 전체 비교에서 `e4a` 320개 / `e74` 10,608개, `c52a` 경계 5,951개 / `31d6` 경계 4,977개를 확인했다. archived whole-H 재현은 5,953개, wait release는 `16bd0` 3,720개 / `ef2` 366개다. 15개 부정·잔여 큐·프로세스 exit 검사와 입력 SHA 실행 전후 동일 검사가 통과했다. 별도 출력 경로 검사에서도 symlink ancestor와 checkout 밖 경로를 거부했다. 최종 재실행 시간은 107.9초였으며 결과는 `artifacts/animation_machine_frame_head_execution/verification.json`에 저장했다. 메인 리뷰와 통합은 별도 기록을 따른다.
