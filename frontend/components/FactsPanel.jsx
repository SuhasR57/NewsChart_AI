function formatNumber(value) {
    if (typeof value !== "number" || !Number.isFinite(value)) {
        return "Unavailable";
    }

    return new Intl.NumberFormat(undefined, {
        maximumSignificantDigits: 15,
    }).format(value);
}

function formatPeriod(value) {
    if (value == null) return "Unavailable";

    // Preserve the supplied calendar date without timezone conversion.
    return typeof value === "string"
        ? value.split("T")[0]
        : String(value);
}

function formatChange(value) {
    return `${value > 0 ? "+" : ""}${formatNumber(value)}`;
}

function ChangeList({ title, changes, unit, emptyMessage }) {
    return (
        <div>
            <h3>{title}</h3>

            {changes?.length ? (
                <ul>
                    {changes.map((change, index) => (
                        <li key={index}>
                            {formatPeriod(change.from_period)} →{" "}
                            {formatPeriod(change.to_period)}:{" "}
                            <strong>
                                {formatChange(change.absolute_change)} {unit}
                            </strong>
                        </li>
                    ))}
                </ul>
            ) : (
                <p>{emptyMessage}</p>
            )}
        </div>
    );
}

export default function FactsPanel({ facts }) {
    if (!facts) return null;

    const unit = facts.unit;
    const measurement = (value) => `${formatNumber(value)} ${unit}`;
    const percentageAvailable =
        facts.overall_percentage_change != null;

    const cards = [
        ["Observations", String(facts.observation_count)],
        [
            "Period covered",
            `${formatPeriod(facts.period_covered.start)} – ${formatPeriod(facts.period_covered.end)
            }`,
        ],
        ["First value", measurement(facts.first_value)],
        ["Last value", measurement(facts.last_value)],
        ["Mean", measurement(facts.mean)],
        ["Minimum", measurement(facts.minimum.value)],
        ["Maximum", measurement(facts.maximum.value)],
        [
            "Overall absolute change",
            `${formatChange(facts.overall_absolute_change)} ${unit}`,
        ],
    ];

    if (percentageAvailable) {
        cards.push([
            "Overall percentage change",
            `${formatChange(facts.overall_percentage_change)}%`,
        ]);
    }

    return (
        <section className="result-panel">
            <h2>Calculated facts</h2>
            <p>{facts.metric_name}</p>

            <dl className="facts-grid">
                {cards.map(([label, value]) => (
                    <div className="fact-card" key={label}>
                        <dt>{label}</dt>
                        <dd>{value}</dd>
                    </div>
                ))}
            </dl>

            <p>
                <strong>Minimum periods:</strong>{" "}
                {facts.minimum.periods.map(formatPeriod).join(", ")}
            </p>
            <p>
                <strong>Maximum periods:</strong>{" "}
                {facts.maximum.periods.map(formatPeriod).join(", ")}
            </p>

            {!percentageAvailable && (
                <p className="hint">
                    Percentage change is omitted because the starting value
                    is zero or negative. Use the absolute change instead.
                </p>
            )}

            <h3>
                {facts.adjacent_change_label === "year-over-year"
                    ? "Year-over-year changes"
                    : "Adjacent-period changes"}
            </h3>

            <ChangeList
                title="Largest increases"
                changes={facts.largest_adjacent_increases}
                unit={unit}
                emptyMessage="No adjacent increase occurred."
            />

            <ChangeList
                title="Largest decreases"
                changes={facts.largest_adjacent_decreases}
                unit={unit}
                emptyMessage="No adjacent decrease occurred."
            />

            <details>
                <summary>Calculation limitations</summary>
                <ul>
                    {facts.limitations.map((limitation, index) => (
                        <li key={index}>{limitation}</li>
                    ))}
                </ul>
            </details>

            <details>
                <summary>Full fact dictionary</summary>
                <pre>{JSON.stringify(facts, null, 2)}</pre>
            </details>
        </section>
    );
}