import { AnimatePresence, motion, type Variants } from "framer-motion";
import {
	ArrowLeftFromLine,
	ArrowRightFromLine,
	Home,
	Settings,
	Sparkles,
} from "lucide-react";
import { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { ReadinessBanner } from "@/features/health/ReadinessBanner";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
	{ to: "/", label: "Home", icon: Home, end: true },
	{ to: "/assistant", label: "Assistant", icon: Sparkles, end: false },
	{ to: "/settings", label: "Settings", icon: Settings, end: false },
] as const;

const sidebarVariants: Variants = {
	open: {
		width: 256,
		transition: {
			type: "tween",
			stiffness: 300,
			damping: 30,
		},
	},
	closed: {
		width: 64,
		transition: {
			type: "tween",
			stiffness: 300,
			damping: 30,
		},
	},
};

const fadeVariants = {
	open: {
		opacity: 1,
		x: 0,
		transition: { duration: 0.15 },
	},
	closed: {
		opacity: 0,
		x: -10,
		transition: {
			duration: 0.1,
		},
	},
};

export function AppShell() {
	const [isCollapsed, setIsCollapsed] = useState(false);

	return (
		<div
			className={cn(
				"min-h-svh bg-background text-foreground md:grid transition-all duration-300 ease-in-out",
				isCollapsed ? "md:grid-cols-[4rem_1fr]" : "md:grid-cols-[16rem_1fr]",
			)}
		>
			<motion.aside
				initial="open"
				animate={isCollapsed ? "closed" : "open"}
				variants={sidebarVariants}
				className={cn("border-b bg-card/40 md:border-r md:border-b-0 relative")}
			>
				{/* Button perfectly aligned hanging on the outside border edge */}
				<button
					type="button"
					onClick={() => setIsCollapsed(!isCollapsed)}
					className="absolute top-6 -right-3 z-50 flex size-6 items-center justify-center rounded-full border bg-background text-muted-foreground shadow-sm hover:bg-accent hover:text-foreground active:scale-95 transition-transform"
				>
					{isCollapsed ? (
						<ArrowRightFromLine size={12} />
					) : (
						<ArrowLeftFromLine size={12} />
					)}
				</button>

				<div className="px-4 py-5 h-19 flex items-center">
					<div
						className={cn(
							"flex gap-3 items-center w-full layout-container relative",
							isCollapsed ? "justify-center" : "justify-start",
						)}
					>
						<motion.img
							animate={{
								width: isCollapsed ? 28 : 36,
								height: isCollapsed ? 28 : 36,
								rotate: isCollapsed ? 0 : 360,
							}}
							transition={{
								duration: 0.4,
							}}
							src="/Storage Intelligence App Favicon.svg"
							alt="App logo"
							className={cn(
								"rounded-full shadow border border-black/10 shrink-0 transition-all duration-200",
							)}
						/>

						<AnimatePresence mode="popLayout" initial={false}>
							{!isCollapsed && (
								<motion.div
									key="brand-text"
									variants={fadeVariants}
									initial="closed"
									exit="closed"
									className="-space-y-1.25 min-w-0"
								>
									<p className="font-semibold text-lg tracking-tight truncate">
										Storage Intelligence
									</p>
									<p className="text-muted-foreground text-xs truncate">
										Local-first disk insight
									</p>
								</motion.div>
							)}
						</AnimatePresence>
					</div>
				</div>

				<nav aria-label="Primary" className="flex gap-1 px-3 pb-4 md:flex-col">
					{NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
						<NavLink key={to} to={to} end={end} className="block">
							{({ isActive }) => (
								<motion.div
									whileHover={{ scale: 1.01 }}
									whileTap={{ scale: 0.98 }}
									transition={{ duration: 0.15 }}
									className={cn(
										"group flex items-center rounded-md px-3 py-2 font-medium text-sm h-9 relative overflow-hidden",
										isCollapsed
											? "justify-center gap-0"
											: "justify-start gap-3",
										isActive
											? "bg-accent text-accent-foreground active"
											: "text-muted-foreground hover:bg-accent/50 hover:text-foreground",
									)}
								>
									<motion.span
										animate={{
											scale: isActive ? 1.05 : 1,
										}}
										transition={{ duration: 0.2 }}
										className="flex shrink-0 z-10"
									>
										<Icon
											aria-hidden="true"
											className={cn(
												"size-4 transition-colors duration-200",
												isActive && "text-indigo-600",
											)}
										/>
									</motion.span>

									<AnimatePresence mode="popLayout" initial={false}>
										{!isCollapsed && (
											<motion.span
												key={label}
												variants={fadeVariants}
												initial="closed"
												animate="open"
												exit="closed"
												className="whitespace-nowrap truncate"
											>
												{label}
											</motion.span>
										)}
									</AnimatePresence>
								</motion.div>
							)}
						</NavLink>
					))}
				</nav>
			</motion.aside>

			<main className="flex min-w-0 flex-col gap-6 p-4 sm:p-6">
				<ReadinessBanner />
				<Outlet />
			</main>
		</div>
	);
}
