import { defineConfig } from 'vitepress'

export default defineConfig({
  lang: 'zh-CN',
  title: '技术学习手记',
  description: '技术原理、实践流程与开发和测试视角的面试专题.',
  base: '/',
  cleanUrls: false,
  appearance: true,
  head: [['link', { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }]],
  themeConfig: {
    logo: '/favicon.svg',
    siteTitle: '技术学习手记',
    nav: [
      { text: '技术学习', link: '/learning/' },
      { text: '技术面试', link: '/interviews/' }
    ],
    sidebar: {
      '/learning/': [{ text: '技术学习', link: '/learning/', collapsed: false, items: [
        { text: 'AI 评测', link: '/learning/ai-evaluation/', collapsed: false, items: [
          { text: '淘宝购物助手在线评测', link: '/learning/ai-evaluation/taobao-online-agent-evaluation' },
          { text: '美团 Agent 评测全览', link: '/learning/ai-evaluation/meituan-agent-evaluation-overview' }
        ] }
      ] }],
      '/interviews/': [{ text: '技术面试', link: '/interviews/', collapsed: false, items: [
        { text: 'AI 评测', link: '/interviews/ai-evaluation/', collapsed: false, items: [
          { text: '在线 Agent 评测面试', link: '/interviews/ai-evaluation/taobao-online-agent-evaluation' },
          { text: 'Agent 评测体系面试', link: '/interviews/ai-evaluation/meituan-agent-evaluation-overview' }
        ] }
      ] }]
    },
    socialLinks: [{ icon: 'github', link: 'https://github.com/songky-ch/songky-ch.github.io' }],
    search: {
      provider: 'local',
      options: {
        locales: {
          root: {
            translations: {
              button: { buttonText: '搜索', buttonAriaLabel: '搜索文档' },
              modal: {
                noResultsText: '未找到相关内容',
                resetButtonTitle: '清除搜索',
                footer: { selectText: '选择', navigateText: '切换', closeText: '关闭' }
              }
            }
          }
        }
      }
    },
    outline: { label: '本页目录' },
    docFooter: { prev: '上一篇', next: '下一篇' },
    darkModeSwitchLabel: '外观',
    sidebarMenuLabel: '目录',
    returnToTopLabel: '返回顶部',
    footer: { message: '技术原理 · 实践方法 · 面试思考', copyright: '© 2026 songky-ch' }
  }
})
