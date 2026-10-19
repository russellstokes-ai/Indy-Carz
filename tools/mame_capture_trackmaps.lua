-- Capture Indy Heat's original 0x10000-byte QRAM tilemap snapshots.
-- Local reference only. Requires a running, matching MAME indyheat machine.
-- Run from repo root, after mkdir -p local/track-recovery:
--   mame indyheat -rompath /path/to/romdir -autoboot_script tools/mame_capture_trackmaps.lua
--
-- This script has not yet been run against MAME in this development session.
-- It automatically saves changed snapshots every 300 frames (~5 sec at 60 fps).
-- It does NOT capture sprites, gameplay physics or full 14-track metadata.

local OUT = "local/track-recovery/"
local INTERVAL = 300
local MAX_CAPTURES = 120
local frames = 0
local captures = 0
local previous = nil
local share = nil
local warned = false

emu.register_frame_done(function()
    frames = frames + 1
    if (frames % INTERVAL ~= 0) or (captures >= MAX_CAPTURES) then
        return
    end

    if not share then
        share = manager.machine.memory.shares[":qram"]
        if not share then
            if not warned then
                print("INDY_CARZ: :qram memory share missing; check MAME set/revision")
                warned = true
            end
            return
        end
        if share.size ~= 0x10000 or share.bitwidth ~= 8 then
            print("INDY_CARZ: QRAM size or native width unexpected; refusing capture")
            captures = MAX_CAPTURES
            return
        end
    end

    local values = {}
    for i = 0, 0xffff do
        values[i + 1] = string.char(share:read_u8(i))
    end
    local snapshot = table.concat(values)
    if snapshot == previous then
        return
    end
    previous = snapshot
    captures = captures + 1

    local file = string.format("%sindyheat_qram_%03d_f%07d.bin",
                               OUT, captures, frames)
    local handle, err = io.open(file, "wb")
    if not handle then
        print("INDY_CARZ: Cannot write QRAM capture: " .. tostring(err))
        captures = MAX_CAPTURES
        return
    end
    handle:write(snapshot)
    handle:close()
    print("INDY_CARZ: Captured QRAM snapshot #" .. captures .. ": " .. file)
end)
