import { UnavailableState } from "@/components/ui/States";

export default function ProductionPage() {
  return (
    <UnavailableState reason="No video-listing endpoint exists yet (GET /api/channels/{id}/videos or similar). The videos table exists in the database and per-channel produced/uploaded counts are visible on the Channels page, but individual video records — thumbnail, title, per-stage progress — aren't exposed via the API yet." />
  );
}
