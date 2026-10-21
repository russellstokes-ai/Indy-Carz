-- PRIVATE arcade-runtime instrumentation for user-owned original Indy Heat ROM.
-- Tested in MAME 0.264 with actual rev-1 ROM. No ROM content is checked in.
--
-- mkdir -p local/engine-extraction/runtime
-- INDY_CAPTURE_OUT=local/engine-extraction/runtime \
-- INDY_CAPTURE_COIN=1 INDY_CAPTURE_SCREEN=1 \
-- mame indyheat -rompath /PRIVATE/ROM -video none -sound none \
--   -nothrottle -seconds_to_run 230 -autoboot_script tools/mame_capture_live_arcade.lua
--
-- AUTO_COIN is optional and explicitly opt-in. Screenshots and QRAM remain
-- locally private; never commit original program, art or live memory dumps.
--
-- MAME Ataxx hardware mapping: F4 (master bank control), 0xA000-0xDFFF.
-- (control & 0x30) == 0x20 selects QRAM, (control & 0xC0) << 8
-- selects one of four 16,384-byte banks. There is NO public :qram share.
local OUT = os.getenv('INDY_CAPTURE_OUT') or 'local/engine-extraction/runtime'
local AUTO_COIN = os.getenv('INDY_CAPTURE_COIN') == '1'
local MAKE_SCREENS = os.getenv('INDY_CAPTURE_SCREEN') == '1'
local MAX_FRAMES = tonumber(os.getenv('INDY_CAPTURE_FRAMES') or '12000')
local QRAM_INTERVAL = tonumber(os.getenv('INDY_QRAM_INTERVAL') or '300')
local RAM_INTERVAL = tonumber(os.getenv('INDY_RAM_SAMPLE_EVERY') or '1')
local MAX_QRAM_CAPTURES = 350
assert(MAX_FRAMES >= 1 and MAX_FRAMES <= 500000)
assert(QRAM_INTERVAL >= 30 and QRAM_INTERVAL <= 3600)
assert(RAM_INTERVAL >= 1 and RAM_INTERVAL <= 120)

local frame = 0
local qram_count = 0
local previous_qram = nil
local last_course = nil
local last_round = nil
local closed = false
local program = nil
local io_space = nil
local screen = nil
local coin_field = nil
local ram_bin, frame_index, transitions

local function le32(v)
    return string.char(v & 255, (v >> 8) & 255, (v >> 16) & 255, (v >> 24) & 255)
end

local function finish()
    if closed then return end
    closed = true
    if ram_bin then ram_bin:close() end
    if frame_index then frame_index:close() end
    if transitions then transitions:close() end
    if coin_field then coin_field:set_value(0) end
    print(string.format('INDY_LIVE: finished frame=%d QRAM captures=%d', frame, qram_count))
end

local function setup()
    local machine = manager.machine
    local master = assert(machine.devices[':master'], 'No original arcade :master')
    program = assert(master.spaces['program'], 'Original master program missing')
    io_space = assert(master.spaces['io'], 'Original master I/O missing')
    screen = assert(machine.screens[':screen'], 'Original arcade screen missing')
    coin_field = assert(machine.ioport.ports[':IN0'].fields['Coin 1'], 'Coin input missing')
    ram_bin = assert(io.open(OUT .. '/master_ram_frames.bin', 'wb'))
    frame_index = assert(io.open(OUT .. '/capture_index.csv', 'w'))
    transitions = assert(io.open(OUT .. '/course_transitions.csv', 'w'))
    ram_bin:write('ICR1', le32(0xE000), le32(0xA00))
    frame_index:write('frame,course,round,e603,e608,callback0,callback1,callback2,qram_file\n')
    transitions:write('frame,course,round,e603,callback0,callback1,callback2\n')
    print('INDY_LIVE: original master program, IO, screen and coin field ready')
end

local function callback(slot)
    local start = 0xE094 + (slot * 0x100)
    return program:read_u8(start) | (program:read_u8(start+1) << 8)
end

local function original_qram()
    -- E608 is original master software bank shadow; the original game writes
    -- it before outputting F4. Compare the selected window before/after to
    -- catch disagreement rather than silently damage the running game state.
    local shadow = program:read_u8(0xE608)
    local before = program:read_range(0xA000, 0xA03F, 8)
    assert(type(before) == 'string' and #before == 64, 'Invalid original window prefix')
    local chunks = {}
    local ok, err = pcall(function()
        for bank = 0, 3 do
            local control = (shadow & 0x0F) | 0x20 | (bank << 6)
            io_space:write_u8(0xF4, control)
            chunks[#chunks+1] = program:read_range(0xA000, 0xDFFF, 8)
            assert(type(chunks[#chunks]) == 'string' and #chunks[#chunks] == 0x4000,
                   'Invalid original 16KiB QRAM window')
        end
    end)
    -- Restoration happens EVEN when the intermediate bank read fails.
    io_space:write_u8(0xF4, shadow)
    if not ok then error('Original QRAM bank read failed: ' .. tostring(err)) end
    assert(program:read_range(0xA000, 0xA03F, 8) == before,
           'Original CPU bank failed restore verification')
    local result = table.concat(chunks)
    assert(#result == 0x10000, 'Expected 65,536 original QRAM bytes')
    return result
end

local function qram_capture()
    local data = original_qram()
    if data == previous_qram then return '' end
    previous_qram = data
    qram_count = qram_count + 1
    local course, round = program:read_u8(0xE699), program:read_u8(0xE69B)
    local name = string.format('qram_%03d_f%07d_c%02d_r%02d.bin',
                               qram_count, frame, course, round)
    local out = assert(io.open(OUT .. '/' .. name, 'wb'))
    out:write(data)
    out:close()
    if MAKE_SCREENS then
        screen:snapshot(string.format('%s/screen_f%07d_c%02d_r%02d.png',
                       OUT, frame, course, round))
    end
    print(string.format('INDY_LIVE: QRAM=%d frame=%d course=%d round=%d',
                        qram_count, frame, course, round))
    return name
end

emu.register_frame_done(function()
    if closed then return end
    frame = frame + 1
    if frame == 1 then setup() end
    if AUTO_COIN and frame == 200 then coin_field:set_value(1) end
    if AUTO_COIN and frame == 215 then coin_field:set_value(0) end
    if frame > MAX_FRAMES then finish(); return end

    local course, round = program:read_u8(0xE699), program:read_u8(0xE69B)
    if course ~= last_course or round ~= last_round then
        transitions:write(string.format('%d,%d,%d,%d,%04X,%04X,%04X\n',
                          frame, course, round, program:read_u8(0xE603),
                          callback(0), callback(1), callback(2)))
        transitions:flush()
        last_course, last_round = course, round
    end
    if frame % RAM_INTERVAL == 0 then
        local ram = program:read_range(0xE000, 0xE9FF, 8)
        assert(#ram == 0xA00, 'Original 2560-byte RAM capture truncated')
        ram_bin:write(le32(frame), ram)
    end
    if frame % QRAM_INTERVAL == 0 then
        local file = ''
        if qram_count < MAX_QRAM_CAPTURES then file = qram_capture() end
        frame_index:write(string.format('%d,%d,%d,%d,%02X,%04X,%04X,%04X,%s\n',
            frame, course, round, program:read_u8(0xE603),
            program:read_u8(0xE608), callback(0), callback(1), callback(2), file))
        frame_index:flush()
        ram_bin:flush()
    end
    if frame == MAX_FRAMES then finish() end
end)
