# -*- coding: utf-8 -*-
"""Generate localization files for every language Baldur's Gate 3 supports.

BG3 ships 13 languages. The mod previously shipped English + Chinese only; this script
writes the remaining 11 from the table below, then the loca compiler turns each XML into
a .loca that the game loads from Localization/<Language>/.

Vocabulary follows the game's own terminology where it exists (unarmed attack, piercing /
cold / bludgeoning damage, Bleeding, Wet, Vulnerable); the two invented status names
("Shellbreaker" / "Sundered") are translated to fit each language's style.

Run:  python gen_localization.py [--write] [--compile]
"""
import argparse
import io
import os
import subprocess
import sys

HANDLES = {
    "name_steel":       "h6504b930gf358g4889g938cg7eaa90df79af",
    "desc_steel":       "hf40daf82gd785g4612g9fe2gbe012e9846f5",
    "name_frost":       "h4286f685g0c99g44a8g8821ga2a247361b8d",
    "desc_frost":       "hef75a393g9ecbg4243g8a8fg1bb932c8da71",
    "name_gold":        "h8fc8470egf624g4266ga9dcg8368d8df1df9",
    "desc_gold":        "h08c974e9g87b2g480eg815cgfa295c1ae55d",
    "passive_steel":    "h0011a0abg57c7g43e8g8f71gb0a8ec398445",
    "passive_steel_d":  "h2637f832g0cd9g49b4gb8afgce8d87a2e42c",
    "rider_pierce":     "h26d44774g24d6g43f4gb606g2a91b9618fe9",
    "rider_pierce_d":   "h9572dfa4g3098g4547g8fa8g9d6c22c4418e",
    "rider_cold":       "hd526e1deg48a6g4e5ag8f5eg09447aa6f787",
    "rider_cold_d":     "h18c6f016g93e0g41c4gaab7g6f710dd22728",
    "rider_break":      "h66008c7cg95c8g425bg9cc4gd6d504715d6f",
    "rider_break_d":    "h9e163f1dg7e7fg4acfga1dbgb6480bb117f6",
    "atk_name":         "h27456ed8g689fg455bgb82fg5728a2337fa4",
    "atk_desc":         "h548a5901g11b5g440fga3ecgce7dfb42063c",
    "status_break":     "ha1bb7f91g7120g4892g95c9gf0685d51e6c4",
    "status_break_d":   "hca0d6f4bg51cfg49ebga6c6g0fbb01bdf456",
}

ORDER = ["name_steel", "desc_steel", "name_frost", "desc_frost", "name_gold", "desc_gold",
         "passive_steel", "passive_steel_d", "rider_pierce", "rider_pierce_d",
         "rider_cold", "rider_cold_d", "rider_break", "rider_break_d",
         "atk_name", "atk_desc", "status_break", "status_break_d"]

T = {}

T["English"] = {
    "name_steel": "Steel-Spike Fists",
    "desc_steel": "A pair of spiked steel knuckles. Your main-hand attacks with it still count as unarmed attacks; the spikes tear flesh on impact.",
    "name_frost": "Bone-Chill",
    "desc_frost": "Knuckles wrought from cold. Against a soaked target, the chill sinks straight into the bone.",
    "name_gold": "The Unsharpened",
    "desc_gold": "No edge at all, only sheer weight. They say it once turned a full suit of plate - and the man inside - into iron filings.",
    "passive_steel": "Steel Fist",
    "passive_steel_d": "Your main-hand attacks with this weapon count as unarmed attacks.",
    "rider_pierce": "Steel Claw",
    "rider_pierce_d": "Unarmed attacks deal an extra 1d4 Piercing damage and have a 20% chance to inflict Bleeding for 2 turns.",
    "rider_cold": "Piercing Cold",
    "rider_cold_d": "Unarmed attacks deal an extra 1d6 Cold damage, or 2d6 against Wet targets.",
    "rider_break": "Shellbreaker",
    "rider_break_d": "Unarmed attacks deal an extra 2d10 Bludgeoning damage and apply Sundered for 3 turns.",
    "atk_name": "Knuckle Strike",
    "atk_desc": "A melee attack made with knuckle dusters - resolved as an unarmed attack.",
    "status_break": "Sundered",
    "status_break_d": "Vulnerable to Bludgeoning damage. Two stacks are enough to make even a resistant target fragile.",
}

T["Chinese"] = {
    "name_steel": "钢刺之拳",
    "desc_steel": "一套套在指节上的钢刺护手。以指虎出拳时，攻击仍按徒手结算；指节上的尖刺会在命中时撕开皮肉。",
    "name_frost": "彻骨之寒",
    "desc_frost": "寒气凝成的指虎，握上去像攥着一把碎冰。对已经被水浸透的目标，寒意会顺着水渗进骨头里。",
    "name_gold": "无锋",
    "desc_gold": "没有锋刃，只有纯粹的分量。传说它曾把一整套板甲连同里面的人一起打成了铁屑。",
    "passive_steel": "钢拳",
    "passive_steel_d": "使用此武器时，主手攻击被视为徒手攻击。",
    "rider_pierce": "钢爪",
    "rider_pierce_d": "徒手攻击额外造成 1d4 穿刺伤害，并有 20% 概率使目标流血 2 回合。",
    "rider_cold": "刺骨",
    "rider_cold_d": "徒手攻击额外造成 1d6 寒冷伤害；若目标【濡湿】，再额外造成 1d6 寒冷伤害。",
    "rider_break": "剥壳",
    "rider_break_d": "徒手攻击额外造成 2d10 钝击伤害，并使目标【碎甲】3 回合。",
    "atk_name": "指虎攻击",
    "atk_desc": "以指虎发动的近战攻击——判定与加成均按徒手攻击结算。",
    "status_break": "碎甲",
    "status_break_d": "获得钝击易伤。两层碎甲足以让原本抗钝击的目标也变得脆弱。",
}

T["French"] = {
    "name_steel": "Poings d'acier à pointes",
    "desc_steel": "Une paire de poings américains en acier, hérissés de pointes. Vos attaques de main principale comptent toujours comme des attaques à mains nues ; les pointes déchirent les chairs à l'impact.",
    "name_frost": "Frisson d'os",
    "desc_frost": "Des poings américains forgés dans le froid. Contre une cible trempée, le gel s'infiltre jusqu'à l'os.",
    "name_gold": "Le non-affûté",
    "desc_gold": "Aucun tranchant, seulement de la masse pure. On raconte qu'il a déjà réduit une armure de plates entière - et l'homme à l'intérieur - en limaille de fer.",
    "passive_steel": "Poing d'acier",
    "passive_steel_d": "Vos attaques de main principale avec cette arme comptent comme des attaques à mains nues.",
    "rider_pierce": "Griffe d'acier",
    "rider_pierce_d": "Les attaques à mains nues infligent 1d4 dégâts perforants supplémentaires et ont 20 % de chances d'infliger Saignement pendant 2 tours.",
    "rider_cold": "Froid pénétrant",
    "rider_cold_d": "Les attaques à mains nues infligent 1d6 dégâts de froid supplémentaires, ou 2d6 contre une cible mouillée.",
    "rider_break": "Briseur de carapace",
    "rider_break_d": "Les attaques à mains nues infligent 2d10 dégâts contondants supplémentaires et appliquent Fendu pendant 3 tours.",
    "atk_name": "Frappe du poing",
    "atk_desc": "Une attaque au corps à corps portée avec des poings américains - résolue comme une attaque à mains nues.",
    "status_break": "Fendu",
    "status_break_d": "Vulnérable aux dégâts contondants. Deux cumuls suffisent à rendre fragile même une cible résistante.",
}

T["German"] = {
    "name_steel": "Stachelstahlfäuste",
    "desc_steel": "Ein Paar stachelige Stahlschlagringe. Deine Angriffe mit der Haupthand zählen weiterhin als waffenlose Angriffe; die Stacheln reißen beim Treffer Fleisch auf.",
    "name_frost": "Knochenfrost",
    "desc_frost": "Schlagringe aus Kälte geschmiedet. Gegen ein durchnässtes Ziel kriecht die Kälte bis in die Knochen.",
    "name_gold": "Der Ungeschliffene",
    "desc_gold": "Keine Schneide, nur reine Masse. Man sagt, er habe einst einen ganzen Plattnerpanzer - und den Mann darin - zu Eisenspänen zermalmt.",
    "passive_steel": "Stahlfaust",
    "passive_steel_d": "Deine Angriffe mit der Haupthand mit dieser Waffe zählen als waffenlose Angriffe.",
    "rider_pierce": "Stahlklaue",
    "rider_pierce_d": "Waffenlose Angriffe verursachen 1W4 zusätzlichen Stichschaden und haben eine 20-%-Chance, 2 Runden lang Blutung zu verursachen.",
    "rider_cold": "Beißende Kälte",
    "rider_cold_d": "Waffenlose Angriffe verursachen 1W6 zusätzlichen Kälteschaden, bzw. 2W6 gegen nasse Ziele.",
    "rider_break": "Panzerbrecher",
    "rider_break_d": "Waffenlose Angriffe verursachen 2W10 zusätzlichen Wuchtschaden und verursachen 3 Runden lang Zersplittert.",
    "atk_name": "Knöchelschlag",
    "atk_desc": "Ein Nahkampfangriff mit Schlagringen - wird als waffenloser Angriff abgehandelt.",
    "status_break": "Zersplittert",
    "status_break_d": "Anfällig für Wuchtschaden. Zwei Stapel genügen, um selbst ein resistentes Ziel zerbrechlich zu machen.",
}

T["Spanish"] = {
    "name_steel": "Puños de acero con pinchos",
    "desc_steel": "Un par de nudilleras de acero con pinchos. Tus ataques con la mano principal siguen contando como ataques sin armas; los pinchos desgarran la carne al impactar.",
    "name_frost": "Escalofrío óseo",
    "desc_frost": "Nudilleras forjadas en frío. Contra un objetivo empapado, el frío se hunde hasta el hueso.",
    "name_gold": "El sin filo",
    "desc_gold": "Sin filo alguno, solo peso puro. Dicen que una vez convirtió una armadura de placas entera -y al hombre dentro de ella- en limaduras de hierro.",
    "passive_steel": "Puño de acero",
    "passive_steel_d": "Tus ataques con la mano principal con esta arma cuentan como ataques sin armas.",
    "rider_pierce": "Garra de acero",
    "rider_pierce_d": "Los ataques sin armas infligen 1d4 de daño perforante adicional y tienen un 20 % de probabilidad de causar Sangrado durante 2 turnos.",
    "rider_cold": "Frío penetrante",
    "rider_cold_d": "Los ataques sin armas infligen 1d6 de daño de frío adicional, o 2d6 contra objetivos mojados.",
    "rider_break": "Rompeconchas",
    "rider_break_d": "Los ataques sin armas infligen 2d10 de daño contundente adicional y aplican Resquebrajado durante 3 turnos.",
    "atk_name": "Golpe de nudillo",
    "atk_desc": "Un ataque cuerpo a cuerpo realizado con nudilleras: se resuelve como un ataque sin armas.",
    "status_break": "Resquebrajado",
    "status_break_d": "Vulnerable al daño contundente. Dos acumulaciones bastan para volver frágil incluso a un objetivo resistente.",
}

T["Italian"] = {
    "name_steel": "Pugni d'acciaio spinati",
    "desc_steel": "Un paio di tirapugni d'acciaio con spine. I tuoi attacchi con la mano principale contano comunque come attacchi senz'armi; le spine lacerano la carne all'impatto.",
    "name_frost": "Brivido d'ossa",
    "desc_frost": "Tirapugni forgiati nel freddo. Contro un bersaglio fradicio, il gelo penetra fino all'osso.",
    "name_gold": "Il non affilato",
    "desc_gold": "Nessun filo, solo massa pura. Si dice che abbia ridotto un'intera armatura a piastre - e l'uomo che la indossava - in limatura di ferro.",
    "passive_steel": "Pugno d'acciaio",
    "passive_steel_d": "I tuoi attacchi con la mano principale con quest'arma contano come attacchi senz'armi.",
    "rider_pierce": "Artiglio d'acciaio",
    "rider_pierce_d": "Gli attacchi senz'armi infliggono 1d4 danni perforanti extra e hanno il 20% di probabilità di infliggere Sanguinamento per 2 turni.",
    "rider_cold": "Freddo penetrante",
    "rider_cold_d": "Gli attacchi senz'armi infliggono 1d6 danni da freddo extra, oppure 2d6 contro bersagli bagnati.",
    "rider_break": "Spezzagusci",
    "rider_break_d": "Gli attacchi senz'armi infliggono 2d10 danni contundenti extra e applicano Incrinato per 3 turni.",
    "atk_name": "Colpo di nocche",
    "atk_desc": "Un attacco in mischia sferrato con i tirapugni: viene risolto come un attacco senz'armi.",
    "status_break": "Incrinato",
    "status_break_d": "Vulnerabile ai danni contundenti. Due accumuli bastano a rendere fragile anche un bersaglio resistente.",
}

T["Polish"] = {
    "name_steel": "Stalowe kolczaste pięści",
    "desc_steel": "Para stalowych kastetów z kolcami. Twoje ataki bronią główną nadal liczą się jako ataki bez broni; kolce rozrywają ciało przy trafieniu.",
    "name_frost": "Kościsty ziąb",
    "desc_frost": "Kastety wykute z zimna. Przeciw przemokniętemu celowi chłód wnika prosto do kości.",
    "name_gold": "Nienaostrzony",
    "desc_gold": "Żadnego ostrza, tylko czysty ciężar. Mówią, że raz obrócił całą zbroję płytową - wraz z człowiekiem w środku - w opiłki żelaza.",
    "passive_steel": "Stalowa pięść",
    "passive_steel_d": "Twoje ataki bronią główną tą bronią liczą się jako ataki bez broni.",
    "rider_pierce": "Stalowy szpon",
    "rider_pierce_d": "Ataki bez broni zadają dodatkowe 1k4 obrażeń kłutych i mają 20% szans na wywołanie Krwawienia na 2 tury.",
    "rider_cold": "Przenikliwy chłód",
    "rider_cold_d": "Ataki bez broni zadają dodatkowe 1k6 obrażeń od zimna, albo 2k6 przeciw mokrym celom.",
    "rider_break": "Kruszyciel skorup",
    "rider_break_d": "Ataki bez broni zadają dodatkowe 2k10 obrażeń obuchowych i nakładają Pęknięcie na 3 tury.",
    "atk_name": "Uderzenie kastetem",
    "atk_desc": "Atak wręcz wykonany kastetem - rozliczany jako atak bez broni.",
    "status_break": "Pęknięty",
    "status_break_d": "Podatność na obrażenia obuchowe. Dwie warstwy wystarczą, by osłabić nawet odporny cel.",
}

T["Russian"] = {
    "name_steel": "Стальные шипастые кулаки",
    "desc_steel": "Пара стальных кастетов с шипами. Ваши атаки основной рукой по-прежнему считаются атаками без оружия; шипы разрывают плоть при попадании.",
    "name_frost": "Костяной холод",
    "desc_frost": "Кастеты, выкованные из стужи. Против промокшей цели холод проникает прямо в кости.",
    "name_gold": "Незаточенный",
    "desc_gold": "Ни грани, ни лезвия — только чистая масса. Говорят, он однажды превратил целый пластинчатый доспех — и человека внутри — в железную стружку.",
    "passive_steel": "Стальной кулак",
    "passive_steel_d": "Ваши атаки основной рукой этим оружием считаются атаками без оружия.",
    "rider_pierce": "Стальной коготь",
    "rider_pierce_d": "Атаки без оружия наносят дополнительно 1d4 колющего урона и с вероятностью 20% вызывают кровотечение на 2 хода.",
    "rider_cold": "Пронизывающий холод",
    "rider_cold_d": "Атаки без оружия наносят дополнительно 1d6 урона холодом или 2d6 по мокрым целям.",
    "rider_break": "Крушитель панцирей",
    "rider_break_d": "Атаки без оружия наносят дополнительно 2d10 дробящего урона и накладывают эффект «Расколот» на 3 хода.",
    "atk_name": "Удар кастетом",
    "atk_desc": "Ближняя атака кастетом — рассчитывается как атака без оружия.",
    "status_break": "Расколот",
    "status_break_d": "Уязвимость к дробящему урону. Двух стаков достаточно, чтобы сделать хрупкой даже устойчивую цель.",
}

T["Turkish"] = {
    "name_steel": "Çelik Dikenli Yumruklar",
    "desc_steel": "Bir çift dikenli çelik muşta. Ana elinle yaptığın saldırılar hâlâ silahsız saldırı sayılır; dikenler çarptığında eti yırtar.",
    "name_frost": "Kemik Üşümesi",
    "desc_frost": "Soğuktan dövülmüş muştalar. Islanmış bir hedefe karşı soğuk doğrudan kemiğe işler.",
    "name_gold": "Bilenmemiş",
    "desc_gold": "Keskin kenar yok, sadece saf ağırlık. Bir zamanlar tam bir plaka zırhı - ve içindeki adamı - demir talaşına çevirdiği söylenir.",
    "passive_steel": "Çelik Yumruk",
    "passive_steel_d": "Bu silahla ana elinle yaptığın saldırılar silahsız saldırı sayılır.",
    "rider_pierce": "Çelik Pençe",
    "rider_pierce_d": "Silahsız saldırılar fazladan 1d4 delici hasar verir ve %20 ihtimalle 2 tur süreyle Kanama uygular.",
    "rider_cold": "İşleyen Soğuk",
    "rider_cold_d": "Silahsız saldırılar fazladan 1d6 soğuk hasarı verir; ıslak hedeflere karşı 2d6.",
    "rider_break": "Kabuk Kıran",
    "rider_break_d": "Silahsız saldırılar fazladan 2d10 ezici hasar verir ve 3 tur süreyle Çatlamış uygular.",
    "atk_name": "Muşta Vuruşu",
    "atk_desc": "Muştayla yapılan bir yakın dövüş saldırısı - silahsız saldırı olarak hesaplanır.",
    "status_break": "Çatlamış",
    "status_break_d": "Ezici hasara karşı savunmasız. İki katman, dirençli bir hedefi bile kırılgan yapmaya yeter.",
}

T["Ukrainian"] = {
    "name_steel": "Сталеві шипасті кулаки",
    "desc_steel": "Пара сталевих кастетів із шипами. Ваші атаки основною рукою досі вважаються атаками без зброї; шипи рвуть плоть при влучанні.",
    "name_frost": "Кістяний холод",
    "desc_frost": "Кастети, викувані з холоду. Проти просяклої цілі холод проникає просто в кістки.",
    "name_gold": "Незаточений",
    "desc_gold": "Жодного леза — лише чиста маса. Кажуть, він колись обернув цілу пластинчасту броню — і людину всередині — на залізну стружку.",
    "passive_steel": "Сталевий кулак",
    "passive_steel_d": "Ваші атаки основною рукою цією зброєю вважаються атаками без зброї.",
    "rider_pierce": "Сталевий кіготь",
    "rider_pierce_d": "Атаки без зброї завдають додатково 1d4 колючої шкоди і з імовірністю 20% викликають кровотечу на 2 ходи.",
    "rider_cold": "Пронизливий холод",
    "rider_cold_d": "Атаки без зброї завдають додатково 1d6 шкоди холодом або 2d6 по мокрих цілях.",
    "rider_break": "Крушій панцирів",
    "rider_break_d": "Атаки без зброї завдають додатково 2d10 дробильної шкоди і накладають «Розколотий» на 3 ходи.",
    "atk_name": "Удар кастетом",
    "atk_desc": "Ближня атака кастетом — розраховується як атака без зброї.",
    "status_break": "Розколотий",
    "status_break_d": "Уразливість до дробильної шкоди. Двох накопичень достатньо, щоб зробити крихкою навіть стійку ціль.",
}

T["BrazilianPortuguese"] = {
    "name_steel": "Punhos de Aço Espinhosos",
    "desc_steel": "Um par de socos-ingleses de aço com espinhos. Seus ataques com a mão principal ainda contam como ataques desarmados; os espinhos rasgam a carne no impacto.",
    "name_frost": "Frio nos Ossos",
    "desc_frost": "Socos-ingleses forjados no frio. Contra um alvo encharcado, o frio penetra direto nos ossos.",
    "name_gold": "O Não Afiado",
    "desc_gold": "Sem fio algum, apenas peso bruto. Dizem que certa vez transformou uma armadura de placas inteira - e o homem dentro dela - em limalha de ferro.",
    "passive_steel": "Punho de Aço",
    "passive_steel_d": "Seus ataques com a mão principal com esta arma contam como ataques desarmados.",
    "rider_pierce": "Garra de Aço",
    "rider_pierce_d": "Ataques desarmados causam 1d4 de dano perfurante adicional e têm 20% de chance de causar Sangramento por 2 turnos.",
    "rider_cold": "Frio Penetrante",
    "rider_cold_d": "Ataques desarmados causam 1d6 de dano de frio adicional, ou 2d6 contra alvos molhados.",
    "rider_break": "Quebra-Cascos",
    "rider_break_d": "Ataques desarmados causam 2d10 de dano de concussão adicional e aplicam Rachado por 3 turnos.",
    "atk_name": "Golpe de Nós",
    "atk_desc": "Um ataque corpo a corpo feito com socos-ingleses - resolvido como um ataque desarmado.",
    "status_break": "Rachado",
    "status_break_d": "Vulnerável a dano de concussão. Dois acúmulos bastam para tornar frágil até um alvo resistente.",
}

T["Japanese"] = {
    "name_steel": "鋼棘の拳",
    "desc_steel": "棘のついた鋼のナックルダスター。メインハンドでの攻撃は依然として素手攻撃として扱われる。棘は命中時に肉を裂く。",
    "name_frost": "骨の凍気",
    "desc_frost": "冷気から鍛えられたナックルダスター。濡れた目標に対しては、冷気が骨まで染み込む。",
    "name_gold": "刃なきもの",
    "desc_gold": "刃は一切なく、ただ質量のみ。かつてプレートアーマーごと、中の人間ごと鉄屑に変えたという。",
    "passive_steel": "鋼の拳",
    "passive_steel_d": "この武器によるメインハンドの攻撃は素手攻撃として扱われる。",
    "rider_pierce": "鋼の爪",
    "rider_pierce_d": "素手攻撃は追加で1d4の刺突ダメージを与え、20%の確率で2ターンの出血を付与する。",
    "rider_cold": "突き刺す冷気",
    "rider_cold_d": "素手攻撃は追加で1d6の冷気ダメージを与える。濡れた目標には2d6。",
    "rider_break": "殻砕き",
    "rider_break_d": "素手攻撃は追加で2d10の殴打ダメージを与え、3ターンの破砕を付与する。",
    "atk_name": "ナックルストライク",
    "atk_desc": "ナックルダスターによる近接攻撃。素手攻撃として処理される。",
    "status_break": "破砕",
    "status_break_d": "殴打ダメージに脆弱。2スタックで、抵抗を持つ目標さえもろくなる。",
}

T["Korean"] = {
    "name_steel": "강철 가시 주먹",
    "desc_steel": "가시가 달린 강철 너클 더스터 한 쌍. 주 손으로 하는 공격은 여전히 맨손 공격으로 판정된다. 가시는 명중 시 살점을 찢는다.",
    "name_frost": "뼈의 한기",
    "desc_frost": "냉기로 벼려낸 너클 더스터. 흠뻑 젖은 대상에게는 한기가 뼛속까지 스며든다.",
    "name_gold": "날을 세우지 않은 자",
    "desc_gold": "날은 없고 오직 무게뿐. 한때 판금 갑옷과 그 안의 사람을 통째로 쇳가루로 만들었다고 한다.",
    "passive_steel": "강철 주먹",
    "passive_steel_d": "이 무기로 하는 주 손 공격은 맨손 공격으로 판정된다.",
    "rider_pierce": "강철 발톱",
    "rider_pierce_d": "맨손 공격이 1d4의 추가 관통 피해를 입히고, 20% 확률로 2턴 동안 출혈을 부여한다.",
    "rider_cold": "꿰뚫는 냉기",
    "rider_cold_d": "맨손 공격이 1d6의 추가 냉기 피해를 입히며, 젖은 대상에게는 2d6을 입힌다.",
    "rider_break": "껍질 파괴자",
    "rider_break_d": "맨손 공격이 2d10의 추가 타격 피해를 입히고 3턴 동안 균열을 부여한다.",
    "atk_name": "너클 스트라이크",
    "atk_desc": "너클 더스터로 하는 근접 공격. 맨손 공격으로 판정된다.",
    "status_break": "균열",
    "status_break_d": "타격 피해에 취약. 2중첩이면 저항을 가진 대상도 약해진다.",
}

LANGUAGES = ["English", "Chinese", "French", "German", "Spanish", "Italian", "Polish",
             "Russian", "Turkish", "Ukrainian", "BrazilianPortuguese", "Japanese", "Korean"]

XML_DIRS = [
    r"D:\DSH\dist\src\KnuckleDusters\source\meta\Localization",
    r"D:\DSH\github\bg3-knuckle-dusters\mod\meta\Localization",
]
LOCA_ROOTS = [
    r"D:\DSH\knuckle_mod\Localization",
    r"D:\DSH\knuckle_mod\Public\KnuckleDusters\Localization",
]
LOCA_PY = r"D:\DSH\bg3-ascendant\tools\loca.py"


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def write_xml(lang, out_dir):
    d = os.path.join(out_dir, lang)
    os.makedirs(d, exist_ok=True)
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<contentList>"]
    for key in ORDER:
        text = T[lang][key]
        lines.append('\t<content contentuid="%s" version="1">%s</content>'
                     % (HANDLES[key], esc(text)))
    lines.append("</contentList>")
    path = os.path.join(d, "KnuckleDusters.xml")
    io.open(path, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--compile", action="store_true")
    a = ap.parse_args()

    missing = [l for l in LANGUAGES if l not in T]
    if missing:
        raise SystemExit("missing translations: %s" % missing)
    for l in LANGUAGES:
        m = [k for k in ORDER if k not in T[l]]
        if m:
            raise SystemExit("%s missing keys: %s" % (l, m))

    written = []
    for root in XML_DIRS:
        if not os.path.isdir(os.path.dirname(root)):
            print("  skip (no parent):", root)
            continue
        for lang in LANGUAGES:
            p = write_xml(lang, root)
            written.append(p)
    print("  wrote %d xml files" % len(written))

    if not a.compile:
        return 0

    py = sys.executable
    for root in LOCA_ROOTS:
        if not os.path.isdir(os.path.dirname(root)):
            continue
        for lang in LANGUAGES:
            src = os.path.join(XML_DIRS[0], lang, "KnuckleDusters.xml")
            dst_dir = os.path.join(root, lang)
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, "KnuckleDusters.loca")
            r = subprocess.run([py, LOCA_PY, "build", src, dst],
                               capture_output=True, text=True)
            size = os.path.getsize(dst) if os.path.isfile(dst) else 0
            print("  %-22s -> %-40s %6d B %s"
                  % (lang, dst.replace("D:\\DSH\\knuckle_mod", "…"), size,
                     "" if r.returncode == 0 else "FAILED: " + r.stderr[:120]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
