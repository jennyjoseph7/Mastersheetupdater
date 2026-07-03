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

function syncBrandLogo(theme: 'dark' | 'light'): void {
  const img = document.querySelector('.brand-mark img') as HTMLImageElement | null;
  if (img) {
    img.src = theme === 'dark' ? '/images/AN Dark.png' : '/images/AN.png';
  }
}
