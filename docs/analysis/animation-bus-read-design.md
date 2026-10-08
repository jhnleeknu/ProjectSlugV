# Animation40의 주소 계산·버스 읽기 설계 근거

Baseline `e40334b`. 원본 handler는 고정 CPU/ROM offset `4a382..4a3ac`, 프로그램 SHA256은 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`이다. 구현 계약을 확정하기 위한 분석 문서이며, 새 C++40 지원이나 전체 실행 통합을 선언하지 않는다.

## 주소 계산과 실제 메모리의 구분

명령의 주소 레지스터 값은 32비트로 보존하고, signed WORD index를 더한 결과 역시 32비트 연산으로 다뤄야 한다. 외부 메모리 선택은 별도 24비트 bus 주소다. 이 구분 없이 A2 자체를24비트로 잘라 저장하면 이후 레지스터 결과가 바뀐다.

제조사 manual의1.1절은 MC68000의16비트 data bus와24비트 address bus를,2.3절은32비트 address register를 설명한다.2.4절에서 LONG의 두 WORD 위치는 n과n+2이고 WORD/LONG은 짝수 주소에 놓인다. 따라서 메모리 영역 경계도 각 WORD의 bus 주소를 기준으로 분류해야 한다. [MC68000 User's Manual](https://www.nxp.com/docs/en/reference-manual/MC68000UM.pdf), PDF12·18·19·30쪽. 아래 Unicorn 검사만으로 물리 bus cycle을 검증했다고 주장하지 않는다.

`probe_m68k_bus_alias.py`는 원본 ROM을 사용하지 않는 합성 backend 검사다. 설치된 Unicorn2.1.4, M68000 모델에서 다음27조건을 별도 process로 실행했다.

- 같은 ctypes backing을16개 RAM mirror에 연결하면 host와 CPU 쓰기가 모든 alias에서 일치한다. CPU 객체에도 backing 소유자를 보관한다.
- stack1feffc는 canonical RAM10effc를 가리키며 push도 alias에 반영된다.
- LONG10fffe는 내부64KiB mirror 경계를, LONG1ffffe는 RAM→bank 경계를 넘어 두 영역의 bytes를 읽는다.
- WORD/LONG indexed 주소 가산은 시험한32비트 wrap을 재현한다.
- logical1200000과200000은 다른 매핑을 읽었고, logical2200000은 low24 주소로 자동 fallback하지 않았다. 시험한 경로에서 자동24비트 bus mask가 없었다.
- LONG 경계 읽기도 hook은 size4 접근 하나로 보고했다. hook 건수를 실제16비트 bus cycle 수라고 해석하면 안 된다.

메인과 독립 Sol이 결과를 재실행·검토했다. backing 수명 문구를 넘어 실제 소유권도 보장하도록 CPU 객체에 owner를 추가하고 다시27조건을 실행했다. 최종 report SHA256은 `95c90360d8256c5d6d33808740db74848a4a4b258544bb9f4b6858e904a0dba1`이다. 원본 handler observer는 이 backend 한계를 명시적으로 다뤄야 한다.

## 리소스 선택 정책

MS5D v1과 `FixedDataResource`의 기존 metadata로 fixed와 banked 창을 구분할 수 있다. 구조체에 kind 필드가 없어도 두 유효 주소 영역은 겹치지 않는다. CLI는 header의 실제 kind를 읽고1/2 loader로 분기해야 하며, filename 추측이나 kind1 실패 후 무조건 재시도를 사용하지 않는다.

각 reached WORD를 다음과 같이 처리하는 설계를 검토한다.

| bus 주소 | 원본 메모리 | 필요한 입력·검증 |
|---|---|---|
| 000000..00007f | cart/BIOS vector 선택 | 명시적인 vector view; 단순 raw ROM 소유만으로 선택 상태를 증명하지 않음 |
| 000080..0fffff | fixed cartridge ROM | kind1의 유일한 완전한 WORD 범위 |
| 100000..1fffff | 64KiB RAM mirror | canonical index는 bus&ffff |
| 200000..2fdfff | 선택된 cartridge bank | current_bank_base와 physical metadata를 먼저 대조한 kind2 범위 |
| 2fe000..2fffff | PVC cart RAM | 별도 장치 상태; ROM 창으로 대체하지 않음 |
| 기타 | 장치·BIOS·미매핑 영역 | 실제 장치별 계약 필요; 임의0이나ROM bytes로 대체하지 않음 |

bank가 다른 동일 CPU 창은 서로 충돌하지 않는다. active bank를 먼저 고른 후 overlap/partial/ambiguous coverage를 검사한다. loader는 odd resource 시작도 허용하므로, 짝수 WORD를 담은 odd-start 창을 일괄 거부하는 기존 scene reader 조건을 복사하면 안 된다.

LONG은 높은 WORD와 낮은 WORD를 각각 해석해 결합한다. WORD마다 유일한 완전한 리소스 범위를 요구하면 서로 인접한 두 WORD 창이나 fixed→RAM, RAM→bank 경계도 표현할 수 있다. partial WORD를 여러 byte 조각에서 임의로 조합하는 것과는 다르다. 물리 ROM 범위를 넘는 bank 읽기는 ROM 크기로 wrap하지 않는다.

기존 loader의2ffff0 상한이 실제 MS5 PVC 시작2fe000을 대체하지 않는다. 또한 `current_bank_base` 하나는 전체 PVC cart RAM의 내용이나 BIOS vector 선택 상태를 표현하지 않는다. 장치 입력을 어떻게 공유할지는 상위 hardware 계층과 함께 확정해야 한다. 현재 값에서 미확인 장치 메모리를 추측해서는 안 된다.

## 실제 ROM에서 확인한 읽기 후보

아래는 실제 ROM bytes이지 자연적으로 실행된 script 증거가 아니다. first/second offset은 모두0이다.

| physical bank base | first CPU / physical offset | first LONG | second CPU / physical offset | second LONG |
|---|---|---|---|---|
| 200000 | 200004 / 200004 | 0022bd12 | 22bd12 / 22bd12 | 00007fff |
| 300000 | 200004 / 300004 | 00200008 | 200008 / 300008 | 0020013c |
| 400000 | 200004 / 400004 | 00205704 | 205704 / 405704 | 00208198 |
| 500000 | 200004 / 500004 | 0020011c | 20011c / 50011c | 00200800 |

bank3은 기존 scene_maps primary_root/primary_lookup MS5D를 재사용할 수 있다. 다른 세 bank의 위 최소 창은 새 추출이 필요하며 같은 kind2 규격으로 표현 가능하다. bank2 first050a는 fixed84를 가리키며 값은00000202이다. first22fa는RAM10000e, first22ec는mirror1e001c, first22f8는mirror120010을 가리킨다. 원본 pointer가 반드시 ROM을 가리킨다고 가정하지 않는다.

기존 caller 근거가 있는5개 script와 추가 initializer 조사에서는 신뢰할 opcode40 stream을 확보하지 못했다. raw byte40나 무관한 root/caller의 교차 조합은 유효 script로 채택하지 않았다. 이 조사 결과로40을 미사용이라고 결론내릴 수 없으며, 현재 원본 handler 관측은 명시적인 합성 입력으로 분리한다.

## 아직 필요한 통합 근거

원본 isolated handler는 stack을 사용하지 않으므로 coherent mirror 읽기 자체를 검증하기에 적합하다. 반면 whole49fc6는 실제 call stack 쓰기와 mirror alias가 함께 존재한다. 기존 별도 scratchstack 관측기를 그대로 확장하면 그 주소를 읽는40의 의미를 잘못 모델링할 수 있다. handler 관측과 전체 호출·대기 재개 관측을 구분하고, 실제 읽기가 stack에 닿는 조건 및 결과에 반영할 범위를 명시해야 한다. 명령 수를 늘리기 위해 이 문제나 PVC/vector 입력을 조용히 제외한 채 전체40 완료로 선언하지 않는다.

### whole-call stack alias의 구체적 근거

기존 bank-state native case0의14/03 복귀 후 S=`1feffc`에서 S-8은 operand 뒤 script pointer `10600a`, S-4는 outer A0 `100036`이다. 직접30 복귀 후에는 S-8이outer A0 `100036`, S-4가script pointer `10600e`이며 S-12에는return PC `4a2ec`가 남는다. 각 trace의 다음 dispatch `49ffe`에서 A7은S로 돌아온다.

40의 first offset `eff0`은 `200004-1010=1feff4=S-8`을 읽는다. 따라서 먼저 어떤 명령이 실행됐는지에 따라 이 주소에서 읽는 pointer가 달라질 수 있다. saved low byte 옆의 stack padding도 이전 frame의 잔여 bytes에 의존한다. 이는 handler를 실제로 실행한 새 성공 주장과 다르며, 기존 unpatched trace의 stack bytes와40 주소식을 결합한 구체적 alias 근거다.

C++의 기존 continuation metadata는 call stack 전체 RAM bytes를 저장하지 않는다. whole-call 비교에서 stack 영역을 제외하려면 그 영역을 의미상 데이터로 읽거나 쓰지 않는다는 조건도 확인해야 한다. 단순히 RAM diff를 mask하면40이 그 stack bytes를 읽어서 바꾼 D7·object field 차이는 해결되지 않는다. 따라서 완전한 mirrored RAM 동등성을 요구하는 연결에는 A7과 frame memory 효과를 모델링하거나, 다른 명시적인 상태 추상화와 적용 범위를 검증해야 한다. 이 문제를 원본에서 불가능한 입력이라고 단정하지 않는다.
