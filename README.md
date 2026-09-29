# Pokémon 数据收集仓库（pkm-data）

宝可梦图鉴分类数据集（简体中文），供 `pkm-hud` 等脚本按需在线加载，避免把全部数据塞进 HUD 脚本里。

> 本仓库数据均为**从公开网站抓取、清洗、结构化**整理而成，仅作个人学习与同人用途。

## 数据来源（抓取的网站）

| 网站 | 抓取内容 | 对应文件 |
|---|---|---|
| [神奇宝贝百科 wiki.52poke.com](https://wiki.52poke.com)（MediaWiki API） | 特性、招式、道具、精灵（含种族值/图鉴描述/形态）、进化链、徽章、属性相克表、各代可学招式等文字数据 | `abilities.json` `moves.json` `items.json` `evolution.json` `badges.json` `types.json` `pokemon/` `movesets/` |
| [神奇宝贝百科图床 media.52poke.com](https://media.52poke.com) | 道具图标（部分） | `item-sprites/` |
| [Serebii.net ItemDex](https://www.serebii.net/itemdex/) | 道具图标（宝可梦 GO 糖果、装饰品、老世代道具等独有图） | `item-sprites/` |
| [PokeOS](https://www.pokeos.com/) | 精灵高清渲染图 + 128px 动图（普通 + 闪光） | `pokemon-sprites/static/pokeos/` `pokemon-sprites/animated/pokeos/` |
| [Pokémon Showdown](https://play.pokemonshowdown.com/) | 精灵像素动图 + gen5 静态图（普通 + 闪光） | `pokemon-sprites/animated/showdown/` `pokemon-sprites/static/showdown/` |
| [feixianer/pokemon-badges](https://github.com/feixianer/pokemon-badges) | 徽章图片（8 地区） | `badges/` |

> 道具图标命名规则：小写 + 去掉连字符/下划线/空格 + 保留点号，与 Serebii ItemDex 图床命名一致。
> 例：`poke-ball` → `pokeball.png`，`cheri-berry` → `cheriberry.png`。

## 目录结构

```
.
├─ README.md / manifest.json      # 说明 + 总索引（各文件路径与条目数）
├─ pkm-data-loader.js             # HUD 用加载器
├─ types.json                     # 18 属性相克表（0 / 0.5 / 1 / 2）
├─ abilities.json                 # 特性 317 条
├─ moves.json                     # 招式 953 条
├─ items.json                     # 道具 2361 条
├─ evolution.json                 # 进化链 534 条
├─ badges.json                    # 徽章 8 个联盟
├─ dex-list.json                  # 全国图鉴列表（1025 只：编号/名字/英文slug/属性）
├─ pokemon/                       # 精灵，按世代拆分（1315 只）
│  ├─ gen-01.json ~ gen-10.json
├─ movesets/                      # 各精灵各代可学招式（升级/机器/蛋/教学）
├─ item-sprites/                  # 道具图标（1988 张 PNG，命名 = slug 规则）
├─ item-sprites-missing.json      # 暂无图的极少数道具清单
├─ badges/                        # 徽章图片（8 地区 68 张 PNG）
└─ pokemon-sprites/               # 精灵图片（命名统一为英文 slug）
   ├─ animated/                   # 动图
   │  ├─ pokeos/                  # PokeOS 128px 动图
   │  │  ├─ normal/               # 普通
   │  │  └─ shiny/                # 闪光
   │  └─ showdown/                # Showdown 像素动图
   │     ├─ normal/               # 普通
   │     └─ shiny/                # 闪光
   └─ static/                     # 静图
      ├─ pokeos/                  # PokeOS 高清渲染图
      │  ├─ normal/               # 普通
      │  └─ shiny/                # 闪光
      └─ showdown/                # Showdown gen5 静态图
         ├─ normal/               # 普通
         └─ shiny/                # 闪光
```

精灵图片文件名统一为**英文名小写 slug**：基础用 `bulbasaur.png`，形态用 `venusaur-mega.png` / `pikachu-gmax.gif` 等（与 PokeAPI 命名一致）。`dex-list.json`（编号→英文名）与 `form-ids.json`（形态编号→英文名）提供查表。

## 在 HUD 中按需加载

```js
const PKM_DATA_BASE = 'https://raw.githubusercontent.com/xianjiu0926/Pokemon/main/';

async function pkmLoad(file) {
  const r = await fetch(PKM_DATA_BASE + file, { cache: 'force-cache' });
  return r.json();
}
// 例：只加载第九世代精灵
const gen9 = await pkmLoad('pokemon/gen-09.json');
```

完整加载器见仓库根目录的 `pkm-data-loader.js`。道具图源基地址：

```js
var PKM_ITEM_SEREBII_BASE = 'https://raw.githubusercontent.com/xianjiu0926/Pokemon/main/item-sprites/';
```

## Schema（节选）

```jsonc
// abilities.json
{ "count": 317, "data": [ { "id": 1, "name": "恶臭", "en": "stench", "desc": "简介…", "effect": "详细效果…", "gen": "第三世代" } ] }

// moves.json
{ "count": 953, "data": [ { "id": 1, "name": "拍击", "en": "Pound", "type": "一般", "cat": "物理", "power": 40, "acc": 100, "pp": 35, "desc": "说明…", "effect": "效果…" } ] }

// items.json
{ "count": 2361, "data": [ { "id": 1, "name": "精灵球", "en": "poke-ball", "cat": "精灵球", "price": 200, "effect": "捕获率 ×1", "desc": "说明…" } ] }

// pokemon/gen-XX.json
{ "gen": "第一世代", "count": 230, "data": [ { "no": 1, "name": "妙蛙种子", "en": "bulbasaur", "types": ["草","毒"], "stats": {"hp":45,"atk":65,"def":65,"spa":49,"spd":49,"spe":45}, "desc": "图鉴描述…", "evolveChainId": 1 } ] }
```

完整字段说明见各文件内数据，结构直观无需额外文档。

## 数据更新（抓取步骤）

方便以后出新世代/新道具时一键重抓。脚本在 `scripts/` 目录。

### 1. 道具图标

```bash
python3 scripts/fetch_item_sprites.py item-sprites/
```

- 自动抓取 Serebii ItemDex 全 14 个分类（战斗效果/树果/装饰品/进化/化石/携带/重要物品/邮件/杂项/精灵球/回复/维生素等），按 slug 规则命名并去重。
- Serebii 缺的（邮件、玉、诱饵模组等）再从 52poke 图床补（图片需带 `Referer: https://wiki.52poke.com/` 头）。
- 依赖：仅 Python3 标准库。

### 2. 道具效果文字（52poke）

```bash
python3 scripts/fetch_item_effects.py --merge
```

- 批量（每批 50 标题）从 52poke MediaWiki API 抓取 effect 为空的道具页，解析「效果/使用效果/游戏中」段落，清洗后增量写入 `items-effect-fill.json`，`--merge` 时合并回 `items.json`。
- 可断点续跑；配合 `--merge` 一步完成抓取 + 回写。

### 3. 特性 / 招式 / 精灵文字数据

```bash
python3 scripts/fetch_abilities.py abilities-new.json   # 特性 317 条
python3 scripts/fetch_moves.py      moves-new.json      # 招式 953 条
python3 scripts/fetch_pokemon.py    pokemon-new.json    # 精灵 1025 只（可加序号范围）
```

均来自 52poke 的 MediaWiki API，端点如下（`format=json`）：

| 数据 | API 端点 |
|---|---|
| 特性列表 | `api.php?action=parse&page=特性列表&prop=links` |
| 特性详情 | `api.php?action=parse&page={特性名}（特性）&prop=wikitext` |
| 招式列表 | `api.php?action=parse&page=招式列表&prop=links` |
| 招式详情 | `api.php?action=parse&page={招式名}（招式）&prop=wikitext` |
| 道具列表 | `api.php?action=parse&page=道具列表&prop=wikitext` |
| 精灵列表 | `api.php?action=parse&page=宝可梦列表（按全国图鉴编号）/简单版&prop=wikitext` |
| 精灵详情 | `api.php?action=parse&page={精灵名}（宝可梦）&prop=wikitext` |
| 图片地址 | `api.php?action=query&prop=imageinfo&iiprop=url&titles=File:{文件名}` |

解析要点：文字数据在页面信息框（`{{信息框 ...}}`）与对应章节段落里；下载图片需带 `Referer: https://wiki.52poke.com/` 头，否则 403。

### 更新数据后：同步 HUD 缓存版本

数据文件（`items.json` / `moves.json` / `abilities.json` / `dex-list.json` 等）更新后，必须同步更新 `pkm-hud` 里的两个值，用户端才会自动拉取新数据（否则用户本地缓存的旧数据不会刷新）：

1. `PKM_DATA_REV`（在 `pkm-hud.js` 里，形如 `r20260929`）——改成新值（如日期）；
2. `PK_VER`（HUD 版本号）——加一个补丁版本号，并推送 `pkm-hud` 仓库。

## 免责声明

1. 本仓库所收录的宝可梦相关**文字、图片、数据均源自上述公开网站**，版权归 **Nintendo / The Pokémon Company / Game Freak 及原始数据提供方（神奇宝贝百科、Serebii.net 等）** 所有。
2. 本仓库仅对公开数据进行**抓取、索引、格式化**，不拥有任何原始数据的版权。
3. 本项目**仅供个人学习、研究、同人创作**使用，**严禁用于任何商业用途**。
4. 数据可能存在遗漏或误差，请以原始网站及官方资料为准。
5. 如权利人认为本仓库内容侵犯其权益，请联系仓库维护者，收到通知后将及时删除相关内容。
