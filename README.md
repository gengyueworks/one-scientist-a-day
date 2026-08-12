# 每天认识一位科学家 · One Scientist A Day

> 一年 365 天，每天认识一位科学家。
> 不讲百科履历，只讲他人生里最要紧的几个时刻：他怎么走到那一步，付出了什么，又放弃了什么。

一个热爱科学的人，把人类历史上最值得认识的那群头脑，一天一个，整理给你。

---

## 🌐 在线展示站

**[每天认识一位科学家 · One Scientist A Day](https://gengyueworks.github.io/one-scientist-a-day/)**

52 篇人物特写，覆盖物理、数学、化学、生物、天文、医学、计算机等 17 个领域，按月份与领域浏览，每篇都是原创叙事散文（800-1200 字）。

---

## 📅 今日科学家

<!-- SCIENTIST-DAILY:BEGIN -->

## IBM PC 发布｜08/12 事件

**领域**：计算机

> 1981年IBM发布第一台个人电脑，PC时代正式开启

（完整人物故事筹备中，敬请期待）


<!-- SCIENTIST-DAILY:END -->

---

## 这是什么

一个日更型科学家人物库，每天按日期推送一位科学家：

- **日期锚点**：每位科学家的文章挂在他的诞辰/忌日/重大成就日
- **原创叙事散文**：不讲百科履历，只讲关键时刻、关键选择与代价（800-1200 字）
- **重点人物长文**：牛顿、居里、爱因斯坦、图灵这类，单独写深度特写（1500-2500 字）
- **自动更新**：GitHub Actions 每天自动跑，写入 README + 归档 + 重建展示站

选题池（372 位科学家，覆盖全年 366 天）在 [`data/pool.json`](data/pool.json)。

## 目录结构

```
├── scientists/               # 已写好的文章
│   └── MM/
│       └── MM-DD-slug.md
├── index.html                # 展示站（GitHub Pages 自动构建）
├── archive/                  # 每日归档
├── data/
│   └── pool.json             # 选题池（366 天全覆盖）
├── _meta/
│   ├── card-template.md      # 文章写作规范（精品标准）
│   └── top50.json            # 重点人物名单
├── scripts/
│   ├── daily_pick.py         # 每日挑选引擎
│   └── build_site.py         # 展示站构建脚本
├── .github/workflows/
│   ├── daily.yml             # 每日自动更新
│   └── pages.yml             # 展示站自动部署
└── README.md
```

## 浏览

- 在线展示站：[One Scientist A Day](https://gengyueworks.github.io/one-scientist-a-day/)
- 按月份浏览文章：`scientists/MM/`
- 全部选题池：`data/pool.json`

## 文章示例

- [牛顿｜一个不肯开口的天才](scientists/01/01-04-newton.md)
- [图灵｜那个让机器开始思考的人](scientists/06/06-23-turing.md)
- [居里｜她把自己也搭了进去](scientists/11/11-07-curie.md)

## 选题来源说明

选题日历参考了 PanSci 泛科学《科学史上的今天》专栏的日期锚点（同题材公开事实），但**所有文字均为本项目原创撰写**，不复制任何原文。每篇卡片的「参考」字段指向原文章或维基百科，用于事实核实。

## 维护与许可证

- 📋 **[维护日志](_meta/MAINTENANCE.md)** —— 记录每日自动更新与工程改进的实际过程
- 📄 **License**：本项目的**文字内容**采用 [CC BY 4.0](LICENSE)（知识共享署名 4.0 国际）
- ⚙️ 自动化：`.github/workflows/daily.yml`（每日更新）+ `pages.yml`（展示站部署）
