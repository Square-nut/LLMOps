import { existsSync } from 'node:fs'
import { spawn } from 'node:child_process'
import process from 'node:process'

const python = process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python'

if (!existsSync(python)) {
  console.error(`Python virtual environment not found: ${python}`)
  console.error('Create it first with: python -m venv .venv')
  process.exit(1)
}

const child = spawn(python, ['-m', 'uvicorn', 'app.main:app', '--reload', '--port', '8000'], {
  stdio: 'inherit',
})

child.on('error', (error) => {
  console.error(`Unable to start API: ${error.message}`)
  process.exit(1)
})

child.on('exit', (code, signal) => {
  process.exitCode = code ?? (signal ? 1 : 0)
})
