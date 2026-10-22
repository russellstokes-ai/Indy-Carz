-- Read-only original 1991 Indy Heat arcade master Z80 motion-word tracer.
-- This instrument was tested against authentic owner-supplied rev1 ROM
-- in MAME 0.264; it does not alter CPU state or the running arcade game.
-- Output is PRIVATE state data; do not commit captures to GitHub.
--
-- mkdir -p local/private-runtime
-- INDY_VELOCITY_COIN=1 INDY_VELOCITY_FRAMES=9000 \
-- INDY_VELOCITY_OUT=local/private-runtime/velocity_live.csv \
-- mame indyheat -rompath /PRIVATE/original-rompath -video none -sound none \
-- -nothrottle -seconds_to_run 151 \
-- -autoboot_script tools/mame_capture_velocity_7225.lua
--
-- Original master PC 7241 LD (E76B),HL writes the bounded 7225-7244
-- signed-motion result. The write tap captures original E76B before
-- the write, the upstream DE word, and resulting HL from CPU registers.
-- Do not mistake this subroutine for the full grip/acceleration model.
local OUT=os.getenv('INDY_VELOCITY_OUT') or
          'local/private-runtime/velocity7225_live.csv'
local STOP=tonumber(os.getenv('INDY_VELOCITY_FRAMES') or '9000')
local AUTO=os.getenv('INDY_VELOCITY_COIN')=='1'
assert(STOP>=2500 and STOP<=50000)
local frame,count,bad=0,0,0
local cpu,ram,coin,fh,tap
local closed=false
emu.register_frame_done(function()
    if closed then return end
    frame=frame+1
    if frame==1 then
        cpu=assert(manager.machine.devices[':master'])
        ram=assert(cpu.spaces['program'])
        coin=assert(manager.machine.ioport.ports[':IN0'].fields['Coin 1'])
        fh=assert(io.open(OUT,'w'))
        fh:write('frame,pc,ix,old_motion,de_input,hl_result,expected,correct,branch\n')
        tap=ram:install_write_tap(0xE76B,0xE76B,
            'indy_original_7225_motion',function(addr,data,mask)
                if frame<2300 or frame>STOP then return end
                local pc=(cpu.state['CURPC'] or cpu.state['PC']).value&0xFFFF
                if pc~=0x7241 then return end
                local ix=cpu.state['IX'].value&0xFFFF
                local old=ram:read_u8(0xE76B)|(ram:read_u8(0xE76C)<<8)
                local original_de=cpu.state['DE'].value&0xFFFF
                local actual=cpu.state['HL'].value&0xFFFF
                local difference=(old-original_de)&0xFFFF
                local same=((old&0x8000)~=0)==((difference&0x8000)~=0)
                local prediction=same and difference or 0
                local correct=(prediction==actual and (actual&255)==(data&255))
                local branch=(old&0x8000)~=0 and 'negative' or 'positive'
                branch=branch..(same and '_keep' or '_clamp')
                count=count+1
                if not correct then bad=bad+1 end
                fh:write(string.format(
                    '%d,%04X,%04X,%04X,%04X,%04X,%04X,%d,%s\n',
                    frame,pc,ix,old,original_de,actual,prediction,
                    correct and 1 or 0,branch))
            end)
        print('INDY_7225: authentic original motion CPU write tap ready')
    end
    if AUTO and frame==200 then coin:set_value(1) end
    if AUTO and frame==215 then coin:set_value(0) end
    if frame%600==0 and fh then fh:flush() end
    if frame>=STOP then
        if AUTO then coin:set_value(0) end
        fh:flush();fh:close();fh=nil
        closed=true
        print(string.format(
            'INDY_7225: captured %d original motion writes, mismatches=%d',
            count,bad))
    end
end)
