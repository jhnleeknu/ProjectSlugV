# 연결 오브젝트 제거의 후속 분석

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 아래 ROM CPU 주소는 고정 파일 오프셋과 같다. RAM 절대 주소는100000..10ffff다. 메인이 원본 명령을 읽어 해석했으며 아직 linked removal C++나 원본 비교를 완료하지 않았다.

## 299c와 보류된 제거

299c는A5=108000을 설정하고 입력D0.byte를 watchdog300001에 쓴다.2782는8ff4의 팔레트 해제 뒤c3fa를 호출하며,c3fa는46ef4를 호출한다. 기존 `restart_static_object`에 팔레트/좌표 정리와 필드 리셋 구현이 있지만 +10.word=0 정적 오브젝트만 지원한다.

정리 후299c는현재A6.callback=270e로 표시한다. +10.word가0이면A0=A6으로271c에 tail branch한다. nonzero이면287e에서 다음 노드의 +10.word와 현재 값을 unsigned 비교한다. 현재 depth가다음 depth보다 작으면29fe로 반환한다. 이때 노드가 리스트에 남아 있으므로 callback270e는 즉시 free를 의미하지 않는다. 다음 노드가 더 깊은 동안 반환을 보류하는 구조로 해석된다.

현재 depth>=다음 depth이면271c로 필드를 리셋하고, A0=현재.previous/A1=현재.next를 읽어 next.previous=previous와 previous.next=next를 쓴다. 현재.next에 freehead104c9c를 넣고 freehead를현재로 바꾸며 freecount104ca0.word를 증가시킨다. A6=previous로 이동한다. 이전 노드도 callback270e이고 depth!=0이면29c0부터 반복한다. 이 반복에서는 앞의 watchdog·팔레트/좌표 해제를 다시 실행하지 않는다. 그래서 제거 요청과 실제 free-list 복귀를 구분해야 한다.

## 하위 제거와 호출자

2a0a는현재 depth를D0.word에읽고 A6=next로 이동한다. 현재로부터 보관한 depth>=이동한노드.depth면 그 노드의previous로A6를돌리고RTS한다. 더 깊은 노드이면299c를호출하고2a0a부터반복한다.299c 자체가A6를 바꿀 수 있으므로 최초 부모 포인터나 최초depth를 매 반복마다 강제로 복원하면 원본과 달라질 수 있다.

2a84는입력A6와A0 모두depth0인지검사한다. 원본은위반시TRAP15다. A6를저장하고A6=A0로이동해2a0a와299c를순서대로실행한뒤입력A6를복원한다. c4cc는3dce→2a0a를실행하고 A6.next부터고정sentinel100820까지순회하며각노드에2a84를호출한다. 저장한현재노드의live next를호출후읽으므로사전에고정목록을만드는것과동일하다고가정하지않는다.

기존 API재사용 후보는 `reset_object_fields`, `release_palettes`, `update_position`, `restart_static_object`다. field reset은 +4/+8/+c/+10 링크·depth를 보존한다. linked path 구현 시 live read/write 순서, cascade, 비정상순환의오류처리, watchdog순서, 반환레지스터를추가검증해야한다. source의 정적분기분석만으로 실행동등성을 주장하지 않는다.

## 목록 재생성

`python3 tools/inventory_object_removal.py`는5개명시진입의59명령후보/22제어참조와5개helper후보를기록한다. 보고서 `artifacts/object_removal/report.json` SHA256 `3e904a609175dfe0121310ce69a8503d41b0d83dd758af4188c43c6bdb45ee69`. 선형RTS도달은모든분기/함수의동작완료증거가아니다. 문서/엔진텍스트참조는재사용후보이며동등성증거가아니다. 다음구현에서이경계를원본실행으로확인한다.
