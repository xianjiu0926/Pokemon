# 人物立绘

宝可梦人物立绘图库，抓取自神奇宝贝百科（[wiki.52poke.com](https://wiki.52poke.com)）。

> 版权归任天堂 / The Pokémon Company / Game Freak 等官方权利方所有；52poke 仅为整理/翻译来源，尊重其劳动成果。本目录仅个人学习/同人使用。

## 目录结构

```
人物立绘/
├── {角色名}/
│   └── {角色名}.png       ← 该角色主立绘（每个角色 1 张）
└── _portraits-manifest.json  ← 角色清单
```

## 命名规则

1. **文件夹名 = 角色名（简体）**，不带「（动画）/（特别篇）/（THE ORIGIN）」等媒体版本后缀，也不做简繁混用（统一简体）。
2. **图片名 = 角色名 + 扩展名**（如 `大吾.png`、`竹兰.png`），不用版本后缀。
3. 同一角色若有多张立绘，命名 `角色名_1.png`、`角色名_2.png` 递增。

## 筛选规则

- 只抓页面有「登场人物信息框」模板的**具体角色**；NPC 训练家类型（医生、护士、场长、短裤小子等）没有该信息框，自动排除。
- **排除旁支游戏角色**：随乐拍、宝可梦巡护员、Masters EX、Champions、圆形竞技场、XD、战棋大师、卡牌GB、名侦探皮卡丘、Café Mix 等。
- 仅保留单人立绘，群像图（多角色同框）不收录。

## 抓取脚本

`scripts/fetch_portraits.py`，可复用：

```bash
python3 scripts/fetch_portraits.py --scan                        # 扫描分类 + 合并，写清单（不下载）
python3 scripts/fetch_portraits.py --download                    # 读清单下载（断点续跑）
python3 scripts/fetch_portraits.py --titles "小智（动画）|大吾（特别篇）"  # 指定角色补抓
python3 scripts/fetch_portraits.py --cats "主角|勁敵|冠军"       # 指定分类
```

分类来源（游戏角色）：`主角`、`勁敵`、`道馆馆主`、`四天王`、`冠军`、`训练家类型`。
动画主角团（小智、小霞、小刚等）通过 `--titles` 单独补充。

## 更新约定

- 纯新增/修正立绘 → 只推数据仓库，不动 HUD 版本。
- 新增角色优先用 `--titles` 补抓，抓完自行重命名为 `角色名.png` 并同步 manifest。
