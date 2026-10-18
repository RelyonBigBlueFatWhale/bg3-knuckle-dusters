--[[ 指虎：仅保留「手动」工具，自动发放已彻底移除。

     移除原因（2026-10-18）：早先为了免控制台发放，这里订阅了 SessionLoaded 事件
     并挂了一个 15 秒兜底定时器，于是**每次进游戏都会往背包里塞三件指虎**，越攒越多。
     那套逻辑已整段删除 —— 现在这个文件只在玩家自己敲控制台命令时才会发包。

     可用命令：
       !kd   —— 手动发放三件（各一件），用于新存档或测试
     日志：Ext.IO.SaveFile 只接受相对 SE 目录的文件名，所以是 knuckle_grant.log；
     更权威的记录在 SE 自己的 Extender Runtime 日志里的 [KD] 行。
]]

local LOG_PATH = "knuckle_grant.log"

local ITEMS = {
    { name = "KD_SteelSpikeFist", uuid = "d6476755-6fb1-4752-91e4-a51ada4747da", label = "钢刺之拳 (Rare)" },
    { name = "KD_BoneChill",      uuid = "94187658-a74c-4e44-a709-b3526ef1fbfd", label = "彻骨之寒 (VeryRare)" },
    { name = "KD_Unsharpened",    uuid = "7e69ee66-6202-42b3-8e17-b587fd9a0276", label = "无锋 (Legendary)" },
}

local LOG = {}

local function log(msg)
    local ts = "?"
    pcall(function() ts = os.date("%H:%M:%S") end)
    LOG[#LOG + 1] = ts .. "  " .. tostring(msg)
    _P("[KD] " .. tostring(msg))
    pcall(function() Ext.IO.SaveFile(LOG_PATH, table.concat(LOG, "\n")) end)
end

-- 同一件物品按三种模板引用形式依次试，成功即停
local function tryGive(host, it)
    local forms = { it.name .. "_" .. it.uuid, it.uuid, it.name }
    for _, f in ipairs(forms) do
        local ok = pcall(function() Osi.TemplateAddTo(f, host, 1) end)
        if ok then
            log("已发放 " .. it.label .. "  <- " .. f)
            return true
        end
    end
    log("发放失败：" .. it.label .. "（三种引用形式都报错）")
    return false
end

local function resolveHost()
    local h = nil
    pcall(function() h = Osi.DB_Players:Get(nil)[1][1] end)
    if not h then
        pcall(function() h = Osi.GetHostCharacter() end)
    end
    return h
end

-- 唯一的入口：控制台命令 !kd
local okCmd = pcall(function()
    Ext.RegisterConsoleCommand("kd", function()
        local host = resolveHost()
        if not host then
            log("找不到主机角色，发放取消")
            return
        end
        log("手动发放（!kd）：host = " .. tostring(host))
        for _, it in ipairs(ITEMS) do
            tryGive(host, it)
        end
    end)
end)

if not okCmd then
    log("注册 !kd 命令失败（不影响游戏，只是没有手动发放入口）")
end
