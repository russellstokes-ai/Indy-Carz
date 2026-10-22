-- Private original MAME Z80 B8BA LDIR copy source/destination tap.
-- Authentic rev-1 Indy Heat ROM required; no debugger flag is needed.
-- mkdir -p local/private-runtime
-- INDY_CONTACT_OUT=local/private-runtime INDY_CONTACT_COIN=1
-- -autoboot_script tools/mame_capture_collision_b8ac_ldir.lua
-- Original MAME private RAM contents must NEVER be committed publicly.
local OUT=os.getenv('INDY_CONTACT_OUT') or 'local/private-runtime'
local LIMIT=tonumber(os.getenv('INDY_CONTACT_FRAMES') or '7000')
local COIN=os.getenv('INDY_CONTACT_COIN')=='1'
assert(LIMIT>=1000 and LIMIT<=50000)
local frame,writes=0,0
local cpu,ram,coin,fh,tap
local finished=false
emu.register_frame_done(function()
 if finished then return end
 frame=frame+1
 if frame==1 then
  cpu=assert(manager.machine.devices[':master'])
  ram=assert(cpu.spaces['program'])
  coin=assert(manager.machine.ioport.ports[':IN0'].fields['Coin 1'])
  fh=assert(io.open(OUT..'/original_collision_b8ac_ldir.csv','w'))
  fh:write('frame,pc,ix,hl,dest,data,src_before,source_val\n')
  tap=ram:install_write_tap(0xE000,0xE4FF,'indycarz_original_collision_ldir',
    function(address,data,mask)
     local pc=(cpu.state['CURPC'] or cpu.state['PC']).value&0xFFFF
     if pc~=0xB8BA then return end
     local ix=cpu.state['IX'].value&0xFFFF
     local hl_reg=cpu.state['HL']
     local hl=hl_reg and (hl_reg.value&0xFFFF) or 0
     local valid=hl_reg and hl>=0xE000 and hl<0xFFFE
     local source=valid and ram:read_u8(hl) or 0
     fh:write(string.format('%d,%04X,%04X,%04X,%04X,%d,%d,%d\n',
          frame,pc,ix,hl,address,data&255,source,valid and 1 or 0))
     writes=writes+1
    end)
 end
 if COIN and frame==200 then coin:set_value(1) end
 if COIN and frame==215 then coin:set_value(0) end
 if frame%500==0 then fh:flush() end
 if frame>=LIMIT then
  fh:flush();fh:close();fh=nil;finished=true;coin:set_value(0)
  print('INDY_LDIR: original 66-byte transfer instruction writes '..writes)
 end
end)
