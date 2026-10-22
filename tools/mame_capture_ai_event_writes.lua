-- Original 1991 arcade master Z80 AI pending-event CPU-write tracing.
-- PRIVATE local output; original ROM, QRAM, car bytes and game images
-- must never be committed to public GitHub.
--
-- mkdir -p local/private-runtime
-- INDY_AI_OUT=local/private-runtime INDY_COIN=1 INDY_FRAMES=10000 \
-- mame indyheat -rompath /PRIVATE/original-rom -video none -sound none \
--  -nothrottle -seconds_to_run 168 \
--  -autoboot_script tools/mame_capture_ai_event_writes.lua
--
-- Exact original bank0 SET1/SET2 instructions at 2336/235C write
-- IX-09, i.e. physical slot+77 in the user's original five car slots.
local OUT=os.getenv('INDY_AI_OUT') or 'local/private-runtime'
local MAX_FRAMES=tonumber(os.getenv('INDY_FRAMES') or '10000')
local AUTO_COIN=os.getenv('INDY_COIN')=='1'
assert(MAX_FRAMES>=1000 and MAX_FRAMES<=300000)
local f,n=0,0
local cpu,mem,handle,coin,taps
emu.register_frame_done(function()
    f=f+1
    if f==1 then
        cpu=assert(manager.machine.devices[':master'])
        mem=assert(cpu.spaces['program'])
        coin=assert(manager.machine.ioport.ports[':IN0'].fields['Coin 1'])
        handle=assert(io.open(OUT..'/ai_event_writes.csv','w'))
        handle:write('frame,pc,ix,addr,old,new,cmp,pedal_response,b1,b2,fe,linked20,x,y,dc,bound_x,bound_y,course,round\n')
        taps={}
        for i=0,4 do
            local address=0xE077+0x100*i
            taps[#taps+1]=mem:install_write_tap(address,address,
                'indy_original_ai_event_'..i,function(addr,data,mask)
                    if f<2300 or f>MAX_FRAMES then return end
                    local pc=(cpu.state['CURPC'] or cpu.state['PC']).value&0xffff
                    if pc~=0x2336 and pc~=0x235C then return end
                    local ix=cpu.state['IX'].value&0xffff
                    if ix~=0xE080+0x100*i then return end
                    local pointer=mem:read_u8(ix+0x7C)|
                                  (mem:read_u8(ix+0x7D)<<8)
                    local linked20=255
                    if pointer>=0xE000 and pointer<=0xFFDF then
                        linked20=mem:read_u8(pointer+0x20)
                    end
                    local boundx=mem:read_u8(0xE642)|(mem:read_u8(0xE643)<<8)
                    local boundy=mem:read_u8(0xE95B)|(mem:read_u8(0xE95C)<<8)
                    handle:write(string.format(
                        '%d,%04X,%04X,%04X,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n',
                        f,pc,ix,addr,mem:read_u8(addr),data&255,
                        mem:read_u8(ix-0x45),mem:read_u8(ix+0x57),
                        mem:read_u8(ix+0x31),mem:read_u8(ix+0x32),
                        mem:read_u8(ix+0x7E),linked20,
                        mem:read_u8(ix-0x75),mem:read_u8(ix-0x7F),
                        mem:read_u8(ix+0x5C),boundx,boundy,
                        mem:read_u8(0xE699),mem:read_u8(0xE69B)))
                    n=n+1
                end)
        end
        print('INDY_AI: original Z80 five-car event write taps installed')
    end
    if AUTO_COIN and f==200 then coin:set_value(1) end
    if AUTO_COIN and f==215 then coin:set_value(0) end
    if f%500==0 and handle then handle:flush() end
    if f>=MAX_FRAMES and handle then
        handle:flush();handle:close();handle=nil
        if AUTO_COIN then coin:set_value(0) end
        print(string.format('INDY_AI: captured %d original 2336/235C writes',n))
    end
end)
