-- Authentic private original MAME B884 response return, B8AC and B8E3.
-- Requires -debug -debugger none and authentic user-owned indyheat ROM.
-- mkdir -p local/private-runtime
-- INDY_CONTACT_OUT=local/private-runtime INDY_CONTACT_COIN=1
-- Program data, raw captured original state and screenshot assets stay PRIVATE.
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
  fh=assert(io.open(OUT..'/original_collision_b884_returns.csv','w'))
  fh:write('frame,pc,ix,iy,e941,car_b1,car_7c,e608,a\n')
  for _,site in ipairs({0xB884,0xB8AB,0xB8AC,0xB8E3,0x1689}) do
   local action=string.format(
    'printf "RESP,%04X,%%04X,%%04X,%%02X,%%02X,%%02X,%%02X,%%02X\\n",ix,iy,b@e941,b@(ix+31),b@(ix-4),b@e608,a; g',site)
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
  local values=line and line:match('RESP,(.*)')
  if values then fh:write(frame..','..values..'\n');hits=hits+1 end
 end
 last=count
 if frame%500==0 then fh:flush() end
 if frame>=LIMIT then
  fh:flush();fh:close();fh=nil;finished=true;coin:set_value(0)
  print('INDY_B884: original collision callback breakpoint events '..hits)
 end
end)
