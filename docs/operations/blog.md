ACMOJ Blog
==========

ACMOJ 主页的新闻是一个使用 [Hugo][hugo] 管理的静态站，由 Apache 直接提供服务。其源代码位于 [GitHub][src]。Hugo 的详细使用方法请参见 [其网站][hugo]。

[hugo]: https://gohugo.io/
[src]: https://github.com/ACMClassOJ/blog

## 创建文章

安装 Hugo CLI 后在命令行中运行

```sh
hugo new content posts/insert-post-url-here.md
```

即可创建文章。文章的开头有 YAML 格式的 frontmatter，常见属性如下：

- title: 标题
- date: 日期，使用 ISO 格式
- draft: 若为 true，则生成时会忽略这篇文章
- author: 可以为字符串或对象。若为字符串，则作者栏会显示此名称。若为对象，则应包含以下属性：
  - name: 作者名
  - avatar: 头像 URL
  - description: 作者描述
- weight: 若大于 0，则在 ACMOJ 主页会置顶加粗显示
- tags: 一个字符串数组，表示文章的标签

在 blog 首页会显示文章的前一部分作为摘要。摘要和正文之间以 HTML 注释 &lt;!--more--&gt; 分隔；注意横线与 more 之间不能有空格。

## 部署

Git push 到 GitHub 之后，GitHub 会发出一个 webhook 通知 ACM 服务器，ACM 服务器此时将运行命令重新生成内容。注意，在校园网网络维护时期，webhook 无法送达，此时只能登录到服务器上手动更新。

## 主题

Blog 使用的主题经过定制，源代码位于 [GitHub][theme-src]。更新主题时，需要同时更新 blog repo 中的 submodule。

[theme-src]: https://github.com/ACMClassOJ/hugo-paper
