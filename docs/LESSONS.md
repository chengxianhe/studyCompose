# 踩过的坑

保持极简。能升级成机器断言的，升级后就从这里删掉。

升级路径：
  一次性错误   → 当场改掉，不记录
  重复 2 次    → 记在这里，并提示我：这条可以考虑用 knowledge.propose 写进知识库了
                （knowledge.search / knowledge.propose 工具不可用时跳过提示，正常记录）
  重复 3 次    → 提炼成 CLAUDE.md 规则
  可机器检测   → 升级成 Konsist / detekt / hook 断言，然后从这里删除

---

- [示例] [2026-09-15] Room 用了 fallbackToDestructiveMigration 会清空用户数据。
  → 已升级为 Konsist 断言，本条可删。
