import { Navigate, Route, Routes } from "react-router-dom";
import { Login } from "@/components/Login";
import { DashboardLayout } from "@/components/layout/DashboardLayout";
import { useAuth } from "@/context/AuthContext";
import { AgentsPage } from "@/pages/AgentsPage";
import { CalendarPage } from "@/pages/CalendarPage";
import { ChatPage } from "@/pages/ChatPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { FilesPage } from "@/pages/FilesPage";
import { LinkedInPage } from "@/pages/LinkedInPage";
import { MailPage } from "@/pages/MailPage";
import { MeetingsPage } from "@/pages/MeetingsPage";
import { OnboardingPage } from "@/pages/Onboarding";
import { TasksPage } from "@/pages/TasksPage";
import { YouTubePage } from "@/pages/YouTubePage";

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
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="aufgaben" element={<TasksPage />} />
        <Route path="kalender" element={<CalendarPage />} />
        <Route path="mail" element={<MailPage />} />
        <Route path="dateien" element={<FilesPage />} />
        <Route path="meetings" element={<MeetingsPage />} />
        <Route path="agenten" element={<AgentsPage />} />
        <Route path="linkedin" element={<LinkedInPage />} />
        <Route path="youtube" element={<YouTubePage />} />
        <Route path="onboarding" element={<OnboardingPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default App;
