export interface DataPoint {
  id: string | number;
  label: string;
  subLabel?: string;
  values: (string | number)[]; // Flexible columns
  variant?: "primary" | "secondary" | "danger" | "neutral";
}

interface DataTableProps {
  title: string;
  description?: string;
  headers: string[];
  data: DataPoint[];
  onAction?: (point: DataPoint) => void;
  actionLabel?: string;
}

export default function DataTable({
  title,
  description,
  headers,
  data,
  onAction,
  actionLabel = "VIEW",
}: DataTableProps) {
  const getVariantColor = (variant?: string) => {
    switch (variant) {
      case "primary":
        return "bg-blue-500 shadow-[0_0_8px_#3b82f6]";
      case "danger":
        return "bg-red-500 shadow-[0_0_8px_#ef4444]";
      case "secondary":
        return "bg-emerald-500 shadow-[0_0_8px_#10b981]";
      default:
        return "bg-zinc-600";
    }
  };

  return (
    <div className="bg-zinc-950 px-4 py-6 border border-zinc-800 rounded-xl">
      {/* Header Section */}
      <div className="mb-6">
        <h2 className="text-sm font-black uppercase tracking-widest text-white">
          {title}
        </h2>
        {description && (
          <p className="text-[10px] font-mono text-zinc-500 uppercase mt-1">
            {description}
          </p>
        )}
      </div>

      {/* Table Section */}
      <div className="flow-root">
        <div className="-mx-4 overflow-x-auto custom-scrollbar">
          <div className="inline-block min-w-full align-middle px-4">
            <table className="min-w-full divide-y divide-zinc-800">
              <thead>
                <tr className="text-left text-[9px] font-bold uppercase tracking-tighter text-zinc-500">
                  <th className="py-3 px-2">Ref</th>
                  {headers.map((header) => (
                    <th key={header} className="px-3 py-3 font-mono">
                      {header}
                    </th>
                  ))}
                  {onAction && (
                    <th className="relative py-3 pl-3 pr-4 sm:pr-0"></th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-900">
                {data.map((item) => (
                  <tr
                    key={item.id}
                    className="hover:bg-zinc-900/40 transition-colors group"
                  >
                    <td className="py-4 px-2 text-[10px] font-bold text-white whitespace-nowrap">
                      <div className="flex items-center gap-2">
                        <span
                          className={`size-1.5 rounded-full ${getVariantColor(item.variant)}`}
                        />
                        {item.label}
                      </div>
                    </td>

                    {item.values.map((val, idx) => (
                      <td
                        key={idx}
                        className="px-3 py-4 text-[11px] font-mono text-zinc-400 group-hover:text-zinc-200 whitespace-nowrap"
                      >
                        {typeof val === "number" && !Number.isInteger(val)
                          ? val.toFixed(6)
                          : val}
                      </td>
                    ))}

                    {onAction && (
                      <td className="py-4 pl-3 pr-4 text-right text-[9px] font-black whitespace-nowrap sm:pr-0">
                        <button
                          onClick={() => onAction(item)}
                          className="text-zinc-600 hover:text-blue-500 transition-colors"
                        >
                          {actionLabel}
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
