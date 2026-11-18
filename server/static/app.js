const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let lastData=null,map=null,markers=null,zones=null,lastMapSignature='',loading=false;
async function load(){
 if(loading)return;loading=true;
 try{
  const r=await fetch('/api/dashboard',{cache:'no-store'});if(!r.ok){document.querySelector('#server-status').textContent='PC server returned an error ('+r.status+'). Restart the launcher.';return}const d=await r.json();lastData=d;document.querySelector('#server-status').textContent='Connected to PC server.';
  document.querySelector('#count').textContent=d.devices.length;
  document.querySelector('#online').textContent=d.devices.filter(x=>x.connected).length;
  document.querySelector('#zonecount').textContent=d.zones.length;
  document.querySelector('#devices').innerHTML=d.devices.length?d.devices.map(x=>'<div class="device"><div><div class="devname">'+esc(x.name)+'</div><div class="muted">'+(x.updated?'Updated '+ago(x.updated)+' · ±'+Math.round(x.accuracy||0)+' m · Battery '+(x.battery??'—')+'%':'Waiting for first location')+'</div><button onclick="showDeviceHistory(\''+x.id+'\',\''+esc(x.name)+'\')">View location history →</button></div><span class="badge '+(x.connected?'':'off')+'">'+(x.connected?'Online':'Offline')+'</span></div>').join(''):'<div class="empty">No paired devices yet.</div>';
  document.querySelector('#zones').innerHTML=d.zones.length?d.zones.map(z=>'<div class="zone"><span><b>'+esc(z.name)+'</b><div class="muted">'+z.radius+' m radius</div></span><button onclick="delzone('+z.id+')">Remove</button></div>').join(''):'<div class="empty">No safe zones added.</div>';
  const ae=document.querySelector('#alerts');if(ae)ae.innerHTML=d.alerts.length?d.alerts.map(a=>'<div class="zone"><span><b>'+esc(a.device_name)+'</b> '+esc(a.event)+' <b>'+esc(a.zone_name)+'</b><div class="muted">'+new Date(a.created*1000).toLocaleString()+'</div></span></div>').join(''):'<div class="empty">No safe-zone arrivals or departures recorded.</div>';
  if(map)renderMap(d);
 }catch(e){console.error(e);document.querySelector('#server-status').textContent='PC server is not reachable. Start the launcher on the PC and leave its window open.'}finally{loading=false}
}
function ago(t){if(!t)return'No location shared yet';const s=Math.max(0,Date.now()/1000-t);return s<60?Math.floor(s)+'s ago':s<3600?Math.floor(s/60)+'m ago':s<86400?Math.floor(s/3600)+'h ago':Math.floor(s/86400)+'d ago'}
function renderMap(d){
 markers.clearLayers();zones.clearLayers();const pts=[];
 d.devices.filter(x=>x.lat!=null).forEach(x=>{L.marker([x.lat,x.lon]).addTo(markers).bindPopup('<b>'+esc(x.name)+'</b><br>'+ago(x.updated)+'<br>Accuracy ±'+Math.round(x.accuracy||0)+' m<br>Battery '+(x.battery??'—')+'%');pts.push([x.lat,x.lon])});
 const sig=pts.map(p=>p.join(',')).sort().join(';');if(pts.length&&sig!==lastMapSignature){map.fitBounds(pts,{padding:[35,35],maxZoom:14});lastMapSignature=sig}
 d.zones.forEach(z=>L.circle([z.lat,z.lon],{radius:z.radius,color:'#FFC857',fillOpacity:.12}).addTo(zones).bindPopup(esc(z.name)));
}
function loadStylesheet(){
 return new Promise((resolve,reject)=>{if(document.querySelector('#leafletcss')){resolve();return}const l=document.createElement('link');l.id='leafletcss';l.rel='stylesheet';l.href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';l.onload=resolve;l.onerror=reject;document.head.appendChild(l)});
}
function loadLeaflet(){
 return new Promise((resolve,reject)=>{if(window.L){resolve();return}const s=document.createElement('script');s.src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';s.onload=resolve;s.onerror=reject;document.head.appendChild(s)});
}
document.querySelector('#loadmap').onclick=async()=>{
 const b=document.querySelector('#loadmap'),status=document.querySelector('#mapstatus'),el=document.querySelector('#map');b.disabled=true;status.textContent='Loading map…';el.hidden=false;
 try{await loadStylesheet();await loadLeaflet();map=L.map('map').setView([20,0],2);L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{attribution:'&copy; OpenStreetMap contributors',maxZoom:19}).addTo(map);markers=L.layerGroup().addTo(map);zones=L.layerGroup().addTo(map);map.on('click',e=>{document.querySelector('#zoneform').elements.latitude.value=e.latlng.lat.toFixed(6);document.querySelector('#zoneform').elements.longitude.value=e.latlng.lng.toFixed(6)});status.textContent='Map loaded.';b.hidden=true;if(lastData)renderMap(lastData);setTimeout(()=>map.invalidateSize(),100)}catch(e){el.hidden=true;status.textContent='Map could not load. Check the internet connection and try again.';b.disabled=false}
};
document.querySelector('#adddevice').onclick=()=>{document.querySelector('#pairinstructions').hidden=false};
document.querySelector('#getcode').onclick=async()=>{const b=document.querySelector('#getcode'),m=document.querySelector('#pairmessage');b.disabled=true;m.textContent='Getting a code…';try{const r=await fetch('/api/pairing-codes',{method:'POST'}),d=await r.json();if(!r.ok)throw new Error(d.error||'Request failed');document.querySelector('#paircode').textContent=d.code;document.querySelector('#pairresult').hidden=false;m.textContent='Code ready. It expires in 10 minutes.'}catch(e){m.textContent='Could not get a code. Check the connection and try again.'}finally{b.disabled=false}};
document.querySelector('#copycode').onclick=async()=>{const t=document.querySelector('#paircode').textContent;try{await navigator.clipboard.writeText(t)}catch(e){const range=document.createRange();range.selectNodeContents(document.querySelector('#paircode'));const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range)}};
document.querySelector('#addzone').onclick=()=>document.querySelector('#zonedialog').showModal();
document.querySelectorAll('[data-close]').forEach(x=>x.onclick=()=>x.closest('dialog').close());
document.querySelector('#zoneform').onsubmit=async e=>{e.preventDefault();const o=Object.fromEntries(new FormData(e.target));o.latitude=+o.latitude;o.longitude=+o.longitude;o.radius_m=+o.radius_m;const r=await fetch('/api/zones',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(o)});if(!r.ok){alert('Could not save zone');return}e.target.closest('dialog').close();e.target.reset();load()};
window.delzone=async id=>{if(confirm('Remove this safe zone?')){await fetch('/api/zones/'+id,{method:'DELETE'});load()}};
window.showDeviceHistory=async(id,name)=>{const r=await fetch('/api/devices/'+id+'/history?limit=100'),d=await r.json();document.querySelector('#historytitle').textContent=name+' · location history';document.querySelector('#historylist').innerHTML=d.points.length?d.points.map(p=>'<div class="historyrow"><span>'+new Date(p.created*1000).toLocaleString()+'</span><span>±'+Math.round(p.accuracy||0)+' m · '+(p.battery??'—')+'%</span><a target="_blank" href="https://www.openstreetmap.org/?mlat='+p.lat+'&mlon='+p.lon+'#map=16/'+p.lat+'/'+p.lon+'">Open map ↗</a></div>').join(''):'<div class="empty">No location history available.</div>';const b=document.querySelector('#historybox');b.hidden=false;b.scrollIntoView({behavior:'smooth'})};
document.querySelector('#closehistory').onclick=()=>document.querySelector('#historybox').hidden=true;
load();setInterval(load,60000);