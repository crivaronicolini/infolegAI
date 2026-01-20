import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { useTheme } from '@/context/ThemeContext';
import { Button } from '@/components/ui/button';
import { getGoogleAuthUrl, debugLogin, checkDebugMode } from '@/lib/api';

export function Layout() {
  const { user, loading, logout, refetch } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const location = useLocation();
  const [debugMode, setDebugMode] = useState(false);

  useEffect(() => {
    checkDebugMode().then(setDebugMode);
  }, []);

  const navItems = [
    { path: '/', label: 'Chat' },
    { path: '/documents', label: 'Documents' },
    ...(user?.is_superuser ? [{ path: '/analytics', label: 'Analytics' }] : []),
  ];

  const handleGoogleSignIn = async () => {
    try {
      const authUrl = await getGoogleAuthUrl();
      window.location.href = authUrl;
    } catch (error) {
      console.error('Failed to get auth URL:', error);
    }
  };

  const handleDebugLogin = async () => {
    try {
      await debugLogin();
      await refetch();
    } catch (error) {
      console.error('Debug login failed:', error);
    }
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 h-14 flex items-center justify-between">
          <div className="flex items-center gap-6">
            <Link to="/" className="font-semibold text-lg text-primary">
              InfolegAI
            </Link>
            <nav className="flex items-center gap-4">
              {navItems.map((item) => (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`text-sm transition-colors ${location.pathname === item.path
                      ? 'text-foreground font-medium'
                      : 'text-muted-foreground hover:text-foreground'
                    }`}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>

          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={toggleTheme}
              className="w-9 h-9 p-0"
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </Button>

            {loading ? (
              <span className="text-sm text-muted-foreground">Loading...</span>
            ) : user ? (
              <div className="flex items-center gap-3">
                <span className="text-sm text-muted-foreground">{user.email}</span>
                <Button variant="outline" size="sm" onClick={logout}>
                  Logout
                </Button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                {debugMode && (
                  <Button variant="outline" size="sm" onClick={handleDebugLogin}>
                    Admin Login
                  </Button>
                )}
                <Button size="sm" onClick={handleGoogleSignIn}>
                  Sign in with Google
                </Button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  );
}
