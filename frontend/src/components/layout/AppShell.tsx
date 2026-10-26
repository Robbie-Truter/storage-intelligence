import { Home, Settings, Sparkles } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { ReadinessBanner } from "@/features/health/ReadinessBanner";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
	{ to: "/", label: "Home", icon: Home, end: true },
	{ to: "/assistant", label: "Assistant", icon: Sparkles, end: false },
	{ to: "/settings", label: "Settings", icon: Settings, end: false },
] as const;

export function AppShell() {
	return (
		<div className="min-h-svh bg-background text-foreground md:grid md:grid-cols-[16rem_1fr]">
			<aside className="border-b bg-card/40 md:border-r md:border-b-0">
				<div className="px-6 py-5">
					<p className="font-semibold text-lg tracking-tight">
						Storage Intelligence
					</p>
					<p className="text-muted-foreground text-xs">
						Local-first disk insight
					</p>
				</div>
				<nav aria-label="Primary" className="flex gap-1 px-3 pb-4 md:flex-col">
					{NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
						<NavLink
							key={to}
							to={to}
							end={end}
							className={({ isActive }) =>
								cn(
									"flex items-center gap-2 rounded-md px-3 py-2 font-medium text-sm transition-colors",
									isActive
										? "bg-accent text-accent-foreground"
										: "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
								)
							}
						>
							<Icon aria-hidden="true" className="size-4" />
							{label}
						</NavLink>
					))}
				</nav>
			</aside>

			<main className="flex min-w-0 flex-col gap-6 p-4 sm:p-6">
				<ReadinessBanner />
				<Outlet />
			</main>
		</div>
	);
}
