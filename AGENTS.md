# 学习站点约定

- 站点: https://songky-ch.github.io/ . 仓库: songky-ch/songky-ch.github.io, 默认分支 main.
- 学习文章: docs/learning/<主题标识>.md; 面试专题: docs/interviews/<主题标识>.md; 图片: docs/public/images/<主题标识>/.
- 成对文章使用同一主题标识及有效相对链接. 两个栏目索引和侧边栏仅加入本次必要条目.
- 来源、版本、核查日期、核心术语和验证状态清楚. 不公开个人学习档案、凭证、私有资料或受控测试快照.
- 构建: npm run docs:build. 预览: npm run docs:preview. GitHub Actions 在 main 更新后构建并部署.
- 用户已授权本次仓库与站点初始化、初始化提交和首页公开发布. 后续文章提交、推送、覆盖及公开发布须有对应授权, 不将初始化授权自动扩展为持续授权.
- 不修改全局 Git 配置, 不强制推送、不 amend, 不捆绑其他未提交修改.
