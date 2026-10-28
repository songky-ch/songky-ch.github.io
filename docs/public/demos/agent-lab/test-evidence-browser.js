(()=>{
const $=id=>document.getElementById(id),ok=(v,m)=>{if(!v)throw Error(m);},change=(id,v)=>{$(id).value=v;$(id).dispatchEvent(new Event('change'));};
let scenarios=0,transitions=0;
document.querySelector('[data-tab="evidence"]').click();
for(const m of EvidenceLab.modules){change('evidenceModule',m.id);for(let c=0;c<m.cases.length;c++){
 change('evidenceCase',String(c));ok(!$('evidenceResult'),'reset hides result');ok($('evidencePrev').disabled,'start boundary');
 $('evidenceNext').click();ok(!$('evidenceResult'),'second phase hides result');$('evidenceNext').click();
 ok(JSON.stringify(JSON.parse($('evidenceResult').textContent))===JSON.stringify(EvidenceLab.evaluate(m.id,c).result),'render matches result');ok($('evidenceNext').disabled,'end boundary');
 $('evidencePrev').click();ok(!$('evidenceResult'),'back hides result');$('evidenceReset').click();ok($('evidencePrev').disabled,'reset boundary');transitions+=4;scenarios++;
}}
for(const tab of ['run','rag','eval','production','evidence']){document.querySelector('[data-tab="'+tab+'"]').click();ok(!$(tab).hidden,'active tab');ok(['run','rag','eval','production','evidence'].filter(x=>!$(x).hidden).length===1,'isolated tab');}
return {modules:EvidenceLab.modules.length,scenarios,transitions,tabs:5,passed:true};
})()
