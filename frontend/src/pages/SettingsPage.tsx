import { PageHeader } from "@/components/layout/PageHeader";
import {
	Card,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "@/components/ui/card";
import { ModelSelector, ProviderKeyFields } from "@/features/settings";

export function SettingsPage() {
	return (
		<div className="space-y-6">
			<PageHeader
				title="Settings"
				description="Choose a theme and configure the model and provider keys."
			/>

			<div className="grid gap-6 max-w-2xl">
				<Card>
					<CardHeader>
						<CardTitle className="text-base font-semibold">
							AI Model Configuration
						</CardTitle>
						<CardDescription>
							Select the model for analysis queries in the AI Assistant.
						</CardDescription>
					</CardHeader>
					<CardContent className="space-y-6">
						<ModelSelector />
					</CardContent>
				</Card>

				<Card>
					<CardHeader>
						<CardTitle className="text-base font-semibold">
							Provider API Keys
						</CardTitle>
						<CardDescription>
							Configure API keys for cloud providers. Keys are held in React
							memory only.
						</CardDescription>
					</CardHeader>
					<CardContent>
						<ProviderKeyFields />
					</CardContent>
				</Card>
			</div>
		</div>
	);
}
