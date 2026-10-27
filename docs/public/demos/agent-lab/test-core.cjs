const assert=require('node:assert/strict');
const L=(()=>{const m={exports:{}};new Function('module',require('node:fs').readFileSync(__dirname+'/core.js','utf8'))(m);return m.exports;})();
let checks=0;
function check(f){f();checks++;}
const cfg={k:3,rerank:false,hallucinate:false,hidden:false,timeout:false,judgeError:false};
const score=c=>L.ragScore(L.ragObserve(c),c);
check(()=>{const s=score(cfg);assert.equal(s[0].recall,1);assert.equal(s[0].precision,2/3);assert.equal(s[0].rr,.5);assert.equal(s[1].rr,.5);assert.equal(s[2].recall,null);assert.equal(s[2].accuracy,null);assert.equal(s[2].faithfulness,null);});
check(()=>{const r=L.ragReport(score(cfg));assert.deepEqual(r.mrr,{value:.5,n:2});assert.deepEqual(r.accuracy,{value:1,n:2});assert.deepEqual(r.faithfulness,{value:1,n:2});});
check(()=>{const s=score({...cfg,k:1});assert.equal(s[0].recall,0);assert.equal(s[0].rr,0);assert.equal(s[0].accuracy,0);assert.equal(s[1].recall,0);});
check(()=>{const s=score({...cfg,k:1,rerank:true});assert.equal(s[0].recall,.5);assert.equal(s[0].precision,1);assert.equal(s[0].accuracy,0);assert.equal(s[1].accuracy,1);});
check(()=>{const s=score({...cfg,hallucinate:true});assert.equal(s[0].accuracy,0);assert.equal(s[0].faithfulness,2/3);});
check(()=>{const r=L.ragReport(score({...cfg,hidden:true}));assert.equal(r.recall.value,null);assert.equal(r.faithfulness.n,0);assert.equal(r.accuracy.value,1);});
check(()=>{const s=score({...cfg,judgeError:true});assert.equal(s[0].faithfulness,null);assert.equal(s[0].accuracy,1);assert.equal(L.ragReport(s).faithfulness.n,1);});
check(()=>{const r=L.ragReport(score({...cfg,timeout:true}));assert.equal(r.total,3);assert.equal(r.ok,2);assert.equal(r.error,1);assert.equal(r.accuracy.n,1);});
check(()=>{assert.deepEqual(L.agentReport(L.agentScore(L.agentObserve(false))),{total:4,completed:3,errors:1,goal:3,qualified:3,violations:0});});
check(()=>{assert.deepEqual(L.agentReport(L.agentScore(L.agentObserve(true))),{total:4,completed:3,errors:1,goal:1,qualified:0,violations:2});});
for(const scenario of ['success','assertfail','timeout']){
 check(()=>{let s=L.createRun(scenario);for(let i=0;i<3;i++)s=L.advance(s);assert.equal(s.phase,'WAITING_APPROVAL');assert.deepEqual(L.advance(s),s);assert.equal(s.executions,0);s=L.advance(s,'approve');s=L.advance(s,'change');assert.equal(s.phase,'WAITING_APPROVAL');assert.equal(s.approved,null);s=L.advance(s,'approve');s=L.advance(s);assert.equal(s.executions,1);s=L.advance(s);if(scenario==='timeout'){assert.equal(s.phase,'UNKNOWN');assert.deepEqual(L.advance(s),s);}else{s=L.advance(s);assert.equal(s.phase,'COMPLETED');assert.equal(s.verdict,scenario==='success'?'PASS':'FAIL');}assert.equal(s.executions,1);});
}
check(()=>{let s=L.createRun('success');for(let i=0;i<3;i++)s=L.advance(s);s=L.advance(s,'deny');assert.equal(s.phase,'CANCELLED');assert.equal(s.executions,0);assert.deepEqual(L.advance(s,'approve'),s);});
check(()=>{let s=L.createRun('success');s=L.advance(s,'cancel');assert.equal(s.phase,'CANCELLED');assert.equal(L.advance(s).executions,0);});
// 枚举全部页面允许的 RAG 配置, 检查缺证据时不输出分数以及指标范围.
let combinations=0;
for(let k=1;k<=3;k++)for(let mask=0;mask<32;mask++){
 const c={k};['rerank','hallucinate','hidden','timeout','judgeError'].forEach((key,i)=>c[key]=!!(mask&(1<<i)));
 const rows=score(c),r=L.ragReport(rows);assert.equal(r.total,3);assert.equal(r.ok+r.error,3);
 for(const row of rows)for(const key of ['recall','precision','rr','accuracy','faithfulness'])assert.ok(row[key]===null||(row[key]>=0&&row[key]<=1));
 if(c.hidden)for(const row of rows){assert.equal(row.recall,null);assert.equal(row.faithfulness,null);}
 if(c.timeout)assert.equal(rows[1].accuracy,null);
 combinations++;
}
console.log(JSON.stringify({checks,rag_configurations:combinations,errors:0}));
