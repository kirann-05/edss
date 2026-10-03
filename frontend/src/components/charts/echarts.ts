// Only the ECharts pieces we use, so the bundle stays small. The SVG renderer keeps text crisp
// at any zoom and prints cleanly, which matters for a projector and for the PDF export.
import { BarChart } from "echarts/charts";
import { GridComponent, MarkLineComponent, TooltipComponent } from "echarts/components";
import * as echarts from "echarts/core";
import { SVGRenderer } from "echarts/renderers";

echarts.use([BarChart, GridComponent, MarkLineComponent, TooltipComponent, SVGRenderer]);

export { echarts };
