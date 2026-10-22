-- ORIGINAL 1991 Indy Heat rev-1 MAME 0.264 two-car collision dispatch.
-- Run privately with: -debug -debugger none -autoboot_script
-- tools/mame_capture_collision_service_dispatch.lua
-- mkdir -p local/private-runtime
-- INDY_CONTACT_OUT=local/private-runtime INDY_CONTACT_COIN=1
-- No original ROM or captured car bytes may be committed to GitHub.
local OUT=os.getenv('INDY_CONTACT_OUT') or 'local/private-runtime'
local LIMIT=tonumber(os.getenv('INDY_CONTACT_FRAMES') or '7000')
local COIN=os.getenv('INDY_CONTACT_COIN')=='1'
assert(LIMIT>=1000 and LIMIT<=50000)
local frame,last,hits=0,0,0
local debug,master,coin,fh
local finished=false
emu.register_frame_done(function()
 if finished then return end
 frame=frame+1
 if frame==1 then
  master=assert(manager.machine.devices[':master'])
  debug=assert(manager.machine.debugger,'Use -debug -debugger none')
  coin=assert(manager.machine.ioport.ports[':IN0'].fields['Coin 1'])
  fh=assert(io.open(OUT..'/original_collision_service_dispatch.csv','w'))
  fh:write('frame,stage,ix,iy,status_ix,status_iy,e941\n')
  for _,site in ipairs({0xB86C,0xB884}) do
   local name=site==0xB86C and 'DISPATCH' or 'SERVICE'
   local action=string.format(
    'printf "MAME_SVC,%s,%%04X,%%04X,%%02X,%%02X,%%02X\\n",ix,iy,b@(ix-4),b@(iy-4),b@e941; g',name)
   assert(master.debug:bpset(site,nil,action))
  end
  master.debug:go()
  last=#debug.consolelog
 end
 if COIN and frame==200 then coin:set_value(1) end
 if COIN and frame==215 then coin:set_value(0) end
 local logs=debug.consolelog;local count=#logs
 if count<last then last=0 end
 for i=last+1,count do
  local line=logs[i]
  local values=line and line:match('MAME_SVC,(.*)')
  if values then fh:write(frame..','..values..'\n');hits=hits+1 end
 end
 last=count
 if frame%500==0 then fh:flush() end
 if frame>=LIMIT then
  fh:flush();fh:close();fh=nil;finished=true;coin:set_value(0)
  print('INDY_SVC: original B86C/B884 breakpoint events '..hits)
 end
end)
