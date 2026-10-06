CXX = clang++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra -pedantic -Iengine/include
PYTHON = .venv/bin/python

.PHONY: all test runtime-resources setup-tools
all: build/check_tiles build/reset_object

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

test: build/tile_resource_test build/object_state_test
	$(PYTHON) -m unittest discover -s tools/tests -v
	./build/tile_resource_test
	./build/object_state_test

runtime-resources:
	python3 tools/pack_tiles.py

setup-tools:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-analysis.txt
