"use client";

import { useEffect, useState } from "react";
import { RefreshCw, Clock, Flame, Sunrise, Sun, Moon as MoonIcon, Cookie } from "lucide-react";
import { api, FullMealPlan, MealItem } from "../utils/api";

const MEAL_ICONS: Record<string, typeof Sunrise> = {
  breakfast: Sunrise,
  lunch: Sun,
  dinner: MoonIcon,
  snack: Cookie,
};

function MealCard({ meal }: { meal: MealItem }) {
  const Icon = MEAL_ICONS[meal.meal_type] ?? Cookie;
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.03] p-4">
      <div className="mb-2 flex items-center gap-2">
        <Icon size={14} className="text-emerald-400" />
        <span className="text-xs font-semibold uppercase tracking-wide text-zinc-500">{meal.meal_type}</span>
      </div>
      <h4 className="font-medium text-white">{meal.dish_name}</h4>
      <p className="mt-1 text-xs leading-relaxed text-zinc-500">{meal.description}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        <span className="rounded-full bg-emerald-400/10 px-2 py-0.5 text-[11px] font-medium text-emerald-300">
          {meal.calories} kcal
        </span>
        <span className="rounded-full bg-blue-400/10 px-2 py-0.5 text-[11px] font-medium text-blue-300">
          P {meal.protein_g}g
        </span>
        <span className="rounded-full bg-amber-400/10 px-2 py-0.5 text-[11px] font-medium text-amber-300">
          C {meal.carbs_g}g
        </span>
        <span className="rounded-full bg-rose-400/10 px-2 py-0.5 text-[11px] font-medium text-rose-300">
          F {meal.fat_g}g
        </span>
      </div>
      <div className="mt-2 flex items-center gap-1 text-[11px] text-zinc-600">
        <Clock size={11} /> {meal.prep_time_minutes} min
      </div>
    </div>
  );
}

export default function PlanPage() {
  const [plan, setPlan] = useState<FullMealPlan | null>(null);
  const [loading, setLoading] = useState(true);
  const [regenerating, setRegenerating] = useState(false);
  const [activeDay, setActiveDay] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const load = () => {
    setLoading(true);
    api
      .getLatestPlan()
      .then(setPlan)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const regenerate = async () => {
    setRegenerating(true);
    try {
      const fresh = await api.generatePlan(true);
      setPlan(fresh);
      setActiveDay(1);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRegenerating(false);
    }
  };

  const day = plan?.days.find((d) => d.day_number === activeDay);

  return (
    <div className="mx-auto max-w-6xl px-6 py-10">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white">Your 14-Day Meal Plan</h1>
          <p className="mt-2 text-zinc-400">
            {plan
              ? `Goal: ${plan.goal.replace("_", " ")} · Target ${plan.target_calories_per_day} kcal/day`
              : "Generating a plan tailored to your TDEE and macros…"}
          </p>
        </div>
        <button
          onClick={regenerate}
          disabled={regenerating}
          className="flex items-center gap-2 rounded-full bg-gradient-to-r from-emerald-400 to-teal-500 px-5 py-2.5 text-sm font-semibold text-black transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          <RefreshCw size={15} className={regenerating ? "animate-spin" : ""} />
          {regenerating ? "Regenerating…" : "Regenerate Plan"}
        </button>
      </div>

      {error && (
        <div className="mb-6 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      {loading ? (
        <p className="text-zinc-500">Loading your plan…</p>
      ) : plan ? (
        <>
          <div className="mb-6 flex gap-2 overflow-x-auto pb-2">
            {plan.days.map((d) => (
              <button
                key={d.day_number}
                onClick={() => setActiveDay(d.day_number)}
                className={`flex-shrink-0 rounded-xl px-4 py-2.5 text-sm font-medium transition-all ${
                  activeDay === d.day_number
                    ? "bg-gradient-to-r from-emerald-400 to-teal-500 text-black shadow-lg shadow-emerald-500/20"
                    : "glass-card text-zinc-300 hover:text-white"
                }`}
              >
                {d.day_name}
              </button>
            ))}
          </div>

          {day && (
            <div className="glass-card rounded-2xl p-6">
              <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
                <h2 className="text-xl font-semibold text-white">{day.day_name}</h2>
                <div className="flex items-center gap-2 rounded-full bg-white/5 px-3 py-1.5 text-sm text-zinc-300">
                  <Flame size={14} className="text-orange-400" />
                  {day.total_calories} / {day.target_calories} kcal
                </div>
              </div>
              {day.notes && <p className="mb-4 text-sm italic text-zinc-500">{day.notes}</p>}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {day.meals.map((m, i) => (
                  <MealCard key={i} meal={m} />
                ))}
              </div>
              <div className="mt-5 grid grid-cols-3 gap-3 border-t border-white/10 pt-4 text-center">
                <div>
                  <p className="text-lg font-bold text-white">{day.total_protein_g}g</p>
                  <p className="text-xs text-zinc-500">Total Protein</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-white">{day.total_carbs_g}g</p>
                  <p className="text-xs text-zinc-500">Total Carbs</p>
                </div>
                <div>
                  <p className="text-lg font-bold text-white">{day.total_fat_g}g</p>
                  <p className="text-xs text-zinc-500">Total Fat</p>
                </div>
              </div>
            </div>
          )}
        </>
      ) : (
        <p className="text-zinc-500">No plan found.</p>
      )}
    </div>
  );
}
