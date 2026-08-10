import { Panel } from "@/components/ui/Panel";

export default function SettingsPage() {
  const baseUrl = process.env.BACKEND_API_BASE_URL ?? "not set";
  const keyConfigured = Boolean(process.env.BACKEND_API_KEY);

  return (
    <div className="space-y-6">
      <Panel title="Backend Connection">
        <dl className="grid grid-cols-[160px_1fr] gap-y-3 text-sm">
          <dt className="text-slate-500">API base URL</dt>
          <dd className="font-mono text-slate-200">{baseUrl}</dd>
          <dt className="text-slate-500">API key</dt>
          <dd className="font-mono text-slate-200">{keyConfigured ? "•••••••••••• (configured)" : "not configured"}</dd>
          <dt className="text-slate-500">Auth model</dt>
          <dd className="text-slate-200">
            Single-operator — one shared API key, no user accounts or roles. The key is only ever used
            server-side (this page&apos;s proxy route); it&apos;s never sent to your browser.
          </dd>
        </dl>
      </Panel>

      <Panel title="Not yet available">
        <p className="text-sm text-slate-500">
          There&apos;s no real settings backend — nothing here is editable or persisted. Theme, notification
          preferences, and account management aren&apos;t implemented since this is a single-operator tool with
          no user-accounts system.
        </p>
      </Panel>
    </div>
  );
}
