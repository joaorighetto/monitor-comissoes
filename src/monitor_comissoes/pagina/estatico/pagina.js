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

  /* Os ids dos itens que atendem à comissão E ao motivo escolhidos ("" = todos). `itens` são
     {id, comissao, etiquetas: [...]}; a ordem de entrada é preservada. */
  function filtrar(itens, comissao, motivo) {
    return itens
      .filter(function (item) {
        var daComissao = comissao === "" || item.comissao === comissao;
        var doMotivo = motivo === "" || item.etiquetas.indexOf(motivo) !== -1;
        return daComissao && doMotivo;
      })
      .map(function (item) {
        return item.id;
      });
  }

  function itemDaPagina(elemento) {
    var etiquetas = elemento.dataset.etiquetas;
    return {
      id: elemento.dataset.id,
      comissao: elemento.dataset.comissao,
      etiquetas: etiquetas ? etiquetas.split(" ") : [],
    };
  }

  function lista(colecao) {
    return Array.prototype.slice.call(colecao);
  }

  /* Esconde os itens que não atendem, marca o chip escolhido de cada grupo e anuncia o resultado. */
  function aplicar(documento, comissao, motivo) {
    var elementos = lista(documento.querySelectorAll(".item"));
    var visiveis = filtrar(elementos.map(itemDaPagina), comissao, motivo);
    elementos.forEach(function (elemento) {
      elemento.hidden = visiveis.indexOf(elemento.dataset.id) === -1;
    });
    lista(documento.querySelectorAll(".pf-chip")).forEach(function (chip) {
      var escolhido = chip.dataset.grupo === "comissao" ? comissao : motivo;
      chip.setAttribute("aria-pressed", String(chip.dataset.valor === escolhido));
    });
    var aviso = documento.getElementById("filtro-status");
    if (aviso) {
      aviso.textContent =
        "Mostrando " + visiveis.length + " de " + elementos.length +
        (elementos.length === 1 ? " item." : " itens.");
    }
  }

  /* Libera os filtros (que nascem escondidos) e liga os cliques dos chips. Não escreve na região
     aria-live ao carregar: o anúncio de "Mostrando N de M" só vem depois de uma escolha. */
  function iniciar(documento) {
    var filtros = documento.getElementById("filtros");
    if (!filtros) {
      return;
    }
    var escolha = { comissao: "", motivo: "" };
    filtros.hidden = false;
    filtros.addEventListener("click", function (evento) {
      var chip = evento.target.closest(".pf-chip");
      if (!chip) {
        return;
      }
      escolha[chip.dataset.grupo] = chip.dataset.valor;
      aplicar(documento, escolha.comissao, escolha.motivo);
    });
  }

  var PaginaMonitor = {
    atrasada: atrasada,
    verificarAtraso: verificarAtraso,
    filtrar: filtrar,
    aplicar: aplicar,
    iniciar: iniciar,
  };
  raiz.PaginaMonitor = PaginaMonitor;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = PaginaMonitor;
  }
  if (typeof document !== "undefined") {
    verificarAtraso(document, Date.now());
    iniciar(document);
  }
})(typeof window !== "undefined" ? window : globalThis);
