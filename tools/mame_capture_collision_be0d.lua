-- Authenticated original MAME Z80 live BE0D-BE67 collision translation trace.
-- Copyrighted program and track data remain LOCAL to the user's emulator.
-- Captures original CPU RAM values only to a PRIVATE CSV, never GitHub.
--
-- mkdir -p local/private-runtime
-- INDY_BE0D_COIN=1 INDY_BE0D_OUT=local/private-runtime/be0d_live.csv \
-- INDY_BE0D_FRAMES=33000 mame indyheat -rompath /PRIVATE/original-rompath \
-- -video none -sound none -nothrottle -debug -debugger none \
-- -seconds_to_run 560 -autoboot_script tools/mame_capture_collision_be0d.lua
--
-- BE0D is the original Z80 entry, BE65 the original JP BCA5 exit.
-- Both debugger actions are read-only printf/go and never edit game state.
-- A single ENTRY/EXIT pair can be checked against the exact 16-bit delta
-- model at tools/arcade_live_collision_be0d_translation.py.
local OUT=os.getenv('INDY_BE0D_OUT') or
          'local/private-runtime/be0d_translation_live.csv'
local AUTO_COIN=os.getenv('INDY_BE0D_COIN')=='1'
local MAX_FRAMES=tonumber(os.getenv('INDY_BE0D_FRAMES') or '8000')
assert(MAX_FRAMES>=2300 and MAX_FRAMES<=60000)
local frame,events=0,0
local master,coin,debugger,file
local lastlog=0
local started,closed=false,false
local names={
    'ix','target_x','target_y','base_x','base_y',
    'x1','x2','x3','x4','y1','y2','y3','y4'}
local values={
    'ix','w@e98d','w@e98f','w@e731','w@e73b',
    'w@e72d','w@e72f','w@e733','w@e72b',
    'w@e737','w@e739','w@e73d','w@e735'}
local function action(label)
    local format={}
    for i=1,#values do format[i]='%04X' end
    return 'printf "BE0D_TRACE,'..label..','..
        table.concat(format,',')..'\\n",'..
        table.concat(values,',')..'; g'
end
local function setup()
    local machine=manager.machine
    master=assert(machine.devices[':master'],'Original master Z80 unavailable')
    coin=assert(machine.ioport.ports[':IN0'].fields['Coin 1'])
    debugger=assert(machine.debugger,
                    'Original MAME debugger required; use -debug -debugger none')
    file=assert(io.open(OUT,'w'))
    file:write('frame,phase,'..table.concat(names,',')..'\n')
    print('INDY_BE0D: original Z80 collision translation trace ready')
end
emu.register_frame_done(function()
    if closed then return end
    frame=frame+1
    if frame==1 then setup() end
    if AUTO_COIN and frame==200 then coin:set_value(1) end
    if AUTO_COIN and frame==215 then coin:set_value(0) end
    if frame==2200 then
        assert(master.debug:bpset(0xBE0D,nil,action('ENTRY')))
        assert(master.debug:bpset(0xBE65,nil,action('EXIT')))
        master.debug:go()
        started=true
        lastlog=#debugger.consolelog
        print('INDY_BE0D: original BE0D/BE65 read-only breakpoints installed')
    end
    if started then
        local logs=debugger.consolelog
        local n=#logs
        if n<lastlog then lastlog=0 end
        for i=lastlog+1,n do
            local line=logs[i]
            local fields=line and line:match('BE0D_TRACE,(.*)')
            if fields then
                file:write(frame..','..fields..'\n')
                events=events+1
            end
        end
        lastlog=n
    end
    if frame%300==0 and file then file:flush() end
    if frame>=MAX_FRAMES then
        if AUTO_COIN then coin:set_value(0) end
        file:flush();file:close();file=nil
        closed=true
        print(string.format(
            'INDY_BE0D: captured %d original Z80 entry/exit records',events))
    end
end)
