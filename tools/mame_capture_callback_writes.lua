-- Trace original Indy Heat callback pointer changes during MAME execution.
--
-- REQUIRES local authentic 1991 arcade indyheat ROM; does not include it.
-- No ROM/graphics is ever written by this script.
-- Tested only against MAME's documented Lua API, NOT run in this session.
--
-- mkdir -p local/engine-extraction/runtime
-- mame indyheat -rompath /absolute/path/to/roms -autoboot_script tools/mame_capture_callback_writes.lua
--
-- MAME API: address_space:install_write_tap (inclusive range), emu.register_frame_done.
-- Keep tap subscriptions referenced for script lifetime.
-- Output CSV is PRIVATE runtime metadata; do not check into public GitHub.

local OUTPUT = "local/engine-extraction/runtime/original_callback_write_trace.csv"
local MAX_EVENTS = 50000
local frame = 0
local events = 0
local started = false
local inactive = false
local file = nil
local cpu = nil
local space = nil
local taps = {}

local function pc()
    local ok, value = pcall(function()
        local state = cpu.state["CURPC"] or cpu.state["PC"]
        return state and state.value
    end)
    if ok and type(value) == "number" then return value & 0xffff end
    return 0xffff  -- unknown PC, never fabricate a specific instruction
end

local function log_event(kind, address, data)
    if inactive or not file then return end
    if events >= MAX_EVENTS then
        print("INDY_CARZ: callback event limit reached (" .. MAX_EVENTS .. ")")
        file:flush()
        file:close()
        file = nil
        inactive = true
        return
    end
    events = events + 1
    file:write(string.format("%d,%s,%04X,%02X,%04X\n",
                 frame, kind, address & 0xffff, data & 0xff, pc()))
    if events % 100 == 0 then file:flush() end
end

local function snapshot()
    -- Includes currently installed callbacks, even if initial writes
    -- happened before the Lua tap registration during machine boot.
    for slot = 0, 5 do
        local base = 0xE000 + (slot * 0x100)
        for offset = 0x94, 0x97 do
            local addr = base + offset
            log_event("snapshot", addr, space:read_u8(addr))
        end
    end
    for _, address in ipairs({0xE699, 0xE69B, 0xE67D}) do
        log_event("snapshot_global", address, space:read_u8(address))
    end
end

local function install()
    cpu = manager.machine.devices[":master"]
    if not cpu then
        print("INDY_CARZ: Original master Z80 device not found")
        return false
    end
    space = cpu.spaces["program"]
    if not space then
        print("INDY_CARZ: Original master Z80 program address space missing")
        return false
    end
    local err
    file, err = io.open(OUTPUT, "w")
    if not file then
        print("INDY_CARZ: Output folder missing or unwritable: " .. tostring(err))
        return false
    end
    file:write("frame,kind,address,value,master_pc\n")

    for slot = 0, 5 do
        local first = 0xE094 + (slot * 0x100)
        taps[#taps+1] = space:install_write_tap(
            first, first+3, "indycarz_callback_slot_" .. slot,
            function(address, data, mask)
                -- Non-invasive pass-through: do not return modified data.
                log_event("callback_write", address, data)
            end)
    end
    for _, address in ipairs({0xE699, 0xE69B, 0xE67D}) do
        taps[#taps+1] = space:install_write_tap(
            address, address, "indycarz_global_" .. string.format("%04X", address),
            function(offset, data, mask)
                log_event("global_write", offset, data)
            end)
    end
    started = true
    snapshot()
    print("INDY_CARZ: Original callback and championship write taps registered")
    return true
end

emu.register_frame_done(function()
    if inactive then return end
    frame = frame + 1
    if not started and not install() then
        inactive = true
        return
    end
    if file and frame % 120 == 0 then file:flush() end
end)
