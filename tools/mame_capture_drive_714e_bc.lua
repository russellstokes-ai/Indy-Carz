-- Original 1991 Indy Heat master Z80 PC 714E/71C8 register parity.
-- Requires user-owned ROM and debugger-capable MAME (0.264).
-- Output contains PRIVATE live arcade RAM/register values; DO NOT commit CSV.
--
-- mkdir -p local/private-runtime
-- INDY_DRIVE714E_OUT=local/private-runtime/drive_714e_live.csv \
-- mame indyheat -rompath /PRIVATE/rompath -video none -sound none \
--   -debug -debugger none -nothrottle -seconds_to_run 65 \
--   -autoboot_script tools/mame_capture_drive_714e_bc.lua
--
-- Original 7124 finishes with E933 and CARRY; 714E consumes that carry
-- to select original B/C. Its normal exit is 71C8. A rare direct 7315
-- bypass is NOT audited by the paired-exit verifier; use separate
-- branch-specific instrumentation to validate it in a live race.
local OUT=os.getenv('INDY_DRIVE714E_OUT') or
          'local/private-runtime/drive_714e_live.csv'
local AUTO_COIN=os.getenv('INDY_DRIVE714E_COIN')~='0'
local STOP=tonumber(os.getenv('INDY_DRIVE714E_FRAMES') or '3600')
assert(STOP>=2500 and STOP<=50000)
local frame=0
local master,debugger,coin,fh,last
local closed=false
local function setup()
 local machine=manager.machine
 master=assert(machine.devices[':master'],'Original master Z80 missing')
 debugger=assert(machine.debugger,'Requires -debug -debugger none')
 coin=assert(machine.ioport.ports[':IN0'].fields['Coin 1'])
 fh=assert(io.open(OUT,'w'))
 fh:write('frame,marker,values\n')
 assert(master.debug:bpset(0x714E,nil,
    'printf "SE714E,IX=%04X,AF=%04X,E76D=%04X,E76F=%04X,E76B=%04X,E768=%02X,E769=%04X,E933=%04X,IDX0=%02X,IDX1=%02X,TABLE=%04X,E76C=%02X\\n",ix,af,w@e76d,w@e76f,w@e76b,b@e768,w@e769,w@e933,b@(ix+6e),b@(ix+6f),w@e96b,b@e76c;g'))
 assert(master.debug:bpset(0x71C8,nil,
    'printf "SE71C8,IX=%04X,BC=%04X,AF=%04X\\n",ix,bc,af;g'))
 master.debug:go()
 last=#debugger.consolelog
 print('INDY_714E: original control selection read-only CPU taps armed')
end
emu.register_frame_done(function()
 if closed then return end
 frame=frame+1
 if frame==1 then setup() end
 if AUTO_COIN and frame==200 then coin:set_value(1) end
 if AUTO_COIN and frame==215 then coin:set_value(0) end
 local log=debugger.consolelog
 local n=#log
 if n<last then last=0 end
 for i=last+1,n do
    local line=log[i]
    if line and (line:find('SE714E,') or line:find('SE71C8,')) then
       fh:write(frame..',LINE,'..line..'\n')
    end
 end
 last=n
 if frame%500==0 then fh:flush() end
 if frame>=STOP then
    if AUTO_COIN then coin:set_value(0) end
    fh:flush();fh:close();fh=nil
    closed=true
    print('INDY_714E: private original register snapshot finished')
 end
end)
