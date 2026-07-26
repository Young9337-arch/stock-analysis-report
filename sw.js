const CACHE='stock-report-shell-v4';
const SHELL=['./','./index.html','./daily-market-report.html','./vendor/echarts.min.js','./vendor/company-inspur-representative.jpg','./support-alipay-qr.jpg'];
self.addEventListener('install',event=>event.waitUntil(caches.open(CACHE).then(cache=>Promise.allSettled(SHELL.map(url=>cache.add(url)))).then(()=>self.skipWaiting())));
self.addEventListener('activate',event=>event.waitUntil(caches.keys().then(keys=>Promise.all(keys.filter(key=>key!==CACHE).map(key=>caches.delete(key)))).then(()=>self.clients.claim())));
self.addEventListener('fetch',event=>{
  const request=event.request,url=new URL(request.url);
  if(request.method!=='GET'||url.origin!==self.location.origin)return;
  if(request.mode==='navigate'){
    const normalized=new Request(url.origin+url.pathname,{method:'GET'});
    event.respondWith(fetch(request).then(response=>{const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(normalized,copy));return response}).catch(()=>caches.match(normalized).then(hit=>hit||caches.match('./daily-market-report.html'))));
    return;
  }
  event.respondWith(caches.match(request).then(hit=>hit||fetch(request).then(response=>{if(response.ok){const copy=response.clone();caches.open(CACHE).then(cache=>cache.put(request,copy))}return response})));
});
