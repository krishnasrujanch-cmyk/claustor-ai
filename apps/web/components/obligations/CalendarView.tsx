"use client";
import { useState, useMemo } from "react";
import { C } from "@/lib/design-tokens";

interface Obligation {
  id: string;
  title: string;
  obligation_type: string;
  due_date: string;
  status: string;
  contract_title: string;
  contract_id: string;
  urgency: string;
}

interface Props {
  obligations: Obligation[];
  onMarkComplete: (id: string) => void;
}

const URGENCY_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  overdue:  { bg: "#FEE2E2", text: "#991B1B", dot: "#DC2626" },
  urgent:   { bg: "#FEF3C7", text: "#92400E", dot: "#F59E0B" },
  upcoming: { bg: "#DBEAFE", text: "#1E40AF", dot: "#3B82F6" },
  normal:   { bg: "#F0FDF4", text: "#166534", dot: "#22C55E" },
};

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December"];

function getUrgency(dueDate: string): string {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate);
  due.setHours(0, 0, 0, 0);
  const diff = Math.ceil((due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24));
  if (diff < 0) return "overdue";
  if (diff <= 7) return "urgent";
  if (diff <= 30) return "upcoming";
  return "normal";
}

export function CalendarView({ obligations, onMarkComplete }: Props) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const year = currentDate.getFullYear();
  const month = currentDate.getMonth();

  const prevMonth = () => setCurrentDate(new Date(year, month - 1, 1));
  const nextMonth = () => setCurrentDate(new Date(year, month + 1, 1));
  const goToday = () => setCurrentDate(new Date());

  const obsByDate = useMemo(() => {
    const map: Record<string, Obligation[]> = {};
    obligations.forEach(ob => {
      if (!ob.due_date) return;
      const key = ob.due_date.slice(0, 10);
      if (!map[key]) map[key] = [];
      map[key].push(ob);
    });
    return map;
  }, [obligations]);

  const firstDay = new Date(year, month, 1).getDay();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayStr = today.toISOString().slice(0, 10);

  const weeks: (number | null)[][] = [];
  let week: (number | null)[] = Array(firstDay).fill(null);
  for (let d = 1; d <= daysInMonth; d++) {
    week.push(d);
    if (week.length === 7) { weeks.push(week); week = []; }
  }
  if (week.length > 0) {
    while (week.length < 7) week.push(null);
    weeks.push(week);
  }

  const dateKey = (d: number) => `${year}-${String(month + 1).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
  const selectedObs = selectedDay ? (obsByDate[selectedDay] || []) : [];

  const monthObs = obligations.filter(ob => {
    if (!ob.due_date) return false;
    const d = new Date(ob.due_date);
    return d.getFullYear() === year && d.getMonth() === month;
  });
  const overdueCount = monthObs.filter(ob => getUrgency(ob.due_date) === "overdue").length;
  const urgentCount = monthObs.filter(ob => getUrgency(ob.due_date) === "urgent").length;

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 16 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <button onClick={prevMonth} style={{ padding: "6px 12px", borderRadius: 8,
            border: "1px solid #E2E8F0", background: "white", cursor: "pointer",
            fontSize: 16, color: "#64748B" }}>&#8592;</button>
          <h2 style={{ fontSize: 18, fontWeight: 700, color: C.heading, margin: 0, minWidth: 200,
            textAlign: "center" }}>{MONTHS[month]} {year}</h2>
          <button onClick={nextMonth} style={{ padding: "6px 12px", borderRadius: 8,
            border: "1px solid #E2E8F0", background: "white", cursor: "pointer",
            fontSize: 16, color: "#64748B" }}>&#8594;</button>
          <button onClick={goToday} style={{ padding: "6px 10px", borderRadius: 8,
            border: "1px solid #E2E8F0", background: "white", cursor: "pointer",
            fontSize: 12, color: C.primary, fontWeight: 600 }}>Today</button>
        </div>
        <div style={{ display: "flex", gap: 16, fontSize: 12 }}>
          <span style={{ color: "#DC2626", fontWeight: 600 }}>&#9679; {overdueCount} overdue</span>
          <span style={{ color: "#F59E0B", fontWeight: 600 }}>&#9679; {urgentCount} urgent</span>
          <span style={{ color: "#64748B" }}>&#9679; {monthObs.length} total this month</span>
        </div>
      </div>

      <div style={{ display: "flex", gap: 20 }}>
        <div style={{ flex: 1 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", tableLayout: "fixed" }}>
            <thead>
              <tr>
                {DAYS.map(d => (
                  <th key={d} style={{ padding: "8px 4px", fontSize: 11, fontWeight: 600,
                    color: C.muted, textTransform: "uppercase", textAlign: "center",
                    borderBottom: "2px solid #E2E8F0" }}>{d}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {weeks.map((week, wi) => (
                <tr key={wi}>
                  {week.map((day, di) => {
                    if (day === null) return <td key={di} style={{ border: "1px solid #F1F5F9", height: 80 }} />;
                    const dk = dateKey(day);
                    const dayObs = obsByDate[dk] || [];
                    const isToday = dk === todayStr;
                    const isSelected = dk === selectedDay;
                    const hasOverdue = dayObs.some(o => getUrgency(o.due_date) === "overdue");

                    return (
                      <td key={di} onClick={() => setSelectedDay(isSelected ? null : dk)}
                        style={{
                          border: "1px solid #F1F5F9", padding: 4, height: 80, verticalAlign: "top",
                          cursor: dayObs.length > 0 ? "pointer" : "default",
                          background: isSelected ? "#EFF6FF" : isToday ? "#FEFCE8" : "white",
                          transition: "background 0.15s",
                        }}>
                        <div style={{ fontSize: 12, fontWeight: isToday ? 700 : 400,
                          color: isToday ? C.primary : C.text, marginBottom: 2,
                          textAlign: "right", paddingRight: 4 }}>{day}</div>
                        {dayObs.slice(0, 3).map((ob, oi) => {
                          const u = getUrgency(ob.due_date);
                          const colors = URGENCY_COLORS[u] || URGENCY_COLORS.normal;
                          return (
                            <div key={oi} style={{
                              fontSize: 10, padding: "1px 4px", marginBottom: 1,
                              borderRadius: 3, background: colors.bg, color: colors.text,
                              overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                              fontWeight: 500,
                            }}>{ob.title.slice(0, 20)}</div>
                          );
                        })}
                        {dayObs.length > 3 && (
                          <div style={{ fontSize: 10, color: C.muted, paddingLeft: 4 }}>+{dayObs.length - 3} more</div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedDay && (
          <div style={{ width: 320, borderLeft: "1px solid #E2E8F0", paddingLeft: 20, flexShrink: 0 }}>
            <h3 style={{ fontSize: 14, fontWeight: 700, color: C.heading, marginBottom: 12 }}>
              {new Date(selectedDay + "T00:00:00").toLocaleDateString("en-US",
                { weekday: "long", month: "long", day: "numeric" })}
            </h3>
            {selectedObs.length === 0 ? (
              <p style={{ color: C.muted, fontSize: 13 }}>No obligations on this day</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {selectedObs.map(ob => {
                  const u = getUrgency(ob.due_date);
                  const colors = URGENCY_COLORS[u] || URGENCY_COLORS.normal;
                  return (
                    <div key={ob.id} style={{ padding: 12, borderRadius: 8,
                      border: "1px solid #E2E8F0", background: "white",
                      borderLeft: `3px solid ${colors.dot}` }}>
                      <div style={{ fontSize: 13, fontWeight: 600, color: C.text, marginBottom: 4 }}>{ob.title}</div>
                      <div style={{ fontSize: 11, color: C.muted, marginBottom: 4 }}>{ob.contract_title}</div>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span style={{ fontSize: 10, padding: "2px 6px", borderRadius: 4,
                          background: colors.bg, color: colors.text, fontWeight: 600,
                          textTransform: "uppercase" }}>{u}</span>
                        <span style={{ fontSize: 11, color: C.muted }}>{ob.obligation_type}</span>
                      </div>
                      {ob.status !== "completed" && (
                        <button onClick={(e) => { e.stopPropagation(); onMarkComplete(ob.id); }}
                          style={{ marginTop: 8, fontSize: 11, padding: "4px 10px",
                            borderRadius: 6, border: "1px solid #22C55E", background: "#F0FDF4",
                            color: "#16A34A", cursor: "pointer", fontWeight: 600 }}>
                          &#10003; Mark Complete
                        </button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
