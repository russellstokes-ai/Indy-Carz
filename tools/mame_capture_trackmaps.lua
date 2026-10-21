-- Corrected private QRAM capture for original 1991 Indy Heat in MAME 0.264.
-- The original program does NOT expose a ':qram' share. Its 65536-byte
-- tilemap is memory-mapped in four 16384-byte banks at master A000-DFFF.
-- MAME ataxx_bankswitch controls this window via master I/O port F4:
--   (control & 0x30) == 0x20 selects QRAM
--   (control & 0xC0) << 8 selects the 16KiB bank.
--
-- mkdir -p local/track-recovery
-- INDY_TRACK_OUT=local/track-recovery INDY_CAPTURE_COIN=1 \
--   mame indyheat -rompath /PRIVATE/original-roms -video none -sound none \
--   -nothrottle -seconds_to_run 180 -autoboot_script tools/mame_capture_trackmaps.lua
-- Original screenshots, QRAM, ROM and all derived art remain PRIVATE.
local OUT = os.getenv('INDY_TRACK_OUT') or 'local/track-recovery'
local INTERVAL = tonumber(os.getenv('INDY_QRAM_INTERVAL') or '300')
local AUTO_COIN = os.getenv('INDY_CAPTURE_COIN') == '1'
local MAX_CAPTURES = 350
assert(INTERVAL >= 30 and INTERVAL <= 3600)
local frames = 0
local captures = 0
local previous = nil
local cpu = nil
local program = nil
local ports = nil
local coin = nil
local halted = false
local function initialize()
    cpu = assert(manager.machine.devices[':master'], 'Original master Z80 absent')
    program = assert(cpu.spaces['program'], 'Original program RAM missing')
    ports = assert(cpu.spaces['io'], 'Original master IO missing')
    coin = assert(manager.machine.ioport.ports[':IN0'].fields['Coin 1'], 'Coin input absent')
end
local function snapshot_original_qram()
    local saved = program:read_u8(0xE608) -- original bank-control shadow
    local original_window = program:read_range(0xA000, 0xA03F, 8)
    assert(type(original_window) == 'string' and #original_window == 64)
    local banks = {}
    local ok, err = pcall(function()
        for bank = 0, 3 do
            ports:write_u8(0xF4, (saved & 0x0F) | 0x20 | (bank << 6))
            banks[#banks+1] = program:read_range(0xA000, 0xDFFF, 8)
            assert(type(banks[#banks]) == 'string' and #banks[#banks] == 0x4000,
                   'Original QRAM bank read was truncated')
        end
    end)
    -- Restoration is mandatory, including when one of the reads fails.
    ports:write_u8(0xF4, saved)
    if not ok then error('Original QRAM capture failed: ' .. tostring(err)) end
    assert(program:read_range(0xA000, 0xA03F, 8) == original_window,
           'Original master bank view was not restored')
    local joined = table.concat(banks)
    assert(#joined == 0x10000, 'Original QRAM image must be 64KiB')
    return joined
end
emu.register_frame_done(function()
    if halted then return end
    frames = frames + 1
    if frames == 1 then initialize() end
    if AUTO_COIN and frames == 200 then coin:set_value(1) end
    if AUTO_COIN and frames == 215 then coin:set_value(0) end
    if frames % INTERVAL ~= 0 or captures >= MAX_CAPTURES then return end
    local image = snapshot_original_qram()
    if image == previous then return end
    previous = image
    captures = captures + 1
    local course = program:read_u8(0xE699)
    local round = program:read_u8(0xE69B)
    local filename = string.format(
       '%s/indyheat_qram_%03d_f%07d_c%02d_r%02d.bin',
       OUT, captures, frames, course, round)
    local out = assert(io.open(filename, 'wb'))
    out:write(image)
    out:close()
    print(string.format(
      'INDY_CARZ: captured original 64KiB QRAM image %d at frame %d, course %d, round %d',
      captures, frames, course, round))
end)
