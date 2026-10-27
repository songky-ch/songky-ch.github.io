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
      { text: '技术面试', link: '/interviews/' },
      { text: '测试 Agent Wiki', link: '/test-agent-wiki/' }
    ],
    sidebar: {
      '/test-agent-wiki/': [{ text: '测试 Agent 项目 Wiki', link: '/test-agent-wiki/', collapsed: false, items: [
        { text: '架构设计', link: '/test-agent-wiki/architecture/', collapsed: false, items: [
          { text: '总览与阅读地图', link: '/test-agent-wiki/architecture/' },
          { text: '01. 目标、约束与决策', link: '/test-agent-wiki/architecture/01-scope-decisions' },
          { text: '02. 技术底座与模块架构', link: '/test-agent-wiki/architecture/02-stack-architecture' },
          { text: '03. Windows 客户端与身份', link: '/test-agent-wiki/architecture/03-client-identity' },
          { text: '04. Agent、工具与 Skill', link: '/test-agent-wiki/architecture/04-agent-tools-skills' },
          { text: '05. 任务、执行器与恢复', link: '/test-agent-wiki/architecture/05-tasks-executor' },
          { text: '06. 人工介入与审批', link: '/test-agent-wiki/architecture/06-hitl-policy' },
          { text: '07. RAG 与长短期记忆', link: '/test-agent-wiki/architecture/07-rag-memory' },
          { text: '08. 文档、图片与用例生成', link: '/test-agent-wiki/architecture/08-documents-cases' },
          { text: '09. 接口、UI 与压力性能测试', link: '/test-agent-wiki/architecture/09-testing' },
          { text: '10. 知识库与 Agent 评测', link: '/test-agent-wiki/architecture/10-evaluation' },
          { text: '11. 数据模型与 API 契约', link: '/test-agent-wiki/architecture/11-data-api' },
          { text: '12. 无 Docker 部署与运维', link: '/test-agent-wiki/architecture/12-deployment-operations' },
          { text: '13. 分支目录与验收', link: '/test-agent-wiki/architecture/13-branches-acceptance' },
          { text: '14. 开发顺序与文档规范', link: '/test-agent-wiki/architecture/14-delivery-learning' },
          { text: '15. 术语与官方依据', link: '/test-agent-wiki/architecture/15-glossary-sources' },
          { text: '检查记录与发布说明', link: '/test-agent-wiki/architecture/validation' }
        ] }
      ] }],
      '/learning/': [{ text: '技术学习', link: '/learning/', collapsed: false, items: [
        { text: 'Web 测试', link: '/learning/web-testing/', collapsed: false, items: [
          { text: 'W1 业务链与数据核对', link: '/learning/web-testing/business-flow' }
        ] },
        { text: '接口测试', link: '/learning/api-testing/', collapsed: false, items: [
          { text: 'I1 接口结果判定', link: '/learning/api-testing/api-test-oracle' },
          { text: 'I2 Postman 请求复现', link: '/learning/api-testing/browser-to-postman' },
          { text: 'I3 参数、权限与分页覆盖', link: '/learning/api-testing/api-coverage' },
          { text: 'I4 接口关联与数据管理', link: '/learning/api-testing/api-data-lifecycle' }
        ] },
        { text: 'Mock 测试', link: '/learning/mock-testing/', collapsed: false, items: [
          { text: 'M1 测试替身设计', link: '/learning/mock-testing/test-doubles' },
          { text: 'M2 Python 依赖替换', link: '/learning/mock-testing/patch-dependencies' },
          { text: 'M3 异常与连续返回', link: '/learning/mock-testing/fault-sequences' }
        ] },
        { text: 'Agent', link: '/learning/agent/', collapsed: false, items: [
          { text: '通用 Agent 与垂直领域 Agent', link: '/learning/agent/general-vs-domain-agents' },
          { text: 'Agent 意图识别与路由', link: '/learning/agent/agent-intent-routing' },
          { text: 'A1 Agent 请求链路', link: '/learning/agent/agent-request-map' },
          { text: 'A2 单次工具调用测试', link: '/learning/agent/single-call-tool-testing' }
        ] },
        { text: 'AI 评测', link: '/learning/ai-evaluation/', collapsed: false, items: [
          { text: '淘宝购物助手在线评测', link: '/learning/ai-evaluation/taobao-online-agent-evaluation' },
          { text: '美团 Agent 评测全览', link: '/learning/ai-evaluation/meituan-agent-evaluation-overview' },
          { text: 'RAG、Agent 与混合评测', link: '/learning/ai-evaluation/rag-agent-evaluation' },
          { text: 'EvalScope 架构与光模块案例', link: '/learning/ai-evaluation/evalscope-architecture' },
          { text: 'A3 Agent benchmark 设计', link: '/learning/ai-evaluation/agent-benchmark-design' },
          { text: 'A4 规则与模型评分器', link: '/learning/ai-evaluation/rule-and-llm-graders' },
          { text: 'R3 检索指标与证据覆盖', link: '/learning/ai-evaluation/retrieval-metrics' },
          { text: 'R4 回答事实、证据与引用', link: '/learning/ai-evaluation/rag-answer-quality' },
          { text: 'R5 RAG benchmark 设计', link: '/learning/ai-evaluation/rag-benchmark-design' }
        ] },
        { text: 'RAG', link: '/learning/rag/', collapsed: false, items: [
          { text: '五种 RAG 的同异与实现流程', link: '/learning/rag/rag-architectures' },
          { text: 'R1 知识库问答证据链', link: '/learning/rag/rag-evidence-pipeline' },
          { text: 'R2 切分过滤与重排', link: '/learning/rag/retrieval-candidates' }
        ] }
      ] }],
      '/interviews/': [{ text: '技术面试', link: '/interviews/', collapsed: false, items: [
        { text: 'Web 测试', link: '/interviews/web-testing/', collapsed: false, items: [
          { text: 'W1 业务链与数据核对', link: '/interviews/web-testing/business-flow' }
        ] },
        { text: '接口测试', link: '/interviews/api-testing/', collapsed: false, items: [
          { text: 'I1 接口结果判定', link: '/interviews/api-testing/api-test-oracle' },
          { text: 'I2 Postman 请求复现', link: '/interviews/api-testing/browser-to-postman' },
          { text: 'I3 参数、权限与分页覆盖', link: '/interviews/api-testing/api-coverage' },
          { text: 'I4 接口关联与数据管理', link: '/interviews/api-testing/api-data-lifecycle' }
        ] },
        { text: 'Mock 测试', link: '/interviews/mock-testing/', collapsed: false, items: [
          { text: 'M1 测试替身设计', link: '/interviews/mock-testing/test-doubles' },
          { text: 'M2 Python 依赖替换', link: '/interviews/mock-testing/patch-dependencies' },
          { text: 'M3 异常与连续返回', link: '/interviews/mock-testing/fault-sequences' }
        ] },
        { text: 'Agent', link: '/interviews/agent/', collapsed: false, items: [
          { text: '通用与垂直领域 Agent 面试', link: '/interviews/agent/general-vs-domain-agents' },
          { text: '意图识别与路由面试', link: '/interviews/agent/agent-intent-routing' },
          { text: 'A1 Agent 请求链路', link: '/interviews/agent/agent-request-map' },
          { text: 'A2 单次工具调用测试', link: '/interviews/agent/single-call-tool-testing' }
        ] },
        { text: 'AI 评测', link: '/interviews/ai-evaluation/', collapsed: false, items: [
          { text: '在线 Agent 评测面试', link: '/interviews/ai-evaluation/taobao-online-agent-evaluation' },
          { text: 'Agent 评测体系面试', link: '/interviews/ai-evaluation/meituan-agent-evaluation-overview' },
          { text: 'RAG、Agent 与混合评测面试', link: '/interviews/ai-evaluation/rag-agent-evaluation' },
          { text: 'EvalScope 架构面试', link: '/interviews/ai-evaluation/evalscope-architecture' },
          { text: 'A3 Agent benchmark 设计', link: '/interviews/ai-evaluation/agent-benchmark-design' },
          { text: 'A4 规则与模型评分器', link: '/interviews/ai-evaluation/rule-and-llm-graders' },
          { text: 'R3 检索指标与证据覆盖', link: '/interviews/ai-evaluation/retrieval-metrics' },
          { text: 'R4 回答事实、证据与引用', link: '/interviews/ai-evaluation/rag-answer-quality' },
          { text: 'R5 RAG benchmark 设计', link: '/interviews/ai-evaluation/rag-benchmark-design' }
        ] },
        { text: 'RAG', link: '/interviews/rag/', collapsed: false, items: [
          { text: '五种 RAG 面试专题', link: '/interviews/rag/rag-architectures' },
          { text: 'R1 知识库问答证据链', link: '/interviews/rag/rag-evidence-pipeline' },
          { text: 'R2 切分过滤与重排', link: '/interviews/rag/retrieval-candidates' }
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
