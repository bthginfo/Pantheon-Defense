import { mkdirSync, writeFileSync, existsSync } from 'node:fs';
import { homedir, tmpdir } from 'node:os';
import { delimiter, join } from 'node:path';
import { spawnSync } from 'node:child_process';

const bin = join(homedir(), '.cargo', 'bin');
process.env.PATH = [bin, process.env.PATH].join(delimiter);

function run(command, args) {
  const result = spawnSync(command, args, { stdio: 'inherit', env: process.env });
  if (result.error || result.status !== 0) {
    throw new Error(`${command} ${args.join(' ')} failed`, { cause: result.error });
  }
}

if (spawnSync('cargo', ['--version']).status !== 0) {
  const installer = join(tmpdir(), 'pantheon-rustup.sh');
  run('curl', ['-fsSL', '--retry', '3', 'https://sh.rustup.rs', '-o', installer]);
  run('sh', [installer, '-y', '--profile', 'minimal', '--default-toolchain', 'stable']);
}
run('rustup', ['target', 'add', 'wasm32-unknown-unknown']);
const bindgen = spawnSync('wasm-bindgen', ['--version'], { encoding: 'utf8' });
if (bindgen.stdout?.trim() !== 'wasm-bindgen 0.2.108') {
  const directory = join(tmpdir(), 'pantheon-bindgen-cli');
  mkdirSync(directory, { recursive: true });
  if (process.arch === 'x64' && process.platform === 'linux') {
    const file = join(directory, 'cli.tar.gz');
    try {
      run('curl', ['-fsSL', '--retry', '2', 'https://github.com/wasm-bindgen/wasm-bindgen/releases/download/0.2.108/wasm-bindgen-0.2.108-x86_64-unknown-linux-musl.tar.gz', '-o', file]);
      run('tar', ['-xzf', file, '-C', directory, '--strip-components=1']);
      mkdirSync(bin, { recursive: true });
      run('install', [join(directory, 'wasm-bindgen'), join(bin, 'wasm-bindgen')]);
    } catch {
      run('cargo', ['install', 'wasm-bindgen-cli', '--version', '0.2.108', '--locked']);
    }
  } else {
    run('cargo', ['install', 'wasm-bindgen-cli', '--version', '0.2.108', '--locked']);
  }
}

const simulationOnly = process.argv.includes('--simulation');
const target = process.env.CARGO_TARGET_DIR ?? (process.env.VERCEL ? 'node_modules/.cache/pantheon-rust' : 'target');
process.env.CARGO_TARGET_DIR = target;
run('cargo', ['build', '--locked', '--release', '--target', 'wasm32-unknown-unknown', '-p', 'pantheon-simulation',
  ...(!simulationOnly ? ['-p', 'pantheon-arena'] : [])]);
const wasm = join(target, 'wasm32-unknown-unknown', 'release');
mkdirSync('server/generated', { recursive: true });
run('wasm-bindgen', [join(wasm, 'pantheon_simulation.wasm'), '--target', 'nodejs',
  '--out-dir', 'server/generated', '--out-name', 'simulation']);
writeFileSync('server/generated/package.json', '{"type":"commonjs"}\n');
if (!simulationOnly) {
  mkdirSync('public/wasm', { recursive: true });
  run('wasm-bindgen', [join(wasm, 'pantheon_arena.wasm'), '--target', 'web',
    '--out-dir', 'public/wasm', '--out-name', 'arena', '--no-typescript', '--remove-name-section', '--remove-producers-section']);
  if (!existsSync('public/assets/models/thekla.glb')) throw new Error('Run npm run art to export the Blender models.');
  run('node', ['node_modules/vite/bin/vite.js', 'build']);
}
