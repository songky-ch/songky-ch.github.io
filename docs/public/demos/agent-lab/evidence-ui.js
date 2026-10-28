'use strict';
let evidenceStep=0;
const evidenceModule=$('evidenceModule'),evidenceCase=$('evidenceCase');
evidenceModule.innerHTML=EvidenceLab.modules.map(m=>'<option value="'+m.id+'">'+esc(m.title)+'</option>').join('');
function renderEvidence(){
 const m=EvidenceLab.modules.find(m=>m.id===evidenceModule.value),record=EvidenceLab.evaluate(m.id,Number(evidenceCase.value));
 const phases=['1. 固定输入','2. 检查与分流','3. 结果与验收'];
 $('evidencePrev').disabled=evidenceStep===0;$('evidenceNext').disabled=evidenceStep===2;
 $('evidenceView').innerHTML='<h3>'+esc(m.title)+'</h3><ol class="steps">'+phases.map((x,i)=>'<li class="'+(i===evidenceStep?'active':i<evidenceStep?'done':'')+'">'+x+'</li>').join('')+'<p class="tag">'+esc(record.task_id)+'</p><article class="card"><h3>输入快照</h3><pre>'+esc(JSON.stringify(record.input,null,2))+'</pre></article>'+(evidenceStep>=1?'<article class="card"><h3>执行依据</h3><ol>'+record.events.map(e=>'<li>'+esc(e)+'</li>').join('')+'</ol></article>':'')+(evidenceStep===2?'<article class="card"><h3>结果记录</h3><p>null 表示无有效数值, 不是 0 分. 下方字段均来自当前合成情境.</p><pre id="evidenceResult">'+esc(JSON.stringify(record.result,null,2))+'</pre></article><details class="card"><summary>面试回答: 为什么这样做?</summary><p>'+esc(m.why)+'</p></details><details class="card"><summary>测试追问: 怎样证明实现正确?</summary><p>'+esc(m.test)+'</p><p>这些是生产系统的验收方向. 本页验证的是合成分支和计算, 不代表做过真实故障注入.</p></details>':'<p>点击下一步, 查看当前条件下的检查和结果.</p>')+'<p><a href="https://songky-ch.github.io/learning/ai-evaluation/redtech-evaluation.html">小红书原文机制与项目迁移</a> · <a href="https://songky-ch.github.io/interviews/agent/production-agent.html">完整项目叙述与新增面试追问</a></p>';
}
function resetEvidenceModule(){const m=EvidenceLab.modules.find(m=>m.id===evidenceModule.value);evidenceCase.innerHTML=m.cases.map((s,i)=>'<option value="'+i+'">'+esc(s)+'</option>').join('');evidenceCase.value='0';evidenceStep=0;renderEvidence();}
evidenceModule.addEventListener('change',resetEvidenceModule);
evidenceCase.addEventListener('change',()=>{evidenceStep=0;renderEvidence();});
$('evidencePrev').addEventListener('click',()=>{evidenceStep=Math.max(0,evidenceStep-1);renderEvidence();});
$('evidenceNext').addEventListener('click',()=>{evidenceStep=Math.min(2,evidenceStep+1);renderEvidence();});
$('evidenceReset').addEventListener('click',()=>{evidenceStep=0;renderEvidence();});
evidenceModule.value='rewrite';resetEvidenceModule();
