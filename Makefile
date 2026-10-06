CXX = clang++
CXXFLAGS = -std=c++11 -O2 -Wall -Wextra -pedantic -Iengine/include

.PHONY: all test runtime-resources
all: build/check_tiles

build:
	mkdir -p build

build/check_tiles: engine/src/tile_resource.cpp engine/tools/check_tiles.cpp engine/include/ms5/tile_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/tile_resource.cpp engine/tools/check_tiles.cpp -o $@

build/tile_resource_test: engine/src/tile_resource.cpp engine/tests/tile_resource_test.cpp engine/include/ms5/tile_resource.h | build
	$(CXX) $(CXXFLAGS) engine/src/tile_resource.cpp engine/tests/tile_resource_test.cpp -o $@

test: build/tile_resource_test
	python3 -m unittest discover -s tools/tests -v
	./build/tile_resource_test

runtime-resources:
	python3 tools/pack_tiles.py
