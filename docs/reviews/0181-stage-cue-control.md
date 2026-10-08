# Cue 제어·할당 wrapper 리뷰

Baseline `7ef7bb1`, branch `codex/stage-cue-frame`. 신규 stage_cue_control API/CLI/unit, default packer, bounded inventory와Musashi 관측/비교, Makefile 및문서를대상으로한다. 후속sprite_submit_execution 작업은이리뷰/통합에포함하지않는다.

메인이 원본5entry와cd58후속흐름을직접읽고계약을정했다. core/header/CLI/unit전체를읽어WORD상위보존,unsigned gate와+12진행,두flag의실제camera주소,원래A6와allocator용A1parent분리,실패후byte복사,lateerror전체rollback을확인했다. 출력과입력/리소스의동일경로·inode거부,숫자범위와loader검증도확인했다. 기존allocator는변경하지않았다.

Packer의정확한8/14byte범위,MS5Dheader/CRC/source/hash/reload,재생성동일을확인했다. 메인별도오염24조건거부도통과했다. Inventory의147명령과DATA3창/catalognonnullroot42prefix를다시생성해동일hash를확인했다. Raw검색0건을callback폐쇄성으로해석하지않는다.

관측/검증도구전체를읽고,raw branch row에서재집계한결과와native aggregate의대조를추가하도록수정요청했다. 수정후원본/CLI최종증거를재생성했다. 메인이555저장RAM·fixture·incomingregister·입력승계·분기·현재provenance를직접확인했고실제CLI검증도재실행해동일보고서hash를확인했다.

원본555조건의64KiB RAM·14register가일치했다.2986성공69/실패89모두후속copy실행,12live-byte alias증거,8조건분기양쪽,오류155조건통과다.28d6nullfreehead는지원정상graph에서제외하고C++오류로검증했다. 세sequence의12호출/9prior소비는allocation A0/A1설정과stream phase갱신을포함하며cue sequence만host수정이없다. Full CCR이나자연stage실행동일주장은하지않는다.

전체make Python182/C++122/경고0, `artifacts/stage_cue_control_build_test.log`. Native SHA `b820dff0be27fbc038c563473840fc6bb3652788c57bf200c7248d0c1a06da52`, verification `3607ca69a390b0d133ece913f9ac5956ed99f221d1aa22e597d0bdd29c7d2e20`, CLI `04231d0f1ef04ed52a865e6e2bcc951e0ae82031d5f1e8ec01b06926cbdf4f5b`.

이단위통합을수용한다. 전체e8a48과sprite pending은후속이다. 원격없는로컬commit/review이며전체goal은active다.
