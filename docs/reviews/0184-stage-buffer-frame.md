# 전체 stage buffer frame 리뷰

대상 baseline `4c924b5`, branch `codex/stage-buffer-frame`. 신규 core/header/CLI/unit, inventory/observer/verifier, Makefile 및 문서를 리뷰했다.

메인은 원본4aa88/4b784/cd58의 전체 계약, 두 pending stack layout과 bank mapping을 직접 읽고 구현에 대조했다. WORD 상위 보존, live 크기/flag 읽기, slot D7 WORD 복원, 두 번의 bank reset, ring 자기 alias와 앞선 shift가 바꾼 toggle을 확인했다. 오류 시 RAM/state/ports 전체 transaction과 실제 MS5D 읽기 범위/중첩 검사도 검토했다.

Pending slot index를 lowWORD로만 검사하던 문제를 전체uint32 0..15 검사로 수정했다. Unit 및 negative의0x10000 입력 거부로 검증했다. 초기 원본 corpus의 빈틈인 fresh 둘째만 대기4조건과 앞 slot 포트 이후 다음 slot 대기2조건을 추가했다. Source probes가 모두 clipping되어 잘못된 bank를 가릴 가능성을 줄이도록 offset을 맞춰 첫 sprite가 보이게 하고 bank3→reset2→bank2 조회를 확인했다.

전체 observer/verifier와 CLI를 읽었다. 원본 no-SR-hook, 동일CPU/stack 대기 재개, 정확한 hold PC[cda4,cda8], immutable ROM/bank, 기록된 host변경과 현재 provenance 검사를 확인했다. 최종659조건/695단계의 RAM·14register·bank/phase/저장 상태·orderedports1340건이 일치한다. 20분기 중19양쪽, cdb2 normal-only는 caller가bit6을 설정하지 않아 생긴 제한이다. Musashi 독립337정상 호출도 일치한다.

메인이 CLI 검증을 재실행하여 동일hash를 확인했다. 별도 스크립트로695단계 원본 RAM writes를 입력과 외부변경에서 순서대로 재생해 모든 저장snapshot과 일치함을 확인했다. 오류196조건과 직접API원자성5조건, 성공ports교체 통과. 전체make Python182/C++125/경고0 (`artifacts/stage_buffer_frame_build_test.log`).

Native SHA256 `6b77299d0809fd21439effba2e1edf8a27cd32e7f2287ef25da009693320850c`; verification `3a96ceb91f257dbcd2e1cd94694d73c178f2ad85101d3aa938d5357849d4f197`; CLI `e7cb83ef01ec4e7c09171e545ec440628047b7d986eafdbd57c5d07819e8e21d`.

이 단위 통합을 수용한다. 기존 source8byte probes는 논리record 경계/자연사용 증명이 아니다. 파일저장 I/O실패의 다중파일 원자성, 임의callback/전체CCR/IRQ timing/자연scheduler/전체480bc/직접플레이는 보장하지 않는다. 원격 없는 로컬 통합이며 전체goal은active다.
