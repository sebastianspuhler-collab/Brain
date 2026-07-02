import { Navigate, Route, Routes } from "react-router-dom";
import { Login } from "@/components/Login";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { CalendarPage } from "@/pages/CalendarPage";
import { ChatPage } from "@/pages/ChatPage";
import { FilesPage } from "@/pages/FilesPage";
import { LinkedInPage } from "@/pages/LinkedInPage";
import { MailPage } from "@/pages/MailPage";
import { OnboardingPage } from "@/pages/Onboarding";
import { TasksPage } from "@/pages/TasksPage";

function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-muted-foreground">Lädt...</div>;
  }
  if (!user) return <Login />;

  return (
    <Routes>
      <Route element={<DashboardLayout />}>
        <Route index element={<ChatPage />} />
        <Route path="aufgaben" element={<TasksPage />} />
        <Route path="kalender" element={<CalendarPage />} />
        <Route path="mail" element={<MailPage />} />
        <Route path="dateien" element={<FilesPage />} />
        <Route path="linkedin" element={<LinkedInPage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
