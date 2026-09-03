"use client";

import { useEffect, useRef, useState } from "react";
import { Mic, Send, Sparkles, ThumbsUp, AlertCircle, PartyPopper } from "lucide-react";
import { api, FoodQAResponse } from "../utils/api";

type ChatEntry = { role: "user" | "assistant"; response?: FoodQAResponse; text?: string };

const TONE_STYLE: Record<string, { icon: typeof ThumbsUp; color: string }> = {
  encouraging: { icon: ThumbsUp, color: "text-emerald-400" },
  supportive_caution: { icon: AlertCircle, color: "text-amber-400" },
  celebratory: { icon: PartyPopper, color: "text-pink-400" },
};

export default function VoicePage() {
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const [asking, setAsking] = useState(false);
  const [listening, setListening] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.getVoiceSuggestions().then(setSuggestions).catch(() => {});
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [history]);

  const ask = async (query: string) => {
    if (!query.trim() || asking) return;
    setHistory((h) => [...h, { role: "user", text: query }]);
    setInput("");
    setAsking(true);
    try {
      const res = await api.askFoodQuestion(query);
      setHistory((h) => [...h, { role: "assistant", response: res }]);
    } catch (e) {
      setHistory((h) => [
        ...h,
        {
          role: "assistant",
          text: `Sorry, I couldn't reach the nutrition service: ${(e as Error).message}`,
        },
      ]);
    } finally {
      setAsking(false);
    }
  };

  const startListening = () => {
    const SpeechRecognition =
      (window as unknown as { webkitSpeechRecognition?: unknown; SpeechRecognition?: unknown })
        .SpeechRecognition ||
      (window as unknown as { webkitSpeechRecognition?: unknown }).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Voice recognition isn't supported in this browser. Try typing your question instead.");
      return;
    }
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const recognition = new (SpeechRecognition as any)();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.onstart = () => setListening(true);
    recognition.onend = () => setListening(false);
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      ask(transcript);
    };
    recognition.start();
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col px-6 py-10">
      <div className="mb-6 text-center">
        <p className="mb-2 flex items-center justify-center gap-1.5 text-sm font-medium text-teal-400">
          <Sparkles size={14} /> Grounded by USDA FoodData via BigQuery RAG
        </p>
        <h1 className="text-3xl font-bold tracking-tight text-white">Ask About Any Food</h1>
        <p className="mt-2 text-zinc-400">
          No blunt yes/no. Just honest, contextual guidance based on your daily budget.
        </p>
      </div>

      <div className="mb-4 flex justify-center">
        <button
          onClick={startListening}
          className={`relative flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-emerald-400 to-teal-600 text-black shadow-xl shadow-emerald-500/20 transition-transform hover:scale-105 ${
            listening ? "mic-pulse" : ""
          }`}
        >
          <Mic size={28} />
        </button>
      </div>
      <p className="mb-6 text-center text-xs text-zinc-500">
        {listening ? "Listening…" : "Tap to speak, or type your question below"}
      </p>

      {history.length === 0 && (
        <div className="mb-6 flex flex-wrap justify-center gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              onClick={() => ask(s)}
              className="glass-card rounded-full px-4 py-2 text-xs text-zinc-300 transition-colors hover:text-white hover:border-emerald-400/40"
            >
              {s}
            </button>
          ))}
        </div>
      )}

      <div ref={scrollRef} className="mb-4 flex-1 space-y-4 overflow-y-auto" style={{ maxHeight: "50vh" }}>
        {history.map((entry, i) => {
          if (entry.role === "user") {
            return (
              <div key={i} className="flex justify-end">
                <div className="max-w-[85%] rounded-2xl bg-gradient-to-r from-emerald-400 to-teal-500 px-4 py-2.5 text-sm font-medium text-black">
                  {entry.text}
                </div>
              </div>
            );
          }
          if (entry.text && !entry.response) {
            return (
              <div key={i} className="flex justify-start">
                <div className="max-w-[85%] rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-2.5 text-sm text-red-300">
                  {entry.text}
                </div>
              </div>
            );
          }
          const res = entry.response!;
          const tone = TONE_STYLE[res.tone_verdict] ?? TONE_STYLE.encouraging;
          const ToneIcon = tone.icon;
          return (
            <div key={i} className="glass-card rounded-2xl p-5">
              <div className={`mb-2 flex items-center gap-2 font-semibold ${tone.color}`}>
                <ToneIcon size={16} />
                {res.verdict_summary}
              </div>
              <p className="text-sm leading-relaxed text-zinc-300">{res.impact_analysis}</p>

              {res.nutrition_facts && (
                <div className="mt-3 flex flex-wrap gap-2 text-[11px]">
                  <span className="rounded-full bg-white/5 px-2.5 py-1 text-zinc-400">
                    {res.nutrition_facts.food_name} · {res.nutrition_facts.serving_size}
                  </span>
                  <span className="rounded-full bg-emerald-400/10 px-2.5 py-1 text-emerald-300">
                    {res.nutrition_facts.calories} kcal
                  </span>
                  <span className="rounded-full bg-blue-400/10 px-2.5 py-1 text-blue-300">
                    P {res.nutrition_facts.protein_g}g
                  </span>
                  <span className="rounded-full bg-amber-400/10 px-2.5 py-1 text-amber-300">
                    C {res.nutrition_facts.carbs_g}g
                  </span>
                  <span className="rounded-full bg-rose-400/10 px-2.5 py-1 text-rose-300">
                    F {res.nutrition_facts.fat_g}g
                  </span>
                </div>
              )}

              {res.tradeoffs_and_adjustments.length > 0 && (
                <ul className="mt-3 space-y-1 text-sm text-zinc-400">
                  {res.tradeoffs_and_adjustments.map((t, j) => (
                    <li key={j} className="flex gap-2">
                      <span className="text-emerald-400">•</span> {t}
                    </li>
                  ))}
                </ul>
              )}

              {res.healthy_alternatives.length > 0 && (
                <div className="mt-3">
                  <p className="text-xs font-medium text-zinc-500">Alternatives</p>
                  <div className="mt-1 flex flex-wrap gap-1.5">
                    {res.healthy_alternatives.map((a, j) => (
                      <span key={j} className="rounded-full bg-teal-400/10 px-2.5 py-1 text-[11px] text-teal-300">
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <p className="mt-3 border-t border-white/10 pt-3 text-xs italic text-zinc-500">
                💡 {res.suggested_balance_action}
              </p>
            </div>
          );
        })}
        {asking && <p className="text-sm text-zinc-500">NextBite is thinking…</p>}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          ask(input);
        }}
        className="flex items-center gap-2 rounded-full border border-white/10 bg-white/5 p-1.5 pl-4"
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="e.g. Is a slice of pepperoni pizza okay for dinner?"
          className="flex-1 bg-transparent text-sm text-white placeholder:text-zinc-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={asking || !input.trim()}
          className="flex h-9 w-9 items-center justify-center rounded-full bg-gradient-to-r from-emerald-400 to-teal-500 text-black disabled:opacity-40"
        >
          <Send size={15} />
        </button>
      </form>
    </div>
  );
}
