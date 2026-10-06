# 하드웨어 색상 변환 리뷰

기준3c7ba53. 생성된32×4 표의 원본 해시, 색상 word bit mapping, shadow/dark 열, RGB byte 순서를 메인 에이전트가 검토했다. reference는 원본 MAME palette 쓰기 함수와 저항망을 실행하므로 엔진 함수의 재작성만 서로 비교한 테스트가 아니다.

65536word × normal/shadow 두 모드 전체 RGB 일치. reference의 두 bank도 같은 결과다. CLI input/output inode 보호, 홀수/빈 입력 및 잘못된 모드 거부, 크기 overflow 검사를 검토했다. strict C++11 빌드와 make all test 통과. 확인용 PNG가 같은 C++ 변환을 사용하도록 중복 Python 변환을 제거했다.

하드웨어 모델 조회표는 코드에 포함하며 ROM·게임 추출물은 포함하지 않는다. 실제 CRT 및 시점에 따른 화면 비교는 이 검증 범위 밖이다.
