# `480bc` 이후 animation machine 다음 범위 분석(구현 전 계획)

Canonical BE ROM SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. Claude Opus 5.5 / high 읽기 전용 분석 작업자가 작성했고 메인(Claude Opus 5.5)이 검토해 기록했다. 기준은 worktree `metalslug-input` HEAD `57ec34a`(카드 메뉴 0236~0239, `480bc` U1~U7 core 포함)다. [F]=원본 바이트·기록 산출물·작업자 scratch Unicorn 탐침 사실, [I]=추론, [U]=미확인. **구현·검증 기록이 아니다.** block 시작 수는 capstone closure·동적 leader 기반 추정이다.

## 현재 범위와 기존 trace의 미도달

- [F] routing 규칙 27개(사운드·sprite·readiness·HUD·transition·exit·cleanup·screen·scene·palette_bind·map_transfer·interpreter·fade_card·card_child·card_menu 7·U1~U7)가 있다. stage controller의 정상 frame `47c6c→…→480bc→480f0`, `47eac..47fe0`, `47fe4→4804e→…→2a00`, 디스패처 `2ab8..2ac6`가 연결돼 있다.
- [F] 미연결 controller 구간: `477e4..47a94`(catalog·area·transition), `47a94..47aec` 진입 본문, `47af0` gate·`72f0`·`47b06` 표, `47c04..47c54` 활성화, `47da4..47ea8` area clear→다음 area.
- [F] stage_frame 등 기존 frame trace는 이미 전부 routing 안이다. stage_entry_body(152, `47a94→480bc`)는 미연결 leader 실행 10,667회(고유 84): `1a5a4` 3622, `19e30` 1136, `e905c` 1012, `47a94` 본문 989, `19938` 896, `19dee` 710, `1a414` 651 등. stage_activation_prefix(106)는 `477a2→ddf9a/362a..364a`, `47c04` 본문, `c3c0`, `ca56`, `ca76`, `9060`, `4e254`.
- [F] 기존 trace가 다루지 않는 것: 디스패처 전체 cycle, `47af0` 이후, pool 객체·stage event callback, frame head `e74`, controller `c66a`, player 객체.

## 자연 디스패치 cycle(작업자 scratch 탐침)

- [F] stage_entry_body begin seed 142개(`480bc` RTS 시점, `100b30`=`47af0`, `100bf4`=`e9150`)에서 PC=`2ac2`, A6=`100b30`으로 한 cycle을 돌리면 137개는 `e4a`, 5개는 sound wait `3aea`에서 멈춘다. 명령 637,593개, leader 실행 169,788 중 79%가 미연결(고유 2,571).
- [F] 미연결 실행의 분포: 지형 충돌 `43eb8..46fff`+`18be8` 49%, 객체 callback long tail 16%, stage event `e9150..` 11%, palette 참조 `8ebe`/`c6a96`/`c6bf6` 10%, 객체 이동 `4b5xx..4c3xx` 6%, 수학·난수 `490xx..49axx` 5%.

## Scheduler·IRQ·호출자·카드 메뉴 이후

- [F] boot `a26`→`2aac`(A6=`100820`), `2ab2`가 A7을 `104ca4`에 저장, `2ab8` 루프(JSR (A6), A6=8(A6)). 정적 node: `100820` frame head(`e4a→e74`), `1008e4` controller(`c52a…c654`가 `477e4`를 `100b30`에 설치, 이후 매 frame `c66a`), `100b30` stage controller, `100bf4` stage event(`e9150`), `100cb8`/`100da8` player(`1d1f4`). pool slot은 `100f5c`부터.
- [F] `e74`는 `ef2`에서 IRQ `c8c`가 올리는 `108016`≥`108017`을 기다리고 `3c0004`/`3c0000`을 쓰며 `3c0006`을 읽는다. `72f0`은 `107ded` bit7을 기다리는데 이를 지우는 곳은 IRQ palette 전송 `72fa`의 `7302`뿐이다. [I] bit7은 palette 전송 대기이며 새 Waiting 종류가 필요하다.
- [F] `480bc` 호출자 16곳 중 `47da0`·`47f3e`·`47fac`·`47fe0`이 연결돼 있고, 진입·전환 `478da 4790e 47992 479ac 47aec 47b60 47c00`과 area clear `47de8 47e26 47e66 47e74 47e96`이 미연결이다.
- [F] 카드 메뉴 객체 제거 뒤 controller `c66a`는 `100b30` 비활성을 `289e`로 확인하고 `c69a`(`c4cc`, `caf0`, `ca76`, 자식 `e66aa`, 62 대기, BIOS `c00444`)로 간다. [I] 게임 종료 후 BIOS 복귀 경로다. 일관된 seed는 없다.

## 제안 단위(의존 순서)

| # | 단위 | 진입→끝 | block 시작 추정 | seed | 위험 |
| --- | --- | --- | --- | --- | --- |
| F1 | stage controller 완성(catalog, 진입 본문+`1a5a4` 잔여+`e905c`+`e8a1c`+`19e30`/`19938`/`19dee`/`1a414`, `47af0` gate·`47b06`, `47c04` 활성화+`477a2`/`ddf9a`/`362a`, area clear) | `477e4`/`47a94`/`47af0`→`480bc`/`47c6c`/`477ee`/`2a00` | ~250 | stage_entry_body, stage_activation_prefix | `72f0` IRQ gate, 범위 검사 없는 표, PVC bank, sound wait |
| F2 | scheduler shell `2aac`/`2ab2`/`270e`, frame head `e4a`/`e74`·controller `c52a`/`c66a` 경계 | `2aac`/`2ac2`→node callback→`100820`/`1008e4` stop | ~10 | stage_entry_body begin | `104ca4`/A7 규약, boot 초기 node 값 |
| F3 | stage event `e9150` interpreter+`2a28` | `e9150`→RTS | ~130~150 | begin seed | opcode 표 범위, event stream window |
| F4 | 공유 객체 core: 4a 지형 충돌, 4b 이동, 4c palette 참조+난수 | callback→RTS | 4a ~360, 4b ~430, 4c ~150 | 새 관측 필요 | 간접 JSR 표, map buffer, SUBX/X, 64bit 비교 |
| F5 | frame head `e74`, controller `c66a` | `e74`→RTS, `c66a`→RTS/BIOS | ~850+~280 | host API 산출물만 | IRQ poll, raster read, video port 장치, BIOS |

[I] 뒤로 미룸: player `1d1f4`(정적 closure 약 2,618 leader, seed 없음), 적 callback long tail(약 2,000).

## 미확인

정확한 block 분할, host skip 없는 steady-state 객체 구성, 자연 `104ca4`·A7 값, BIOS 없이 `e74`/`c66a` live 상태를 만들 수 있는지.
