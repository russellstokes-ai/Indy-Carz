-- Read-only MAME 0.264 original Indy Heat master Z80 movement+geometry tap.
-- For user-owned rev-1 original ROM only. CSV is PRIVATE and must not be
-- committed: contains actual original game runtime RAM-derived geometry.
--
-- mkdir -p local/private-runtime
-- INDY_DRIVE_OUT=local/private-runtime INDY_COIN=1 INDY_FRAMES=10000 \
-- mame indyheat -rompath /PRIVATE/romdir -video none -sound none \
--  -nothrottle -seconds_to_run 168 \
--  -autoboot_script tools/mame_capture_drive_geometry.lua
--
-- Captures each ORIGINAL CPU write, not an approximated frame diff.
-- Original master PC 7555/756F: integrated 16-bit centre coordinates.
-- Original master PC 75B2..75EE: eight 16-bit oriented-rectangle words.
-- Some original game paths compute the rectangle WITHOUT integrating
-- position. The corresponding replay verifier explicitly handles both.
local OUT = os.getenv('INDY_DRIVE_OUT') or 'local/private-runtime'
local MAX_FRAMES = tonumber(os.getenv('INDY_FRAMES') or '10000')
local START_FRAME = tonumber(os.getenv('INDY_START') or '2300')
local AUTO_COIN = os.getenv('INDY_COIN') == '1'
local MAX_EVENTS = 700000
assert(MAX_FRAMES >= 1 and MAX_FRAMES <= 300000)
assert(START_FRAME >= 1 and START_FRAME < MAX_FRAMES)
local events, frame = 0, 0
local cpu, program, tap, handle, coin
local permitted = {
    [0x7555] = 0xE735, [0x756F] = 0xE72B,
    [0x75B2] = 0xE73D, [0x75BB] = 0xE737,
    [0x75C3] = 0xE73B, [0x75CC] = 0xE739,
    [0x75D4] = 0xE733, [0x75DD] = 0xE72D,
    [0x75E5] = 0xE731, [0x75EE] = 0xE72F,
}
local function initialize()
    cpu = assert(manager.machine.devices[':master'], 'Missing original master Z80')
    program = assert(cpu.spaces['program'], 'Missing original master CPU program space')
    coin = manager.machine.ioport.ports[':IN0'].fields['Coin 1']
    handle = assert(io.open(OUT..'/live_drive_geometry.csv','w'))
    handle:write('frame,pc,ix,addr,data,angle,motion,x,y,course,round\n')
    -- The write tap is invoked before the original CPU RAM write.
    tap = program:install_write_tap(0xE72B,0xE73E,
        'indycarz_original_vehicle_writes',function(addr,data,mask)
            if frame < START_FRAME or frame > MAX_FRAMES then return end
            local pc=(cpu.state['CURPC'] or cpu.state['PC']).value & 0xFFFF
            local first=permitted[pc]
            if not first or (addr ~= first and addr ~= first+1) then return end
            local ix=cpu.state['IX'].value & 0xFFFF
            if ix < 0xE080 or ix > 0xE580 or (ix & 0xFF) ~= 0x80 then return end
            events=events+1
            assert(events <= MAX_EVENTS, 'Original CPU write capture budget exceeded')
            local is_movement=(pc==0x7555 or pc==0x756F)
            local angle_address=is_movement and 0xE76A or 0xE768
            local x=program:read_u8(0xE735)|(program:read_u8(0xE736)<<8)
            local y=program:read_u8(0xE72B)|(program:read_u8(0xE72C)<<8)
            local angle=program:read_u8(angle_address)
            local motion=program:read_u8(0xE76C)
            handle:write(string.format(
                '%d,%04X,%04X,%04X,%d,%d,%d,%d,%d,%d,%d\n',
                frame,pc,ix,addr,data & 255,angle,motion,x,y,
                program:read_u8(0xE699),program:read_u8(0xE69B)))
        end)
    print('INDY_DRIVE: original master movement/footprint write taps ready')
end
emu.register_frame_done(function()
    frame=frame+1
    if frame==1 then initialize() end
    if AUTO_COIN and coin and frame==200 then coin:set_value(1) end
    if AUTO_COIN and coin and frame==215 then coin:set_value(0) end
    if frame%600==0 and handle then handle:flush() end
    if frame>=MAX_FRAMES and handle then
        handle:flush()
        handle:close()
        handle=nil
        if AUTO_COIN and coin then coin:set_value(0) end
        print(string.format('INDY_DRIVE: completed %d original CPU byte writes',events))
    end
end)
