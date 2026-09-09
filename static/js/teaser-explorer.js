// Only this small loader runs initially; the renderer loads after a click.
(() => {
  const preview=document.querySelector('.teaser-preview');
  const host=document.querySelector('.teaser-explorer');
  const toolbar=document.querySelector('.viewer-toolbar');
  const close=toolbar.querySelector('[data-close]');
  const status=host.querySelector('.viewer-status');
  const bundleUrl=new URL('./teaser-viewer.bundle.js',document.currentScript.src).href;
  let viewer, pending, bundlePending, active=false;
  function loadViewer() {
    if(window.NFCTeaserViewer)return Promise.resolve(window.NFCTeaserViewer);
    if(!bundlePending) {
      bundlePending=new Promise((resolve,reject)=>{
        const script=document.createElement('script');
        script.src=bundleUrl;script.async=true;
        script.onload=()=>{
          if(window.NFCTeaserViewer)resolve(window.NFCTeaserViewer);
          else {bundlePending=null;script.remove();reject(new Error('Viewer bundle did not initialize.'));}
        };
        script.onerror=()=>{bundlePending=null;script.remove();reject(new Error('Could not load the 3D viewer file.'));};
        document.head.append(script);
      });
    }
    return bundlePending;
  }
  preview.disabled=false;
  preview.querySelector('.teaser-preview-action').hidden=false;
  function setActive(value) {
    active=value;host.hidden=!value;preview.hidden=value;toolbar.hidden=!value;
    document.dispatchEvent(new CustomEvent('teaser-view-change',{detail:{active:value}}));
    if(viewer)viewer.setActive(value);
  }
  preview.addEventListener('click',async()=>{
    setActive(true);close.focus({preventScroll:true});
    if(viewer)return;
    status.hidden=false;status.textContent='Loading 3D view…';
    try {
      pending=pending||loadViewer().then(module=>module.createViewer(host));
      viewer=await pending;status.hidden=true;viewer.setActive(active);
    } catch(error) {
      pending=null;
      status.textContent=/WebGL|context/i.test(error.message)
        ? 'The browser could not start 3D graphics. Check graphics acceleration, then reopen the page.'
        : 'The 3D view could not load. Close and refresh the page to try again.';
      console.warn('NFC 3D view:',error);
    }
  });
  close.addEventListener('click',()=>{setActive(false);preview.focus({preventScroll:true});});
  document.querySelectorAll('video:not([data-teaser-real])').forEach(video=>{
    video.addEventListener('play',()=>{if(viewer)viewer.pause();});
  });
  host.addEventListener('viewer-error',()=>{
    if(viewer)viewer.setActive(false);
    status.hidden=false;status.textContent='The 3D view was interrupted. Close to return to the preview.';
  });
})();
