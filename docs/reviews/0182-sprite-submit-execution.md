# 스프라이트 제출·대기 재개 리뷰

Baseline `ea635cd`, branch `codex/sprite-submit-execution`. 신규 full-register API/header/CLI/unit, native 관측/비교 도구, Makefile 및문서를검토한다. 원본 SHA와fixed CPU=ROM 매핑은sprite-submit-execution.md에기록했다.

메인이 원본cd58..ce00과core/header/unit을대조했다. Callback이clipping전에실행되고각clip/full의register변화를반환한다. 대기는캡처D4/D6/A1을유지하고cda4부터재개한다. Normal/deferred의live read/write순서, count증가와source읽기순서, MOVEM의세LONG순서를확인했다. 모든산술은unsigned폭으로정의하며signedWORD주소는명시적으로확장한다. 완전한정렬RAMspan밖접근은오류이며candidateRAM/state/status만성공시게시한다.

독립읽기전용리뷰에서도정수폭/UB/alias/transaction문제를발견하지않았다. Unit의수동D6=061a waiting값은보통cd58의mask로생길수없으므로메인이합성direct-resume검증이라는주석을추가했다. 자연도달의증거로쓰지않는다.

CLI전체의parser/파일동일경로·inode검사/입출력/상태게시를읽었다. Observer/verifier전체를읽고tautological주소검사를실제normalcursor/deferredcount주소검사로수정요청했다. 여섯분기의실제successor를각phase에서재집계해보고서와대조한다. Nativeorderedwrite는원본내순서증거이며, C++은alias에민감한최종RAM과source리뷰로대조한다. 독립C++write-event trace동일이라는주장은없다.

원본616조건/736단계의64KiB RAM·14register·waiting/status가일치했다. accepted512/clipped88/full16/waiting120, 실제대기60chain과120CLI재개를검증했다. Hold는실제CMP/BNE2명령후cda4로돌아온다. NativeCPU reset/register재설정없이원본captured상태를유지하며외부RAM변경만기록대로수행한다. Unknowncallback으로바뀐뒤재개에서도그callback을다시실행하지않는다.

CLI오류31조건과별도directAPI6조건에서입력/기존출력또는RAM/state/status원자성을검증했다. 메인이736저장RAM/입력승계/외부변경/PC/A7/branch/provenance를직접확인했고실제CLI검증을재실행해동일hash를확인했다. 전체make Python182/C++123/경고0, 로그 `artifacts/sprite_submit_execution_build_test.log`.

Native SHA `e5ed5e1e0119a1684f40318f708e920553dc1a071a09b9fedb19b4506d651b39`, verification `06ee2a59080d2c5d984a35d5bc2f06a7807ad44c8cff441d391f66e58800844e`, CLI `78eb3a1ffcc79634c963d076d8e94f8d6cdca51f115b73bd0b2ebc0ee559266d`.

이단위를수용한다. 임의callback/전체CCR/IRQ timing/자연scheduler/전체stage frame은범위밖이다. 원격없는로컬commit/review이며전체goal은active다.
