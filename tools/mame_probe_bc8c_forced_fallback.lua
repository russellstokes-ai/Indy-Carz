-- Controlled ORIGINAL MAME CPU experiment; NOT a normal-game capture.
-- User-owned 1991 arcade indyheat.zip and MAME 0.264 required.
-- Bounded original Z80 BC8C/C468 fallback, never published ROM/game data.
--
-- Explicit opt-in is REQUIRED because this changes original emulated RAM.
-- mkdir -p local/private-runtime
-- INDY_FORCE_BC8C=1 INDY_BC8C_OUT=local/private-runtime/forced_bc8c.csv \
-- mame indyheat -rompath /PRIVATE/rompath -video none -sound none \
--   -nothrottle -debug -debugger none -seconds_to_run 58 \
--   -autoboot_script tools/mame_probe_bc8c_forced_fallback.lua
--
-- At frame 2400, install a one-time original PC BCA5 breakpoint:
-- "do b@e92e=11; bpclear; g" (debugger numbers are hexadecimal!).
-- Setting original RAM E92E=0x11 before INC A causes count 0x12 (18).
-- The debugger breakpoint deletes itself before game continuation.
-- No mutation occurs unless INDY_FORCE_BC8C=1 is explicitly supplied.
-- This does NOT demonstrate a naturally occurring retry exhaustion.
assert(os.getenv('INDY_FORCE_BC8C') == '1',
       'Controlled original arcade RAM injection requires explicit opt-in')
local OUT=os.getenv('INDY_BC8C_OUT') or
          'local/private-runtime/forced_bc8c_fallback.csv'
local frame,events,errors=0,0,0
local master,ram,coin,fh,debugger
local taps={}
local forced,closed=false,false
local counters={}
local restore={
 [0xBCB8]={0xE749,0xE72B},[0xBCBE]={0xE753,0xE735},
 [0xBCC4]={0xE74B,0xE72D},[0xBCCA]={0xE74D,0xE72F},
 [0xBCD0]={0xE74F,0xE731},[0xBCD6]={0xE751,0xE733},
 [0xBCDC]={0xE755,0xE737},[0xBCE2]={0xE757,0xE739},
 [0xBCE8]={0xE759,0xE73B},[0xBCEE]={0xE75B,0xE73D},
 [0xBCF4]={0xE747,0xE767}}
local shared_reset={
 [0xC46F]={[0xE76A]='angle'},
 [0xC475]={[0xE76B]=0,[0xE76C]=0xCC},
 [0xC47B]={[0xE765]=0,[0xE766]=0}}
local function pc()
 local value=master.state['CURPC'] or master.state['PC']
 return value.value & 0xFFFF
end
local function emit(kind,original_pc,address,correct)
 events=events+1
 if not correct then errors=errors+1 end
 counters[kind]=(counters[kind] or 0)+1
 fh:write(string.format('%d,%s,%04X,%04X,%04X,%d,%d\n',
     frame,kind,original_pc,master.state['IX'].value&0xFFFF,
     address,correct and 1 or 0,ram:read_u8(0xE92E)))
end
local function init()
 local machine=manager.machine
 master=assert(machine.devices[':master'],'Original master Z80 missing')
 ram=assert(master.spaces['program'],'Original master program space missing')
 coin=assert(machine.ioport.ports[':IN0'].fields['Coin 1'],
             'Original arcade coin control missing')
 debugger=assert(machine.debugger,'Requires MAME -debug -debugger none')
 fh=assert(io.open(OUT,'w'))
 fh:write('frame,kind,pc,ix,addr,correct,counter\n')
 taps[1]=ram:install_write_tap(0xE72B,0xE76D,'original_bc8c_rollback',
   function(addr,data,mask)
    if frame < 2399 or frame > 2450 then return end
    local at=pc()
    local pair=restore[at]
    local kind,correct
    if pair and addr>=pair[2] and addr<pair[2]+2 then
       kind='restore'
       correct=ram:read_u8(pair[1]+addr-pair[2])==(data&255)
    elseif shared_reset[at] and shared_reset[at][addr]~=nil then
       kind='global_reset'
       local expected=shared_reset[at][addr]
       if expected=='angle' then expected=ram:read_u8(0xE768) end
       correct=(data&255)==expected
    else
       return
    end
    emit(kind,at,addr,correct)
   end)
 taps[2]=ram:install_write_tap(0xE0C1,0xE0CD,'original_bc8c_car_reset',
   function(addr,data,mask)
    if frame < 2399 or frame > 2450 then return end
    local at=pc()
    if at<0xC468 or at>0xC486 then return end
    if addr~=0xE0C1 and addr~=0xE0CC and addr~=0xE0CD then return end
    emit('car_reset',at,addr,(data&255)==0)
   end)
 print('INDY_BC8C_CONTROL: private original-machine probe armed')
end
emu.register_frame_done(function()
 if closed then return end
 frame=frame+1
 if frame==1 then init() end
 if frame==200 then coin:set_value(1) end
 if frame==215 then coin:set_value(0) end
 if frame==2400 then
    local action='do b@e92e=11; printf "BC8C_SINGLE_INJECTION,IX=%04X,E92E=%02X\\n",ix,b@e92e; bpclear; g'
    local id=assert(master.debug:bpset(0xBCA5,nil,action))
    print('INDY_BC8C_CONTROL: one-shot BCA5 breakpoint id='..id)
 end
 if frame>=2410 and not forced then
    local logs=debugger.consolelog
    for i=1,#logs do
       local line=logs[i]
       if line and line:find('BC8C_SINGLE_INJECTION') then
          forced=true
          print('INDY_BC8C_CONTROL: '..line)
          break
       end
    end
 end
 if frame==3400 then
    coin:set_value(0)
    fh:flush();fh:close();fh=nil
    closed=true
    print(string.format(
      'INDY_BC8C_CONTROL: forced=%s writes=%d correct=%d errors=%d restored_bytes=%d reset_bytes=%d car_bytes=%d',
      tostring(forced),events,events-errors,errors,counters.restore or 0,
      counters.global_reset or 0,counters.car_reset or 0))
 end
end)
