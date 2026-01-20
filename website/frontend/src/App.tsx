import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from '@/context/AuthContext';
import { ThemeProvider } from '@/context/ThemeContext';
import { Layout } from '@/components/Layout';
import { ChatPage } from '@/pages/ChatPage';
import { DocumentsPage } from '@/pages/DocumentsPage';
import { AnalyticsPage } from '@/pages/AnalyticsPage';
import { AuthCallback } from '@/pages/AuthCallback';

export default function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
        <AuthProvider>
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/chat/:conversationId?" element={<ChatPage />} />
            <Route element={<Layout />}>
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/analytics" element={<AnalyticsPage />} />
            </Route>
            <Route path="/auth/callback" element={<AuthCallback />} />
          </Routes>
        </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  );
}
