// 事件接线检查使用 DOM 替身, 不冒充浏览器渲染或移动端视觉验收.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const html=fs.readFileSync(__dirname+'/index.html','utf8');
const nodes={};for(const match of html.matchAll(/\bid="([^"]+)"/g)){assert.ok(!nodes[match[1]],'duplicate id');nodes[match[1]]={value:'',checked:false,disabled:false,hidden:false,innerHTML:'',events:{},attrs:{},addEventListener(t,f){this.events[t]=f;},setAttribute(k,v){this.attrs[k]=v;}};}
nodes.scenario.value='success';nodes.k.value='3';nodes.agentVersion.value='safe';
const tabs=['run','rag','eval'].map(id=>({dataset:{tab:id},attrs:{},events:{},addEventListener(t,f){this.events[t]=f;},setAttribute(k,v){this.attrs[k]=v;}}));
const document={getElementById(id){assert.ok(nodes[id],'unknown id '+id);return nodes[id];},querySelectorAll(selector){assert.equal(selector,'[data-tab]');return tabs;}};
vm.runInNewContext(fs.readFileSync(__dirname+'/ui.js','utf8'),{document,Lab:(()=>{const m={exports:{}};new Function('module',require('node:fs').readFileSync(__dirname+'/core.js','utf8'))(m);return m.exports;})()});
let checks=0;function click(id){assert.ok(!nodes[id].disabled,'disabled '+id);nodes[id].events.click();}
function check(f){f();checks++;}
check(()=>{assert.equal(nodes.approve.disabled,true);assert.match(nodes.runView.innerHTML,/CREATED/);for(let i=0;i<3;i++)click('next');assert.equal(nodes.next.disabled,true);assert.equal(nodes.approve.disabled,false);click('approve');click('change');assert.match(nodes.runView.innerHTML,/WAITING_APPROVAL/);click('approve');click('next');click('next');click('next');assert.match(nodes.runView.innerHTML,/COMPLETED/);assert.equal(nodes.next.disabled,true);});
check(()=>{click('resetRun');nodes.scenario.value='timeout';nodes.scenario.events.change();for(let i=0;i<3;i++)click('next');click('approve');click('next');click('next');assert.match(nodes.runView.innerHTML,/UNKNOWN/);assert.equal(nodes.next.disabled,true);});
check(()=>{tabs[1].events.click();assert.equal(nodes.rag.hidden,false);assert.equal(nodes.run.hidden,true);assert.equal(tabs[1].attrs['aria-pressed'],'true');for(let i=0;i<3;i++)click('ragNext');assert.equal(nodes.ragNext.disabled,true);assert.match(nodes.ragView.innerHTML,/聚合报告/);assert.match(nodes.ragView.innerHTML,/0.500/);});
check(()=>{nodes.hidden.checked=true;nodes.hidden.events.change();assert.equal(nodes.ragNext.disabled,false);assert.doesNotMatch(nodes.ragView.innerHTML,/逐样本评分<\/h3>/);for(let i=0;i<3;i++)click('ragNext');assert.match(nodes.ragView.innerHTML,/N\/A/);assert.doesNotMatch(nodes.ragView.innerHTML,/&quot;retrieved&quot;/);});
check(()=>{tabs[2].events.click();for(let i=0;i<3;i++)click('evalNext');assert.match(nodes.evalView.innerHTML,/75.0%/);nodes.agentVersion.value='buggy';nodes.agentVersion.events.change();assert.equal(nodes.evalNext.disabled,false);for(let i=0;i<3;i++)click('evalNext');assert.match(nodes.evalView.innerHTML,/0\/4 = 0.0%/);click('evalReset');assert.equal(nodes.evalNext.disabled,false);});
console.log(JSON.stringify({dom_substitute_checks:checks,errors:0,not_browser_rendering:true}));
