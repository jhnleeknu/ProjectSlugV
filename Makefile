CXX = clang++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra -pedantic -Iengine/include
PYTHON = .venv/bin/python

.PHONY: all test runtime-resources setup-tools
all: build/execute_animation_banked_lookup build/step_animation_sound_execution build/step_animation_execution build/execute_object_sound_lookup build/execute_object_sprite_wrapper build/execute_stage_activation_helper build/execute_stage_readiness build/execute_stage_counter build/step_stage_hud_counter build/execute_palette_blend build/initialize_stage_activation_prefix build/execute_stage_block_draw build/reset_game_screen_full build/execute_palette_effect build/step_stage_entry_body build/step_stage_frame build/step_stage_sound_frame build/execute_sound_word build/execute_sound_cancel build/execute_sound_byte build/step_stage_spatial_frame build/step_stage_region_frame build/step_stage_buffer_frame build/step_stage_cue_frame build/execute_sprite_submit build/step_stage_cue_control build/step_stage_input_loop build/step_stage_input_callback build/step_stage_input build/step_scene_frame build/step_scene_frame_control build/step_scene_camera build/step_scene_motion_pair build/step_scene_motion_bounds build/initialize_stage_events build/restart_object_full build/initialize_scene build/execute_scene_placement build/step_scene_command build/inspect_scene_script build/step_stage_sound_initialization build/step_sound_word_registers build/step_stage_area_initialization build/step_player_record_capture build/step_stage_area_resume build/step_stage_players build/step_stage_preparation build/step_stage_transition build/step_stage_entry build/step_sound_pair build/step_scene_initialization build/step_scene_node build/step_game_ready build/restart_game build/reset_game_screen build/remove_object build/allocate_object build/finish_game build/initialize_game build/reset_game_objects build/configure_game_record build/reset_game_subsystem build/prepare_game build/step_game_startup build/step_random build/start_main build/prepare_main_frame build/dispatch_stage_area_menu build/dispatch_stage_group_menu build/dispatch_debug_menu build/initialize_interrupt build/step_irq_envelope build/step_interrupt build/queue_interrupt_task build/restore_interrupt_task build/trace_palette_transfer build/refresh_column_controls build/process_credit_request build/step_sound build/sound_word build/enqueue_sound_byte build/service_sound_queue build/poll_frame_gate build/step_input_control build/begin_input_frame build/update_input_status build/initialize_input build/sample_input build/step_control_caller build/consume_control build/advance_control_counter build/video_control build/step_control build/step_control_menu build/finish_control_menu build/step_control_wait build/start_control_menu build/activate_control build/step_menu_frame build/update_menu_header build/redraw_menu_stack build/query_stage build/stage_state build/trace_table_text build/dispatch_menu_event build/push_menu build/navigate_menu build/select_menu_input build/draw_menu_text build/trace_direct_text build/step_menu_motion build/trace_menu_border build/init_menu build/measure_fixed_text build/check_menu build/read_control_request build/snapshot_palette build/setup_palette_fill build/transfer_palette_banks build/transfer_palette build/control_palette build/step_palette_frame build/prepare_palette build/palette_allocator build/step_animation_data build/step_animation_resource build/step_animation build/decode_animation_draw build/emit_composition_blocks build/emit_composition_variant build/configure_sprite_pool build/produce_sprite_queue build/prepare_sprite_queue build/radix_sprite_queue build/refresh_sprite_queue build/emit_composition_reverse build/sort_sprite_queue build/parse_sprite_scanline build/emit_sprite_resource build/check_tiles build/reset_object build/init_objects build/upload_palette build/init_palette build/check_palettes build/trace_fixed_text build/render_fixed_words build/convert_color_words build/render_text_scene build/update_position build/emit_composition build/emit_composition_refresh build/format_text build/step_main_debug build/run_scene_script build/evaluate_scene_motion build/step_scene_node_registers build/update_scene_coordinates build/inspect_scene_tilemap build/inspect_scene_path build/transfer_scene_map build/refresh_scene_map build/execute_scene_path build/step_scene_update build/inspect_scene_placement build/resolve_scene_motion_time

build:
	mkdir -p build

build/check_tiles: engine/src/tile_resource.cpp engine/tools/check_tiles.cpp engine/include/ms5/tile_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/tile_resource.cpp engine/tools/check_tiles.cpp -o $@

build/tile_resource_test: build/object_sprite_wrapper_test build/palette_effect_execution_test build/stage_sound_frame_test build/sound_word_execution_test build/sound_cancel_execution_test build/sound_byte_execution_test build/stage_spatial_frame_test build/stage_region_frame_test build/stage_buffer_frame_test build/stage_cue_frame_test build/sprite_submit_execution_test build/stage_cue_control_test build/stage_input_loop_test build/stage_input_callback_test build/stage_input_test build/scene_frame_test build/scene_frame_control_test build/scene_camera_test build/scene_motion_pair_test build/scene_motion_bounds_test build/stage_event_initialization_test build/object_restart_execution_test build/scene_general_initialization_test build/scene_placement_execution_test engine/src/tile_resource.cpp engine/tests/tile_resource_test.cpp engine/include/ms5/tile_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/tile_resource.cpp engine/tests/tile_resource_test.cpp -o $@

build/reset_object: engine/src/object_state.cpp engine/tools/reset_object.cpp engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_state.cpp engine/tools/reset_object.cpp -o $@

build/object_state_test: engine/src/object_state.cpp engine/tests/object_state_test.cpp engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_state.cpp engine/tests/object_state_test.cpp -o $@

build/init_objects: engine/src/object_lists.cpp engine/src/object_state.cpp engine/tools/init_objects.cpp engine/include/ms5/object_lists.h engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_lists.cpp engine/src/object_state.cpp engine/tools/init_objects.cpp -o $@

build/object_lists_test: engine/src/object_lists.cpp engine/src/object_state.cpp engine/tests/object_lists_test.cpp engine/include/ms5/object_lists.h engine/include/ms5/object_state.h | build
	$(CXX) $(CXXFLAGS) engine/src/object_lists.cpp engine/src/object_state.cpp engine/tests/object_lists_test.cpp -o $@

test: build/physical_rom_resource_test build/program_bus_test build/animation_execution_test build/object_sound_lookup_test build/stage_activation_helpers_test build/stage_readiness_test build/stage_counter_test build/stage_hud_counter_test build/palette_blend_execution_test build/stage_activation_prefix_test build/stage_block_draw_test build/game_screen_reset_execution_test build/stage_entry_body_test build/stage_frame_test build/scene_command_test build/scene_script_test build/stage_sound_initialization_test build/sound_word_registers_test build/stage_area_initialization_test build/player_record_capture_test build/stage_players_test build/stage_preparation_test build/stage_transition_test build/stage_entry_test build/sound_pair_test build/scene_initialization_test build/scene_node_test build/game_ready_test build/game_restart_test build/object_removal_test build/object_allocation_test build/game_initialization_test build/game_objects_test build/game_records_test build/game_reset_test build/game_prelude_test build/irq_envelope_test build/interrupt_service_test build/game_screen_reset_test build/game_startup_test build/random_state_test build/main_startup_test build/main_prelude_irq_test build/main_prelude_test build/main_frame_test build/interrupt_task_test build/sprite_refresh_d0_test build/palette_transfer_trace_test build/column_control_test build/credit_request_test build/sound_service_test build/sound_word_test build/sound_byte_test build/sound_queue_test build/frame_gate_test build/input_control_test build/input_frame_test build/input_status_test build/input_sampler_test build/control_caller_step_test build/control_caller_test build/control_counter_test build/video_control_test build/control_test build/control_menu_frame_test build/control_finish_test build/control_wait_test build/control_menu_start_test build/control_activation_test build/menu_frame_test build/menu_redraw_test build/menu_header_test build/stage_area_menu_test build/stage_group_menu_test build/stage_catalog_test build/menu_debug_test build/menu_event_test build/menu_stack_test build/menu_navigation_test build/menu_input_test build/menu_text_test build/direct_text_test build/menu_motion_test build/menu_border_test build/menu_init_test build/text_measure_test build/menu_descriptor_test build/palette_fill_test build/palette_transfer_test build/palette_frame_test build/palette_prepare_test build/palette_allocator_test build/animation_data_test build/fixed_data_resource_test build/animation_resource_test build/animation_step_test build/animation_draw_test build/sprite_blocks_test build/sprite_pool_test build/sprite_producer_test build/sprite_prepare_queue_test build/sprite_radix_test build/sprite_refresh_queue_test build/sprite_queue_test build/sprite_scanline_test build/composition_resource_test build/tile_resource_test build/object_state_test build/object_lists_test build/palette_resource_test build/fixed_renderer_test build/text_resource_test build/formatted_text_test build/scene_script_run_test build/scene_motion_test build/scene_coordinates_test build/scene_map_resource_test build/scene_map_transfer_test build/scene_map_refresh_test build/scene_path_execution_test build/scene_update_test build/scene_placement_resource_test build/scene_motion_time_test
	./build/animation_machine_test
	./build/animation_machine_device_test
	./build/animation_machine_callers_test
	./build/animation_machine_carry_test
	./build/animation_machine_activation_test
	./build/animation_machine_readiness_test
	./build/animation_machine_hud_test
	./build/animation_machine_transition_test
	./build/animation_machine_exit_test
	./build/animation_machine_screen_test
	./build/animation_machine_cleanup_test
	./build/animation_machine_scene_test
	./build/animation_machine_palette_bind_test
	./build/animation_machine_map_transfer_test
	./build/animation_machine_fade_card_test
	./build/animation_machine_card_child_test
	./build/animation_machine_card_menu_test
	./build/animation_machine_card_menu_open_test
	./build/animation_machine_card_menu_input_test
	./build/animation_machine_card_menu_close_test
	./build/animation_machine_card_menu_save_test
	./build/animation_machine_card_menu_nested_test
	./build/animation_machine_frame_helpers_test
	./build/animation_machine_scene_core_test
	./build/animation_machine_motion_walk_test
	./build/animation_machine_scene_update_test
	./build/animation_machine_script_placement_test
	./build/animation_machine_input_test
	./build/animation_machine_buffer_cue_test
	./build/animation_machine_stage_entry_test
	./build/animation_machine_area_clear_test
	./build/program_stack_test
	./build/physical_rom_resource_test
	./build/program_bus_test
	./build/animation_execution_test
	./build/object_sound_lookup_test
	./build/object_sprite_wrapper_test
	./build/stage_activation_helpers_test
	./build/stage_readiness_test
	./build/stage_counter_test
	./build/stage_hud_counter_test
	./build/palette_blend_execution_test
	./build/stage_activation_prefix_test
	./build/stage_block_draw_test
	./build/game_screen_reset_execution_test
	./build/palette_effect_execution_test
	./build/game_screen_reset_test
	./build/irq_envelope_test
	./build/interrupt_service_test
	./build/interrupt_task_test
	./build/sprite_refresh_d0_test
	./build/palette_transfer_trace_test
	./build/column_control_test
	./build/credit_request_test
	./build/sound_service_test
	./build/scene_command_test
	./build/scene_script_run_test
	./build/scene_motion_test
	./build/scene_coordinates_test
	./build/scene_map_resource_test
	./build/scene_map_transfer_test
	./build/scene_map_refresh_test
	./build/scene_path_execution_test
	./build/scene_update_test
	./build/stage_event_initialization_test
	./build/object_restart_execution_test
	./build/scene_general_initialization_test
	./build/scene_placement_execution_test
	./build/scene_placement_resource_test
	./build/stage_entry_body_test
	./build/stage_frame_test
	./build/stage_sound_frame_test
	./build/sound_word_execution_test
	./build/sound_cancel_execution_test
	./build/sound_byte_execution_test
	./build/stage_spatial_frame_test
	./build/stage_region_frame_test
	./build/stage_buffer_frame_test
	./build/stage_cue_frame_test
	./build/sprite_submit_execution_test
	./build/stage_cue_control_test
	./build/stage_input_loop_test
	./build/stage_input_callback_test
	./build/stage_input_test
	./build/scene_frame_test
	./build/scene_frame_control_test
	./build/scene_camera_test
	./build/scene_motion_pair_test
	./build/scene_motion_bounds_test
	./build/scene_motion_time_test
	./build/scene_script_test
	./build/stage_sound_initialization_test
	./build/sound_word_registers_test
	./build/sound_word_test
	./build/sound_byte_test
	./build/sound_queue_test
	./build/frame_gate_test
	./build/random_state_test
	./build/game_reset_test
	./build/game_initialization_test
	./build/stage_area_initialization_test
	./build/player_record_capture_test
	./build/stage_players_test
	./build/stage_preparation_test
	./build/stage_transition_test
	./build/stage_entry_test
	./build/sound_pair_test
	./build/scene_initialization_test
	./build/scene_node_test
	./build/game_ready_test
	./build/game_restart_test
	./build/object_removal_test
	./build/object_allocation_test
	./build/game_objects_test
	./build/game_records_test
	./build/game_prelude_test
	./build/game_startup_test
	./build/main_startup_test
	./build/main_prelude_irq_test
	./build/main_prelude_test
	./build/main_frame_test
	./build/input_control_test
	./build/input_frame_test
	./build/input_status_test
	./build/input_sampler_test
	./build/control_caller_step_test
	./build/control_caller_test
	./build/control_counter_test
	./build/video_control_test
	./build/control_test
	./build/control_menu_frame_test
	./build/control_finish_test
	./build/control_wait_test
	./build/control_menu_start_test
	./build/control_activation_test
	./build/menu_frame_test
	./build/menu_redraw_test
	./build/menu_header_test
	./build/formatted_text_test
	$(PYTHON) -m unittest discover -s tools/tests -v
	./build/stage_area_menu_test
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
	$(PYTHON) tools/pack_animation_control.py
	$(PYTHON) tools/pack_activation_animation.py
	$(PYTHON) tools/pack_object_sound_lookup.py
	$(PYTHON) tools/pack_stage_hud_counter.py
	$(PYTHON) tools/pack_stage_block_draw.py
	$(PYTHON) tools/pack_scene_debug.py
	$(PYTHON) tools/pack_scene_scripts.py
	$(PYTHON) tools/inventory_scene_placements.py
	$(PYTHON) tools/pack_scene_placements.py
	$(PYTHON) tools/pack_stage_catalog.py
	$(PYTHON) tools/pack_stage_events.py
	$(PYTHON) tools/pack_menu_font.py
	$(PYTHON) tools/pack_control_pause.py
	$(PYTHON) tools/pack_input_streams.py
	$(PYTHON) tools/pack_input_status.py
	$(PYTHON) tools/pack_control_menu_tree.py
	python3 tools/pack_tiles.py
	$(PYTHON) tools/pack_object_boot.py
	$(PYTHON) tools/pack_main_startup.py
	$(PYTHON) tools/pack_stage_palettes.py
	$(PYTHON) tools/pack_stage_players.py
	$(PYTHON) tools/pack_player_record_lookup.py
	$(PYTHON) tools/pack_stage_selector_lookup.py
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
SPRITE_REFRESH_HEADERS = engine/include/ms5/video_port.h engine/include/ms5/sprite_refresh_queue.h engine/include/ms5/sprite_composition.h engine/include/ms5/composition_resource.h
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

build/step_palette_frame: engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/src/palette_resource.cpp engine/include/ms5/palette_frame.h engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/tools/step_palette_frame.cpp engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/src/palette_resource.cpp engine/tools/step_palette_frame.cpp -o $@

build/palette_frame_test: engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/include/ms5/palette_frame.h engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/tests/palette_frame_test.cpp engine/include/ms5/video_port.h | build
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

build/draw_menu_text: engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_text.h engine/tools/draw_menu_text.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/draw_menu_text.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp -o $@

build/menu_text_test: engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_text.h engine/tests/menu_text_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h engine/src/fixed_data_resource.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_text_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/src/fixed_data_resource.cpp -o $@

build/select_menu_input: engine/src/menu_input.cpp engine/include/ms5/menu_input.h engine/tools/select_menu_input.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_input.cpp engine/tools/select_menu_input.cpp -o $@

build/menu_input_table: engine/src/menu_input.cpp engine/include/ms5/menu_input.h engine/tests/menu_input_table.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_input.cpp engine/tests/menu_input_table.cpp -o $@

build/menu_input_test: engine/src/menu_input.cpp engine/include/ms5/menu_input.h engine/tests/menu_input_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_input.cpp engine/tests/menu_input_test.cpp -o $@

build/navigate_menu: engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/tools/navigate_menu.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/navigate_menu.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp -o $@

build/menu_navigation_test: engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/tests/menu_navigation_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h engine/src/fixed_data_resource.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_navigation.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_navigation_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/fixed_data_resource.cpp -o $@

build/push_menu: engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_stack.h engine/include/ms5/menu_text.h engine/include/ms5/menu_init.h engine/tools/push_menu.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/push_menu.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp -o $@

build/menu_stack_test: engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_stack.h engine/include/ms5/menu_text.h engine/include/ms5/menu_init.h engine/tests/menu_stack_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h engine/src/fixed_data_resource.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_stack_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/src/fixed_data_resource.cpp -o $@

build/dispatch_menu_event: engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tools/dispatch_menu_event.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/dispatch_menu_event.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/menu_event_test: engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tests/menu_event_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/menu_event_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/trace_table_text: engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/fixed_text.h engine/tools/trace_table_text.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/trace_table_text.cpp -o $@

build/menu_debug_test: engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_debug.h engine/tests/menu_debug_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h engine/src/fixed_data_resource.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tests/menu_debug_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/src/fixed_data_resource.cpp -o $@

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

build/stage_area_menu_test: engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tests/stage_area_menu_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_stack.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/stage_area_menu_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/redraw_menu_stack: engine/src/menu_debug.cpp engine/src/menu_redraw.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_text.h engine/tools/redraw_menu_stack.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h engine/include/ms5/menu_redraw.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_redraw.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/redraw_menu_stack.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp -o $@

build/update_menu_header: engine/src/menu_header.cpp engine/src/control_request.cpp engine/tools/update_menu_header.cpp engine/include/ms5/menu_header.h engine/include/ms5/control_request.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_header.cpp engine/src/control_request.cpp engine/tools/update_menu_header.cpp -o $@

build/menu_header_test: engine/src/menu_header.cpp engine/src/control_request.cpp engine/tests/menu_header_test.cpp engine/include/ms5/menu_header.h engine/include/ms5/control_request.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_header.cpp engine/src/control_request.cpp engine/tests/menu_header_test.cpp -o $@

build/menu_redraw_test: engine/src/menu_debug.cpp engine/src/menu_redraw.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_text.h engine/tests/menu_redraw_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h engine/include/ms5/menu_redraw.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_redraw.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/menu_redraw_test.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp -o $@

build/step_menu_frame: engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tools/step_menu_frame.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/step_menu_frame.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/menu_frame_test: engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tests/menu_frame_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/menu_frame_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/start_control_menu: engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tools/start_control_menu.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/include/ms5/control_menu_start.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/start_control_menu.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/activate_control: engine/src/control_activation.cpp engine/src/control_request.cpp engine/tools/activate_control.cpp engine/include/ms5/control_activation.h engine/include/ms5/control_request.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_activation.cpp engine/src/control_request.cpp engine/tools/activate_control.cpp -o $@

build/control_activation_test: engine/src/control_activation.cpp engine/src/control_request.cpp engine/tests/control_activation_test.cpp engine/include/ms5/control_activation.h engine/include/ms5/control_request.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_activation.cpp engine/src/control_request.cpp engine/tests/control_activation_test.cpp -o $@

build/control_menu_start_test: engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tests/control_menu_start_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/include/ms5/control_menu_start.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/control_menu_start_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/step_control_wait: engine/src/control_wait.cpp engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tools/step_control_wait.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/include/ms5/control_menu_start.h engine/include/ms5/control_wait.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_wait.cpp engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/step_control_wait.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

build/control_wait_test: engine/src/control_wait.cpp engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tests/control_wait_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/include/ms5/control_menu_start.h engine/include/ms5/control_wait.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_wait.cpp engine/src/control_menu_start.cpp engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/control_wait_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp -o $@

CONTROL_FINISH_SOURCES = engine/src/control_finish.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp
CONTROL_FINISH_HEADERS = engine/include/ms5/control_finish.h engine/include/ms5/menu_frame.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/finish_control_menu: $(CONTROL_FINISH_SOURCES) $(CONTROL_FINISH_HEADERS) engine/tools/finish_control_menu.cpp | build
	$(CXX) $(CXXFLAGS) $(CONTROL_FINISH_SOURCES) engine/tools/finish_control_menu.cpp -o $@

build/control_finish_test: $(CONTROL_FINISH_SOURCES) $(CONTROL_FINISH_HEADERS) engine/tests/control_finish_test.cpp | build
	$(CXX) $(CXXFLAGS) $(CONTROL_FINISH_SOURCES) engine/tests/control_finish_test.cpp -o $@

build/step_control_menu: engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tools/step_control_menu.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/src/control_finish.cpp engine/src/control_menu_frame.cpp engine/include/ms5/control_finish.h engine/include/ms5/control_menu_frame.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/step_control_menu.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/src/control_finish.cpp engine/src/control_menu_frame.cpp -o $@

build/control_menu_frame_test: engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tests/control_menu_frame_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/src/control_finish.cpp engine/src/control_menu_frame.cpp engine/include/ms5/control_finish.h engine/include/ms5/control_menu_frame.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/control_menu_frame_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/src/control_finish.cpp engine/src/control_menu_frame.cpp -o $@

build/step_control: engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/tools/step_control.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/src/control_finish.cpp engine/src/control_menu_frame.cpp engine/include/ms5/control_finish.h engine/include/ms5/control_menu_frame.h engine/src/control.cpp engine/src/control_activation.cpp engine/src/control_wait.cpp engine/src/control_menu_start.cpp engine/include/ms5/control.h engine/include/ms5/control_activation.h engine/include/ms5/control_wait.h engine/include/ms5/control_menu_start.h | build
	$(CXX) $(CXXFLAGS) engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/step_control.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/src/control_finish.cpp engine/src/control_menu_frame.cpp engine/src/control.cpp engine/src/control_activation.cpp engine/src/control_wait.cpp engine/src/control_menu_start.cpp -o $@

build/control_test: engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/src/control_finish.cpp engine/src/control_menu_frame.cpp engine/include/ms5/control_finish.h engine/include/ms5/control_menu_frame.h engine/src/control.cpp engine/src/control_activation.cpp engine/src/control_wait.cpp engine/src/control_menu_start.cpp engine/include/ms5/control.h engine/include/ms5/control_activation.h engine/include/ms5/control_wait.h engine/include/ms5/control_menu_start.h engine/tests/control_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tests/control_test.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/src/control_finish.cpp engine/src/control_menu_frame.cpp engine/src/control.cpp engine/src/control_activation.cpp engine/src/control_wait.cpp engine/src/control_menu_start.cpp -o $@

build/video_control: engine/src/video_control.cpp engine/tools/video_control.cpp engine/include/ms5/video_control.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/video_control.cpp engine/tools/video_control.cpp -o $@

build/video_control_test: engine/src/video_control.cpp engine/tests/video_control_test.cpp engine/include/ms5/video_control.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/video_control.cpp engine/tests/video_control_test.cpp -o $@

build/advance_control_counter: engine/src/control_counter.cpp engine/tools/advance_control_counter.cpp engine/include/ms5/control_counter.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_counter.cpp engine/tools/advance_control_counter.cpp -o $@

build/control_counter_test: engine/src/control_counter.cpp engine/tests/control_counter_test.cpp engine/include/ms5/control_counter.h | build
	$(CXX) $(CXXFLAGS) engine/src/control_counter.cpp engine/tests/control_counter_test.cpp -o $@

CONTROL_CALLER_SOURCES = engine/src/control_caller.cpp engine/src/control_counter.cpp engine/src/video_control.cpp engine/src/palette_snapshot.cpp engine/src/palette_control.cpp engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/src/palette_resource.cpp
CONTROL_CALLER_HEADERS = engine/include/ms5/control_caller.h engine/include/ms5/control_counter.h engine/include/ms5/video_control.h engine/include/ms5/palette_snapshot.h engine/include/ms5/palette_control.h engine/include/ms5/palette_frame.h engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/include/ms5/video_port.h
build/consume_control: $(CONTROL_CALLER_SOURCES) $(CONTROL_CALLER_HEADERS) engine/tools/consume_control.cpp | build
	$(CXX) $(CXXFLAGS) $(CONTROL_CALLER_SOURCES) engine/tools/consume_control.cpp -o $@

build/control_caller_test: $(CONTROL_CALLER_SOURCES) $(CONTROL_CALLER_HEADERS) engine/tests/control_caller_test.cpp | build
	$(CXX) $(CXXFLAGS) $(CONTROL_CALLER_SOURCES) engine/tests/control_caller_test.cpp -o $@

CONTROL_CALLER_STEP_SOURCES = engine/src/menu_frame.cpp engine/src/menu_motion.cpp engine/src/menu_redraw.cpp engine/src/menu_header.cpp engine/src/control_request.cpp engine/src/menu_input.cpp engine/src/menu_event.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/object_restart.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp engine/src/object_state.cpp engine/src/menu_stack.cpp engine/src/menu_init.cpp engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/src/stage_area_menu.cpp engine/src/menu_navigation.cpp engine/src/control_finish.cpp engine/src/control_menu_frame.cpp engine/src/control.cpp engine/src/control_activation.cpp engine/src/control_wait.cpp engine/src/control_menu_start.cpp engine/src/control_caller.cpp engine/src/control_counter.cpp engine/src/video_control.cpp engine/src/palette_snapshot.cpp engine/src/palette_control.cpp engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/src/palette_resource.cpp engine/src/control_caller_step.cpp
CONTROL_CALLER_STEP_HEADERS = engine/include/ms5/menu_event.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart.h engine/include/ms5/stage_area_menu.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/video_port.h engine/include/ms5/menu_frame.h engine/include/ms5/menu_motion.h engine/include/ms5/menu_redraw.h engine/include/ms5/menu_header.h engine/include/ms5/control_request.h engine/include/ms5/menu_input.h engine/include/ms5/control_finish.h engine/include/ms5/control_menu_frame.h engine/include/ms5/control.h engine/include/ms5/control_activation.h engine/include/ms5/control_wait.h engine/include/ms5/control_menu_start.h engine/include/ms5/control_caller.h engine/include/ms5/control_counter.h engine/include/ms5/video_control.h engine/include/ms5/palette_snapshot.h engine/include/ms5/palette_control.h engine/include/ms5/palette_frame.h engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h engine/include/ms5/control_caller_step.h
build/step_control_caller: $(CONTROL_CALLER_STEP_SOURCES) $(CONTROL_CALLER_STEP_HEADERS) engine/tools/step_control_caller.cpp | build
	$(CXX) $(CXXFLAGS) $(CONTROL_CALLER_STEP_SOURCES) engine/tools/step_control_caller.cpp -o $@

build/control_caller_step_test: $(CONTROL_CALLER_STEP_SOURCES) $(CONTROL_CALLER_STEP_HEADERS) engine/tests/control_caller_step_test.cpp | build
	$(CXX) $(CXXFLAGS) $(CONTROL_CALLER_STEP_SOURCES) engine/tests/control_caller_step_test.cpp -o $@

build/sample_input: engine/src/input_sampler.cpp engine/src/fixed_data_resource.cpp engine/tools/sample_input.cpp engine/include/ms5/input_sampler.h engine/include/ms5/fixed_data_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/input_sampler.cpp engine/src/fixed_data_resource.cpp engine/tools/sample_input.cpp -o $@

build/input_sampler_test: engine/src/input_sampler.cpp engine/tests/input_sampler_test.cpp engine/include/ms5/input_sampler.h engine/include/ms5/fixed_data_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/input_sampler.cpp engine/tests/input_sampler_test.cpp -o $@

build/initialize_input: engine/src/input_sampler.cpp engine/src/fixed_data_resource.cpp engine/tools/initialize_input.cpp engine/include/ms5/input_sampler.h engine/include/ms5/fixed_data_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/input_sampler.cpp engine/src/fixed_data_resource.cpp engine/tools/initialize_input.cpp -o $@

INPUT_STATUS_SOURCES = engine/src/input_status.cpp engine/src/input_sampler.cpp
INPUT_STATUS_HEADERS = engine/include/ms5/input_status.h engine/include/ms5/input_sampler.h engine/include/ms5/fixed_data_resource.h
build/update_input_status: $(INPUT_STATUS_SOURCES) $(INPUT_STATUS_HEADERS) engine/src/fixed_data_resource.cpp engine/tools/update_input_status.cpp | build
	$(CXX) $(CXXFLAGS) $(INPUT_STATUS_SOURCES) engine/src/fixed_data_resource.cpp engine/tools/update_input_status.cpp -o $@
build/input_status_test: $(INPUT_STATUS_SOURCES) $(INPUT_STATUS_HEADERS) engine/tests/input_status_test.cpp | build
	$(CXX) $(CXXFLAGS) $(INPUT_STATUS_SOURCES) engine/tests/input_status_test.cpp -o $@

INPUT_FRAME_SOURCES = engine/src/input_frame.cpp $(INPUT_STATUS_SOURCES)
INPUT_FRAME_HEADERS = engine/include/ms5/input_frame.h $(INPUT_STATUS_HEADERS)
build/begin_input_frame: $(INPUT_FRAME_SOURCES) $(INPUT_FRAME_HEADERS) engine/src/fixed_data_resource.cpp engine/tools/begin_input_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(INPUT_FRAME_SOURCES) engine/src/fixed_data_resource.cpp engine/tools/begin_input_frame.cpp -o $@
build/input_frame_test: $(INPUT_FRAME_SOURCES) $(INPUT_FRAME_HEADERS) engine/tests/input_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(INPUT_FRAME_SOURCES) engine/tests/input_frame_test.cpp -o $@

INPUT_CONTROL_SOURCES = engine/src/frame_gate.cpp engine/src/input_control.cpp $(INPUT_FRAME_SOURCES) $(CONTROL_CALLER_STEP_SOURCES)
INPUT_CONTROL_HEADERS = engine/include/ms5/frame_gate.h engine/include/ms5/input_control.h $(INPUT_FRAME_HEADERS) $(CONTROL_CALLER_STEP_HEADERS)
MAIN_PRELUDE_SOURCES = $(sort engine/src/main_prelude.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/column_control.cpp $(SPRITE_PREPARE_SOURCES) engine/src/palette_frame.cpp engine/src/palette_prepare.cpp engine/src/palette_resource.cpp)
MAIN_PRELUDE_HEADERS = engine/include/ms5/video_port.h engine/include/ms5/main_frame.h engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h engine/include/ms5/column_control.h $(SPRITE_PREPARE_HEADERS) engine/include/ms5/palette_frame.h engine/include/ms5/palette_prepare.h engine/include/ms5/palette_resource.h
build/prepare_main_frame: $(MAIN_PRELUDE_SOURCES) $(MAIN_PRELUDE_HEADERS) engine/tools/prepare_main_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(MAIN_PRELUDE_SOURCES) engine/tools/prepare_main_frame.cpp -o $@
build/main_prelude_test: $(MAIN_PRELUDE_SOURCES) $(MAIN_PRELUDE_HEADERS) engine/tests/main_prelude_test.cpp | build
	$(CXX) $(CXXFLAGS) $(MAIN_PRELUDE_SOURCES) engine/tests/main_prelude_test.cpp -o $@
MAIN_FRAME_SOURCES = $(sort $(MAIN_PRELUDE_SOURCES) engine/src/main_frame.cpp engine/src/formatted_text.cpp $(INPUT_CONTROL_SOURCES))
MAIN_FRAME_HEADERS = $(MAIN_PRELUDE_HEADERS) engine/include/ms5/main_frame.h engine/include/ms5/formatted_text.h $(INPUT_CONTROL_HEADERS)
build/step_input_control: $(MAIN_FRAME_SOURCES) $(MAIN_FRAME_HEADERS) engine/tools/step_input_control.cpp | build
	$(CXX) $(CXXFLAGS) $(MAIN_FRAME_SOURCES) engine/tools/step_input_control.cpp -o $@
build/main_frame_test: $(MAIN_FRAME_SOURCES) $(MAIN_FRAME_HEADERS) engine/tests/main_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(MAIN_FRAME_SOURCES) engine/tests/main_frame_test.cpp -o $@
build/input_control_test: $(INPUT_CONTROL_SOURCES) $(INPUT_CONTROL_HEADERS) engine/tests/input_control_test.cpp | build
	$(CXX) $(CXXFLAGS) $(INPUT_CONTROL_SOURCES) engine/tests/input_control_test.cpp -o $@

build/poll_frame_gate: engine/src/frame_gate.cpp engine/tools/poll_frame_gate.cpp engine/include/ms5/frame_gate.h | build
	$(CXX) $(CXXFLAGS) engine/src/frame_gate.cpp engine/tools/poll_frame_gate.cpp -o $@
build/frame_gate_test: engine/src/frame_gate.cpp engine/tests/frame_gate_test.cpp engine/include/ms5/frame_gate.h | build
	$(CXX) $(CXXFLAGS) engine/src/frame_gate.cpp engine/tests/frame_gate_test.cpp -o $@

build/service_sound_queue: engine/src/sound_queue.cpp engine/tools/service_sound_queue.cpp engine/include/ms5/sound_queue.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_queue.cpp engine/tools/service_sound_queue.cpp -o $@
build/sound_queue_test: engine/src/sound_queue.cpp engine/tests/sound_queue_test.cpp engine/include/ms5/sound_queue.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_queue.cpp engine/tests/sound_queue_test.cpp -o $@

build/enqueue_sound_byte: engine/src/sound_byte.cpp engine/tools/enqueue_sound_byte.cpp engine/include/ms5/sound_byte.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_byte.cpp engine/tools/enqueue_sound_byte.cpp -o $@
build/sound_byte_test: engine/src/sound_byte.cpp engine/src/sound_queue.cpp engine/tests/sound_byte_test.cpp engine/include/ms5/sound_byte.h engine/include/ms5/sound_queue.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_byte.cpp engine/src/sound_queue.cpp engine/tests/sound_byte_test.cpp -o $@


build/sound_word: engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/tools/sound_word.cpp engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/tools/sound_word.cpp -o $@

build/sound_word_test: engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/tests/sound_word_test.cpp engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/tests/sound_word_test.cpp -o $@

build/step_sound: engine/src/sound_service.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/sound_queue.cpp engine/tools/step_sound.cpp engine/include/ms5/sound_service.h engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h engine/include/ms5/sound_queue.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_service.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/sound_queue.cpp engine/tools/step_sound.cpp -o $@
build/sound_service_test: engine/src/sound_service.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/sound_queue.cpp engine/tests/sound_service_test.cpp engine/include/ms5/sound_service.h engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h engine/include/ms5/sound_queue.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/sound_service.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/sound_queue.cpp engine/tests/sound_service_test.cpp -o $@

build/process_credit_request: engine/src/credit_request.cpp engine/tools/process_credit_request.cpp engine/include/ms5/credit_request.h | build
	$(CXX) $(CXXFLAGS) engine/src/credit_request.cpp engine/tools/process_credit_request.cpp -o $@
build/credit_request_test: engine/src/credit_request.cpp engine/tests/credit_request_test.cpp engine/include/ms5/credit_request.h | build
	$(CXX) $(CXXFLAGS) engine/src/credit_request.cpp engine/tests/credit_request_test.cpp -o $@

build/refresh_column_controls: engine/src/column_control.cpp engine/tools/refresh_column_controls.cpp engine/include/ms5/column_control.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/column_control.cpp engine/tools/refresh_column_controls.cpp -o $@
build/column_control_test: engine/src/column_control.cpp engine/tests/column_control_test.cpp engine/include/ms5/column_control.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/column_control.cpp engine/tests/column_control_test.cpp -o $@

build/trace_palette_transfer: engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tools/trace_palette_transfer.cpp engine/include/ms5/palette_transfer.h engine/include/ms5/palette_upload.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tools/trace_palette_transfer.cpp -o $@
build/palette_transfer_trace_test: engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tests/palette_transfer_trace_test.cpp engine/include/ms5/palette_transfer.h engine/include/ms5/palette_upload.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tests/palette_transfer_trace_test.cpp -o $@

build/sprite_refresh_d0_test: $(SPRITE_REFRESH_SOURCES) $(SPRITE_REFRESH_HEADERS) engine/tests/sprite_refresh_d0_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SPRITE_REFRESH_SOURCES) engine/tests/sprite_refresh_d0_test.cpp -o $@

build/restore_interrupt_task: engine/src/interrupt_task.cpp engine/tools/restore_interrupt_task.cpp engine/include/ms5/interrupt_task.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/interrupt_task.cpp engine/tools/restore_interrupt_task.cpp -o $@

build/interrupt_task_test: engine/src/interrupt_task.cpp engine/tests/interrupt_task_test.cpp engine/include/ms5/interrupt_task.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/interrupt_task.cpp engine/tests/interrupt_task_test.cpp -o $@

build/queue_interrupt_task: engine/src/interrupt_task.cpp engine/tools/queue_interrupt_task.cpp engine/include/ms5/interrupt_task.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/interrupt_task.cpp engine/tools/queue_interrupt_task.cpp -o $@

INTERRUPT_SERVICE_SOURCES = engine/src/interrupt_service.cpp engine/src/interrupt_task.cpp engine/src/credit_request.cpp engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/src/column_control.cpp $(SPRITE_REFRESH_SOURCES) engine/src/sound_service.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/sound_queue.cpp
INTERRUPT_SERVICE_HEADERS = engine/include/ms5/interrupt_service.h engine/include/ms5/interrupt_task.h engine/include/ms5/credit_request.h engine/include/ms5/palette_transfer.h engine/include/ms5/palette_upload.h engine/include/ms5/column_control.h $(SPRITE_REFRESH_HEADERS) engine/include/ms5/sound_service.h engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h engine/include/ms5/sound_queue.h
MAIN_PRELUDE_IRQ_SOURCES = $(sort $(MAIN_PRELUDE_SOURCES) $(INTERRUPT_SERVICE_SOURCES))
MAIN_PRELUDE_IRQ_HEADERS = $(MAIN_PRELUDE_HEADERS) $(INTERRUPT_SERVICE_HEADERS)
build/main_prelude_irq_test: $(MAIN_PRELUDE_IRQ_SOURCES) $(MAIN_PRELUDE_IRQ_HEADERS) engine/tests/main_prelude_irq_test.cpp | build
	$(CXX) $(CXXFLAGS) $(MAIN_PRELUDE_IRQ_SOURCES) engine/tests/main_prelude_irq_test.cpp -o $@

build/step_interrupt: $(INTERRUPT_SERVICE_SOURCES) $(INTERRUPT_SERVICE_HEADERS) engine/tools/step_interrupt.cpp | build
	$(CXX) $(CXXFLAGS) $(INTERRUPT_SERVICE_SOURCES) engine/tools/step_interrupt.cpp -o $@
build/interrupt_service_test: $(INTERRUPT_SERVICE_SOURCES) $(INTERRUPT_SERVICE_HEADERS) engine/tests/interrupt_service_test.cpp | build
	$(CXX) $(CXXFLAGS) $(INTERRUPT_SERVICE_SOURCES) engine/tests/interrupt_service_test.cpp -o $@

build/step_irq_envelope: engine/src/irq_envelope.cpp engine/tools/step_irq_envelope.cpp engine/include/ms5/irq_envelope.h engine/include/ms5/interrupt_task.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/irq_envelope.cpp engine/tools/step_irq_envelope.cpp -o $@

build/irq_envelope_test: engine/src/irq_envelope.cpp engine/tests/irq_envelope_test.cpp engine/include/ms5/irq_envelope.h engine/include/ms5/interrupt_task.h engine/include/ms5/video_port.h | build
	$(CXX) $(CXXFLAGS) engine/src/irq_envelope.cpp engine/tests/irq_envelope_test.cpp -o $@

build/initialize_interrupt: engine/src/interrupt_init.cpp engine/tools/initialize_interrupt.cpp engine/include/ms5/interrupt_init.h | build
	$(CXX) $(CXXFLAGS) engine/src/interrupt_init.cpp engine/tools/initialize_interrupt.cpp -o $@

build/step_main_debug: engine/src/formatted_text.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/step_main_debug.cpp engine/include/ms5/formatted_text.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/formatted_text.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp engine/tools/step_main_debug.cpp -o $@

build/dispatch_debug_menu: engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/include/ms5/menu_debug.h engine/tools/dispatch_debug_menu.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/include/ms5/stage_area_menu.h engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_navigation.h engine/include/ms5/menu_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h engine/src/fixed_data_resource.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/menu_debug.cpp engine/src/menu_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/tools/dispatch_debug_menu.cpp engine/src/stage_area_menu.cpp engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_navigation.cpp engine/src/fixed_data_resource.cpp -o $@

STAGE_GROUP_DISPATCH_SOURCES = engine/src/stage_group_menu.cpp engine/src/stage_catalog.cpp engine/src/stage_state.cpp engine/src/formatted_text.cpp engine/src/menu_border.cpp engine/src/menu_descriptor.cpp engine/src/fixed_text.cpp engine/src/fixed_data_resource.cpp
STAGE_GROUP_DISPATCH_HEADERS = engine/include/ms5/stage_group_menu.h engine/include/ms5/stage_catalog.h engine/include/ms5/stage_state.h engine/include/ms5/formatted_text.h engine/include/ms5/menu_border.h engine/include/ms5/menu_descriptor.h engine/include/ms5/fixed_text.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/dispatch_stage_group_menu: $(STAGE_GROUP_DISPATCH_SOURCES) $(STAGE_GROUP_DISPATCH_HEADERS) engine/tools/dispatch_stage_group_menu.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_GROUP_DISPATCH_SOURCES) engine/tools/dispatch_stage_group_menu.cpp -o $@

STAGE_AREA_DISPATCH_SOURCES = $(STAGE_GROUP_DISPATCH_SOURCES) engine/src/menu_text.cpp engine/src/menu_debug.cpp engine/src/menu_navigation.cpp engine/src/stage_area_menu.cpp
STAGE_AREA_DISPATCH_HEADERS = $(STAGE_GROUP_DISPATCH_HEADERS) engine/include/ms5/menu_text.h engine/include/ms5/menu_debug.h engine/include/ms5/menu_navigation.h engine/include/ms5/stage_area_menu.h
build/dispatch_stage_area_menu: $(STAGE_AREA_DISPATCH_SOURCES) $(STAGE_AREA_DISPATCH_HEADERS) engine/tools/dispatch_stage_area_menu.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_AREA_DISPATCH_SOURCES) engine/tools/dispatch_stage_area_menu.cpp -o $@

MAIN_STARTUP_SOURCES = engine/src/main_startup.cpp engine/src/palette_control.cpp engine/src/fixed_data_resource.cpp
MAIN_STARTUP_HEADERS = engine/include/ms5/main_startup.h engine/include/ms5/palette_control.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/start_main: $(MAIN_STARTUP_SOURCES) $(MAIN_STARTUP_HEADERS) engine/tools/start_main.cpp | build
	$(CXX) $(CXXFLAGS) $(MAIN_STARTUP_SOURCES) engine/tools/start_main.cpp -o $@
build/main_startup_test: $(MAIN_STARTUP_SOURCES) $(MAIN_STARTUP_HEADERS) engine/src/palette_state.cpp engine/include/ms5/palette_state.h engine/tests/main_startup_test.cpp | build
	$(CXX) $(CXXFLAGS) $(MAIN_STARTUP_SOURCES) engine/src/palette_state.cpp engine/tests/main_startup_test.cpp -o $@

build/step_random: engine/src/random_state.cpp engine/include/ms5/random_state.h engine/tools/step_random.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/random_state.cpp engine/tools/step_random.cpp -o $@
build/random_state_test: engine/src/random_state.cpp engine/include/ms5/random_state.h engine/tests/random_state_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/random_state.cpp engine/tests/random_state_test.cpp -o $@

GAME_STARTUP_SOURCES = $(sort engine/src/game_startup.cpp engine/src/palette_fill.cpp engine/src/random_state.cpp $(MAIN_STARTUP_SOURCES) engine/src/palette_resource.cpp)
GAME_STARTUP_HEADERS = engine/include/ms5/game_startup.h engine/include/ms5/palette_fill.h engine/include/ms5/random_state.h engine/include/ms5/palette_resource.h $(MAIN_STARTUP_HEADERS)
build/step_game_startup: $(GAME_STARTUP_SOURCES) $(GAME_STARTUP_HEADERS) engine/tools/step_game_startup.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_STARTUP_SOURCES) engine/tools/step_game_startup.cpp -o $@
build/game_startup_test: $(GAME_STARTUP_SOURCES) $(GAME_STARTUP_HEADERS) engine/src/palette_state.cpp engine/include/ms5/palette_state.h engine/tests/game_startup_test.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_STARTUP_SOURCES) engine/src/palette_state.cpp engine/tests/game_startup_test.cpp -o $@

GAME_PRELUDE_SOURCES = engine/src/game_prelude.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp
GAME_PRELUDE_HEADERS = engine/include/ms5/game_prelude.h engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h
build/prepare_game: $(GAME_PRELUDE_SOURCES) $(GAME_PRELUDE_HEADERS) engine/tools/prepare_game.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_PRELUDE_SOURCES) engine/tools/prepare_game.cpp -o $@
build/game_prelude_test: $(GAME_PRELUDE_SOURCES) $(GAME_PRELUDE_HEADERS) engine/tests/game_prelude_test.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_PRELUDE_SOURCES) engine/tests/game_prelude_test.cpp -o $@

build/reset_game_subsystem: engine/src/game_reset.cpp engine/include/ms5/game_reset.h engine/tools/reset_game_subsystem.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_reset.cpp engine/tools/reset_game_subsystem.cpp -o $@
build/game_reset_test: engine/src/game_reset.cpp engine/include/ms5/game_reset.h engine/tests/game_reset_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_reset.cpp engine/tests/game_reset_test.cpp -o $@

build/reset_game_objects: engine/src/game_objects.cpp engine/include/ms5/game_objects.h engine/tools/reset_game_objects.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_objects.cpp engine/tools/reset_game_objects.cpp -o $@
build/game_objects_test: engine/src/game_objects.cpp engine/include/ms5/game_objects.h engine/tests/game_objects_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_objects.cpp engine/tests/game_objects_test.cpp -o $@
build/configure_game_record: engine/src/game_records.cpp engine/src/fixed_data_resource.cpp engine/include/ms5/game_records.h engine/include/ms5/fixed_data_resource.h engine/tools/configure_game_record.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_records.cpp engine/src/fixed_data_resource.cpp engine/tools/configure_game_record.cpp -o $@
build/game_records_test: engine/src/game_records.cpp engine/include/ms5/game_records.h engine/include/ms5/fixed_data_resource.h engine/tests/game_records_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_records.cpp engine/tests/game_records_test.cpp -o $@

GAME_INITIALIZATION_SOURCES = engine/src/game_initialization.cpp engine/src/game_prelude.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/game_reset.cpp engine/src/game_objects.cpp engine/src/game_records.cpp engine/src/fixed_data_resource.cpp
GAME_INITIALIZATION_HEADERS = engine/include/ms5/game_initialization.h engine/include/ms5/game_prelude.h engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h engine/include/ms5/game_reset.h engine/include/ms5/game_objects.h engine/include/ms5/game_records.h engine/include/ms5/fixed_data_resource.h
build/finish_game: $(GAME_INITIALIZATION_SOURCES) $(GAME_INITIALIZATION_HEADERS) engine/tools/finish_game.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_INITIALIZATION_SOURCES) engine/tools/finish_game.cpp -o $@
build/initialize_game: $(GAME_INITIALIZATION_SOURCES) $(GAME_INITIALIZATION_HEADERS) engine/tools/initialize_game.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_INITIALIZATION_SOURCES) engine/tools/initialize_game.cpp -o $@
build/game_initialization_test: $(GAME_INITIALIZATION_SOURCES) $(GAME_INITIALIZATION_HEADERS) engine/tests/game_initialization_test.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_INITIALIZATION_SOURCES) engine/tests/game_initialization_test.cpp -o $@

build/allocate_object: engine/src/object_allocation.cpp engine/include/ms5/object_allocation.h engine/tools/allocate_object.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/object_allocation.cpp engine/tools/allocate_object.cpp -o $@
build/object_allocation_test: engine/src/object_allocation.cpp engine/include/ms5/object_allocation.h engine/tests/object_allocation_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/object_allocation.cpp engine/tests/object_allocation_test.cpp -o $@

OBJECT_REMOVAL_SOURCES = engine/src/object_removal.cpp engine/src/object_state.cpp engine/src/palette_allocator.cpp engine/src/position_state.cpp
OBJECT_REMOVAL_HEADERS = engine/include/ms5/object_removal.h engine/include/ms5/object_state.h engine/include/ms5/palette_allocator.h engine/include/ms5/position_state.h engine/include/ms5/video_port.h
build/remove_object: $(OBJECT_REMOVAL_SOURCES) $(OBJECT_REMOVAL_HEADERS) engine/tools/remove_object.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_REMOVAL_SOURCES) engine/tools/remove_object.cpp -o $@
build/object_removal_test: $(OBJECT_REMOVAL_SOURCES) $(OBJECT_REMOVAL_HEADERS) engine/tests/object_removal_test.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_REMOVAL_SOURCES) engine/tests/object_removal_test.cpp -o $@

GAME_SCREEN_RESET_HEADERS = engine/include/ms5/game_screen_reset.h engine/include/ms5/game_screen_reset_execution.h engine/include/ms5/object_restart_execution.h engine/include/ms5/video_port.h
build/reset_game_screen: engine/src/game_screen_reset.cpp $(GAME_SCREEN_RESET_HEADERS) engine/tools/reset_game_screen.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_screen_reset.cpp engine/tools/reset_game_screen.cpp -o $@
build/game_screen_reset_test: engine/src/game_screen_reset.cpp $(GAME_SCREEN_RESET_HEADERS) engine/tests/game_screen_reset_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_screen_reset.cpp engine/tests/game_screen_reset_test.cpp -o $@

GAME_RESTART_SOURCES = $(sort engine/src/game_restart.cpp engine/src/game_screen_reset.cpp engine/src/random_state.cpp engine/src/stage_state.cpp engine/src/input_sampler.cpp $(GAME_INITIALIZATION_SOURCES) $(OBJECT_REMOVAL_SOURCES))
GAME_RESTART_HEADERS = engine/include/ms5/game_restart.h $(GAME_SCREEN_RESET_HEADERS) engine/include/ms5/random_state.h engine/include/ms5/stage_state.h engine/include/ms5/input_sampler.h $(GAME_INITIALIZATION_HEADERS) $(OBJECT_REMOVAL_HEADERS)
build/restart_game: $(GAME_RESTART_SOURCES) $(GAME_RESTART_HEADERS) engine/tools/restart_game.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_RESTART_SOURCES) engine/tools/restart_game.cpp -o $@
build/game_restart_test: $(GAME_RESTART_SOURCES) $(GAME_RESTART_HEADERS) engine/tests/game_restart_test.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_RESTART_SOURCES) engine/tests/game_restart_test.cpp -o $@

GAME_READY_SOURCES = $(sort engine/src/game_ready.cpp engine/src/object_restart.cpp engine/src/object_allocation.cpp engine/src/game_screen_reset.cpp $(OBJECT_REMOVAL_SOURCES))
GAME_READY_HEADERS = engine/include/ms5/game_ready.h engine/include/ms5/object_restart.h engine/include/ms5/object_allocation.h $(GAME_SCREEN_RESET_HEADERS) $(OBJECT_REMOVAL_HEADERS)
build/step_game_ready: $(GAME_READY_SOURCES) $(GAME_READY_HEADERS) engine/tools/step_game_ready.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_READY_SOURCES) engine/tools/step_game_ready.cpp -o $@
build/game_ready_test: $(GAME_READY_SOURCES) $(GAME_READY_HEADERS) engine/tests/game_ready_test.cpp | build
	$(CXX) $(CXXFLAGS) $(GAME_READY_SOURCES) engine/tests/game_ready_test.cpp -o $@

SCENE_NODE_SOURCES = engine/src/scene_node.cpp engine/src/position_state.cpp
SCENE_NODE_HEADERS = engine/include/ms5/scene_node.h engine/include/ms5/position_state.h
build/step_scene_node: $(SCENE_NODE_SOURCES) $(SCENE_NODE_HEADERS) engine/tools/step_scene_node.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_NODE_SOURCES) engine/tools/step_scene_node.cpp -o $@
build/scene_node_test: $(SCENE_NODE_SOURCES) $(SCENE_NODE_HEADERS) engine/tests/scene_node_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_NODE_SOURCES) engine/tests/scene_node_test.cpp -o $@

SCENE_INITIALIZATION_SOURCES = engine/src/scene_initialization.cpp engine/src/scene_node.cpp engine/src/position_state.cpp engine/src/game_screen_reset.cpp engine/src/fixed_data_resource.cpp
SCENE_INITIALIZATION_HEADERS = engine/include/ms5/scene_map_transfer.h engine/include/ms5/scene_initialization.h engine/include/ms5/scene_node.h engine/include/ms5/position_state.h $(GAME_SCREEN_RESET_HEADERS) engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/step_scene_initialization: $(SCENE_INITIALIZATION_SOURCES) $(SCENE_INITIALIZATION_HEADERS) engine/tools/step_scene_initialization.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_INITIALIZATION_SOURCES) engine/tools/step_scene_initialization.cpp -o $@
build/scene_initialization_test: $(SCENE_INITIALIZATION_SOURCES) $(SCENE_INITIALIZATION_HEADERS) engine/tests/scene_initialization_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_INITIALIZATION_SOURCES) engine/tests/scene_initialization_test.cpp -o $@

SOUND_PAIR_SOURCES = engine/src/sound_pair.cpp engine/src/sound_byte.cpp
SOUND_PAIR_HEADERS = engine/include/ms5/sound_pair.h engine/include/ms5/sound_byte.h
build/step_sound_pair: $(SOUND_PAIR_SOURCES) $(SOUND_PAIR_HEADERS) engine/tools/step_sound_pair.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_PAIR_SOURCES) engine/tools/step_sound_pair.cpp -o $@
build/sound_pair_test: $(SOUND_PAIR_SOURCES) $(SOUND_PAIR_HEADERS) engine/tests/sound_pair_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_PAIR_SOURCES) engine/tests/sound_pair_test.cpp -o $@

STAGE_ENTRY_SOURCES = engine/src/stage_entry.cpp $(SCENE_INITIALIZATION_SOURCES) engine/src/sound_pair.cpp engine/src/sound_byte.cpp engine/src/stage_catalog.cpp
STAGE_ENTRY_HEADERS = engine/include/ms5/stage_entry.h $(SCENE_INITIALIZATION_HEADERS) $(SOUND_PAIR_HEADERS) engine/include/ms5/stage_catalog.h
build/step_stage_entry: $(STAGE_ENTRY_SOURCES) $(STAGE_ENTRY_HEADERS) engine/tools/step_stage_entry.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ENTRY_SOURCES) engine/tools/step_stage_entry.cpp -o $@
build/stage_entry_test: $(STAGE_ENTRY_SOURCES) $(STAGE_ENTRY_HEADERS) engine/tests/stage_entry_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ENTRY_SOURCES) engine/tests/stage_entry_test.cpp -o $@

STAGE_TRANSITION_SOURCES = engine/src/stage_transition.cpp engine/src/palette_control.cpp engine/src/game_screen_reset.cpp engine/src/object_allocation.cpp
STAGE_TRANSITION_HEADERS = engine/include/ms5/stage_transition.h engine/include/ms5/palette_control.h $(GAME_SCREEN_RESET_HEADERS) engine/include/ms5/object_allocation.h engine/include/ms5/video_port.h
build/step_stage_transition: $(STAGE_TRANSITION_SOURCES) $(STAGE_TRANSITION_HEADERS) engine/tools/step_stage_transition.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_TRANSITION_SOURCES) engine/tools/step_stage_transition.cpp -o $@
build/stage_transition_test: $(STAGE_TRANSITION_SOURCES) $(STAGE_TRANSITION_HEADERS) engine/tests/stage_transition_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_TRANSITION_SOURCES) engine/tests/stage_transition_test.cpp -o $@

STAGE_PREPARATION_SOURCES = $(sort engine/src/stage_preparation.cpp $(MAIN_STARTUP_SOURCES) $(OBJECT_REMOVAL_SOURCES))
STAGE_PREPARATION_HEADERS = engine/include/ms5/stage_preparation.h $(MAIN_STARTUP_HEADERS) $(OBJECT_REMOVAL_HEADERS)
build/step_stage_preparation: $(STAGE_PREPARATION_SOURCES) $(STAGE_PREPARATION_HEADERS) engine/tools/step_stage_preparation.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_PREPARATION_SOURCES) engine/tools/step_stage_preparation.cpp -o $@
build/stage_preparation_test: $(STAGE_PREPARATION_SOURCES) $(STAGE_PREPARATION_HEADERS) engine/src/palette_state.cpp engine/include/ms5/palette_state.h engine/tests/stage_preparation_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_PREPARATION_SOURCES) engine/src/palette_state.cpp engine/tests/stage_preparation_test.cpp -o $@

STAGE_PLAYERS_SOURCES = $(sort engine/src/stage_players.cpp engine/src/game_objects.cpp engine/src/object_restart.cpp engine/src/random_state.cpp engine/src/fixed_data_resource.cpp $(OBJECT_REMOVAL_SOURCES))
STAGE_PLAYERS_HEADERS = engine/include/ms5/stage_players.h engine/include/ms5/game_objects.h engine/include/ms5/object_restart.h engine/include/ms5/random_state.h engine/include/ms5/fixed_data_resource.h $(OBJECT_REMOVAL_HEADERS)
build/step_stage_players: $(STAGE_PLAYERS_SOURCES) $(STAGE_PLAYERS_HEADERS) engine/tools/step_stage_players.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_PLAYERS_SOURCES) engine/tools/step_stage_players.cpp -o $@
build/stage_players_test: $(STAGE_PLAYERS_SOURCES) $(STAGE_PLAYERS_HEADERS) engine/tests/stage_players_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_PLAYERS_SOURCES) engine/tests/stage_players_test.cpp -o $@

PLAYER_RECORD_CAPTURE_SOURCES = engine/src/player_record_capture.cpp $(GAME_INITIALIZATION_SOURCES)
PLAYER_RECORD_CAPTURE_HEADERS = engine/include/ms5/player_record_capture.h $(GAME_INITIALIZATION_HEADERS)
build/step_player_record_capture: $(PLAYER_RECORD_CAPTURE_SOURCES) $(PLAYER_RECORD_CAPTURE_HEADERS) engine/tools/step_player_record_capture.cpp | build
	$(CXX) $(CXXFLAGS) $(PLAYER_RECORD_CAPTURE_SOURCES) engine/tools/step_player_record_capture.cpp -o $@
build/step_stage_area_resume: $(PLAYER_RECORD_CAPTURE_SOURCES) $(PLAYER_RECORD_CAPTURE_HEADERS) engine/tools/step_stage_area_resume.cpp | build
	$(CXX) $(CXXFLAGS) $(PLAYER_RECORD_CAPTURE_SOURCES) engine/tools/step_stage_area_resume.cpp -o $@
build/player_record_capture_test: $(PLAYER_RECORD_CAPTURE_SOURCES) $(PLAYER_RECORD_CAPTURE_HEADERS) engine/tests/player_record_capture_test.cpp | build
	$(CXX) $(CXXFLAGS) $(PLAYER_RECORD_CAPTURE_SOURCES) engine/tests/player_record_capture_test.cpp -o $@

STAGE_AREA_INITIALIZATION_SOURCES = engine/src/stage_area_initialization.cpp engine/src/object_allocation.cpp $(PLAYER_RECORD_CAPTURE_SOURCES)
STAGE_AREA_INITIALIZATION_HEADERS = engine/include/ms5/stage_area_initialization.h engine/include/ms5/object_allocation.h $(PLAYER_RECORD_CAPTURE_HEADERS)
build/step_stage_area_initialization: $(STAGE_AREA_INITIALIZATION_SOURCES) $(STAGE_AREA_INITIALIZATION_HEADERS) engine/tools/step_stage_area_initialization.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_AREA_INITIALIZATION_SOURCES) engine/tools/step_stage_area_initialization.cpp -o $@
build/stage_area_initialization_test: $(STAGE_AREA_INITIALIZATION_SOURCES) $(STAGE_AREA_INITIALIZATION_HEADERS) engine/tests/stage_area_initialization_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_AREA_INITIALIZATION_SOURCES) engine/tests/stage_area_initialization_test.cpp -o $@

SOUND_WORD_REGISTERS_SOURCES = engine/src/sound_word.cpp engine/src/sound_byte.cpp
SOUND_WORD_REGISTERS_HEADERS = engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h
build/step_sound_word_registers: $(SOUND_WORD_REGISTERS_SOURCES) $(SOUND_WORD_REGISTERS_HEADERS) engine/tools/step_sound_word_registers.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_WORD_REGISTERS_SOURCES) engine/tools/step_sound_word_registers.cpp -o $@
build/sound_word_registers_test: $(SOUND_WORD_REGISTERS_SOURCES) $(SOUND_WORD_REGISTERS_HEADERS) engine/tests/sound_word_registers_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_WORD_REGISTERS_SOURCES) engine/tests/sound_word_registers_test.cpp -o $@

STAGE_SOUND_INITIALIZATION_SOURCES = engine/src/stage_sound_initialization.cpp engine/src/sound_word.cpp engine/src/sound_byte.cpp engine/src/stage_catalog.cpp engine/src/fixed_data_resource.cpp
STAGE_SOUND_INITIALIZATION_HEADERS = engine/include/ms5/stage_sound_initialization.h engine/include/ms5/sound_word.h engine/include/ms5/sound_byte.h engine/include/ms5/stage_catalog.h engine/include/ms5/fixed_data_resource.h
build/step_stage_sound_initialization: $(STAGE_SOUND_INITIALIZATION_SOURCES) $(STAGE_SOUND_INITIALIZATION_HEADERS) engine/tools/step_stage_sound_initialization.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_SOUND_INITIALIZATION_SOURCES) engine/tools/step_stage_sound_initialization.cpp -o $@
build/stage_sound_initialization_test: $(STAGE_SOUND_INITIALIZATION_SOURCES) $(STAGE_SOUND_INITIALIZATION_HEADERS) engine/tests/stage_sound_initialization_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_SOUND_INITIALIZATION_SOURCES) engine/tests/stage_sound_initialization_test.cpp -o $@

SCENE_SCRIPT_SOURCES = engine/src/scene_script.cpp engine/src/fixed_data_resource.cpp
SCENE_SCRIPT_HEADERS = engine/include/ms5/scene_script.h engine/include/ms5/fixed_data_resource.h
build/inspect_scene_script: $(SCENE_SCRIPT_SOURCES) $(SCENE_SCRIPT_HEADERS) engine/tools/inspect_scene_script.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_SCRIPT_SOURCES) engine/tools/inspect_scene_script.cpp -o $@
build/scene_script_test: $(SCENE_SCRIPT_SOURCES) $(SCENE_SCRIPT_HEADERS) engine/tests/scene_script_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_SCRIPT_SOURCES) engine/tests/scene_script_test.cpp -o $@

SCENE_COMMAND_SOURCES = engine/src/scene_setup.cpp engine/src/sprite_producer.cpp engine/src/sprite_pool.cpp engine/src/main_startup.cpp engine/src/palette_control.cpp engine/src/palette_state.cpp engine/src/scene_command.cpp engine/src/scene_script.cpp engine/src/fixed_data_resource.cpp engine/src/scene_node.cpp engine/src/position_state.cpp
SCENE_COMMAND_HEADERS = engine/include/ms5/scene_setup.h engine/include/ms5/sprite_producer.h engine/include/ms5/sprite_pool.h engine/include/ms5/main_startup.h engine/include/ms5/palette_control.h engine/include/ms5/palette_state.h engine/include/ms5/scene_command.h engine/include/ms5/scene_script.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/scene_node.h engine/include/ms5/position_state.h engine/include/ms5/video_port.h
build/step_scene_command: $(SCENE_COMMAND_SOURCES) $(SCENE_COMMAND_HEADERS) engine/tools/step_scene_command.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_COMMAND_SOURCES) engine/tools/step_scene_command.cpp -o $@
build/scene_command_test: $(SCENE_COMMAND_SOURCES) $(SCENE_COMMAND_HEADERS) engine/tests/scene_command_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_COMMAND_SOURCES) engine/tests/scene_command_test.cpp -o $@

SCENE_SCRIPT_RUN_SOURCES = engine/src/scene_script_run.cpp $(SCENE_COMMAND_SOURCES)
SCENE_SCRIPT_RUN_HEADERS = engine/include/ms5/scene_script_run.h $(SCENE_COMMAND_HEADERS)
build/run_scene_script: $(SCENE_SCRIPT_RUN_SOURCES) $(SCENE_SCRIPT_RUN_HEADERS) engine/tools/run_scene_script.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_SCRIPT_RUN_SOURCES) engine/tools/run_scene_script.cpp -o $@
build/scene_script_run_test: $(SCENE_SCRIPT_RUN_SOURCES) $(SCENE_SCRIPT_RUN_HEADERS) engine/tests/scene_script_run_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_SCRIPT_RUN_SOURCES) engine/tests/scene_script_run_test.cpp -o $@

SCENE_MOTION_SOURCES = engine/src/scene_motion.cpp engine/src/fixed_data_resource.cpp
SCENE_MOTION_HEADERS = engine/include/ms5/scene_motion.h engine/include/ms5/scene_command.h engine/include/ms5/scene_script.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/evaluate_scene_motion: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tools/evaluate_scene_motion.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tools/evaluate_scene_motion.cpp -o $@
build/scene_motion_test: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tests/scene_motion_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tests/scene_motion_test.cpp -o $@

SCENE_COORDINATES_SOURCES = engine/src/scene_coordinates.cpp engine/src/scene_node.cpp
SCENE_COORDINATES_HEADERS = engine/include/ms5/scene_coordinates.h engine/include/ms5/scene_node.h
build/step_scene_node_registers: engine/src/scene_node.cpp engine/include/ms5/scene_node.h engine/tools/step_scene_node_registers.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/scene_node.cpp engine/tools/step_scene_node_registers.cpp -o $@
build/update_scene_coordinates: $(SCENE_COORDINATES_SOURCES) $(SCENE_COORDINATES_HEADERS) engine/tools/update_scene_coordinates.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_COORDINATES_SOURCES) engine/tools/update_scene_coordinates.cpp -o $@
build/scene_coordinates_test: $(SCENE_COORDINATES_SOURCES) $(SCENE_COORDINATES_HEADERS) engine/tests/scene_coordinates_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_COORDINATES_SOURCES) engine/tests/scene_coordinates_test.cpp -o $@

SCENE_MAP_RESOURCE_SOURCES = engine/src/scene_map_resource.cpp engine/src/fixed_data_resource.cpp
SCENE_MAP_RESOURCE_HEADERS = engine/include/ms5/scene_map_resource.h engine/include/ms5/fixed_data_resource.h
build/inspect_scene_tilemap: $(SCENE_MAP_RESOURCE_SOURCES) $(SCENE_MAP_RESOURCE_HEADERS) engine/tools/inspect_scene_tilemap.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_RESOURCE_SOURCES) engine/tools/inspect_scene_tilemap.cpp -o $@
build/inspect_scene_path: $(SCENE_MAP_RESOURCE_SOURCES) $(SCENE_MAP_RESOURCE_HEADERS) engine/tools/inspect_scene_path.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_RESOURCE_SOURCES) engine/tools/inspect_scene_path.cpp -o $@
build/scene_map_resource_test: $(SCENE_MAP_RESOURCE_SOURCES) $(SCENE_MAP_RESOURCE_HEADERS) engine/tests/scene_map_resource_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_RESOURCE_SOURCES) engine/tests/scene_map_resource_test.cpp -o $@

SCENE_MAP_TRANSFER_SOURCES = engine/src/scene_map_transfer.cpp engine/src/fixed_data_resource.cpp
SCENE_MAP_TRANSFER_HEADERS = engine/include/ms5/scene_path_execution.h engine/include/ms5/scene_map_refresh.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/transfer_scene_map: $(SCENE_MAP_TRANSFER_SOURCES) $(SCENE_MAP_TRANSFER_HEADERS) engine/tools/transfer_scene_map.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_TRANSFER_SOURCES) engine/tools/transfer_scene_map.cpp -o $@
build/scene_map_transfer_test: $(SCENE_MAP_TRANSFER_SOURCES) $(SCENE_MAP_TRANSFER_HEADERS) engine/tests/scene_map_transfer_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_TRANSFER_SOURCES) engine/tests/scene_map_transfer_test.cpp -o $@

build/refresh_scene_map: $(SCENE_MAP_TRANSFER_SOURCES) $(SCENE_MAP_TRANSFER_HEADERS) engine/tools/refresh_scene_map.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_TRANSFER_SOURCES) engine/tools/refresh_scene_map.cpp -o $@
build/scene_map_refresh_test: $(SCENE_MAP_TRANSFER_SOURCES) $(SCENE_MAP_TRANSFER_HEADERS) engine/tests/scene_map_refresh_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_TRANSFER_SOURCES) engine/tests/scene_map_refresh_test.cpp -o $@

build/execute_scene_path: $(SCENE_MAP_TRANSFER_SOURCES) $(SCENE_MAP_TRANSFER_HEADERS) engine/tools/execute_scene_path.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_TRANSFER_SOURCES) engine/tools/execute_scene_path.cpp -o $@
build/scene_path_execution_test: $(SCENE_MAP_TRANSFER_SOURCES) $(SCENE_MAP_TRANSFER_HEADERS) engine/tests/scene_path_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MAP_TRANSFER_SOURCES) engine/tests/scene_path_execution_test.cpp -o $@

SCENE_UPDATE_SOURCES = engine/src/scene_update.cpp engine/src/scene_initialization.cpp engine/src/scene_coordinates.cpp engine/src/scene_node.cpp engine/src/game_screen_reset.cpp $(SCENE_MAP_TRANSFER_SOURCES)
SCENE_UPDATE_HEADERS = engine/include/ms5/scene_update.h engine/include/ms5/scene_initialization.h engine/include/ms5/scene_coordinates.h engine/include/ms5/scene_node.h $(GAME_SCREEN_RESET_HEADERS) $(SCENE_MAP_TRANSFER_HEADERS)
build/step_scene_update: $(SCENE_UPDATE_SOURCES) $(SCENE_UPDATE_HEADERS) engine/tools/step_scene_update.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_UPDATE_SOURCES) engine/tools/step_scene_update.cpp -o $@
build/scene_update_test: $(SCENE_UPDATE_SOURCES) $(SCENE_UPDATE_HEADERS) engine/tests/scene_update_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_UPDATE_SOURCES) engine/tests/scene_update_test.cpp -o $@

SCENE_PLACEMENT_SOURCES = engine/src/scene_placement_resource.cpp engine/src/fixed_data_resource.cpp
SCENE_PLACEMENT_HEADERS = engine/include/ms5/scene_placement_resource.h engine/include/ms5/fixed_data_resource.h
build/inspect_scene_placement: $(SCENE_PLACEMENT_SOURCES) $(SCENE_PLACEMENT_HEADERS) engine/tools/inspect_scene_placement.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_PLACEMENT_SOURCES) engine/tools/inspect_scene_placement.cpp -o $@
build/scene_placement_resource_test: $(SCENE_PLACEMENT_SOURCES) $(SCENE_PLACEMENT_HEADERS) engine/tests/scene_placement_resource_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_PLACEMENT_SOURCES) engine/tests/scene_placement_resource_test.cpp -o $@

build/resolve_scene_motion_time: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tools/resolve_scene_motion_time.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tools/resolve_scene_motion_time.cpp -o $@
build/scene_motion_time_test: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tests/scene_motion_time_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tests/scene_motion_time_test.cpp -o $@

SCENE_PLACEMENT_EXECUTION_SOURCES = engine/src/scene_placement_execution.cpp engine/src/scene_motion.cpp engine/src/scene_node.cpp engine/src/object_allocation.cpp engine/src/fixed_data_resource.cpp
SCENE_PLACEMENT_EXECUTION_HEADERS = engine/include/ms5/scene_placement_execution.h engine/include/ms5/scene_motion.h engine/include/ms5/scene_node.h engine/include/ms5/object_allocation.h engine/include/ms5/scene_command.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/scene_script.h engine/include/ms5/video_port.h
build/execute_scene_placement: $(SCENE_PLACEMENT_EXECUTION_SOURCES) $(SCENE_PLACEMENT_EXECUTION_HEADERS) engine/tools/execute_scene_placement.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_PLACEMENT_EXECUTION_SOURCES) engine/tools/execute_scene_placement.cpp -o $@
build/scene_placement_execution_test: $(SCENE_PLACEMENT_EXECUTION_SOURCES) $(SCENE_PLACEMENT_EXECUTION_HEADERS) engine/tests/scene_placement_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_PLACEMENT_EXECUTION_SOURCES) engine/tests/scene_placement_execution_test.cpp -o $@

SCENE_GENERAL_INITIALIZATION_SOURCES = $(sort engine/src/scene_general_initialization.cpp $(SCENE_UPDATE_SOURCES) $(SCENE_COMMAND_SOURCES) $(SCENE_SCRIPT_RUN_SOURCES) $(SCENE_PLACEMENT_EXECUTION_SOURCES))
SCENE_GENERAL_INITIALIZATION_HEADERS = $(sort engine/include/ms5/scene_general_initialization.h $(SCENE_UPDATE_HEADERS) $(SCENE_COMMAND_HEADERS) $(SCENE_SCRIPT_RUN_HEADERS) $(SCENE_PLACEMENT_EXECUTION_HEADERS))
build/initialize_scene: $(SCENE_GENERAL_INITIALIZATION_SOURCES) $(SCENE_GENERAL_INITIALIZATION_HEADERS) engine/tools/initialize_scene.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_GENERAL_INITIALIZATION_SOURCES) engine/tools/initialize_scene.cpp -o $@
build/scene_general_initialization_test: $(SCENE_GENERAL_INITIALIZATION_SOURCES) $(SCENE_GENERAL_INITIALIZATION_HEADERS) engine/tests/scene_general_initialization_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_GENERAL_INITIALIZATION_SOURCES) engine/tests/scene_general_initialization_test.cpp -o $@

OBJECT_RESTART_EXECUTION_SOURCES = engine/src/object_restart_execution.cpp engine/src/object_state.cpp engine/src/scene_node.cpp
OBJECT_RESTART_EXECUTION_HEADERS = engine/include/ms5/object_restart_execution.h engine/include/ms5/object_state.h engine/include/ms5/scene_node.h engine/include/ms5/video_port.h
build/restart_object_full: $(OBJECT_RESTART_EXECUTION_SOURCES) $(OBJECT_RESTART_EXECUTION_HEADERS) engine/tools/restart_object_full.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_RESTART_EXECUTION_SOURCES) engine/tools/restart_object_full.cpp -o $@
build/object_restart_execution_test: $(OBJECT_RESTART_EXECUTION_SOURCES) $(OBJECT_RESTART_EXECUTION_HEADERS) engine/tests/object_restart_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_RESTART_EXECUTION_SOURCES) engine/tests/object_restart_execution_test.cpp -o $@

STAGE_EVENT_INITIALIZATION_SOURCES = engine/src/stage_event_initialization.cpp engine/src/fixed_data_resource.cpp $(OBJECT_RESTART_EXECUTION_SOURCES)
STAGE_EVENT_INITIALIZATION_HEADERS = engine/include/ms5/stage_event_initialization.h engine/include/ms5/fixed_data_resource.h $(OBJECT_RESTART_EXECUTION_HEADERS)
build/initialize_stage_events: $(STAGE_EVENT_INITIALIZATION_SOURCES) $(STAGE_EVENT_INITIALIZATION_HEADERS) engine/tools/initialize_stage_events.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_EVENT_INITIALIZATION_SOURCES) engine/tools/initialize_stage_events.cpp -o $@
build/stage_event_initialization_test: $(STAGE_EVENT_INITIALIZATION_SOURCES) $(STAGE_EVENT_INITIALIZATION_HEADERS) engine/tests/stage_event_initialization_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_EVENT_INITIALIZATION_SOURCES) engine/tests/stage_event_initialization_test.cpp -o $@

build/step_scene_motion_bounds: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tools/step_scene_motion_bounds.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tools/step_scene_motion_bounds.cpp -o $@
build/scene_motion_bounds_test: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tests/scene_motion_bounds_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tests/scene_motion_bounds_test.cpp -o $@

build/step_scene_motion_pair: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tools/step_scene_motion_pair.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tools/step_scene_motion_pair.cpp -o $@
build/scene_motion_pair_test: $(SCENE_MOTION_SOURCES) $(SCENE_MOTION_HEADERS) engine/tests/scene_motion_pair_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_MOTION_SOURCES) engine/tests/scene_motion_pair_test.cpp -o $@

SCENE_CAMERA_SOURCES = engine/src/scene_camera.cpp $(SCENE_MOTION_SOURCES)
SCENE_CAMERA_HEADERS = engine/include/ms5/scene_camera.h $(SCENE_MOTION_HEADERS)
build/step_scene_camera: $(SCENE_CAMERA_SOURCES) $(SCENE_CAMERA_HEADERS) engine/tools/step_scene_camera.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_CAMERA_SOURCES) engine/tools/step_scene_camera.cpp -o $@
build/scene_camera_test: $(SCENE_CAMERA_SOURCES) $(SCENE_CAMERA_HEADERS) engine/tests/scene_camera_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_CAMERA_SOURCES) engine/tests/scene_camera_test.cpp -o $@

SCENE_FRAME_CONTROL_SOURCES = engine/src/scene_frame_control.cpp engine/src/fixed_data_resource.cpp
SCENE_FRAME_CONTROL_HEADERS = engine/include/ms5/scene_frame_control.h engine/include/ms5/scene_command.h engine/include/ms5/scene_script.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/step_scene_frame_control: $(SCENE_FRAME_CONTROL_SOURCES) $(SCENE_FRAME_CONTROL_HEADERS) engine/tools/step_scene_frame_control.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_FRAME_CONTROL_SOURCES) engine/tools/step_scene_frame_control.cpp -o $@
build/scene_frame_control_test: $(SCENE_FRAME_CONTROL_SOURCES) $(SCENE_FRAME_CONTROL_HEADERS) engine/tests/scene_frame_control_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_FRAME_CONTROL_SOURCES) engine/tests/scene_frame_control_test.cpp -o $@

SCENE_FRAME_SOURCES = $(sort engine/src/scene_frame.cpp $(SCENE_FRAME_CONTROL_SOURCES) $(SCENE_CAMERA_SOURCES) $(SCENE_UPDATE_SOURCES) $(SCENE_SCRIPT_RUN_SOURCES) $(SCENE_PLACEMENT_EXECUTION_SOURCES))
SCENE_FRAME_HEADERS = $(sort engine/include/ms5/scene_frame.h $(SCENE_FRAME_CONTROL_HEADERS) $(SCENE_CAMERA_HEADERS) $(SCENE_UPDATE_HEADERS) $(SCENE_SCRIPT_RUN_HEADERS) $(SCENE_PLACEMENT_EXECUTION_HEADERS))
build/step_scene_frame: $(SCENE_FRAME_SOURCES) $(SCENE_FRAME_HEADERS) engine/tools/step_scene_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_FRAME_SOURCES) engine/tools/step_scene_frame.cpp -o $@
build/scene_frame_test: $(SCENE_FRAME_SOURCES) $(SCENE_FRAME_HEADERS) engine/tests/scene_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SCENE_FRAME_SOURCES) engine/tests/scene_frame_test.cpp -o $@

STAGE_INPUT_SOURCES = engine/src/stage_input.cpp engine/src/fixed_data_resource.cpp
STAGE_INPUT_HEADERS = engine/include/ms5/stage_input.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/step_stage_input: $(STAGE_INPUT_SOURCES) $(STAGE_INPUT_HEADERS) engine/tools/step_stage_input.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_INPUT_SOURCES) engine/tools/step_stage_input.cpp -o $@
build/stage_input_test: $(STAGE_INPUT_SOURCES) $(STAGE_INPUT_HEADERS) engine/tests/stage_input_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_INPUT_SOURCES) engine/tests/stage_input_test.cpp -o $@

STAGE_INPUT_CALLBACK_SOURCES = engine/src/stage_input_callback.cpp $(STAGE_INPUT_SOURCES)
STAGE_INPUT_CALLBACK_HEADERS = engine/include/ms5/stage_input_callback.h $(STAGE_INPUT_HEADERS)
build/step_stage_input_callback: $(STAGE_INPUT_CALLBACK_SOURCES) $(STAGE_INPUT_CALLBACK_HEADERS) engine/tools/step_stage_input_callback.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_INPUT_CALLBACK_SOURCES) engine/tools/step_stage_input_callback.cpp -o $@
build/stage_input_callback_test: $(STAGE_INPUT_CALLBACK_SOURCES) $(STAGE_INPUT_CALLBACK_HEADERS) engine/tests/stage_input_callback_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_INPUT_CALLBACK_SOURCES) engine/tests/stage_input_callback_test.cpp -o $@

STAGE_INPUT_LOOP_SOURCES = $(sort engine/src/stage_input_loop.cpp $(STAGE_INPUT_CALLBACK_SOURCES) $(PLAYER_RECORD_CAPTURE_SOURCES))
STAGE_INPUT_LOOP_HEADERS = $(sort engine/include/ms5/stage_input_loop.h $(STAGE_INPUT_CALLBACK_HEADERS) $(PLAYER_RECORD_CAPTURE_HEADERS))
build/step_stage_input_loop: $(STAGE_INPUT_LOOP_SOURCES) $(STAGE_INPUT_LOOP_HEADERS) engine/tools/step_stage_input_loop.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_INPUT_LOOP_SOURCES) engine/tools/step_stage_input_loop.cpp -o $@
build/stage_input_loop_test: $(STAGE_INPUT_LOOP_SOURCES) $(STAGE_INPUT_LOOP_HEADERS) engine/tests/stage_input_loop_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_INPUT_LOOP_SOURCES) engine/tests/stage_input_loop_test.cpp -o $@

STAGE_CUE_CONTROL_SOURCES = engine/src/stage_cue_control.cpp engine/src/object_allocation.cpp engine/src/fixed_data_resource.cpp
STAGE_CUE_CONTROL_HEADERS = engine/include/ms5/stage_cue_control.h engine/include/ms5/object_allocation.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/step_stage_cue_control: $(STAGE_CUE_CONTROL_SOURCES) $(STAGE_CUE_CONTROL_HEADERS) engine/tools/step_stage_cue_control.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_CUE_CONTROL_SOURCES) engine/tools/step_stage_cue_control.cpp -o $@
build/stage_cue_control_test: $(STAGE_CUE_CONTROL_SOURCES) $(STAGE_CUE_CONTROL_HEADERS) engine/tests/stage_cue_control_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_CUE_CONTROL_SOURCES) engine/tests/stage_cue_control_test.cpp -o $@

SPRITE_SUBMIT_EXECUTION_SOURCES = engine/src/sprite_submit_execution.cpp
SPRITE_SUBMIT_EXECUTION_HEADERS = engine/include/ms5/sprite_submit_execution.h engine/include/ms5/sprite_producer.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/execute_sprite_submit: $(SPRITE_SUBMIT_EXECUTION_SOURCES) $(SPRITE_SUBMIT_EXECUTION_HEADERS) engine/tools/execute_sprite_submit.cpp | build
	$(CXX) $(CXXFLAGS) $(SPRITE_SUBMIT_EXECUTION_SOURCES) engine/tools/execute_sprite_submit.cpp -o $@
build/sprite_submit_execution_test: $(SPRITE_SUBMIT_EXECUTION_SOURCES) $(SPRITE_SUBMIT_EXECUTION_HEADERS) engine/tests/sprite_submit_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SPRITE_SUBMIT_EXECUTION_SOURCES) engine/tests/sprite_submit_execution_test.cpp -o $@

STAGE_CUE_FRAME_SOURCES = $(sort engine/src/stage_cue_frame.cpp engine/src/scene_node.cpp $(STAGE_CUE_CONTROL_SOURCES) $(SPRITE_SUBMIT_EXECUTION_SOURCES))
STAGE_CUE_FRAME_HEADERS = $(sort engine/include/ms5/stage_cue_frame.h engine/include/ms5/scene_node.h $(STAGE_CUE_CONTROL_HEADERS) $(SPRITE_SUBMIT_EXECUTION_HEADERS))
build/step_stage_cue_frame: $(STAGE_CUE_FRAME_SOURCES) $(STAGE_CUE_FRAME_HEADERS) engine/tools/step_stage_cue_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_CUE_FRAME_SOURCES) engine/tools/step_stage_cue_frame.cpp -o $@
build/stage_cue_frame_test: $(STAGE_CUE_FRAME_SOURCES) $(STAGE_CUE_FRAME_HEADERS) engine/tests/stage_cue_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_CUE_FRAME_SOURCES) engine/tests/stage_cue_frame_test.cpp -o $@

STAGE_BUFFER_FRAME_SOURCES = engine/src/stage_buffer_frame.cpp engine/src/sprite_submit_execution.cpp engine/src/fixed_data_resource.cpp
STAGE_BUFFER_FRAME_HEADERS = engine/include/ms5/stage_buffer_frame.h $(SPRITE_SUBMIT_EXECUTION_HEADERS)
build/step_stage_buffer_frame: $(STAGE_BUFFER_FRAME_SOURCES) $(STAGE_BUFFER_FRAME_HEADERS) engine/tools/step_stage_buffer_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_BUFFER_FRAME_SOURCES) engine/tools/step_stage_buffer_frame.cpp -o $@
build/stage_buffer_frame_test: $(STAGE_BUFFER_FRAME_SOURCES) $(STAGE_BUFFER_FRAME_HEADERS) engine/tests/stage_buffer_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_BUFFER_FRAME_SOURCES) engine/tests/stage_buffer_frame_test.cpp -o $@

STAGE_REGION_FRAME_SOURCES = engine/src/stage_region_frame.cpp engine/src/fixed_data_resource.cpp
STAGE_REGION_FRAME_HEADERS = engine/include/ms5/stage_region_frame.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/step_stage_region_frame: $(STAGE_REGION_FRAME_SOURCES) $(STAGE_REGION_FRAME_HEADERS) engine/tools/step_stage_region_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_REGION_FRAME_SOURCES) engine/tools/step_stage_region_frame.cpp -o $@
build/stage_region_frame_test: $(STAGE_REGION_FRAME_SOURCES) $(STAGE_REGION_FRAME_HEADERS) engine/tests/stage_region_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_REGION_FRAME_SOURCES) engine/tests/stage_region_frame_test.cpp -o $@


STAGE_SPATIAL_FRAME_SOURCES = engine/src/stage_spatial_frame.cpp engine/src/scene_node.cpp engine/src/fixed_data_resource.cpp
STAGE_SPATIAL_FRAME_HEADERS = engine/include/ms5/stage_spatial_frame.h engine/include/ms5/scene_node.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/fixed_data_resource.h
build/step_stage_spatial_frame: $(STAGE_SPATIAL_FRAME_SOURCES) $(STAGE_SPATIAL_FRAME_HEADERS) engine/tools/step_stage_spatial_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_SPATIAL_FRAME_SOURCES) engine/tools/step_stage_spatial_frame.cpp -o $@

build/stage_spatial_frame_test: $(STAGE_SPATIAL_FRAME_SOURCES) $(STAGE_SPATIAL_FRAME_HEADERS) engine/tests/stage_spatial_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_SPATIAL_FRAME_SOURCES) engine/tests/stage_spatial_frame_test.cpp -o $@


SOUND_BYTE_EXECUTION_HEADERS = engine/include/ms5/sound_byte_execution.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/video_port.h
build/execute_sound_byte: engine/src/sound_byte_execution.cpp engine/tools/execute_sound_byte.cpp $(SOUND_BYTE_EXECUTION_HEADERS) | build
	$(CXX) $(CXXFLAGS) engine/src/sound_byte_execution.cpp engine/tools/execute_sound_byte.cpp -o $@

build/sound_byte_execution_test: engine/src/sound_byte_execution.cpp engine/tests/sound_byte_execution_test.cpp $(SOUND_BYTE_EXECUTION_HEADERS) | build
	$(CXX) $(CXXFLAGS) engine/src/sound_byte_execution.cpp engine/tests/sound_byte_execution_test.cpp -o $@

SOUND_CANCEL_EXECUTION_SOURCES = engine/src/sound_cancel_execution.cpp engine/src/sound_byte_execution.cpp
SOUND_CANCEL_EXECUTION_HEADERS = engine/include/ms5/sound_cancel_execution.h $(SOUND_BYTE_EXECUTION_HEADERS)
build/execute_sound_cancel: $(SOUND_CANCEL_EXECUTION_SOURCES) $(SOUND_CANCEL_EXECUTION_HEADERS) engine/tools/execute_sound_cancel.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_CANCEL_EXECUTION_SOURCES) engine/tools/execute_sound_cancel.cpp -o $@
build/sound_cancel_execution_test: $(SOUND_CANCEL_EXECUTION_SOURCES) $(SOUND_CANCEL_EXECUTION_HEADERS) engine/tests/sound_cancel_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_CANCEL_EXECUTION_SOURCES) engine/tests/sound_cancel_execution_test.cpp -o $@

SOUND_WORD_EXECUTION_SOURCES = engine/src/sound_word_execution.cpp engine/src/sound_byte_execution.cpp
SOUND_WORD_EXECUTION_HEADERS = engine/include/ms5/sound_word_execution.h $(SOUND_BYTE_EXECUTION_HEADERS)
build/execute_sound_word: $(SOUND_WORD_EXECUTION_SOURCES) $(SOUND_WORD_EXECUTION_HEADERS) engine/tools/execute_sound_word.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_WORD_EXECUTION_SOURCES) engine/tools/execute_sound_word.cpp -o $@
build/sound_word_execution_test: $(SOUND_WORD_EXECUTION_SOURCES) $(SOUND_WORD_EXECUTION_HEADERS) engine/tests/sound_word_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(SOUND_WORD_EXECUTION_SOURCES) engine/tests/sound_word_execution_test.cpp -o $@

STAGE_SOUND_FRAME_SOURCES = engine/src/stage_sound_frame.cpp engine/src/sound_word_execution.cpp engine/src/sound_cancel_execution.cpp engine/src/sound_byte_execution.cpp
STAGE_SOUND_FRAME_HEADERS = engine/include/ms5/stage_sound_frame.h $(SOUND_WORD_EXECUTION_HEADERS) $(SOUND_CANCEL_EXECUTION_HEADERS)
build/step_stage_sound_frame: $(STAGE_SOUND_FRAME_SOURCES) $(STAGE_SOUND_FRAME_HEADERS) engine/tools/step_stage_sound_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_SOUND_FRAME_SOURCES) engine/tools/step_stage_sound_frame.cpp -o $@
build/stage_sound_frame_test: $(STAGE_SOUND_FRAME_SOURCES) $(STAGE_SOUND_FRAME_HEADERS) engine/tests/stage_sound_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_SOUND_FRAME_SOURCES) engine/tests/stage_sound_frame_test.cpp -o $@

STAGE_FRAME_SOURCES = $(sort engine/src/stage_frame.cpp $(SCENE_FRAME_SOURCES) $(STAGE_INPUT_LOOP_SOURCES) $(STAGE_BUFFER_FRAME_SOURCES) $(STAGE_REGION_FRAME_SOURCES) $(STAGE_SPATIAL_FRAME_SOURCES) $(STAGE_CUE_FRAME_SOURCES) $(STAGE_SOUND_FRAME_SOURCES))
STAGE_FRAME_HEADERS = $(sort engine/include/ms5/stage_frame.h $(SCENE_FRAME_HEADERS) $(STAGE_INPUT_LOOP_HEADERS) $(STAGE_BUFFER_FRAME_HEADERS) $(STAGE_REGION_FRAME_HEADERS) $(STAGE_SPATIAL_FRAME_HEADERS) $(STAGE_CUE_FRAME_HEADERS) $(STAGE_SOUND_FRAME_HEADERS))
build/step_stage_frame: $(STAGE_FRAME_SOURCES) $(STAGE_FRAME_HEADERS) engine/tools/step_stage_frame.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_FRAME_SOURCES) engine/tools/step_stage_frame.cpp -o $@
build/stage_frame_test: $(STAGE_FRAME_SOURCES) $(STAGE_FRAME_HEADERS) engine/tests/stage_frame_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_FRAME_SOURCES) engine/tests/stage_frame_test.cpp -o $@

STAGE_ENTRY_BODY_SOURCES = $(sort engine/src/stage_entry_body.cpp $(STAGE_FRAME_SOURCES) $(SCENE_GENERAL_INITIALIZATION_SOURCES) $(STAGE_EVENT_INITIALIZATION_SOURCES))
STAGE_ENTRY_BODY_HEADERS = $(sort engine/include/ms5/stage_entry_body.h $(STAGE_FRAME_HEADERS) $(SCENE_GENERAL_INITIALIZATION_HEADERS) $(STAGE_EVENT_INITIALIZATION_HEADERS))
build/step_stage_entry_body: $(STAGE_ENTRY_BODY_SOURCES) $(STAGE_ENTRY_BODY_HEADERS) engine/tools/step_stage_entry_body.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ENTRY_BODY_SOURCES) engine/tools/step_stage_entry_body.cpp -o $@
build/stage_entry_body_test: $(STAGE_ENTRY_BODY_SOURCES) $(STAGE_ENTRY_BODY_HEADERS) engine/tests/stage_entry_body_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ENTRY_BODY_SOURCES) engine/tests/stage_entry_body_test.cpp -o $@

PALETTE_EFFECT_EXECUTION_SOURCES = engine/src/palette_effect_execution.cpp
PALETTE_EFFECT_EXECUTION_HEADERS = engine/include/ms5/palette_effect_execution.h engine/include/ms5/object_restart_execution.h engine/include/ms5/video_port.h
build/execute_palette_effect: $(PALETTE_EFFECT_EXECUTION_SOURCES) $(PALETTE_EFFECT_EXECUTION_HEADERS) engine/tools/execute_palette_effect.cpp | build
	$(CXX) $(CXXFLAGS) $(PALETTE_EFFECT_EXECUTION_SOURCES) engine/tools/execute_palette_effect.cpp -o $@
build/palette_effect_execution_test: $(PALETTE_EFFECT_EXECUTION_SOURCES) $(PALETTE_EFFECT_EXECUTION_HEADERS) engine/src/palette_control.cpp engine/include/ms5/palette_control.h engine/tests/palette_effect_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(PALETTE_EFFECT_EXECUTION_SOURCES) engine/src/palette_control.cpp engine/tests/palette_effect_execution_test.cpp -o $@

build/reset_game_screen_full: engine/src/game_screen_reset.cpp $(GAME_SCREEN_RESET_HEADERS) engine/tools/reset_game_screen_full.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_screen_reset.cpp engine/tools/reset_game_screen_full.cpp -o $@
build/game_screen_reset_execution_test: engine/src/game_screen_reset.cpp $(GAME_SCREEN_RESET_HEADERS) engine/tests/game_screen_reset_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) engine/src/game_screen_reset.cpp engine/tests/game_screen_reset_execution_test.cpp -o $@

STAGE_BLOCK_DRAW_SOURCES = engine/src/stage_block_draw.cpp engine/src/fixed_data_resource.cpp
STAGE_BLOCK_DRAW_HEADERS = engine/include/ms5/stage_block_draw.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/object_restart_execution.h engine/include/ms5/video_port.h
build/execute_stage_block_draw: $(STAGE_BLOCK_DRAW_SOURCES) $(STAGE_BLOCK_DRAW_HEADERS) engine/tools/execute_stage_block_draw.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_BLOCK_DRAW_SOURCES) engine/tools/execute_stage_block_draw.cpp -o $@
build/stage_block_draw_test: $(STAGE_BLOCK_DRAW_SOURCES) $(STAGE_BLOCK_DRAW_HEADERS) engine/tests/stage_block_draw_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_BLOCK_DRAW_SOURCES) engine/tests/stage_block_draw_test.cpp -o $@

STAGE_ACTIVATION_PREFIX_SOURCES = $(sort $(STAGE_BLOCK_DRAW_SOURCES) engine/src/stage_activation_prefix.cpp)
STAGE_ACTIVATION_PREFIX_HEADERS = $(sort $(STAGE_BLOCK_DRAW_HEADERS) engine/include/ms5/stage_activation_prefix.h)
build/initialize_stage_activation_prefix: $(STAGE_ACTIVATION_PREFIX_SOURCES) $(STAGE_ACTIVATION_PREFIX_HEADERS) engine/tools/initialize_stage_activation_prefix.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ACTIVATION_PREFIX_SOURCES) engine/tools/initialize_stage_activation_prefix.cpp -o $@
build/stage_activation_prefix_test: $(STAGE_ACTIVATION_PREFIX_SOURCES) $(STAGE_ACTIVATION_PREFIX_HEADERS) engine/tests/stage_activation_prefix_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ACTIVATION_PREFIX_SOURCES) engine/tests/stage_activation_prefix_test.cpp -o $@

PALETTE_BLEND_EXECUTION_SOURCES = engine/src/palette_blend_execution.cpp engine/src/palette_control.cpp
PALETTE_BLEND_EXECUTION_HEADERS = engine/include/ms5/palette_blend_execution.h engine/include/ms5/palette_control.h engine/include/ms5/object_restart_execution.h engine/include/ms5/video_port.h
build/execute_palette_blend: $(PALETTE_BLEND_EXECUTION_SOURCES) $(PALETTE_BLEND_EXECUTION_HEADERS) engine/tools/execute_palette_blend.cpp | build
	$(CXX) $(CXXFLAGS) $(PALETTE_BLEND_EXECUTION_SOURCES) engine/tools/execute_palette_blend.cpp -o $@
build/palette_blend_execution_test: $(PALETTE_BLEND_EXECUTION_SOURCES) $(PALETTE_BLEND_EXECUTION_HEADERS) engine/tests/palette_blend_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(PALETTE_BLEND_EXECUTION_SOURCES) engine/tests/palette_blend_execution_test.cpp -o $@

STAGE_HUD_COUNTER_SOURCES = $(sort $(SOUND_WORD_EXECUTION_SOURCES) $(PALETTE_BLEND_EXECUTION_SOURCES) $(STAGE_BLOCK_DRAW_SOURCES) engine/src/stage_hud_counter.cpp)
STAGE_HUD_COUNTER_HEADERS = $(sort $(SOUND_WORD_EXECUTION_HEADERS) $(PALETTE_BLEND_EXECUTION_HEADERS) $(STAGE_BLOCK_DRAW_HEADERS) engine/include/ms5/stage_hud_counter.h)
build/step_stage_hud_counter: $(STAGE_HUD_COUNTER_SOURCES) $(STAGE_HUD_COUNTER_HEADERS) engine/tools/step_stage_hud_counter.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_HUD_COUNTER_SOURCES) engine/tools/step_stage_hud_counter.cpp -o $@
build/stage_hud_counter_test: $(STAGE_HUD_COUNTER_SOURCES) $(STAGE_HUD_COUNTER_HEADERS) engine/tests/stage_hud_counter_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_HUD_COUNTER_SOURCES) engine/tests/stage_hud_counter_test.cpp -o $@

STAGE_COUNTER_SOURCES = engine/src/stage_counter.cpp
STAGE_COUNTER_HEADERS = engine/include/ms5/stage_counter.h engine/include/ms5/object_restart_execution.h engine/include/ms5/video_port.h
build/execute_stage_counter: $(STAGE_COUNTER_SOURCES) $(STAGE_COUNTER_HEADERS) engine/tools/execute_stage_counter.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_COUNTER_SOURCES) engine/tools/execute_stage_counter.cpp -o $@
build/stage_counter_test: $(STAGE_COUNTER_SOURCES) $(STAGE_COUNTER_HEADERS) engine/tests/stage_counter_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_COUNTER_SOURCES) engine/tests/stage_counter_test.cpp -o $@

STAGE_READINESS_SOURCES = engine/src/stage_readiness.cpp
STAGE_READINESS_HEADERS = engine/include/ms5/stage_readiness.h engine/include/ms5/object_restart_execution.h engine/include/ms5/video_port.h
build/execute_stage_readiness: $(STAGE_READINESS_SOURCES) $(STAGE_READINESS_HEADERS) engine/tools/execute_stage_readiness.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_READINESS_SOURCES) engine/tools/execute_stage_readiness.cpp -o $@
build/stage_readiness_test: $(STAGE_READINESS_SOURCES) $(STAGE_READINESS_HEADERS) engine/tests/stage_readiness_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_READINESS_SOURCES) engine/tests/stage_readiness_test.cpp -o $@

STAGE_ACTIVATION_HELPERS_SOURCES = engine/src/stage_activation_helpers.cpp
STAGE_ACTIVATION_HELPERS_HEADERS = engine/include/ms5/stage_activation_helpers.h engine/include/ms5/object_restart_execution.h engine/include/ms5/video_port.h
build/execute_stage_activation_helper: $(STAGE_ACTIVATION_HELPERS_SOURCES) $(STAGE_ACTIVATION_HELPERS_HEADERS) engine/tools/execute_stage_activation_helper.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ACTIVATION_HELPERS_SOURCES) engine/tools/execute_stage_activation_helper.cpp -o $@
build/stage_activation_helpers_test: $(STAGE_ACTIVATION_HELPERS_SOURCES) $(STAGE_ACTIVATION_HELPERS_HEADERS) engine/tests/stage_activation_helpers_test.cpp | build
	$(CXX) $(CXXFLAGS) $(STAGE_ACTIVATION_HELPERS_SOURCES) engine/tests/stage_activation_helpers_test.cpp -o $@

OBJECT_SPRITE_WRAPPER_SOURCES = $(sort engine/src/object_sprite_wrapper.cpp $(SPRITE_SUBMIT_EXECUTION_SOURCES))
OBJECT_SPRITE_WRAPPER_HEADERS = $(sort engine/include/ms5/object_sprite_wrapper.h $(SPRITE_SUBMIT_EXECUTION_HEADERS))
build/execute_object_sprite_wrapper: $(OBJECT_SPRITE_WRAPPER_SOURCES) $(OBJECT_SPRITE_WRAPPER_HEADERS) engine/tools/execute_object_sprite_wrapper.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_SPRITE_WRAPPER_SOURCES) engine/tools/execute_object_sprite_wrapper.cpp -o $@
build/object_sprite_wrapper_test: $(OBJECT_SPRITE_WRAPPER_SOURCES) $(OBJECT_SPRITE_WRAPPER_HEADERS) engine/tests/object_sprite_wrapper_test.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_SPRITE_WRAPPER_SOURCES) engine/tests/object_sprite_wrapper_test.cpp -o $@

OBJECT_SOUND_LOOKUP_SOURCES = $(sort engine/src/object_sound_lookup.cpp $(SOUND_WORD_EXECUTION_SOURCES))
OBJECT_SOUND_LOOKUP_HEADERS = $(sort engine/include/ms5/object_sound_lookup.h $(SOUND_WORD_EXECUTION_HEADERS))
build/execute_object_sound_lookup: $(OBJECT_SOUND_LOOKUP_SOURCES) engine/src/fixed_data_resource.cpp $(OBJECT_SOUND_LOOKUP_HEADERS) engine/tools/execute_object_sound_lookup.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_SOUND_LOOKUP_SOURCES) engine/src/fixed_data_resource.cpp engine/tools/execute_object_sound_lookup.cpp -o $@
build/object_sound_lookup_test: $(OBJECT_SOUND_LOOKUP_SOURCES) $(OBJECT_SOUND_LOOKUP_HEADERS) engine/tests/object_sound_lookup_test.cpp | build
	$(CXX) $(CXXFLAGS) $(OBJECT_SOUND_LOOKUP_SOURCES) engine/tests/object_sound_lookup_test.cpp -o $@

ANIMATION_EXECUTION_SOURCES = $(sort engine/src/animation_execution.cpp $(SPRITE_SUBMIT_EXECUTION_SOURCES) $(OBJECT_SOUND_LOOKUP_SOURCES))
ANIMATION_EXECUTION_HEADERS = $(sort engine/include/ms5/animation_execution.h engine/include/ms5/animation_resource.h $(SPRITE_SUBMIT_EXECUTION_HEADERS) $(OBJECT_SOUND_LOOKUP_HEADERS))
build/step_animation_execution: $(ANIMATION_EXECUTION_SOURCES) engine/src/animation_resource.cpp engine/src/fixed_data_resource.cpp $(ANIMATION_EXECUTION_HEADERS) engine/tools/step_animation_execution.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_EXECUTION_SOURCES) engine/src/animation_resource.cpp engine/src/fixed_data_resource.cpp engine/tools/step_animation_execution.cpp -o $@
build/animation_execution_test: $(ANIMATION_EXECUTION_SOURCES) $(ANIMATION_EXECUTION_HEADERS) engine/tests/animation_execution_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_EXECUTION_SOURCES) engine/tests/animation_execution_test.cpp -o $@

build/step_animation_sound_execution: $(ANIMATION_EXECUTION_SOURCES) engine/src/animation_resource.cpp engine/src/fixed_data_resource.cpp $(ANIMATION_EXECUTION_HEADERS) engine/tools/step_animation_sound_execution.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_EXECUTION_SOURCES) engine/src/animation_resource.cpp engine/src/fixed_data_resource.cpp engine/tools/step_animation_sound_execution.cpp -o $@

PROGRAM_BUS_SOURCES = engine/src/program_bus.cpp engine/src/animation_banked_lookup.cpp engine/src/physical_rom_resource.cpp
PROGRAM_BUS_HEADERS = engine/include/ms5/physical_rom_resource.h engine/include/ms5/program_bus.h engine/include/ms5/animation_banked_lookup.h engine/include/ms5/fixed_data_resource.h engine/include/ms5/scene_map_transfer.h engine/include/ms5/video_port.h
build/execute_animation_banked_lookup: $(PROGRAM_BUS_SOURCES) $(PROGRAM_BUS_HEADERS) engine/src/fixed_data_resource.cpp engine/tools/execute_animation_banked_lookup.cpp | build
	$(CXX) $(CXXFLAGS) $(PROGRAM_BUS_SOURCES) engine/src/fixed_data_resource.cpp engine/tools/execute_animation_banked_lookup.cpp -o $@
build/program_bus_test: $(PROGRAM_BUS_SOURCES) $(PROGRAM_BUS_HEADERS) engine/tests/program_bus_test.cpp | build
	$(CXX) $(CXXFLAGS) $(PROGRAM_BUS_SOURCES) engine/tests/program_bus_test.cpp -o $@

build/physical_rom_resource_test: $(PROGRAM_BUS_SOURCES) $(PROGRAM_BUS_HEADERS) engine/src/fixed_data_resource.cpp engine/tests/physical_rom_resource_test.cpp | build
	$(CXX) $(CXXFLAGS) $(PROGRAM_BUS_SOURCES) engine/src/fixed_data_resource.cpp engine/tests/physical_rom_resource_test.cpp -o $@

test: build/program_stack_test
build/program_stack_test: engine/src/program_stack.cpp engine/src/program_bus.cpp engine/tests/program_stack_test.cpp engine/include/ms5/program_stack.h $(PROGRAM_BUS_HEADERS) | build
	$(CXX) $(CXXFLAGS) engine/src/program_stack.cpp engine/src/program_bus.cpp engine/tests/program_stack_test.cpp -o $@

ANIMATION_MACHINE_SOURCES = engine/src/animation_machine.cpp engine/src/animation_machine_interpreter.cpp engine/src/animation_machine_sprite.cpp engine/src/animation_machine_sound.cpp engine/src/animation_machine_readiness.cpp engine/src/animation_machine_hud.cpp engine/src/animation_machine_transition.cpp engine/src/animation_machine_exit.cpp engine/src/animation_machine_screen.cpp engine/src/animation_machine_cleanup.cpp engine/src/animation_machine_scene.cpp engine/src/animation_machine_palette_bind.cpp engine/src/animation_machine_map_transfer.cpp engine/src/animation_machine_fade_card.cpp engine/src/animation_machine_card_child.cpp engine/src/animation_machine_card_menu.cpp engine/src/animation_machine_card_menu_open.cpp engine/src/animation_machine_card_menu_input.cpp engine/src/animation_machine_card_menu_close.cpp engine/src/animation_machine_card_menu_save.cpp engine/src/animation_machine_card_menu_nested.cpp engine/src/animation_machine_frame_helpers.cpp engine/src/animation_machine_scene_core.cpp engine/src/animation_machine_motion_walk.cpp engine/src/animation_machine_scene_update.cpp engine/src/animation_machine_script_placement.cpp engine/src/animation_machine_input.cpp engine/src/animation_machine_buffer_cue.cpp engine/src/animation_machine_stage_entry.cpp engine/src/animation_machine_area_clear.cpp engine/src/palette_effect_execution.cpp engine/src/program_bus.cpp engine/src/program_stack.cpp
ANIMATION_MACHINE_HEADERS = engine/include/ms5/palette_effect_execution.h engine/include/ms5/object_restart_execution.h engine/include/ms5/animation_machine.h engine/src/animation_machine_internal.h engine/include/ms5/program_stack.h $(PROGRAM_BUS_HEADERS)
test: build/animation_machine_test build/animation_machine_device_test
build/animation_machine_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_test.cpp -o $@
build/animation_machine_device_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_device_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_device_test.cpp -o $@

test: build/animation_machine_callers_test
build/animation_machine_callers_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_callers_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_callers_test.cpp -o $@

test: build/animation_machine_carry_test
build/animation_machine_carry_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_carry_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_carry_test.cpp -o $@

test: build/animation_machine_activation_test
build/animation_machine_activation_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_activation_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_activation_test.cpp -o $@

test: build/animation_machine_readiness_test
build/animation_machine_readiness_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_readiness_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_readiness_test.cpp -o $@

test: build/animation_machine_hud_test
build/animation_machine_hud_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_hud_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_hud_test.cpp -o $@

test: build/animation_machine_transition_test
build/animation_machine_transition_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_transition_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_transition_test.cpp -o $@

test: build/animation_machine_exit_test
build/animation_machine_exit_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_exit_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_exit_test.cpp -o $@

test: build/animation_machine_screen_test
build/animation_machine_screen_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_screen_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_screen_test.cpp -o $@

test: build/animation_machine_cleanup_test
build/animation_machine_cleanup_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_cleanup_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_cleanup_test.cpp -o $@

test: build/animation_machine_scene_test
build/animation_machine_scene_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_scene_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_scene_test.cpp -o $@

test: build/animation_machine_palette_bind_test
build/animation_machine_palette_bind_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_palette_bind_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_palette_bind_test.cpp -o $@

test: build/animation_machine_map_transfer_test
build/animation_machine_map_transfer_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_map_transfer_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_map_transfer_test.cpp -o $@

test: build/animation_machine_fade_card_test
build/animation_machine_fade_card_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_fade_card_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_fade_card_test.cpp -o $@

test: build/animation_machine_card_child_test
build/animation_machine_card_child_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_card_child_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_card_child_test.cpp -o $@

test: build/animation_machine_card_menu_test
build/animation_machine_card_menu_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_card_menu_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_card_menu_test.cpp -o $@

test: build/animation_machine_card_menu_open_test
build/animation_machine_card_menu_open_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_card_menu_open_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_card_menu_open_test.cpp -o $@

test: build/animation_machine_card_menu_input_test
build/animation_machine_card_menu_input_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_card_menu_input_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_card_menu_input_test.cpp -o $@

test: build/animation_machine_card_menu_close_test
build/animation_machine_card_menu_close_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_card_menu_close_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_card_menu_close_test.cpp -o $@

test: build/animation_machine_card_menu_save_test
build/animation_machine_card_menu_save_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_card_menu_save_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_card_menu_save_test.cpp -o $@

test: build/animation_machine_card_menu_nested_test
build/animation_machine_card_menu_nested_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_card_menu_nested_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_card_menu_nested_test.cpp -o $@

test: build/animation_machine_frame_helpers_test
build/animation_machine_frame_helpers_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_frame_helpers_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_frame_helpers_test.cpp -o $@

test: build/animation_machine_scene_core_test
build/animation_machine_scene_core_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_scene_core_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_scene_core_test.cpp -o $@

test: build/animation_machine_motion_walk_test
build/animation_machine_motion_walk_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_motion_walk_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_motion_walk_test.cpp -o $@

test: build/animation_machine_scene_update_test
build/animation_machine_scene_update_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_scene_update_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_scene_update_test.cpp -o $@

test: build/animation_machine_script_placement_test
build/animation_machine_script_placement_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_script_placement_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_script_placement_test.cpp -o $@

test: build/animation_machine_input_test
build/animation_machine_input_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_input_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_input_test.cpp -o $@

test: build/animation_machine_buffer_cue_test
build/animation_machine_buffer_cue_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_buffer_cue_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_buffer_cue_test.cpp -o $@

test: build/animation_machine_stage_entry_test
build/animation_machine_stage_entry_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/include/ms5/palette_transfer.h engine/include/ms5/palette_upload.h engine/tests/animation_machine_stage_entry_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/src/palette_transfer.cpp engine/src/palette_upload.cpp engine/tests/animation_machine_stage_entry_test.cpp -o $@

test: build/animation_machine_area_clear_test
build/animation_machine_area_clear_test: $(ANIMATION_MACHINE_SOURCES) $(ANIMATION_MACHINE_HEADERS) engine/tests/animation_machine_area_clear_test.cpp | build
	$(CXX) $(CXXFLAGS) $(ANIMATION_MACHINE_SOURCES) engine/tests/animation_machine_area_clear_test.cpp -o $@
