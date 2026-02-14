import React from 'react';
import { 
  LayoutDashboard, 
  LineChart, 
  Wallet, 
  History, 
  Settings, 
  ChevronLeft, 
  ChevronRight,
  TrendingUp
} from 'lucide-react';

interface SidebarProps {
  activeTab: string;
  onTabChange: (tab: string) => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

export default function Sidebar({ activeTab, onTabChange, isCollapsed, setIsCollapsed }: SidebarProps) {
  const menuItems = [
    { id: 'recommendation', label: 'Recomendação', icon: LayoutDashboard },
    { id: 'simulator', label: 'Simulador de Compra', icon: LineChart },
    { id: 'portfolio', label: 'Minha Carteira', icon: Wallet },
    { id: 'history', label: 'Histórico', icon: History },
  ];

  return (
    <aside 
      className={`
        fixed left-0 top-0 h-screen bg-surface border-r border-surface-light
        transition-all duration-300 z-50 flex flex-col
        ${isCollapsed ? 'w-20' : 'w-64'}
      `}
    >
      {/* Logo */}
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-linear-to-br from-primary to-primary-light flex items-center justify-center shrink-0">
          <TrendingUp className="w-5 h-5 text-white" />
        </div>
        {!isCollapsed && (
          <span className="font-bold text-xl gradient-text whitespace-nowrap">Smart Invest</span>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 space-y-2 mt-4">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`
                w-full flex items-center gap-3 p-3 rounded-xl transition-all group
                ${isActive 
                  ? 'bg-(--primary-muted) text-primary-light' 
                  : 'text-(--text-secondary) hover:bg-surface-light hover:text-(--text-primary)'}
              `}
              title={isCollapsed ? item.label : ''}
            >
              <Icon className={`w-5 h-5 shrink-0 ${isActive ? 'text-primary-light' : 'group-hover:text-primary'}`} />
              {!isCollapsed && (
                <span className="font-medium whitespace-nowrap">{item.label}</span>
              )}
              {isActive && !isCollapsed && (
                <div className="ml-auto w-1.5 h-1.5 rounded-full bg-primary-light" />
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer / Settings */}
      <div className="p-3 border-t border-surface-light">
        <button
          className="w-full flex items-center gap-3 p-3 rounded-xl text-(--text-secondary) hover:bg-surface-light hover:text-(--text-primary) transition-all"
          onClick={() => onTabChange('settings')}
        >
          <Settings className="w-5 h-5 shrink-0" />
          {!isCollapsed && <span className="font-medium">Configurações</span>}
        </button>
        
        <button 
          onClick={() => setIsCollapsed(!isCollapsed)}
          className="mt-2 w-full flex items-center justify-center p-2 rounded-lg bg-surface-light text-(--text-muted) hover:text-(--text-primary) transition-all"
        >
          {isCollapsed ? <ChevronRight className="w-5 h-5" /> : <ChevronLeft className="w-5 h-5" />}
        </button>
      </div>
    </aside>
  );
}
