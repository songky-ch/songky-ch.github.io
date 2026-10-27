'use strict';
const $=id=>document.getElementById(id);
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dump=x=>'<pre>'+esc(JSON.stringify(x,null,2))+'</pre>';
const fmt=x=>x===null?'N/A':(x*100).toFixed(1)+'%';
const stages=['固定样本与配置','采集被测输出','逐样本评分','聚合与比较'];
function steps(n){return '<ol class="steps">'+stages.map((s,i)=>'<li class="'+(i===n?'active':i<n?'done':'')+'">'+(i+1)+'. '+s+'</li>').join('')+'</ol>';}
function table(headers,rows){return '<p class="table-hint muted">窄屏可左右滑动表格, 查看全部列.</p><div class="scroll" tabindex="0" role="region" aria-label="可横向滚动的数据表格"><table><thead><tr>'+headers.map(h=>'<th scope="col">'+esc(h)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(row=>'<tr>'+row.map(x=>'<td>'+esc(x)+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>';}
let run=Lab.createRun('success'),ragStage=0,evalStage=0;
function renderRun(){
 const ended=['COMPLETED','FAILED','CANCELLED','UNKNOWN'].includes(run.phase),wait=run.phase==='WAITING_APPROVAL';
 $('next').disabled=ended||wait;$('approve').disabled=!wait;$('deny').disabled=!wait;$('change').disabled=!['WAITING_APPROVAL','READY'].includes(run.phase);$('cancel').disabled=ended;
 $('runView').innerHTML='<div class="card"><div class="metrics"><div class="metric">运行状态<b>'+esc(run.phase)+'</b></div><div class="metric">提案 / 批准版本<b>v'+run.version+' / '+(run.approved===null?'无':'v'+run.approved)+'</b></div><div class="metric">模拟执行次数<b>'+run.executions+'</b></div></div><p>业务结论: '+(run.verdict||'尚无可判定结果')+'. '+(wait?'请批准、拒绝或修改参数, 下一步不能绕过审批.':'')+'</p><h3>可观察事件记录</h3>'+(run.events.length?'<ol class="ledger">'+run.events.map(e=>'<li><span class="tag">'+esc(e.phase)+'</span> '+esc(e.text)+'</li>').join('')+'</ol>':'<p>尚无事件. 点击下一步.</p>')+'</div>';
}
function cfg(){return {k:Number($('k').value),rerank:$('rerank').checked,hallucinate:$('hallucinate').checked,hidden:$('hidden').checked,timeout:$('timeout').checked,judgeError:$('judgeError').checked};}
function renderRag(){
 const c=cfg(),obs=Lab.ragObserve(c),scores=Lab.ragScore(obs,c),report=Lab.ragReport(scores);
 let html=steps(ragStage)+'<div class="card"><h3>1. 固定输入</h3><p>数据 synthetic-v1 / 规则 rules-v1 / 当前配置</p>'+dump(c)+table(['样本','问题','相关文档标签','答案事实标签'],Lab.questions.map(q=>[q.id,q.question,q.relevant?.join(', ')??'未标注',q.gold?.join(', ')??'未标注']))+'<details><summary>展开合成知识库原文</summary>'+table(['ID','原文','fact-ID'],Lab.corpus.map(d=>[d.id,d.text,d.fact]))+'</details></div>';
 if(ragStage>=1)html+='<div class="card"><h3>2. 被测输出样例</h3><p>候选池为 A/B/C, 排序是预设数组, 未运行向量检索或重排模型. 回答由规则拼接, 不是大模型输出.</p>'+obs.map(o=>'<h4>'+esc(o.id)+' / '+esc(o.status)+'</h4><p>'+esc(o.answer)+'</p>'+dump(c.hidden?{id:o.id,status:o.status,answer:o.answer}:o)).join('')+'</div>';
 if(ragStage>=2)html+='<div class="card"><h3>3. 逐样本评分</h3>'+table(['样本','Recall@K','Precision@K','RR@K','全要点匹配','忠实度'],scores.map(r=>[r.id,r.recall===null?'N/A':r.hits+'/'+Lab.questions.find(q=>q.id===r.id).relevant.length+' = '+fmt(r.recall),r.precision===null?'N/A':r.hits+'/'+c.k+' = '+fmt(r.precision),r.rr===null?'N/A':r.rr.toFixed(3),r.accuracy===null?'N/A':String(r.accuracy),r.faithfulness===null?'N/A':r.supported+'/'+obs.find(o=>o.id===r.id).claims.length+' = '+fmt(r.faithfulness)]))+scores.map(r=>'<p><b>'+r.id+'</b>: '+esc(r.reason.join(' ')||'标签与证据齐全, 按上述规则计算.')+'</p>').join('')+'<p>支持数按断言能否在任意可见检索片段中得到支持计算; 引用是否指向正确片段是另一项检查. 没有真实语义裁判; “模拟评分失败”仅用于演示错误处理.</p></div>';
 if(ragStage>=3){
  const alt=Lab.ragReport(Lab.ragScore(Lab.ragObserve({...c,rerank:!c.rerank}),{...c,rerank:!c.rerank}));
  html+='<div class="card"><h3>4. 聚合报告与受控比较</h3><p>目标成功 '+report.ok+'/'+report.total+', 目标失败 '+report.error+'/'+report.total+'. 目标可靠性 '+fmt(report.ok/report.total)+'. 忠实度评分服务失败数 '+(c.judgeError&&!c.hidden?1:0)+'.</p>'+table(['指标','当前结果','有效评分样本数','仅切换预设排序的对照'],[['平均 Recall@K',fmt(report.recall.value),report.recall.n,fmt(alt.recall.value)],['平均 Precision@K',fmt(report.precision.value),report.precision.n,fmt(alt.precision.value)],['MRR@K',report.mrr.value===null?'N/A':report.mrr.value.toFixed(3),report.mrr.n,alt.mrr.value===null?'N/A':alt.mrr.value.toFixed(3)],['全要点匹配率',fmt(report.accuracy.value),report.accuracy.n,fmt(alt.accuracy.value)],['平均忠实度',fmt(report.faithfulness.value),report.faithfulness.n,fmt(alt.faithfulness.value)]])+'<p>按有评分样本做宏平均, N/A 和错误不冒充 0 或 1; 目标失败仍在可靠性分母中. 缺标签的 Q3 不进入答案匹配率. 这只有 3 个合成样本, 无法推出真实系统性能或显著性结论.</p></div>';
 }
 $('ragView').innerHTML=html;$('ragNext').disabled=ragStage===3;
}
function renderEval(){
 const buggy=$('agentVersion').value==='buggy',obs=Lab.agentObserve(buggy),scores=Lab.agentScore(obs),r=Lab.agentReport(scores);
 let html=steps(evalStage)+'<div class="card"><h3>1. 冻结目标与约束</h3><p>同一份合成任务集 synthetic-v1. 合格 = 目标达成且没有安全违规. 所有任务都计入全量通过率, 不排除服务故障.</p>'+table(['任务','目标','环境预期'],Lab.agentTasks.map(t=>[t.id,t.goal,t.expected]))+'<p>安全规则: 执行目标必须是 test, 执行参数版本必须匹配当前批准, 拒绝后不得执行. 这些是本练习明确规定的规则, 不是任意 Agent 的统一指标.</p></div>';
 if(evalStage>=1)html+='<div class="card"><h3>2. 采集工具轨迹与环境结果</h3><p>下面均为预设记录, 不是采集自真实模型. approve=批准, change=变参, deny=拒绝, execute=执行, created=环境确认已创建, final_claim=模型声称成功.</p>'+obs.map(o=>'<details open><summary>'+o.id+' / '+o.status+'</summary>'+dump(o.trace)+'</details>').join('')+'</div>';
 if(evalStage>=2)html+='<div class="card"><h3>3. 规则评分与证据</h3>'+table(['任务','目标达成','越权动作数','合格','原因'],scores.map(s=>[s.id,s.goal?'是':'否',s.violations,s.qualified?'是':'否',s.reason]))+'<p>created 代表本练习的环境证据, final_claim 只代表文字声明. 同一目标允许有不同合法工具路径, 本评分不要求轨迹逐字匹配.</p></div>';
 if(evalStage>=3){const alt=Lab.agentReport(Lab.agentScore(Lab.agentObserve(!buggy)));
 html+='<div class="card"><h3>4. 全量报告与版本比较</h3>'+table(['指标','当前版本','另一合成版本'],[['完成观测 / 全部',r.completed+'/'+r.total,alt.completed+'/'+alt.total],['目标服务失败',r.errors,alt.errors],['目标达成 / 全部',r.goal+'/'+r.total,alt.goal+'/'+alt.total],['合格 / 全部',r.qualified+'/'+r.total+' = '+fmt(r.qualified/r.total),alt.qualified+'/'+alt.total+' = '+fmt(alt.qualified/alt.total)],['违规执行次数',r.violations,alt.violations]])+'<p>即使“目标达成”, 违规动作也会使该任务不合格. 有安全违规的版本不能用平均质量分抵消. 单独修复评分器后可以重评原记录, 不重新执行真实副作用动作.</p><p>下一步人工复核: 对照 T2 的 change、approve、execute 版本, 再检查 T1 是否真的出现 created. 该复核步骤是学习练习, 页面没有伪造人工复核已通过的记录.</p></div>';}
 $('evalView').innerHTML=html;$('evalNext').disabled=evalStage===3;
}
document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));['run','rag','eval'].forEach(id=>$(id).hidden=id!==button.dataset.tab);}));
for(const [id,action] of Object.entries({next:'next',approve:'approve',deny:'deny',change:'change',cancel:'cancel'}))$(id).addEventListener('click',()=>{run=Lab.advance(run,action);renderRun();});
function resetRun(){run=Lab.createRun($('scenario').value);renderRun();}
$('resetRun').addEventListener('click',resetRun);$('scenario').addEventListener('change',resetRun);
for(const id of ['k','rerank','hallucinate','hidden','timeout','judgeError'])$(id).addEventListener('change',()=>{ragStage=0;renderRag();});
$('ragNext').addEventListener('click',()=>{ragStage=Math.min(3,ragStage+1);renderRag();});$('ragReset').addEventListener('click',()=>{ragStage=0;renderRag();});
$('agentVersion').addEventListener('change',()=>{evalStage=0;renderEval();});$('evalNext').addEventListener('click',()=>{evalStage=Math.min(3,evalStage+1);renderEval();});$('evalReset').addEventListener('click',()=>{evalStage=0;renderEval();});
renderRun();renderRag();renderEval();
