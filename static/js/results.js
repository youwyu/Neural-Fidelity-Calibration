// All robot rows together. Inspect the paper's exact plotted samples on demand.
(() => {
  const section=document.querySelector('#results');
  const explorer=section.querySelector('.results-explorer');
  const dataUrl=new URL('./results-data.js',document.currentScript.src).href;
  const assetUrl=new URL('../images/results-panels/',document.currentScript.src).href;
  const robotAssetUrl=new URL('../images/results-robots/',document.currentScript.src).href;
  const robotSnapshots=['ant','go1','h1','ingenuity','jackal_pr146'];
  const grid=explorer.querySelector('.results-grid');
  const status=explorer.querySelector('[data-results-status]');
  const tabs=Array.from(explorer.querySelectorAll('[data-results-environment]'));
  const legend=explorer.querySelector('.results-legend');
  const dialog=section.querySelector('.results-dialog');
  const dialogTitle=dialog.querySelector('[data-results-title]');
  const comparison=dialog.querySelector('.results-comparison');
  const detailNote=dialog.querySelector('[data-results-detail-note]');
  let data,environment='flat',started=false,opener,activePlot;
  const titles={flat:'Flat environment',rough:'Rough environment',residual:'Residual fidelity'};
  explorer.hidden=false;
  function format(pair){return `(${pair.map(value=>value.toFixed(3)).join(', ')})`;}
  function name(panel){return panel.method==='SDE-TCN'?'SDE–TCN (ours)':panel.method.replaceAll('-', '–');}
  function clearActive(){if(activePlot){activePlot.clear();activePlot=null;}}
  function plot(panel,detail=false) {
    const box=document.createElement('div');box.className='posterior-plot';box.tabIndex=0;
    box.dataset.sourceImage=String(panel.source_image);box.setAttribute('role','group');
    const context=`${data.robots[panel.robot]} · ${name(panel)} · ${titles[panel.environment]}`;
    box.setAttribute('aria-label',`${context}. Inspect 72 samples with the arrow keys; Enter compares environments.`);
    const img=document.createElement('img');img.src=assetUrl+panel.file;img.width=512;img.height=512;img.decoding='async';img.loading='lazy';
    img.alt=`${context}: posterior density, sampled points, ground truth, and posterior mean.`;
    const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');svg.setAttribute('viewBox','0 0 512 512');svg.setAttribute('aria-hidden','true');
    const ring=document.createElementNS(svg.namespaceURI,'circle');ring.setAttribute('class','sample-highlight');ring.setAttribute('r','20');ring.setAttribute('vector-effect','non-scaling-stroke');svg.append(ring);
    const readout=document.createElement('output');readout.className='sample-readout';readout.setAttribute('aria-live','off');
    box.append(img,svg,readout);
    let selected=-1,pinned=false;
    const handle={clear(){selected=-1;pinned=false;box.classList.remove('has-selection','sample-pinned');delete box.dataset.sampleIndex;readout.textContent='';}};
    function select(index,pin=false,keyboard=false) {
      if(activePlot&&activePlot!==handle)activePlot.clear();activePlot=handle;
      selected=index;pinned=pin;
      const point=panel.samples[index],rect=box.getBoundingClientRect();
      ring.setAttribute('cx',String(point[0]*512));ring.setAttribute('cy',String((1-point[1])*512));ring.setAttribute('r',String(7*512/rect.width));
      box.classList.add('has-selection');box.classList.toggle('sample-pinned',pin);box.dataset.sampleIndex=String(index);
      readout.setAttribute('aria-live',keyboard?'polite':'off');readout.textContent=`Sample ${index+1} · ${format(point)}`;
      box.setAttribute('aria-label',`${context}. Sample ${index+1}, normalized coordinates ${format(point)}. Arrow keys inspect samples; Enter compares environments.`);
    }
    function nearest(event) {
      const r=box.getBoundingClientRect(),x=(event.clientX-r.left)/r.width,y=1-(event.clientY-r.top)/r.height;
      let closest=-1,distance=12*12;
      panel.samples.forEach((p,i)=>{const d=((p[0]-x)*r.width)**2+((p[1]-y)*r.height)**2;if(d<distance){distance=d;closest=i;}});
      return closest;
    }
    box.addEventListener('pointermove',event=>{
      if(pinned||event.target.closest('button'))return;
      const index=nearest(event);if(index<0)handle.clear();else if(index!==selected)select(index);
    });
    box.addEventListener('pointerleave',()=>{if(!pinned)handle.clear();});
    box.addEventListener('click',event=>{
      if(event.target.closest('button'))return;
      const index=nearest(event);
      if(index>=0){if(pinned&&selected===index)handle.clear();else select(index,true);}
      else if(!detail)showComparison(panel,box);else handle.clear();
    });
    box.addEventListener('keydown',event=>{
      if(event.target!==box)return;
      let index;
      if(['ArrowRight','ArrowDown'].includes(event.key))index=(selected+1)%panel.samples.length;
      if(['ArrowLeft','ArrowUp'].includes(event.key))index=selected<0?panel.samples.length-1:(selected+panel.samples.length-1)%panel.samples.length;
      if(event.key==='Home')index=0;if(event.key==='End')index=panel.samples.length-1;
      if(index!==undefined){event.preventDefault();select(index,true,true);}
      else if(event.key===' '){event.preventDefault();select(selected<0?0:selected,!pinned,true);}
      else if(event.key==='Enter'&&!detail){event.preventDefault();showComparison(panel,box);}
      else if(event.key==='Escape'&&!dialog.open){event.preventDefault();handle.clear();}
    });
    if(!detail) {
      const open=document.createElement('button');open.type='button';open.className='plot-open';open.textContent='↗';
      open.setAttribute('aria-label',`Enlarge ${context}`);open.addEventListener('click',()=>showComparison(panel,open));box.append(open);
    }
    return box;
  }
  function showComparison(panel,button) {
    clearActive();opener=button;
    const residual=panel.environment==='residual';
    const panels=data.panels.filter(p=>p.robot===panel.robot&&(residual?p.environment==='residual':p.method===panel.method));
    dialogTitle.textContent=`${data.robots[panel.robot]} · ${residual?'Residual fidelity':name(panel)}`;
    comparison.replaceChildren();
    panels.forEach(p=>{
      const figure=document.createElement('figure'),heading=document.createElement('h3');heading.textContent=residual?p.method:titles[p.environment];
      const info=document.createElement('dl');info.className='results-coordinates';
      for(const [label,value] of [['Ground truth',format(p.truth)],['Posterior mean',format(p.mean)]]) {
        const row=document.createElement('div'),dt=document.createElement('dt'),dd=document.createElement('dd');dt.textContent=label;dd.textContent=value;row.append(dt,dd);info.append(row);
      }
      figure.append(heading,plot(p,true),info);comparison.append(figure);
    });
    detailNote.textContent=residual?'Coordinates are normalized within each panel.':'Sample and marker coordinates are normalized within the plotted parameter ranges.';
    dialog.showModal();
  }
  function render() {
    if(!data)return;clearActive();grid.replaceChildren();
    const visiblePanel=p=>p.environment===environment||(environment==='rough'&&p.environment==='residual');
    const methods=data.panels.filter(p=>p.robot===0&&visiblePanel(p));
    const table=document.createElement('table');table.className='posterior-matrix';if(environment==='rough')table.classList.add('has-residual');
    const thead=document.createElement('thead'),header=document.createElement('tr'),corner=document.createElement('th');corner.scope='col';corner.setAttribute('aria-label','Robot');header.append(corner);
    methods.forEach(panel=>{const th=document.createElement('th');th.scope='col';th.textContent=name(panel);if(panel.method==='SDE-TCN')th.className='is-ours';header.append(th);});thead.append(header);table.append(thead);
    const tbody=document.createElement('tbody');
    data.robots.forEach((label,robot)=>{
      const row=document.createElement('tr'),heading=document.createElement('th');heading.scope='row';
      const snapshot=document.createElement('img');snapshot.className='results-robot-snapshot';snapshot.src=robotAssetUrl+robotSnapshots[robot]+'.webp';snapshot.alt=label;snapshot.width=80;snapshot.height=88;snapshot.loading='lazy';snapshot.decoding='async';heading.append(snapshot);row.append(heading);
      data.panels.filter(p=>p.robot===robot&&visiblePanel(p)).forEach(panel=>{const cell=document.createElement('td');cell.append(plot(panel));row.append(cell);});tbody.append(row);
    });
    table.append(tbody);grid.append(table);
    tabs.forEach(tab=>{const selected=tab.dataset.resultsEnvironment===environment;tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1;});
    grid.setAttribute('aria-labelledby',tabs.find(tab=>tab.dataset.resultsEnvironment===environment).id);
    status.classList.add('is-sr-only');status.textContent=`All five robot systems, ${titles[environment]}, ${methods.length*5} panels.`;
    legend.hidden=false;
  }
  function initialize() {
    if(started)return;started=true;
    const script=document.createElement('script');script.src=dataUrl;script.async=true;
    const fail=()=>{status.classList.remove('is-sr-only');status.textContent='The results could not load. Reload the page to try again.';};
    script.onload=()=>{data=window.NFCResultsData;if(data)render();else fail();};script.onerror=fail;document.head.append(script);
  }
  tabs.forEach((tab,index)=>{
    tab.addEventListener('click',()=>{environment=tab.dataset.resultsEnvironment;render();});
    tab.addEventListener('keydown',event=>{
      let next;if(event.key==='ArrowRight')next=(index+1)%tabs.length;if(event.key==='ArrowLeft')next=(index+tabs.length-1)%tabs.length;
      if(event.key==='Home')next=0;if(event.key==='End')next=tabs.length-1;
      if(next!==undefined){event.preventDefault();tabs[next].click();tabs[next].focus();}
    });
  });
  dialog.querySelector('[data-results-close]').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
  dialog.addEventListener('close',()=>{clearActive();if(opener&&opener.isConnected)opener.focus({preventScroll:true});});
  if('IntersectionObserver' in window){const observer=new IntersectionObserver(entries=>{if(entries.some(e=>e.isIntersecting)){observer.disconnect();initialize();}},{rootMargin:'250px'});observer.observe(section);}else initialize();
})();
