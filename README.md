# TDLL 简体中文本地化

[The Demon Lord's Lover](https://ayumu98.itch.io/the-demon-lords-lover) 简体中文翻译项目。

**翻译平台：** [ParaTranz](https://paratranz.cn)（项目 ID 见 `config.json`）

**上游仓库：** [gitgud.io/ayumu98/the-demon-lords-lover-translations](https://gitgud.io/ayumu98/the-demon-lords-lover-translations)

---

## 安装

1. 从 [Releases](../../releases) 下载最新的 `.zip` 文件（**不要解压**）
2. 游戏内 **Settings → Translations → Import translation…** → 选择 zip
3. 选中后即可切换到中文

## 项目结构

```
config.json              # 包元数据 & PZ 项目配置
scripts/
  build_pack.py          # PZ 导出 → 游戏包构建
  fetch_pz.py            # 从 ParaTranz 下载翻译
.github/workflows/
  build.yml              # 自动构建 CI
```

## 工作流

翻译在 ParaTranz 上进行。CI 自动：

1. 从 ParaTranz 下载最新翻译
2. 克隆上游 [ayumu98 的翻译仓库](https://gitgud.io/ayumu98/the-demon-lords-lover-translations) 获取英文原文
3. 将 PZ 翻译合并到英文源文件中生成游戏包
4. 用上游的 `validate_pack.py` 校验
5. 输出可直接导入游戏的 `.zip`

### 手动构建

```bash
# 1. 克隆上游
git clone https://gitgud.io/ayumu98/the-demon-lords-lover-translations.git upstream

# 2. 从 PZ 下载（需要 token）
PZ_TOKEN=xxx python3 scripts/fetch_pz.py --project-id PROJECT_ID --out pz_export

# 3. 构建
python3 scripts/build_pack.py \
  --pz-dir pz_export \
  --source upstream/0.18/source \
  --config config.json \
  --out build

# 4. 校验（可选）
python3 upstream/tools/validate_pack.py build/zh-cn-tanghy

# build/zh-cn-tanghy.zip 即可导入游戏
```

### CI 触发

- **Push to main** — 修改 config/scripts/workflow 时自动触发
- **手动触发** — Actions 页面 → Run workflow
- **打 tag** — 自动创建 Release 并附带 zip

需要在仓库 Settings → Secrets 中配置 `PZ_TOKEN`。

## 翻译规范

详见上游仓库的 [README](https://gitgud.io/ayumu98/the-demon-lords-lover-translations) 中的翻译指南。

### 已确立术语

| English | 中文 |
|---------|------|
| Class | 职业 |
| Feats | 专长 |
| Moves | 招式 |
| Stats | 属性 |
| Items | 物品 |
| Mage | 法师 |
| Wizard | 巫师 |
| Golem | 魔像 |
| Kobold | 地精 |
| Hero | 主角/勇者（视语境）|
| Presence | 感知 |
| Startup | 前摇 |
| Lag | 后摇 |
| Knockback | 击退 |
| Pull | 拉近 |
| Knocks down | 击倒 |
| Grounded | 地面单位 |

### 角色译名

| English | 中文 |
|---------|------|
| Torne | 托露妮 |
| Seri | 芹莉 |
| Pila | 琵拉 |
| Paila | 帕依拉 |
| Xena | 泽娜 |
| Kira | 琪拉 |
| Viola | 薇奥拉 |
| Rudo (Dojo) | 鲁多道场 |
| Garland | 加尔兰 |

## License

翻译内容版权归原作者 ayumu98 及各译者所有。
