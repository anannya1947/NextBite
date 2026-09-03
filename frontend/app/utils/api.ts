const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
const DEMO_UID = "demo-user-001";

export interface MacroBreakdown {
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
  sugar_limit_g: number;
  sodium_limit_mg: number;
}

export interface HealthProfile {
  uid: string;
  bmr: number;
  tdee: number;
  target_calories: number;
  activity_level: string;
  avg_daily_steps: number;
  avg_resting_hr: number;
  avg_sleep_hours: number;
  recommended_macros: MacroBreakdown;
  insights: string[];
  calculated_at: string;
}

export interface FitnessSummary {
  user_id: string;
  period_days: number;
  avg_steps: number;
  avg_calories: number;
  avg_sleep_minutes: number;
  avg_resting_hr: number;
  active_days_count: number;
}

export interface FitnessTrend {
  dates: string[];
  steps: number[];
  calories: number[];
  sleep_hours: number[];
  resting_hr: number[];
}

export interface IngredientItem {
  name: string;
  amount_g: number;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
}

export interface MealItem {
  meal_type: "breakfast" | "lunch" | "dinner" | "snack";
  dish_name: string;
  description: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  fiber_g: number;
  prep_time_minutes: number;
  ingredients: IngredientItem[];
  tags: string[];
}

export interface DailyMealPlan {
  day_number: number;
  day_name: string;
  meals: MealItem[];
  total_calories: number;
  total_protein_g: number;
  total_carbs_g: number;
  total_fat_g: number;
  target_calories: number;
  notes?: string;
}

export interface FullMealPlan {
  plan_id: string;
  uid: string;
  duration_days: number;
  goal: string;
  target_calories_per_day: number;
  target_macros: Record<string, number>;
  days: DailyMealPlan[];
  created_at: string;
}

export interface NutritionContext {
  food_name: string;
  serving_size: string;
  calories: number;
  protein_g: number;
  carbs_g: number;
  fat_g: number;
  sugar_g: number;
  sodium_mg: number;
}

export interface FoodQAResponse {
  query: string;
  verdict_summary: string;
  tone_verdict: "encouraging" | "supportive_caution" | "celebratory" | string;
  nutrition_facts?: NutritionContext;
  impact_analysis: string;
  tradeoffs_and_adjustments: string[];
  healthy_alternatives: string[];
  suggested_balance_action: string;
  timestamp: string;
}

function authHeaders(): HeadersInit {
  // Demo-mode header recognized by the backend's dev auth fallback.
  // In production, swap this for a Firebase ID token: `Authorization: Bearer <idToken>`.
  return {
    "Content-Type": "application/json",
    "X-Dev-User-Id": DEMO_UID,
  };
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { ...authHeaders(), ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => apiFetch<{ status: string; service: string; version: string }>("/api/health"),
  getHealthProfile: () => apiFetch<HealthProfile>("/api/health/profile"),
  recalculateHealthProfile: () => apiFetch<HealthProfile>("/api/health/recalculate", { method: "POST" }),
  getFitnessSummary: () => apiFetch<FitnessSummary>("/api/fitness/summary"),
  getFitnessTrends: (days = 14) => apiFetch<FitnessTrend>(`/api/fitness/trends?days=${days}`),
  getLatestPlan: () => apiFetch<FullMealPlan>("/api/plan/latest"),
  generatePlan: (forceNew = false) => apiFetch<FullMealPlan>(`/api/plan/generate?force_new=${forceNew}`, { method: "POST" }),
  askFoodQuestion: (query: string, mealType = "snack", contextPortion = "1 serving") =>
    apiFetch<FoodQAResponse>("/api/voice/ask", {
      method: "POST",
      body: JSON.stringify({ query, meal_type: mealType, context_portion: contextPortion }),
    }),
  getVoiceSuggestions: () => apiFetch<string[]>("/api/voice/suggestions"),
};

export { API_BASE_URL, DEMO_UID };
