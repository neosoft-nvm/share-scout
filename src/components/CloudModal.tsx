import { useState, useEffect, useRef } from 'react';
import { Modal } from './Modal';
import { GoogleDriveSmallIcon, OneDriveSmallIcon } from './BrandIcons';
import { cloudStart, cloudStep, cloudCancel, cloudFinish, cloudAccounts, getDefaults, errorMessage } from '../services/api';
import type { ResourceItem, CloudQuestion } from '../types';

type Provider = 'Google Drive' | 'OneDrive';
export function CloudModal({ isOpen, onClose, onAddCloudAccount }: {
  isOpen: boolean; onClose: () => void; onAddCloudAccount: (item: ResourceItem) => Promise<void>;
}) {
  const [provider, setProvider] = useState<Provider>('Google Drive');
  const [mountPath, setMountPath] = useState('');
  const [driveName, setDriveName] = useState('Google Drive');
  const [accounts, setAccounts] = useState<{ remote: string; provider: Provider }[]>([]);
  const [saved, setSaved] = useState('');
  const [busy, setBusy] = useState(false);
  const [ready, setReady] = useState(false);
  const [question, setQuestion] = useState<CloudQuestion | null>(null);
  const [answer, setAnswer] = useState('');
  const [error, setError] = useState('');
  const [status, setStatus] = useState('');
  const [windows, setWindows] = useState(false);
  const session = useRef('');
  const remote = useRef('');
  const generation = useRef(0);
  const completed = useRef(false);
  const defaults = useRef({ windows: false, mountRoot: '', drive: '' });

  useEffect(() => {
    if (!isOpen) return;
    const token = ++generation.current;
    setReady(false); setError(''); setQuestion(null); setStatus(''); setBusy(false); setSaved(''); completed.current = false;
    void Promise.all([getDefaults(), cloudAccounts()]).then(([value, existing]) => {
      if (generation.current !== token) return;
      defaults.current = value; setWindows(value.windows); setMountPath(value.windows ? value.drive : `${value.mountRoot}/${provider}`); setAccounts(existing); setReady(true);
    }).catch(err => { if (generation.current === token) setError(errorMessage(err)); });
    return () => { generation.current++; };
  }, [isOpen]);

  function changeProvider(value: Provider) {
    setProvider(value); setDriveName(value); setMountPath(defaults.current.windows ? defaults.current.drive : `${defaults.current.mountRoot}/${value}`); setSaved('');
  }
  async function close() {
    if (completed.current && busy) return;
    generation.current++;
    try { if (session.current) await cloudCancel(session.current); session.current = ''; setBusy(false); onClose(); }
    catch (err) { setError(errorMessage(err)); }
  }
  async function connectRemote(value: string) {
    completed.current = true;
    setStatus('Connecting your cloud drive…');
    await onAddCloudAccount({ name: driveName.trim(), kind: provider, source: value, target: mountPath.trim(), auto: true, status: 'Disconnected' });
    onClose();
  }
  async function submit() {
    const token = generation.current;
    setError(''); setBusy(true);
    try {
      if (saved) { await connectRemote(saved); return; }
      if (completed.current) { await connectRemote(remote.current); return; }
      if (!session.current) {
        const start = await cloudStart(provider);
        if (generation.current !== token) { await cloudCancel(start.session); return; }
        session.current = start.session; remote.current = start.remote;
      }
      setStatus('Finish secure sign-in in your browser. You can cancel here.');
      let result = await cloudStep(session.current, question?.State, question ? answer : undefined);
      while (result.State && result.Option?.Name === 'config_is_local') result = await cloudStep(session.current, result.State, true);
      if (generation.current !== token) return;
      if (result.Error) throw new Error(result.Error);
      if (!result.State) {
        await cloudFinish(session.current); session.current = ''; completed.current = true; setQuestion(null);
        await connectRemote(remote.current);
      } else {
        setQuestion(result); setAnswer(String(result.Option?.Default ?? '')); setStatus('Choose an option to finish sign-in.');
      }
    } catch (err) { if (generation.current === token) setError(errorMessage(err)); }
    finally { if (generation.current === token) setBusy(false); }
  }
  return <Modal isOpen={isOpen} onClose={() => void close()} title="Connect Cloud Storage" subtitle="Mount Google Drive or Microsoft OneDrive directly to your desktop" maxWidth="max-w-xl">
    <form className="space-y-5" onSubmit={e => { e.preventDefault(); void submit(); }}>
      <fieldset disabled={!ready || busy || !!session.current || completed.current} className="grid grid-cols-2 gap-4">
        {(['Google Drive', 'OneDrive'] as Provider[]).map(value => <button key={value} type="button" onClick={() => changeProvider(value)} aria-pressed={provider === value} className={`provider-card ${provider === value ? 'selected' : ''}`}>
          {value === 'Google Drive' ? <GoogleDriveSmallIcon className="w-16 h-16" /> : <OneDriveSmallIcon className="w-16 h-16" />}<span>{value === 'OneDrive' ? 'Microsoft OneDrive' : value}</span>
        </button>)}
      </fieldset>
      {!session.current && !completed.current && accounts.some(x => x.provider === provider) && <label className="field-label">Account<select className="field" value={saved} onChange={e => setSaved(e.target.value)} disabled={busy}><option value="">Sign in to a new account</option>{accounts.filter(x => x.provider === provider).map(x => <option key={x.remote} value={x.remote}>{x.remote}</option>)}</select></label>}
      <label className="field-label">{windows ? 'Drive letter' : 'Mount folder path'}<input required disabled={busy} className="field" value={mountPath} onChange={e => setMountPath(e.target.value)} placeholder={windows ? 'R:' : '~/ShareScout/Google Drive'} /></label>
      <label className="field-label">Folder name<input required disabled={busy} className="field" value={driveName} onChange={e => setDriveName(e.target.value)} /></label>
      {question && <label className="field-label">{question.Option?.Help || 'Choose an option'}
        {question.Option?.Exclusive ? <select className="field" value={answer} onChange={e => setAnswer(e.target.value)} disabled={busy} required={question.Option.Required}><option value="">Choose…</option>{question.Option.Examples?.map(x => <option key={x.Value} value={x.Value}>{x.Help || x.Value}</option>)}</select> : <input className="field" type={question.Option?.IsPassword ? 'password' : 'text'} required={question.Option?.Required} value={answer} onChange={e => setAnswer(e.target.value)} disabled={busy} />}
      </label>}
      {status && <p role="status" className="text-sm text-slate-600">{status}</p>}
      {error && <p role="alert" className="error-message">{error}</p>}
      <div className="dialog-actions"><button type="button" disabled={busy && completed.current} className="secondary" onClick={() => void close()}>Cancel</button><button disabled={!ready || busy} className="primary">{busy ? 'Connecting…' : question ? 'Continue' : completed.current ? 'Retry connection' : 'Connect Account'}</button></div>
    </form>
  </Modal>;
}
