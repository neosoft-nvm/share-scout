import { useEffect, useState } from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import { Modal } from './Modal';
import { runDiagnostics, repairSharing, checkUpdates, prepareUpdate, installUpdate, errorMessage, repairFusePermission } from '../services/api';
import type { Diagnostics } from '../types';

export function DiagnosticsModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [result, setResult] = useState<Diagnostics | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [confirmFuse, setConfirmFuse] = useState(false);
  const [upgrade, setUpgrade] = useState('');
  async function action(task: () => Promise<void>) {
    setBusy(true); setError(''); setMessage('');
    try { await task(); } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }
  useEffect(() => {
    if (!isOpen) return;
    let alive = true; setConfirmFuse(false); setBusy(true); setResult(null); setError(''); setMessage('');
    void runDiagnostics().then(value => { if (alive) setResult(value); }).catch(err => { if (alive) setError(errorMessage(err)); }).finally(() => { if (alive) setBusy(false); });
    return () => { alive = false; };
  }, [isOpen]);
  return <Modal isOpen={isOpen} onClose={() => { if (!busy) onClose(); }} title="Sharing Diagnostics" subtitle="System tools and configuration status for file sharing" maxWidth="max-w-2xl">
    <div className="space-y-5">
      {!result && busy && <p role="status">Checking your computer…</p>}
      {result && <div className="rounded-xl border border-slate-200 divide-y divide-slate-200">{result.checks.map(item => <div key={item.name} className="p-4 flex gap-3 justify-between items-center"><div className="flex gap-3 items-center">{item.ok ? <CheckCircle2 size={22} className="text-emerald-600 shrink-0" /> : <AlertCircle size={22} className="text-amber-600 shrink-0" />}<div><p className="font-semibold">{item.name}</p><p className="text-xs text-slate-500">{item.desc}</p></div></div><span className={`diagnostic-status ${item.ok ? 'ready' : 'missing'}`}>{item.status}</span></div>)}</div>}
      {error && <p role="alert" className="error-message">{error}</p>}{message && <p role="status" className="text-sm text-slate-600">{message}</p>}
      <div className="flex flex-wrap gap-3"><button className="primary" disabled={busy} onClick={() => void action(async () => { const value = await checkUpdates(); setUpgrade(value.newer && value.canInstall ? value.latest : ''); setMessage(value.newer ? `ShareScout ${value.latest} is available. Installed: ${value.installed}.${value.canInstall ? "" : " A verified desktop update package has not been published for this platform."}` : `ShareScout ${value.installed} is up to date.`); })}>Check for Updates</button><button className="secondary" disabled={busy} onClick={() => void action(async () => { const value = await repairSharing(); setMessage(value.message || 'Sharing setup finished.'); setResult(await runDiagnostics()); })}>Repair Local Sharing</button><button className="secondary" disabled={busy} onClick={() => void action(async () => setResult(await runDiagnostics()))}>Check Again</button></div>
      {result?.fusePermission?.applicable && !result.fusePermission.enabled && <div className="rounded-xl border border-amber-200 p-4 space-y-3 text-sm">
        <p>This computer needs SELinux permission for Samba to read its configured NTFS/FUSE shares. This applies to configured FUSE-backed shares system-wide; SELinux stays enabled.</p>
        <p className="break-all">Affected folders: {result.fusePermission.paths.join(', ')}</p>
        <label className="flex gap-2"><input type="checkbox" disabled={busy} checked={confirmFuse} onChange={e => setConfirmFuse(e.target.checked)} />Allow Samba access to configured NTFS/FUSE shares on this computer.</label>
        <button className="primary" disabled={busy || !confirmFuse} onClick={() => void action(async () => {
          const repaired = await repairFusePermission(); setResult(repaired.diagnostics); setMessage(repaired.message); setConfirmFuse(false);
        })}>Approve & Repair NTFS/FUSE Sharing</button>
      </div>}
      {upgrade && <button className="primary" disabled={busy} onClick={() => void action(async () => {
        setMessage('Downloading and verifying the update…');
        const stage = await prepareUpdate(upgrade); setMessage('Installing and restarting…'); await installUpdate(stage);
      })}>Upgrade to {upgrade}</button>}
      <div className="dialog-actions"><button className="secondary" disabled={busy} onClick={onClose}>Close</button></div>
    </div>
  </Modal>;
}
