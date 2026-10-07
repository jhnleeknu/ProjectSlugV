# 스프라이트 준비 전체 레지스터와 포트 리뷰

Baseline `8437616`. 메인 에이전트가 원본ce82/cf54..cf5a/d6ea..d6fc/11884..1188a, radix166bc..16bb8과 준비16bba..16cf8의 제어 흐름을 검토하고 코어를 구현했다. 프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`; 위 코드 CPU주소는 고정 ROM 파일 오프셋과 같다.

## 구현과 검토

D1 상위word는 마지막 타일 열의 첫 attribute 주소이고, 하위word는 레코드 style에서bit2를 지운 값이다. 클리핑과 슬롯 소진으로 출력하지 않으면 상위word를 유지한다. 수직 반전은 첫 attribute 주소에 `(height-1)*2`를 더한다. D3는 비어 있지 않은 radix에서0이 된 후 emitter의 MOVEM으로 보존된다. 빈 큐의 begin은 둘 다 보존한다. radix 반환 D1은 마지막 역순 임시 배열 소비의 high-key-byte×2로 계산했다.

선택적 포트 출력은 각 레코드의 PVC 선택, VRAM long 쓰기, 마지막 PVC 복구를 원본 순서로 반환한다. disabled pool도 PVC 선택이 있고 빈 큐도 마지막 복구가 있다. 기존 MS5C 로더와 raw VRAM 쌍을 유지한다. 블록 helper, 준비/재개와 동기 wrapper 모두 실패 시 외부 레지스터/출력 보존을 검토했다.

CLI와 단위 검사를 서브에이전트에 위임하고 메인이 diff를 검토했다. 테스트의 identifier2152 뱅크를1000으로 기대한 오류를 발견해3000으로 수정했다(원본AND7+1<<12). CLI 초기 빌드와 최종 파일이 같은 초에 저장되어 오래된 바이너리가 남은 것을 확인한 뒤 최종 CLI를 강제 재빌드했다. 잘못된 기대값에 맞춰 엔진을 변경하지 않았다.

검증 스크립트의 최초 두 리소스가 모두 단일 블록인데 multi-block profile로 표시된 것을 메인이 발견했다. 실제2/3/2블록 리소스2382a/2402a/2482a를 추가하고, 원본 resolve_blocks와 MS5C variant2를 확인하도록 수정했다. 비어 있지 않은 begin은 D3를0으로 만들므로 보존 검증에는 이것만으로 부족하다. 대기 중 비영 D1/D3를 명시적으로 주입한4시퀀스에서 실제 반환을 다시 승계하여 rendering/disabled 재개를 검증했다. 이 변경은 자연 IRQ 관측이 아니라 통제된 fixture로 표시한다.

## 검증 결과

`make -j3 all test`: session74022 exit0, Python73개 및 C++ 전체 검사 통과, 경고 없음. 로그 `artifacts/sprite_prepare_registers_build_test.log`. 다중블록 후반 오류가 앞 블록의 D1 변경을 외부에 유출하지 않는 검사와 cached 열의 D1 보존도 포함한다.

`.venv/bin/python tools/verify_sprite_prepare_registers.py`: session8013 exit0. 1,873경계(begin471/wait924/release470/sync8), 470개 승계시퀀스, 전체64KiBRAM/fullD1/D3 및 순서 있는 포트688,064개 일치(그중VRAM681,860개). 출력 보존 오류42조건 통과. 프로그램과 bank ROM 불변 확인. 메인이 스크립트 전체, 생성 보고서의 집계와 해시를 재확인했다.

추가4개의 실제 sprite→scene좌표 준비 연결은 반환 RAM/D1/D3를1ae56과 CLI에 전달하며 포트16개와 전체 RAM/레지스터가 일치한다. 이 scene 경계의 D0는 별도 fixture이며 sprite가 전체D0를 복원했다는 증거로 사용하지 않는다.

보고서 SHA256 `5fc87b656fd8679312163060e7c58a0557511148f4081f7f0a574296ac77a04b`.

## 남은 범위

사운드3c08의 대기·재개 및 e74→ec4 전체 준비 순서 연결이 다음 단계다. D1/D3 외 scratch registers/CCR, 실제 IRQ/물리 시간, 비직사각형 레코드와 전체 게임 동작 복원은 미완료다. 새 helper의 refresh 옵션은 기존 출력을 유지하지만, 이번 전체 레지스터 원본 비교의 범위는 일반 준비 경로다.
