# F5 frame head `e4a`/`e74` native 관측 결과

표기: [F]=원본 바이트 또는 기록 산출물에서 확인한 사실, [I]=추론, [U]=미확인.

이 문서는 `tools/observe_animation_machine_frame_head.py`가 원본 ROM을 Unicorn M68000 oracle로 실행한 관측 결과를 기록한다. 결정 D1~D10은 `docs/analysis/animation-machine-frame-head-f5-scope.md`를 따른다. **자연 게임 실행이 아니다.** BIOS 실행, 자연 IRQ, 자연 scheduler를 주장하지 않는다. 모든 재진입과 host 쓰기는 선언된 단계이며 observation에 기록된다. controller 본체(`c52a`/`c66a`)는 실행하지 않았다.

## 기준과 산출물

- [F] canonical BE ROM `extracted/program/maincpu.decrypted.be.bin` SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`, 8 MiB. 관측 전후 SHA·크기·mtime이 같다(`rom_stat_start`=`rom_stat_end`). ROM은 수정하지 않았다. fixed 영역은 CPU 주소=file offset이다.
- [F] oracle: Unicorn 2.1.4, `UC_CPU_M68K_M68000`, 라이브러리 SHA256 `7207c8e3d7a63118fb0bca73e01816797fd51b1d8a39a4cbc7abfd562ee59c85`.
- [F] routing 원천 `engine/src/animation_machine.cpp` SHA256 `36cb03c8e257208e0685cdb93a071867920bba256320f2dc2e1612c8ee506da0`(git `ea30912`, 규칙 78개, routed PC 47,255개).
- [F] 입력 고정 데이터: `docs/analysis/data/animation-machine-frame-head-leaders.json` SHA256 `6bda408618578fa6dfc3f62585259dd3321c0b2b03d8d7017bed092dd774a6cf`, `animation-machine-frame-head-fixtures.json`(정적 leader·fixture 목록, SHA는 `observation.json` `inputs`에 기록. 첫 두 run은 scratch 경로에서 읽은 값 `3bbff977…`).
- 산출물: `artifacts/animation_machine_frame_head_native/observation.json`(Git 제외). 최종 `observation.json` SHA256 `4fe4f796879af90df1c1fd4c753485a9bf0a04d2667b14b8c00dbab23879b16b`(저장소 경로 두 run 동일, `diff -rq` 차이 없음). 이전 scratch 경로 두 run(SHA256 `dbb631a8…`)과는 `inputs`의 자료 파일 경로 키만 다르고 나머지 값은 모두 같다.
- 출력 크기: 파일 8,100개, blob 7,715개(505,610,240바이트), 합계 592,355,199바이트.

## 프로토콜(D1)

seed 준비는 `observe_animation_machine_scheduler_rng.py`와 같다(`49a1a`, D0=0, F4 결정 1). 자연 seed는 `stage_entry_body` begin 출력 137개이고 guard row 5개(release 출력)를 따로 둔다. 총 142.

- [F] frame 0: N만 실행한다(F2 pass, `2ac2`, A6 `1008e4`, A7 `1ff000`).
- [F] frame 1..399: H -> 선언 controller 생략 -> N. frame당 한 번이며 400 frame을 한도로 한다.
  - H: pass-end 상태(A6 `100820`, A7 SPd-4, LONG(SPd-4)=`2ac2`)에서 frame head를 native로 RTS까지 실행한다. dispatcher(`2ac2..2ac6`, `2ab8`)가 다음 node를 A6=`1008e4`로 읽고, `2ac0`의 `JSR (A0)` 직후에 멈춘다. 멈춤은 A6/A7/복귀 LONG을 확인한 뒤에만 허용한다.
  - 생략(선언): PC := `2ac2`, A7 += 4, SR := `2000`(CCR 0, 읽지 않음. H 시작 CCR 정규화도 같은 선언).
  - N: 기존 F2/F3/F4 pass와 동일.
- H 명령 상한 6,000,000, SPd=`1ff000`(2,093,056).

### 대기와 해제 선언

stop-before-instruction 후 host가 쓰고 같은 segment를 이어간다. 주소·live 값·해제 값을 기록한다.

| 대기 | 조건 | 선언 해제 | 결정 |
| --- | --- | --- | --- |
| `ef2` vblank | BYTE `100016` < BYTE `100017` | BYTE `100016` := BYTE `100017` | D2 |
| `16bd0` sprite flush | WORD `108d34` <> D0.W(=WORD `108d36`) | WORD `108d34` := D0.W | D5 |
| `3aea` sound ring | 기존 vocabulary | WORD `104d74` := `ffff` | D6 |
| `c376` card | `c00468` 호출 중 `c376`만 | fade_card 계약 재개(PC `c37c`, A7 += 4, BYTE `10fdc6`) | 기존 F4 |

`72f0`/`cda4`는 기존 F2/F4 관측기와 같고 H에서는 자연 상태로 도달하지 않는다(fixture용). IRQ `c8c` 자체는 F6이다.

### 외부 읽기 queue(D3/D4)

- raster `3c0006` WORD, 입력 `300000`/`340000`/`380000` BYTE는 frame별 선언 queue에서 읽는다. 기본값 raster 0, 입력 `ff`(active-low, 누름 없음). queue가 모자라면 `external-read-queue-empty` checked stop이다.
- [F] 자연 H 54,264개 전부 읽기 패턴이 동일하다: `3c0006/2 3c0006/2 380000/1 300000/1 340000/1 300000/1 340000/1`(H당 7회).
- 순서 있는 port 이벤트(D7): watchdog `300001`, `3c0000`/`3c0004`, PVC `2ffff0`/`2ffff2`. 자연 H 합계: `300001/1` 3,047,696, `3c0000/4` 3,845,876, `3c0004/2` 54,264, `2ffff0` 218,452, `2ffff2` 218,452.

### guard(checked stop, 상태 보존)

aux callback `f3c`(`100896` <> 0), menu callback `931a`(`107df6` <> 0), `fee`의 TRAP #15, 선언되지 않은 device 읽기, BIOS fetch(`c00444`/`c00450`/`c00468`, 선언된 `c376` 재개 제외) `bios-boundary`, 홀수 PC/data, 매핑 밖 접근, 명령 watchdog.

## 결과(자연 seed)

- [F] 자연(`natural`) 기록 137개(case 0..135, 141) 중 400 frame 완주 136개(case 0..135, 정지 `frame-limit`). case 141은 frame 0에서 `odd-pc`(PC `47c05`)로 멈춘다(node A6 `100b30`, 그 node의 callback `47af0`). 완주 136개는 기존 old frame limit 136과 같다.
- [F] guard-release 5개(case 136..140)는 frame 0에서 `fetch-unmapped`(주소 `deadbeef`, node A6 `100b30`, cb `deadbeef`)로 멈춘다.
- [F] 정지 분류: frame-limit 136, fetch-unmapped 5, odd-pc 1. 위 6개 모두 기존 baseline 재현(142/142)에 포함되고 기존과 같은 위치에서 멈춘다(`baseline.reproduced`).
- [F] H segment 54,264개(136 seed × 399), N pass 54,406개. 모든 H가 controller transfer에서 멈췄다(`h_stop_totals` controller 54,264). H 시작 callback: `e4a` 136(첫 frame), `e74` 54,128. transfer 시 `1008e4`의 callback은 54,264개 전부 `c52a`다(LONG(`1008e4`)=`c52a`).
- [F] A7 오류 `a7_bad`=0, head 오류 `head_bad`=0, 생략 오류 `skip_bad`=0.
- [F] H 규모(seed별 최댓값 범위): H당 port 최대 14..2,644, H당 translation block 최대 1,263..1,797, H당 RAM 변경 바이트 최대 516..2,348(seed별 한 H의 pre/post 차이). pass당 node 최대 6..47, pass당 TB 최대 102..8,969.
- [F] 경로 hit(PC 도달 횟수, 전체 H): `e74` 경로 대부분이 54,264(=H 수). `e4a` 첫 frame 본체와 callback 설치 `e6e` 136. 0회: `fee` TRAP, aux `f3c`/`f46`/`f4c`, `eda` debug call, forward writer path `16bec`, input mode1 `334e`, mode>1 `3406`, menu callback `931a`, pause 경로 `fb4`/`f8e`/`f6e`. reverse path `16c6a` 54,264. `16bd0` sprite flush 대기 지점 62,364(=54,264 + 선언 해제 8,100).
- [F] `16bd0` 대기: 자연 seed 100개에서 발생, 합계 8,100회, 36 seed는 0회. seed별 횟수는 85회가 61개, 81회가 25개이고 나머지는 80/84/70/61/50/39 등이다. 최대 85회.
- [F] vblank 대기(`ef2`)는 자연 seed에서 0회다(자연 seed의 `100017`=0). card(BIOS) 재개는 seed 130개에서 각 1회, 7개는 0회.
- [F] H transfer 시점 필드: `100012`/`10fdaf`/`10fdae`/`10fd82`/`104cd4`/`100016`/`100017`/`100018`/`10001a`/`107dea`/`108d3c`/`10f000`=0 전부, `10001b`=`80` 전부. `10000e`는 1..c(12개 값, 각 136회; H마다 frame 번호는 1..399인데 기록은 이 12개 값만 가지므로 필드 hist의 표본 한계 [U]). sprite consumer/producer `108d34`/`108d36`은 대부분 0이고 일부 H에서 `4`..`b0` 값을 가졌다. stage controller node cb `100b30`: `270e` 23,268, `4806a` 16,256, `47fa8` 3,968, `47fdc` 3,968, `48090` 3,968, `47bfc` 2,136, `47b5c` 700.
- [F] controller idle(`100b30`=`270e`가 처음 H에 나타나는 frame): 245 -> 89 seed, 241 -> 35, 1 -> 8, 221 -> 4, 없음 -> 1(case 141).
- [F] 모델 H 54,264개 ok, 불일치 0, 독립 모델 총 60,699,668 step.

## 동일성 검사

- [F] fresh-CPU 분할 실행과 연속 실행을 각각 두 번씩 비교해 전부 같다(`fresh_split_equal_all`=true, 142 seed 모두 `split_first`/`split_second`/`continuous_twice`/`frames`/`stop`/`prep_exit` 참). 변종 48개와 fixture 195개도 같다.
- [F] 기존 선언 모델 재현: 142 seed 모두 재현(`baseline_reproduced`=142/142). 기존 400 frame 완주 136개. 기록된 `run_digest`는 옛 입력 worktree의 routing coverage flag를 포함해 77개에서 digest 자체는 다르지만(해당 필드는 비교 대상 아님), 마지막 3개 pass-end 상태 digest·frame 수는 142개 모두 같다(`pass_end_tail_equal`).
- [F] 기록 observation 교차 비교 8 case(0,1,2,100,106,111,135,141): frame 0 N 시작·끝이 같고, 7개는 frame 1의 H 시작 상태가 기존 pass 0 끝 digest와 같다. case 141은 기존 기록도 완주 0 frame이다.
- [F] 독립 Python M68000 모델: 68000 Programmer's Reference 형식으로 원본 ROM 바이트를 직접 디코드하는 인터프리터. 전체 CCR(XNZVC), 32비트 레지스터, 바이트/워드/롱 연산을 명시한다. Unicorn·capstone·C++ 코드를 공유하지 않고 PVC bank 공식(`address_map.pvc_bank_update`)만 공유한다. 미지원 opcode/EA는 `ModelError`로 센다(BCD, bit-field, CHK, MOVEP, 68020 형식 포함). 선언 프로토콜(queue, 대기 해제, controller stop)을 모델이 자체적으로 재생한다. 결과: 불일치 0.
- [F] 음성 대조 12건(`model_self_tests`): 비교가 실제로 차이를 잡는지 확인한다. 무변경 1건 ok, 변형 10건(RAM 1비트, D3 1비트, A2, PC, port 값 하나, port 마지막 항목 누락, 외부 읽기 값, RAM write 값, RAM write 마지막 누락, 가짜 wait 기록) 모두 불일치로 검출, 빈 입력 queue는 모델이 정지.

## 변종(declared variants)

case 0, 1, 2, 100, 106, 111 6개 seed × 8종 = 48개, 전부 400 frame 완주·분할/연속 동일·모델 ok.

| 변종 | 선언 |
| --- | --- |
| `vblank1`, `vblank2` | H마다 BYTE `100017` := 1 또는 2. `ef2`가 frame당 대기하고 `100016 := 100017`로 해제 |
| `raster-hi` | raster >= 8000(clamp 미실행), 두 읽기 값이 다르고 가끔 낮은 첫 읽기 |
| `raster-mixed` | 의사 난수 16비트 raster |
| `input-rand` / `input-all` / `input-start` | 난수 active-low / 전부 누름(00) / 380000 start·coin 비트가 3 frame마다 low, P1 방향 토글 |
| `combo` | vblank 1 + 난수 입력 |

seed 0 vblank 변종에서 `ef2` 도달 798(frame당 2회: 대기 진입과 해제 후), vblank wait 해제 399, `16bd0` 해제는 자연과 같은 85회. 새 leader를 더한 변종은 4개 leader에 그쳤다.

## BIOS 경계

[F] 7개 사이트가 원본 명령과 일치하고 두 번 반복해서 같다: `c00444`(SYSTEM_RETURN; JMP 사이트 `c598`(controller boot), `c5a6`, `c6c8`, `c7c0`, `c982`), `c00468`(card BIOS 요청 JSR; 사이트 `c310`), `c00450`(BIOS 크레딧 요청 JSR; 사이트 `4a98c`, `10fd82` <> 0일 때만). 사이트 값은 observation의 10진 `site`를 hex로 바꾼 것이다. 모두 해당 BIOS 주소(`c00444`/`c00468`/`c00450`)의 unmapped fetch(`UC_ERR_FETCH_UNMAPPED`)로 멈춘다. 멈춘 시점의 A7·RAM digest·스택 top을 기록했고, 이 정지를 BIOS 실행으로 세지 않는다. BIOS 코드는 실행하지 않았다. `c00468` 선언 재개는 `c376` 호출에만 존재한다.

## fixture

- [F] 195개: 코드에 정의한 손 fixture 13개(`guard-*` 4: trap-fee, aux-callback, queue-empty-raster, queue-empty-input; `path-*` 9: raster-short-queue, debug-3a70, sprite-forward, vblank-wait-1/2, raster-high, input-all, input-mode1, input-mode2) + 고정 데이터 파일 `fixtures.json`의 합성 182개(search 169, search2 6, guard-search-* 7). 합성분은 구조화된 host 편집을 커버리지 유도 탐색(scratch, 납품 대상 아님)으로 찾은 것이며 데이터 파일에 (case, frame, writes, script)를 명시해 재생한다.
- [F] 195개 모두 ok, 분할/연속 동일, 모델 불일치 0. 종료 사유: frame-limit 174, external-read-queue-empty 10, odd-data-access 2, invalid-memory-access 2, 각 1: trap-boundary, frame-head-aux-callback, step-limit, head-next-node-not-controller, wait-not-released, fetch-unmapped, undeclared-device-read.
- [I] 합성 fixture의 RAM 편집은 도달 가능한 게임 상태라고 주장하지 않는다. 코드 경로 시험용이다.

## leader 커버리지

정적 leader 2,038개(+ Duff 진입 256개) 대비 실행 범위. 기준: H segment의 실행된 translation block 바이트 범위에 leader가 들어 있으면 덮인 것으로 센다(block hook, 명령 단위가 아님).

| 구분 | 개수 |
| --- | --- |
| 자연 seed | 577 |
| 변종 추가 | +4 |
| fixture 추가 | +1,666 |
| 미커버 | 47 (Duff 7 포함) |

단위별(natural/variants/fixtures 추가/미커버): H1 78/0/38/4, H2 28/4/95/24, H3 312/0/239/0, H4 89/0/67/1, H5 13/0/135/1, H6 53/0/154/4, H7 0/0/213/2, H8 0/0/156/1, H9 0/0/147/2, H10 0/0/213/2, H11 0/0/209/6. 단위 열은 단위별 값이며 열 합이 총합과 정확히 맞지 않을 수 있다([U] 단위 간 중복 처리는 확인하지 않음).

미커버 47개(CPU 주소 hex): `f44`, `f4c`, `f52`, `3360`, `3364`, `3424`, `346e`, `349c`, `34d6`, `34e4`, `34e6`, `34ec`, `34ee`, `34f4`, `350e`, `3512`, `3522`, `3dc0`, `90aa`, `90b6`, `90ba`, `90c4`, `90c8`, `90ea`, `9106`, `9282`, `931a`, `9326`, `cfe2`, `d784`, `db30`, `df04`, `e20e`, `e92c`, `e974`, `ec3e`, `ecce`, `ee4c`, `f15e`, `11c98`, `1243a`, `1282c`, `12b36`, `12d86`, `130d8`, `13270`, `135a2`.

- [F] 입력 recorder `349c..3520`(`3360`/`3364` 경유)은 ROM WORD `000180`=0이어서 도달 불가다(하단 정정 절 참조).
- [I] pause/menu 요청 `9086..932e`(BYTE `100012`=2 게임 mode와 start edge), menu callback 가드 `931a`, aux `f44..f52`, TRAP `fee`는 가드 또는 다단계 입력 상태로만 도달한다. 선언된 단일 frame 편집이 만들지 못했다.
- [F] 미커버 47개 중 Duff 진입 7개(`leaders.json` `duff` 배열과 대조): `e20e`, `ec3e`, `ecce`, `f15e`, `12b36`, `130d8`, `135a2`.

## 미확인·한계

- [U] 실제 LSPC raster 값, 입력 타이밍, vblank/IRQ 발생 값은 선언값이다. 자연 seed는 `100017`=0, `104cd4`=0, `100012`=`10fdaf`=0이며 host API 산출물이다. vblank 대기는 변종/fixture에서만 나타난다.
- [U] controller 본체(`c52a`/`c66a`)는 실행하지 않았다. controller 효과에 대해 말하지 않는다. C1/C2 선언(D9)은 별도.
- [U] leader 커버리지는 TB 바이트 범위 기준이며 명령 단위 hit가 아니다.
- [U] 독립 모델은 head와 호출하는 routed callee만 덮는다.
- [U] 합성 fixture 탐색 과정에서 Unicorn이 일부 탐색 상태에서 SIGABRT로 종료한 적이 있다. 납품 fixture 195개에는 해당 상태가 없다. 원인은 분석하지 않았다.
- [U] H 시작 CCR은 SR `2000`(CCR 0)로 선언했다. 원본 CCR을 읽는 head라면 차이가 날 수 있으나 native CCR은 사용하지 않는다.
