"use client";

import { cn } from "cn";
import { useEffect, useMemo, useRef } from "react";

import { ROW_HEIGHT } from "@/lib/chart-theme";
import { usePrefersReducedMotion } from "@/lib/use-reduced-motion";

import { buildBarOption, chartSummary, type BarChartInput } from "./bar-option";
import { echarts } from "./echarts";

type Props = Omit<BarChartInput, "animate"> & {
  /** Hold the previous render at reduced opacity while a new period loads. No skeleton, no jump. */
  refetching?: boolean;
};

export function DeptBarChart({ refetching = false, ...input }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const chart = useRef<ReturnType<typeof echarts.init> | null>(null);
  const reduceMotion = usePrefersReducedMotion();

  const { name, unit, precision, target, rows, highlight } = input;
  const option = useMemo(
    () => buildBarOption({ name, unit, precision, target, rows, highlight, animate: !reduceMotion }),
    [name, unit, precision, target, rows, highlight, reduceMotion],
  );

  useEffect(() => {
    const element = host.current;
    if (!element) return;
    const instance = echarts.init(element, undefined, { renderer: "svg" });
    chart.current = instance;
    const observer = new ResizeObserver(() => instance.resize());
    observer.observe(element);
    return () => {
      observer.disconnect();
      instance.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    chart.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      role="img"
      aria-label={chartSummary({ name, unit, precision, target, rows, animate: false })}
      className={cn("w-full transition-opacity", refetching && "opacity-60")}
      style={{ height: rows.length * ROW_HEIGHT + 60 }}
    >
      <div ref={host} className="size-full" />
    </div>
  );
}
