# 指虎 · Knuckle Dusters

三件嵌宝指虎，攻击按**武僧式徒手打击**结算，同时保留武器自身的伤害与附伤通道，
因此既适合武僧（含散打宗），也适合任何徒手流派。

---

## 三件物品

| 品质 | 名称 | 解锁章节（戴摩） | 主要特性 |
|---|---|---|---|
| 稀有 | **钢刺之拳** | 第一章 · 翠绿林地 | 钢爪：徒手额外 1d4 穿刺，20% 概率流血 2 回合 |
| 珍奇 | **彻骨之寒** | 第二章 · 终焉之光 | 刺骨：徒手额外 1d6 寒冷；目标濡湿时再 +1d6 |
| 传说 | **无锋** | 第三章 · 下城区锻炉 | 剥壳：命中使目标获得【碎甲】（钝击易伤） |

第一件在第一章上架，第二、三件按章节递进解锁；第一章的商品在后续章节会继续售卖。
商人库存按**长休 / 升级**刷新，若没看到就先长休一次。

---

## 特性

- **按徒手结算、但吃武器附伤**：攻击是真正的武器攻击（所以神圣武器、元素武器这类
  挂在武器上的附伤都会生效），同时伤害链里保留 `UnarmedDamage`，因此
  **酒馆殴斗者**与武僧具现等徒手加成照样吃。
- **武僧武器**：隐藏被动授予 `MonkWeaponAttackOverride()` 与
  `MonkWeaponDamageDiceOverride(LevelMapValue(MartialArts))`，所以疾风连击、
  武艺：附赠徒手打击都把指虎当作武僧武器。
- **散打宗三支变体全覆盖**：`Target_OpenHandTechnique_Push / Knock / NoReactions`
  都被覆盖，两击各自带上武器伤害与武器 functor，同时**动画与散打宗特效原样保留**
  （推击的力量豁免、摔绊的倒地、无反应的封锁）。
- **灵巧 + 单手 + 禁副手**：`Melee;Dippable;Magical;Finesse;Light;NoDualWield`。
- **符文自发光**：材质改用 `CHAR_BASE_GM` 并接入 Glowmap，钢刺为蓝色符文光，
  寒霜为冰蓝，无锋不发光。

## 安装

1. 把 `KnuckleDusters.pak` 放到
   `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\`（或用 BG3 Mod Manager 导入）。
2. 在模组管理器里启用 **Knuckle Dusters**。
3. **加载顺序**：如果你装了其它同样修改武僧法术
   （`Target_FlurryOfBlows`、`Target_UnarmedStrike_Monk`）或徒手攻击的 mod，
   请把本 mod 排在它们**之后**（后加载者生效）。

## 兼容性说明

- 本 mod 覆盖了 `Target_FlurryOfBlows`、`Target_UnarmedStrike_Monk`、
  三支 `Target_OpenHandTechnique_*`、`Target_UnarmedAttack`、
  `Target_StunningStrike_Unarmed`、`Target_ShadowStrike_Instant_Unarmed`、
  `Target_KiResonation_Punch`。与其冲突的 mod 需要调整加载顺序。
- `Target_UnarmedAttack` 是全局覆盖：**任何角色在手持武器时用徒手攻击**都会附加该武器
  的伤害；空手时该段为 0（`max(0, MainMeleeWeapon)`），行为与原版一致。
- 以「是否徒手」为条件的 stat 效果不会触发，因为本武器的攻击按武器攻击结算。

## 控制台（可选）

安装 BG3 Script Extender 后，控制台输入 `!kd` 可各发一件用于测试。

## 制作说明

模型基于多视角重建（Qwen 生成正交参考图 → Blender 重建 → 重拓扑 8.7k–10k 三角面 →
UV/烘焙 → 程序化贴图 + 法线浮雕 + 自发光），骨架为原版匕首七骨链的刚性绑定。
源码、全部素材与调研文档都在压缩包的 `source/` 目录内。

作者：16084　适配版本：BG3 Patch 8（4.1.1.7209685）
