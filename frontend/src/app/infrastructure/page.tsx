import Link from "next/link";
import { UnavailableState } from "@/components/ui/States";

export default function InfrastructurePage() {
  return (
    <UnavailableState reason="No dedicated infrastructure-metrics endpoint exists (CPU/memory/disk/queue-depth of the running services). The closest real equivalent is the Integrations page, which reports live reachability and response time for each external dependency (database, FFmpeg, YouTube API, TTS).">
      <Link href="/integrations" className="text-sm text-sky-400 hover:underline">
        Go to Integrations →
      </Link>
    </UnavailableState>
  );
}
