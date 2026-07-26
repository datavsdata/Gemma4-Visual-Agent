-- DuckDB OHLC (n8n expression). Always emits rows OR one _skip sentinel so Loop Dates continues.

={{ `WITH raw AS (
  SELECT * FROM read_csv_auto('/data/tips_5years.csv', header=true)
),
base AS (
  SELECT
    upper(trim(Symbol)) AS symbol,
    strptime(trim(Date), '%d-%b-%Y')::DATE AS trade_date,
    trim(Series) AS series,
    try_cast(replace(trim("Open Price"), ',', '') AS DOUBLE) AS open,
    try_cast(replace(trim("High Price"), ',', '') AS DOUBLE) AS high,
    try_cast(replace(trim("Low Price"), ',', '') AS DOUBLE) AS low,
    try_cast(replace(trim("Close Price"), ',', '') AS DOUBLE) AS close,
    try_cast(replace(trim("Prev Close"), ',', '') AS DOUBLE) AS prev_close,
    try_cast(replace(trim("Last Price"), ',', '') AS DOUBLE) AS ltp,
    try_cast(replace(trim("Average Price"), ',', '') AS DOUBLE) AS vwap,
    try_cast(replace(trim("Total Traded Quantity"), ',', '') AS DOUBLE) AS volume,
    try_cast(replace(trim("Turnover ₹"), ',', '') AS DOUBLE) AS value,
    try_cast(replace(trim("No. of Trades"), ',', '') AS DOUBLE) AS trades
  FROM raw
),
as_of AS (
  SELECT 1 AS ok FROM base
  WHERE symbol = '${$json.nse_code}' AND trade_date = DATE '${$json.date}'
),
bars AS (
  SELECT
    strftime(trade_date, '%d-%b-%Y') AS DATE,
    series AS SERIES,
    open AS OPEN,
    high AS HIGH,
    low AS LOW,
    prev_close AS "PREV. CLOSE",
    ltp AS LTP,
    close AS CLOSE,
    vwap AS VWAP,
    NULL AS "52W H",
    NULL AS "52W L",
    volume AS VOLUME,
    value AS VALUE,
    trades AS "NO. OF  TRADES",
    false AS _skip
  FROM (
    SELECT * FROM base
    WHERE symbol = '${$json.nse_code}'
      AND trade_date <= DATE '${$json.date}'
      AND EXISTS (SELECT 1 FROM as_of)
    ORDER BY trade_date DESC
    LIMIT 200
  )
  ORDER BY trade_date ASC
)
SELECT * FROM bars
UNION ALL
SELECT
  NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL, NULL,
  true AS _skip
WHERE NOT EXISTS (SELECT 1 FROM as_of)` }}
