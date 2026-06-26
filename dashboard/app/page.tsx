import type { DriftEvent } from "@/app/lib/types";
import DriftCard from "@/app/components/DriftCard";
import ServiceHeatmap from "@/app/components/ServiceHeatmap";

async function getDriftEvents(): Promise<DriftEvent[]> {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/drift-history`, {
    cache: "no-store",
  });
  if (!res.ok) return [];
  return res.json();
}

export default async function Page() {
  const events = await getDriftEvents();

  return (
    <main className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-4xl mx-auto px-4 py-10">
        <div className="mb-8">
          <h1 className="text-2xl font-bold tracking-tight">Interstellar</h1>
          <p className="text-sm text-zinc-400 mt-1">
            Intent vs. execution drift — {events.length} event{events.length !== 1 ? "s" : ""}
          </p>
        </div>

        <div className="flex flex-col gap-8">
          {events.length > 0 && <ServiceHeatmap events={events} />}

          <section>
            <h2 className="text-sm font-semibold text-zinc-400 mb-4 uppercase tracking-wider">
              Drift Feed
            </h2>
            {events.length === 0 ? (
              <div className="rounded-lg border border-zinc-800 bg-zinc-900 p-8 text-center">
                <p className="text-zinc-500 text-sm">No drift events detected yet.</p>
                <p className="text-zinc-600 text-xs mt-1">Merge a PR to trigger analysis.</p>
              </div>
            ) : (
              <div className="flex flex-col gap-4">
                {events.map((event) => (
                  <DriftCard key={event.id} event={event} />
                ))}
              </div>
            )}
          </section>
        </div>
      </div>
    </main>
  );
}
