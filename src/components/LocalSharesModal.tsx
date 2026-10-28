import { useEffect, useState } from 'react';
import { Modal } from './Modal';
import { listLocalShares, errorMessage, type LocalShare } from '../services/api';

export function LocalSharesModal({ isOpen, onClose, onSetup }: { isOpen: boolean; onClose: () => void; onSetup: () => void }) {
  const [shares, setShares] = useState<LocalShare[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    if (!isOpen) return;
    let active = true;
    setLoading(true); setError(''); setShares([]); setWarnings([]);
    void listLocalShares().then(result => { if (active) { setShares(result.shares); setWarnings(result.warnings); } })
      .catch(err => { if (active) setError(errorMessage(err)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [isOpen, revision]);
  return <Modal isOpen={isOpen} onClose={onClose} title="Folders Shared by This Computer"
    subtitle="Local folders offered to other devices over the network" maxWidth="max-w-2xl">
    <p className="text-sm text-slate-600 mb-4">These shares belong to this computer, including folders shared outside ShareScout. Network and cloud folders you connect to are listed on the main screen.</p>
    {loading && <p role="status">Reading local shared folders…</p>}
    {error && <p role="alert" className="error-message">{error}</p>}
    {warnings.map(warning => <p role="status" key={warning} className="text-sm text-amber-800 mb-2">{warning}</p>)}
    {!loading && !error && shares.length === 0 && <p className="text-sm text-slate-600">No local folder shares found.</p>}
    <ul className="space-y-3">
      {shares.map(share => <li key={share.name} className="rounded-xl border border-slate-200 p-3 text-sm">
        <p className="font-semibold text-slate-900 break-all">{share.name}</p>
        <p className="font-mono text-xs text-slate-600 break-all mt-1">{share.path}</p>
        <p className="text-xs text-slate-600 mt-1">{share.access}{share.hidden ? ' · Hidden from browsing' : ''}{!share.available ? ' · Disabled in sharing settings' : ''}</p>
      </li>)}
    </ul>
    {!loading && shares.length > 0 && <p className="text-xs text-slate-500 mt-3">Configured shares are shown here. Folder permissions, sharing services and firewall settings determine whether another device can access them.</p>}
    <div className="dialog-actions">
      <button type="button" className="secondary" onClick={onClose}>Close</button>
      <button type="button" className="secondary" disabled={loading} onClick={() => setRevision(value => value + 1)}>Refresh</button>
      <button type="button" className="primary" onClick={onSetup}>Set Up a Share</button>
    </div>
  </Modal>;
}
