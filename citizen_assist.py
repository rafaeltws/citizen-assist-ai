"""Citizen Assist AI - protótipo de gerenciamento de serviços ao cidadão.

Execução:  python citizen_assist.py [arquivo.json]
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from typing import Optional

from algoritmos import (busca_linear_por_id, contar_por_categoria, normalizar,
                        ordenar_lista, pesquisar_por_atributo)
from estruturas import ListaEncadeada, Servico

ARQUIVO_PADRAO = "dados_cidadao.json"

CATEGORIAS = (
    "Saúde",
    "Assistência Social",
    "Documentação e Cidadania",
    "Educação e Qualificação",
    "Serviços Urbanos",
)

LIMITES = {"titulo": 120, "descricao": 500, "requisitos": 300, "local": 150}
ID_MAXIMO = 999_999


# ============================================================== EXCEÇÕES
class ErroSistema(Exception):
    """Base dos erros esperados do sistema (mostrados ao usuário)."""


class ErroValidacao(ErroSistema):
    pass


class IdDuplicado(ErroValidacao):
    pass


class ServicoNaoEncontrado(ErroSistema):
    pass


# =========================================================== NÚCLEO (sem I/O)
class SistemaCidadao:
    """Regras de negócio: CRUD, busca, ordenação, análise e persistência."""

    def __init__(self, arquivo: Optional[str] = None) -> None:
        self.lista = ListaEncadeada()
        self.arquivo = arquivo

    # ------------------------------------------------------------ validação
    @staticmethod
    def validar_id(valor) -> int:
        if isinstance(valor, bool):
            raise ErroValidacao("O identificador deve ser um número inteiro positivo.")
        if isinstance(valor, str):
            texto = valor.strip()
            if not (texto.isascii() and texto.isdigit()):
                raise ErroValidacao("O identificador deve ser um número inteiro positivo.")
            valor = int(texto)
        if not isinstance(valor, int) or valor <= 0:
            raise ErroValidacao("O identificador deve ser um número inteiro positivo.")
        if valor > ID_MAXIMO:
            raise ErroValidacao(f"O identificador deve ser no máximo {ID_MAXIMO}.")
        return valor

    @staticmethod
    def validar_campos(campos: dict) -> dict:
        """Valida e normaliza (strip / categoria canônica) os campos de texto."""
        resultado = {}
        for nome, valor in campos.items():
            if nome == "categoria":
                if not isinstance(valor, str) or not valor.strip():
                    raise ErroValidacao("A categoria é obrigatória.")
                for oficial in CATEGORIAS:
                    if normalizar(oficial) == normalizar(valor):
                        resultado[nome] = oficial
                        break
                else:
                    raise ErroValidacao(
                        "Categoria inválida. Opções: " + ", ".join(CATEGORIAS) + ".")
            elif nome in LIMITES:
                if not isinstance(valor, str) or not valor.strip():
                    raise ErroValidacao(f"O campo '{nome}' é obrigatório.")
                valor = valor.strip()
                if len(valor) > LIMITES[nome]:
                    raise ErroValidacao(
                        f"O campo '{nome}' aceita no máximo {LIMITES[nome]} caracteres.")
                resultado[nome] = valor
            else:
                raise ErroValidacao(f"Campo desconhecido: '{nome}'.")
        return resultado

    # ----------------------------------------------------------------- CRUD
    def cadastrar(self, id_servico, titulo, categoria, descricao,
                  requisitos, local) -> Servico:
        id_valido = self.validar_id(id_servico)
        if busca_linear_por_id(self.lista, id_valido) is not None:
            raise IdDuplicado(f"Já existe um serviço com o ID {id_valido}.")
        campos = self.validar_campos({
            "titulo": titulo, "categoria": categoria, "descricao": descricao,
            "requisitos": requisitos, "local": local})
        servico = Servico(id_valido, **campos)
        self.lista.inserir_fim(servico)
        return servico

    def consultar(self, id_servico) -> Optional[Servico]:
        return busca_linear_por_id(self.lista, self.validar_id(id_servico))

    def atualizar(self, id_servico, **campos) -> Servico:
        id_valido = self.validar_id(id_servico)
        if self.lista.esta_vazia():
            raise ServicoNaoEncontrado("A lista está vazia: nada a atualizar.")
        servico = busca_linear_por_id(self.lista, id_valido)
        if servico is None:
            raise ServicoNaoEncontrado(f"Nenhum serviço com o ID {id_valido}.")
        if not campos:
            raise ErroValidacao("Nenhum campo informado para atualização.")
        # Valida tudo antes de alterar: se algo falhar, o registro fica intacto.
        novos = self.validar_campos(campos)
        for nome, valor in novos.items():
            setattr(servico, nome, valor)
        return servico

    def excluir(self, id_servico) -> Servico:
        id_valido = self.validar_id(id_servico)
        if self.lista.esta_vazia():
            raise ServicoNaoEncontrado("A lista está vazia: nada a excluir.")
        removido = self.lista.remover_por_id(id_valido)
        if removido is None:
            raise ServicoNaoEncontrado(f"Nenhum serviço com o ID {id_valido}.")
        return removido

    # ------------------------------------------------- pesquisa / ordenação
    def pesquisar(self, atributo: str, termo: str) -> list:
        if not isinstance(termo, str) or not termo.strip():
            raise ErroValidacao("Informe um termo de pesquisa.")
        return pesquisar_por_atributo(self.lista, atributo, termo)

    def ordenar(self, criterio: str) -> None:
        try:
            ordenar_lista(self.lista, criterio)
        except ValueError as erro:
            raise ErroValidacao(str(erro)) from None

    # --------------------------------------------------------------- análise
    def analise(self) -> dict:
        total = len(self.lista)
        contagem = contar_por_categoria(self.lista)
        por_categoria = {cat: contagem.get(cat, 0) for cat in CATEGORIAS}
        for cat, qtd in contagem.items():      # categorias fora da lista oficial
            por_categoria.setdefault(cat, qtd)
        maior = max(por_categoria.values(), default=0)
        mais_frequentes = [c for c, q in por_categoria.items() if q == maior and maior > 0]
        return {
            "total": total,
            "por_categoria": por_categoria,
            "percentuais": {c: (q * 100 / total if total else 0.0)
                            for c, q in por_categoria.items()},
            "mais_frequentes": mais_frequentes,
            "sem_registros": [c for c, q in por_categoria.items() if q == 0],
        }

    # ------------------------------------------------------------ persistência
    def salvar(self, caminho: Optional[str] = None) -> str:
        caminho = caminho or self.arquivo
        if not caminho:
            raise ErroSistema("Nenhum arquivo definido para salvar.")
        dados = [s.para_dict() for s in self.lista]
        pasta = os.path.dirname(os.path.abspath(caminho))
        fd, temporario = tempfile.mkstemp(dir=pasta, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as arq:
                json.dump(dados, arq, ensure_ascii=False, indent=2)
            os.replace(temporario, caminho)     # troca atômica
        except OSError as erro:
            if os.path.exists(temporario):
                os.remove(temporario)
            raise ErroSistema(f"Falha ao salvar: {erro}") from None
        return caminho

    def carregar(self, caminho: Optional[str] = None) -> tuple:
        """Carrega registros do JSON. Retorna (carregados, ignorados)."""
        caminho = caminho or self.arquivo
        if not caminho or not os.path.exists(caminho):
            return (0, 0)
        try:
            with open(caminho, encoding="utf-8") as arq:
                dados = json.load(arq)
        except (OSError, json.JSONDecodeError) as erro:
            raise ErroSistema(f"Arquivo de dados ilegível ({erro}).") from None
        if not isinstance(dados, list):
            raise ErroSistema("Arquivo de dados em formato inesperado.")
        carregados = ignorados = 0
        for item in dados:
            try:
                self.cadastrar(item["id"], item["titulo"], item["categoria"],
                               item["descricao"], item["requisitos"], item["local"])
                carregados += 1
            except (ErroSistema, KeyError, TypeError):
                ignorados += 1
        return (carregados, ignorados)


# ===================================================== DADOS DE EXEMPLO
EXEMPLOS = [
    (1, "Consulta clínica geral na UBS", "Saúde",
     "Atendimento básico de saúde, com acompanhamento e encaminhamentos.",
     "Documento com foto, cartão SUS e comprovante de residência.",
     "Unidade Básica de Saúde do bairro"),
    (2, "Vacinação", "Saúde",
     "Aplicação de vacinas do calendário nacional de imunização.",
     "Documento com foto e caderneta de vacinação.",
     "Unidades de saúde e postos de vacinação"),
    (3, "Cadastro Único (CadÚnico)", "Assistência Social",
     "Inscrição de famílias de baixa renda para acesso a programas sociais.",
     "Documentos de todos os membros da família e comprovante de residência.",
     "CRAS da região"),
    (4, "Orientação socioassistencial", "Assistência Social",
     "Atendimento e orientação sobre benefícios e programas de proteção social.",
     "Documento com foto.",
     "CRAS ou CREAS"),
    (5, "Emissão de carteira de identidade", "Documentação e Cidadania",
     "Primeira e segunda via do documento de identidade.",
     "Certidão de nascimento ou casamento e comprovante de residência.",
     "Posto de identificação"),
    (6, "Título de eleitor", "Documentação e Cidadania",
     "Emissão, transferência e regularização do título de eleitor.",
     "Documento com foto e comprovante de residência.",
     "Cartório eleitoral"),
    (7, "Curso de informática básica", "Educação e Qualificação",
     "Curso gratuito de introdução ao uso de computadores e internet.",
     "Idade mínima de 16 anos e documento com foto.",
     "Centro de qualificação profissional"),
    (8, "Solicitação de reparo de iluminação pública", "Serviços Urbanos",
     "Abertura de chamado para troca de lâmpadas e reparo de postes.",
     "Endereço exato e ponto de referência.",
     "Central de atendimento ao cidadão"),
]


# ======================================================= ENTRADA / SAÍDA
def cortar(texto: str, tamanho: int) -> str:
    return texto if len(texto) <= tamanho else texto[:tamanho - 1] + "…"


def ler_id(rotulo: str = "ID do serviço") -> Optional[int]:
    """Lê um ID válido; Enter em branco cancela (retorna None)."""
    while True:
        bruto = input(f"{rotulo} (Enter para cancelar): ").strip()
        if not bruto:
            return None
        try:
            return SistemaCidadao.validar_id(bruto)
        except ErroValidacao as erro:
            print(f"  ✗ {erro}")


def ler_texto(campo: str, rotulo: str, atual: Optional[str] = None) -> str:
    """Lê texto obrigatório. Se 'atual' existir, Enter mantém o valor."""
    sufixo = f" [{cortar(atual, 40)}]" if atual is not None else ""
    while True:
        valor = input(f"{rotulo}{sufixo}: ").strip()
        if not valor and atual is not None:
            return atual
        try:
            return SistemaCidadao.validar_campos({campo: valor})[campo]
        except ErroValidacao as erro:
            print(f"  ✗ {erro}")


def escolher_categoria(atual: Optional[str] = None) -> str:
    for i, cat in enumerate(CATEGORIAS, 1):
        print(f"  {i}. {cat}")
    sufixo = f" [{atual}]" if atual else ""
    while True:
        bruto = input(f"Categoria (número){sufixo}: ").strip()
        if not bruto and atual:
            return atual
        if bruto.isascii() and bruto.isdigit() and 1 <= int(bruto) <= len(CATEGORIAS):
            return CATEGORIAS[int(bruto) - 1]
        print(f"  ✗ Escolha um número de 1 a {len(CATEGORIAS)}.")


def confirmar(pergunta: str) -> bool:
    while True:
        resp = normalizar(input(f"{pergunta} (s/n): "))
        if resp in ("s", "sim"):
            return True
        if resp in ("n", "nao"):
            return False
        print("  ✗ Responda com 's' ou 'n'.")


def exibir_tabela(servicos) -> None:
    print(f"{'ID':>6} | {'Título':<36} | {'Categoria':<26} | Local")
    print("-" * 104)
    for s in servicos:
        print(f"{s.id:>6} | {cortar(s.titulo, 36):<36} | "
              f"{cortar(s.categoria, 26):<26} | {cortar(s.local, 30)}")


# ================================================================ AÇÕES
def acao_cadastrar(sis: SistemaCidadao) -> None:
    print("\n--- Cadastrar serviço ---")
    while True:
        id_servico = ler_id()
        if id_servico is None:
            print("Cadastro cancelado.")
            return
        if sis.consultar(id_servico) is None:
            break
        print(f"  ✗ Já existe um serviço com o ID {id_servico}. Informe outro.")
    titulo = ler_texto("titulo", "Título")
    categoria = escolher_categoria()
    descricao = ler_texto("descricao", "Descrição")
    requisitos = ler_texto("requisitos", "Requisitos")
    local = ler_texto("local", "Local de atendimento")
    sis.cadastrar(id_servico, titulo, categoria, descricao, requisitos, local)
    print(f"✓ Serviço {id_servico} cadastrado com sucesso.")


def acao_consultar(sis: SistemaCidadao) -> None:
    print("\n--- Consultar por ID ---")
    if sis.lista.esta_vazia():
        print("A lista está vazia. Cadastre serviços primeiro.")
        return
    id_servico = ler_id()
    if id_servico is None:
        return
    servico = sis.consultar(id_servico)
    print("\n" + str(servico) if servico else f"Nenhum serviço encontrado com o ID {id_servico}.")


def acao_atualizar(sis: SistemaCidadao) -> None:
    print("\n--- Atualizar serviço ---")
    if sis.lista.esta_vazia():
        print("A lista está vazia. Nada a atualizar.")
        return
    id_servico = ler_id()
    if id_servico is None:
        return
    atual = sis.consultar(id_servico)
    if atual is None:
        print(f"Nenhum serviço encontrado com o ID {id_servico}.")
        return
    print("\n" + str(atual) + "\n\nPressione Enter para manter o valor atual.")
    campos = {
        "titulo": ler_texto("titulo", "Título", atual.titulo),
        "categoria": escolher_categoria(atual.categoria),
        "descricao": ler_texto("descricao", "Descrição", atual.descricao),
        "requisitos": ler_texto("requisitos", "Requisitos", atual.requisitos),
        "local": ler_texto("local", "Local de atendimento", atual.local),
    }
    sis.atualizar(id_servico, **campos)
    print(f"✓ Serviço {id_servico} atualizado.")


def acao_excluir(sis: SistemaCidadao) -> None:
    print("\n--- Excluir serviço ---")
    if sis.lista.esta_vazia():
        print("A lista está vazia. Nada a excluir.")
        return
    id_servico = ler_id()
    if id_servico is None:
        return
    servico = sis.consultar(id_servico)
    if servico is None:
        print(f"Nenhum serviço encontrado com o ID {id_servico}.")
        return
    print("\n" + str(servico))
    if confirmar("\nConfirma a exclusão?"):
        sis.excluir(id_servico)
        print(f"✓ Serviço {id_servico} excluído.")
    else:
        print("Exclusão cancelada.")


def acao_pesquisar(sis: SistemaCidadao) -> None:
    print("\n--- Pesquisar ---")
    if sis.lista.esta_vazia():
        print("A lista está vazia. Nada a pesquisar.")
        return
    print("  1. Por título\n  2. Por categoria")
    escolha = input("Pesquisar por: ").strip()
    atributo = {"1": "titulo", "2": "categoria"}.get(escolha)
    if atributo is None:
        print("  ✗ Opção inválida.")
        return
    termo = input("Termo de pesquisa: ").strip()
    if not termo:
        print("  ✗ Informe um termo de pesquisa.")
        return
    resultados = sis.pesquisar(atributo, termo)
    if not resultados:
        print(f"Nenhum serviço encontrado para '{termo}' em {atributo}.")
        return
    print(f"\n{len(resultados)} serviço(s) encontrado(s):\n")
    exibir_tabela(resultados)


def acao_ordenar(sis: SistemaCidadao) -> None:
    print("\n--- Ordenar e exibir ---")
    if sis.lista.esta_vazia():
        print("A lista está vazia. Nada a ordenar.")
        return
    print("  1. Por ID\n  2. Por título\n  3. Por categoria")
    criterio = {"1": "id", "2": "titulo", "3": "categoria"}.get(input("Ordenar por: ").strip())
    if criterio is None:
        print("  ✗ Opção inválida.")
        return
    sis.ordenar(criterio)
    print(f"\nLista ordenada por {criterio} (Merge Sort):\n")
    exibir_tabela(sis.lista)


def acao_listar(sis: SistemaCidadao) -> None:
    print("\n--- Todos os serviços ---")
    if sis.lista.esta_vazia():
        print("Nenhum serviço cadastrado.")
        return
    exibir_tabela(sis.lista)
    print(f"\nTotal: {len(sis.lista)}")


def acao_analise(sis: SistemaCidadao) -> None:
    print("\n--- Análise dos serviços cadastrados ---")
    res = sis.analise()
    print(f"Total de registros: {res['total']}")
    if res["total"] == 0:
        print("Sem dados para análise.")
        return
    print("\nServiços por categoria:")
    for cat, qtd in res["por_categoria"].items():
        barra = "█" * qtd
        print(f"  {cat:<26} {qtd:>3}  ({res['percentuais'][cat]:5.1f}%) {barra}")
    print("\nCategoria(s) com mais serviços:", ", ".join(res["mais_frequentes"]))
    if res["sem_registros"]:
        print("Categorias sem nenhum serviço:", ", ".join(res["sem_registros"]))


def acao_salvar(sis: SistemaCidadao) -> None:
    caminho = sis.salvar()
    print(f"✓ {len(sis.lista)} registro(s) salvo(s) em '{caminho}'.")


def acao_exemplos(sis: SistemaCidadao) -> None:
    novos = 0
    for dados in EXEMPLOS:
        try:
            sis.cadastrar(*dados)
            novos += 1
        except IdDuplicado:
            pass
    print(f"✓ {novos} serviço(s) de exemplo adicionado(s)"
          f" ({len(EXEMPLOS) - novos} já existiam).")


ACOES = {
    "1": ("Cadastrar serviço", acao_cadastrar),
    "2": ("Consultar por ID", acao_consultar),
    "3": ("Atualizar serviço", acao_atualizar),
    "4": ("Excluir serviço", acao_excluir),
    "5": ("Pesquisar (título/categoria)", acao_pesquisar),
    "6": ("Ordenar e exibir", acao_ordenar),
    "7": ("Listar todos", acao_listar),
    "8": ("Apresentar análise", acao_analise),
    "9": ("Salvar dados em arquivo", acao_salvar),
    "10": ("Carregar dados de exemplo", acao_exemplos),
}


def exibir_menu() -> None:
    print("\n" + "=" * 44)
    print("        CITIZEN ASSIST AI - MENU")
    print("=" * 44)
    for chave, (nome, _) in ACOES.items():
        print(f" {chave:>2}. {nome}")
    print("  0. Encerrar")


def menu(sis: SistemaCidadao) -> None:
    while True:
        exibir_menu()
        try:
            opcao = input("Escolha uma opção: ").strip()
            if opcao == "0":
                break
            if opcao not in ACOES:
                print("  ✗ Opção inexistente. Escolha uma das opções do menu.")
                continue
            ACOES[opcao][1](sis)
        except ErroSistema as erro:
            print(f"  ✗ {erro}")
        except (EOFError, KeyboardInterrupt):
            print("\nEntrada encerrada.")
            break
    if sis.arquivo:
        try:
            sis.salvar()
            print(f"Dados salvos em '{sis.arquivo}'.")
        except ErroSistema as erro:
            print(f"  ✗ {erro}")
    print("Até logo!")


def main() -> None:
    arquivo = sys.argv[1] if len(sys.argv) > 1 else ARQUIVO_PADRAO
    sis = SistemaCidadao(arquivo)
    try:
        carregados, ignorados = sis.carregar()
        if carregados or ignorados:
            print(f"{carregados} registro(s) carregado(s) de '{arquivo}'"
                  + (f" ({ignorados} inválido(s) ignorado(s))." if ignorados else "."))
    except ErroSistema as erro:
        print(f"Aviso: {erro} Iniciando com lista vazia.")
    menu(sis)


if __name__ == "__main__":
    main()
