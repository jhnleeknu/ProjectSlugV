CXX = clang++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra -pedantic -Iengine/include
PYTHON = .venv/bin/python

.PHONY: all test runtime-resources setup-tools
all: build/step_animation build/decode_animation_draw build/emit_composition_blocks build/emit_composition_variant build/configure_sprite_pool build/produce_sprite_queue build/prepare_sprite_queue build/radix_sprite_queue build/refresh_sprite_queue build/emit_composition_reverse build/sort_sprite_queue build/parse_sprite_scanline build/emit_sprite_resource build/check_tiles build/reset_object build/init_objects build/upload_palette build/init_palette build/check_palettes build/trace_fixed_text build/render_fixed_words build/convert_color_words build/render_text_scene build/update_position build/emit_composition build/emit_composition_refresh

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

test: build/animation_step_test build/animation_draw_test build/sprite_blocks_test build/sprite_pool_test build/sprite_producer_test build/sprite_prepare_queue_test build/sprite_radix_test build/sprite_refresh_queue_test build/sprite_queue_test build/sprite_scanline_test build/composition_resource_test build/tile_resource_test build/object_state_test build/object_lists_test build/palette_resource_test build/fixed_renderer_test build/text_resource_test
	$(PYTHON) -m unittest discover -s tools/tests -v
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
ANIMATION_HEADERS = engine/include/ms5/animation_step.h engine/include/ms5/animation_draw.h engine/include/ms5/sprite_producer.h
build/step_animation: $(ANIMATION_SOURCES) $(ANIMATION_HEADERS) engine/tools/step_animation.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_SOURCES) engine/tools/step_animation.cpp -o $@

build/animation_step_test: $(ANIMATION_SOURCES) $(ANIMATION_HEADERS) engine/tests/animation_step_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_SOURCES) engine/tests/animation_step_test.cpp -o $@
