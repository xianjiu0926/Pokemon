/* pkm-data-loader.js — 按需加载 pkm-data 数据集（供 pkm-hud 等脚本使用）
 * 用法：把 PKM_DATA_BASE 改成你自己的 GitHub 仓库地址，然后：
 *   await PkmData.init();
 *   PkmData.move('拍击')   -> 招式对象
 *   PkmData.pokemon(1)     -> 精灵对象
 */
(function (global) {
  'use strict';

  var PKM_DATA_BASE = 'https://raw.githubusercontent.com/xianjiu0926/Pokemon/main/';

  var cache = {};          // 文件级缓存
  var mem = {};            // 内存索引
  var ready = false;

  function baseUrl() {
    return (typeof window !== 'undefined' && window.__PKM_DATA_BASE__) || PKM_DATA_BASE;
  }

  function fetchJson(file) {
    if (cache[file]) return cache[file];
    cache[file] = fetch(baseUrl() + file, { cache: 'force-cache' })
      .then(function (r) { if (!r.ok) throw new Error('pkm-data 加载失败 ' + file + ' HTTP ' + r.status); return r.json(); });
    return cache[file];
  }

  function index(arr, keys) {
    var m = {};
    (arr || []).forEach(function (o) {
      keys.forEach(function (k) {
        var v = o[k];
        if (v === undefined || v === null) return;
        if (!m[String(v)]) m[String(v)] = o;
      });
    });
    return m;
  }

  var api = {
    ready: function () { return ready; },
    init: function () {
      if (ready) return Promise.resolve(api);
      return Promise.all([
        fetchJson('manifest.json'),
        fetchJson('types.json'),
        fetchJson('abilities.json'),
        fetchJson('moves.json'),
        fetchJson('items.json'),
        fetchJson('evolution.json'),
        fetchJson('badges.json')
      ]).then(function (r) {
        mem.manifest = r[0]; mem.types = r[1]; mem.abilities = r[2].data;
        mem.moves = r[3].data; mem.items = r[4].data;
        mem.evolution = r[5].data; mem.badges = r[6].data;
        mem.moveById = index(mem.moves, ['id']);
        mem.moveByName = index(mem.moves, ['name', 'en', 'jp']);
        mem.abilityByName = index(mem.abilities, ['name', 'en']);
        mem.itemByName = index(mem.items, ['name', 'en', 'jp']);
        ready = true;
        return api;
      });
    },

    // —— 类型 ——
    typeChart: function () { return mem.types.chart; },
    typeEffect: function (atk, def) {
      var c = mem.types.chart;
      return (c && c[atk] && c[atk][def] !== undefined) ? c[atk][def] : 1;
    },

    // —— 特性 / 招式 / 道具 ——
    ability: function (name) { return mem.abilityByName[String(name)] || null; },
    move: function (name) {
      if (mem.moveById[String(name)]) return mem.moveById[String(name)];
      return mem.moveByName[String(name)] || null;
    },
    item: function (name) { return mem.itemByName[String(name)] || null; },
    allAbilities: function () { return mem.abilities; },
    allMoves: function () { return mem.moves; },
    allItems: function () { return mem.items; },

    // —— 徽章 ——
    badges: function () { return mem.badges; },

    // —— 精灵（按世代按需加载） ——
    loadGen: function (gen) {
      // gen: 'gen-01' … 'gen-10'
      var file = 'pokemon/' + gen + '.json';
      return fetchJson(file).then(function (d) {
        mem.pokemon = mem.pokemon || {};
        mem.pokemon[gen] = d.data;
        if (!mem.pokeByNo) { mem.pokeByNo = {}; mem.pokeByName = {}; }
        d.data.forEach(function (p) {
          mem.pokeByNo[p.no] = p;
          mem.pokeByName[p.name] = p;
          mem.pokeByName[p.en] = p;
          mem.pokeByName[p.jp] = p;
        });
        return d.data;
      });
    },
    loadAllGen: function () {
      var gens = ['gen-01','gen-02','gen-03','gen-04','gen-05','gen-06','gen-07','gen-08','gen-09','gen-10'];
      return Promise.all(gens.map(function (g) { return api.loadGen(g); })).then(function () { return api; });
    },
    pokemon: function (noOrName) {
      if (mem.pokeByNo && mem.pokeByNo[noOrName]) return mem.pokeByNo[noOrName];
      if (mem.pokeByName && mem.pokeByName[String(noOrName)]) return mem.pokeByName[String(noOrName)];
      return null;
    },

    // —— 进化链 ——
    evolution: function (chainId) {
      return mem.evolution.find(function (e) { return String(e.id) === String(chainId); }) || null;
    },

    // —— 单只精灵可学招式（movesets/） ——
    loadMoveset: function (no) {
      var file = 'movesets/pokemon-' + String(no).padStart(4, '0') + '.json';
      return fetchJson(file);
    }
  };

  global.PkmData = api;
})(typeof window !== 'undefined' ? window : this);
