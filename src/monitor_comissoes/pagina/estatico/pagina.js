/* Monitor de comissões · comportamento da página pública (PAG).
   Sem JavaScript a página já é completa; este arquivo só acrescenta o filtro e a faixa de atraso. */
(function (raiz) {
  "use strict";

  var LIMITE_DE_ATRASO_MS = 30 * 3600 * 1000;

  /* Verdadeiro se a verificação passou de 30 horas. Entrada inválida: falso (a faixa só aparece
     com certeza). `agora` é um número (Date.now()) ou uma Date. */
  function atrasada(verificadoEm, agora) {
    var momento = Date.parse(verificadoEm);
    var instante = Number(agora);
    if (isNaN(momento) || isNaN(instante)) {
      return false;
    }
    return instante - momento > LIMITE_DE_ATRASO_MS;
  }

  /* Mostra a faixa de atraso (que nasce escondida) quando for o caso. */
  function verificarAtraso(documento, agora) {
    var faixa = documento.getElementById("faixa-atraso");
    if (!faixa) {
      return false;
    }
    var atrasado = atrasada(faixa.dataset.verificadoEm, agora);
    if (atrasado) {
      faixa.hidden = false;
    }
    return atrasado;
  }

  var PaginaMonitor = { atrasada: atrasada, verificarAtraso: verificarAtraso };
  raiz.PaginaMonitor = PaginaMonitor;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = PaginaMonitor;
  }
  if (typeof document !== "undefined") {
    verificarAtraso(document, Date.now());
  }
})(typeof window !== "undefined" ? window : globalThis);
