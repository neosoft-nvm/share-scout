import { useState } from 'react';
import type { Credentials } from '../types';
import { Modal } from './Modal';
import { errorMessage } from '../services/api';

export function CredentialsModal({ isOpen, address, onClose, onSubmit }: {
  isOpen: boolean; address: string; onClose: () => void;
  onSubmit: (credentials: Credentials, remember: boolean) => Promise<void>;
}) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [domain, setDomain] = useState('');
  const [remember, setRemember] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return <Modal isOpen={isOpen} onClose={() => { if (!busy) { setPassword(''); onClose(); } }} title="Sign In to Device" subtitle={`Enter credentials for ${address}`} maxWidth="max-w-md">
    <form className="space-y-4" onSubmit={async e => {
      e.preventDefault(); setError(''); setBusy(true);
      try { await onSubmit({ username: username.trim(), password, domain: domain.trim() }, remember); setPassword(''); }
      catch (err) { setError(errorMessage(err)); }
      finally { setBusy(false); }
    }}>
      <label className="field-label">Username<input autoFocus required autoComplete="username" value={username} onChange={e => setUsername(e.target.value)} className="field" /></label>
      <label className="field-label">Password<input type="password" autoComplete="current-password" value={password} onChange={e => setPassword(e.target.value)} className="field" /></label>
      <label className="field-label">Domain (optional)<input value={domain} onChange={e => setDomain(e.target.value)} className="field" /></label>
      <label className="flex gap-2 items-center text-sm"><input type="checkbox" checked={remember} onChange={e => setRemember(e.target.checked)} />Remember password in system keychain</label>
      {error && <p role="alert" className="error-message">{error}</p>}
      <div className="dialog-actions"><button type="button" disabled={busy} className="secondary" onClick={() => { setPassword(''); onClose(); }}>Cancel</button><button disabled={busy} className="primary">{busy ? 'Signing in…' : 'Sign In'}</button></div>
    </form>
  </Modal>;
}
