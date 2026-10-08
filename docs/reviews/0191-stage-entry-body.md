# 47a94 초기화 본문과 첫 frame 연결 리뷰

Baseline `e05fa5c`, branch `codex/stage-entry-body`. 대상은 body API/CLI/unit, Makefile, native observer/differential verifier, 후속 callback 정적 계약과 기존 frame CLI의 FIFO 수정이다. 원본 ROM·추출 데이터·실행 산출물은 Git에 포함하지 않는다.

Sol6.1/medium 세 작업자에게 core/unit, CLI/문서, native 관찰/비교를 분리했다. 메인은47a94/48398/30f4 원본 명령, A5 고정 전제, register/port adapter와 전체 transaction을 검토했다. 완료 작업자는 문서 보완과 기존480bc 재검증에 재배정했다. 각 파일 소유권을 분리했고 최종 빌드 후 source freeze 상태에서 두 verifier를 병렬 실행했다.

본문은 매 호출 지점에서 live A6+76 record를 다시 읽는다. scene 초기화, cue 선택, flags/lookup, event 초기화, callback47af0 게시와480bc를 원본 순서대로 수행한다. A5=108000, D0..D7/A0..A6를 보존·반환하며 event의15register adapter를 사용한다. 초기화 완료 후 frame 대기는phase1, 전체 반환은phase2이고 완료 body 재호출을 거부한다. 대기 재개는 초기화·lookup·callback을 반복하지 않으며 실패는 이번 호출 전체 RAM/state/ports/readcount를 보존한다.

메인이 scene metadata와 겹치는 live RAM record10d420을 원본에서 직접 실행했다. 초기화가 +6 cue를00a00080, +a indirect를0, +e target을ffff로 바꾸며 뒤쪽 호출은 바뀐 값을 읽는다. 실제 CLI도 전체 RAM/15regs/bank/ports와 일치했고 이 사례를 최종 matrix에 포함했다. 단위 테스트의 별도 인위적 리소스 alias를 원본 증거로 대체하지 않았다.

Opus `claude-opus-5-5` / high 독립 읽기 전용 리뷰는 core 논리 오류를 찾지 못했고 FIFO를 blocking open하는 CLI 문제를 발견했다. 새body와 기존frame CLI 모두 RAM/TABLE의 일반 파일 여부를 stream 전에 확인하고 출력 예약에O_NONBLOCK을 적용했다. 기존 inode/입력 보호 및 새 placeholder 정리를 유지했다. 두 CLI의 FIFO5종씩과 정상 실행·별칭을 포함한16개 timeout 회귀를 통과했다. 결과 `artifacts/stage_entry_body_cli_review/smoke.json`. 일반 쓰기/close 실패 시 두 파일 원자적 교체는 보장하지 않는다.

Opus 로그 `artifacts/stage_entry_body_opus_review.json`: 실제 modelUsage claude-opus-5-5, effort는 CLI high 요청이며 결과별 확인 필드는 없다. 268.423초, 보고 비용$1.458841, output26190(thinking20028), input36/cachecreation93407/cacheread938205. Opus는 테스트를 실행하지 않았다. 리뷰의 물리 RAM mirror/stack 지적은 계약 한계로 명시했다. oracle stack1feffc는 비교하는64KiB RAM 밖의 독립 영역이며 어떤 RAM byte도 비교에서 마스킹하지 않는다. A7/stack/CCR은 native 관찰 항목이고 API의 물리 기판 동등성 주장이 아니다. cue status의 초기Accepted만 강제하지 않는 것은 의도된 보존 계약이다.

최종 native142조건/152단계와 실제 CLI가 전체 RAM/15register/bank/pending/external read/정확한 JSON/순서 있는1,510,070 watchdog·video·PVC writes에서 일치했다. actual59records×2register profiles, lookup8개를 null/nonnull event에 적용, initial bank3, live record alias, sound5pending 및 동일 CPU/stack/CCR 재개를 검증했다. 재개에는 명시된 host 쓰기만 적용하고 이전 callback/flags/record를 손상시켜 초기화가 반복되지 않음을 확인했다.620개 MS5D는 원본 byte/헤더/CRC/hash를 검사했다.187오류조건(FIFO5종 포함)과 별도 실제 case alias1조건을 통과했다.

재현 명령은 `.venv/bin/python tools/observe_stage_entry_body.py` 다음 `.venv/bin/python tools/verify_stage_entry_body.py`다. native observation SHA256 `1f65100f1fedc36b4999543c720814dc6f9eb4bf634f3af3439aa68d70e31207`, verification `6b0ad56cdf7300916f8274e55c78f613dca4dba3f92dbaa47cf3750671356454`, CLI `9fe92b655e0fa6d1b070749ddd468f5ef69b7daf8b7bb6761cd52558c1b766d3`. Trace는 schema1 gzip JSON으로 모든 PC/RAM write/bank read 값을 보존하고 SHA/count/format을 검증한다.

기존frame도 수정된CLI로 원본96단계/오류148조건/casealias/264ports를 재검증했다. 새 reportSHA `47645dd39e0df8241cb504cd637a99cdc751544b4ac47c9e1227d8d5705f53b5`, CLI `5e48e796a14c184289a73d10bea2b252a5d85d27c5ce8f530137be34f5207d42`. 메인은 body270개 및frame281개 현재 source/binary 입력 hash, native152단계의 RAM/ports/trace와 리소스·metadata를 재대조했다. 최종 `make -j4 all test` exit0: Python182/C++133/경고0. 로그 `artifacts/stage_entry_body_final_build_test.log`.

통합을 수용한다. canonical noIRQ 초기화가cce0/cce8에서 sprite queue를 초기화하므로 body부터 시작한 buffer/cue 대기 도달성은 이 matrix가 증명하지 않는다. 기존480bc 자체의 해당 대기 검증과 구분한다. 본문 reader는 aligned RAM/unique fixed window이며 banked record/24bit alias/RAM mirror 일반화는 미지원이다.47af0 이후 callback, 자연scheduler/IRQ, 직접플레이, 전체CCR/cycle/화면·오디오 동등성은 미완료다. 전체Goal은 active로 유지한다.
