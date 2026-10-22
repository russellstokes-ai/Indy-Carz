-- Indy Carz / original Indy Heat: private per-frame RAM capture.
--
-- Prerequisites: authentic 1991 arcade "indyheat" ROM in local MAME rompath.
-- Make the output folder yourself: mkdir -p local/engine-extraction/runtime
-- Run: mame indyheat -rompath /path/to/roms -autoboot_script tools/mame_capture_carstate.lua
--
-- IMPORTANT: this script has NOT yet been run against MAME in the development
-- container. It uses the documented MAME Lua address_space:read_range method.
-- Captures actual emulated game RAM, not original graphics ROMs.
-- Do not commit any generated .bin/.csv run data to the public repository.

local DIRECTORY = "local/engine-extraction/runtime/"
local FIRST_ADDR = 0xE000
local LAST_ADDR = 0xE9FF
local RECORD_SIZE = LAST_ADDR - FIRST_ADDR + 1  -- 2560 bytes
local MAX_FRAMES = 12000 -- 200 seconds at 60fps, bounded to avoid large logs

local frame = 0
local memory = nil
local bin = nil
local csv = nil
local closed = false

local function le32(n)
    return string.char(n & 255, (n >> 8) & 255, (n >> 16) & 255, (n >> 24) & 255)
end

local function close_capture()
    if closed then return end
    closed = true
    if bin then bin:close() end
    if csv then csv:close() end
    print(string.format("INDY_CARZ: RAM capture finished after %d frames", frame))
end

local function setup()
    local master = manager.machine.devices[":master"]
    if not master then
        print("INDY_CARZ: missing :master device; expected original arcade set")
        return false
    end
    memory = master.spaces["program"]
    if not memory then
        print("INDY_CARZ: :master program address space unavailable")
        return false
    end
    local error_info
    bin, error_info = io.open(DIRECTORY .. "master_ram_frames.bin", "wb")
    if not bin then
        print("INDY_CARZ: cannot open binary capture: " .. tostring(error_info))
        return false
    end
    csv, error_info = io.open(DIRECTORY .. "capture_index.csv", "w")
    if not csv then
        print("INDY_CARZ: cannot open frame index: " .. tostring(error_info))
        close_capture()
        return false
    end
    bin:write("ICR1")
    bin:write(le32(FIRST_ADDR))
    bin:write(le32(RECORD_SIZE))
    csv:write("frame,start_hex,size\n")
    csv:flush()
    print("INDY_CARZ: writing 2560 emulated RAM bytes per frame to private capture folder")
    return true
end

emu.register_frame_done(function()
    if closed then return end
    if frame >= MAX_FRAMES then
        close_capture()
        return
    end
    if memory == nil and not setup() then
        close_capture()
        return
    end
    local snapshot = memory:read_range(FIRST_ADDR, LAST_ADDR, 8)
    if type(snapshot) ~= "string" or #snapshot ~= RECORD_SIZE then
        print("INDY_CARZ: invalid RAM snapshot size; stopping safely")
        close_capture()
        return
    end
    frame = frame + 1
    bin:write(le32(frame))
    bin:write(snapshot)
    csv:write(string.format("%d,%04X,%d\n", frame, FIRST_ADDR, RECORD_SIZE))
    if frame % 120 == 0 then
        bin:flush()
        csv:flush()
        print("INDY_CARZ: RAM frames captured " .. frame)
    end
end)
