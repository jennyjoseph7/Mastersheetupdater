import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function proxy(request: NextRequest) {
  const token = request.cookies.get('gryd_token')?.value;
  const expiry = parseInt(request.cookies.get('gryd_expiry')?.value || '0');
  const { pathname } = request.nextUrl;
  const now = Math.floor(Date.now() / 1000);
  
  const publicPaths = ['/login'];
  if (pathname.startsWith('/api/') || pathname === '/api') {
    return NextResponse.next();
  }
  if (publicPaths.some(p => pathname === p || pathname.startsWith(p + '/'))) {
    return addSecurityHeaders(NextResponse.next());
  }
  
  if (pathname.startsWith('/_next/') || pathname.startsWith('/images/') || 
      pathname.startsWith('/fonts/') || pathname === '/favicon.ico' ||
      pathname === '/jejo-config.js') {
    return addSecurityHeaders(NextResponse.next());
  }
  
  
  if (!token || !expiry || expiry <= now) {
    const loginUrl = new URL('/login', request.url);
    loginUrl.searchParams.set('redirect', pathname);
    return addSecurityHeaders(NextResponse.redirect(loginUrl));
  }
  
  return addSecurityHeaders(NextResponse.next());
}

function addSecurityHeaders(res: NextResponse): NextResponse {
  res.headers.set('X-Content-Type-Options', 'nosniff');
  res.headers.set('X-Frame-Options', 'DENY');
  res.headers.set('Content-Security-Policy', 
    "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; font-src 'self' https://frontend-cdn.perplexity.ai; img-src 'self' data:; connect-src 'self' https://autongagetools.jennyjoseph-k.workers.dev https://autobot-webapp-dev.gryd.in; form-action 'self'; base-uri 'self'; object-src 'none';"
  );
  return res;
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
