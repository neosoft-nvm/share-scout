import { useState, useEffect, useRef } from 'react';
import type { ResourceItem, Credentials } from './types';
import { ApiError, loadResources, saveResources, mountResource, unmountResource, openInFileManager, errorMessage, isTauri, desktopCall, startupUpdate, type UpdateInfo } from './services/api';
import { Dashboard } from './screens/Dashboard';
import { Discovery } from './screens/Discovery';
import { CloudModal } from './components/CloudModal';
import { ManualAddressModal } from './components/ManualAddressModal';
import { LocalSharesModal } from './components/LocalSharesModal';
import { ShareFolderModal } from './components/ShareFolderModal';
import { DiagnosticsModal } from './components/DiagnosticsModal';
import { NetworkInfoModal } from './components/NetworkInfoModal';
import { CredentialsModal } from './components/CredentialsModal';
import { PermanentMountModal } from './components/PermanentMountModal';
import { UpdateModal } from './components/UpdateModal';

const same = (a: ResourceItem, b: ResourceItem) => a.kind === b.kind && a.source === b.source;

export function App() {
  const [currentScreen, setCurrentScreen] = useState<'dashboard' | 'discovery'>('dashboard');
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const items = useRef<ResourceItem[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [modal, setModal] = useState('');
  const [mountItem, setMountItem] = useState<ResourceItem | null>(null);
  const [error, setError] = useState('');
  const [update, setUpdate] = useState<UpdateInfo | null>(null);
  const [authItem, setAuthItem] = useState<ResourceItem | null>(null);
  const busy = useRef(false);
  const [working, setWorking] = useState(false);
  const loaded = useRef(false);
  const initialized = useRef(false);

  function show(next: ResourceItem[]) { items.current = next; setResources(next); }
  async function persist(next: ResourceItem[]) {
    if (!loaded.current) throw new Error('Saved connections could not be loaded. Restart ShareScout before making changes.');
    if (!await saveResources(next)) throw new Error('Connections could not be saved.');
    show(next);
  }
  async function connect(item: ResourceItem, credentials?: Credentials, remember = false): Promise<ResourceItem> {
    const original = items.current.find(x => same(x, item)) || item;
    show(items.current.map(x => same(x, item) ? { ...x, status: 'Connecting…' } : x));
    let connected: ResourceItem;
    try {
      connected = await mountResource(original, credentials, remember);
    } catch (err) {
      show(items.current.map(x => same(x, item) ? { ...original, status: 'Disconnected' } : x));
      if (err instanceof ApiError && err.auth && !credentials) setAuthItem(original);
      throw err;
    }
    show(items.current.map(x => same(x, item) ? connected : x));
    await persist(items.current);
    if (connected.warning) setError(connected.warning);
    return connected;
  }
  async function perform(action: () => Promise<void>) {
    if (busy.current) return;
    busy.current = true; setWorking(true); setError('');
    try { await action(); }
    catch (err) { setError(errorMessage(err)); }
    finally { busy.current = false; setWorking(false); }
  }
  async function addAndConnect(item: ResourceItem) {
    const existing = items.current.find(x => same(x, item));
    if (!existing) await persist([...items.current, { ...item, status: 'Disconnected' }]);
    const index = items.current.findIndex(x => same(x, item));
    setSelectedIndex(index);
    const connected = await connect(existing || item);
    await openInFileManager(connected);
  }
  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;
    if (isTauri()) void startupUpdate().then(setUpdate).catch(() => {});
    void perform(async () => {
      const saved = await loadResources(); loaded.current = true;
      show(saved); setSelectedIndex(saved.length ? 0 : null);
      for (const item of saved.filter(x => x.auto && x.mountMode !== 'system' && x.status !== 'Connected')) {
        try { await connect(item); }
        catch (err) { setError(errorMessage(err)); if (err instanceof ApiError && err.auth) break; }
      }
    });
  }, []);
  useEffect(() => {
    if (!isTauri()) return;
    let cleanup: (() => void) | undefined;
    let disposed = false;
    void import('@tauri-apps/api/window').then(async ({ getCurrentWindow }) => {
      const win = getCurrentWindow();
      const unlisten = await win.onCloseRequested(async event => {
        event.preventDefault();
        if (busy.current) { setError('Wait for the current operation to finish before closing.'); return; }
        try { await desktopCall('shutdown'); await win.destroy(); }
        catch (err) { setError(errorMessage(err)); }
      });
      if (disposed) unlisten(); else cleanup = unlisten;
    }).catch(err => setError(errorMessage(err)));
    return () => { disposed = true; cleanup?.(); };
  }, []);

  return <>
    {error && <div role="alert" className="app-alert"><span>{error}</span><button aria-label="Dismiss message" onClick={() => setError('')}>×</button></div>}
    {currentScreen === 'dashboard' ? <Dashboard resources={resources} selectedIndex={selectedIndex} onSelectIndex={setSelectedIndex} busy={working}
      onOpen={item => void perform(async () => { const connected = item.status === 'Connected' ? item : await connect(item); await openInFileManager(connected); })}
      onConnect={index => void perform(async () => { await connect(items.current[index]); })}
      onDisconnect={index => void perform(async () => { const item = items.current[index]; if (!await unmountResource(item)) throw new Error('Disconnect did not finish.'); await persist(items.current.map(x => same(x, item) ? { ...x, status: 'Disconnected', auto: false } : x)); })}
      onRemove={index => void perform(async () => { const item = items.current[index]; if (item.status === 'Connected' && !await unmountResource(item)) throw new Error('Disconnect this folder before removing it.'); await persist(items.current.filter(x => !same(x, item))); setSelectedIndex(items.current.length ? 0 : null); })}
      onOpenDiscovery={() => setCurrentScreen('discovery')} onOpenCloud={() => setModal('cloud')} onOpenShareFolder={() => setModal('local-shares')} onOpenManualAddress={() => setModal('manual')} onCheckTools={() => setModal('diagnostics')}
      onRefreshConnections={() => void perform(async () => { show(await loadResources()); })}
      onNetworkInfo={() => setModal('network-info')}
      onPermanentMount={item => setMountItem(item)}
      onToggleAuto={(index, auto) => void perform(async () => { await persist(items.current.map((item, i) => i === index ? { ...item, auto } : item)); })}
    /> : <Discovery onBack={() => setCurrentScreen('dashboard')} onConnectShare={async (address, name, auto) => {
      await addAndConnect({ name: `${name} · ${address}`, kind: 'Network share', source: `smb://${address}/${encodeURIComponent(name)}`, target: '', auto, status: 'Disconnected' });
    }} onPermanentMountShare={async (address, name) => {
      const item: ResourceItem = { name: `${name} · ${address}`, kind: 'Network share', source: `smb://${address}/${encodeURIComponent(name)}`, target: '', auto: false, status: 'Disconnected' };
      const existing = items.current.find(x => same(x, item));
      if (!existing) await persist([...items.current, item]);
      setSelectedIndex(items.current.findIndex(x => same(x, item)));
      setCurrentScreen('dashboard'); setMountItem(existing || item);
    }} />}
    <CloudModal isOpen={modal === 'cloud'} onClose={() => setModal('')} onAddCloudAccount={addAndConnect} />
    <ManualAddressModal isOpen={modal === 'manual'} onClose={() => setModal('')} onAddAddress={async (name, source, auto) => addAndConnect({ name, source, auto, kind: 'Network share', status: 'Disconnected', target: '' })} />
    <LocalSharesModal isOpen={modal === 'local-shares'} onClose={() => setModal('')} onSetup={() => setModal('share')} />
    <ShareFolderModal isOpen={modal === 'share'} onClose={() => setModal('local-shares')} />
    <DiagnosticsModal isOpen={modal === 'diagnostics'} onClose={() => setModal('')} />
    <NetworkInfoModal isOpen={modal === 'network-info'} onClose={() => setModal('')} />
    {mountItem && <PermanentMountModal item={mountItem} onClose={() => setMountItem(null)} onBusy={value => { busy.current = value; setWorking(value); }} onUpdated={persist} />}
    {update && !mountItem && !modal && !authItem && !working && currentScreen === 'dashboard' && <UpdateModal result={update} onClose={() => setUpdate(null)} />}
    {authItem && <CredentialsModal isOpen address={authItem.source} onClose={() => setAuthItem(null)} onSubmit={async (credentials, remember) => {
      const connected = await connect(authItem, credentials, remember); await openInFileManager(connected); setAuthItem(null); setError(connected.warning || '');
    }} />}
  </>;
}
export default App;
