# Issue tracker: GitHub

Issues e specs deste repositório vivem no GitHub Issues. Use a CLI `gh` para todas as operações.

## Convenções

- Criar issue: `gh issue create --title "..." --body "..."`
- Ler issue: `gh issue view <number> --comments`
- Listar issues: `gh issue list --state open --json number,title,body,labels,comments`
- Comentar: `gh issue comment <number> --body "..."`
- Aplicar/remover rótulos: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- Fechar: `gh issue close <number> --comment "..."`

O remote `origin` aponta para `https://github.com/dargmiguel/dinheiro-compra-votos`. `gh` pode inferir o repositório automaticamente a partir deste clone.

## Wayfinding operations

- Map label: `wayfinder:map`. Ticket labels: `wayfinder:research`, `wayfinder:prototype`, `wayfinder:grilling` or `wayfinder:task`.
- Create a map under its parent specification with `gh issue create --title "..." --body "..." --label wayfinder:map --parent <spec-number>`.
- Create a ticket under the map with `gh issue create --title "..." --body "## Question\n\n..." --label wayfinder:<type> --assignee @me --parent <map-number>`. The assignee claims the ticket.
- Express native blockers with `gh issue create --blocked-by <number>` or `gh issue edit <number> --add-blocked-by <number>`.
- Inspect children and dependencies with `gh issue view <map-number> --json subIssues` and `gh issue list --state open --label wayfinder:research --json number,title,url,assignees,parent,blockedBy`. The frontier contains open map children that are unassigned and have no open blockers.
- Record a resolution with `gh issue comment <number> --body "..."`, then close with `gh issue close <number>`.

The GitHub issue page is the canonical view for parent/child and blocked-by relationships.

## Pull requests como superfície de triagem

PRs como superfície de requisições: não.
