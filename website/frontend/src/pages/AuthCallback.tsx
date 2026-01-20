import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/context/AuthContext';
import { Loader } from '@/components/ui/loader';

export function AuthCallback() {
  const navigate = useNavigate();
  const { refetch } = useAuth();

  useEffect(() => {
    const handleCallback = async () => {
      await refetch();
      navigate('/', { replace: true });
    };
    handleCallback();
  }, [refetch, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <Loader variant="dots" size="lg" />
        <p className="mt-4 text-muted-foreground">Signing you in...</p>
      </div>
    </div>
  );
}
