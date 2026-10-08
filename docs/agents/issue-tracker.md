# Issue tracker: GitHub

Issues e specs deste repositório vivem no GitHub Issues. Use a CLI `gh` para todas as operações.

## Convenções

- Criar issue: `gh issue create --title "..." --body "..."`
- Ler issue: `gh issue view <number> --comments`
- Listar issues: `gh issue list --state open --json number,title,body,labels,comments`
- Comentar: `gh issue comment <number> --body "..."`
- Aplicar/remover rótulos: `gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- Fechar: `gh issue close <number> --comment "..."`

O repositório atualmente não possui remote Git configurado. Antes de publicar issues, configure um remote GitHub para que `gh` consiga inferir `owner/repository`.

## Pull requests como superfície de triagem

PRs como superfície de requisições: não.
