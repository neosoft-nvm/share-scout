import { useEffect, useRef, useState } from 'react';
import { Folder, Laptop, RotateCw } from 'lucide-react';
import type { DiscoveredDevice, DiscoveredShare, Credentials } from '../types';
import { ApiError, errorMessage, listDeviceShares, scanLocalNetwork, stopScan } from '../services/api';
import { CredentialsModal } from '../components/CredentialsModal';
import { Modal } from '../components/Modal';

export function Discovery({ onBack, onConnectShare, onPermanentMountShare }: {
  onBack: () => void; onConnectShare: (address: string, name: string, auto: boolean) => Promise<void>;
  onPermanentMountShare?: (address: string, name: string) => Promise<void>;
}) {
  const [scanning, setScanning] = useState(false);
  const [devices, setDevices] = useState<DiscoveredDevice[]>([]);
  const [selectedDevice, setSelectedDevice] = useState('');
  const [shares, setShares] = useState<DiscoveredShare[]>([]);
  const [selectedShare, setSelectedShare] = useState('');
  const [loading, setLoading] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [error, setError] = useState('');
  const [networkLabel, setNetworkLabel] = useState('Connected IPv4 networks');
  const [showAuth, setShowAuth] = useState(false);
  const [showManual, setShowManual] = useState(false);
  const [manual, setManual] = useState('');
  const [auto, setAuto] = useState(true);
  const activeScan = useRef('');
  const shareRequest = useRef(0);
  const alive = useRef(true);

  async function selectDevice(address: string, credentials?: Credentials, remember = false) {
    const request = ++shareRequest.current;
    setSelectedDevice(address); setSelectedShare(''); setShares([]); setLoading(true); setError('');
    try {
      const result = await listDeviceShares(address, credentials, remember);
      if (!alive.current || request !== shareRequest.current) return;
      setShares(result); setSelectedShare(result[0]?.name || '');
    } catch (err) {
      if (alive.current && request === shareRequest.current) {
        setError(errorMessage(err));
        if (err instanceof ApiError && err.auth && !credentials) setShowAuth(true);
      }
      if (credentials) throw err;
    } finally { if (alive.current && request === shareRequest.current) setLoading(false); }
  }
  async function scan() {
    const id = crypto.randomUUID(); activeScan.current = id; setScanning(true); setError('');
    try {
      const result = await scanLocalNetwork(id);
      if (!alive.current || activeScan.current !== id) return;
      setDevices(result.devices);
      setNetworkLabel(result.networks.map(x => x.network + (x.limited ? ' (nearby /24 only)' : '')).join(', ') || 'No connected IPv4 networks');
      if (result.devices.length) void selectDevice(result.devices[0].address);
      else { setSelectedDevice(''); setShares([]); setSelectedShare(''); }
    } catch (err) { if (alive.current) setError(errorMessage(err)); }
    finally { if (alive.current && activeScan.current === id) { setScanning(false); activeScan.current = ''; } }
  }
  useEffect(() => {
    alive.current = true;
    void scan();
    return () => { alive.current = false; shareRequest.current++; if (activeScan.current) void stopScan(activeScan.current).catch(() => {}); };
  }, []);
  async function leave() {
    if (activeScan.current) { await stopScan(activeScan.current); activeScan.current = ''; }
    onBack();
  }
  return <div className="app-screen scanner">
    <header className="scanner-header">
      <h1 className="text-2xl font-semibold">Find Network Folders</h1>
      <div className={`scan-progress ${scanning ? 'scanning' : ''}`} aria-label={scanning ? 'Scanning' : 'Scan complete'}><div /></div>
      <div className="flex flex-wrap justify-between items-center gap-3"><p className="text-sm text-slate-600">{scanning ? 'Scanning connected networks…' : `${networkLabel} · Found ${devices.length} devices`}</p>
        <button className="secondary flex items-center gap-2" onClick={() => scanning ? void stopScan(activeScan.current).catch(err => setError(errorMessage(err))) : void scan()}><RotateCw size={16} />{scanning ? 'Stop' : 'Rescan'}</button></div>
    </header>
    {error && <p role="alert" className="error-message mx-6 mt-3">{error}</p>}
    <div className="scanner-columns">
      <section className="scanner-column"><h2>Discovered Devices</h2><div className="scanner-list space-y-3">
        {!devices.length && <p className="empty-state">{scanning ? 'Searching for devices offering SMB sharing…' : 'No devices found. Enable file sharing on the other device, or use Manual IP.'}</p>}
        {devices.map(device => <button type="button" key={device.address} onClick={() => void selectDevice(device.address)} className={`device-row ${selectedDevice === device.address ? 'selected' : ''}`}><Laptop size={26} /><span>{device.address}{device.name ? ` — ${device.name}` : ''}</span>{device.category && <span className="text-xs text-slate-500">{device.category}</span>}</button>)}
      </div></section>
      <section className="scanner-column"><h2>{selectedDevice ? `Shared Folders on ${selectedDevice}` : 'Shared Folders'}</h2><div className="scanner-list share-list">
        {!shares.length && <p className="empty-state">{loading ? 'Loading folders…' : selectedDevice ? 'No folders available. Try Sign In or check sharing on this device.' : 'Choose a device to see its folders.'}</p>}
        {shares.map(share => <button type="button" key={share.name} onClick={() => setSelectedShare(share.name)} className={`share-row ${selectedShare === share.name ? 'selected' : ''}`}><Folder size={28} /><span><strong>{share.name}</strong>{share.comment && <small>{share.comment}</small>}{share.permission && <small>{share.permission}</small>}</span></button>)}
      </div></section>
    </div>
    <footer className="scanner-footer"><div className="space-y-2"><button className="text-sm underline text-indigo-700" disabled={!selectedDevice || connecting} onClick={() => setShowAuth(true)}>Need credentials? Sign In</button><label className="flex gap-2 text-xs"><input type="checkbox" checked={auto} onChange={e => setAuto(e.target.checked)} />Reconnect when app opens</label></div>
      <div className="flex flex-wrap gap-2"><button className="primary" disabled={!selectedDevice || !selectedShare || loading || connecting} onClick={async () => {
        setConnecting(true); setError('');
        try { await onConnectShare(selectedDevice, selectedShare, auto); onBack(); }
        catch (err) { setError(errorMessage(err)); if (err instanceof ApiError && err.auth) setShowAuth(true); }
        finally { setConnecting(false); }
      }}>{connecting ? 'Connecting…' : 'Connect Selected Folder'}</button>{onPermanentMountShare && <button className="secondary" disabled={!selectedDevice || !selectedShare || loading || connecting} onClick={() => {
        setConnecting(true); setError('');
        void onPermanentMountShare(selectedDevice, selectedShare).catch(err => setError(errorMessage(err))).finally(() => setConnecting(false));
      }}>Permanent Mount…</button>}<button className="secondary" disabled={connecting} onClick={() => void leave().catch(err => setError(errorMessage(err)))}>Cancel</button><button className="secondary" disabled={connecting} onClick={() => setShowManual(true)}>Manual IP</button></div>
    </footer>
    {showAuth && <CredentialsModal isOpen address={selectedDevice} onClose={() => setShowAuth(false)} onSubmit={async (credentials, remember) => { await selectDevice(selectedDevice, credentials, remember); setShowAuth(false); }} />}
    <Modal isOpen={showManual} onClose={() => setShowManual(false)} title="Find a Device by IP" subtitle="Enter the IPv4 address of the device offering shared folders.">
      <form className="space-y-4" onSubmit={e => { e.preventDefault(); setShowManual(false); void selectDevice(manual.trim()); }}><label className="field-label">IPv4 address<input className="field" autoFocus required value={manual} onChange={e => setManual(e.target.value)} placeholder="192.168.1.150" /></label><div className="dialog-actions"><button className="secondary" type="button" onClick={() => setShowManual(false)}>Cancel</button><button className="primary">Show Folders</button></div></form>
    </Modal>
  </div>;
}
