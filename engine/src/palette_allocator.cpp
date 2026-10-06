#include "ms5/palette_allocator.h"

namespace {

const std::size_t node_base = 0x4d92;
const std::uint16_t free_sentinel = 0x1000;

std::uint16_t read_word(const std::vector<std::uint8_t>& ram,
                        std::size_t offset) {
    return static_cast<std::uint16_t>(
        (static_cast<unsigned int>(ram[offset]) << 8) | ram[offset + 1]);
}

void write_word(std::vector<std::uint8_t>& ram, std::size_t offset,
                std::uint16_t value) {
    ram[offset] = static_cast<std::uint8_t>(value >> 8);
    ram[offset + 1] = static_cast<std::uint8_t>(value);
}

bool is_node(std::uint16_t offset) {
    return offset <= 0xff0 && (offset & 15) == 0;
}

bool is_link(std::uint16_t offset) {
    return is_node(offset) || offset == free_sentinel ||
        (offset <= 0xff4 && (offset & 15) == 4);
}

bool validate_input(const std::vector<std::uint8_t>& ram,
                    std::size_t object, std::string& error) {
    if (ram.size() != 65536) {
        error = "RAM must contain exactly 65536 bytes at CPU 0x100000";
        return false;
    }
    if (object > ram.size() - 0x1e) {
        error = "object does not have 0x1e bytes available in RAM";
        return false;
    }
    if (ram[object + 0x1d] > 4) {
        error = "object palette count exceeds four";
        return false;
    }
    return true;
}

bool check_list_end(const std::vector<std::uint8_t>& ram,
                    std::uint16_t sentinel, std::string& error) {
    const std::uint16_t previous = read_word(ram, node_base + sentinel);
    const std::uint16_t next = read_word(ram, node_base + sentinel + 2);
    if (!is_link(previous) || !is_link(next) ||
        read_word(ram, node_base + previous + 2) != sentinel ||
        read_word(ram, node_base + next) != sentinel) {
        error = "corrupt palette sentinel links";
        return false;
    }
    return true;
}

bool unlink_node(std::vector<std::uint8_t>& ram, std::uint16_t node,
                 std::string& error) {
    const std::uint16_t previous = read_word(ram, node_base + node);
    const std::uint16_t next = read_word(ram, node_base + node + 2);
    if (!is_link(previous) || !is_link(next) || previous == node ||
        next == node || read_word(ram, node_base + previous + 2) != node ||
        read_word(ram, node_base + next) != node) {
        error = "corrupt palette node links";
        return false;
    }
    write_word(ram, node_base + previous + 2, next);
    write_word(ram, node_base + next, previous);
    return true;
}

} // namespace

namespace ms5 {

bool acquire_palette(std::vector<std::uint8_t>& ram, std::size_t object,
                     std::uint16_t id, std::uint8_t flags,
                     bool& allocated, std::string& error) {
    if (!validate_input(ram, object, error)) {
        return false;
    }
    const unsigned int count = ram[object + 0x1d];
    if (count == 4) {
        error = "original palette acquire TRAP: object already has four palettes";
        return false;
    }
    std::vector<std::uint8_t> result(ram);
    const std::uint16_t bucket = static_cast<std::uint16_t>((id & 255) * 16 + 4);
    if (!check_list_end(result, bucket, error)) {
        return false;
    }
    std::uint16_t selected = free_sentinel;
    if ((flags & 1) == 0) {
        std::uint16_t current = read_word(result, node_base + bucket + 2);
        unsigned int visits = 0;
        bool visited[256] = {};
        while (current != bucket) {
            if (!is_node(current) || visits == 256 || visited[current >> 4]) {
                error = "corrupt palette bucket chain";
                return false;
            }
            visited[current >> 4] = true;
            ++visits;
            if (read_word(result, node_base + current + 10) == id &&
                (result[node_base + current + 15] & 1) == 0) {
                selected = current;
                break;
            }
            current = read_word(result, node_base + current + 2);
        }
    }
    if (selected == free_sentinel) {
        if (!check_list_end(result, free_sentinel, error)) {
            return false;
        }
        selected = read_word(result, node_base + free_sentinel + 2);
        if (selected == free_sentinel) {
            if ((result[0xf000] & 4) != 0) {
                error = "palette exhaustion debug UI is unsupported";
                return false;
            }
            allocated = false;
            result[object + 0x14] = 0xff;
            ram.swap(result);
            error.clear();
            return true;
        }
        if (!is_node(selected)) {
            error = "corrupt palette free-list head";
            return false;
        }
        write_word(result, node_base + selected + 10, id);
        write_word(result, node_base + selected + 12, id);
        result[node_base + selected + 15] = static_cast<std::uint8_t>(flags | 0x80);
    }
    const std::uint16_t references = read_word(result, node_base + selected + 8);
    if (references != 0xffff) {
        write_word(result, node_base + selected + 8,
                   static_cast<std::uint16_t>(static_cast<unsigned int>(references) + 1));
    }
    if (read_word(result, node_base + bucket + 2) != selected) {
        if (!unlink_node(result, selected, error)) {
            return false;
        }
        const std::uint16_t old_next = read_word(result, node_base + bucket + 2);
        write_word(result, node_base + old_next, selected);
        write_word(result, node_base + selected + 2, old_next);
        write_word(result, node_base + selected, bucket);
        write_word(result, node_base + bucket + 2, selected);
    }
    const std::uint8_t slot = static_cast<std::uint8_t>(selected >> 4);
    result[object + 0x19 + count] = slot;
    result[object + 0x14] = slot;
    result[object + 0x1d] = static_cast<std::uint8_t>(count + 1);
    ram.swap(result);
    allocated = true;
    error.clear();
    return true;
}

bool release_palettes(std::vector<std::uint8_t>& ram, std::size_t object,
                      std::string& error) {
    if (!validate_input(ram, object, error)) {
        return false;
    }
    std::vector<std::uint8_t> result(ram);
    unsigned int count = result[object + 0x1d];
    while (count != 0) {
        --count;
        const std::uint16_t node = static_cast<std::uint16_t>(
            result[object + 0x19 + count] * 16);
        const std::uint16_t references = read_word(result, node_base + node + 8);
        if (references == 0 || references == 0xffff) {
            continue;
        }
        const std::uint16_t remaining = static_cast<std::uint16_t>(references - 1);
        write_word(result, node_base + node + 8, remaining);
        if (remaining != 0) {
            continue;
        }
        if (!unlink_node(result, node, error) ||
            !check_list_end(result, free_sentinel, error)) {
            return false;
        }
        const std::uint16_t old_tail = read_word(result, node_base + free_sentinel);
        write_word(result, node_base + node + 2, free_sentinel);
        write_word(result, node_base + node, old_tail);
        write_word(result, node_base + old_tail + 2, node);
        write_word(result, node_base + free_sentinel, node);
        write_word(result, node_base + node + 10, 0xffff);
        write_word(result, node_base + node + 12, 0xffff);
        result[node_base + node + 15] = 2;
    }
    result[object + 0x1d] = 0;
    ram.swap(result);
    error.clear();
    return true;
}

} // namespace ms5
