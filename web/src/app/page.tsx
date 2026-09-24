"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { supabase } from "@/lib/supabase";

import {
  Activity,
  ArrowRight,
  BarChart3,
  Camera,
  Check,
  CheckCircle2,
  Clock3,
  Database,
  Gauge,
  Heart,
  Info,
  Radio,
  ShieldCheck,
  TrendingUp,
  Users,
  UtensilsCrossed,
  Wifi,
  WifiOff,
  X,
} from "lucide-react";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";

type LiveStatus = {
  id: number;
  updated_at: string;
  section: string;
  meal_period: string;
  queue_count: number;
  queue_status: string;
  trend: string;
  entries: number;
  served: number;
  abandoned: number;
  avg_wait_seconds: number;
  throughput_per_min: number;
  camera_online: boolean;
};

type SessionMetric = {
  id: number;
  session_id: string;
  service_date: string;
  meal_period: string;
  section: string;
  menu_id: string | null;
  queue_entry: number;
  service_completion: number;
  abandonment: number;
  avg_wait_seconds: number;
  throughput_per_min: number;
  peak_queue: number;
  mean_queue: number;
  median_queue: number;
  congestion_duration_min: number;
  queue_burden_person_min: number;
  meals_served: number;
  menu_demand_index: number;
  menu_acceptance_index: number;
  data_source: string;
};

type Meal = {
  id: number;
  menu_id: string | null;
  meal_date: string;
  meal_period: string;
  main_dish: string | null;
  staple: string | null;
  animal_protein: string | null;
  plant_protein: string | null;
  vegetable: string | null;
  fruit: string | null;
  drink: string | null;
  other: string | null;
  data_source: string;
};

type Snapshot = {
  id: number;
  recorded_at: string;
  session_id: string;
  meal_period: string;
  section: string;
  queue_count: number;
  throughput_per_min: number;
  data_source: string;
};

type Validation = {
  id: number;
  recorded_at: string;
  session_id: string | null;
  section: string;
  actual_count: number;
  qsense_count: number;
  absolute_error: number | null;
  context: string | null;
  data_source: string;
};

type Tab =
  | "overview"
  | "analytics"
  | "menu"
  | "validation"
  | "system";

const MEAL_ORDER: Record<string, number> = {
  breakfast: 1,
  lunch: 2,
  dinner: 3,
};

const COLORS = {
  ink: "#18352B",
  tomato: "#E86652",
  mustard: "#F1BD4A",
  sage: "#82AE8F",
  blue: "#5E87A4",
  purple: "#9877A8",
};

export default function Home() {
  const [live, setLive] = useState<LiveStatus[]>([]);
  const [metrics, setMetrics] = useState<SessionMetric[]>([]);
  const [meals, setMeals] = useState<Meal[]>([]);
  const [snapshots, setSnapshots] = useState<Snapshot[]>([]);
  const [validation, setValidation] = useState<Validation[]>([]);
  const [tab, setTab] = useState<Tab>("overview");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nowMs, setNowMs] = useState(Date.now());

  const loadLive = useCallback(async () => {
    const { data, error } = await supabase
      .from("live_status")
      .select("*")
      .order("id");

    if (error) {
      setError(error.message);
      setLoading(false);
      return;
    }

    setLive((data ?? []) as LiveStatus[]);
    setError(null);
    setLoading(false);
  }, []);

  const loadStatic = useCallback(async () => {
    const [m1, m2, m3, m4] = await Promise.all([
      supabase
        .from("session_metrics")
        .select("*")
        .order("service_date", { ascending: false }),

      supabase
        .from("meal_log")
        .select("*")
        .order("meal_date", { ascending: false }),

      supabase
        .from("queue_snapshots")
        .select("*")
        .order("recorded_at", { ascending: true })
        .limit(2000),

      supabase
        .from("manual_validation")
        .select("*")
        .order("recorded_at", { ascending: true })
        .limit(1000),
    ]);

    setMetrics((m1.data ?? []) as SessionMetric[]);
    setMeals((m2.data ?? []) as Meal[]);
    setSnapshots((m3.data ?? []) as Snapshot[]);
    setValidation((m4.data ?? []) as Validation[]);
  }, []);

  useEffect(() => {
    loadLive();
    loadStatic();
  }, [loadLive, loadStatic]);

  useEffect(() => {
    const timer = setInterval(loadLive, 3000);
    return () => clearInterval(timer);
  }, [loadLive]);

  useEffect(() => {
    const timer = setInterval(() => setNowMs(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const sortedMetrics = useMemo(() => {
    return [...metrics].sort((a, b) => {
      const dateCompare = b.service_date.localeCompare(
        a.service_date
      );

      if (dateCompare !== 0) {
        return dateCompare;
      }

      return (
        (MEAL_ORDER[b.meal_period] ?? 0)
        -
        (MEAL_ORDER[a.meal_period] ?? 0)
      );
    });
  }, [metrics]);

  const sortedMeals = useMemo(() => {
    return [...meals].sort((a, b) => {
      const dateCompare = b.meal_date.localeCompare(
        a.meal_date
      );

      if (dateCompare !== 0) {
        return dateCompare;
      }

      return (
        (MEAL_ORDER[b.meal_period] ?? 0)
        -
        (MEAL_ORDER[a.meal_period] ?? 0)
      );
    });
  }, [meals]);

  function isOnline(row: LiveStatus | undefined) {
    if (!row) {
      return false;
    }

    const age =
      (
        nowMs
        -
        new Date(row.updated_at).getTime()
      )
      / 1000;

    return row.camera_online && age < 20;
  }

  const male = live.find(
    (row) => row.section === "male"
  );

  const female = live.find(
    (row) => row.section === "female"
  );

  const maleOnline = isOnline(male);
  const femaleOnline = isOnline(female);

  const onlineRows = live.filter(isOnline);

  const totalQueue = onlineRows.reduce(
    (sum, row) => sum + (row.queue_count ?? 0),
    0
  );

  const liveEntries = onlineRows.reduce(
    (sum, row) => sum + (row.entries ?? 0),
    0
  );

  const liveServed = onlineRows.reduce(
    (sum, row) => sum + (row.served ?? 0),
    0
  );

  const liveAbandoned = onlineRows.reduce(
    (sum, row) => sum + (row.abandoned ?? 0),
    0
  );

  const liveThroughput = onlineRows.reduce(
    (sum, row) =>
      sum + (row.throughput_per_min ?? 0),
    0
  );

  const liveWait =
    onlineRows.length > 0
      ?
        onlineRows.reduce(
          (sum, row) =>
            sum + (row.avg_wait_seconds ?? 0),
          0
        ) / onlineRows.length
      :
        0;

  const latestMetric =
    sortedMetrics[0] ?? null;

  const latestCurve = useMemo(() => {
    if (!latestMetric) {
      return [];
    }

    return snapshots.filter(
      (row) =>
        row.session_id === latestMetric.session_id
    );
  }, [latestMetric, snapshots]);

  const sessionChart = useMemo(() => {
    return [...sortedMetrics]
      .reverse()
      .map((row) => ({
        label:
          `${formatShortDate(row.service_date)} `
          + mealShort(row.meal_period),
        peak: row.peak_queue,
        mean: row.mean_queue,
        burden: row.queue_burden_person_min,
      }));
  }, [sortedMetrics]);

  const menuMetricData = useMemo(() => {
    const menuById = new Map(
      sortedMeals.map(
        (meal) => [
          meal.menu_id,
          meal,
        ]
      )
    );

    return sortedMetrics
      .filter((row) => row.menu_id)
      .map((row) => {
        const meal = menuById.get(
          row.menu_id
        );

        return {
          ...row,
          main_dish:
            meal?.main_dish
            ?? row.menu_id
            ?? "Menu",
          meal,
        };
      });
  }, [sortedMeals, sortedMetrics]);

  const validationStats = useMemo(() => {
    if (validation.length === 0) {
      return null;
    }

    const errors = validation.map(
      (row) =>
        row.qsense_count
        -
        row.actual_count
    );

    const absolute =
      errors.map(Math.abs);

    const mae =
      absolute.reduce(
        (a, b) => a + b,
        0
      )
      /
      absolute.length;

    const rmse = Math.sqrt(
      errors
        .map(
          (value) =>
            value * value
        )
        .reduce(
          (a, b) => a + b,
          0
        )
      /
      errors.length
    );

    const bias =
      errors.reduce(
        (a, b) => a + b,
        0
      )
      /
      errors.length;

    const exact =
      (
        absolute.filter(
          (value) => value === 0
        ).length
        /
        absolute.length
      )
      * 100;

    const withinOne =
      (
        absolute.filter(
          (value) => value <= 1
        ).length
        /
        absolute.length
      )
      * 100;

    return {
      n: validation.length,
      mae,
      rmse,
      bias,
      exact,
      withinOne,
      mealN:
        validation.filter(
          (row) =>
            row.context === "meal_period"
        ).length,
      outsideN:
        validation.filter(
          (row) =>
            row.context === "outside_meal"
        ).length,
    };
  }, [validation]);

  const validationScatter =
    validation.map((row) => ({
      actual: row.actual_count,
      predicted: row.qsense_count,
      context: row.context,
    }));

  if (loading) {
    return (
      <main
        className="
          min-h-screen
          flex
          items-center
          justify-center
          text-[#18352B]
        "
      >
        <div className="text-center">
          <div
            className="
              w-14
              h-14
              rounded-full
              bg-[#F1BD4A]
              flex
              items-center
              justify-center
              mx-auto
              animate-pulse
            "
          >
            <Radio size={25} />
          </div>

          <p className="mt-4 font-semibold">
            Connecting to Q-SENSE...
          </p>
        </div>
      </main>
    );
  }

  if (error) {
    return (
      <main
        className="
          min-h-screen
          flex
          items-center
          justify-center
          p-6
          text-[#18352B]
        "
      >
        <div className="max-w-xl text-center">
          <X
            size={40}
            className="mx-auto text-[#E86652]"
          />

          <h1 className="text-4xl font-black mt-4">
            Q-SENSE
          </h1>

          <p className="mt-3 text-[#7A7469]">
            {error}
          </p>
        </div>
      </main>
    );
  }

  return (
    <main
      className="
        min-h-screen
        text-[#18352B]
      "
    >
      <div
        className="
          max-w-[1400px]
          mx-auto
          px-4
          sm:px-7
          lg:px-10
          py-7
          sm:py-9
        "
      >
        <header
          className="
            flex
            flex-col
            lg:flex-row
            lg:items-center
            justify-between
            gap-6
          "
        >
          <div>
            <div
              className="
                flex
                items-center
                gap-3
              "
            >
              <div
                className="
                  w-12
                  h-12
                  rounded-[18px]
                  bg-[#E86652]
                  text-white
                  flex
                  items-center
                  justify-center
                  shadow-[0_6px_0_#B94F40]
                "
              >
                <UtensilsCrossed size={24} />
              </div>

              <div>
                <h1
                  className="
                    text-3xl
                    sm:text-4xl
                    font-black
                    tracking-[-0.04em]
                  "
                >
                  Q-SENSE
                </h1>

                <p
                  className="
                    text-sm
                    text-[#7A7469]
                  "
                >
                  Queue Sensing &
                  Evaluation System
                </p>
              </div>
            </div>

            <div
              className="
                flex
                flex-wrap
                gap-2
                mt-5
              "
            >
              <Badge color="tomato">
                LIVE POC
              </Badge>

              <Badge color="sage">
                2-NODE READY
              </Badge>

              <Badge color="mustard">
                HISTORICAL: DEMO
              </Badge>
            </div>
          </div>

          <div
            className="
              flex
              flex-wrap
              items-center
              gap-3
            "
          >
            <SystemStatus
              online={onlineRows.length > 0}
            />

            <div
              className="
                px-4
                py-2.5
                rounded-full
                bg-white
                border
                border-[#DED6C7]
                text-sm
                font-semibold
              "
            >
              {male?.meal_period
                ?.replaceAll("_", " ")
                ?.toUpperCase()
                ?? "OUTSIDE MEAL"}
            </div>
          </div>
        </header>

        <section
          className="
            mt-8
            grid
            lg:grid-cols-[1.2fr_.8fr]
            gap-5
          "
        >
          <div
            className="
              relative
              overflow-hidden
              bg-[#18352B]
              text-white
              rounded-[36px]
              p-7
              sm:p-10
              min-h-[330px]
            "
          >
            <div
              className="
                absolute
                -right-16
                -bottom-20
                w-64
                h-64
                rounded-full
                bg-[#E86652]
              "
            />

            <div
              className="
                absolute
                right-32
                -top-12
                w-36
                h-36
                rounded-full
                bg-[#F1BD4A]
              "
            />

            <div className="relative">
              <p
                className="
                  text-sm
                  tracking-[0.15em]
                  uppercase
                  text-[#D5E0D7]
                  font-bold
                "
              >
                Active queue
              </p>

              <div
                className="
                  mt-5
                  flex
                  items-end
                  gap-5
                "
              >
                <span
                  className="
                    text-[92px]
                    sm:text-[130px]
                    leading-[.8]
                    font-black
                    tracking-[-0.08em]
                  "
                >
                  {
                    onlineRows.length > 0
                      ? totalQueue
                      : "—"
                  }
                </span>

                <div className="pb-2 sm:pb-4">
                  <p className="text-xl font-bold">
                    people
                  </p>

                  <p
                    className="
                      text-[#BFD0C3]
                      mt-1
                    "
                  >
                    across active nodes
                  </p>
                </div>
              </div>

              <div
                className="
                  mt-8
                  flex
                  flex-wrap
                  gap-3
                "
              >
                <LiveChip
                  icon={
                    <Activity size={16} />
                  }
                >
                  {male?.trend ?? "stable"}
                </LiveChip>

                <LiveChip
                  icon={
                    <Gauge size={16} />
                  }
                >
                  {liveThroughput.toFixed(1)}
                  /min throughput
                </LiveChip>

                <LiveChip
                  icon={
                    <Clock3 size={16} />
                  }
                >
                  {formatWait(liveWait)}
                </LiveChip>
              </div>
            </div>
          </div>

          <div
            className="
              grid
              sm:grid-cols-2
              lg:grid-cols-1
              gap-5
            "
          >
            <CameraCard
              title="Male queue"
              subtitle="PoC camera node"
              online={maleOnline}
              count={male?.queue_count ?? 0}
              age={ageSeconds(male, nowMs)}
              accent="tomato"
            />

            <CameraCard
              title="Female queue"
              subtitle="Second node ready"
              online={femaleOnline}
              count={female?.queue_count ?? 0}
              age={ageSeconds(female, nowMs)}
              accent="blue"
              placeholder
            />
          </div>
        </section>

        <nav
          className="
            mt-7
            bg-white
            border
            border-[#DED6C7]
            rounded-[22px]
            p-1.5
            flex
            gap-1
            overflow-x-auto
            shadow-[0_7px_0_#E8E0D2]
          "
        >
          <TabButton
            active={tab === "overview"}
            icon={<Activity size={17} />}
            onClick={() => setTab("overview")}
          >
            Overview
          </TabButton>

          <TabButton
            active={tab === "analytics"}
            icon={<BarChart3 size={17} />}
            onClick={() => setTab("analytics")}
          >
            Queue Analytics
          </TabButton>

          <TabButton
            active={tab === "menu"}
            icon={<UtensilsCrossed size={17} />}
            onClick={() => setTab("menu")}
          >
            Menu Lab
          </TabButton>

          <TabButton
            active={tab === "validation"}
            icon={<ShieldCheck size={17} />}
            onClick={() => setTab("validation")}
          >
            Validation
          </TabButton>

          <TabButton
            active={tab === "system"}
            icon={<Database size={17} />}
            onClick={() => setTab("system")}
          >
            System
          </TabButton>
        </nav>

        <section
          className="
            mt-5
            rounded-[22px]
            bg-[#FFF3CE]
            border
            border-[#E9C966]
            px-5
            py-4
            flex
            gap-3
            items-start
          "
        >
          <Info
            size={20}
            className="shrink-0 mt-0.5"
          />

          <p
            className="
              text-sm
              leading-relaxed
            "
          >
            <b>Presentation mode:</b>{" "}
            live camera status and live queue
            counters come from the actual
            prototype. Historical queue
            analytics, menu-side details,
            acceptance values, and validation
            observations below are{" "}
            <b>synthetic demonstration data</b>.
          </p>
        </section>

        {tab === "overview" && (
          <div className="mt-6 space-y-6">
            <section
              className="
                grid
                sm:grid-cols-2
                xl:grid-cols-5
                gap-4
              "
            >
              <MetricCard
                icon={<ArrowRight size={21} />}
                title="Queue entries"
                value={
                  onlineRows.length
                    ? String(liveEntries)
                    : "—"
                }
                color="mustard"
              />

              <MetricCard
                icon={
                  <CheckCircle2 size={21} />
                }
                title="Service completion"
                value={
                  onlineRows.length
                    ? String(liveServed)
                    : "—"
                }
                color="sage"
              />

              <MetricCard
                icon={<X size={21} />}
                title="Abandonment"
                value={
                  onlineRows.length
                    ? String(liveAbandoned)
                    : "—"
                }
                color="tomato"
              />

              <MetricCard
                icon={<Clock3 size={21} />}
                title="Waiting time"
                value={
                  onlineRows.length
                    ? formatWait(liveWait)
                    : "—"
                }
                color="blue"
              />

              <MetricCard
                icon={<Gauge size={21} />}
                title="Throughput"
                value={
                  onlineRows.length
                    ?
                      `${liveThroughput.toFixed(1)}/min`
                    :
                      "—"
                }
                color="purple"
              />
            </section>

            <section
              className="
                grid
                xl:grid-cols-[1.35fr_.65fr]
                gap-5
              "
            >
              <PaperCard>
                <SectionTitle
                  eyebrow="Historical session"
                  title="Queue curve"
                  icon={<Activity />}
                />

                {latestCurve.length > 0 ? (
                  <div className="h-[320px] mt-7">
                    <ResponsiveContainer
                      width="100%"
                      height="100%"
                    >
                      <AreaChart data={latestCurve}>
                        <defs>
                          <linearGradient
                            id="queueFill"
                            x1="0"
                            y1="0"
                            x2="0"
                            y2="1"
                          >
                            <stop
                              offset="0%"
                              stopColor={COLORS.tomato}
                              stopOpacity={0.5}
                            />
                            <stop
                              offset="100%"
                              stopColor={COLORS.tomato}
                              stopOpacity={0.03}
                            />
                          </linearGradient>
                        </defs>

                        <CartesianGrid
                          stroke="#E9E2D5"
                          strokeDasharray="4 4"
                          vertical={false}
                        />

                        <XAxis
                          dataKey="recorded_at"
                          tickFormatter={
                            (value) =>
                              new Date(
                                String(value)
                              ).toLocaleTimeString(
                                [],
                                {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                }
                              )
                          }
                          tickLine={false}
                          axisLine={false}
                          stroke="#8E877B"
                        />

                        <YAxis
                          allowDecimals={false}
                          tickLine={false}
                          axisLine={false}
                          stroke="#8E877B"
                        />

                        <Tooltip
                          labelFormatter={
                            (value) =>
                              new Date(
                                String(value)
                              ).toLocaleString()
                          }
                          contentStyle={tooltipStyle}
                        />

                        <Area
                          type="monotone"
                          dataKey="queue_count"
                          name="Queue"
                          stroke={COLORS.tomato}
                          strokeWidth={3}
                          fill="url(#queueFill)"
                          dot={false}
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                ) : (
                  <EmptyState>
                    No historical queue curve yet.
                  </EmptyState>
                )}
              </PaperCard>

              <PaperCard>
                <SectionTitle
                  eyebrow="Latest session"
                  title={
                    latestMetric
                      ?
                        mealLabel(
                          latestMetric.meal_period
                        )
                      :
                        "No session"
                  }
                  icon={<TrendingUp />}
                />

                {latestMetric && (
                  <div className="mt-6 space-y-4">
                    <MiniStat
                      label="Peak queue"
                      value={String(
                        latestMetric.peak_queue
                      )}
                    />

                    <MiniStat
                      label="Mean queue"
                      value={
                        latestMetric.mean_queue.toFixed(1)
                      }
                    />

                    <MiniStat
                      label="Median queue"
                      value={
                        latestMetric.median_queue.toFixed(1)
                      }
                    />

                    <MiniStat
                      label="Congestion"
                      value={
                        `${latestMetric.congestion_duration_min.toFixed(0)} min`
                      }
                    />

                    <MiniStat
                      label="Queue burden"
                      value={
                        `${latestMetric.queue_burden_person_min.toFixed(0)} person-min`
                      }
                    />
                  </div>
                )}
              </PaperCard>
            </section>

            {latestMetric && (
              <PaperCard>
                <SectionTitle
                  eyebrow="Flow"
                  title="From arrival to meal"
                  icon={<Users />}
                />

                <div
                  className="
                    mt-7
                    grid
                    lg:grid-cols-[1fr_auto_1fr_auto_1fr]
                    gap-4
                    items-center
                  "
                >
                  <FlowBox
                    color="mustard"
                    value={latestMetric.queue_entry}
                    label="Queue entry"
                  />

                  <ArrowRight
                    className="
                      hidden
                      lg:block
                      text-[#9E978C]
                    "
                  />

                  <FlowBox
                    color="sage"
                    value={
                      latestMetric.service_completion
                    }
                    label="Service completion"
                  />

                  <ArrowRight
                    className="
                      hidden
                      lg:block
                      text-[#9E978C]
                    "
                  />

                  <FlowBox
                    color="blue"
                    value={latestMetric.meals_served}
                    label="Meals served"
                  />
                </div>

                <div
                  className="
                    mt-4
                    rounded-[18px]
                    bg-[#FFF0EC]
                    border
                    border-[#F4B9AD]
                    p-4
                    flex
                    items-center
                    justify-between
                    gap-4
                  "
                >
                  <div
                    className="
                      flex
                      gap-3
                      items-center
                    "
                  >
                    <X size={19} />
                    <span className="font-semibold">
                      Abandoned queue
                    </span>
                  </div>

                  <span
                    className="
                      text-2xl
                      font-black
                    "
                  >
                    {latestMetric.abandonment}
                  </span>
                </div>
              </PaperCard>
            )}
          </div>
        )}

        {tab === "analytics" && (
          <div className="mt-6 space-y-6">
            <SectionHeading
              kicker="QUEUE ANALYTICS"
              title="What actually happened?"
              description="
                Session-level metrics derived
                from queue counts and service
                events.
              "
            />

            {latestMetric && (
              <section
                className="
                  grid
                  sm:grid-cols-2
                  lg:grid-cols-3
                  xl:grid-cols-6
                  gap-4
                "
              >
                <MetricCard
                  title="Peak queue"
                  value={String(
                    latestMetric.peak_queue
                  )}
                  icon={<TrendingUp />}
                  color="tomato"
                />

                <MetricCard
                  title="Mean queue"
                  value={
                    latestMetric.mean_queue.toFixed(1)
                  }
                  icon={<BarChart3 />}
                  color="mustard"
                />

                <MetricCard
                  title="Median queue"
                  value={
                    latestMetric.median_queue.toFixed(1)
                  }
                  icon={<Activity />}
                  color="sage"
                />

                <MetricCard
                  title="Congestion"
                  value={
                    `${latestMetric.congestion_duration_min.toFixed(0)} min`
                  }
                  icon={<Clock3 />}
                  color="blue"
                />

                <MetricCard
                  title="Queue burden"
                  value={
                    `${latestMetric.queue_burden_person_min.toFixed(0)}`
                  }
                  sub="person-min"
                  icon={<Users />}
                  color="purple"
                />

                <MetricCard
                  title="Meals served"
                  value={String(
                    latestMetric.meals_served
                  )}
                  icon={<UtensilsCrossed />}
                  color="sage"
                />
              </section>
            )}

            <PaperCard>
              <SectionTitle
                eyebrow="Across sessions"
                title="Peak vs mean queue"
                icon={<BarChart3 />}
              />

              <div className="h-[390px] mt-7">
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <BarChart data={sessionChart}>
                    <CartesianGrid
                      stroke="#E9E2D5"
                      strokeDasharray="4 4"
                      vertical={false}
                    />

                    <XAxis
                      dataKey="label"
                      tickLine={false}
                      axisLine={false}
                      stroke="#8E877B"
                    />

                    <YAxis
                      tickLine={false}
                      axisLine={false}
                      stroke="#8E877B"
                    />

                    <Tooltip
                      contentStyle={tooltipStyle}
                    />

                    <Legend />

                    <Bar
                      dataKey="peak"
                      name="Peak queue"
                      fill={COLORS.tomato}
                      radius={[8, 8, 0, 0]}
                    />

                    <Bar
                      dataKey="mean"
                      name="Mean queue"
                      fill={COLORS.mustard}
                      radius={[8, 8, 0, 0]}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </PaperCard>

            <PaperCard>
              <SectionTitle
                eyebrow="Session table"
                title="Nine meal sessions"
                icon={<Database />}
              />

              <div className="overflow-x-auto mt-6">
                <table
                  className="
                    min-w-[1050px]
                    w-full
                    text-sm
                  "
                >
                  <thead>
                    <tr
                      className="
                        text-left
                        text-[#797266]
                        border-b
                        border-[#E7DFD1]
                      "
                    >
                      <Th>Session</Th>
                      <Th>Entry</Th>
                      <Th>Served</Th>
                      <Th>Abandoned</Th>
                      <Th>Wait</Th>
                      <Th>Peak</Th>
                      <Th>Mean</Th>
                      <Th>Median</Th>
                      <Th>Congestion</Th>
                      <Th>Burden</Th>
                    </tr>
                  </thead>

                  <tbody>
                    {sortedMetrics.map((row) => (
                      <tr
                        key={row.session_id}
                        className="
                          border-b
                          border-[#EEE7DB]
                          last:border-0
                        "
                      >
                        <Td>
                          <div className="font-bold">
                            {mealLabel(
                              row.meal_period
                            )}
                          </div>

                          <div
                            className="
                              text-xs
                              text-[#8C8578]
                              mt-1
                            "
                          >
                            {formatLongDate(
                              row.service_date
                            )}
                          </div>
                        </Td>

                        <Td>{row.queue_entry}</Td>
                        <Td>
                          {row.service_completion}
                        </Td>
                        <Td>{row.abandonment}</Td>
                        <Td>
                          {formatWait(
                            row.avg_wait_seconds
                          )}
                        </Td>
                        <Td>{row.peak_queue}</Td>
                        <Td>
                          {row.mean_queue.toFixed(1)}
                        </Td>
                        <Td>
                          {row.median_queue.toFixed(1)}
                        </Td>
                        <Td>
                          {row.congestion_duration_min}m
                        </Td>
                        <Td>
                          {row.queue_burden_person_min.toFixed(0)}
                        </Td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </PaperCard>
          </div>
        )}

        {tab === "menu" && (
          <div className="mt-6 space-y-6">
            <SectionHeading
              kicker="MENU LAB"
              title="Does the menu move the queue?"
              description="
                Demand is represented as a
                queue/service proxy. Acceptance
                values here are synthetic
                placeholders and are not inferred
                from camera behavior.
              "
            />

            <section
              className="
                grid
                xl:grid-cols-[.85fr_1.15fr]
                gap-5
              "
            >
              <PaperCard>
                <SectionTitle
                  eyebrow="Demand × acceptance"
                  title="Menu map"
                  icon={<Heart />}
                />

                <div className="h-[420px] mt-7">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <ScatterChart>
                      <CartesianGrid
                        stroke="#E9E2D5"
                        strokeDasharray="4 4"
                      />

                      <XAxis
                        type="number"
                        dataKey="menu_demand_index"
                        name="Demand"
                        domain={[60, 100]}
                        tickLine={false}
                        axisLine={false}
                        stroke="#8E877B"
                      />

                      <YAxis
                        type="number"
                        dataKey="menu_acceptance_index"
                        name="Acceptance"
                        domain={[70, 100]}
                        tickLine={false}
                        axisLine={false}
                        stroke="#8E877B"
                      />

                      <ZAxis range={[100, 400]} />

                      <Tooltip
                        cursor={{
                          strokeDasharray: "4 4",
                        }}
                        content={<MenuTooltip />}
                      />

                      <Scatter
                        name="Menu"
                        data={menuMetricData}
                        fill={COLORS.tomato}
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </PaperCard>

              <div
                className="
                  grid
                  sm:grid-cols-2
                  gap-4
                "
              >
                {menuMetricData.map((row) => (
                  <MenuCard
                    key={row.session_id}
                    row={row}
                    meal={row.meal}
                  />
                ))}
              </div>
            </section>
          </div>
        )}

        {tab === "validation" && (
          <div className="mt-6 space-y-6">
            <SectionHeading
              kicker="VALIDATION"
              title="How close is Q-SENSE to manual counting?"
              description="
                This presentation dataset uses
                48 synthetic paired observations,
                including outside meal hours, to
                demonstrate the planned validation
                workflow.
              "
            />

            {validationStats && (
              <section
                className="
                  grid
                  sm:grid-cols-2
                  lg:grid-cols-3
                  xl:grid-cols-6
                  gap-4
                "
              >
                <MetricCard
                  title="Observations"
                  value={String(
                    validationStats.n
                  )}
                  icon={<Database />}
                  color="mustard"
                />

                <MetricCard
                  title="MAE"
                  value={
                    validationStats.mae.toFixed(2)
                  }
                  sub="people"
                  icon={<BarChart3 />}
                  color="sage"
                />

                <MetricCard
                  title="RMSE"
                  value={
                    validationStats.rmse.toFixed(2)
                  }
                  sub="people"
                  icon={<Activity />}
                  color="blue"
                />

                <MetricCard
                  title="Mean bias"
                  value={
                    validationStats.bias.toFixed(2)
                  }
                  icon={<TrendingUp />}
                  color="purple"
                />

                <MetricCard
                  title="Exact"
                  value={
                    `${validationStats.exact.toFixed(1)}%`
                  }
                  icon={<Check />}
                  color="sage"
                />

                <MetricCard
                  title="Within ±1"
                  value={
                    `${validationStats.withinOne.toFixed(1)}%`
                  }
                  icon={<ShieldCheck />}
                  color="tomato"
                />
              </section>
            )}

            <section
              className="
                grid
                xl:grid-cols-[1.1fr_.9fr]
                gap-5
              "
            >
              <PaperCard>
                <SectionTitle
                  eyebrow="Paired counts"
                  title="Manual vs Q-SENSE"
                  icon={<ShieldCheck />}
                />

                <div className="h-[430px] mt-7">
                  <ResponsiveContainer
                    width="100%"
                    height="100%"
                  >
                    <ScatterChart>
                      <CartesianGrid
                        stroke="#E9E2D5"
                        strokeDasharray="4 4"
                      />

                      <XAxis
                        type="number"
                        dataKey="actual"
                        name="Manual"
                        domain={[0, 20]}
                        allowDecimals={false}
                        stroke="#8E877B"
                      />

                      <YAxis
                        type="number"
                        dataKey="predicted"
                        name="Q-SENSE"
                        domain={[0, 20]}
                        allowDecimals={false}
                        stroke="#8E877B"
                      />

                      <Tooltip
                        contentStyle={tooltipStyle}
                      />

                      <ReferenceLine
                        segment={[
                          { x: 0, y: 0 },
                          { x: 20, y: 20 },
                        ]}
                        stroke={COLORS.sage}
                        strokeWidth={2}
                        strokeDasharray="5 5"
                      />

                      <Scatter
                        data={validationScatter}
                        fill={COLORS.blue}
                      />
                    </ScatterChart>
                  </ResponsiveContainer>
                </div>
              </PaperCard>

              <PaperCard>
                <SectionTitle
                  eyebrow="Validation design"
                  title="Coverage"
                  icon={<Database />}
                />

                {validationStats && (
                  <div className="mt-7 space-y-4">
                    <ValidationRow
                      label="Meal-period observations"
                      value={validationStats.mealN}
                      color={COLORS.tomato}
                    />

                    <ValidationRow
                      label="Outside-meal observations"
                      value={validationStats.outsideN}
                      color={COLORS.blue}
                    />

                    <div
                      className="
                        mt-6
                        p-5
                        rounded-[20px]
                        bg-[#EFF6F0]
                        border
                        border-[#C8DDCE]
                      "
                    >
                      <p className="font-bold">
                        Why MAE and RMSE?
                      </p>

                      <p
                        className="
                          text-sm
                          text-[#65756C]
                          mt-2
                          leading-relaxed
                        "
                      >
                        They remain interpretable
                        when the true queue is zero,
                        unlike percentage error.
                      </p>
                    </div>
                  </div>
                )}
              </PaperCard>
            </section>
          </div>
        )}

        {tab === "system" && (
          <div className="mt-6 space-y-6">
            <SectionHeading
              kicker="SYSTEM"
              title="From camera to cafeteria insight"
              description="
                Q-SENSE publishes derived queue
                metrics to the public dashboard;
                it does not need to publish the
                live video feed.
              "
            />

            <section
              className="
                grid
                lg:grid-cols-4
                gap-4
              "
            >
              <ArchitectureCard
                number="01"
                icon={<Camera />}
                title="Camera node"
                text="
                  ESP32-S3 N16R8 + OV5640
                  captures the queue view.
                "
                color="tomato"
              />

              <ArchitectureCard
                number="02"
                icon={<Activity />}
                title="Queue engine"
                text="
                  YOLO detects people and
                  ByteTrack assigns temporary
                  movement IDs.
                "
                color="mustard"
              />

              <ArchitectureCard
                number="03"
                icon={<Database />}
                title="Supabase"
                text="
                  Stores live counts, sessions,
                  menus, and validation metrics.
                "
                color="sage"
              />

              <ArchitectureCard
                number="04"
                icon={<Radio />}
                title="Public dashboard"
                text="
                  Next.js on Vercel shows the
                  live and historical analytics.
                "
                color="blue"
              />
            </section>

            <section
              className="
                grid
                xl:grid-cols-2
                gap-5
              "
            >
              <PaperCard>
                <SectionTitle
                  eyebrow="Privacy"
                  title="What Q-SENSE does not do"
                  icon={<ShieldCheck />}
                />

                <div
                  className="
                    mt-6
                    grid
                    sm:grid-cols-2
                    gap-3
                  "
                >
                  <PrivacyItem>
                    No facial recognition
                  </PrivacyItem>

                  <PrivacyItem>
                    No student names
                  </PrivacyItem>

                  <PrivacyItem>
                    Temporary tracking IDs
                  </PrivacyItem>

                  <PrivacyItem>
                    Public dashboard uses
                    metrics, not identities
                  </PrivacyItem>
                </div>
              </PaperCard>

              <PaperCard>
                <SectionTitle
                  eyebrow="Scale-up"
                  title="Two physical queues"
                  icon={<Users />}
                />

                <div
                  className="
                    mt-6
                    grid
                    sm:grid-cols-2
                    gap-4
                  "
                >
                  <NodeBox
                    title="Male node"
                    online={maleOnline}
                    subtitle="Physical PoC camera"
                  />

                  <NodeBox
                    title="Female node"
                    online={femaleOnline}
                    subtitle="
                      Database and UI ready;
                      camera not installed yet.
                    "
                  />
                </div>
              </PaperCard>
            </section>

            <PaperCard>
              <SectionTitle
                eyebrow="Metric dictionary"
                title="What the system measures"
                icon={<Database />}
              />

              <div
                className="
                  mt-6
                  grid
                  sm:grid-cols-2
                  lg:grid-cols-3
                  gap-3
                "
              >
                {[
                  [
                    "Queue count",
                    "People currently inside the calibrated queue zone.",
                  ],
                  [
                    "Queue entry",
                    "Confirmed entry into the queue zone.",
                  ],
                  [
                    "Service completion",
                    "A queued track crosses the calibrated service line toward the served side.",
                  ],
                  [
                    "Abandonment",
                    "A confirmed queued track leaves without crossing the service line.",
                  ],
                  [
                    "Waiting time",
                    "Time from confirmed queue entry to service completion.",
                  ],
                  [
                    "Throughput",
                    "Service completions per minute.",
                  ],
                  [
                    "Peak queue",
                    "Maximum queue count observed in a session.",
                  ],
                  [
                    "Mean queue",
                    "Average queue count across a session.",
                  ],
                  [
                    "Median queue",
                    "Median queue count across a session.",
                  ],
                  [
                    "Congestion duration",
                    "Time spent above a chosen queue threshold.",
                  ],
                  [
                    "Queue burden",
                    "Area under the queue curve in person-minutes.",
                  ],
                  [
                    "Meals served",
                    "Service-completion count used as a proxy for meals collected.",
                  ],
                  [
                    "Menu demand",
                    "Relative queue/service demand associated with a menu session.",
                  ],
                  [
                    "Menu acceptance",
                    "Requires independent acceptance evidence; the current values are synthetic placeholders.",
                  ],
                ].map(([title, text]) => (
                  <DefinitionCard
                    key={title}
                    title={title}
                    text={text}
                  />
                ))}
              </div>
            </PaperCard>
          </div>
        )}

        <footer
          className="
            mt-12
            pt-6
            pb-3
            border-t
            border-[#DED6C7]
            flex
            flex-col
            sm:flex-row
            justify-between
            gap-3
            text-xs
            text-[#837B6F]
          "
        >
          <span>
            Q-SENSE · Queue Sensing &
            Evaluation System
          </span>

          <span>
            Proof of Concept · 2026
          </span>
        </footer>
      </div>
    </main>
  );
}

function Badge({
  children,
  color,
}: {
  children: ReactNode;
  color:
    | "tomato"
    | "sage"
    | "mustard";
}) {
  const styles = {
    tomato:
      "bg-[#FFF0EC] border-[#F4B9AD]",
    sage:
      "bg-[#EEF6EF] border-[#BCD5C3]",
    mustard:
      "bg-[#FFF4D2] border-[#EBCF76]",
  };

  return (
    <span
      className={`
        px-3
        py-1.5
        rounded-full
        border
        text-[11px]
        font-black
        tracking-[0.08em]
        ${styles[color]}
      `}
    >
      {children}
    </span>
  );
}

function SystemStatus({
  online,
}: {
  online: boolean;
}) {
  return (
    <div
      className={`
        px-4
        py-2.5
        rounded-full
        border
        flex
        items-center
        gap-2
        text-sm
        font-bold
        ${
          online
            ?
              "bg-[#EEF6EF] border-[#BBD5C3] text-[#356447]"
            :
              "bg-[#FFF0EC] border-[#F4B9AD] text-[#A84134]"
        }
      `}
    >
      <span
        className={`
          w-2
          h-2
          rounded-full
          ${
            online
              ?
                "bg-[#4D9362] animate-pulse"
              :
                "bg-[#D95B49]"
          }
        `}
      />

      {
        online
          ? "SYSTEM ONLINE"
          : "SYSTEM OFFLINE"
      }
    </div>
  );
}

function CameraCard({
  title,
  subtitle,
  online,
  count,
  age,
  accent,
  placeholder = false,
}: {
  title: string;
  subtitle: string;
  online: boolean;
  count: number;
  age: number;
  accent: "tomato" | "blue";
  placeholder?: boolean;
}) {
  const stripe =
    accent === "tomato"
      ? "bg-[#E86652]"
      : "bg-[#5E87A4]";

  return (
    <div
      className="
        bg-white
        border
        border-[#DED6C7]
        rounded-[30px]
        p-6
        relative
        overflow-hidden
        shadow-[0_7px_0_#E8E0D2]
      "
    >
      <div
        className={`
          absolute
          left-0
          top-0
          bottom-0
          w-2
          ${stripe}
        `}
      />

      <div
        className="
          flex
          justify-between
          gap-4
        "
      >
        <div>
          <p
            className="
              text-sm
              text-[#7B7468]
            "
          >
            {subtitle}
          </p>

          <h3
            className="
              text-xl
              font-black
              mt-1
            "
          >
            {title}
          </h3>
        </div>

        {
          online
            ?
              <Wifi className="text-[#4D9362]" />
            :
              <WifiOff className="text-[#B7AFA3]" />
        }
      </div>

      <div
        className="
          mt-6
          flex
          items-end
          justify-between
        "
      >
        <div>
          <p
            className="
              text-5xl
              font-black
              tracking-[-0.05em]
            "
          >
            {online ? count : "—"}
          </p>

          <p
            className="
              text-sm
              text-[#81796E]
            "
          >
            {
              online
                ?
                  "people queued"
                :
                  placeholder
                    ?
                      "not installed"
                    :
                      "offline"
            }
          </p>
        </div>

        <div
          className="
            text-right
            text-xs
            text-[#8D8579]
          "
        >
          {online ? (
            <>
              <p>heartbeat</p>
              <b>{Math.round(age)}s ago</b>
            </>
          ) : (
            <b>OFFLINE</b>
          )}
        </div>
      </div>
    </div>
  );
}

function LiveChip({
  icon,
  children,
}: {
  icon: ReactNode;
  children: ReactNode;
}) {
  return (
    <div
      className="
        bg-white/10
        border
        border-white/15
        rounded-full
        px-3.5
        py-2
        flex
        items-center
        gap-2
        text-sm
        capitalize
      "
    >
      {icon}
      {children}
    </div>
  );
}

function TabButton({
  active,
  icon,
  children,
  onClick,
}: {
  active: boolean;
  icon: ReactNode;
  children: ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        px-4
        py-2.5
        rounded-[16px]
        flex
        items-center
        gap-2
        whitespace-nowrap
        font-bold
        text-sm
        transition
        ${
          active
            ?
              "bg-[#18352B] text-white"
            :
              "hover:bg-[#F2ECE1] text-[#625D54]"
        }
      `}
    >
      {icon}
      {children}
    </button>
  );
}

function PaperCard({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <section
      className="
        bg-white
        border
        border-[#DED6C7]
        rounded-[30px]
        p-5
        sm:p-7
        shadow-[0_7px_0_#E8E0D2]
      "
    >
      {children}
    </section>
  );
}

function MetricCard({
  title,
  value,
  icon,
  color,
  sub,
}: {
  title: string;
  value: string;
  icon: ReactNode;
  color:
    | "tomato"
    | "mustard"
    | "sage"
    | "blue"
    | "purple";
  sub?: string;
}) {
  const colors = {
    tomato:
      "bg-[#FFF0EC] border-[#F4B9AD]",
    mustard:
      "bg-[#FFF4D2] border-[#EACD72]",
    sage:
      "bg-[#EFF6F0] border-[#BED6C4]",
    blue:
      "bg-[#EEF4F7] border-[#C3D4DE]",
    purple:
      "bg-[#F4EFF6] border-[#D8C7DF]",
  };

  return (
    <div
      className={`
        rounded-[24px]
        border
        p-5
        ${colors[color]}
      `}
    >
      <div
        className="
          flex
          items-center
          justify-between
          gap-3
        "
      >
        <p
          className="
            text-sm
            font-bold
            text-[#6C665C]
          "
        >
          {title}
        </p>

        {icon}
      </div>

      <p
        className="
          text-3xl
          font-black
          tracking-[-0.04em]
          mt-5
        "
      >
        {value}
      </p>

      {sub && (
        <p
          className="
            text-xs
            text-[#7B7468]
            mt-1
          "
        >
          {sub}
        </p>
      )}
    </div>
  );
}

function SectionTitle({
  eyebrow,
  title,
  icon,
}: {
  eyebrow: string;
  title: string;
  icon: ReactNode;
}) {
  return (
    <div
      className="
        flex
        justify-between
        items-start
        gap-4
      "
    >
      <div>
        <p
          className="
            text-xs
            tracking-[0.14em]
            font-black
            text-[#928A7E]
          "
        >
          {eyebrow.toUpperCase()}
        </p>

        <h2
          className="
            text-2xl
            sm:text-3xl
            font-black
            tracking-[-0.03em]
            mt-1
          "
        >
          {title}
        </h2>
      </div>

      <div
        className="
          w-11
          h-11
          rounded-[16px]
          bg-[#F2ECE1]
          flex
          items-center
          justify-center
        "
      >
        {icon}
      </div>
    </div>
  );
}

function SectionHeading({
  kicker,
  title,
  description,
}: {
  kicker: string;
  title: string;
  description: string;
}) {
  return (
    <div className="max-w-3xl">
      <p
        className="
          text-xs
          tracking-[0.14em]
          font-black
          text-[#E86652]
        "
      >
        {kicker}
      </p>

      <h2
        className="
          text-3xl
          sm:text-5xl
          font-black
          tracking-[-0.05em]
          mt-2
        "
      >
        {title}
      </h2>

      <p
        className="
          text-[#726B60]
          mt-3
          leading-relaxed
        "
      >
        {description}
      </p>
    </div>
  );
}

function MiniStat({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div
      className="
        flex
        justify-between
        gap-5
        py-3
        border-b
        border-[#EEE7DB]
        last:border-0
      "
    >
      <span className="text-[#746D62]">
        {label}
      </span>

      <b>{value}</b>
    </div>
  );
}

function FlowBox({
  color,
  value,
  label,
}: {
  color:
    | "mustard"
    | "sage"
    | "blue";
  value: number;
  label: string;
}) {
  const colors = {
    mustard:
      "bg-[#FFF4D2] border-[#EACD72]",
    sage:
      "bg-[#EFF6F0] border-[#BED6C4]",
    blue:
      "bg-[#EEF4F7] border-[#C3D4DE]",
  };

  return (
    <div
      className={`
        rounded-[22px]
        border
        p-6
        text-center
        ${colors[color]}
      `}
    >
      <p className="text-4xl font-black">
        {value}
      </p>

      <p
        className="
          text-sm
          font-bold
          text-[#6E675D]
          mt-1
        "
      >
        {label}
      </p>
    </div>
  );
}

function MenuCard({
  row,
  meal,
}: {
  row: SessionMetric & {
    main_dish: string;
    meal?: Meal;
  };
  meal?: Meal;
}) {
  return (
    <article
      className="
        bg-white
        border
        border-[#DED6C7]
        rounded-[26px]
        p-5
        shadow-[0_6px_0_#E8E0D2]
      "
    >
      <div
        className="
          flex
          justify-between
          gap-4
        "
      >
        <div>
          <p
            className="
              text-xs
              font-black
              tracking-[0.1em]
              text-[#91897D]
            "
          >
            {formatShortDate(
              row.service_date
            )}
            {" · "}
            {mealLabel(
              row.meal_period
            ).toUpperCase()}
          </p>

          <h3
            className="
              text-xl
              font-black
              mt-2
            "
          >
            {row.main_dish}
          </h3>
        </div>

        <div
          className="
            w-11
            h-11
            rounded-[16px]
            bg-[#FFF4D2]
            flex
            items-center
            justify-center
          "
        >
          <UtensilsCrossed size={20} />
        </div>
      </div>

      <div
        className="
          grid
          grid-cols-2
          gap-3
          mt-5
        "
      >
        <ScoreBox
          label="Demand"
          value={row.menu_demand_index}
          color={COLORS.tomato}
        />

        <ScoreBox
          label="Demo acceptance"
          value={row.menu_acceptance_index}
          color={COLORS.sage}
        />
      </div>

      <div
        className="
          mt-5
          text-xs
          text-[#7D756A]
          leading-relaxed
        "
      >
        {meal && (
          <>
            <p>
              <b>Carb:</b>{" "}
              {meal.staple}
            </p>

            <p>
              <b>Animal:</b>{" "}
              {meal.animal_protein}
            </p>

            <p>
              <b>Vegetable:</b>{" "}
              {meal.vegetable}
            </p>

            <p>
              <b>Fruit:</b>{" "}
              {meal.fruit}
            </p>
          </>
        )}
      </div>
    </article>
  );
}

function ScoreBox({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div
      className="
        rounded-[18px]
        bg-[#FBF7EE]
        border
        border-[#E8E0D3]
        p-3
      "
    >
      <p
        className="
          text-xs
          text-[#7B7468]
        "
      >
        {label}
      </p>

      <div
        className="
          flex
          items-end
          gap-1
          mt-1
        "
      >
        <p className="text-2xl font-black">
          {value}
        </p>

        <span
          className="
            text-xs
            mb-1
            text-[#81796E]
          "
        >
          /100
        </span>
      </div>

      <div
        className="
          h-2
          rounded-full
          bg-[#E8E0D3]
          overflow-hidden
          mt-3
        "
      >
        <div
          className="
            h-full
            rounded-full
          "
          style={{
            width: `${value}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

function MenuTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{
    payload?: {
      main_dish?: string;
      menu_demand_index?: number;
      menu_acceptance_index?: number;
    };
  }>;
}) {
  if (!active || !payload?.length) {
    return null;
  }

  const data = payload[0]?.payload;

  return (
    <div
      className="
        bg-white
        border
        border-[#DED6C7]
        rounded-[16px]
        p-3
        shadow-xl
        text-sm
      "
    >
      <b>{data?.main_dish}</b>

      <p className="mt-1 text-[#716A60]">
        Demand: {data?.menu_demand_index}
      </p>

      <p className="text-[#716A60]">
        Demo acceptance:{" "}
        {data?.menu_acceptance_index}
      </p>
    </div>
  );
}

function ValidationRow({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div>
      <div
        className="
          flex
          justify-between
          gap-4
        "
      >
        <span>{label}</span>
        <b>{value}</b>
      </div>

      <div
        className="
          h-3
          rounded-full
          bg-[#EEE7DB]
          overflow-hidden
          mt-2
        "
      >
        <div
          className="
            h-full
            rounded-full
          "
          style={{
            width:
              `${Math.min(100, value * 2)}%`,
            backgroundColor: color,
          }}
        />
      </div>
    </div>
  );
}

function ArchitectureCard({
  number,
  icon,
  title,
  text,
  color,
}: {
  number: string;
  icon: ReactNode;
  title: string;
  text: string;
  color:
    | "tomato"
    | "mustard"
    | "sage"
    | "blue";
}) {
  const colors = {
    tomato:
      "bg-[#FFF0EC] border-[#F4B9AD]",
    mustard:
      "bg-[#FFF4D2] border-[#EACD72]",
    sage:
      "bg-[#EFF6F0] border-[#BED6C4]",
    blue:
      "bg-[#EEF4F7] border-[#C3D4DE]",
  };

  return (
    <article
      className={`
        rounded-[28px]
        border
        p-6
        ${colors[color]}
      `}
    >
      <div
        className="
          flex
          justify-between
          items-center
        "
      >
        <span
          className="
            text-xs
            font-black
            tracking-[0.12em]
          "
        >
          {number}
        </span>

        {icon}
      </div>

      <h3
        className="
          text-xl
          font-black
          mt-8
        "
      >
        {title}
      </h3>

      <p
        className="
          text-sm
          text-[#6F685D]
          mt-2
          leading-relaxed
        "
      >
        {text}
      </p>
    </article>
  );
}

function PrivacyItem({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div
      className="
        rounded-[18px]
        bg-[#EFF6F0]
        border
        border-[#C7DDCC]
        p-4
        flex
        items-start
        gap-3
      "
    >
      <Check
        size={18}
        className="shrink-0 mt-0.5"
      />

      <span
        className="
          text-sm
          font-semibold
        "
      >
        {children}
      </span>
    </div>
  );
}

function NodeBox({
  title,
  subtitle,
  online,
}: {
  title: string;
  subtitle: string;
  online: boolean;
}) {
  return (
    <div
      className="
        rounded-[20px]
        border
        border-[#E3DBCE]
        p-5
        bg-[#FBF7EE]
      "
    >
      <div
        className="
          flex
          justify-between
          gap-3
        "
      >
        <b>{title}</b>

        {
          online
            ?
              <Wifi
                size={18}
                className="text-[#4D9362]"
              />
            :
              <WifiOff
                size={18}
                className="text-[#A69E91]"
              />
        }
      </div>

      <p
        className="
          text-sm
          text-[#756E63]
          mt-2
        "
      >
        {subtitle}
      </p>

      <p
        className={`
          text-xs
          font-black
          mt-4
          ${
            online
              ?
                "text-[#4D9362]"
              :
                "text-[#A69E91]"
          }
        `}
      >
        {online ? "ONLINE" : "OFFLINE"}
      </p>
    </div>
  );
}

function DefinitionCard({
  title,
  text,
}: {
  title: string;
  text: string;
}) {
  return (
    <div
      className="
        rounded-[18px]
        border
        border-[#E5DDCF]
        p-4
        bg-[#FBF7EE]
      "
    >
      <b>{title}</b>

      <p
        className="
          text-sm
          text-[#716A60]
          mt-2
          leading-relaxed
        "
      >
        {text}
      </p>
    </div>
  );
}

function EmptyState({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <div
      className="
        py-20
        text-center
        text-[#8B8377]
      "
    >
      <Database
        size={30}
        className="mx-auto mb-3"
      />

      {children}
    </div>
  );
}

function Th({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <th
      className="
        py-3
        pr-5
        font-bold
      "
    >
      {children}
    </th>
  );
}

function Td({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <td
      className="
        py-4
        pr-5
      "
    >
      {children}
    </td>
  );
}

const tooltipStyle = {
  background: "#FFFDF7",
  border: "1px solid #DED6C7",
  borderRadius: "14px",
  color: "#18352B",
};

function formatWait(seconds: number) {
  if (!Number.isFinite(seconds)) {
    return "—";
  }

  if (seconds < 60) {
    return `${seconds.toFixed(0)} sec`;
  }

  return `${(seconds / 60).toFixed(1)} min`;
}

function ageSeconds(
  row: LiveStatus | undefined,
  now: number
) {
  if (!row) {
    return 999;
  }

  return Math.max(
    0,
    (
      now
      -
      new Date(row.updated_at).getTime()
    )
    / 1000
  );
}

function mealLabel(meal: string) {
  if (meal === "breakfast") {
    return "Breakfast";
  }

  if (meal === "lunch") {
    return "Lunch";
  }

  if (meal === "dinner") {
    return "Dinner";
  }

  if (meal === "test") {
    return "Test mode";
  }

  return meal.replaceAll("_", " ");
}

function mealShort(meal: string) {
  if (meal === "breakfast") {
    return "B";
  }

  if (meal === "lunch") {
    return "L";
  }

  if (meal === "dinner") {
    return "D";
  }

  return meal;
}

function formatShortDate(value: string) {
  return new Date(
    `${value}T00:00:00`
  ).toLocaleDateString(
    "en-GB",
    {
      day: "2-digit",
      month: "short",
    }
  );
}

function formatLongDate(value: string) {
  return new Date(
    `${value}T00:00:00`
  ).toLocaleDateString(
    "en-GB",
    {
      day: "numeric",
      month: "short",
      year: "numeric",
    }
  );
}
