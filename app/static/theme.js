// Theme toggler using localStorage
;(function(){
  const toggle = document.getElementById('themeToggle');
  const root = document.documentElement;
  function applyTheme(t){
    if(t==='dark'){
      document.documentElement.setAttribute('data-theme','dark');
      document.body.classList.add('bg-dark','text-light');
    } else {
      document.documentElement.setAttribute('data-theme','light');
      document.body.classList.remove('bg-dark','text-light');
    }
  }
  const stored = localStorage.getItem('theme') || 'light';
  applyTheme(stored);
  if(toggle){ toggle.checked = stored==='dark'; }
  if(toggle){
    toggle.addEventListener('change', function(e){
      const t = e.target.checked ? 'dark' : 'light';
      localStorage.setItem('theme', t);
      applyTheme(t);
    });
  }
})();
