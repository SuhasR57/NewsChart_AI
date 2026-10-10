import { useMemo } from "react";
import Plot from "react-plotly.js";

export default function AnalysisChart({ chart }) {
    // Plotly can mutate figure objects. Give it a separate copy
    // so the API result used for downloads stays unchanged.
    const figure = useMemo(
        () => (chart ? JSON.parse(JSON.stringify(chart)) : null),
        [chart]
    );

    if (!figure?.data?.length) {
        return <p>No chart data is available.</p>;
    }

    return (
        <section className="result-panel" aria-label="Interactive chart">
            <h2>Chart</h2>

            <Plot
                data={figure.data}
                layout={{
                    ...figure.layout,
                    autosize: true,
                    width: undefined,
                    height: 440,
                    margin: {
                        ...figure.layout?.margin,
                        l: 70,
                        r: 30,
                        t: 80,
                        b: 70,
                    },
                }}
                config={{
                    responsive: true,
                    displaylogo: false,
                    scrollZoom: false,
                    toImageButtonOptions: {
                        format: "png",
                        filename: "newschart-chart",
                    },
                }}
                useResizeHandler
                style={{ width: "100%", height: "440px" }}
            />

            <p className="hint">
                Hover to inspect values. Drag to zoom and double-click to reset.
            </p>
        </section>
    );
}