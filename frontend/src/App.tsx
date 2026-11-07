import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/layout/AppShell'
import { ToastProvider } from './components/ui/Toast'
import { AdvisorPage } from './pages/Advisor'
import { HomePage } from './pages/Home'
import { DocumentsPage } from './pages/Documents'

export default function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="advisor" element={<AdvisorPage />} />
          <Route path="admin/documents" element={<DocumentsPage />} />
          <Route element={<AppShell />}>
            <Route index element={<HomePage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}
