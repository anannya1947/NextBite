import { LucideIcon } from "lucide-react";

interface StatCardProps {
  label: string;
  value: string | number;
  unit?: string;
  icon: LucideIcon;
  accent?: string;
  sublabel?: string;
}

export default function StatCard({ label, value, unit, icon: Icon, accent = "from-emerald-400 to-teal-500", sublabel }: StatCardProps) {
  return (
    <div className="glass-card rounded-2xl p-5 transition-transform hover:-translate-y-0.5">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-zinc-400">{label}</span>
        <span className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${accent}`}>
          <Icon size={16} className="text-black" />
        </span>
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-3xl font-bold tracking-tight text-white">{value}</span>
        {unit && <span className="text-sm text-zinc-400">{unit}</span>}
      </div>
      {sublabel && <p className="mt-1 text-xs text-zinc-500">{sublabel}</p>}
    </div>
  );
}
