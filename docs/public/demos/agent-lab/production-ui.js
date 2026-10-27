'use strict';
let productionStep=0;
const productionTopic=document.getElementById('productionTopic'),productionPath=document.getElementById('productionPath');
productionTopic.innerHTML=ProductionTopics.map((t,i)=>'<option value="'+i+'">'+esc(t.title)+'</option>').join('');
function renderProduction(){
 const t=ProductionTopics[Number(productionTopic.value)],p=t.paths[Number(productionPath.value)];
 $('productionPrev').disabled=productionStep===0;$('productionNext').disabled=productionStep===p.length-2;
 $('productionView').innerHTML='<h3>'+esc(t.question)+'</h3><p class="muted">考察点: '+esc(t.point)+'</p><p>当前路径: '+esc(p[0])+' · 步骤 '+(productionStep+1)+' / '+(p.length-1)+'</p><ol class="production-flow">'+p.slice(1).map((s,i)=>'<li class="'+(i===productionStep?'current':i<productionStep?'visited':'pending')+'"'+(i===productionStep?' aria-current="step"':'')+'><span>步骤 '+(i+1)+(i>productionStep?' · 尚未展开':'')+'</span><p>'+(i<=productionStep?esc(s):'点击下一步查看这一步的动作与条件.')+'</p></li>').join('')+'</ol><p class="notice">这是预设分支的逐步讲解, 不是实际模型规划、调度或故障注入. 其他情境请切换“条件分支”, 页面不会自动执行外部动作.</p><details class="card"><summary>开发视角: 实现思路与参考回答</summary><p>'+esc(t.answer)+'</p><p><b>递进追问:</b> '+esc(t.follow)+'</p><p><b>容易答错:</b> '+esc(t.wrong)+'</p></details><details class="card"><summary>测试视角: 怎样验证回答成立?</summary><p>'+esc(t.test)+'</p><p><b>测试追问:</b> '+esc(t.testQuestion)+'</p><p>'+esc(t.testFollow)+'</p><p>本页仅展示学习路径. 上述生产验证需要真实或受控替身环境, 本页没有执行这些测试.</p></details><button id="productionRelated">打开对应的可计算演示</button><p><a href="https://songky-ch.github.io/interviews/agent/production-agent.html">阅读完整面试专题</a> · <a href="https://songky-ch.github.io/learning/agent/production-agent.html">阅读机制与来源</a></p>';
 $('productionRelated').addEventListener('click',()=>{document.querySelector('[data-tab="'+t.link+'"]').click();});
}
function resetProductionTopic(){const t=ProductionTopics[Number(productionTopic.value)];productionPath.innerHTML=t.paths.map((p,i)=>'<option value="'+i+'">'+esc(p[0])+'</option>').join('');productionPath.value='0';productionStep=0;renderProduction();}
productionTopic.addEventListener('change',resetProductionTopic);
productionPath.addEventListener('change',()=>{productionStep=0;renderProduction();});
$('productionNext').addEventListener('click',()=>{const t=ProductionTopics[Number(productionTopic.value)];productionStep=Math.min(t.paths[Number(productionPath.value)].length-2,productionStep+1);renderProduction();});
$('productionPrev').addEventListener('click',()=>{productionStep=Math.max(0,productionStep-1);renderProduction();});
$('productionReset').addEventListener('click',()=>{productionStep=0;renderProduction();});
productionTopic.value='0';resetProductionTopic();
