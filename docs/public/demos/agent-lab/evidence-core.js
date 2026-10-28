(function(root){
'use strict';
const modules=[
 {id:'rewrite',title:'问题改写: 高相似也可能改错',cases:['指代有证据, 安全补全','高相似但删除否定','把 5 秒改成 5 分钟','指代不清, 先问用户'],why:'改写候选不能取代原问题. 检查实体、否定、数值单位、时间范围、权限和意图; 相似度只作辅助信号. 错别字纠正可能改变字面关键词, 所以保护的是规范化实体与约束, 不是所有原始字符.',test:'构造只改变否定、单位和实体的最小对照样本. 记录原问题、候选、保护槽位和决策; 同时评价召回收益与意图损坏率.'},
 {id:'pdf',title:'文档入库: 复杂表格与切片',cases:['文本层与结构可用','OCR 丢失单位','跨页表头待确认','固定切片丢失否定条件'],why:'可用文本层优先解析, 扫描页按需 OCR. 表格保留行列、合并单元格、表头、单位与页码, 也可生成带表头的行组片段参与检索. 语义切片、固定长度和重叠都是可比较策略, 没有固定 512 必错的规则.',test:'检查双栏阅读序、跨页表头、单位、公式符号和出处. OCR 置信度不等于业务正确; 与抽样人工真值核对, 不明内容隔离复核.'},
 {id:'ragfault',title:'RAG 诊断: 不堆组件找证据',cases:['切片破坏前提','召回有噪声','证据正确但答案幻觉','公式抽取不确定'],why:'先冻结失败现场, 分别定位解析、切片、召回、重排与生成. 重叠可能增加重复, 多路召回可能增加噪声, 重排可能增加延时; 用同一评测集比较改动, 不把整套组件当作必胜答案.',test:'检查正确证据是否在语料、候选池、Top K 和最终模型输入中; 只改变故障层后重评, 记录效果和成本.'},
 {id:'multi',title:'多 Agent: Manager 也有边界',cases:['两个独立分析任务','重复投递与迟到结果','子任务证据冲突'],why:'本教学案例采用 Manager 统一调度, 因为审批与证据汇聚容易集中管理. 这不是企业唯一架构. 事件驱动、交接和分层结构也可使用; 关键是所有权、权限、预算与冲突处理. Manager 本身也需持久化与故障恢复.',test:'验证租约过期后旧执行者无法提交, 外部工具另做幂等. 冲突用来源版本和证据裁决, 证据不足交人工, 不能由 Manager 凭空定真伪.'},
 {id:'checkpoint',title:'断点恢复: 写入与检查点之间',cases:['写入已提交, 检查点未保存','写入效果无法查询','副作用前崩溃, 服务支持幂等'],why:'检查点保存状态和结果引用, 不能原子覆盖任意外部服务. 恢复先加载持久化状态与实际操作账本, 再查询业务效果. 相同操作复用幂等键, 改参数必须新建操作并重新批准. 不承诺任意故障下 100% 恢复.',test:'在发送前、服务提交后、回执后、检查点落盘前分别注入故障. 断言业务记录数量、批准版本和下一动作, 不只看对话恢复了.'},
 {id:'deploy',title:'模型服务: 质量与资源准入',cases:['小模型候选满足门槛','小模型质量退化','显存预算不足','服务超时但已开始输出'],why:'调用托管 API 不等于部署模型. 自部署还需权重与许可证、运行时兼容、显存及 KV cache 容量、量化回归、并发调度与压测. 小模型/大模型路由要在业务集上验证; 灰度监控质量、延时和资源, 不只看 token.',test:'记录硬件、模型和量化版本、上下文长度分布、并发、首 token 延时与吞吐. 服务超时是否可以重试取决于流式输出和后续工具效果, 不能重复发送业务动作.'},
 {id:'intent',title:'意图路由: 多意图与兜底口径',cases:['高置信规则命中','多意图有依赖','歧义需要澄清','LLM 占比 40% 的合成流量'],why:'规则、分类模型和 LLM 是可选组合, 不必每次逐层经过. 多意图可形成任务依赖图, 不等于必须拆成多轮对话. 兜底占比须定义分母和路由触发条件; 没有证据支持成熟项目统一低于 5%-10%.',test:'用误路由代价校准置信阈值, 检查缺参、拒识、冲突意图与越权. 按流量类型看路由精确率、召回、澄清率、成本与端到端合格率.'},
 {id:'memory',title:'记忆一致性: 持久记录与缓存',cases:['数据库新版本, 缓存旧版本','持久化失败, 不确认成功','删除事件重复投递','等会话结束才落盘的风险'],why:'MySQL 可存消息、任务、事实与快照元数据, 大文档原件通常放对象存储并保存引用; Redis 可缓存会话且自身也可配置持久化. 关键消息和状态逐次落盘, 数据库事务同时写 outbox, 消费者按版本更新缓存; 不是等会话结束再保证一致性.',test:'测试缓存更新失败、乱序、重复事件、进程崩溃、删除后旧值复活. 重要决策读当前权威版本, 明确最终一致窗口和用户读己之写要求.'},
 {id:'rageval',title:'RAG 指标: 名称不能代替定义',cases:['证据有噪声并含不支持断言','裁判失败','没有召回标签','没有可核验断言'],why:'区分召回、证据支持、事实正确、问题相关性与运营可靠性. 忠实不必然正确, 幻觉率也只有在相同断言集合和二分类规则下才是 1-忠实度. 线上脱敏抽样、人工复核、漂移告警与冻结回归集互补, 不能只监控一个准确率.',test:'固定相关性标注粒度和分母, 分别统计不适用、失败和有效评分. 问答匹配可定义为回答覆盖任务要点, 不等于语义相似度; 上下文相关性需相关性标签或独立裁判.'},
 {id:'redtech',title:'小红书机制迁移: 独立维度与回放',cases:['完整证据','上下文缺失','获取工具失败','语义裁判失败','未请求目标符合度','快照不一致, 拒绝回放','仅行为结果变化','校准标签只有中间档'],why:'来源是 REDtech 原文第 5-17 页的请求单元、分维度状态、规则/语义分工、校准与快照回放. 此处把它迁移成测试计划证据, 状态编码、数据与评分条件均为教学设计. 原文的语义评测不替代线上行为实验.',test:'改变行为数据不应改变语义输入; 不同缺失状态不可合并成 0 分. 核对输入与评分版本, 对独立人工标签计算一致率、加权 Kappa 和低分召回, 报告分母与分布.'}
];
function calibration(human,judge){
 const matrix=Array.from({length:3},()=>[0,0,0]);human.forEach((v,i)=>matrix[v][judge[i]]++);
 const n=human.length,rows=matrix.map(r=>r.reduce((a,b)=>a+b,0)),cols=[0,1,2].map(j=>matrix.reduce((s,r)=>s+r[j],0));
 let observed=0,expected=0;for(let i=0;i<3;i++)for(let j=0;j<3;j++){const weight=Math.abs(i-j)/2;observed+=weight*matrix[i][j]/n;expected+=weight*rows[i]*cols[j]/(n*n);}
 return {matrix,n,agreement:matrix.reduce((s,r,i)=>s+r[i],0)/n,linear_weighted_kappa:expected===0?null:1-observed/expected,zero_recall:rows[0]===0?null:matrix[0][0]/rows[0],human_zero_count:rows[0]};
}
function evaluate(id,c){
 let input={},events=[],result={};
 if(id==='rewrite'){
  const original={entity:'订单 A',environment:'test',negated:true,timeout_seconds:5,intent:'仅查询'};
  const candidates=[{...original},{...original,negated:false},{...original,timeout_seconds:300},null];
  const candidate=candidates[c],changed=candidate?Object.keys(original).filter(k=>original[k]!==candidate[k]):[];
  input={original_text:'只查询测试环境订单 A, 不取消, 超时 5 秒',candidate_text:['查询 test 环境订单 A 的状态, 禁止取消, 超时 5 秒','查询并取消测试环境订单 A, 超时 5 秒','只查询测试环境订单 A, 不取消, 超时 5 分钟','查询它的状态'][c],original_slots:original,candidate_slots:candidate,similarity_fixture:[0.98,0.99,0.99,0.75][c]};
  events=['保留原问题与授权上下文','候选和槽位为预设样例, 没有运行模型或通用解析器','逐字段检查实体、环境、否定、单位和意图'];
  result={changed_fields:changed,decision:c===3?'ASK_USER':changed.length?'USE_ORIGINAL':'ACCEPT_CANDIDATE',semantic_equivalence_guaranteed:false};
 }else if(id==='pdf'){
  input={page:3,table:'接口 | P95 上限 | 单位',row:['创建订单',200,c===1?null:'ms'],source_type:c===1?'scanned':'text-layer',header_verified:c!==2,condition_preserved:c!==3};
  const usable=input.row[2]!==null&&input.header_verified&&input.condition_preserved;
  events=['读取文本层与版面结构; 扫描页按需 OCR','保留表头、行列、单位、原页引用, 不把所有单元格压平','检查跨页延续与前置条件, 本例是预设解析结果'];
  result={status:usable?'READY_FOR_INDEX':'NEEDS_REVIEW',normalized_limit_ms:usable?200:null,chunk:usable?'创建订单接口: P95 <= 200 ms (页3, 表1, 行2)':'不发布有歧义的片段',actual_ocr_executed:false};
 }else if(id==='ragfault'){
  input={question:'取消接口是否适用生产?',required_fact:'仅测试环境可用',evidence_in_corpus:c!==0,candidate_hit:c!==1,in_prompt:c===2,formula_verified:c!==3};
  const layers=['切片层','召回/过滤层','生成层','解析层'];
  events=['冻结问题、语料版本与当次输入','沿解析 → 片段 → 候选 → 模型输入 → 回答定位','保留原配置, 只改已定位层并做配对回归'];
  result={suspected_layer:layers[c],next_check:['恢复父级限制并检查索引片段','检查权限过滤与多路召回, 对重排做对照','保留正确证据, 检查条件完整性与无依据断言','回到原 PDF 核对符号与单位, 未确认不入库'][c],universal_fix:false};
 }else if(id==='multi'){
  input={parent_task:'T-001',child_tasks:['API-risk','UI-risk'],lease_version:2,submitted_version:c===1?1:2,conflicting_evidence:c===2};
  events=['Manager 以 task_id、目标、证据引用和预算派发','子 Agent 只读分析并回传结构化结果; 本页未真实运行代理','账本检查所有权版本, 汇聚时核对证据冲突'];
  result={accept_submission:input.lease_version===input.submitted_version,decision:c===1?'REJECT_STALE':c===2?'REVIEW_CONFLICT':'MERGE_EVIDENCE',external_write_owner:'唯一批准执行者',decentralized_always_wrong:false};
 }else if(id==='checkpoint'){
  input={operation_id:'op-T001-create',checkpoint:'BEFORE_WRITE',business_state:['COMMITTED','UNQUERYABLE','NOT_COMMITTED'][c],idempotency_supported:c!==1,approved_version:1};
  events=['从持久化记录加载任务与操作键, 不只恢复聊天摘要','查询业务状态, 不从旧检查点推断未写入','只在幂等契约、当前授权与参数版本成立时派发'];
  result={next_action:['REUSE_BUSINESS_RESULT','STOP_AND_RECONCILE','REPLAY_SAME_OPERATION_KEY'][c],new_create_requests:c===2?1:0,expected_records_after_reconciliation:c===1?null:1,exactly_once_guaranteed:false};
 }else if(id==='deploy'){
  input={model:'synthetic-small-v2',quality_pass_rate:c===1?0.80:0.96,teaching_gate:0.95,estimated_memory_gib:20,available_memory_gib:c===2?16:24,stream_started:c===3};
  events=['容量数值、分数是预设教学值, 不是实测性能','检查质量门槛和资源准入; 真实值必须来自硬件与任务集测试','灰度监控并保留模型、量化、Prompt 与路由版本'];
  result={decision:c===3?'END_STREAM_WITH_ERROR':input.quality_pass_rate<input.teaching_gate?'KEEP_BASELINE':input.estimated_memory_gib>input.available_memory_gib?'REJECT_CAPACITY':'ELIGIBLE_FOR_CANARY',actual_model_deployed:false,threshold_is_universal:false};
 }else if(id==='intent'){
  input={query:['查询任务状态','先查需求版本, 再生成用例, 不执行','停止它','混合开放任务流量'][c],request_count:100,llm_fallback_requests:c===3?40:8};
  events=['规则/分类/LLM 是候选路由策略, 本例路由结果预设','多意图保留“先后”与“禁止执行”约束','按请求为分母计算占比, 单独看误路由成本与端到端质量'];
  result={route:['READ_TOOL','DEPENDENCY_DAG','ASK_CLARIFICATION','LLM_ROUTE'][c],tasks:c===1?['read_version','generate_cases']:[],execute_tests:false,fallback_rate:input.llm_fallback_requests/input.request_count,quality_cannot_be_inferred_from_rate:true};
 }else if(id==='memory'){
  input={db_version:2,cache_version:1,db_committed:c!==1,event_version:c===2?1:2,deleted:c===2};
  events=['关键状态先持久提交, 事务内记录待发送事件(outbox)','缓存失败可重试, 更新检查版本; 删除使用持久墓碑','重要动作以权威版本为准, 不把“会话结束再同步”视为不丢数据保证'];
  result={acknowledged:c!==1,read_source:c===1?'UNAVAILABLE':'DURABLE_STORE',cache_update:c===2?'IGNORE_OLD_EVENT':c===1?'NO_EVENT':'RETRY_VERSION_2',deleted_value_visible:false,loss_window:c===3?'未落盘消息可随进程丢失, 必须改变写入时机':'本例关键记录已按提交结果处理'};
 }else if(id==='rageval'){
  input={relevant:c===2?null:['A','B'],retrieved:['A','C'],claims:c===3?[]:[{id:'x',supported:true},{id:'y',supported:false}],judge_status:c===1?'error':'ok'};
  const hits=input.relevant?input.retrieved.filter(x=>input.relevant.includes(x)).length:null;
  const supported=input.claims.filter(x=>x.supported).length,den=input.claims.length;
  events=['固定文档粒度与标签版本; 返回2条, 不是宣称固定Top3','检索标签评分和回答评分独立, 裁判失败不抹去检索结果','不支持断言仅按本例二分类定义, 不推出通用事实错误率'];
  result={recall:hits===null?null:hits/input.relevant.length,precision:hits===null?null:hits/input.retrieved.length,faithfulness:c===1||!den?null:supported/den,unsupported_claim_rate:c===1||!den?null:(den-supported)/den,claim_denominator:den,answer_relevance:'未标注, N/A',context_relevance:'仅有二元文档相关标签, 见 precision',judge_error:c===1};
 }else if(id==='redtech'){
  const semanticInput={snapshot_id:c===5?'snap-other':'snap-T001',expected_snapshot_id:'snap-T001',request_time:'2026-10-28T08:00:00+08:00',ordered_artifacts:['case-1','case-2'],rubric:'synthetic-r1',context_status:c===1?'missing_context':c===2?'acquisition_error':'available'};
  input={semantic_input:semanticInput,behavior_analysis_only:{adopted_cases:c===6?8:2}};
  events=['分离语义证据与后续业务效果, 不把采纳数放进裁判输入','本页仅演示快照 ID 校验; 生产还需核对时间、内容、状态和配置版本','分数、理由、执行状态独立保存; 没有真实 LLM 裁判'];
  if(c===5)result={status:'REPLAY_REJECTED',scores:null};
  else{
   const status=c===1?'missing_context':c===2?'acquisition_error':c===3?'judge_error':'scored';
   const dimensions=[{name:'环境授权',status:'scored',score:2,reason:'规则: test 环境符合约束'},{name:'需求覆盖',status,score:status==='scored'?0:null,reason:status==='scored'?'合成裁判记录: 未覆盖取消失败分支':status},{name:'目标符合度',status:c===4?'not_requested':'scored',score:c===4?null:1,reason:c===4?'本次未请求该维度':'合成裁判记录: 仅部分达到指定覆盖目标'}];
   const scored=dimensions.filter(d=>d.status==='scored'),requested=dimensions.filter(d=>d.status!=='not_requested');
   result={status:'FINISHED',dimensions,requested:requested.length,scored:scored.length,coverage:scored.length/requested.length,score_distribution:[0,1,2].map(v=>scored.filter(d=>d.score===v).length),release:'不能仅凭均分发布; 缺证据或关键0分需复核',calibration:calibration(c===7?[1,1,1,1]:[0,0,1,2],c===7?[1,1,1,1]:[0,1,1,2])};
  }
 }
 return {task_id:'T-001 (合成教学任务)',module:id,input,events,result};
}
const api={modules,evaluate,calibration};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.EvidenceLab=api;
})(globalThis);
