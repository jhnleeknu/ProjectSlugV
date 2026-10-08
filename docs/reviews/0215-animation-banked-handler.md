# 0215 — Animation40 원본 handler와 RAM mirror 관측

Baseline `e40334b`, branch `codex/animation-banked-read-analysis`. C++ 엔진 변경 없이 새 분석 도구 세 개와 설계·관측 근거를 추가한다. 전체40 구현이나 Goal 완료 기록이 아니다.

## 원본과 검토 범위

Canonical 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. CPU/ROM offset `4a382..4a3ac`의 원본 handler를 수정 없이 실행하고 `4a276` 직전에 멈춘다. 입력 script와 RAM pointer는 명시적인 합성 fixture다. 실제 field table과 bank ROM bytes를 사용하며 기대 레지스터를 실행 중 주입하지 않는다.

메인은 원본 명령 순서, 부분 레지스터 갱신, signed WORD 주소 계산, 실제 ROM offset, RAM mirror, PVC overlay와 scope를 검토했다. 두 LONG 조회 뒤 마지막에만 destination을 쓰므로 operand·pointer·source alias 조건에서도 읽기 순서가 유지된다. 기존 caller/script 조사에서는 신뢰할 자연40 stream을 아직 확보하지 못했으며 미사용이라고 결론내리지 않는다.

## 발견 사항과 수정

- **P1, 공유 RAM backing 수명, 수정 완료.** 초기 `Observer.close()`의 `self.cpu=None`은 Uc hook callback의 순환 참조 때문에 즉시 native 해제를 보장하지 않았다. GC를 비활성화한 독립 실험에서 CPU는 살아 있지만 backing은 이미 해제됐다. 메인은 pointer mapping 전에 `cpu._ram_backing=self.backing`을 추가하고 잘못된 즉시 해제 설명을 수정했다. 실제 수정본에서 둘 다 GC까지 살아 있고 이후 모두 회수됨을 Sol이 재확인했다. 해제된 pointer를 역참조하거나 crash가 발생했다고 주장하지 않는다.
- **관측기 SR 한계 확인.** 합성 `CMP.W` 뒤 host SR은 `2000`, 같은 CPU 실행 안의 `MOVE SR,D2`는 `2009`였다. `MOVEQ/MOVE.L`에서도 Z 차이가 재현됐으며 명시적인 `ORI #1,CCR`은 일치했다. 새 handler의 CCR은 모델 값으로만 기록하고 원본 관측으로 취급하지 않는다. system byte만 비교한다. 기존 carry 관측에 대한 별도 영향 감사는 아래 기록으로 구분한다.
- RAM mirror와 stack은 같은 물리64KiB다. 기존 scratchstack 독립 mapping을 그대로40 근거로 재사용할 수 없다. 기존 trace의 deadstack S-8을 first offset eff0으로 읽을 수 있는 구체적 사례를 설계 문서에 남겼다. 단순 RAM 비교 mask로 의미 차이를 숨기지 않는다.

## 검증

- `.venv/bin/python tools/observe_animation_banked_handler.py`를 메인이 수정 후 실행했다. 95조건을 각각 fresh CPU로 두 번 실행하여73완료·22guard/제외,380payload 생성에 성공했다. 전체64KiB RAM,15레지스터+A7,PC,순서 있는 읽기/쓰기와 쓰기 전 값,16mirror 일치 및 ROM/PVC 불변을 확인한다.
- 22제외는 홀수 주소10, high32bit3, 장치 영역5, ROM 밖 bank2, 비RAM write2다. 하드웨어 예외 실행 증거가 아니다. Guard를 끈8개 대조군은 backend가 홀수 접근을 허용하거나 부분 쓰기를 남기는 한계를 별도 기록한다.
- 메인은 입력5개·산출물380개 해시와 실제 source를 검토했다. 독립 Sol도 최종95조건·380payload·8control·SR probe를 다시 실행하여 모든 결과와 provenance가 일치함을 확인했다. ROM hash/stat 변경이 없으며 자세한 결과는 관측 문서에 기록한다.
- `probe_m68k_bus_alias.py`의27조건은 ROM 없는 합성 검사다. 최종 source로 별도 subprocess27개를 다시 실행해 모두 통과했다. Report SHA `95c90360d8256c5d6d33808740db74848a4a4b258544bb9f4b6858e904a0dba1`.
- 최종 handler source SHA `66a156cd73be2a10cfb91413396a8fa9379f6ee09cea48c17f3d561d3e9daed3`, native report SHA `a6b075d468e015c8fde64129abf6003964bd1f1669ef8c6538545cc0aa3d39a5`. 초기 report `c15a224c...`는 소유권 수정 전 결과이며 최종 근거로 사용하지 않는다.
- 이번 변경은 Python 관측기·문서에 한정한다. C++ 전체 빌드·기존 일곱 verifier를 다시 실행한 것으로 기록하지 않는다. 직전 구현 단위의 검증은 리뷰0214에 있다.

## 협업과 남은 범위

Opus5.5/high 요청으로 원본 observer를 작성했다. 종료 JSON의 actual model은 `claude-opus-5-5`이며 별도 applied effort 필드는 없었다. Sol6.1/medium은 backend probe, script·리소스 조사, 독립 재실행, 수명·SR 영향 감사와 문서화를 분담했다. 메인은 의미 추론·계약·실제 diff 검토·수정·통합을 담당했다. 내부 최대3개, 외부 포함 최대4개로 전체 상한5개를 지켰다.

관측의 PVC 내용과 cart vector view는 선언된 입력이다. 24비트 hardware bus masking, odd address exception, MMIO, arbitrary256-byte PVC bank base, IRQ/timing, whole49fc6·대기재개·자연도달성 및 C++40은 이번 범위가 아니다. 기존 MS5D v1을 이용한 bank 선택 reader와 전체 호출 stack 상태를 다음에 연결한다. 완료 집계는17명령 중14종 및14/3c의일부로 유지한다.

## 기존 final carry 영향 감사

Sol의9개 주요 animation native 보고서 감사에서3085phase 중2813완료와272대기를 구분했다. 완료2811개는 최종 flag writer가 고정 CPU/ROM `4a0e0:e247` (`ASR.W #1,D7`)이고, 나머지 null-object2개는 `49fe6:003c0001` (`ORI #1,CCR`)이다. 이어지는 `RTS`는 CCR을 바꾸지 않는다. 대기는 carry=null로 기록하여 SR을 읽지 않는다. Bank-state92완료도 모두 ASR 경로다.

원본의 두 exit를 그대로 실행한 별도28조건은 caller return을 ROM 밖 `400000`의 합성 `MOVE SR,D2` readout으로 지정했다. 14가지 D7 입력씩 검사했고 original flag writer→original RTS→readout을 같은 emu_start에서 실행했다. Host SR과 CPU readout이 일치하고 ASR carry는 원래 D7 bit0, ORI carry는1이었다. 메인이 독립 재실행해 산출물 SHA `3eeea65a65b440808383f668258532198abbfa9b230065f5311493a48bb75762` 일치를 확인했다. 전체 호출 재실행이나 물리 CPU 검증을 의미하지 않는다.

따라서 이번 감사 범위에서는 기존 final carry의 확정 오류를 발견하지 않았다. 다만 host SR 읽기는 일반적인 CCR oracle로 사용할 수 없다. CMP.W 뒤 emu_start를 나눠도 중간 SR 읽기가 없으면 CPU readout `2009`가 보존되지만, 중간 host SR 읽기를 삽입하면 이후 CPU readout까지 `2000`이 됐다. Context save/restore만으로 소실된다고 결론내리지 않는다. Pending/restart 경로에서 SR을 읽어 강제로 flag를 확인하면 원본 실행을 바꿀 수 있다.

감사 범위는 activation scripts, control, indexed, field, direct sound, sound callback, WORD callback, RTS callback, bank-state의9개 주 보고서다. 다른 scene/stage 관측기와 추가 verifier fixture의 모든 CCR 사용까지 감사한 것은 아니다. 일반 NZVCX 검증으로 확대하지 않으며 기존9개 보고서는 변경하지 않았다.

`.venv/bin/python tools/probe_m68k_sr_read.py`는 ROM 없는7그룹×4전략28조건을 각각 두 번 실행한다. ASR odd/even, ORI/ANDI와 CMP/MOVEQ/ADDQ를 same-start, split-no-host-SR, split-with-host-SR, split-context-restore로 비교한다. 메인은 결과 설명을 실제 관측 뒤 assertion으로 검사하도록 보강을 요청했고, context restore와 explicit reg_write를 구분하도록 문구를 정정했다. 최종본을 메인이 재실행해 동일 SHA를 확인했다. Source SHA `f256d11f3fdc76adb877ee589f55116a8efc37d713f4517b18452792c96a7375`, report SHA `b4a967b5e8c277fd5137f7f850feddceedd5710e834b7a9636d747e3244f21ee`.

별도 Sol이 최종28개 experiment를 메모리에서 재실행하여 모든 row·trace·register·CPU/host SR과 source/API/library 해시 일치를 확인했다. **이번 분석 단위 수용.** 확정된 관측 근거를 저장하며 새 C++40이나 전체 게임 완료로 집계하지 않는다.
