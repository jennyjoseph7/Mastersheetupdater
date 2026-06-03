import re

# Fix 1: Remove dead dispDefs in pre-sales
with open('pages/disposition_sync_v2.html', 'r', encoding='utf-8') as f:
    pre = f.read()

# Remove the dead dispDefs block
old_block = ('        // Build dispDefs here (needed for cache too)\n'
    '        var dispKeys = Object.keys(ALL_DISPOSITIONS);\n'
    '        var dispDefs = dispKeys.map(function(k) { return \'- \"\' + k + \'\": \' + ALL_DISPOSITIONS[k]; }).join(\'\\\\n\');\n'
    '\n'
    '        var runnerResult = await runOpenRouterBatches(runnerOpts);')
new_block = '        var runnerResult = await runOpenRouterBatches(runnerOpts);'

if old_block in pre:
    pre = pre.replace(old_block, new_block, 1)
    print("Fixed pre-sales dead code")
else:
    print("WARNING: Could not find dead dispDefs block in pre-sales")
    # Try to find it differently
    idx = pre.find('Build dispDefs here')
    if idx >= 0:
        print(f"  Found 'Build dispDefs here' at position {idx}")
        print(f"  Context: {pre[idx:idx+300]}")

with open('pages/disposition_sync_v2.html', 'w', encoding='utf-8') as f:
    f.write(pre)

# Fix 2: Remove dead callDeepSeekBatch in dashboard
with open('pages/dashboard.html', 'r', encoding='utf-8') as f:
    dash = f.read()

old_func_start = '    async function callDeepSeekBatch(systemPrompt, summaries, apiKey) {'
idx = dash.find(old_func_start)
if idx >= 0:
    # Find the closing brace by counting
    # The function ends right before the next function or section
    next_func = dash.find('\n    async function classifyWithDeepSeek', idx)
    if next_func < 0:
        next_func = dash.find('\n    async function ', idx + 5)
    
    if next_func > idx:
        # The function includes the newline before it
        # Remove from the function declaration to just before the next function
        dash = dash[:idx] + dash[next_func:]
        print("Fixed dashboard dead code (removed callDeepSeekBatch)")
    else:
        print("WARNING: Could not find end of callDeepSeekBatch in dashboard")
else:
    print("WARNING: Could not find callDeepSeekBatch in dashboard (may already be removed)")

with open('pages/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(dash)

print("Done")
