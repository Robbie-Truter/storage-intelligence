import { QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import "./index.css";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { queryClient } from "@/providers/query-client";
import { SettingsProvider } from "@/providers/SettingsProvider";
import { ThemeProvider } from "@/providers/ThemeProvider";
import App from "./App.tsx";

const rootElement = document.getElementById("root");

if (!rootElement) {
	throw new Error("Root element not found");
}

createRoot(rootElement).render(
	<StrictMode>
		<QueryClientProvider client={queryClient}>
			<ThemeProvider>
				<SettingsProvider>
					<BrowserRouter>
						<App />
						<ReactQueryDevtools initialIsOpen={false} />
					</BrowserRouter>
				</SettingsProvider>
			</ThemeProvider>
		</QueryClientProvider>
	</StrictMode>,
);
