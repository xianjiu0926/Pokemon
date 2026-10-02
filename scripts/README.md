# 抓取脚本说明（更新仓库数据用）

本目录是从外部网站抓数据、更新仓库的脚本。以后要更新某类数据，来这里查「跑哪个」。

## 更新速查（最常见场景）

```bash
# 加新叫声（如 Gen10 1026+，等源站补）
python3 scripts/fetch_cries.py --from 1026

# 补道具效果（批量抓 52poke + 合并回 items.json）
python3 scripts/fetch_item_effects.py --merge

# 补招式效果
python3 scripts/fetch_move_effects.py

# 补精灵可学招式（PokeAPI，支持 --from/--to，断点续跑）
python3 scripts/fetch_movesets.py 899 1025

# 补精灵动图缺口（下载 + 压 128px，断点续跑）
python3 scripts/fetch_missing_animated.py

# 补 Showdown 像素图缺口（4 槽位：动图/静态 × 普通/闪光）
python3 scripts/fetch_showdown_sprites.py

# 批量重压 PokeOS 动图去毛边（阈值二值化，断点续跑，参数=并发数）
python3 scripts/refetch_pokeos_animated.py 6

# 检查缺图（生成 pokemon-sprites-missing.json）
python3 scripts/check_sprites.py
```

## 脚本索引

### 数据 JSON（文字数据，52poke）
| 脚本 | 抓什么 | 输出 |
|---|---|---|
| `fetch_pokemon.py` | 精灵文字数据 | `pokemon/gen-*.json` |
| `fetch_moves.py` | 招式 | `moves.json` |
| `fetch_abilities.py` | 特性 | `abilities.json` |
| `fetch_52poke_items.py` | 道具 | `items.json` |

### 可学招式（PokeAPI）
| 脚本 | 抓什么 | 输出 |
|---|---|---|
| `fetch_movesets.py` | 精灵可学招式（升级/技能机/蛋/教学，按版本分组） | `movesets/pokemon-XXXX.json` |

### 效果字段补全（52poke）
| 脚本 | 用途 |
|---|---|
| `fetch_item_effects.py` | 补 `items.json` 的 effect（`--merge` 合并回写，批量 50/批，断点续跑） |
| `fetch_move_effects.py` | 补 `moves.json` 的 effect |
| `fill_item_effects.py` | 一次性补 effect（已跑完，归档参考） |

### 图片
| 脚本 | 抓什么 | 数据源 |
|---|---|---|
| `fetch_pokemon_sprites.py` | 精灵图（HOME 动图 + 渲染静态，普通/闪光） | PokeOS |
| `fetch_missing_animated.py` | 补 PokeOS 动图缺口（压 128px） | PokeOS |
| `fetch_special_forms.py` | 命名特殊形态图（原始回归/帽子/品种等） | PokeOS |
| `fetch_showdown_sprites.py` | 补 Showdown 像素图缺口（4 槽位） | Pokémon Showdown |
| `fetch_item_sprites.py` | 道具图 | Serebii + 52poke |
| `resize_pokeos_gifs.py` | PokeOS 动图压 128px（阈值二值化去毛边） | 本地处理 |
| `refetch_pokeos_animated.py` | 批量重下 PokeOS 动图原图 + 阈值二值化重压（去毛边） | PokeOS |

### 音频
| 脚本 | 抓什么 | 数据源 |
|---|---|---|
| `fetch_cries.py` | 叫声 `.ogg` | PokeAPI（jsdelivr），支持 `--from/--to` |

### 工具
| 脚本 | 用途 |
|---|---|
| `check_sprites.py` | 扫 8 个图槽，生成缺图清单 |
| `fix_sprite_aliases.py` | 把 pokeos 实际文件名复制成 dex-list 的 en 名（修命名不一致） |

## 抓取约定（写新脚本照这个来）

1. **断点续跑**：进度写 `{name}-done.txt` 或靠「文件已存在就跳过」，重跑不重复。
2. **范围参数**：编号类资源支持 `--from/--to`，加新数据只下新增段。
3. **幂等**：重复跑不产生重复数据；合并回 JSON 用 key 去重。
4. **52poke 限流**：MediaWiki API 批量请求，一次最多 50 个标题，别逐条抓（会 429）。
5. **52poke 图片**：下载必须带 `Referer: https://wiki.52poke.com/`，否则 403。
6. **PokeOS 动图**：源站「编号+简化后缀」命名，完整规则：
   - 原始回归 `-mega`（`383-mega`，不是 `-primal`）
   - 帽子 `-{region}-cap`（`25-unova-cap`，不是 `-unova`）
   - 肯泰罗品种 `-regional-p-{combat/blaze/aqua}`（`128-regional-p-combat`）
   - 奈克洛兹玛 `-dusk/-dawn/-ultra`（`800-dusk`，不是 `-dusk-mane`）
   - 地区形态 `-regional-a/g/h/p`（`26-regional-a`，不是 `-alola`）
   - 海兔 `-west/-east`、土龙节节 `-three-segment`
   - 雌性动图源站没有（只有静态 `-female`）
   - 这套映射已写进 `fetch_pokemon_sprites.py` 的 `pokeos_id()`，抓图直接复用。
7. **Showdown 图**：命名 = 英文小写去连字符 + `mega-x→megax`：
   - 基础名去连字符（`mr-mime→mrmime`、`ho-oh→hooh`、`porygon-z→porygonz`、`type-null→typenull`、`tapu-koko→tapukoko`、`nidoran-f→nidoranf`）
   - `mega-x/y/z→megax/y/z`（`charizard-megax`）；其余形态（`-f`、`-galar`、`-gmax`）保持。
8. **GIF 压缩毛边**：GIF 不支持半透明，缩放原图会硬切半透明边缘出白边/黑边。**正确做法是「阈值二值化」**（alpha≥128 保留、保持原色），**别用预乘 alpha**（半透明压暗会变黑边）。`resize_pokeos_gifs.py` 已按阈值二值化处理。
9. **提交约定**：
   - 纯加图/音频 → 只推数据仓库，HUD 不用动；
   - 动了 JSON → 推数据 + bump `PKM_DATA_REV` + 推 HUD；
   - 动了 HUD 逻辑 → bump `PK_VER` + 推 HUD。
