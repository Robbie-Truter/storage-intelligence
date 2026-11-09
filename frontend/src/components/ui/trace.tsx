"use client";

import * as Collapsible from "@radix-ui/react-collapsible";
import { ChevronRightIcon } from "lucide-react";
import type * as React from "react";

import { cn } from "@/lib/utils";

function Trace({ className, ...props }: React.ComponentProps<"div">) {
	return (
		<div
			data-slot="trace"
			className={cn("flex w-full min-w-0 flex-col space-y-1", className)}
			{...props}
		/>
	);
}

function TraceLine({
	className,
	status,
	...props
}: React.ComponentProps<"span"> & {
	status?: "running" | "error" | "pending";
}) {
	return (
		<span
			data-slot="trace-line"
			data-status={status}
			className={cn(
				"flex w-fit max-w-full min-w-0 items-center text-muted-foreground transition-colors",
				"in-[a,button]:cursor-pointer",
				"in-[a:hover,button:hover]:text-foreground",
				"data-[status=error]:text-destructive",
				"data-[status=pending]:opacity-60",
				"data-[status=running]:*:data-[slot=trace-title]:animate-pulse",
				className,
			)}
			{...props}
		/>
	);
}

function TraceIcon({ className, ...props }: React.ComponentProps<"span">) {
	return (
		<span
			data-slot="trace-icon"
			aria-hidden="true"
			className={cn(
				"flex shrink-0 items-center justify-center [&_svg]:pointer-events-none",
				className,
			)}
			{...props}
		/>
	);
}

function TraceTitle({ className, ...props }: React.ComponentProps<"span">) {
	return (
		<span
			data-slot="trace-title"
			className={cn("min-w-0 truncate", className)}
			{...props}
		/>
	);
}

function TraceDescription({
	className,
	...props
}: React.ComponentProps<"span">) {
	return (
		<span
			data-slot="trace-description"
			className={cn(
				"shrink-0 text-muted-foreground/70 tabular-nums",
				className,
			)}
			{...props}
		/>
	);
}

function TraceCollapsible({
	className,
	...props
}: React.ComponentProps<typeof Collapsible.Root>) {
	return (
		<Collapsible.Root
			data-slot="trace-collapsible"
			className={cn("flex w-full min-w-0 flex-col", className)}
			{...props}
		/>
	);
}

function TraceCollapsibleTrigger({
	className,
	children,
	...props
}: React.ComponentProps<typeof Collapsible.Trigger>) {
	return (
		<Collapsible.Trigger
			data-slot="trace-collapsible-trigger"
			className={cn(
				"group/trace-collapsible-trigger flex w-fit max-w-full min-w-0 cursor-pointer items-center text-left text-muted-foreground transition-colors outline-none hover:text-foreground",
				className,
			)}
			{...props}
		>
			{children}

			<TraceIcon className="transition-transform group-aria-expanded/trace-collapsible-trigger:rotate-90">
				<ChevronRightIcon />
			</TraceIcon>
		</Collapsible.Trigger>
	);
}

function TraceCollapsibleContent({
	className,
	children,
	...props
}: React.ComponentProps<typeof Collapsible.Content>) {
	return (
		<Collapsible.Content
			data-slot="trace-collapsible-content"
			className="min-w-0 overflow-hidden data-[state=open]:animate-accordion-down data-[state=closed]:animate-accordion-up"
			{...props}
		>
			<div
				data-slot="trace-collapsible-content-inner"
				className={cn(
					"min-w-0 wrap-break-word text-muted-foreground",
					className,
				)}
			>
				{children}
			</div>
		</Collapsible.Content>
	);
}

export {
	Trace,
	TraceCollapsible,
	TraceCollapsibleContent,
	TraceCollapsibleTrigger,
	TraceDescription,
	TraceIcon,
	TraceLine,
	TraceTitle,
};
