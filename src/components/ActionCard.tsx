import React from 'react';

interface ActionCardProps {
  icon: React.ReactNode;
  title: string;
  description: string;
  buttonText: string;
  onAction: () => void;
  accent?: boolean;
}

export const ActionCard: React.FC<ActionCardProps> = ({
  icon,
  title,
  description,
  buttonText,
  onAction,
  accent = false,
}) => {
  return (
    <div
      onClick={onAction}
      className={`group relative flex flex-col justify-between p-5 rounded-2xl bg-white border transition-all duration-200 cursor-pointer shadow-xs hover:shadow-md ${
        accent
          ? 'border-indigo-200 hover:border-indigo-500 hover:ring-2 hover:ring-indigo-100'
          : 'border-slate-200 hover:border-slate-300'
      }`}
    >
      <div className="flex flex-col items-center text-center">
        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center mb-3 transition-colors ${
            accent ? 'bg-indigo-50 text-indigo-600' : 'bg-slate-100 text-slate-700'
          }`}
        >
          {icon}
        </div>
        <h3 className="text-sm font-bold text-slate-900 group-hover:text-indigo-600 transition-colors">
          {title}
        </h3>
        <p className="mt-1 text-xs text-slate-500 leading-relaxed max-w-[200px]">
          {description}
        </p>
      </div>

      <div className="mt-4 pt-2">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onAction();
          }}
          className={`w-full py-2 px-3 rounded-lg text-xs font-semibold transition-all duration-150 ${
            accent
              ? 'bg-indigo-600 hover:bg-indigo-700 text-white shadow-xs'
              : 'bg-slate-100 hover:bg-slate-200 text-slate-800'
          }`}
        >
          {buttonText}
        </button>
      </div>
    </div>
  );
};
