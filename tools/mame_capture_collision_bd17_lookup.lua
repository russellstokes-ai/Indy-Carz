-- ORIGINAL 1991 Indy Heat arcade collision-memory lookup trace (PRIVATE).
-- No original ROM, asset bytes, private graphics or raw traces in GitHub.
--
-- mkdir -p local/private-runtime
-- INDY_BD17_OUT=local/private-runtime/bd17_lookup_private.csv \
-- INDY_BD17_COIN=1 INDY_BD17_FRAMES=6500 \
-- mame indyheat -rompath /PRIVATE/ROM -debug -debugger none \
--  -video none -sound none -nothrottle -seconds_to_run 110 \
--  -autoboot_script tools/mame_capture_collision_bd17_lookup.lua
--
-- Exact original Z80 PCs: BD17 performs LD A,(HL), BD1A compares to 84,
-- BD1D continues for >=84, BE6B is the <84 external branch target.
-- At BD17 HL is the calculated 16-bit pointer; original input E731/E73B
-- and original E978 are logged so clean-room maths can verify every hit.
local OUT=os.getenv('INDY_BD17_OUT') or 'local/private-runtime/bd17_lookup_private.csv'
local FRAMES=tonumber(os.getenv('INDY_BD17_FRAMES') or '6500')
local AUTO=os.getenv('INDY_BD17_COIN')=='1'
assert(FRAMES>=1000 and FRAMES<=250000)
local frame,last,hits=0,0,0
local cpu,debugger,coin,file
local finished=false
local sites={0xBD17,0xBD1A,0xBD1D,0xBE6B}
local function initialize()
    local machine=manager.machine
    cpu=assert(machine.devices[':master'],'Original master Z80 required')
    debugger=assert(machine.debugger,'MAME -debug -debugger none required')
    coin=assert(machine.ioport.ports[':IN0'].fields['Coin 1'])
    file=assert(io.open(OUT,'w'))
    file:write('frame,pc,ix,iy,hl,a,e978,e731,e73b,e608,e976,e92e,mem_hl\n')
    for _,pc in ipairs(sites) do
        local cmd=string.format(
          'printf "BCFA_PTR,%04X,%%04X,%%04X,%%04X,%%02X,%%02X,%%04X,%%04X,%%02X,%%02X,%%02X,%%02X\\n",ix,iy,hl,a,b@e978,w@e731,w@e73b,b@e608,b@e976,b@e92e,b@(hl); g',pc)
        assert(cpu.debug:bpset(pc,nil,cmd))
    end
    cpu.debug:go()
    last=#debugger.consolelog
    print('INDY_BD17: debugger breakpoints for original collision pointer/branch active')
end
emu.register_frame_done(function()
    if finished then return end
    frame=frame+1
    if frame==1 then initialize() end
    if AUTO and frame==200 then coin:set_value(1) end
    if AUTO and frame==215 then coin:set_value(0) end
    local log=debugger.consolelog
    local current=#log
    if current<last then last=0 end
    for i=last+1,current do
        local msg=log[i]
        local values=msg and msg:match('BCFA_PTR,(.*)')
        if values then file:write(frame..','..values..'\n');hits=hits+1 end
    end
    last=current
    if frame%500==0 then file:flush() end
    if frame>=FRAMES then
        file:flush();file:close();file=nil;finished=true
        if AUTO then coin:set_value(0) end
        print(string.format('INDY_BD17: %d original lookup PC hits',hits))
    end
end)
