'use client';
import Link from 'next/link';
import { useTheme } from './ThemeProvider';

const PREFIX = process.env.NODE_ENV === 'development' ? '' : '/Mastersheetupdater';

export default function BrandLogo({ href = '/' }: { href?: string }) {
  const { theme } = useTheme();
  return (
    <Link href={href} className="brand-mark" aria-label="Go to home">
      <img src={theme === 'dark' ? `${PREFIX}/images/AN Dark.png` : `${PREFIX}/images/AN.png`} alt="AutoNage" />
    </Link>
  );
}
