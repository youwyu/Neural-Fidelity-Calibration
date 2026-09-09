// Experiment videos are click-to-play, with at most one active decoder.
(() => {
  const videos=Array.from(document.querySelectorAll('video'));
  const pauseAll=()=>videos.forEach(video=>video.pause());
  videos.forEach(video=>{
    video.addEventListener('play',()=>videos.forEach(other=>{if(other!==video)other.pause();}));
  });
  if('IntersectionObserver' in window) {
    const observer=new IntersectionObserver(entries=>{
      entries.forEach(({target,isIntersecting,intersectionRatio})=>{
        if(!isIntersecting||intersectionRatio<.2)target.pause();
      });
    },{threshold:[0,.2]});
    videos.forEach(video=>observer.observe(video));
  }
  document.addEventListener('visibilitychange',()=>{if(document.hidden)pauseAll();});
  document.addEventListener('teaser-view-change',event=>{if(event.detail.active)videos.forEach(video=>{if(!video.hasAttribute('data-teaser-real'))video.pause();});});
})();
