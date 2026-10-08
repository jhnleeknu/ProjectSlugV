# Animation 실제 bank 상태 보존 계약

Baseline `35aa5d5`. 전체 opcode40 연결에 필요한 persistent 장치 상태를 먼저 추가한다. 이는40을bank2전용으로축소하는구현이아니며,40원본조회·리소스연결은후속단계다. canonical BE SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정 CPU49fc6 및4a33c/4a354,4a426/4a43e는같은ROM파일offset이다.

## C++ 상태와 전환

`AnimationExecutionState.current_bank_base`는std::uint32_t 물리ROM byte base이며기본값200000이다. saved_bank WORD(복귀용RAMshadow)와별개다. 이단계에서는current_bank_base의임의uint32입력을허용하되, 실제ROM읽기연결시도달한물리span의지원범위를검사한다. fresh49fc6은원본PVC쓰기때200000으로대체하므로입력값에서bank를추론하지않는다. unused/hold 상태는도달하지않은ROM읽기검사를선행하지않는다.

현재animation의PVC함수는2ffff2←WORDvalue,2ffff0←0의완전한쌍만발행한다. 두번째쓰기후의최종bank_base는100000+((value&7fff)<<8)이다. pinned neogeo.cpp의write_bankprot_pvc는두쓰기각각get_bank_base를호출한다. 첫ff9쓰기의get_bank_base가저장ff9를7fff로mask하므로, 두번째ff8=0쓰기는이미mask된ff9를사용한다. 첫쓰기의순간bank와쌍완료후bank를혼동하지않는다. raw출력port WORD는원래value&ffff그대로유지한다. 일반적인임의PVC쓰기전체를지원한다는뜻이아니다. 이쌍을발행할때current_bank_base도갱신하며RAMshadow변경만으로갱신하지않는다.

- zero_bank/초기진입/terminal은value1000이므로current_bank_base200000.
- draw/callback복귀는원본의WORDshift값을그대로PVC에쓰고그값으로bank를갱신한다. shadow→shift계산을다시추측하여별도계산하지않는다.
- phase1/2/3에서callee대기·hold는실제쓰기없으므로현재bank유지. 정상복귀후원본PVC쌍이currentbank를갱신한다.
- phase4직접sound는fresh/hold/release에PVC복귀가없으므로기존currentbank를보존한다. 뒤terminal을실행하면그terminal의PVC에의해200000이된다.
- 실패시새필드도RAM/state/carry/ports/external_reads와함께rollback한다. 원본레지스터와혼동하지않는다. API overload수는유지한다.

## CLI와 검증 규격 이행

별도bank전용CLI를만들지않고두기존CLI에필드를추가한다. 공통numeric순서는기존SAVED_LIST_END 바로뒤에CURRENT_BANK_BASE를추가한다. 일반CLI는22numeric/23JSON, soundCLI는공통22numeric 뒤callback4와external1로27numeric/28JSON이다. 모든Python FIELDS/initial/expected/parse와명시적argv offset을같이이행한다. 암묵적으로bank를기본값으로채우는구schema fallback을만들지않는다.

각native기대값은shadow가아니라실제관측ports의PVC쌍으로도출한다. 새invocation과동일CPU재개를구분하여incoming bank에서쌍의완료마다갱신한다. 기존native관측에bank가직접기록되지않은경우"pinnedPVC수식과실제ports에서도출"이라고명시하고새native bank-chain관측으로대기중보존을확인한다. 원본의기존RAM/register/trace파일을수정하지않는다. 기존report currentSHA는스키마이행후다시생성한다.

MS5D kind2 routing과opcode40 데이터읽기는이계약에서완료라고주장하지않는다. current bank를ROM크기로wrap하거나RAMshadow와동일시하지않는다. 모든callbacks가bank를변경하지않는다고가정하지않는다.
