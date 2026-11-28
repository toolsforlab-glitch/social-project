#!/usr/bin/env bash
# Envia o commit de uma rotina. Se outra rotina (ou uma pessoa) enviou entretanto, junta as mudanças e tenta de
# novo, até 5 vezes; em conflito fica a versão da rotina (docs e estado acabados de gerar). Criado a 28/11/2026,
# depois de a rotina diária perder o envio por causa de um envio feito à mão ao mesmo tempo.
for i in 1 2 3 4 5; do
  git push -q && exit 0
  sleep $((i * 5))
  if ! git pull -q --rebase -X theirs; then
    git rebase --abort 2>/dev/null
    git pull -q --no-rebase -X ours --no-edit || git merge --abort 2>/dev/null
  fi
done
echo "Não foi possível enviar o commit depois de 5 tentativas."
exit 1
