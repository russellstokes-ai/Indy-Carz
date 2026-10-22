-- Capture ACTUAL original arcade master-Z80 contact control flow in MAME 0.264.
-- This Lua instrument has been exercised against a private authentic rev-1 ROM.
-- No original ROM, code, art, sound, lookup bytes or private CSV are committed.
--
-- mkdir -p local/private-runtime
-- INDY_BRANCH_OUT=local/private-runtime INDY_BRANCH_COIN=1 \
--   mame indyheat -rompath /PRIVATE/rompath -debug -debugger none \
--   -video none -sound none -nothrottle -seconds_to_run 115 \
--   -autoboot_script tools/mame_capture_collision_branches.lua
--
-- The original B6ED branch can execute B728, then FALL THROUGH into B778,
-- then FALL THROUGH into B86C. Capturing only one branch hides this behaviour.
-- The original category bitfield E919 is 0..31; values 24..31 really index
-- beyond the original 24-record table into adjacent original ROM code bytes.
local OUT=os.getenv('INDY_BRANCH_OUT') or 'local/private-runtime'
local COIN=os.getenv('INDY_BRANCH_COIN')=='1'
local FRAME_LIMIT=tonumber(os.getenv('INDY_BRANCH_FRAMES') or '7000')
assert(FRAME_LIMIT>=1000 and FRAME_LIMIT<=50000)
local frame=0
local last_log=0
local debugger, master, coin, file
local sites={0xB6ED,0xB728,0xB778,0xB86C}
local closed=false
local hits=0

local function finish()
    if closed then return end
    closed=true
    if file then file:flush();file:close();file=nil end
    if coin then coin:set_value(0) end
    print(string.format('INDY_BRANCH: recorded %d original debugger hits',hits))
end

local function init()
    master=assert(manager.machine.devices[':master'],'Original master Z80 missing')
    debugger=assert(manager.machine.debugger,'Use -debug -debugger none')
    coin=assert(manager.machine.ioport.ports[':IN0'].fields['Coin 1'])
    file=assert(io.open(OUT..'/original_collision_branches.csv','w'))
    file:write('frame,stage,ix,iy,d,e,e919,angle3d,a,e925\n')
    for _,pc in ipairs(sites) do
        local stage=(pc==0xB6ED) and 'START' or string.format('%04X',pc)
        local action=string.format(
            'printf "TRACE_STAGE,%s,%%04X,%%04X,%%02X,%%02X,%%02X,%%02X,%%02X,%%02X\\n",ix,iy,d,e,b@e919,b@(iy-43),a,b@e925; g',stage)
        local n=master.debug:bpset(pc,nil,action)
        assert(n,'Failed to install original CPU breakpoint')
    end
    master.debug:go()
    last_log=#debugger.consolelog
    print('INDY_BRANCH: original contact breakpoints and live debugger logger installed')
end

emu.register_frame_done(function()
    if closed then return end
    frame=frame+1
    if frame==1 then init() end
    if COIN and frame==200 then coin:set_value(1) end
    if COIN and frame==215 then coin:set_value(0) end
    local logs=debugger.consolelog
    local current=#logs
    if current<last_log then last_log=0 end
    for i=last_log+1,current do
        local msg=logs[i]
        local values=msg and msg:match('TRACE_STAGE,(.*)')
        if values then
            file:write(frame..','..values..'\n')
            hits=hits+1
        end
    end
    last_log=current
    if frame%500==0 then file:flush() end
    if frame>=FRAME_LIMIT then finish() end
end)
