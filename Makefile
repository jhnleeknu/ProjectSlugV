CXX = clang++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra -pedantic -Iengine/include
PYTHON = .venv/bin/python

.PHONY: all test runtime-resources setup-tools
all: build/query_stage build/stage_state build/trace_table_text build/dispatch_menu_event build/push_menu build/navigate_menu build/select_menu_input build/draw_menu_text build/trace_direct_text build/step_menu_motion build/trace_menu_border build/init_menu build/measure_fixed_text build/check_menu build/read_control_request build/snapshot_palette build/setup_palette_fill build/transfer_palette_banks build/transfer_palette build/control_palette build/step_palette_frame build/prepare_palette build/palette_allocator build/step_animation_data build/step_animation_resource build/step_animation build/decode_animation_draw build/emit_composition_blocks build/emit_composition_variant build/configure_sprite_pool build/produce_sprite_queue build/prepare_sprite_queue build/radix_sprite_queue build/refresh_sprite_queue build/emit_composition_reverse build/sort_sprite_queue build/parse_sprite_scanline build/emit_sprite_resource build/check_tiles build/reset_object build/init_objects build/upload_palette build/init_palette build/check_palettes build/trace_fixed_text build/render_fixed_words build/convert_color_words build/render_text_scene build/update_position build/emit_composition build/emit_composition_refresh build/format_text

build:
	mkdir -p build

build/check_tiles: engine/src/tile_resource.cpp engine/tools/check_tiles.cpp engine/include/ms5/tile_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/tile_resource.cpp engine/tools/check_tiles.cpp -o $@

build/tile_resource_test: engine/src/tile_resource.cpp engine/tests/tile_resource_test.cpp engine/include/ms5/tile_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/tile_resource.cpp engine/tests/tile_resource_test.cpp -o $@

build/reset_object: engine/src/object_state.cpp engine/tools/reset_object.cpp engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_state.cpp engine/tools/reset_object.cpp -o $@

build/object_state_test: engine/src/object_state.cpp engine/tests/object_state_test.cpp engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_state.cpp engine/tests/object_state_test.cpp -o $@

build/init_objects: engine/src/object_lists.cpp engine/src/object_state.cpp engine/tools/init_objects.cpp engine/include/ms5/object_lists.h engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_lists.cpp engine/src/object_state.cpp engine/tools/init_objects.cpp -o $@

build/object_lists_test: engine/src/object_lists.cpp engine/src/object_state.cpp engine/tests/object_lists_test.cpp engine/include/ms5/object_lists.h engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_lists.cpp engine/src/object_state.cpp engine/tests/object_lists_test.cpp -o $@

test: build/stage_group_menu_test build/stage_catalog_test build/menu_debug_test build/menu_event_test build/menu_stack_test build/menu_navigation_test build/menu_input_test build/menu_text_test build/direct_text_test build/menu_motion_test build/menu_border_test build/menu_init_test build/text_measure_test build/menu_descriptor_test build/palette_fill_test build/palette_transfer_test build/palette_frame_test build/palette_prepare_test build/palette_allocator_test build/animation_data_test build/fixed_data_resource_test build/animation_resource_test build/animation_step_test build/animation_draw_test build/sprite_blocks_test build/sprite_pool_test build/sprite_producer_test build/sprite_prepare_queue_test build/sprite_radix_test build/sprite_refresh_queue_test build/sprite_queue_test build/sprite_scanline_test build/composition_resource_test build/tile_resource_test build/object_state_test build/object_lists_test build/palette_resource_test build/fixed_renderer_test build/text_resource_test build/formatted_text_test
	./build/formatted_text_test
	$(PYTHON) -m unittest discover -s tools/tests -v
	./build/stage_group_menu_test
	./build/stage_catalog_test
	./build/menu_debug_test
	./build/menu_event_test
	./build/menu_stack_test
	./build/menu_navigation_test
	./build/menu_input_test
	./build/menu_text_test
	./build/direct_text_test
	./build/menu_motion_test
	./build/menu_border_test
	./build/menu_init_test
	./build/text_measure_test
	./build/menu_descriptor_test
	./build/palette_fill_test
	./build/palette_transfer_test
	./build/palette_frame_test
	./build/palette_prepare_test
	./build/palette_allocator_test
	./build/animation_data_test
	./build/fixed_data_resource_test
	./build/animation_resource_test
	./build/animation_step_test
	./build/animation_draw_test
	./build/sprite_blocks_test
	./build/tile_resource_test
	./build/object_state_test
	./build/object_lists_test
	./build/palette_resource_test
	./build/fixed_renderer_test
	./build/text_resource_test
	./build/composition_resource_test
	./build/sprite_scanline_test
	./build/sprite_queue_test
	./build/sprite_refresh_queue_test
	./build/sprite_radix_test
	./build/sprite_prepare_queue_test
	./build/sprite_producer_test
	./build/sprite_pool_test

runtime-resources:
	$(PYTHON) tools/pack_stage_catalog.py
	$(PYTHON) tools/pack_menu_font.py
	$(PYTHON) tools/pack_control_menu_tree.py
	python3 tools/pack_tiles.py
	$(PYTHON) tools/pack_object_boot.py
	$(PYTHON) tools/pack_palettes.py
	$(PYTHON) tools/pack_text_scene.py
	$(PYTHON) tools/pack_compositions.py

setup-tools:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-analysis.txt

build/upload_palette: engine/src/palette_upload.cpp engine/tools/upload_palette.cpp engine/include/ms5/palette_upload.h | build
	$(CXX) $(CXXFLAGS) engine/src/palette_upload.cpp engine/tools/upload_palette.cpp -o $@

build/init_palette: engine/src/palette_state.cpp engine/tools/init_palette.cpp engine/include/ms5/palette_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/palette_state.cpp engine/tools/init_palette.cpp -o $@

build/check_palettes: engine/src/palette_resource.cpp engine/tools/check_palettes.cpp engine/include/ms5/palette_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/palette_resource.cpp engine/tools/check_palettes.cpp -o $@

build/palette_resource_test: engine/src/palette_resource.cpp engine/tests/palette_resource_test.cpp engine/include/ms5/palette_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/palette_resource.cpp engine/tests/palette_resource_test.cpp -o $@

build/trace_fixed_text: engine/src/fixed_text.cpp engine/tools/trace_fixed_text.cpp engine/include/ms5/fixed_text.h | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_text.cpp engine/tools/trace_fixed_text.cpp -o $@

build/render_fixed_words: engine/src/fixed_renderer.cpp engine/src/tile_resource.cpp engine/src/palette_resource.cpp engine/tools/render_fixed_words.cpp engine/include/ms5/fixed_renderer.h engine/include/ms5/tile_resource.h engine/include/ms5/palette_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_renderer.cpp engine/src/tile_resource.cpp engine/src/palette_resource.cpp engine/tools/render_fixed_words.cpp -o $@

build/fixed_renderer_test: engine/src/fixed_renderer.cpp engine/tests/fixed_renderer_test.cpp engine/include/ms5/fixed_renderer.h engine/include/ms5/tile_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_renderer.cpp engine/tests/fixed_renderer_test.cpp -o $@

build/convert_color_words: engine/src/hardware_color.cpp engine/src/color_lookup.inc engine/tools/convert_color_words.cpp engine/include/ms5/hardware_color.h | build
	$(CXX) $(CXXFLAGS) engine/src/hardware_color.cpp engine/tools/convert_color_words.cpp -o $@

TEXT_SCENE_SOURCES = engine/src/text_resource.cpp engine/src/tile_resource.cpp engine/src/palette_resource.cpp engine/src/fixed_text.cpp engine/src/fixed_renderer.cpp engine/src/hardware_color.cpp
TEXT_SCENE_HEADERS = engine/include/ms5/text_resource.h engine/include/ms5/tile_resource.h engine/include/ms5/palette_resource.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_renderer.h engine/include/ms5/hardware_color.h engine/src/color_lookup.inc
build/render_text_scene: $(TEXT_SCENE_SOURCES) $(TEXT_SCENE_HEADERS) engine/tools/render_text_scene.cpp | build
	$(CXX) $(CXXFLAGS) $(TEXT_SCENE_SOURCES) engine/tools/render_text_scene.cpp -o $@

build/text_resource_test: engine/src/text_resource.cpp engine/include/ms5/text_resource.h engine/tests/text_resource_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/text_resource.cpp engine/tests/text_resource_test.cpp -o $@

build/update_position: engine/src/position_state.cpp engine/include/ms5/position_state.h engine/tools/update_position.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/position_state.cpp engine/tools/update_position.cpp -o $@

build/emit_composition: engine/src/sprite_composition.cpp engine/include/ms5/sprite_composition.h engine/tools/emit_composition.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_composition.cpp engine/tools/emit_composition.cpp -o $@

build/emit_composition_refresh: engine/src/sprite_composition.cpp engine/include/ms5/sprite_composition.h engine/tools/emit_composition_refresh.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_composition.cpp engine/tools/emit_composition_refresh.cpp -o $@

COMPOSITION_HEADERS = engine/include/ms5/composition_resource.h engine/include/ms5/sprite_composition.h
build/emit_sprite_resource: engine/src/composition_resource.cpp engine/src/sprite_composition.cpp engine/tools/emit_sprite_resource.cpp $(COMPOSITION_HEADERS) | build
	$(CXX) $(CXXFLAGS) engine/src/composition_resource.cpp engine/src/sprite_composition.cpp engine/tools/emit_sprite_resource.cpp -o $@

build/composition_resource_test: engine/src/composition_resource.cpp engine/tests/composition_resource_test.cpp engine/include/ms5/composition_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/composition_resource.cpp engine/tests/composition_resource_test.cpp -o $@

build/parse_sprite_scanline: engine/src/sprite_scanline.cpp engine/tools/parse_sprite_scanline.cpp engine/include/ms5/sprite_scanline.h | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_scanline.cpp engine/tools/parse_sprite_scanline.cpp -o $@

build/sprite_scanline_test: engine/src/sprite_scanline.cpp engine/tests/sprite_scanline_test.cpp engine/include/ms5/sprite_scanline.h | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_scanline.cpp engine/tests/sprite_scanline_test.cpp -o $@

build/sort_sprite_queue: engine/src/sprite_queue.cpp engine/tools/sort_sprite_queue.cpp engine/include/ms5/sprite_queue.h | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_queue.cpp engine/tools/sort_sprite_queue.cpp -o $@

build/sprite_queue_test: engine/src/sprite_queue.cpp engine/tests/sprite_queue_test.cpp engine/include/ms5/sprite_queue.h | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_queue.cpp engine/tests/sprite_queue_test.cpp -o $@

build/emit_composition_reverse: engine/src/sprite_composition.cpp engine/tools/emit_composition_reverse.cpp engine/include/ms5/sprite_composition.h | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_composition.cpp engine/tools/emit_composition_reverse.cpp -o $@

SPRITE_REFRESH_SOURCES = engine/src/sprite_refresh_queue.cpp engine/src/sprite_composition.cpp engine/src/composition_resource.cpp
SPRITE_REFRESH_HEADERS = engine/include/ms5/sprite_refresh_queue.h engine/include/ms5/sprite_composition.h engine/include/ms5/composition_resource.h
build/refresh_sprite_queue: $(SPRITE_REFRESH_SOURCES) $(SPRITE_REFRESH_HEADERS) engine/tools/refresh_sprite_queue.cpp | build
	$(CXX) $(CXXFLAGS) $(SPRITE_REFRESH_SOURCES) engine/tools/refresh_sprite_queue.cpp -o $@

build/sprite_refresh_queue_test: $(SPRITE_REFRESH_SOURCES) $(SPRITE_REFRESH_HEADERS) engine/tests/sprite_refresh_queue_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SPRITE_REFRESH_SOURCES) engine/tests/sprite_refresh_queue_test.cpp -o $@

build/radix_sprite_queue: engine/src/sprite_queue.cpp engine/tools/radix_sprite_queue.cpp engine/include/ms5/sprite_queue.h | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_queue.cpp engine/tools/radix_sprite_queue.cpp -o $@

build/sprite_radix_test: engine/src/sprite_queue.cpp engine/tests/sprite_radix_test.cpp engine/include/ms5/sprite_queue.h | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_queue.cpp engine/tests/sprite_radix_test.cpp -o $@

SPRITE_PREPARE_SOURCES = engine/src/sprite_prepare_queue.cpp engine/src/sprite_queue.cpp engine/src/sprite_composition.cpp engine/src/composition_resource.cpp
SPRITE_PREPARE_HEADERS = engine/include/ms5/sprite_prepare_queue.h engine/include/ms5/sprite_queue.h engine/include/ms5/sprite_composition.h engine/include/ms5/composition_resource.h
build/prepare_sprite_queue: $(SPRITE_PREPARE_SOURCES) $(SPRITE_PREPARE_HEADERS) engine/tools/prepare_sprite_queue.cpp | build
	$(CXX) $(CXXFLAGS) $(SPRITE_PREPARE_SOURCES) engine/tools/prepare_sprite_queue.cpp -o $@

build/sprite_prepare_queue_test: $(SPRITE_PREPARE_SOURCES) $(SPRITE_PREPARE_HEADERS) engine/tests/sprite_prepare_queue_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SPRITE_PREPARE_SOURCES) engine/tests/sprite_prepare_queue_test.cpp -o $@

build/produce_sprite_queue: engine/src/sprite_producer.cpp engine/include/ms5/sprite_producer.h engine/tools/produce_sprite_queue.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_producer.cpp engine/tools/produce_sprite_queue.cpp -o $@

build/sprite_producer_test: engine/src/sprite_producer.cpp engine/include/ms5/sprite_producer.h engine/tests/sprite_producer_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_producer.cpp engine/tests/sprite_producer_test.cpp -o $@

build/configure_sprite_pool: engine/src/sprite_pool.cpp engine/include/ms5/sprite_pool.h engine/tools/configure_sprite_pool.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_pool.cpp engine/tools/configure_sprite_pool.cpp -o $@

build/sprite_pool_test: engine/src/sprite_pool.cpp engine/include/ms5/sprite_pool.h $(SPRITE_PREPARE_SOURCES) engine/src/sprite_refresh_queue.cpp engine/include/ms5/sprite_refresh_queue.h engine/tests/sprite_pool_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_pool.cpp $(SPRITE_PREPARE_SOURCES) engine/src/sprite_refresh_queue.cpp engine/tests/sprite_pool_test.cpp -o $@

build/emit_composition_variant: engine/src/sprite_composition.cpp engine/include/ms5/sprite_composition.h engine/tools/emit_composition_variant.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_composition.cpp engine/tools/emit_composition_variant.cpp -o $@

build/emit_composition_blocks: engine/src/sprite_composition.cpp engine/include/ms5/sprite_composition.h engine/tools/emit_composition_blocks.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_composition.cpp engine/tools/emit_composition_blocks.cpp -o $@

build/sprite_blocks_test: engine/src/sprite_composition.cpp engine/include/ms5/sprite_composition.h engine/tests/sprite_blocks_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/sprite_composition.cpp engine/tests/sprite_blocks_test.cpp -o $@

build/decode_animation_draw: engine/src/animation_draw.cpp engine/include/ms5/animation_draw.h engine/tools/decode_animation_draw.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/animation_draw.cpp engine/tools/decode_animation_draw.cpp -o $@

build/animation_draw_test: engine/src/animation_draw.cpp engine/include/ms5/animation_draw.h engine/tests/animation_draw_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/animation_draw.cpp engine/tests/animation_draw_test.cpp -o $@

ANIMATION_SOURCES = engine/src/animation_step.cpp engine/src/animation_draw.cpp engine/src/sprite_producer.cpp
ANIMATION_HEADERS = engine/include/ms5/fixed_data_resource.h engine/include/ms5/animation_step.h engine/include/ms5/animation_draw.h engine/include/ms5/sprite_producer.h
build/step_animation: $(ANIMATION_SOURCES) $(ANIMATION_HEADERS) engine/tools/step_animation.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_SOURCES) engine/tools/step_animation.cpp -o $@

build/animation_step_test: $(ANIMATION_SOURCES) $(ANIMATION_HEADERS) engine/tests/animation_step_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_SOURCES) engine/tests/animation_step_test.cpp -o $@

build/step_animation_resource: $(ANIMATION_SOURCES) $(ANIMATION_HEADERS) engine/src/animation_resource.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/animation_resource.h engine/tools/step_animation_resource.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_SOURCES) engine/src/animation_resource.cpp engine/src/fixed_data_resource.cpp engine/tools/step_animation_resource.cpp -o $@

build/animation_resource_test: engine/src/animation_resource.cpp engine/include/ms5/animation_resource.h engine/tests/animation_resource_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/animation_resource.cpp engine/tests/animation_resource_test.cpp -o $@

build/step_animation_data: $(ANIMATION_SOURCES) $(ANIMATION_HEADERS) engine/src/fixed_data_resource.cpp engine/include/ms5/fixed_data_resource.h engine/tools/step_animation_data.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_SOURCES) engine/src/fixed_data_resource.cpp engine/tools/step_animation_data.cpp -o $@
build/fixed_data_resource_test: engine/src/fixed_data_resource.cpp engine/include/ms5/fixed_data_resource.h engine/tests/fixed_data_resource_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_data_resource.cpp engine/tests/fixed_data_resource_test.cpp -o $@

build/animation_data_test: $(ANIMATION_SOURCES) $(ANIMATION_HEADERS) engine/tests/animation_data_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_SOURCES) engine/tests/animation_data_test.cpp -o $@

build/palette_allocator: engine/src/palette_allocator.cpp engine/include/ms5/palette_allocator.h engine/tools/palette_allocator.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_allocator.cpp engine/tools/palette_allocator.cpp -o $@

build/palette_allocator_test: engine/src/palette_allocator.cpp engine/src/palette_state.cpp engine/include/ms5/palette_allocator.h engine/include/ms5/palette_state.h engine/tests/palette_allocator_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_allocator.cpp engine/src/palette_state.cpp engine/tests/palette_allocator_test.cpp -o $@

build/prepare_palette: engine/src/palette_prepare.cpp engine/src/palette_resource.cpp engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/tools/prepare_palette.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_prepare.cpp engine/src/palette_resource.cpp engine/tools/prepare_palette.cpp -o $@

build/palette_prepare_test: engine/src/palette_prepare.cpp engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/tests/palette_prepare_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_prepare.cpp engine/tests/palette_prepare_test.cpp -o $@

build/step_palette_frame: engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/src/palette_resource.cpp engine/include/ms5/palette_frame.h engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/tools/step_palette_frame.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/src/palette_resource.cpp engine/tools/step_palette_frame.cpp -o $@

build/palette_frame_test: engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/include/ms5/palette_frame.h engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/tests/palette_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/tests/palette_frame_test.cpp -o $@

build/control_palette: engine/src/palette_control.cpp engine/include/ms5/palette_control.h engine/tools/control_palette.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_control.cpp engine/tools/control_palette.cpp -o $@

build/transfer_palette: engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/include/ms5/palette_transfer.h engine/include/ms5/palette_upload.h engine/tools/transfer_palette.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tools/transfer_palette.cpp -o $@

build/palette_transfer_test: engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/include/ms5/palette_transfer.h engine/include/ms5/palette_upload.h engine/tests/palette_transfer_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tests/palette_transfer_test.cpp -o $@

build/transfer_palette_banks: engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/include/ms5/palette_transfer.h engine/include/ms5/palette_upload.h engine/tools/transfer_palette_banks.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tools/transfer_palette_banks.cpp -o $@

build/setup_palette_fill: engine/src/palette_fill.cpp engine/src/palette_resource.cpp engine/include/ms5/palette_fill.h engine/include/ms5/palette_resource.h engine/tools/setup_palette_fill.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_fill.cpp engine/src/palette_resource.cpp engine/tools/setup_palette_fill.cpp -o $@

build/palette_fill_test: engine/src/palette_fill.cpp engine/include/ms5/palette_fill.h engine/include/ms5/palette_resource.h engine/tests/palette_fill_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_fill.cpp engine/tests/palette_fill_test.cpp -o $@

build/snapshot_palette: engine/src/palette_snapshot.cpp engine/include/ms5/palette_snapshot.h engine/tools/snapshot_palette.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/palette_snapshot.cpp engine/tools/snapshot_palette.cpp -o $@

build/read_control_request: engine/src/control_request.cpp engine/include/ms5/control_request.h engine/tools/read_control_request.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/control_request.cpp engine/tools/read_control_request.cpp -o $@

build/check_menu: engine/src/menu_descriptor.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_data_resource.h engine/tools/check_menu.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_descriptor.cpp engine/src/fixed_data_resource.cpp engine/tools/check_menu.cpp -o $@

build/menu_descriptor_test: engine/src/menu_descriptor.cpp engine/include/ms5/menu_descriptor.h engine/tests/menu_descriptor_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_descriptor.cpp engine/tests/menu_descriptor_test.cpp -o $@

build/measure_fixed_text: engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/tools/measure_fixed_text.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/measure_fixed_text.cpp -o $@

build/text_measure_test: engine/src/fixed_text.cpp engine/include/ms5/fixed_text.h engine/tests/text_measure_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_text.cpp engine/tests/text_measure_test.cpp -o $@

build/init_menu: engine/src/menu_init.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_init.h engine/tools/init_menu.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_init.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/init_menu.cpp -o $@

build/menu_init_test: engine/src/menu_init.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_init.h engine/tests/menu_init_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_init.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_init_test.cpp -o $@

build/trace_menu_border: engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_border.h engine/tools/trace_menu_border.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_data_resource.cpp engine/tools/trace_menu_border.cpp -o $@

build/menu_border_test: engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/include/ms5/menu_border.h engine/tests/menu_border_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/tests/menu_border_test.cpp -o $@

build/step_menu_motion: engine/src/menu_motion.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_motion.h engine/tools/step_menu_motion.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_motion.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_data_resource.cpp engine/tools/step_menu_motion.cpp -o $@

build/menu_motion_test: engine/src/menu_motion.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/include/ms5/menu_motion.h engine/tests/menu_motion_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_motion.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/tests/menu_motion_test.cpp -o $@

build/trace_direct_text: engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/tools/trace_direct_text.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/trace_direct_text.cpp -o $@

build/direct_text_test: engine/src/fixed_text.cpp engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/tests/direct_text_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_text.cpp engine/tests/direct_text_test.cpp -o $@

build/draw_menu_text: engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_text.h engine/tools/draw_menu_text.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/draw_menu_text.cpp -o $@

build/menu_text_test: engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_text.h engine/tests/menu_text_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_text_test.cpp -o $@

build/select_menu_input: engine/src/menu_input.cpp engine/include/ms5/menu_input.h engine/tools/select_menu_input.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_input.cpp engine/tools/select_menu_input.cpp -o $@

build/menu_input_table: engine/src/menu_input.cpp engine/include/ms5/menu_input.h engine/tests/menu_input_table.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_input.cpp engine/tests/menu_input_table.cpp -o $@

build/menu_input_test: engine/src/menu_input.cpp engine/include/ms5/menu_input.h engine/tests/menu_input_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_input.cpp engine/tests/menu_input_test.cpp -o $@

build/navigate_menu: engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/tools/navigate_menu.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/navigate_menu.cpp -o $@

build/menu_navigation_test: engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/tests/menu_navigation_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_navigation_test.cpp -o $@

build/push_menu: engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_stack.h engine/include/ms5/menu_text.h engine/include/ms5/menu_init.h engine/tools/push_menu.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/push_menu.cpp -o $@

build/menu_stack_test: engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_stack.h engine/include/ms5/menu_text.h engine/include/ms5/menu_init.h engine/tests/menu_stack_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_stack_test.cpp -o $@

build/dispatch_menu_event: engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tools/dispatch_menu_event.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/dispatch_menu_event.cpp -o $@

build/menu_event_test: engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tests/menu_event_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/menu_event_test.cpp -o $@

build/trace_table_text: engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/fixed_text.h engine/tools/trace_table_text.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/trace_table_text.cpp -o $@

build/menu_debug_test: engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_debug.h engine/tests/menu_debug_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_debug_test.cpp -o $@

build/query_stage: engine/src/stage_catalog.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/stage_catalog.h engine/tools/query_stage.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/stage_catalog.cpp engine/src/fixed_data_resource.cpp engine/tools/query_stage.cpp -o $@

build/stage_state: engine/src/stage_state.cpp engine/include/ms5/stage_state.h engine/tools/stage_state.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/stage_state.cpp engine/tools/stage_state.cpp -o $@

build/stage_catalog_test: engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/tests/stage_catalog_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/fixed_data_resource.cpp engine/tests/stage_catalog_test.cpp -o $@

FORMATTED_TEXT_SOURCES = engine/src/formatted_text.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp
FORMATTED_TEXT_HEADERS = engine/include/ms5/formatted_text.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/format_text: $(FORMATTED_TEXT_SOURCES) $(FORMATTED_TEXT_HEADERS) engine/tools/format_text.cpp | build
	$(CXX) $(CXXFLAGS) $(FORMATTED_TEXT_SOURCES) engine/tools/format_text.cpp -o $@

build/formatted_text_test: $(FORMATTED_TEXT_SOURCES) $(FORMATTED_TEXT_HEADERS) engine/tests/formatted_text_test.cpp | build
	$(CXX) $(CXXFLAGS) $(FORMATTED_TEXT_SOURCES) engine/tests/formatted_text_test.cpp -o $@

STAGE_GROUP_MENU_SOURCES = engine/src/stage_group_menu.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/formatted_text.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp
STAGE_GROUP_MENU_HEADERS = engine/include/ms5/stage_group_menu.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h
build/stage_group_menu_test: $(STAGE_GROUP_MENU_SOURCES) $(STAGE_GROUP_MENU_HEADERS) engine/tests/stage_group_menu_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_GROUP_MENU_SOURCES) engine/tests/stage_group_menu_test.cpp -o $@
