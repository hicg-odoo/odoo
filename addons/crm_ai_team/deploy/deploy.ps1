param(
    [Parameter(Position = 0)]
    [ValidateSet("quickstart", "up", "up-mcp", "seed-demo", "down", "logs", "ps", "restart")]
    [string]$Command = "quickstart",

    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ExtraArgs
)

$ErrorActionPreference = "Stop"

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ComposeFile = Join-Path $RootDir "docker-compose.yml"
$EnvFile = Join-Path $RootDir ".env"
$EnvExample = Join-Path $RootDir ".env.example"
$EnvExamplePlain = Join-Path $RootDir "env.example"

function Ensure-EnvFile {
    if (-not (Test-Path $EnvFile)) {
        if (Test-Path $EnvExample) {
            Copy-Item $EnvExample $EnvFile
            Write-Host "Created $EnvFile from .env.example"
        }
        elseif (Test-Path $EnvExamplePlain) {
            Copy-Item $EnvExamplePlain $EnvFile
            Write-Host "Created $EnvFile from env.example"
        }
        else {
            throw "Missing env template. Add .env.example or env.example in $RootDir"
        }
    }
}

function Invoke-Compose {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$ComposeArgs
    )

    $argsList = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile) + $ComposeArgs
    & docker @argsList
}

function Ensure-DockerEngine {
    try {
        & docker version | Out-Null
    }
    catch {
        throw "Docker CLI is not installed or not in PATH."
    }

    try {
        & docker info | Out-Null
    }
    catch {
        throw @"
Cannot connect to the Docker engine.

If you see errors containing:
  //./pipe/dockerDesktopLinuxEngine

Then Docker Desktop is usually not running (or Linux engine is unavailable).
Fix:
  1) Start Docker Desktop
  2) Switch to Linux containers
  3) Wait until Docker Desktop shows 'Engine running'
"@
    }
}

switch ($Command) {
    "quickstart" {
        Ensure-EnvFile
        Ensure-DockerEngine
        Invoke-Compose -ComposeArgs @("up", "-d", "--build", "db", "odoo")

        $EnvMap = @{}
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
            $parts = $_ -split '=', 2
            if ($parts.Length -eq 2) {
                $EnvMap[$parts[0].Trim()] = $parts[1].Trim()
            }
        }
        $httpPort = if ($EnvMap.ContainsKey("ODOO_HTTP_PORT")) { $EnvMap["ODOO_HTTP_PORT"] } else { "8069" }

        Write-Host ""
        Write-Host "Odoo is starting. Open: http://localhost:$httpPort"
        Write-Host "Tip: run '.\\deploy.ps1 logs odoo' to follow startup logs."
    }
    "up" {
        Ensure-EnvFile
        Ensure-DockerEngine
        Invoke-Compose -ComposeArgs (@("up", "-d", "--build") + $ExtraArgs)
    }
    "up-mcp" {
        Ensure-EnvFile
        Ensure-DockerEngine
        Invoke-Compose -ComposeArgs (@("--profile", "mcp", "up", "-d", "--build") + $ExtraArgs)
    }
    "seed-demo" {
        Ensure-EnvFile
        Ensure-DockerEngine

        $envVars = @{}
        Get-Content $EnvFile | ForEach-Object {
            if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
            $parts = $_ -split '=', 2
            if ($parts.Length -eq 2) {
                $envVars[$parts[0].Trim()] = $parts[1].Trim()
            }
        }

        $dbUser = if ($envVars.ContainsKey("POSTGRES_USER")) { $envVars["POSTGRES_USER"] } else { "odoo" }
        $dbPassword = if ($envVars.ContainsKey("POSTGRES_PASSWORD")) { $envVars["POSTGRES_PASSWORD"] } else { "odoo" }
        $odooDb = if ($envVars.ContainsKey("ODOO_DB")) { $envVars["ODOO_DB"] } else { "odoo" }

        $shellScript = @'
result = env['crm.ai.agent.team'].create_dummy_dataset(team_name='Local Demo Team', agent_count=5, transcript_count=15, auto_run=True)
print(result)
'@

        $composeArgs = @(
            "exec", "-T", "odoo", "odoo", "shell",
            "--db_host=db",
            "--db_user=$dbUser",
            "--db_password=$dbPassword",
            "-d", $odooDb
        )
        $fullArgs = @("compose", "--env-file", $EnvFile, "-f", $ComposeFile) + $composeArgs
        $shellScript | & docker @fullArgs
    }
    "down" {
        Ensure-EnvFile
        Ensure-DockerEngine
        Invoke-Compose -ComposeArgs (@("down") + $ExtraArgs)
    }
    "logs" {
        Ensure-EnvFile
        Ensure-DockerEngine
        Invoke-Compose -ComposeArgs (@("logs", "-f") + $ExtraArgs)
    }
    "ps" {
        Ensure-EnvFile
        Ensure-DockerEngine
        Invoke-Compose -ComposeArgs (@("ps") + $ExtraArgs)
    }
    "restart" {
        Ensure-EnvFile
        Ensure-DockerEngine
        Invoke-Compose -ComposeArgs (@("restart") + $ExtraArgs)
    }
}
