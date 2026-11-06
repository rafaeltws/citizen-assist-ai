"""Estruturas de dados do Citizen Assist AI.

Contém o registro de serviço (Servico), o nó (No) e a lista encadeada
simples (ListaEncadeada), todos implementados pela equipe, sem usar
list/deque do Python para armazenar os registros.
"""

from __future__ import annotations

from typing import Iterator, Optional


class Servico:
    """Registro de um serviço/orientação ao cidadão."""

    CAMPOS = ("id", "titulo", "categoria", "descricao", "requisitos", "local")

    def __init__(self, id_servico: int, titulo: str, categoria: str,
                 descricao: str, requisitos: str, local: str) -> None:
        self.id = id_servico
        self.titulo = titulo
        self.categoria = categoria
        self.descricao = descricao
        self.requisitos = requisitos
        self.local = local

    def para_dict(self) -> dict:
        return {
            "id": self.id,
            "titulo": self.titulo,
            "categoria": self.categoria,
            "descricao": self.descricao,
            "requisitos": self.requisitos,
            "local": self.local,
        }

    @classmethod
    def de_dict(cls, dados: dict) -> "Servico":
        return cls(dados["id"], dados["titulo"], dados["categoria"],
                   dados["descricao"], dados["requisitos"], dados["local"])

    def __str__(self) -> str:
        return (f"ID: {self.id}\n"
                f"Título: {self.titulo}\n"
                f"Categoria: {self.categoria}\n"
                f"Descrição: {self.descricao}\n"
                f"Requisitos: {self.requisitos}\n"
                f"Local de atendimento: {self.local}")

    def __repr__(self) -> str:
        return f"Servico(id={self.id}, titulo={self.titulo!r})"


class No:
    """Nó da lista encadeada: guarda um Servico e a referência ao próximo nó."""

    __slots__ = ("servico", "proximo")

    def __init__(self, servico: Optional[Servico],
                 proximo: Optional["No"] = None) -> None:
        self.servico = servico
        self.proximo = proximo


class ListaEncadeada:
    """Lista encadeada simples com referências para cabeça e cauda.

    Complexidades (n = número de nós):
      inserir_inicio / inserir_fim : O(1)
      remover_por_id               : O(n)
      percurso (iteração)          : O(n)
    """

    def __init__(self) -> None:
        self.cabeca: Optional[No] = None
        self.cauda: Optional[No] = None
        self._tamanho = 0

    # ---------------------------------------------------------- consultas
    def __len__(self) -> int:
        return self._tamanho

    def esta_vazia(self) -> bool:
        return self.cabeca is None

    def __iter__(self) -> Iterator[Servico]:
        """Percurso: visita cada nó, da cabeça até a cauda."""
        atual = self.cabeca
        while atual is not None:
            yield atual.servico
            atual = atual.proximo

    # ---------------------------------------------------------- inserção
    def inserir_inicio(self, servico: Servico) -> None:
        novo = No(servico, self.cabeca)
        self.cabeca = novo
        if self.cauda is None:
            self.cauda = novo
        self._tamanho += 1

    def inserir_fim(self, servico: Servico) -> None:
        novo = No(servico)
        if self.cauda is None:
            self.cabeca = novo
        else:
            self.cauda.proximo = novo
        self.cauda = novo
        self._tamanho += 1

    # ---------------------------------------------------------- remoção
    def remover_por_id(self, id_servico: int) -> Optional[Servico]:
        """Remove o nó com o id informado. Retorna o Servico removido ou None."""
        anterior: Optional[No] = None
        atual = self.cabeca
        while atual is not None:
            if atual.servico.id == id_servico:
                if anterior is None:          # remoção da cabeça
                    self.cabeca = atual.proximo
                else:                         # meio ou fim
                    anterior.proximo = atual.proximo
                if atual is self.cauda:       # removeu a cauda
                    self.cauda = anterior
                atual.proximo = None
                self._tamanho -= 1
                return atual.servico
            anterior, atual = atual, atual.proximo
        return None

    def limpar(self) -> None:
        self.cabeca = None
        self.cauda = None
        self._tamanho = 0

    # -------------------------------------------------- uso pela ordenação
    def substituir_cabeca(self, nova_cabeca: Optional[No]) -> None:
        """Assume uma nova cadeia (já reordenada) e recalcula cauda/tamanho."""
        self.cabeca = nova_cabeca
        self.cauda = None
        self._tamanho = 0
        atual = nova_cabeca
        while atual is not None:
            self.cauda = atual
            self._tamanho += 1
            atual = atual.proximo
