// Run unchanged upstream checks, then require actual page coverage.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawnSync } = require('node:child_process');
const source = path.resolve(__dirname, '../design/guizang-social-card/validate-social-deck.mjs');
const hash = filename => crypto.createHash('sha256').update(fs.readFileSync(filename)).digest('hex');

if (process.argv[2] === '--upstream-worker') {
  process.argv.splice(2, 1);
  const modulePath = require.resolve('playwright', { paths: [process.env.NODE_PATH || '', process.cwd(), path.dirname(source)] });
  const upstream = fs.readFileSync(source, 'utf8');
  globalThis.__videoDesignPlaywright = require(modulePath);
  const code = upstream.replace('import { chromium } from "playwright";', 'const { chromium } = globalThis.__videoDesignPlaywright;');
  if (code === upstream) throw Error('Upstream import changed; inspect launcher compatibility');
  import('data:text/javascript;base64,' + Buffer.from(code).toString('base64')).catch(e => { console.error(e.message); process.exitCode = 1; });
} else {
  try {
    let expected = 1;
    let reportPath;
    const forwarded = [];
    for (const arg of process.argv.slice(2)) {
      if (arg.startsWith('--expected-pages=')) {
        const value = arg.slice('--expected-pages='.length);
        if (!/^[1-9][0-9]*$/.test(value) || !Number.isSafeInteger(Number(value))) throw Error('expected-pages must be a positive integer');
        expected = Number(value);
      } else if (arg.startsWith('--report=')) {
        reportPath = path.resolve(arg.slice('--report='.length));
        if (fs.existsSync(reportPath)) throw Error('Report already exists; choose a new report version');
      } else if (arg.startsWith('--') && !arg.startsWith('--style=')) {
        throw Error('Unknown option: ' + arg);
      } else forwarded.push(arg);
    }
    const target = forwarded.find(arg => !arg.startsWith('--'));
    if (!target) throw Error('Usage: node run_design_validator.cjs HTML --style=swiss --expected-pages=1 [--report=FILE.json]');
    const abs = path.resolve(target);
    const html = fs.statSync(abs).isDirectory() ? path.join(abs, 'index.html') : abs;
    const before = hash(html);
    const result = spawnSync(process.execPath, [__filename, '--upstream-worker', ...forwarded], { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 });
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    if (result.error) throw result.error;
    const summary = result.stdout.match(/^sections: (\d+)\s+·\s+(\d+) clean\s+·\s+(\d+) fails\s+·\s+(\d+) warns$/m);
    const actual = summary ? Number(summary[1]) : null;
    const stable = hash(html) === before;
    const covered = actual !== null && actual > 0 && actual === expected;
    const ok = result.status === 0 && covered && stable && Number(summary[3]) === 0;
    if (!covered) console.error(`BLOCKED: expected ${expected} section.poster page(s), checked ${actual ?? 'unknown'}. Zero or incomplete coverage is not a pass.`);
    if (!stable) console.error('BLOCKED: HTML changed during validation; rerun on the finished version.');
    if (reportPath) {
      const report = { status: ok ? 'pass' : 'fail', scope: 'upstream-static-checks-and-page-coverage',
        html, html_sha256: before, upstream_sha256: hash(source),
        expected_pages: expected, checked_pages: actual,
        fails: summary ? Number(summary[3]) : null, warnings: summary ? Number(summary[4]) : null,
        upstream_exit_code: result.status, html_unchanged: stable,
        note: 'Technical evidence only; not a visual judgment or user approval.' };
      fs.mkdirSync(path.dirname(reportPath), { recursive: true });
      fs.writeFileSync(reportPath, JSON.stringify(report, null, 2) + '\n', { flag: 'wx' });
    }
    process.exitCode = ok ? 0 : 1;
  } catch (error) {
    console.error('BLOCKED: ' + error.message);
    process.exitCode = 1;
  }
}
