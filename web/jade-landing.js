'use strict';
document.getElementById('year').textContent=String(new Date().getFullYear());
const menu=document.getElementById('menuToggle');
const nav=document.getElementById('nav');
menu.addEventListener('click',()=>{
  const open=nav.classList.toggle('open');
  menu.setAttribute('aria-expanded',String(open));
});
nav.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{
  nav.classList.remove('open');
  menu.setAttribute('aria-expanded','false');
}));
