# ef2 대기와 video counter 연결 리뷰

대상 기준 커밋: `07ddfe3`.

메인이 원본ef2..f0e를 확인하고 unsigned readiness, word shift/subtract, borrow 처리와 저장 순서를 구현했다. 비준비 상태는RAM을 변경하지 않는 성공 경계로 표현하며 비디오 값을 소비하지 않는다. 준비 상태만 기존 입력·컨트롤러로 연결한다. gpt-6.1-sol / medium에는 CLI/배치 실행기와 원본 전수 비교를 분리 위임했다.

원본 대기를 호스트의 무한 busy loop로 옮기지 않고 한 번의 관측으로 표현했다. next_pc=ef2가 이후 scheduler 재개 지점이다. 실제 인터럽트 신호 생산이나 장치시간 경과를 가정하지 않는다. 기다리는 API는 사용하지 않는 오브젝트·스택·리소스를 검사하지 않는다. CLI는 전달된 파일을 로드한다.

모든 byte signal/threshold 조합과 모든16비트 video 값을 원본으로 실행한131,072조건에서 batch 결과가 일치했다. 원본 전체RAM을 각 조건에서 검사하고 video 읽기0/1회를 확인했다. C++의 전체RAM은 별도48조건에서 비교했다. 통합14조건은 기다림·준비·callback·루프·trap·정상 반환을 포함하며,8회 승계의 외부 신호 변경은 명시적인 host fixture다. 늦은 팔레트 오류2조건에서 gate의0018 저장까지 포함하여 출력을 취소했다. 단위 검사에서도 RAM18 rollback과 대기의 리소스 우회를 확인했다.

`make all test`: Python73개 및 C++ 전체 통과. 로그: `artifacts/frame_gate_build_test.log`. CLI batch framing·숫자 경계 검사와 `git diff --check` 통과. 원본 고정ROM/팔레트bank 불변 부분을 확인했다.

보고서 SHA256: `51db2650febb37abb93aa025ab2353588419a624045ad4516322b3d2231ba723`. 메인이 verifier의 hook 범위, 전수 입력 범위, 원본/RAM 비교와 통합 fixture를 리뷰했다.

ec4 앞부분의 디버그 출력, 실제 interrupt/BIOS/sound/task 복구와 시간축, 외부callback, trap handler, 전체 부팅은 미완료다. 전체 목표는 active다.
