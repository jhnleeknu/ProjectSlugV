# Animation10 전체 상태 분석 리뷰

Baseline `27cadc4`, branch `codex/animation-indexed-analysis`. 대상은 두 원본 관측 도구와 세 분석 문서다. 원본 canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`는 유지된다. 고정 CPU 주소와 ROM 파일 offset이 같은 범위만 분석했다.

메인은 handler의 partial WORD/BYTE, signed displacement와 unsigned 비교, 실제 조건부 fetch, 내부 draw 복귀와 외부 list 복귀를 리뷰했다. 특히 list length가7이어도8BYTE record를 읽는 원본을 array bounds 의미로 바꾸지 않으며, field의상위BYTE를버리지않는다. callback_return을 재사용하면D6와상태pointer가변하므로 별도 list 복귀가 필요하다. saved_a1과saved_list_end가다른중간record 및 poisoning 후 대기를 근거로phase3 상태를 확정했다.

메인은 observer source의 ROM불변,실행범위,trap중단,SR읽기시점,실제stack/전체RAM write replay를 확인했다. 합성846조건/854단계를 메모리에서 전부 재실행하여 보고서 모든 info와RAM/ports/trace를 비교했다. 입력6개와산출물3416개SHA도일치했다. native SHA `db3247ceba5327719b84882b7d1abe006f0e30c87d28642ed7c2f9a9f75a6508`;PVC3564개. 독립Sol의90조건98단계감사도일치한다.

기존fixed script 기반30조건/30단계는 독립Sol이 `/tmp/metalslug_audit_indexed_fixed.py`로 전부재실행했다. RAM15regs/carry/trace/PVC300개 및입력9/산출물120해시일치,exit0. native SHA `7f50c9d4ddf4023e47dd22abc6849cbd6322bd4916f2e620a04a2ca78b61fd37`. 도달한list는65f64/6605a만이며8개전체실행을주장하지않는다.

재생성 명령은 `.venv/bin/python tools/observe_animation_indexed_execution.py` 및 `.venv/bin/python tools/observe_animation_indexed_fixed_scripts.py`다. 산출물은ignored artifacts에만있다. 이번에는전체빌드나기존C++회귀를반복하지않았다. C++와규격은변경되지않았고새C++동등성은후속작업이다. 잘못된selectedopcode/TRAP와목록밖을선택하는네음수길이조합은정상성공oracle에넣지않았다.

구체적인코드/증거불일치를발견하지못했다. 공통CLI positional schema의명시적변경과세기존verifier갱신을구현단위에서함께수행한다. 자연scheduler/IRQ,모든selector/length,전체opcode/callback,직접플레이및전체Goal은미완료다.
