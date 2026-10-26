import { Route, Routes } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { AssistantPage } from "@/pages/AssistantPage";
import { HomePage } from "@/pages/HomePage";
import { NotFoundPage } from "@/pages/NotFoundPage";
import { SettingsPage } from "@/pages/SettingsPage";

function App() {
	return (
		<Routes>
			<Route element={<AppShell />}>
				<Route index element={<HomePage />} />
				<Route path="assistant" element={<AssistantPage />} />
				<Route path="settings" element={<SettingsPage />} />
				<Route path="*" element={<NotFoundPage />} />
			</Route>
		</Routes>
	);
}

export default App;
