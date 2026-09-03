"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Footprints,
  Flame,
  Moon,
  HeartPulse,
  CalendarRange,
  Mic,
  Sparkles,
} from "lucide-react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import StatCard from "./components/StatCard";
import { api, FitnessSummary, FitnessTrend, HealthProfile } from "./utils/api";

export default function DashboardPage() {
  const [summary, setSummary] = useState<FitnessSummary | null>(null);
  const [trend, setTrend] = useState<FitnessTrend | null>(null);
  const [health, setHealth] = useState<HealthProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.getFitnessSummary(), api.getFitnessTrends(14), api.getHealthProfile()])
      .then(([s, t, h]) => {
        setSummary(s);
        setTrend(t);
        setHealth(h);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const chartData =
    trend?.dates.map((date, i) => ({
      date,
      steps: trend.steps[i],
      calories: trend.calories[i],
    })) ?? [];

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8">
        <p className="mb-2 flex items-center gap-1.5 text-sm font-medium text-emerald-400">
          <Sparkles size={14} /> Powered by Gemini + BigQuery + Firestore
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-white sm:text-4xl">
          Welcome back, Alex 👋
        </h1>
        <p className="mt-2 max-w-2xl text-zinc-400">
          Here&apos;s a snapshot of your fitness trends, grounded in real Fitbit sensor data,
          and your personalized nutrition targets.
        </p>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          Couldn&apos;t reach the NextBite API: {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Avg Daily Steps"
          value={loading ? "…" : summary?.avg_steps.toLocaleString() ?? "—"}
          icon={Footprints}
          accent="from-emerald-400 to-teal-500"
          sublabel={`over ${summary?.period_days ?? 30} days`}
        />
        <StatCard
          label="Calories Burned"
          value={loading ? "…" : summary?.avg_calories.toLocaleString() ?? "—"}
          unit="kcal/day"
          icon={Flame}
          accent="from-orange-400 to-red-500"
        />
        <StatCard
          label="Avg Sleep"
          value={loading ? "…" : ((summary?.avg_sleep_minutes ?? 0) / 60).toFixed(1)}
          unit="hrs/night"
          icon={Moon}
          accent="from-indigo-400 to-violet-500"
        />
        <StatCard
          label="Resting Heart Rate"
          value={loading ? "…" : summary?.avg_resting_hr ?? "—"}
          unit="bpm"
          icon={HeartPulse}
          accent="from-pink-400 to-rose-500"
        />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="glass-card rounded-2xl p-6 lg:col-span-2">
          <h2 className="mb-4 text-lg font-semibold text-white">14-Day Activity Trend</h2>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                <XAxis dataKey="date" stroke="#71717a" fontSize={11} tickLine={false} />
                <YAxis stroke="#71717a" fontSize={11} tickLine={false} />
                <Tooltip
                  contentStyle={{
                    background: "#0f1115",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: 12,
                  }}
                  labelStyle={{ color: "#e5e5e5" }}
                />
                <Line type="monotone" dataKey="steps" stroke="#34d399" strokeWidth={2} dot={false} name="Steps" />
                <Line type="monotone" dataKey="calories" stroke="#fb923c" strokeWidth={2} dot={false} name="Calories" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="glass-card rounded-2xl p-6">
          <h2 className="mb-4 text-lg font-semibold text-white">Your Nutrition Targets</h2>
          {health ? (
            <div className="space-y-3">
              <div className="flex items-center justify-between rounded-xl bg-white/5 px-4 py-3">
                <span className="text-sm text-zinc-400">Daily Target</span>
                <span className="font-semibold text-emerald-400">{health.target_calories} kcal</span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center">
                <div className="rounded-xl bg-white/5 px-2 py-3">
                  <p className="text-lg font-bold text-white">{health.recommended_macros.protein_g}g</p>
                  <p className="text-xs text-zinc-500">Protein</p>
                </div>
                <div className="rounded-xl bg-white/5 px-2 py-3">
                  <p className="text-lg font-bold text-white">{health.recommended_macros.carbs_g}g</p>
                  <p className="text-xs text-zinc-500">Carbs</p>
                </div>
                <div className="rounded-xl bg-white/5 px-2 py-3">
                  <p className="text-lg font-bold text-white">{health.recommended_macros.fat_g}g</p>
                  <p className="text-xs text-zinc-500">Fat</p>
                </div>
              </div>
              <p className="pt-1 text-xs leading-relaxed text-zinc-500">{health.insights[0]}</p>
            </div>
          ) : (
            <p className="text-sm text-zinc-500">Calculating from your BigQuery fitness data…</p>
          )}
        </div>
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Link
          href="/plan"
          className="glass-card group flex items-center justify-between rounded-2xl p-6 transition-all hover:border-emerald-400/40"
        >
          <div>
            <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
              <CalendarRange size={18} className="text-emerald-400" /> Generate Meal Plan
            </h3>
            <p className="mt-1 text-sm text-zinc-400">Get a personalized 14-day meal plan matched to your TDEE.</p>
          </div>
          <span className="text-2xl text-zinc-500 transition-transform group-hover:translate-x-1">→</span>
        </Link>
        <Link
          href="/voice"
          className="glass-card group flex items-center justify-between rounded-2xl p-6 transition-all hover:border-teal-400/40"
        >
          <div>
            <h3 className="flex items-center gap-2 text-lg font-semibold text-white">
              <Mic size={18} className="text-teal-400" /> Ask About Food
            </h3>
            <p className="mt-1 text-sm text-zinc-400">&quot;Is pizza okay for lunch?&quot; — get grounded, judgment-free answers.</p>
          </div>
          <span className="text-2xl text-zinc-500 transition-transform group-hover:translate-x-1">→</span>
        </Link>
      </div>
    </div>
  );
}
