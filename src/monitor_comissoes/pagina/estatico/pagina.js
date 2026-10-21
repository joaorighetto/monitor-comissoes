/* Monitor de comissões · comportamento da página pública (PAG).
   Sem JavaScript a página já é completa; este arquivo só acrescenta o filtro e a faixa de atraso. */
(function (raiz) {
  "use strict";
  var PaginaMonitor = {};
  raiz.PaginaMonitor = PaginaMonitor;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = PaginaMonitor;
  }
})(typeof window !== "undefined" ? window : globalThis);
