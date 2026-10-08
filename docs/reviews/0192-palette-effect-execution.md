# Palette effect 8c16 전체 레지스터 리뷰

Baseline `d94a832`, branch `codex/palette-effect-execution`. 후속47af0 연결에 필요한 native8c16 전체 RAM/15register API·CLI·unit·원본 verifier를 검토했다. Sol6.1/medium 세 작업자가 core/unit, CLI/문서, 원본 비교를 분담했고 메인이 원본 명령과 실제 변경 및 결과를 리뷰했다.

기존set_palette_effect는RAM효과만반환하므로후속caller의전체상태를대체하지못한다. 새execute_palette_effect는기존ObjectRestartState의15register형식을재사용한다. A5는입력값과무관하게108000으로설정한다. signedWORD clamp가범위를벗어나면MOVEQ처럼전체LONG을바꾸고,범위안에서는상위WORD를보존한다. WORDshift/subtract/OR와allzero분기,DIVS의나머지상위WORD/몫하위WORD를명시적정수폭으로구현했다. DIVS전duration은1..255로정규화되어0나눗셈이나quotientoverflow가없다. C++ signedshift·overflow에의존하지않는다.

전체RAM/상태는성공시에만반영한다. CLI는15숫자와두파일만받고정확한15키JSON을반환한다. RAM은65536byte/일반파일이어야하며input/output경로·inode별칭을거부한다. 출력예약은O_NONBLOCK과fstat검사를사용하고core성공후에만열어truncate한다. FIFO2종과기존출력보존을실제timeout회귀로확인했다. 일반I/O실패의파일rollback은보장하지않는다.

`.venv/bin/python tools/verify_palette_effect_execution.py`가pinnedMusashi의수정없는원본8c16과실제CLI883조건을비교했다. 전체RAM/15register/JSON일치,allzero324/nonzero559조건,범위밖clamp와zero-delta를조합한27조건,모든duration256값의zero/nonzero분기,signedWORDwrap,나머지음수/양수/0,임의A5입력을검증했다. D4..D7/A0..A4/A6불변도검사했다. 도달가능8조건분기양쪽을관찰했으며8cac의duration0분기는앞선정규화로도달불가다. 잘못된입력104조건에는FIFO2종과파일별칭보존이포함된다.

메인은clamp/WORD/DIVS를Python으로복제하여expected를만들지않고실제CPU결과를쓰는지,원본쓰기순서재생/stack sentinel/ROM불변/13개입력provenance를검사했다. reportSHA256 `4db8fcbafa31fd053b35afb3d2a8beef86183d018a9234f7aab4e74397aaadac`, CLI `cf721606e345b2ede4003fa2120de136c84f0ca02d3699bffdb26c992e64f8f2`. 현재파일hash와보고서일치를재확인했다. 전체 `make -j4 all test` exit0,Python182/C++134/경고0. 작업자의별도UBSan단위검증도통과했다. 로그 `artifacts/palette_effect_execution_build_test.log`.

이단위를수용한다. A7/stack/CCR/cycle/물리RAMmirror및화면동등성은API계약밖이다. 47af0 이후전체callback은아직미완료이며다음ca9e/caf0의D2/D6/D7/A4와A5상대RAM효과를연결해야한다. 메인은 `docs/analysis/screen-reset-full-contract.md`에정적근거를기록했고별도native관찰을위임했다. 전체게임Goal은active다.
