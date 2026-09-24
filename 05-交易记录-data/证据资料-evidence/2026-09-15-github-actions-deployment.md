# Evidence - GitHub Actions Deployment

## Repository

- Owner: `yomislight`
- Repository: `7-day-stock-paper-trading`
- Visibility: private
- Branch: `main`
- Initial commit: `2847b29`
- Workflow: `7-day paper trading observation`

## Secret Handling

- Binance API key and secret were transferred directly from the ignored local env file to GitHub Actions Secrets.
- Secret values were not printed or written to tracked files.
- GitHub logs masked both Binance values as `***`.
- The runtime env file was deleted before artifact upload.
- No live trading permission or order action was enabled.

## First Cloud Run

- GitHub Actions run ID: `34930058749`
- Trigger: manual `workflow_dispatch`
- Secret validation: passed
- Temporary runtime configuration: passed
- Project file validation: passed
- Observation: failed safely with exit code 2
- Binance response: HTTP 451 on public ping and time endpoints
- Temporary credential removal: passed
- Non-secret artifact upload: passed
- Telegram notification: skipped because optional Telegram Secrets were absent

## Conclusion

The repository and workflow are deployed correctly, but a GitHub-hosted runner cannot currently reach Binance.com from its execution region. Use a supported-region VPS or self-hosted runner with a fixed outbound IP before relying on scheduled Binance observations.
