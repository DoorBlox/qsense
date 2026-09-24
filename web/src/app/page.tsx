"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { supabase } from "@/lib/supabase";

import {
  Activity,
  BarChart3,
  Camera,
  CheckCircle2,
  ChevronRight,
  Clock3,
  Database,
  Gauge,
  History,
  Info,
  Menu as MenuIcon,
  ShieldCheck,
  TrendingDown,
  TrendingUp,
  Users,
  Wifi,
  WifiOff,
} from "lucide-react";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";


/* =========================================================
   TYPES
========================================================= */

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

type Snapshot = {
  id: number;
  recorded_at: string;
  session_id: string;
  meal_period: string;
  queue_count: number;
  throughput_per_min: number;
};

type Meal = {
  id: number;
  meal_date: string;
  meal_period: string;
  staple: string | null;
  animal_protein: string | null;
  plant_protein: string | null;
  vegetable: string | null;
  fruit: string | null;
  drink: string | null;
  other: string | null;
};

type Validation = {
  id: number;
  recorded_at: string;
  session_id: string | null;
  actual_count: number;
  qsense_count: number;
  absolute_error: number | null;
};

type LivePoint = {
  time: string;
  count: number;
};

type Tab =
  | "live"
  | "history"
  | "menu"
  | "validation";


/* =========================================================
   MAIN
========================================================= */

export default function Home() {
  const [status, setStatus] = useState<LiveStatus | null>(null);

  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [validation, setValidation] = useState<Validation[]>([]);

  const [liveHistory, setLiveHistory] = useState<LivePoint[]>([]);

  const [tab, setTab] = useState<Tab>("live");
  const [range, setRange] = useState<"24h" | "7d" | "30d">("24h");

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [nowMs, setNowMs] = useState(Date.now());


  /* =======================================================
     LIVE STATUS
  ======================================================= */

  const loadLiveStatus = useCallback(async () => {
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

    const newStatus = data as LiveStatus;

    setStatus(newStatus);

    setLiveHistory((previous) => {
      const point: LivePoint = {
        time: new Date().toLocaleTimeString([], {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        }),
        count: newStatus.queue_count,
      };

      return [...previous, point].slice(-50);
    });

    setError(null);
    setLoading(false);
  }, []);


  /* =======================================================
     HISTORICAL DATA
  ======================================================= */

  const loadSnapshots = useCallback(async () => {
    let hours = 24;

    if (range === "7d") hours = 24 * 7;
    if (range === "30d") hours = 24 * 30;

    const since = new Date(
      Date.now() - hours * 60 * 60 * 1000
    ).toISOString();

    const { data, error } = await supabase
      .from("queue_snapshots")
      .select("*")
      .gte("recorded_at", since)
      .order("recorded_at", { ascending: true })
      .limit(3000);

    if (!error && data) {
      setSnapshots(data as Snapshot[]);
    }
  }, [range]);


  /* =======================================================
     MENU DATA
  ======================================================= */

  const loadMeals = useCallback(async () => {
    const { data, error } = await supabase
      .from("meal_log")
      .select("*")
      .order("meal_date", { ascending: false })
      .limit(30);

    if (!error && data) {
      setMeals(data as Meal[]);
    }
  }, []);


  /* =======================================================
     VALIDATION DATA
  ======================================================= */

  const loadValidation = useCallback(async () => {
    const { data, error } = await supabase
      .from("manual_validation")
      .select("*")
      .order("recorded_at", { ascending: false })
      .limit(500);

    if (!error && data) {
      setValidation(data as Validation[]);
    }
  }, []);


  /* =======================================================
     POLLING
  ======================================================= */

  useEffect(() => {
    loadLiveStatus();
    loadMeals();
    loadValidation();
  }, [
    loadLiveStatus,
    loadMeals,
    loadValidation,
  ]);

  useEffect(() => {
    loadSnapshots();
  }, [loadSnapshots]);

  useEffect(() => {
    const liveTimer = setInterval(loadLiveStatus, 3000);

    return () => clearInterval(liveTimer);
  }, [loadLiveStatus]);

  useEffect(() => {
    const clockTimer = setInterval(() => {
      setNowMs(Date.now());
    }, 1000);

    return () => clearInterval(clockTimer);
  }, []);


  /* =======================================================
     DERIVED LIVE VALUES
  ======================================================= */

  const lastUpdate = status
    ? new Date(status.updated_at)
    : new Date();

  const ageSeconds = Math.max(
    0,
    (nowMs - lastUpdate.getTime()) / 1000
  );

  const actuallyOnline =
    Boolean(status?.camera_online) &&
    ageSeconds < 20;

  const trendIcon =
    status?.trend === "rising" ? (
      <TrendingUp size={18} />
    ) : status?.trend === "falling" ? (
      <TrendingDown size={18} />
    ) : (
      <Activity size={18} />
    );


  /* =======================================================
     HISTORY ANALYTICS
  ======================================================= */

  const historyStats = useMemo(() => {
    if (snapshots.length === 0) {
      return {
        average: 0,
        peak: 0,
        averageThroughput: 0,
        observations: 0,
      };
    }

    const queueValues = snapshots.map(
      (item) => item.queue_count
    );

    const throughputValues = snapshots.map(
      (item) => item.throughput_per_min
    );

    return {
      average:
        queueValues.reduce((a, b) => a + b, 0) /
        queueValues.length,

      peak: Math.max(...queueValues),

      averageThroughput:
        throughputValues.reduce((a, b) => a + b, 0) /
        throughputValues.length,

      observations: snapshots.length,
    };
  }, [snapshots]);


  const historyChartData = useMemo(() => {
    if (snapshots.length <= 300) {
      return snapshots;
    }

    const step = Math.ceil(
      snapshots.length / 300
    );

    return snapshots.filter(
      (_, index) => index % step === 0
    );
  }, [snapshots]);


  /* =======================================================
     VALIDATION ANALYTICS
  ======================================================= */

  const validationStats = useMemo(() => {
    if (validation.length === 0) {
      return null;
    }

    const errors = validation.map(
      (row) =>
        row.qsense_count - row.actual_count
    );

    const absErrors = errors.map(Math.abs);

    const mae =
      absErrors.reduce((a, b) => a + b, 0) /
      absErrors.length;

    const rmse = Math.sqrt(
      errors
        .map((value) => value * value)
        .reduce((a, b) => a + b, 0) /
        errors.length
    );

    const bias =
      errors.reduce((a, b) => a + b, 0) /
      errors.length;

    const exact =
      (absErrors.filter((value) => value === 0)
        .length /
        absErrors.length) *
      100;

    const withinOne =
      (absErrors.filter((value) => value <= 1)
        .length /
        absErrors.length) *
      100;

    return {
      n: validation.length,
      mae,
      rmse,
      bias,
      exact,
      withinOne,
    };
  }, [validation]);


  /* =======================================================
     CURRENT / LATEST MENU
  ======================================================= */

  const latestMeal =
    meals.length > 0 ? meals[0] : null;


  /* =======================================================
     LOADING / ERROR
  ======================================================= */

  if (loading) {
    return (
      <main className="min-h-screen bg-[#07090d] text-white flex items-center justify-center">
        <div className="text-center">
          <Activity
            className="mx-auto mb-4 animate-pulse"
            size={36}
          />
          <p className="text-zinc-400">
            Connecting to Q-SENSE...
          </p>
        </div>
      </main>
    );
  }


  if (error) {
    return (
      <main className="min-h-screen bg-[#07090d] text-white flex items-center justify-center px-6">
        <div className="max-w-lg text-center">
          <h1 className="text-4xl font-black">
            Q-SENSE
          </h1>

          <p className="text-red-400 mt-5">
            {error}
          </p>
        </div>
      </main>
    );
  }


  if (!status) {
    return null;
  }


  /* =======================================================
     PAGE
  ======================================================= */

  return (
    <main className="min-h-screen bg-[#07090d] text-zinc-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8">

        {/* =================================================
            HEADER
        ================================================= */}

        <header className="mb-8">

          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">

            <div>
              <div className="flex items-center gap-3">

                <div className="w-11 h-11 rounded-2xl bg-white text-black flex items-center justify-center">
                  <Activity size={24} />
                </div>

                <div>
                  <h1 className="text-3xl sm:text-4xl font-black tracking-tight">
                    Q-SENSE
                  </h1>

                  <p className="text-zinc-500 text-sm">
                    Queue Sensing & Evaluation System
                  </p>
                </div>

              </div>
            </div>


            <div className="flex flex-wrap gap-3">

              <StatusPill
                online={actuallyOnline}
              />

              <div className="px-4 py-2 rounded-full border border-zinc-800 bg-zinc-900 text-sm capitalize">
                {status.meal_period.replaceAll("_", " ")}
              </div>

              {status.meal_period === "test" && (
                <div className="px-4 py-2 rounded-full border border-yellow-800/60 bg-yellow-500/10 text-yellow-300 text-sm">
                  TEST MODE
                </div>
              )}

            </div>

          </div>

        </header>


        {/* =================================================
            NAVIGATION
        ================================================= */}

        <nav className="flex overflow-x-auto gap-2 p-1 bg-zinc-900/70 rounded-2xl border border-zinc-800 mb-7">

          <NavButton
            active={tab === "live"}
            icon={<Activity size={17} />}
            label="Live"
            onClick={() => setTab("live")}
          />

          <NavButton
            active={tab === "history"}
            icon={<History size={17} />}
            label="History"
            onClick={() => setTab("history")}
          />

          <NavButton
            active={tab === "menu"}
            icon={<MenuIcon size={17} />}
            label="Menu"
            onClick={() => setTab("menu")}
          />

          <NavButton
            active={tab === "validation"}
            icon={<ShieldCheck size={17} />}
            label="Validation"
            onClick={() => setTab("validation")}
          />

        </nav>


        {/* =================================================
            LIVE TAB
        ================================================= */}

        {tab === "live" && (
          <div className="space-y-5">

            <section className="grid lg:grid-cols-3 gap-5">

              {/* QUEUE HERO */}

              <div className="lg:col-span-2 rounded-[28px] border border-zinc-800 bg-gradient-to-br from-zinc-900 to-zinc-950 p-7 sm:p-9">

                <div className="flex justify-between items-start">

                  <div>
                    <p className="text-zinc-500 text-sm">
                      Current queue
                    </p>

                    <div className="flex items-end gap-5 mt-3">

                      <span className="text-7xl sm:text-9xl font-black leading-none tracking-tight">
                        {actuallyOnline
                          ? status.queue_count
                          : "—"}
                      </span>

                      <span className="text-zinc-500 pb-2 sm:pb-3">
                        people
                      </span>

                    </div>
                  </div>


                  <Users
                    size={32}
                    className="text-zinc-600"
                  />

                </div>


                <div className="mt-7 flex flex-wrap gap-3">

                  <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-zinc-800/70 capitalize">
                    {trendIcon}
                    {status.trend}
                  </div>

                  <div className="px-3 py-2 rounded-xl bg-zinc-800/70 capitalize">
                    {status.queue_status}
                  </div>

                </div>

              </div>


              {/* CAMERA STATUS */}

              <div className="rounded-[28px] border border-zinc-800 bg-zinc-900 p-7">

                <div className="flex justify-between">

                  <p className="text-zinc-500">
                    Camera node
                  </p>

                  <Camera size={21} />
                </div>

                <p className="text-2xl font-bold mt-5">
                  {actuallyOnline
                    ? "Operational"
                    : "Offline"}
                </p>

                <p className="text-zinc-500 text-sm mt-2">
                  Last heartbeat
                </p>

                <p className="mt-1">
                  {Math.round(ageSeconds)} sec ago
                </p>


                <div className="mt-6 pt-5 border-t border-zinc-800">

                  <div className="flex items-center gap-2 text-sm">

                    {actuallyOnline ? (
                      <>
                        <Wifi
                          size={17}
                          className="text-green-400"
                        />
                        <span className="text-green-400">
                          Connected
                        </span>
                      </>
                    ) : (
                      <>
                        <WifiOff
                          size={17}
                          className="text-red-400"
                        />
                        <span className="text-red-400">
                          No heartbeat
                        </span>
                      </>
                    )}

                  </div>

                </div>

              </div>

            </section>


            {/* METRICS */}

            <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">

              <Metric
                icon={<Clock3 size={20} />}
                title="Average wait"
                value={
                  actuallyOnline
                    ? formatWait(status.avg_wait_seconds)
                    : "—"
                }
              />

              <Metric
                icon={<Gauge size={20} />}
                title="Throughput"
                value={
                  actuallyOnline
                    ? `${status.throughput_per_min}/min`
                    : "—"
                }
              />

              <Metric
                icon={<CheckCircle2 size={20} />}
                title="Served"
                value={
                  actuallyOnline
                    ? String(status.served)
                    : "—"
                }
              />

              <Metric
                icon={<Database size={20} />}
                title="Data age"
                value={`${Math.round(ageSeconds)} sec`}
              />

            </section>


            {/* LIVE GRAPH */}

            <section className="rounded-[28px] border border-zinc-800 bg-zinc-900 p-5 sm:p-7">

              <div className="flex items-center justify-between mb-7">

                <div>
                  <h2 className="text-xl font-bold">
                    Live queue activity
                  </h2>

                  <p className="text-zinc-500 text-sm mt-1">
                    Browser session · updates every 3 seconds
                  </p>
                </div>

                <Activity
                  size={22}
                  className="text-zinc-500"
                />

              </div>


              <div className="h-[280px]">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <LineChart data={liveHistory}>

                    <CartesianGrid
                      strokeDasharray="3 3"
                      stroke="#27272a"
                      vertical={false}
                    />

                    <XAxis
                      dataKey="time"
                      stroke="#71717a"
                      tickLine={false}
                      axisLine={false}
                      minTickGap={35}
                    />

                    <YAxis
                      stroke="#71717a"
                      tickLine={false}
                      axisLine={false}
                      allowDecimals={false}
                      width={28}
                    />

                    <Tooltip
                      contentStyle={{
                        background: "#18181b",
                        border: "1px solid #3f3f46",
                        borderRadius: "12px",
                      }}
                    />

                    <Line
                      type="monotone"
                      dataKey="count"
                      stroke="#fafafa"
                      strokeWidth={3}
                      dot={false}
                      isAnimationActive={true}
                    />

                  </LineChart>

                </ResponsiveContainer>

              </div>

            </section>


            {/* PRIVACY */}

            <section className="rounded-[24px] border border-zinc-800 bg-zinc-950 p-6">

              <div className="flex gap-4">

                <ShieldCheck
                  className="text-zinc-400 shrink-0"
                  size={23}
                />

                <div>
                  <h3 className="font-semibold">
                    Privacy-aware monitoring
                  </h3>

                  <p className="text-zinc-500 text-sm mt-1 leading-relaxed">
                    Q-SENSE uses person detection and temporary
                    multi-object tracking identifiers. Facial
                    recognition and real-world identity tracking are
                    not used.
                  </p>
                </div>

              </div>

            </section>

          </div>
        )}


        {/* =================================================
            HISTORY TAB
        ================================================= */}

        {tab === "history" && (
          <div className="space-y-5">

            <section className="flex flex-col sm:flex-row justify-between sm:items-center gap-4">

              <div>
                <h2 className="text-2xl font-bold">
                  Queue history
                </h2>

                <p className="text-zinc-500 mt-1">
                  Recorded research snapshots
                </p>
              </div>


              <div className="flex gap-2">

                {(["24h", "7d", "30d"] as const).map(
                  (item) => (
                    <button
                      key={item}
                      onClick={() => setRange(item)}
                      className={`px-4 py-2 rounded-xl transition ${
                        range === item
                          ? "bg-white text-black"
                          : "bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white"
                      }`}
                    >
                      {item}
                    </button>
                  )
                )}

              </div>

            </section>


            <section className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">

              <Metric
                icon={<Users size={20} />}
                title="Average queue"
                value={historyStats.average.toFixed(1)}
              />

              <Metric
                icon={<TrendingUp size={20} />}
                title="Peak queue"
                value={String(historyStats.peak)}
              />

              <Metric
                icon={<Gauge size={20} />}
                title="Avg throughput"
                value={`${historyStats.averageThroughput.toFixed(
                  1
                )}/min`}
              />

              <Metric
                icon={<Database size={20} />}
                title="Observations"
                value={String(historyStats.observations)}
              />

            </section>


            <section className="rounded-[28px] border border-zinc-800 bg-zinc-900 p-5 sm:p-7">

              <h3 className="text-xl font-bold">
                Queue level over time
              </h3>


              {historyChartData.length === 0 ? (

                <EmptyState
                  text="No research snapshots in this period yet."
                />

              ) : (

                <div className="h-[400px] mt-6">

                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >

                    <LineChart
                      data={historyChartData}
                    >

                      <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="#27272a"
                        vertical={false}
                      />

                      <XAxis
                        dataKey="recorded_at"
                        tickFormatter={(value) =>
                          new Date(value).toLocaleTimeString(
                            [],
                            {
                              hour: "2-digit",
                              minute: "2-digit",
                            }
                          )
                        }
                        stroke="#71717a"
                        tickLine={false}
                        axisLine={false}
                        minTickGap={45}
                      />

                      <YAxis
                        allowDecimals={false}
                        stroke="#71717a"
                        tickLine={false}
                        axisLine={false}
                      />

                      <Tooltip
			labelFormatter={(value) =>
			  new Date(String(value)).toLocaleString()
			}
                        contentStyle={{
                          background: "#18181b",
                          border:
                            "1px solid #3f3f46",
                          borderRadius: "12px",
                        }}
                      />

                      <Line
                        type="monotone"
                        dataKey="queue_count"
                        name="Queue"
                        stroke="#fafafa"
                        strokeWidth={2.5}
                        dot={false}
                      />

                    </LineChart>

                  </ResponsiveContainer>

                </div>

              )}

            </section>

          </div>
        )}


        {/* =================================================
            MENU TAB
        ================================================= */}

        {tab === "menu" && (
          <div className="space-y-5">

            <div>
              <h2 className="text-2xl font-bold">
                Cafeteria menu
              </h2>

              <p className="text-zinc-500 mt-1">
                Menu records can later be compared against queue
                patterns.
              </p>
            </div>


            {latestMeal ? (

              <>
                <section className="rounded-[28px] border border-zinc-800 bg-zinc-900 p-7">

                  <div className="flex flex-col sm:flex-row sm:justify-between gap-4 mb-7">

                    <div>
                      <p className="text-zinc-500 text-sm">
                        Latest recorded menu
                      </p>

                      <h3 className="text-2xl font-bold capitalize mt-1">
                        {latestMeal.meal_period}
                      </h3>
                    </div>

                    <div className="text-zinc-400">
                      {latestMeal.meal_date}
                    </div>

                  </div>


                  <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">

                    <FoodItem
                      title="Staple"
                      value={latestMeal.staple}
                    />

                    <FoodItem
                      title="Animal protein"
                      value={latestMeal.animal_protein}
                    />

                    <FoodItem
                      title="Plant protein"
                      value={latestMeal.plant_protein}
                    />

                    <FoodItem
                      title="Vegetable"
                      value={latestMeal.vegetable}
                    />

                    <FoodItem
                      title="Fruit"
                      value={latestMeal.fruit}
                    />

                    <FoodItem
                      title="Drink"
                      value={latestMeal.drink}
                    />

                    <FoodItem
                      title="Other"
                      value={latestMeal.other}
                    />

                  </div>

                </section>


                <section className="rounded-[28px] border border-zinc-800 overflow-hidden">

                  <div className="p-6 bg-zinc-900">
                    <h3 className="font-bold">
                      Recent meal records
                    </h3>
                  </div>


                  <div className="divide-y divide-zinc-800">

                    {meals.slice(0, 8).map((meal) => (

                      <div
                        key={meal.id}
                        className="p-5 flex justify-between items-center bg-zinc-950 hover:bg-zinc-900 transition"
                      >

                        <div>

                          <p className="font-medium capitalize">
                            {meal.meal_period}
                          </p>

                          <p className="text-zinc-500 text-sm mt-1">
                            {[
                              meal.staple,
                              meal.animal_protein,
                            ]
                              .filter(Boolean)
                              .join(" · ")}
                          </p>

                        </div>


                        <div className="flex items-center gap-3 text-zinc-500">

                          <span className="text-sm">
                            {meal.meal_date}
                          </span>

                          <ChevronRight size={17} />

                        </div>

                      </div>

                    ))}

                  </div>

                </section>

              </>

            ) : (

              <EmptyState
                text="No menu records have been entered yet."
              />

            )}

          </div>
        )}


        {/* =================================================
            VALIDATION TAB
        ================================================= */}

        {tab === "validation" && (
          <div className="space-y-5">

            <div>
              <h2 className="text-2xl font-bold">
                System validation
              </h2>

              <p className="text-zinc-500 mt-1">
                Comparison between manual observations and
                Q-SENSE counts.
              </p>
            </div>


            {validationStats ? (

              <>

                <section className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">

                  <Metric
                    title="Validation observations"
                    value={String(validationStats.n)}
                    icon={<Database size={20} />}
                  />

                  <Metric
                    title="MAE"
                    value={`${validationStats.mae.toFixed(
                      2
                    )} people`}
                    icon={<BarChart3 size={20} />}
                  />

                  <Metric
                    title="RMSE"
                    value={`${validationStats.rmse.toFixed(
                      2
                    )} people`}
                    icon={<BarChart3 size={20} />}
                  />

                  <Metric
                    title="Mean bias"
                    value={validationStats.bias.toFixed(2)}
                    icon={<Activity size={20} />}
                  />

                  <Metric
                    title="Exact agreement"
                    value={`${validationStats.exact.toFixed(
                      1
                    )}%`}
                    icon={<CheckCircle2 size={20} />}
                  />

                  <Metric
                    title="Within ±1 person"
                    value={`${validationStats.withinOne.toFixed(
                      1
                    )}%`}
                    icon={<ShieldCheck size={20} />}
                  />

                </section>


                <section className="rounded-[28px] border border-zinc-800 bg-zinc-900 p-6">

                  <div className="flex gap-4">

                    <Info
                      size={23}
                      className="text-zinc-400 shrink-0"
                    />

                    <p className="text-zinc-400 leading-relaxed">
                      Validation statistics are calculated directly
                      from manually recorded actual queue counts and
                      the corresponding Q-SENSE estimates. MAE and
                      RMSE are reported in people rather than
                      percentage error so zero-person queues remain
                      valid observations.
                    </p>

                  </div>

                </section>

              </>

            ) : (

              <section className="rounded-[28px] border border-zinc-800 bg-zinc-900 p-8">

                <ShieldCheck
                  size={35}
                  className="text-zinc-500"
                />

                <h3 className="text-xl font-bold mt-5">
                  Field validation not available yet
                </h3>

                <p className="text-zinc-500 mt-2 max-w-xl">
                  This is expected during the proof-of-concept
                  stage. Once manual observations are entered,
                  Q-SENSE will calculate MAE, RMSE, bias and
                  agreement automatically.
                </p>

              </section>

            )}

          </div>
        )}


        {/* =================================================
            FOOTER
        ================================================= */}

        <footer className="mt-12 pt-6 border-t border-zinc-900 flex flex-col sm:flex-row justify-between gap-3 text-xs text-zinc-600">

          <span>
            Q-SENSE · Proof of Concept
          </span>

          <span>
            Anonymous queue analytics · No facial recognition
          </span>

        </footer>

      </div>
    </main>
  );
}


/* =========================================================
   COMPONENTS
========================================================= */

function NavButton({
  active,
  icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-2 px-4 py-2.5 rounded-xl whitespace-nowrap transition ${
        active
          ? "bg-white text-black"
          : "text-zinc-400 hover:text-white hover:bg-zinc-800"
      }`}
    >
      {icon}
      {label}
    </button>
  );
}


function StatusPill({
  online,
}: {
  online: boolean;
}) {
  return (
    <div
      className={`flex items-center gap-2 px-4 py-2 rounded-full border text-sm ${
        online
          ? "border-green-900 bg-green-500/10 text-green-400"
          : "border-red-900 bg-red-500/10 text-red-400"
      }`}
    >
      <span
        className={`w-2 h-2 rounded-full ${
          online
            ? "bg-green-400 animate-pulse"
            : "bg-red-400"
        }`}
      />

      {online
        ? "SYSTEM ONLINE"
        : "SYSTEM OFFLINE"}
    </div>
  );
}


function Metric({
  icon,
  title,
  value,
}: {
  icon: React.ReactNode;
  title: string;
  value: string;
}) {
  return (
    <div className="rounded-[24px] border border-zinc-800 bg-zinc-900 p-5">

      <div className="flex justify-between text-zinc-500">
        <span className="text-sm">
          {title}
        </span>

        {icon}
      </div>

      <p className="text-2xl font-bold mt-4">
        {value}
      </p>

    </div>
  );
}


function FoodItem({
  title,
  value,
}: {
  title: string;
  value: string | null;
}) {
  return (
    <div className="rounded-2xl bg-zinc-950 border border-zinc-800 p-5">

      <p className="text-zinc-500 text-xs uppercase tracking-wider">
        {title}
      </p>

      <p className="font-semibold mt-2">
        {value || "—"}
      </p>

    </div>
  );
}


function EmptyState({
  text,
}: {
  text: string;
}) {
  return (
    <div className="py-20 text-center text-zinc-500">
      <Database
        className="mx-auto mb-4"
        size={31}
      />

      <p>
        {text}
      </p>
    </div>
  );
}


function formatWait(seconds: number) {
  if (seconds < 60) {
    return `${seconds.toFixed(0)} sec`;
  }

  return `${(seconds / 60).toFixed(1)} min`;
}