import { AppShell } from "@/components/app-shell";
import { AgentImageWorkbench } from "@/components/agent-image-workbench";

export default function AgentPage() {
  return (
    <AppShell>
      <AgentImageWorkbench variant="compact" />
    </AppShell>
  );
}
