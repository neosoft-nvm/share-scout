import { useEffect, useState } from 'react';
import type { ResourceItem } from '../types';
import { Modal } from './Modal';
import { errorMessage, permanentApply, permanentDefaults, permanentPreview, permanentRemove,
  type PermanentMountDefaults, type PermanentMountPlan } from '../services/api';

export function PermanentMountModal({ item, onClose, onUpdated, onBusy }: {
  item: ResourceItem; onClose: () => void; onUpdated: (items: ResourceItem[]) => Promise<void>;
  onBusy: (busy: boolean) => void;
}) {
  const [info, setInfo] = useState<PermanentMountDefaults | null>(null);
  const [target, setTarget] = useState('');
  const [account, setAccount] = useState('');
  const [readOnly, setReadOnly] = useState(true);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [domain, setDomain] = useState('');
  const [plan, setPlan] = useState<PermanentMountPlan | null>(null);
  const [confirmed, setConfirmed] = useState(false);
  const [removing, setRemoving] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [done, setDone] = useState('');
  useEffect(() => {
    let alive = true;
    void permanentDefaults(item.source).then(data => {
      if (!alive) return;
      setInfo(data); setTarget(data.target || ''); setAccount(data.account || '');
    }).catch(err => { if (alive) setError(errorMessage(err)); });
    return () => { alive = false; };
  }, [item.source]);
  async function work(action: () => Promise<void>) {
    if (busy) return;
    setBusy(true); onBusy(true); setError('');
    try { await action(); }
    catch (err) { setError(errorMessage(err)); }
    finally { setBusy(false); onBusy(false); }
  }
  const close = () => { if (!busy) { setPassword(''); onClose(); } };
  return <Modal isOpen onClose={close} title="Permanent Mount" maxWidth="max-w-lg"
    subtitle="Give this share a stable folder path for Plex or other background services.">
    <div className="space-y-4">
      <p className="text-sm break-all">Network folder: <strong>{item.source}</strong></p>
      {error && <p role="alert" className="error-message">{error}</p>}
      {!info && !error && <p role="status">Checking this computer…</p>}
      {info && !info.supported && <p>{info.reason}</p>}
      {done ? <><p role="status" className="text-sm whitespace-pre-line">{done}</p><div className="dialog-actions"><button className="primary" onClick={close}>Done</button></div></> : info?.supported && <>
        {info.existing ? <>
          <p className="text-sm">Folder path: <strong className="break-all">{info.existing.target}</strong></p>
          <p className="text-sm">Access for <strong>{info.existing.account}</strong> · {info.existing.readOnly ? 'Read only' : 'Read and write'}</p>
          <p className="text-sm">{info.existing.connected ? 'Mounted now.' : 'Configured; the sharing computer may be offline.'} Reconnects on access after reboot and stays available when ShareScout closes.</p>
          {removing && <p role="status" className="text-sm">Removing this mount stops access through this path, including Plex libraries using it. The original shared folder and its files stay unchanged.</p>}
          <div className="dialog-actions"><button className="secondary" disabled={busy} onClick={removing ? () => setRemoving(false) : close}>Cancel</button>
            <button className="primary" disabled={busy} onClick={() => {
              if (!removing) { setRemoving(true); return; }
              void work(async () => { const result = await permanentRemove(item.source); await onUpdated(result.resources); setDone('Permanent mount removed. The original shared folder and files were kept.'); });
            }}>{busy ? 'Removing…' : removing ? 'Confirm Removal' : 'Remove Permanent Mount'}</button></div>
        </> : plan ? <>
          <div className="rounded-xl border border-slate-200 p-4 space-y-2 text-sm">
            <p>Mount at: <strong className="break-all">{plan.target}</strong></p>
            <p>Local access: <strong>{plan.account}</strong> and your account</p>
            <p>Permissions: <strong>{plan.readOnly ? 'Read only' : 'Read and write'}</strong></p>
            <p>Available after reboot and when ShareScout is closed. The sharing computer must stay reachable.</p>
          </div>
          <p className="text-sm">Administrator approval is required. Setup installs cifs-utils if needed, creates this mount, and checks access. Failed setup is rolled back.</p>
          <label className="flex gap-2 text-sm items-start"><input type="checkbox" checked={confirmed} disabled={busy} onChange={e => setConfirmed(e.target.checked)} />Save this share’s sign-in in a protected, administrator-only file so it can reconnect without opening ShareScout.</label>
          <div className="dialog-actions"><button className="secondary" disabled={busy} onClick={() => { setPlan(null); setConfirmed(false); }}>Back</button><button className="secondary" disabled={busy} onClick={close}>Cancel</button>
            <button className="primary" disabled={busy || !confirmed} onClick={() => void work(async () => {
              const result = await permanentApply(item.source, plan.target, plan.account, plan.readOnly, username.trim() ? { username: username.trim(), password, domain: domain.trim() } : undefined);
              setPassword(''); await onUpdated(result.resources);
              setDone(`Mounted and ready.\nAdd this exact folder to Plex on THIS computer:\n${result.target}\nThe folder remains mounted when ShareScout closes.`);
            })}>{busy ? 'Setting up…' : 'Confirm & Mount'}</button></div>
        </> : <form className="space-y-4" onSubmit={e => { e.preventDefault(); void work(async () => setPlan(await permanentPreview(item.source, target, account, readOnly))); }}>
          <fieldset disabled={busy} className="space-y-4">
            <label className="field-label">Mount folder<input required className="field" value={target} onChange={e => setTarget(e.target.value)} /></label>
            <label className="field-label">Allow access for<select className="field" value={account} onChange={e => setAccount(e.target.value)}>{info.accounts?.map(x => <option key={x.name} value={x.name}>{x.label}</option>)}</select></label>
            <label className="flex gap-2 text-sm"><input type="checkbox" checked={readOnly} onChange={e => setReadOnly(e.target.checked)} />Read only (recommended for Plex)</label>
            <p className="text-sm">Use the sharing computer’s login. Leave the sign-in fields blank to reuse your saved ShareScout sign-in.</p>
            <label className="field-label">Sharing username<input className="field" autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} /></label>
            <label className="field-label">Sharing password<input type="password" className="field" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} /></label>
            <label className="field-label">Domain (optional)<input className="field" value={domain} onChange={e => setDomain(e.target.value)} /></label>
          </fieldset>
          {!info.approvalAvailable && <p role="alert" className="error-message">Administrator approval is unavailable. Install polkit and run ShareScout in your desktop session.</p>}
          <div className="dialog-actions"><button type="button" className="secondary" disabled={busy} onClick={close}>Cancel</button><button className="primary" disabled={busy || !info.approvalAvailable}>{busy ? 'Checking…' : 'Review Mount'}</button></div>
        </form>}
      </>}
      {(!info || !info.supported) && <div className="dialog-actions"><button className="secondary" onClick={close}>Close</button></div>}
    </div>
  </Modal>;
}
