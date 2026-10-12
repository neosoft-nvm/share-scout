import { useEffect, useState } from 'react';
import { Modal } from './Modal';
import { desktopCall, errorMessage } from '../services/api';

interface NetworkInfo {
  interface: string;
  address: string;
  subnet: string;
  netmask: string;
  gateways: string[];
}

export function NetworkInfoModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [result, setResult] = useState<NetworkInfo[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => {
    if (!isOpen) return;
    let alive = true;
    setResult(null); setError('');
    void desktopCall<NetworkInfo[]>('network_info')
      .then(value => { if (alive) setResult(value); })
      .catch(err => { if (alive) setError(errorMessage(err)); });
    return () => { alive = false; };
  }, [isOpen]);
  return <Modal isOpen={isOpen} onClose={onClose} title="Local Network Info" subtitle="This computer’s active IPv4 connections">
    <div className="space-y-4">
      {!result && !error && <p role="status">Reading network information…</p>}
      {error && <p role="alert" className="error-message">{error}</p>}
      {result?.length === 0 && <p>No active IPv4 connections found.</p>}
      {result?.map(item => <section key={`${item.interface}/${item.address}`} className="rounded-xl border border-slate-200 p-4 space-y-2 break-words">
        <h3 className="font-semibold">{item.interface}</h3>
        <dl className="text-sm space-y-2">
          <div><dt className="text-slate-500">IP address</dt><dd>{item.address}</dd></div>
          <div><dt className="text-slate-500">Subnet</dt><dd>{item.subnet}</dd></div>
          <div><dt className="text-slate-500">Subnet mask</dt><dd>{item.netmask}</dd></div>
          <div><dt className="text-slate-500">Default gateway</dt><dd>{item.gateways.join(', ') || 'No default gateway configured'}</dd></div>
        </dl>
      </section>)}
      <div className="dialog-actions"><button className="secondary" onClick={onClose}>Close</button></div>
    </div>
  </Modal>;
}
