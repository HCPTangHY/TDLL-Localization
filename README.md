# TDLL 简体中文本地化

[The Demon Lord's Lover](https://ayumu98.itch.io/the-demon-lords-lover) 简体中文翻译项目。

**翻译平台：** [ParaTranz](https://paratranz.cn)

**上游仓库：** [gitgud.io/ayumu98/the-demon-lords-lover-translations](https://gitgud.io/ayumu98/the-demon-lords-lover-translations)

---

## 安装

1. 从 [Releases](../../releases/tag/latest) 下载最新的 `.zip` 文件（**不要解压**）
2. 游戏内 **Settings → Translations → Import translation…** → 选择 zip
3. 选中后即可切换到中文

## 工作流

翻译在 ParaTranz 上进行。CI 自动拉取最新翻译 → 合并英文原文 → 构建游戏包 → 更新 Release。

### 手动构建

```bash
git clone https://gitgud.io/ayumu98/the-demon-lords-lover-translations.git upstream

PZ_TOKEN=xxx PZ_PROJECT_ID=12345 python3 scripts/fetch_pz.py --out pz_export

python3 scripts/build_pack.py \
  --pz-dir pz_export \
  --source upstream/0.18/source \
  --config config.json \
  --out build
```

需要在仓库 Settings → Secrets 中配置 `PZ_TOKEN` 和 `PZ_PROJECT_ID`。

## License

翻译内容版权归原作者 ayumu98 及各译者所有。
