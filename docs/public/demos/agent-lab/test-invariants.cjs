const fs=require('fs'),assert=require('node:assert/strict');
const root=__dirname,L=(()=>{const m={exports:{}};new Function('module',require('node:fs').readFileSync(__dirname+'/core.js','utf8'))(m);return m.exports;})();
let transitions=0;
for(const scenario of ['success','assertfail','timeout']){
 let frontier=[L.createRun(scenario)];
 for(let depth=0;depth<9;depth++){
  const unique=new Map();
  for(const old of frontier)for(const action of ['next','approve','deny','change','cancel']){
   const s=L.advance(old,action);transitions++;
   assert.ok(s.executions>=old.executions&&s.executions<=1);
   if(s.executions>old.executions){assert.equal(old.phase,'READY');assert.equal(old.approved,old.version);}
   if(['COMPLETED','FAILED','UNKNOWN','CANCELLED'].includes(old.phase))assert.deepEqual(s,old);
   if(s.phase==='WAITING_APPROVAL')assert.equal(s.executions,0);
   unique.set(JSON.stringify([s.phase,s.version,s.approved,s.executions,s.verdict]),s);
  }
  frontier=[...unique.values()];
 }
}
const cfg={k:3,rerank:false,hallucinate:false,hidden:false,timeout:false,judgeError:false};
const before=L.ragObserve(cfg);const gold=L.questions[0].gold;L.questions[0].gold=['unrelated'];assert.deepEqual(L.ragObserve(cfg),before);L.questions[0].gold=gold;
const obs=L.ragObserve(cfg);obs[0].claims[0].cite='C';assert.equal(L.ragScore(obs,cfg)[0].faithfulness,1,'faithfulness independent of citation correctness');
console.log(JSON.stringify({state_transitions_checked:transitions,reference_label_leakage_check:'passed',faithfulness_vs_citation_check:'passed',errors:0}));
