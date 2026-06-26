"use client";

import { useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL;

export default function AcknowledgeButton({ driftEventId, initialStatus }: {
  driftEventId: number;
  initialStatus: string;
}) {
  const [status, setStatus] = useState(initialStatus);
  const [loading, setLoading] = useState(false);

  if (status === "acknowledged") {
    return (
      <span className="text-xs text-green-400 font-medium">✓ Acknowledged</span>
    );
  }

  async function handleAck() {
    setLoading(true);
    try {
      const res = await fetch(`${API}/acknowledge`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ drift_event_id: driftEventId, note: "" }),
      });
      if (res.ok) setStatus("acknowledged");
    } finally {
      setLoading(false);
    }
  }

  return (
    <button
      onClick={handleAck}
      disabled={loading}
      className="text-xs px-3 py-1 rounded border border-zinc-600 text-zinc-300 hover:border-zinc-400 hover:text-white transition-colors disabled:opacity-50"
    >
      {loading ? "Acknowledging…" : "Acknowledge"}
    </button>
  );
}
