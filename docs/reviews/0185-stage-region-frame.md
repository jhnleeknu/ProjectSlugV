# 전체 stage region frame 리뷰

대상 baseline `77ff5cc`, branch `codex/stage-region-frame`. 신규5entry core/header/CLI/unit, inventory/observer/verifier와Makefile/문서를리뷰했다. stage-spatial-frame.md는후속원본분석초안이며검증완료범위에넣지않는다.

메인이전체89명령/5창을직접읽고원본계약을작성했다. 49392의ANDI가C를지우는점,4d9d6의A6상위WORD사용과두종류null반환,1c028의D0하위WORD만복원,메모리MOVEM.W의32bit부호확장,첫/둘째게시순서,6WORD stride10 clear를구현과대조했다. 기존4d7a6lookup을잘못재사용하지않는다.

Core/header/unit 전체와기존CLI대비전체diff를읽었다. source window 선택/중첩거부/24bit상한과RAM경계,정수WORDwrap,오류transaction을검토했다. API49392이외carry보존은원본전체CCR가아닌명시적API계약이다. A6/bank는읽기전용이다.

관측/검증도구전체를읽고둘째source=dd50이직전sentinel을읽는추가fixture를요청했다. NativeMOVEM결과ffff8000을확인한다. 기존첫게시→둘째source/coordinate alias와함께원본순서를검증했다. Inventory의문서hash는최종보고서hash와순환하지않도록제외하고경로참조를유지했다. 리소스fixture수문구를실제8조건과일치시켰다.

원본801조건(Musashi797,banked Unicorn4)의전체RAM·14register·bank·carry가일치했다. 15지원분기양쪽,signextend중간snapshot65건,byte선택/bit0fallback불일치40조건,6frame중5prioroutput승계,154CLI오류/5directAPI원자성통과. 원본A5불일치TRAP는범위밖이다. SR은49392반환후에만읽고hook에서는읽지않는다. ROM/bank불변과원본도구provenance를검사한다.

메인이실제CLI검증을재실행해동일hash를확인했다. 801snapshot의원본write2407건을독립순서재생해RAM이일치하고입력승계·현재provenance·branch집계도확인했다. Inventory재실행도동일hash다. 전체make Python182/C++126/경고0 (`artifacts/stage_region_frame_build_test.log`).

Native SHA256 `46a80065db1ccc48d27696743c04e9e005f8dedc8024eecf2fcd4f27c3d0c1a9`; verification `7aa3576aa81864ba55e3ab21252ebe3d31ee4e8c1f81658d8443dbce67bce078`; CLI `5bf69cc5ad55e73bd130f2519792389fe950cf38cf337aef83fd188d36c77e09`.

이단위통합을수용한다. 기존raw8byteprobe는자연record/사용성증명이아니다. 전체CCR/IRQ timing/전체480bc/자연scheduler/직접플레이는미완료다. 원격없는로컬통합이며전체goal은active다.
