"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Salad, LayoutDashboard, CalendarRange, Mic } from "lucide-react";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/plan", label: "Meal Plan", icon: CalendarRange },
  { href: "/voice", label: "Ask About Food", icon: Mic },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-white/10 bg-black/40 backdrop-blur-xl">
      <nav className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-semibold text-white">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-emerald-400 to-teal-600">
            <Salad size={18} className="text-black" />
          </span>
          NextBite
        </Link>
        <div className="flex items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1">
          {links.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-medium transition-all ${
                  active
                    ? "bg-gradient-to-r from-emerald-400 to-teal-500 text-black shadow-lg shadow-emerald-500/20"
                    : "text-zinc-300 hover:text-white hover:bg-white/5"
                }`}
              >
                <Icon size={15} />
                <span className="hidden sm:inline">{label}</span>
              </Link>
            );
          })}
        </div>
        <div className="hidden items-center gap-2 rounded-full bg-white/5 px-3 py-1.5 text-sm text-zinc-300 sm:flex">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
          Demo Mode &middot; Alex Demo
        </div>
      </nav>
    </header>
  );
}
