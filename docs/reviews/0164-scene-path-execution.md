# 장면 경로 실행 리뷰

Baseline `f1d0d1b`. 이전구현·검증goal turn은progress이며직후사용자화면확인질문에대한답변은상태설명만이었다. 이번에는보존된최종검증을현재binary/resources와대조하고리뷰·진행기록을통합했다.

메인이원본19e64..1a07a/16ff8..17012를분석해계약을제공했다. gpt-6.1-sol medium은확정사양의C++/CLI/unit과독립원본반복관찰·비교를담당했다. 메인은core/CLI/unit/observer/verifier와최종보고서를검토했다.

## 리뷰 결과와 보강

BCLR.B는metadata+c의highbyte만다루고OR.W는전체word를다룬다. 04는old descriptor가null일때bits1/3를지우지않는다. 새descriptor좌표는signed12bit이며MOVE.W의highword를보존한다. 조건분기는N-only와TST뒤BLE를구분하고false경로에서는metadata cursor를게시하지않는다. 원본이저장한A1/A2만helper뒤복원하고나머지scratch를승계한다.

초기2,446조건의metadata highflags가0b/70에치우쳐bit2/7와BCLR조합을충분히구분하지못했다. 메인이canonical04에256highflags×oldmapnull/non-null 512조건추가를요청했다. 최종2,958조건은이전성공재사용없이원본과C++를전체재실행했다. ROMpatch없이RAM합성stream으로canonical에없는조건opcode를관찰했고각true/false를확인했다.

기존transfer/refresh본문은변경하지않고private주소접근도구를재사용했다. Unknown opcode와늦은실패는전체API상태를보존한다. CLI의두출력파일쓰기자체가filesystem-wide atomic하다는주장은하지않는다. 명령1048576개와하위helper탐색/전송한계는명시된미완료영역이다.

## 검증

- 원본2,958 / CLI오류36 / orderedports130,388. 전체RAM/13register 일치; 원본RTS/A7복귀와ROM/bank불변확인.
- 원본 SHA256 `29facad109b2bcac22b1b0a114cac5dc5fa41d317b1e0cd1a1a183c840b082a0`.
- 전체비교 SHA256 `9f4d41d3bd8c55215a56f060f138603e0e972f8c59293715e4db85dd8a8ff687`.
- Binary SHA256 `c2d6651bc3c6c25711c813f5d22118f93e1d080a4038c175221b225c82c12420`.
- 전체make Python170/C++106/경고0. 기존refresh회귀1,744/오류35/23,636ports; report SHA256 `baa483f1209b6388603b2d61e1282ee531dfb91f83cfc5d26f98fb2d31f20531`.

메인이현재파일의SHA와보고서내binary/resource SHA를직접재계산했다. 공유refresh회귀가통과하고기존transfer본문은변경없어동일transfer corpus의추가재실행은하지않았다. 재생성명령과case구성은scene-path-execution.md에있다.

## 남은 연결

기존update_scene_debug는RAM/ports와D0/D1/D3만반환한다. 전체1a7a8을구성하려면이함수의전체register scratch를복원하고12register좌표prefix와13register path사이A3를보존하는연결이필요하다. 일반1a5a4는nullscript특수화로대체할수없다. 자연frame·입력·전체stage화면·전체게임복원은미완료이며goal은active다.
