"""n8n Code node — Parse Agent Output (JavaScript).

Paste into a Code node between AI Agent and Draw Shapes.
"""

const prev = $('Label Candles').item;
const agentJson = $input.item.json;

let text = agentJson.output ?? agentJson.text ?? agentJson.response ?? '';
if (typeof text !== 'string') {
  text = JSON.stringify(text);
}
text = text.trim()
  .replace(/^```(?:json)?\s*/i, '')
  .replace(/\s*```$/i, '')
  .trim();

let parsed;
try {
  parsed = JSON.parse(text);
} catch (e) {
  const m = text.match(/\{[\s\S]*\}/);
  if (!m) {
    throw new Error('Agent did not return JSON. Got: ' + text.slice(0, 300));
  }
  parsed = JSON.parse(m[0]);
}

let cmds = Array.isArray(parsed) ? parsed : parsed.draw_commands;
if (!Array.isArray(cmds)) {
  throw new Error('draw_commands missing in agent output: ' + text.slice(0, 300));
}

cmds = cmds.map((c) => {
  if (!c || typeof c !== 'object') return c;
  const out = { ...c };
  if (!out.shape && out.type) out.shape = out.type;
  delete out.type;
  return out;
});

const json = {
  ...prev.json,
  draw_commands: cmds,
  agent_raw: text,
};
const out = { json };
if (prev.binary) {
  out.binary = prev.binary;
}
return [out];
