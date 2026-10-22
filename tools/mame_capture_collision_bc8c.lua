-- Original Indy Heat 1991 collision retry / fallback debugger trace.
-- PRIVATE: supply a user-owned rev-1 indyheat.zip; never commit original
-- ROM, RAM traces, QRAM or game screenshots to GitHub.
--
-- mkdir -p local/private-runtime
-- INDY_BC8C_OUT=local/private-runtime/bc8c_live_private.csv \
-- INDY_BC8C_COIN=1 INDY_BC8C_FRAMES=9000 \
-- mame indyheat -rompath /PRIVATE/romdir -debug -debugger none \
--   -video none -sound none -nothrottle -seconds_to_run 151 \
--   -autoboot_script tools/mame_capture_collision_bc8c.lua
--
-- Original CPU PCs: BC8C entry, BC9E zero counter, BCA5 retry, BCFA
-- normal processing, BCB2/C468/BCF7 fallback/11-word geometry restore.
-- The trace deliberately does not record copyrighted ROM opcode bytes.
local OUT=os.getenv('INDY_BC8C_OUT') or 'local/private-runtime/bc8c_live_private.csv'
local STOP=tonumber(os.getenv('INDY_BC8C_FRAMES') or '9000')
local AUTO=os.getenv('INDY_BC8C_COIN')=='1'
assert(STOP>=1000 and STOP<=250000)
local frame,last,hits=0,0,0
local device,dbg,coin,file
local completed=false
local sites={0xBC8C,0xBCA5,0xBCB2,0xC468,0xBCFA,0xBCF7,0xBC9E}

local function init()
    local machine=manager.machine
    device=assert(machine.devices[':master'],'Original master Z80 missing')
    dbg=assert(machine.debugger,'Use -debug -debugger none')
    coin=assert(machine.ioport.ports[':IN0'].fields['Coin 1'])
    file=assert(io.open(OUT,'w'))
    file:write('frame,pc,ix,iy,e608,e976,e92e,e92c,car_b1,e768,e76a,e76b,e765\n')
    for _,pc in ipairs(sites) do
        local action=string.format(
            'printf "BC8C_TRACE,%04X,%%04X,%%04X,%%02X,%%02X,%%02X,%%02X,%%02X,%%02X,%%02X,%%04X,%%04X\\n",ix,iy,b@e608,b@e976,b@e92e,b@e92c,b@(ix+31),b@e768,b@e76a,w@e76b,w@e765; g',pc)
        assert(device.debug:bpset(pc,nil,action))
    end
    device.debug:go()
    last=#dbg.consolelog
    print('INDY_BC8C: recording real arcade retry/rollback Z80 breakpoints')
end

emu.register_frame_done(function()
    if completed then return end
    frame=frame+1
    if frame==1 then init() end
    if AUTO and frame==200 then coin:set_value(1) end
    if AUTO and frame==215 then coin:set_value(0) end
    local logs=dbg.consolelog
    local now=#logs
    if now<last then last=0 end
    for i=last+1,now do
        local line=logs[i]
        local values=line and line:match('BC8C_TRACE,(.*)')
        if values then file:write(frame..','..values..'\n');hits=hits+1 end
    end
    last=now
    if frame%300==0 then file:flush() end
    if frame>=STOP then
        file:flush();file:close();file=nil
        if AUTO then coin:set_value(0) end
        completed=true
        print(string.format('INDY_BC8C: %d original collision retry breakpoint hits',hits))
    end
end)
