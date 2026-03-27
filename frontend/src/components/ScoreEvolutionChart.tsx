"use client";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

interface Point {
  date: string;
  catalog_score: number;
  text_score: number;
  visual_score: number;
}

export default function ScoreEvolutionChart({ data }: { data: Point[] }) {
  if (!data.length) return null;
  return (
    <div className="card" style={{ marginBottom: 24 }}>
      <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 20, color: "var(--text-muted)" }}>
        EVOLUTION 30 JOURS
      </h2>
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={data}>
          <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: "var(--text-faint)" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "var(--text-faint)" }}
            tickLine={false}
            axisLine={false}
            width={28}
          />
          <Tooltip
            contentStyle={{
              background: "var(--bg)",
              border: "1px solid var(--border)",
              borderRadius: 8,
              fontSize: 12,
            }}
          />
          <Line dataKey="catalog_score" stroke="#10b981" strokeWidth={2} dot={false} name="Catalogue" />
          <Line dataKey="text_score" stroke="var(--score-text)" strokeWidth={1.5} dot={false} name="Texte" />
          <Line dataKey="visual_score" stroke="var(--score-visual)" strokeWidth={1.5} dot={false} name="Visuel" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
