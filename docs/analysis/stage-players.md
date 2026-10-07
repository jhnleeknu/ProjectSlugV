# Stage player 원시 조회 창

## 원본과 주소 계산

원본 canonical decrypted 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`다. 아래 주소는 첫1MiB의 고정 ROM CPU 주소이며 canonical 파일의 같은 오프셋이다. RAM/MMIO와 banked 주소는 별도로 취급한다. 주소·필드 값은16진수이며 바이트·반복 개수는10진수다.

메인이 확정한476dc의 조회는 A6+7c.byte(stage)와 A6+7d.byte(area)를 사용한다. Stage가6..8이면476d0의3-long pointer 표에서 index=stage−6을 고르고, 다른 byte는 첫 pointer를 고른다. 그 pointer에 unsigned area byte×4를 더한 주소에서 BE16 두 word를 순서대로 읽는다. Pointer는476bc/476c4/476cc다. 최대 주소는476cc+255×4이고 두 word까지 포함한 exclusive end는47acc다.

조회 가능한 원시 창은 `[476bc,47acc)`의1040바이트다. **이1040바이트가 원본 논리 테이블 길이라는 주장은 하지 않는다.** 앞20바이트만 아래 다섯 pair로 분류하고, 다음12바이트는 pointer 표다. 그 뒤에는 원본 명령 코드가 포함된다. 임의 area byte로 pointer나 code에 겹쳐 읽을 수 있는 바이트까지 보존하며, 자연 실행에서 그런 area가 사용됐는지는 미확인이다.

| pair CPU 주소/ROM 오프셋 | word_00 | word_02 |
| --- | --- | --- |
| 476bc | 0000 | ffff |
| 476c0 | 0003 | ffff |
| 476c4 | 0001 | ffff |
| 476c8 | 0002 | 0001 |
| 476cc | 0004 | ffff |

Word의 게임 의미나 callback 효과는 이 원시 field 목록만으로 확정하지 않는다. Packer는476dc..4770a의 stage/area 연산·pointer 조회·첫 word 읽기와47724의 두 번째 word 읽기 명령 바이트를 pin한다. 명령 근거와 전체 source hash를 함께 검사하되 자동 역어셈블을 전체476dc 함수 분석 완료로 취급하지 않는다.

## MS5D와 재생성

`tools/pack_stage_players.py`는 기존 MS5D v1 kind1을 사용한다. Header32바이트와 raw payload1040바이트를 합친 container는1072바이트다. Stable ID는 `stage-players:000476bc`이며 출력은 `extracted/runtime/stage_players.ms5d`와 `stage_players.manifest.json`이다. Manifest는 source CPU/ROM offset, exclusive end, source/payload/container hash, leading pairs, pointer 표와 주소 계산, code overlap 및 미확인 범위를 기록한다. 원본과 추출 게임 데이터는 Git에 추가하지 않는다.

Payload SHA256은 `25428ef0315eda68ca0e772c8bdba8beaed38c831b835bf866a866e1724b3391`, container SHA256은 `9248616256431f9e81b27ab938bf2d6cc8e108006b7f032929babfa8c1c604e9`다. C++ 소비는 기존 `FixedDataResource`/`load_fixed_data_resource` 포맷을 사용하며 별도 schema를 만들지 않는다. Player wrapper가 이 리소스를 직접 소비하며 독립 native 동등성 결과는 아래 최종 관측 범위에서 확인했다.

실제 재생성 및 합성 검사는 다음 명령으로 수행했다.

```text
.venv/bin/python tools/pack_stage_players.py
.venv/bin/python -m unittest tools.tests.test_stage_players_resource -v
```

Packer는 전체8MiB 길이·canonical SHA, 조회 명령 evidence, payload 길이·leading pairs·pointer 표·payload SHA를 확인한 뒤 container header/CRC/payload roundtrip을 검사했다. 합성 테스트7개가 모든 stage byte의0/1/255 area 주소, 최대 end, 잘린 범위, source SHA, pair/pointer/code/evidence 변경, header schema·CRC·길이 및 CRC를 다시 맞춘 payload 변경을 확인했다. 모두 통과했다. Tracked 테스트는 원본 전체 창을 포함하지 않고 합성 bytes로 source/payload pin을 대체한다.

## Player API와 세 지원 진입

Baseline은 `5e896cd`다. 생성된 `engine/include/ms5/stage_players.h`와 `engine/src/stage_players.cpp`를 읽고 아래 계약을 대조했다. `StagePlayersState`는 전체32bit D0/D1/D3/A6를 운반한다. 모든 API는 정확한64KiB RAM을 요구하고 candidate RAM/state/ports에서 수행한 뒤 성공 시 게시한다. 늦은 두 번째 player 오류나 random pointer 오류도 앞선 restart/removal과 포트까지 보존한다. 다른 레지스터·CCR·stack 및 자연 호출 시점은 노출 계약 밖이다.

| 원본 진입/범위 | API | 종료 |
| --- | --- | --- |
| 47742 | `configure_stage_player` | 원본477a0의 RTS에 대응하는 단일 player 설정/제거 |
| 476dc | `configure_stage_players` | stage/area pair 조회와 두 gate 처리 후 원본 wrapper RTS |
| 479ba..479d0 | `begin_stage_players` | wrapper를 조건부 실행하고479d0 후속 본문 직전 |

### 단일 player47742

D0.lowword가0이면 고정100cb8, 그 외에는100da8을 선택한다. D0 전체나 lowbyte만 비교하지 않는다. 이 API는 caller A6를 dereference하지 않고 보존하므로 wrapper의 정렬/span 검사를 무조건 적용하지 않는다.

D1.lowword는 먼저 signed로 판정한다. Bit15가 켜진 음수는 제거 경로다. 원본2a48의 nonzero-depth TRAP은 API에서 오류로 거부하며, 지원하는 depth0 경로는 기존 제거 helper로 연결한다. 제거 반환 D0/D1/D3와 ordered watchdog 포트를 유지한다. 음수ffff를 random의 큰 unsigned값으로 처리하지 않는다.

비음수이면 고정 object callback을 검사한다. Callback=270e인 inactive object는 기존 `restart_static_object`로 callback1d1f4를 설치한다. 원본에 맞춰 저장했던 caller D0.word를 object+78.word에 복구하고 `initialize_game_object`의1bd2e 초기화를 연결한다. Callback!=270e인 경우는 재시작하지 않는다. Callback0도 비활성270e와 같다고 취급하지 않는다.1d1f4 body를 이 API가 실행하지 않는다.

저장한 D1.word를 D0.lowword로 복원할 때 그 시점의 D0.highword를 보존한다. 이 비음수 경로에서 unsigned word가4 이상이면 기존49a58 `next_random`을 호출하고 D0.lowword를3으로 AND한다. 그 결과 word를 object+76에 쓴다.0..3은 직접 저장한다. Signed 음수 제거 판정과 이후 unsigned>=4 판정을 하나의 비교로 합치지 않는다. Random cursor 검증 실패는 전체 transaction 오류다.

### 두 gate와 원시 pair wrapper476dc

Wrapper는 aligned completec4-byte A6 span과 exact source CPU/ROM476bc,1040-byte resource를 요구한다.476d0의 세 pointer 값도 확인한다. Stage/area를 LIVE object+7c/+7d.byte에서 읽고 위 주소 계산으로 pair 위치를 정한다. 첫 gate는1009a8, 둘째 gate는100a6c의 callback long이다. 각 gate에서 callback=270e일 때만 해당 단일 player 함수를 호출하며, 그 외에는 호출을 생략한다. Callback0도 여기서는 skip이다. 첫 helper 뒤 두 번째 gate를 LIVE RAM에서 검사한다.

조회가 만든 D0 전체는 area×4다. 각 BE16 word를 D1.lowword에 읽을 때 highword를 보존한다. Gate가 호출되면 MOVEQ0/1에 대응해 D0 전체를 player index로 만들고 단일 helper 반환을 운반한다. 두 gate 모두 생략해도 두 번째 원시 word는 D1.lowword에 읽힌다. 첫 player helper의 D1/D3 변화는 두 번째 처리에 이어지므로 입력 register를 매 단계 초기화하지 않는다. A6는 wrapper와 단일 API 모두 보존한다.

Resource의1040바이트는 원본8bit area가 주소로 접근할 수 있는 창이다. API가 전체 창을 읽을 수 있도록 보존한 사실이나 합성 lookup 검사는 앞의 다섯 known pair가 실제 gameplay에서 사용 완료됐다는 근거가 아니다. Pointer 표 이후 code-overlap pair도 삭제하거나 대체하지 않는다. API shape 검사와 packer의 canonical raw SHA 검증은 구분한다.

### 준비 caller479ba..479d0

Caller는 RAM10d681.byte=ff를 먼저 기록한다. 이어 D0.lowbyte를 `3 & RAM10d684.byte`로 만들고 나머지24bit를 보존한다. 결과 byte가 비영일 때만 wrapper를 호출한다.0인 skip 경로는 D1/D3/A6를 보존하고 A6/table wrapper 검사를 수행하지 않는다. Called 경로가 실패하면 앞선 d681/D0.lowbyte 변경도 rollback한다. 이 순서를 word 전체0 검사나 무조건 resource/span 검사로 바꾸지 않는다.

## CLI와 최종 검증

CLI 형식은 다음과 같다.

```text
build/step_stage_players ENTRY D0 D1 D3 A6 INPUT_RAM OUTPUT_RAM OUTPUT_PORTS TABLE_MS5D
```

ENTRY는47742/476dc/479ba 중 하나다. JSON은 `d0/d1/d3/a6/writes`를 반환한다.479ba 모드는479d0 본문 직전에 끝나지만 가상 caller PC를 JSON에 만들지 않는다. CLI는 모든 진입에서 MS5D loader와 path/inode alias 검사를 수행한다. 단일/skip API가 table을 소비하지 않는 경우도 CLI가 resource를 읽는 것은 host 입력 계약이며 원본의 추가 ROM 읽기로 표현하지 않는다.

최종 `artifacts/stage_players/verification.json` SHA256은 `7d82d2427746eff1edea0e1f3659807d1f84db2e6a6327210dae4ef4e7235e77`다. 실제 보고서를 읽어 원본1899조건·오류 보존42조건·ordered 포트380개, 전체64KiB RAM/D0/D1/D3/A6 일치를 확인했다. RTS stack endpoint도 일치했다. 원본 code 변경0이며 검증 binary SHA256은 `f2acbf26fdd54d496212b644644fa9e0c0697789dec370019adbcddb3da02740`다. 메인의 CPU context 재설정 제거 리뷰를 반영한 최종 session5270이 exit0으로 끝났다.

Known leading pair 조건80개는 stage/area `(6,0),(6,1),(7,0),(7,1),(8,0)`을 대상으로 gates와 player actions를 비교했다. 별도160조건은 pointer/code-overlap pair의 통제된 fixture이며 자연 사용이 입증됐다고 표현하지 않는다. 모든 stage byte의256조건과 세 pointer 각각 모든 area byte의768조건은 두 gate를 활성 상태로 두어 helper 호출을 건너뛰고 원본 pointer/window 읽기를 분리 검증했다. 모든 caller mask byte256조건, signed 제거·unsigned random·callback0·실제 palette/coordinate 정리와 LIVE area alias도 포함했다. 이 분류를 논리256-area table의 게임 동작 완료 주장으로 합치지 않는다.

실제 CLI RAM/full register 출력을 운반하는 RNG 승계6시퀀스는 각각4호출이다. 후속 호출의 D1.lowword=4 지정은 명시적 host 입력이며 다른 반환 bits와 RAM은 actual output을 유지한다. 실제 준비 CLI→player caller 연결2조건은 mask0/3에서 원본 predecessor와 caller의 같은 CPU context를 유지했다. A5/A7/SR나 외부 return stack을 재초기화하지 않았으므로 독립 fixture 두 번의 비교로 이 연결을 대체하지 않는다. 자연 scheduler나 callback body를 실행한 결과는 아니다.

전체 `make -j3 all test` 로그 `artifacts/stage_players_build_test.log`에서 Python111검사·C++93 test executable 실행과 warning/error0을 확인했다. 메인이 빌드 성공을 확인했다. 기존 `artifacts/game_objects/verification.json` 회귀149조건·오류24조건도 통과했으며 SHA256은 `c239a5619c6e929f2cee2ca6f65ccf93635e6f7f35e61d751bedee361d9b75f9`다.

Natural callback1d1f4 player body 실행, 원본 area의 자연 reachability,479d0 후속 본문·자연 scheduler 및 전체 stage/player/gameplay는 아직 미완료다. A7 endpoint 관측을 stack 전체나 기타 레지스터/CCR의 일반 동등성 계약으로 확대하지 않는다.
