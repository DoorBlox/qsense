"use client";

import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

type LiveStatus = {
  id: number;
  updated_at: string;
  meal_period: string;
  queue_count: number;
  queue_status: string;
  trend: string;
  served: number;
  avg_wait_seconds: number;
  throughput_per_min: number;
  camera_online: boolean;
};

export default function Home() {
  const [status, setStatus] = useState<LiveStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadStatus() {
    const { data, error } = await supabase
      .from("live_status")
      .select("*")
      .eq("id", 1)
      .single();

    if (error) {
      console.error(error);
      setError(error.message);
      setLoading(false);
      return;
    }

    setStatus(data);
    setError(null);
    setLoading(false);
  }

  useEffect(() => {
    loadStatus();

    const timer = setInterval(() => {
      loadStatus();
    }, 3000);

    return () => clearInterval(timer);
  }, []);

  if (loading) {
    return (
      <main className="min-h-screen bg-zinc-950 text-white flex items-center justify-center">
        <p className="text-zinc-400">Loading Q-SENSE...</p>
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-zinc-950 text-white flex items-center justify-center px-6">
        <div className="text-center">
          <h1 className="text-4xl font-bold mb-4">Q-SENSE</h1>

          <p className="text-red-400">
            Supabase error: {error}
          </p>
        </div>
      </main>
    );
  }

  if (!status) {
    return null;
  }

  const lastUpdate = new Date(status.updated_at);

  const ageSeconds = Math.max(
    0,
    (Date.now() - lastUpdate.getTime()) / 1000
  );

  // Heartbeat safety:
  // even if camera_online accidentally remains true,
  // data older than 20 sec means camera is considered offline.
  const actuallyOnline =
    status.camera_online && ageSeconds < 20;

  const waitMinutes =
    status.avg_wait_seconds / 60;

  const trendSymbol =
    status.trend === "rising"
      ? "↑"
      : status.trend === "falling"
      ? "↓"
      : "→";

  const queueMessage =
    !actuallyOnline
      ? "Camera offline"
      : status.queue_count === 0
      ? "No queue detected"
      : status.queue_count <= 3
      ? "Short queue"
      : status.queue_count <= 7
      ? "Moderate queue"
      : "Busy queue";

  return (
    <main className="min-h-screen bg-zinc-950 text-white px-5 py-8 sm:px-8 sm:py-10">
      <div className="max-w-6xl mx-auto">

        {/* HEADER */}
        <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-6 mb-10">

          <div>
            <p className="text-xs sm:text-sm tracking-[0.3em] text-zinc-500 uppercase">
              Queue Sensing and Evaluation System
            </p>

            <h1 className="text-4xl sm:text-5xl font-bold mt-2">
              Q-SENSE
            </h1>

            <p className="text-zinc-500 mt-2">
              Cafeteria Queue Monitoring
            </p>
          </div>

          <div
            className={`w-fit px-4 py-2 rounded-full text-sm font-semibold border ${
              actuallyOnline
                ? "bg-green-500/10 text-green-400 border-green-500/20"
                : "bg-red-500/10 text-red-400 border-red-500/20"
            }`}
          >
            {actuallyOnline
              ? "● CAMERA ONLINE"
              : "● CAMERA OFFLINE"}
          </div>

        </header>


        {/* MAIN QUEUE */}
        <section className="grid lg:grid-cols-3 gap-5 mb-5">

          <div className="lg:col-span-2 rounded-3xl border border-zinc-800 bg-zinc-900 p-7 sm:p-9">

            <p className="text-zinc-400">
              Current Queue
            </p>

            <div className="flex items-end gap-6 mt-4">

              <span className="text-7xl sm:text-9xl font-bold leading-none">
                {actuallyOnline
                  ? status.queue_count
                  : "—"}
              </span>

              <div className="pb-2">

                <p className="text-xl sm:text-2xl font-medium">
                  {queueMessage}
                </p>

                {actuallyOnline && (
                  <p className="text-zinc-400 capitalize mt-1">
                    {trendSymbol} {status.trend}
                  </p>
                )}

              </div>

            </div>

          </div>


          {/* MEAL PERIOD */}
          <div className="rounded-3xl border border-zinc-800 bg-zinc-900 p-7 sm:p-9">

            <p className="text-zinc-400">
              Meal Period
            </p>

            <p className="text-3xl font-semibold capitalize mt-4">
              {status.meal_period.replaceAll("_", " ")}
            </p>

            {status.meal_period === "test" && (
              <p className="mt-3 text-yellow-400 text-sm">
                Test mode
              </p>
            )}

          </div>

        </section>


        {/* METRICS */}
        <section className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">

          <MetricCard
            title="Average Wait"
            value={
              !actuallyOnline
                ? "—"
                : waitMinutes >= 1
                ? `${waitMinutes.toFixed(1)} min`
                : `${status.avg_wait_seconds.toFixed(0)} sec`
            }
          />

          <MetricCard
            title="Throughput"
            value={
              actuallyOnline
                ? `${status.throughput_per_min}/min`
                : "—"
            }
          />

          <MetricCard
            title="Served"
            value={
              actuallyOnline
                ? status.served.toString()
                : "—"
            }
          />

        </section>


        {/* HEARTBEAT */}
        <section className="mt-5 rounded-3xl border border-zinc-800 bg-zinc-900 p-6">

          <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-4">

            <div>

              <p className="text-zinc-500 text-sm">
                Last camera heartbeat
              </p>

              <p className="mt-1">
                {lastUpdate.toLocaleString()}
              </p>

            </div>


            <div className="sm:text-right">

              <p className="text-zinc-500 text-sm">
                Data age
              </p>

              <p
                className={`mt-1 ${
                  ageSeconds >= 20
                    ? "text-red-400"
                    : "text-zinc-200"
                }`}
              >
                {Math.round(ageSeconds)} sec
              </p>

            </div>

          </div>

        </section>


        {/* PRIVACY */}
        <section className="mt-5 rounded-3xl border border-zinc-800/70 p-6">

          <p className="text-sm text-zinc-500">
            Q-SENSE analyzes queue activity using anonymous
            object detection and temporary tracking IDs.
            Facial recognition is not used.
          </p>

        </section>


        <footer className="mt-10 pb-4 text-xs text-zinc-600">
          Q-SENSE · Proof of Concept
        </footer>

      </div>
    </main>
  );
}


function MetricCard({
  title,
  value,
}: {
  title: string;
  value: string;
}) {
  return (
    <div className="rounded-3xl border border-zinc-800 bg-zinc-900 p-6">

      <p className="text-zinc-400">
        {title}
      </p>

      <p className="text-3xl font-semibold mt-3">
        {value}
      </p>

    </div>
  );
}