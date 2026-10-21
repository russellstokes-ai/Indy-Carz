-- Authentic original 1991 arcade master Z80 pedal byte-write instrumentation.
-- Requires user's PRIVATE indyheat.zip and MAME 0.264, never original ROM in git.
--
-- mkdir -p local/private-runtime
-- INDY_PEDAL_OUT=local/private-runtime INDY_COIN=1 INDY_PEDAL_SWEEP=1 \
-- mame indyheat -rompath /PRIVATE/rompath -video none -sound none \
--  -nothrottle -seconds_to_run 96 \
--  -autoboot_script tools/mame_capture_pedal_parity.lua
--
-- The opt-in sweep exercises all 256 P1 pedal input values (8 MAME frames
-- each, frames 2500..4547). Capture strictly original CPU write at PC 67D2,
-- car IX=E080, physical slot E0D7; original IX+57 is NOT slot+57.
local OUT=os.getenv('INDY_PEDAL_OUT') or 'local/private-runtime'
local AUTO_COIN=os.getenv('INDY_COIN')=='1'
local SWEEP=os.getenv('INDY_PEDAL_SWEEP')=='1'
local STOP=tonumber(os.getenv('INDY_PEDAL_FRAMES') or '5700')
assert(STOP>=4550 and STOP<=30000)
local frame=0
local cpu,space,pedal,coin,handle,tap
local records=0
emu.register_frame_done(function()
    frame=frame+1
    if frame==1 then
        cpu=assert(manager.machine.devices[':master'],'Original master missing')
        space=assert(cpu.spaces['program'],'Original program memory missing')
        local io=manager.machine.ioport
        pedal=assert(io.ports[':AN3'].fields['P1 Pedal 1'],'Original P1 analogue missing')
        coin=assert(io.ports[':IN0'].fields['Coin 1'],'Original coin field missing')
        handle=assert(io.open(OUT..'/live_pedal_writes.csv','w'))
        handle:write('frame,pc,ix,addr,data,pedal,factor,bias,car_b1,car_b2\n')
        tap=space:install_write_tap(0xE0D7,0xE0D7,'indy_original_pedal',
            function(address,data,mask)
                if frame<2300 or frame>STOP then return end
                local pc=(cpu.state['CURPC'] or cpu.state['PC']).value&0xFFFF
                local ix=cpu.state['IX'].value&0xFFFF
                if pc~=0x67D2 or ix~=0xE080 then return end
                handle:write(string.format('%d,%04X,%04X,%04X,%d,%d,%d,%d,%d,%d\n',
                    frame,pc,ix,address,data&255,
                    io.ports[':AN3']:read(),space:read_u8(ix+0x58),
                    space:read_u8(ix+0x59),space:read_u8(ix+0x31),
                    space:read_u8(ix+0x32)))
                records=records+1
            end)
    end
    if AUTO_COIN and frame==200 then coin:set_value(1) end
    if AUTO_COIN and frame==215 then coin:set_value(0) end
    if SWEEP then
        local value=0
        if frame>=2500 and frame<4548 then value=(frame-2500)//8 end
        pedal:set_value(value)
    end
    if frame%300==0 and handle then handle:flush() end
    if frame==STOP and handle then
        handle:flush();handle:close();handle=nil
        if SWEEP then pedal:set_value(0) end
        if AUTO_COIN then coin:set_value(0) end
        print(string.format('INDY_PEDAL: captured %d original instruction writes',records))
    end
end)
