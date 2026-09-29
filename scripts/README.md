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

# 补精灵动图缺口（下载 + 压 128px，断点续跑）
python3 scripts/fetch_missing_animated.py

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
| `resize_pokeos_gifs.py` | PokeOS 动图压 128px | 本地处理 |

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
6. **PokeOS 动图**：源站是「编号+简化后缀」命名（`383-mega`=原始回归、`25-*-cap`=帽子、`128-regional-p-*`=品种），动图压到 128px。
7. **提交约定**：
   - 纯加图/音频 → 只推数据仓库，HUD 不用动；
   - 动了 JSON → 推数据 + bump `PKM_DATA_REV` + 推 HUD；
   - 动了 HUD 逻辑 → bump `PK_VER` + 推 HUD。
