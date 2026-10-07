# ef2 갱신 대기와 비디오 카운터 취득

원본 프로그램 SHA256: `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`.
명령 주소는 고정 ROM CPU 주소와 복호화 프로그램 오프셋이 같다. RAM 오프셋은100000 기준이다.

원본ef2는RAM0016을0017과 unsigned byte로 비교한다. 작으면ef2로 돌아가며, 같거나 크면efc에서3c0006을word로 읽는다. 읽은word를7비트 오른쪽으로 이동하고 word256을 뺀다. borrow가 있으면0으로 바꾸고, 최종 하위byte를0018에 저장한 뒤f12로 진행한다. 따라서 video7fff/8000/807f는0,8080은1,ffff는255가 된다.0017이0이면0016이0이어도 준비 상태다.

`poll_frame_gate`는 이 대기 루프를 한 번 관찰한다. 준비되지 않았다면 ready=false이고 RAM이 그대로다. 준비되면 호스트가 공급한3c0006 읽기 값을 소비하고0018만 갱신한다. 대기하면서 호스트 스레드를 바쁘게 돌리거나 인터럽트 신호를 임의로 증가시키지 않는다. 이후 실제 장치 계층이 신호·읽기 값을 공급해야 한다. 성공 시 ready는 비디오word 읽기 유무와도 대응한다.

`poll_input_control`은 이 경계를 기존f12 입력·컨트롤러에 연결한다. 대기이면 next_pc=ef2,read_count=0,style=initial_style,callback/context=0,포트 쓰기 없음으로 성공 반환한다. 해당 경로는 object/stack/리소스를 사용하지 않는다. 준비되면 video0018 갱신 후 기존 입력 경로를 실행하며, 후속 지원 오류가 나면0018 변경까지 취소한다. API 전체는 RAM/result/포트 출력 실패 보존 계약을 따른다.

이 API의 진입점은ef2다. 앞선ec4의 선택적 디버그 문자열 출력은 실행하지 않는다. c8c 인터럽트 전체·BIOS·사운드·작업 복구나 실제 대기 시간이 구현된 것은 아니다. video 읽기를 shadow4d90/91 또는 호스트 시간에서 추측하지 않는다.

빌드: `make build/poll_frame_gate build/step_input_control`.
독립 CLI: `build/poll_frame_gate INPUT_RAM OUTPUT_RAM VIDEO`.
통합 CLI: 기존 `step_input_control` 인수 앞에 `--poll VIDEO`를 붙인다.
진단 batch: `poll_frame_gate --batch`는 stdin의5바이트(signal8,threshold8,old0018,videoBE16)를 ready8/value0018의2바이트로 변환한다. 이는 테스트용 스트림이며 게임 리소스 포맷이 아니다.
검증: `.venv/bin/python tools/verify_frame_gate.py`.

## 검증 결과

원본ef2의 모든 signal/threshold 조합65,536개와 모든video word65,536개를 실행했다. 준비98,432건·대기32,640건으로 총131,072건이며, 원본의 전체 RAM과 조건부 비디오 읽기0/1회를 검사했다. C++ batch의ready/0018 결과가 모두 일치했고, 별도48조건은 C++ 전체64KiB RAM도 비교했다.

통합14조건은ef2 대기,f3c callback,ec4 루프,fee trap과 정상 반환을 포함한다. 그중8회 승계에서는 호스트가 명시적으로0016 신호만 변경하고 이전 결과를 이어받았다. 이는 실제 interrupt 생성 구현을 대신한 fixture임을 명시한다. 늦은 팔레트 오류2조건은0018 저장 이후에도 기존 출력 생성/수정을 막는다.

보고서: `artifacts/frame_gate/verification.json`.
SHA256: `51db2650febb37abb93aa025ab2353588419a624045ad4516322b3d2231ba723`.

## 실제 서비스가 만든 신호와의 후속 연결

후속 `tools/verify_interrupt_frame_flow.py`는 RAM16을 호스트가 덮어쓰던 초기 fixture와 달리 실제 c8c 서비스가 만든 신호를 메인 poll에 전달한다. 573조건의 전체 RAM/포트/읽기 횟수가 일치했다. 별도 스택에서 서비스를 호출한 뒤 메인 CPU 문맥을 복구하는 명시적 스케줄링 조건이며, SR/RTE/BIOS와 자연 IRQ 시간축의 구현은 아니다. 상세 범위와 보고서 해시는 `docs/analysis/interrupt-frame-flow.md`를 따른다.
