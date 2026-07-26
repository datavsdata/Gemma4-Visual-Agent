// After DuckDB Store INSERT — restore Draw Shapes item for Loop Dates / binary pass-through.
const prev = $('Draw Shapes').item;
const staged = $('Stage Store').item?.json || {};
const json = { ...(prev.json || {}) };
if (staged.stored === false) json.stored = false;
else {
  json.stored = true;
  json.results_db = '/data/candle_draw_results.duckdb';
  if (staged.image_path) json.image_path = staged.image_path;
}
const out = { json };
if (prev.binary) out.binary = prev.binary;
return [out];
