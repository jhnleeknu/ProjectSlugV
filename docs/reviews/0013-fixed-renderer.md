# 고정 레이어 리뷰

기준b57cab8. 메인 에이전트가 pinned MAME fixed-layer column-major 주소, 타일/팔레트 bit 구분, nibble 읽기, 투명 픽셀의 배경 보존을 확인한 뒤 C++ 구현을 위임했다. 입력 전체 검증 후에만 frame을 수정하며 palette/frame alias는 palette snapshot으로 처리한다. 테스트는 최대타일4095·slot15·transpose·투명도·잘못된 입력의 무변경을 확인한다.

원본 fixed ROM을 독립적으로 읽어 모든81920픽셀 word 일치를 확인했다. 기존 원본CPU write trace 및 MS5T/MS5P 리소스를 사용한다. CLI의 slot0 매핑 설명을 이미 원본에서 확인된 근거와 일치하도록 수정했다.

색상 reference는 고정 MAME의 원본 함수들을 컴파일하여 조회표를 구했다. BSD-3 고지 추가. 확인용 PNG를 직접 열어 글자 배치를 점검했다. 실제 부팅 화면과 일치한다고 주장하지 않는다.

검증: make all test; verify_fixed_renderer.py; inspect_color_reference.py; preview_fixed_frame.py. 소스·도구·문서만 커밋하고 원본/추출물/PNG는 제외한다.
