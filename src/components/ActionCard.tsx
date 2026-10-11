import React from 'react';

interface ActionCardProps {
  icon: React.ReactNode;
  title: string;
  onAction: () => void;
  accent?: boolean;
}

export const ActionCard: React.FC<ActionCardProps> = ({
  icon,
  title,
  onAction,
  accent = false,
}) => {
  return (
    <div
      onClick={onAction}
      className={`group flex flex-col items-center justify-center p-8 rounded-2xl bg-white border transition-all duration-200 cursor-pointer shadow-xs hover:shadow-md min-h-[140px] ${
        accent
          ? 'border-slate-200 hover:border-indigo-400'
          : 'border-slate-200 hover:border-indigo-400'
      }`}
    >
      <div className="flex items-center justify-center mb-4 transition-transform group-hover:scale-105">
        {icon}
      </div>
      <h3 className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors text-center">
        {title}
      </h3>
    </div>
  );
};
