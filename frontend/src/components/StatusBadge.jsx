const colors = {
  running: "bg-green-500/20 text-green-400 ring-green-500/30",
  exited: "bg-red-500/20 text-red-400 ring-red-500/30",
  stopped: "bg-gray-500/20 text-gray-400 ring-gray-500/30",
  paused: "bg-yellow-500/20 text-yellow-400 ring-yellow-500/30",
  restarting: "bg-blue-500/20 text-blue-400 ring-blue-500/30",
};

export default function StatusBadge({ status }) {
  const cls = colors[status] ?? colors.stopped;
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${cls}`}
    >
      {status}
    </span>
  );
}
