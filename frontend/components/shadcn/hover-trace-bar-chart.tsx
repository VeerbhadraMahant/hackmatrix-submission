"use client";

import {
  Bar,
  BarChart,
  Rectangle,
  ReferenceLine,
  Tooltip,
  XAxis,
  type BarShapeProps,
  type CartesianViewBox,
} from "recharts";
import {
  type ChartConfig,
  ChartContainer,
} from "@/components/shadcn/hover-trace-bar-chart-utils/recharts-chart";
import { useMotionValueEvent, useSpring } from "motion/react";
import NumberFlow from "@number-flow/react";
import * as React from "react";

const CHART_MARGIN = 38;

export interface HoverTracePoint {
  month: string;
  amount: number;
}

const SAMPLE: HoverTracePoint[] = [
  { month: "January", amount: 342 },
  { month: "February", amount: 676 },
  { month: "March", amount: 512 },
  { month: "April", amount: 629 },
  { month: "May", amount: 458 },
  { month: "June", amount: 781 },
];

const chartConfig = {
  amount: {
    label: "Value",
    colors: {
      light: ["#5f7f0c"],
      dark: ["#c6f135"],
    },
  },
} satisfies ChartConfig;

export function EvilHoverTraceBarChart({
  data = SAMPLE,
  label = "Value",
  currency = "INR",
}: {
  data?: HoverTracePoint[];
  label?: string;
  currency?: string;
}) {
  const [activeIndex, setActiveIndex] = React.useState<number | null>(null);

  const maxData = React.useMemo(
    () =>
      data.reduce(
        (max, item, index) =>
          item.amount > max.value ? { index, month: item.month, value: item.amount } : max,
        { index: 0, month: data[0]?.month ?? "", value: data[0]?.amount ?? 0 },
      ),
    [data],
  );

  const selectedData =
    activeIndex != null && data[activeIndex]
      ? { index: activeIndex, month: data[activeIndex].month, value: data[activeIndex].amount }
      : maxData;

  const valueSpring = useSpring(selectedData.value, {
    stiffness: 110,
    damping: 20,
  });
  const [springValue, setSpringValue] = React.useState(selectedData.value);

  // Data can change after mount (e.g. fetched); keep the trace line in sync.
  React.useEffect(() => {
    valueSpring.set(maxData.value);
  }, [maxData.value, valueSpring]);

  const handleBarHover = React.useCallback(
    (index: number) => {
      setActiveIndex(index);
      valueSpring.set(data[index]?.amount ?? maxData.value);
    },
    [data, maxData.value, valueSpring],
  );

  useMotionValueEvent(valueSpring, "change", (latest) => {
    setSpringValue(Math.round(latest));
  });

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-4 flex items-end justify-between">
        <div className="space-y-1">
          <p className="text-muted-foreground font-mono text-xs">{`[${label.toLowerCase()}]`}</p>
          <p className="text-primary font-mono text-3xl tracking-tighter">
            <NumberFlow
              value={selectedData.value}
              format={{
                style: "currency",
                currency,
                currencyDisplay: "narrowSymbol",
                maximumFractionDigits: 0,
              }}
            />
          </p>
        </div>

        <div className="space-y-1 text-right">
          <p className="text-muted-foreground font-mono text-[10px]">{"[month]"}</p>
          <p className="text-primary font-mono text-xs">{selectedData.month}</p>
        </div>
      </div>

      <ChartContainer config={chartConfig}>
        <BarChart
          accessibilityLayer
          data={data}
          margin={{ left: CHART_MARGIN }}
          onMouseMove={(state) => {
            if (state?.activeTooltipIndex != null) {
              handleBarHover(Number(state.activeTooltipIndex));
            }
          }}
          onMouseLeave={() => {
            setActiveIndex(null);
            valueSpring.set(maxData.value);
          }}
        >
          <XAxis
            dataKey="month"
            tickLine={false}
            tickMargin={10}
            axisLine={false}
            tickFormatter={(value: string) => value.slice(0, 3)}
          />

          <Tooltip cursor={false} content={() => null} />

          <Bar
            dataKey="amount"
            fill="var(--color-amount-0)"
            radius={4}
            shape={(props: BarShapeProps) => (
              <HoverTraceBarShape {...props} highlightedIndex={selectedData.index} />
            )}
            activeBar={(props: BarShapeProps) => (
              <HoverTraceBarShape {...props} highlightedIndex={selectedData.index} />
            )}
          />

          <ReferenceLine
            y={springValue}
            stroke="var(--foreground)"
            strokeDasharray="3 3"
            label={<HoverTraceLabel value={selectedData.value} />}
          />
        </BarChart>
      </ChartContainer>
    </div>
  );
}

interface HoverTraceLabelProps {
  viewBox?: CartesianViewBox;
  value: number;
}

const HoverTraceLabel = ({ viewBox, value }: HoverTraceLabelProps) => {
  const x = viewBox?.x ?? 0;
  const y = viewBox?.y ?? 0;
  const formattedValue = value.toLocaleString();
  const width = formattedValue.length * 8 + 12;

  return (
    <>
      <rect x={x - CHART_MARGIN} y={y - 9} width={width} height={18} fill="#a6d11a" rx={4} />
      <text
        className="font-mono text-[11px]"
        fontWeight={600}
        x={x - CHART_MARGIN + 7}
        y={y + 4}
        fill="#0d0d0d"
      >
        {formattedValue}
      </text>
      <ellipse cx={"99.5%"} cy={y} rx={3} ry={3} fill="#5f7f0c" />
    </>
  );
};

type HoverTraceBarShapeProps = BarShapeProps & {
  highlightedIndex: number;
};

const HoverTraceBarShape = (props: HoverTraceBarShapeProps) => {
  const { x, y, width, height, fill, index, isActive, highlightedIndex } = props;

  const fillOpacity = isActive || index === highlightedIndex ? 1 : 0.2;

  return (
    <g>
      <Rectangle {...props} fill="transparent" pointerEvents="all" />
      <Rectangle
        x={x}
        y={y}
        width={width}
        height={height}
        radius={4}
        fill={fill}
        fillOpacity={fillOpacity}
        stroke={isActive ? "var(--foreground)" : undefined}
        strokeOpacity={isActive ? 0.35 : undefined}
        strokeWidth={isActive ? 1 : undefined}
        className="transition-opacity duration-200"
      />
    </g>
  );
};

export default EvilHoverTraceBarChart;
