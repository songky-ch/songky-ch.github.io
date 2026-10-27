(() => {
 const doc=document,find=id=>doc.getElementById(id),assert=(v,m)=>{if(!v)throw Error(m);};
 const select=(id,value)=>{find(id).value=String(value);find(id).dispatchEvent(new Event('change',{bubbles:true}));};
 doc.querySelector('[data-tab="production"]').click();
 assert(!find('production').hidden && find('run').hidden,'tab isolation');
 let paths=0,steps=0;
 for(let topic=0;topic<10;topic++){
  select('productionTopic',topic);
  const count=find('productionPath').options.length;
  for(let path=0;path<count;path++){
   select('productionPath',path);
   assert(find('productionPrev').disabled,'reset at start');
   assert(find('productionView').textContent.includes('尚未展开'),'future stages not revealed');
   let clicks=0;
   while(!find('productionNext').disabled){find('productionNext').click();assert(++clicks<=6,'bounded path');steps++;}
   assert(!find('productionView').textContent.includes('尚未展开'),'all stages revealed');
   assert(find('productionView').querySelectorAll('details').length===2,'two expert views');
   find('productionPrev').click();assert(!find('productionNext').disabled,'back enables next');
   find('productionReset').click();assert(find('productionPrev').disabled,'reset works');
   paths++;
  }
  find('productionRelated').click();
  assert(find('production').hidden,'related demo navigation');
  doc.querySelector('[data-tab="production"]').click();
 }
 assert(paths===29,'expected branch coverage');
 select('productionTopic',2);select('productionPath',4);
 for(let n=0;n<3;n++)find('productionNext').click();
 assert(find('productionView').textContent.includes('UNKNOWN'),'unknown side effect is explicit');
 select('productionTopic',0);
 return {topics:10,paths,forward_transitions:steps,errors:0,viewport:innerWidth,horizontal_overflow:doc.documentElement.scrollWidth>innerWidth};
})()
