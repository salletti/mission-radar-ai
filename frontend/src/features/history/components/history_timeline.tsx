import type { ActivityEvent } from "@/features/history/types/activity_event";
import HistoryDateHeader from "./history_date_header";
import HistoryItem from "./history_item";

function toDateKey(isoDate: string): string {
  return isoDate.split("T")[0];
}

function groupByDate(items: ActivityEvent[]): [string, ActivityEvent[]][] {
  const groups = new Map<string, ActivityEvent[]>();
  for (const item of items) {
    const key = toDateKey(item.occurred_at);
    const group = groups.get(key) ?? [];
    group.push(item);
    groups.set(key, group);
  }
  return Array.from(groups.entries());
}

const containerStyle: React.CSSProperties = {
  display: "flex",
  flexDirection: "column",
};

interface HistoryTimelineProps {
  items: ActivityEvent[];
}

export default function HistoryTimeline({ items }: HistoryTimelineProps) {
  const groups = groupByDate(items);

  return (
    <div style={containerStyle}>
      {groups.map(([date, events]) => (
        <div key={date}>
          <HistoryDateHeader date={`${date}T00:00:00Z`} />
          {events.map((event) => (
            <HistoryItem key={event.mission_match_id} event={event} />
          ))}
        </div>
      ))}
    </div>
  );
}
