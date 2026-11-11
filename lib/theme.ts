export function getStoredTheme(): 'dark' | 'light' {
  if (typeof window === 'undefined') return 'dark';
  return (localStorage.getItem('jejo-theme') as 'dark' | 'light') || 'dark';
}

export function applyTheme(theme: 'dark' | 'light'): void {
  if (typeof document === 'undefined') return;
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('jejo-theme', theme);
  syncBrandLogo(theme);
}

export function toggleTheme(): void {
  const current = getStoredTheme();
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
}

const PREFIX = process.env.NODE_ENV === 'development' ? '' : '/Mastersheetupdater';

function syncBrandLogo(theme: 'dark' | 'light'): void {
  const imgs = document.querySelectorAll('.brand-mark img');
  imgs.forEach(el => {
    const img = el as HTMLImageElement;
    if (img.classList.contains('login-logo')) return;
    img.src = theme === 'dark' ? `${PREFIX}/images/AN Dark.png` : `${PREFIX}/images/AN.png`;
  });
}
