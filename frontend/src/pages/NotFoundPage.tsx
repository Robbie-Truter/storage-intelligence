import { Link } from "react-router-dom";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button } from "@/components/ui/button";

export function NotFoundPage() {
	return (
		<div className="space-y-4">
			<PageHeader
				title="Page not found"
				description="The page you are looking for does not exist."
			/>
			<Button asChild variant="outline" className="w-fit">
				<Link to="/">Back to Home</Link>
			</Button>
		</div>
	);
}
