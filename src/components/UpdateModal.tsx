import { useState } from 'react';
import { Modal } from './Modal';
import { prepareUpdate, installUpdate, setUpdatePreference, errorMessage, type UpdateInfo } from '../services/api';

export function UpdateModal({ result, onClose }: { result: UpdateInfo; onClose: () => void }) {
  const [disable, setDisable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  async function dismiss() {
    if (busy) return;
    try { await setUpdatePreference(!disable); onClose(); }
    catch (err) { setError(errorMessage(err)); }
  }
  return <Modal isOpen onClose={() => void dismiss()} title="A New ShareScout Is Ready" subtitle={`Version ${result.latest} is available. You have ${result.installed}.`}>
    <div className="space-y-4">
      <p className="text-sm text-slate-600">Your saved connections and system password store will be kept. Disconnect cloud drives before upgrading.</p>
      <label className="flex gap-2 items-center text-sm"><input type="checkbox" checked={disable} disabled={busy} onChange={e => setDisable(e.target.checked)} />Don’t check for updates automatically</label>
      {status && <p role="status" className="text-sm text-slate-600">{status}</p>}{error && <p role="alert" className="error-message">{error}</p>}
      <div className="dialog-actions"><button className="secondary" disabled={busy} onClick={() => void dismiss()}>Not now</button><button className="primary" disabled={busy || !result.canInstall} onClick={async () => {
        setBusy(true); setError('');
        try { await setUpdatePreference(!disable); setStatus('Downloading and verifying the update…'); const stage = await prepareUpdate(result.latest); setStatus('Installing and restarting…'); await installUpdate(stage); }
        catch (err) { setError(errorMessage(err)); setBusy(false); setStatus(''); }
      }}>{busy ? 'Upgrading…' : 'Upgrade now'}</button></div>
    </div>
  </Modal>;
}
