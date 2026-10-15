(function(){
var d=document,reduce=matchMedia('(prefers-reduced-motion: reduce)').matches;
var nav=d.querySelector('nav'),bar=d.getElementById('bar'),tk=0;
function onScroll(){var h=d.documentElement.scrollHeight-innerHeight;if(bar)bar.style.transform='scaleX('+(h>0?scrollY/h:0)+')';if(nav)nav.classList.toggle('stuck',scrollY>8)}
addEventListener('scroll',function(){if(!tk)tk=requestAnimationFrame(function(){tk=0;onScroll()})},{passive:true});onScroll();
/* phone menu toggle */
var navin=d.querySelector('nav .navin');
if(navin&&nav){var tb=d.createElement('button');tb.className='navtoggle';tb.type='button';tb.setAttribute('aria-label','Menu');tb.setAttribute('aria-expanded','false');tb.textContent='\u2630';
 tb.onclick=function(){var o=nav.classList.toggle('open');tb.setAttribute('aria-expanded',o);tb.textContent=o?'\u2715':'\u2630'};
 navin.appendChild(tb);
 [].forEach.call(nav.querySelectorAll('.links a'),function(a){a.addEventListener('click',function(){nav.classList.remove('open')})})}
/* mark current page in the menu */
var here=(location.pathname.split('/').pop()||'index.html');
[].forEach.call(d.querySelectorAll('nav .links a'),function(a){if(a.getAttribute('href')===here)a.classList.add('on')});
/* scroll reveal for cards and blocks */
if(!reduce&&'IntersectionObserver' in window){
 var els=[].slice.call(d.querySelectorAll('main .card,main .cap,main .kpi-card,main .panel,main .job,main .step,main .item,main .skill,main .notice,main .contact,main .table-wrap,main .visual,main .dq-panel,main .result,main .box,main .finding'));
 els=els.filter(function(e){return e.getBoundingClientRect().top>innerHeight*0.95});
 if(els.length){
  d.documentElement.classList.add('js');
  els.forEach(function(e){var sib=[].slice.call(e.parentNode.children).indexOf(e);e.classList.add('rv');e.style.setProperty('--d',(sib%4*80)+'ms')});
  var io=new IntersectionObserver(function(es){es.forEach(function(x){if(x.isIntersecting){x.target.classList.add('in');io.unobserve(x.target)}})},{threshold:.08,rootMargin:'0px 0px -5% 0px'});
  els.forEach(function(e){io.observe(e)});
 }
}
/* cursor light */
if(!reduce&&matchMedia('(hover:hover)').matches){
 var spot=d.getElementById('spot'),sx=0,sy=0,sr=0;
 if(spot)addEventListener('pointermove',function(e){sx=e.clientX;sy=e.clientY;if(!sr)sr=requestAnimationFrame(function(){sr=0;spot.style.transform='translate3d('+sx+'px,'+sy+'px,0)'})},{passive:true});
}
})();
