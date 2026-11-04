# 术语表模板

复制为工作目录下的 `glossary.md`，按目标领域增删。**必须在派发翻译前完成。**

术语表是全部并行 agent 的共享前提。漏掉一个高频词，各批就会出现不同译法，
后期统一措辞的成本远高于前置整理。

---

## 翻译规则（所有领域通用，原样保留）

1. **逐项对应**：输入 items 有几项，输出 zh 就必须有几项，顺序完全一致，
   不得合并、拆分、增删。
2. **保留 Markdown 结构**：`#` 标题、`- ` 与 `1. ` 列表、`**粗体**`、`*斜体*`、
   `[文本](URL)`、表格 `|` 语法。URL 一律原样保留，只翻译链接显示文本。
3. **标题层级不变**，标题文字翻译。
4. **数字、百分比、单位、日期、文号、期刊名、政策名、机构名、人名、药物名、
   基因名、统计符号**保留原样。
5. **不添加**任何译者注、解释、前言、总结。
6. **语言风格**：学术、严谨、书面化，使用中文全角标点。
7. 纯链接行或纯符号块照原样保留结构。
8. 表格中的 `<br>` 换行标记原样保留，不得删除或替换。

---

## 示例：学术出版 / 期刊投稿（可直接复用）

| 英文 | 中文 |
|---|---|
| submission guidelines | 投稿指南 |
| manuscript | 稿件 |
| editorial policies | 编辑政策 |
| peer review | 同行评议 |
| double-anonymized peer review | 双盲同行评议 |
| corresponding author | 通讯作者 |
| co-author | 共同作者 |
| Acceptance in Principle (AIP) | 原则性接收（AIP） |
| Article Processing Charge (APC) | 文章处理费（APC） |
| open access | 开放获取 |
| subscription / hybrid | 订阅模式 / 混合模式 |
| competing interests | 利益冲突 |
| reporting standards | 报告规范 |
| data availability statement | 数据可用性声明 |
| code availability | 代码可用性 |
| Matters Arising | Matters Arising（商榷文章） |
| Brief Communication | 简短通讯 |
| Review | 综述 |
| Perspective | 观点文章 |
| Comment | 评论 |
| Correspondence | 读者来信 |
| News & Views | 新闻与观点 |
| self-archiving | 自存档 |
| license to publish | 出版许可 |
| preprint | 预印本 |
| embargo | 报道禁令期 |
| image integrity | 图像完整性 |
| plagiarism | 剽窃 |
| duplicate publication | 重复发表 |
| retraction | 撤稿 |
| correction | 更正 |
| expression of concern | 关注声明 |
| guest edited collection | 客座编辑专辑 |
| biosecurity | 生物安全 |
| clinical trial registration | 临床试验注册 |
| Supplementary Information (SI) | 补充信息（SI） |
| Extended Data | 扩展数据 |
| display item | 展示项 |
| artwork | 图件 |
| figure legend | 图注 |
| Methods | 方法 |
| abstract | 摘要 |
| references | 参考文献 |
| word limit | 字数上限 |
| editorial assessment | 编辑评估 |
| appeals | 申诉 |
| transfer | 转投 |
| production | 出版制作 |
| proof | 校样 |
| accepted manuscript | 录用稿 |
| version of record | 正式发表版 |
| aims and scope | 宗旨与范围 |
| content types | 内容类型 |
| editorial process | 编辑流程 |
| presubmission enquiry | 投稿前咨询 |
| writing and language | 写作与语言 |
| English language editing | 英语语言润色 |
| Digital Object Identifier (DOI) | 数字对象标识符（DOI） |

**保留英文不译**：ORCID、TeX/LaTeX、CONSORT / PRISMA / ARRIVE、Nature Portfolio、
Springer Nature、Creative Commons（CC BY 等）、DOI 缩写、全部机构名与人名。

---

## 其他领域的整理要点

- **开发者文档**：API / endpoint / token / payload 等词按厂商中文文档的既有译法，
  不要自创；代码标识符、命令行、参数名一律不译。
- **法规政策**：条款号、施行日期、发文机关保留原文；法条名称首次出现给中文全称加英文括注。
- **医疗 / 药品**：通用名按国家药典译法，商品名保留英文；剂量单位不译。
- **金融**：机构名、评级体系（如 AAA）、指数名保留英文；金额与币种原样。

整理方法：先读 `_chunks_report.txt` 的篇目清单，从中挑出反复出现的概念词；
拿不准的统一标为"保留英文"，比各批各自发挥要好。
