# 메뉴 입력 우선순위와 플레이어 출처

프로그램 SHA256 `29112a94b5c073de95919ab4efbc75427287739eab794ef442d2aa7c886c860f`. 고정CPU/파일a472부터행동진입점까지의판정단계다. 실제물리버튼의이름은별도입력수집분석이필요하다.

현재슬롯+d bit0이플레이어1의RAM4cba,bit1이플레이어2의RAM4cc0을허용한다. 두byte에서우선순위0/1/2/3/5/4순으로처음존재하는bit를택한다. bit6/7은이단계에서무시한다. 같은우선순위를누른플레이어는source1/2로합쳐RAM7f1a에기록한다. 따라서한쪽의높은우선순위는다른쪽의낮은우선순위보다먼저선택된다. 입력없음은7f1a=0이다.

| 입력bit | 원본분기 | 판정결과 |
|---|---|---|
| 0 | a566 | 이전항목방향 |
| 1 | a574 | 다음항목방향 |
| 2 | a596 | event1 |
| 3 | a5a0 | event2 |
| 5 | a58c | event4 |
| 4 | a582 | event3 |
| 없음 | a5ce | 없음 |

이전/다음은후속a216에서선택가능항목을찾는다. event는후속a5aa에서9b3e로전달한다. 이번C++API는이단계들을실행하지않으며판정결과만반환한다. UI버튼명과event의게임별의미를추측으로확정하지않았다.

`select_menu_input`은RAM65536바이트와정렬된current pointer107e0e..107efe를검사하고RAM7f1a및MenuInput(kind,event,sources)을갱신한다. 실패시RAM과출력을보존한다. head는원본이이단계에서읽지않으므로검사하지않는다.

```
make all test
make build/menu_input_table
.venv/bin/python tools/verify_menu_input.py
build/select_menu_input INPUT_RAM OUTPUT_RAM OUTPUT_ACTION
```

ACTION은진단용kind/event/sources의3byte다. 검증은원본a472에서실제분기대상에도달하면멈추며행동본문은건너뛴다. 두입력의256×256조합과enable mask0/1/2/3/255,총327,680조건에서C++결과표와일치했다. 원본의RAM쓰기hook은7f1a초기화와선택source쓰기외의변경이없음을검사했고C++표생성기는매호출전체RAM을비교했다. 전체기존검사와오류보존검사통과.

이는메뉴입력판정복원이다. 실제항목이동·callback처리·전체a370프레임및게임입력도달성검증은남아있다.
