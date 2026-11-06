"""Algoritmos do Citizen Assist AI: busca, ordenação (Merge Sort) e análise.

Nenhuma função pronta de ordenação (sorted, list.sort) é usada.
"""

from __future__ import annotations

import unicodedata
from typing import Callable, Optional

from estruturas import ListaEncadeada, No, Servico


def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparações tolerantes ('Saúde' == 'saude')."""
    decomposto = unicodedata.normalize("NFD", texto)
    sem_acentos = "".join(c for c in decomposto if unicodedata.category(c) != "Mn")
    return sem_acentos.lower().strip()


# ================================================================== BUSCA
def busca_linear_por_id(lista: ListaEncadeada, id_servico: int) -> Optional[Servico]:
    """Busca linear (sequencial) por identificador.

    Percorre os nós a partir da cabeça e para no primeiro id igual.
    Retorna None se chegar ao fim sem encontrar (ou se a lista estiver vazia).
    Complexidade: melhor caso O(1), pior/médio caso O(n).
    """
    atual = lista.cabeca
    while atual is not None:
        if atual.servico.id == id_servico:
            return atual.servico
        atual = atual.proximo
    return None


def pesquisar_por_atributo(lista: ListaEncadeada, atributo: str,
                           termo: str) -> list:
    """Busca linear por texto em 'titulo' ou 'categoria'.

    Compara por substring, ignorando maiúsculas e acentos, e devolve TODAS as
    ocorrências (lista Python apenas como resultado da consulta). Sem
    correspondência, devolve lista vazia. Complexidade: O(n * m).
    """
    if atributo not in ("titulo", "categoria"):
        raise ValueError("Atributo de pesquisa inválido.")
    alvo = normalizar(termo)
    resultados = []
    atual = lista.cabeca
    while atual is not None:
        if alvo in normalizar(getattr(atual.servico, atributo)):
            resultados.append(atual.servico)
        atual = atual.proximo
    return resultados


# ============================================================== ORDENAÇÃO
CHAVES_ORDENACAO: dict = {
    "id": lambda s: s.id,
    "titulo": lambda s: (normalizar(s.titulo), s.id),
    "categoria": lambda s: (normalizar(s.categoria), normalizar(s.titulo), s.id),
}


def _dividir(cabeca: No) -> Optional[No]:
    """Divide a cadeia ao meio (ponteiros lento/rápido) e devolve a 2ª metade."""
    lento = cabeca
    rapido = cabeca.proximo
    while rapido is not None and rapido.proximo is not None:
        lento = lento.proximo
        rapido = rapido.proximo.proximo
    segunda = lento.proximo
    lento.proximo = None
    return segunda


def _mesclar(a: Optional[No], b: Optional[No], chave: Callable) -> Optional[No]:
    """Intercala duas cadeias ordenadas religando nós (sem criar novos nós)."""
    ficticio = No(None)
    ponta = ficticio
    while a is not None and b is not None:
        if chave(a.servico) <= chave(b.servico):
            ponta.proximo = a
            a = a.proximo
        else:
            ponta.proximo = b
            b = b.proximo
        ponta = ponta.proximo
    ponta.proximo = a if a is not None else b
    return ficticio.proximo


def merge_sort_nos(cabeca: Optional[No], chave: Callable) -> Optional[No]:
    """Merge Sort sobre lista encadeada. Complexidade O(n log n), estável."""
    if cabeca is None or cabeca.proximo is None:
        return cabeca
    segunda = _dividir(cabeca)
    esquerda = merge_sort_nos(cabeca, chave)
    direita = merge_sort_nos(segunda, chave)
    return _mesclar(esquerda, direita, chave)


def ordenar_lista(lista: ListaEncadeada, criterio: str) -> None:
    """Ordena a lista in-place pelo critério ('id', 'titulo' ou 'categoria')."""
    if criterio not in CHAVES_ORDENACAO:
        raise ValueError("Critério de ordenação inválido.")
    nova_cabeca = merge_sort_nos(lista.cabeca, CHAVES_ORDENACAO[criterio])
    lista.substituir_cabeca(nova_cabeca)


# =============================================================== ANÁLISE
def contar_por_categoria(lista: ListaEncadeada) -> dict:
    """Quantidade de serviços por categoria. Complexidade O(n)."""
    contagem: dict = {}
    for servico in lista:
        contagem[servico.categoria] = contagem.get(servico.categoria, 0) + 1
    return contagem
