"""Testes automatizados do Citizen Assist AI.

Execução:  python -m unittest -v test_citizen_assist
"""

import contextlib
import io
import os
import tempfile
import unittest
from unittest.mock import patch

import citizen_assist as ca
from algoritmos import (busca_linear_por_id, contar_por_categoria,
                        ordenar_lista, pesquisar_por_atributo)
from citizen_assist import (ErroValidacao, IdDuplicado, ServicoNaoEncontrado,
                            SistemaCidadao)
from estruturas import ListaEncadeada, Servico


def novo(id_, titulo="Serviço", categoria="Saúde"):
    return Servico(id_, titulo, categoria, "desc", "req", "local")


def ids(lista):
    return [s.id for s in lista]


def sistema_com_exemplos():
    sis = SistemaCidadao()
    for dados in ca.EXEMPLOS:
        sis.cadastrar(*dados)
    return sis


# ===================================================== LISTA ENCADEADA
class TestListaEncadeada(unittest.TestCase):
    def test_lista_vazia(self):
        lista = ListaEncadeada()
        self.assertTrue(lista.esta_vazia())
        self.assertEqual(len(lista), 0)
        self.assertEqual(ids(lista), [])
        self.assertIsNone(lista.remover_por_id(1))

    def test_insercao_fim_e_inicio(self):
        lista = ListaEncadeada()
        lista.inserir_fim(novo(2))
        lista.inserir_fim(novo(3))
        lista.inserir_inicio(novo(1))
        self.assertEqual(ids(lista), [1, 2, 3])
        self.assertEqual(len(lista), 3)
        self.assertEqual(lista.cauda.servico.id, 3)

    def test_remocao_cabeca_meio_cauda(self):
        lista = ListaEncadeada()
        for i in range(1, 6):
            lista.inserir_fim(novo(i))
        self.assertEqual(lista.remover_por_id(1).id, 1)      # cabeça
        self.assertEqual(lista.remover_por_id(3).id, 3)      # meio
        self.assertEqual(lista.remover_por_id(5).id, 5)      # cauda
        self.assertEqual(ids(lista), [2, 4])
        self.assertEqual(len(lista), 2)
        self.assertEqual(lista.cauda.servico.id, 4)
        lista.inserir_fim(novo(9))                           # cauda ainda válida
        self.assertEqual(ids(lista), [2, 4, 9])

    def test_remover_unico_elemento(self):
        lista = ListaEncadeada()
        lista.inserir_fim(novo(1))
        lista.remover_por_id(1)
        self.assertTrue(lista.esta_vazia())
        self.assertIsNone(lista.cauda)
        lista.inserir_fim(novo(2))
        self.assertEqual(ids(lista), [2])

    def test_remover_inexistente(self):
        lista = ListaEncadeada()
        lista.inserir_fim(novo(1))
        self.assertIsNone(lista.remover_por_id(99))
        self.assertEqual(len(lista), 1)


# ============================================================== BUSCA
class TestBusca(unittest.TestCase):
    def setUp(self):
        self.sis = sistema_com_exemplos()

    def test_busca_id_existente(self):
        self.assertEqual(busca_linear_por_id(self.sis.lista, 5).id, 5)

    def test_busca_id_inexistente(self):
        self.assertIsNone(busca_linear_por_id(self.sis.lista, 999))

    def test_busca_em_lista_vazia(self):
        self.assertIsNone(busca_linear_por_id(ListaEncadeada(), 1))
        self.assertEqual(pesquisar_por_atributo(ListaEncadeada(), "titulo", "x"), [])

    def test_pesquisa_titulo_ignora_caixa_e_acento(self):
        res = pesquisar_por_atributo(self.sis.lista, "titulo", "CADUNICO")
        self.assertEqual(ids(res), [3])

    def test_pesquisa_categoria(self):
        res = pesquisar_por_atributo(self.sis.lista, "categoria", "saude")
        self.assertEqual(ids(res), [1, 2])

    def test_pesquisa_sem_resultado(self):
        self.assertEqual(pesquisar_por_atributo(self.sis.lista, "titulo", "zzz"), [])

    def test_pesquisa_atributo_invalido(self):
        with self.assertRaises(ValueError):
            pesquisar_por_atributo(self.sis.lista, "local", "x")


# ========================================================== ORDENAÇÃO
class TestOrdenacao(unittest.TestCase):
    def test_ordenar_por_id(self):
        lista = ListaEncadeada()
        for i in (5, 2, 9, 1, 7):
            lista.inserir_fim(novo(i))
        ordenar_lista(lista, "id")
        self.assertEqual(ids(lista), [1, 2, 5, 7, 9])
        self.assertEqual(lista.cauda.servico.id, 9)
        self.assertEqual(len(lista), 5)

    def test_ordenar_por_titulo_ignora_acentos_e_caixa(self):
        lista = ListaEncadeada()
        lista.inserir_fim(novo(1, "Zebra"))
        lista.inserir_fim(novo(2, "água"))
        lista.inserir_fim(novo(3, "Banco"))
        ordenar_lista(lista, "titulo")
        self.assertEqual(ids(lista), [2, 3, 1])

    def test_ordenar_por_categoria_desempata_por_titulo(self):
        lista = ListaEncadeada()
        lista.inserir_fim(novo(1, "B", "Serviços Urbanos"))
        lista.inserir_fim(novo(2, "Z", "Saúde"))
        lista.inserir_fim(novo(3, "A", "Saúde"))
        ordenar_lista(lista, "categoria")
        self.assertEqual(ids(lista), [3, 2, 1])

    def test_ordenar_lista_vazia_e_unitaria(self):
        lista = ListaEncadeada()
        ordenar_lista(lista, "titulo")
        self.assertTrue(lista.esta_vazia())
        lista.inserir_fim(novo(1))
        ordenar_lista(lista, "id")
        self.assertEqual(ids(lista), [1])

    def test_ordenar_ja_ordenada_e_inversa(self):
        lista = ListaEncadeada()
        for i in range(50, 0, -1):
            lista.inserir_fim(novo(i))
        ordenar_lista(lista, "id")
        self.assertEqual(ids(lista), list(range(1, 51)))
        ordenar_lista(lista, "id")
        self.assertEqual(ids(lista), list(range(1, 51)))

    def test_criterio_invalido(self):
        with self.assertRaises(ErroValidacao):
            SistemaCidadao().ordenar("local")

    def test_lista_continua_funcional_apos_ordenar(self):
        sis = sistema_com_exemplos()
        sis.ordenar("titulo")
        sis.cadastrar(50, "Novo", "Saúde", "d", "r", "l")
        sis.excluir(3)
        self.assertEqual(len(sis.lista), 8)
        self.assertEqual(sis.lista.cauda.servico.id, 50)


# ====================================================== CRUD / VALIDAÇÃO
class TestSistema(unittest.TestCase):
    def test_cadastro_normal(self):
        sis = SistemaCidadao()
        s = sis.cadastrar("10", "  Teste  ", "saude", "d", "r", "l")
        self.assertEqual((s.id, s.titulo, s.categoria), (10, "Teste", "Saúde"))
        self.assertEqual(len(sis.lista), 1)

    def test_id_duplicado(self):
        sis = sistema_com_exemplos()
        with self.assertRaises(IdDuplicado):
            sis.cadastrar(1, "x", "Saúde", "d", "r", "l")
        self.assertEqual(len(sis.lista), 8)

    def test_ids_invalidos(self):
        sis = SistemaCidadao()
        for ruim in (0, -3, "abc", "", "1.5", None, True, 1.5, 10**7, "²"):
            with self.subTest(id=ruim):
                with self.assertRaises(ErroValidacao):
                    sis.cadastrar(ruim, "x", "Saúde", "d", "r", "l")
        self.assertEqual(len(sis.lista), 0)

    def test_campos_vazios_ou_longos(self):
        sis = SistemaCidadao()
        with self.assertRaises(ErroValidacao):
            sis.cadastrar(1, "   ", "Saúde", "d", "r", "l")
        with self.assertRaises(ErroValidacao):
            sis.cadastrar(1, "x" * 121, "Saúde", "d", "r", "l")
        self.assertEqual(len(sis.lista), 0)

    def test_categoria_invalida(self):
        with self.assertRaises(ErroValidacao):
            SistemaCidadao().cadastrar(1, "x", "Esportes", "d", "r", "l")

    def test_consultar(self):
        sis = sistema_com_exemplos()
        self.assertEqual(sis.consultar(2).titulo, "Vacinação")
        self.assertIsNone(sis.consultar(404))
        with self.assertRaises(ErroValidacao):
            sis.consultar("abc")

    def test_atualizar(self):
        sis = sistema_com_exemplos()
        sis.atualizar(2, titulo="Vacinação infantil", local="Posto central")
        s = sis.consultar(2)
        self.assertEqual((s.titulo, s.local), ("Vacinação infantil", "Posto central"))
        self.assertEqual(len(sis.lista), 8)

    def test_atualizar_invalido_nao_altera_registro(self):
        sis = sistema_com_exemplos()
        antes = sis.consultar(2).para_dict()
        with self.assertRaises(ErroValidacao):
            sis.atualizar(2, titulo="Novo título", categoria="Inválida")
        self.assertEqual(sis.consultar(2).para_dict(), antes)

    def test_atualizar_inexistente_e_lista_vazia(self):
        with self.assertRaises(ServicoNaoEncontrado):
            sistema_com_exemplos().atualizar(404, titulo="x")
        with self.assertRaises(ServicoNaoEncontrado):
            SistemaCidadao().atualizar(1, titulo="x")

    def test_excluir(self):
        sis = sistema_com_exemplos()
        removido = sis.excluir(4)
        self.assertEqual(removido.id, 4)
        self.assertIsNone(sis.consultar(4))
        self.assertEqual(len(sis.lista), 7)

    def test_excluir_inexistente_e_lista_vazia(self):
        with self.assertRaises(ServicoNaoEncontrado):
            sistema_com_exemplos().excluir(404)
        with self.assertRaises(ServicoNaoEncontrado):
            SistemaCidadao().excluir(1)

    def test_pesquisa_termo_vazio(self):
        with self.assertRaises(ErroValidacao):
            sistema_com_exemplos().pesquisar("titulo", "   ")


# ============================================================ ANÁLISE
class TestAnalise(unittest.TestCase):
    def test_analise_lista_vazia(self):
        res = SistemaCidadao().analise()
        self.assertEqual(res["total"], 0)
        self.assertEqual(res["mais_frequentes"], [])
        self.assertEqual(len(res["sem_registros"]), len(ca.CATEGORIAS))

    def test_analise_com_dados(self):
        res = sistema_com_exemplos().analise()
        self.assertEqual(res["total"], 8)
        self.assertEqual(res["por_categoria"]["Saúde"], 2)
        self.assertEqual(res["por_categoria"]["Serviços Urbanos"], 1)
        self.assertAlmostEqual(res["percentuais"]["Saúde"], 25.0)
        self.assertEqual(sum(res["por_categoria"].values()), 8)

    def test_contar_por_categoria(self):
        self.assertEqual(contar_por_categoria(ListaEncadeada()), {})


# ======================================================== PERSISTÊNCIA
class TestPersistencia(unittest.TestCase):
    def test_salvar_e_carregar(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "dados.json")
            original = sistema_com_exemplos()
            original.salvar(caminho)
            copia = SistemaCidadao()
            self.assertEqual(copia.carregar(caminho), (8, 0))
            self.assertEqual([s.para_dict() for s in original.lista],
                             [s.para_dict() for s in copia.lista])

    def test_arquivo_inexistente(self):
        self.assertEqual(SistemaCidadao().carregar("/tmp/nao_existe_xyz.json"), (0, 0))

    def test_arquivo_corrompido(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "ruim.json")
            with open(caminho, "w", encoding="utf-8") as f:
                f.write("{isto não é json")
            with self.assertRaises(ca.ErroSistema):
                SistemaCidadao().carregar(caminho)

    def test_registros_invalidos_sao_ignorados(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "misto.json")
            with open(caminho, "w", encoding="utf-8") as f:
                f.write('[{"id":1,"titulo":"A","categoria":"Saúde","descricao":"d",'
                        '"requisitos":"r","local":"l"},{"id":-5},'
                        '{"id":1,"titulo":"Dup","categoria":"Saúde","descricao":"d",'
                        '"requisitos":"r","local":"l"}]')
            sis = SistemaCidadao()
            self.assertEqual(sis.carregar(caminho), (1, 2))


# ================================================== MENU (ENTRADA SIMULADA)
def executar_menu(entradas, sis=None):
    sis = sis or SistemaCidadao()
    saida = io.StringIO()
    with patch("builtins.input", side_effect=entradas), contextlib.redirect_stdout(saida):
        ca.menu(sis)
    return sis, saida.getvalue()


class TestMenu(unittest.TestCase):
    def test_opcao_inexistente_e_encerrar(self):
        _, saida = executar_menu(["abc", "99", "", "0"])
        self.assertEqual(saida.count("Opção inexistente"), 3)
        self.assertIn("Até logo!", saida)

    def test_operacoes_com_lista_vazia(self):
        _, saida = executar_menu(["2", "3", "4", "5", "6", "7", "8", "0"])
        self.assertIn("A lista está vazia. Cadastre serviços primeiro.", saida)
        self.assertIn("Nada a atualizar", saida)
        self.assertIn("Nada a excluir", saida)
        self.assertIn("Nada a pesquisar", saida)
        self.assertIn("Nada a ordenar", saida)
        self.assertIn("Nenhum serviço cadastrado.", saida)
        self.assertIn("Sem dados para análise.", saida)

    def test_cadastro_com_entradas_invalidas_e_duplicado(self):
        sis = sistema_com_exemplos()
        entradas = ["1",
                    "abc", "-1", "1", "100",        # inválidos, duplicado, válido
                    "", "Título válido",            # título vazio, depois válido
                    "9", "0", "2",                  # categoria inválida x2, depois 2
                    "Descrição", "Requisitos", "Local",
                    "0"]
        sis, saida = executar_menu(entradas, sis)
        self.assertIn("deve ser um número inteiro positivo", saida)
        self.assertIn("Já existe um serviço com o ID 1", saida)
        self.assertIn("é obrigatório", saida)
        self.assertIn("Escolha um número de 1 a 5", saida)
        self.assertEqual(sis.consultar(100).categoria, "Assistência Social")
        self.assertEqual(len(sis.lista), 9)

    def test_consulta_inexistente(self):
        _, saida = executar_menu(["2", "777", "0"], sistema_com_exemplos())
        self.assertIn("Nenhum serviço encontrado com o ID 777", saida)

    def test_pesquisa_sem_resultado_e_com_resultado(self):
        _, saida = executar_menu(["5", "1", "zzz", "5", "2", "saude", "5", "9", "0"],
                                 sistema_com_exemplos())
        self.assertIn("Nenhum serviço encontrado para 'zzz'", saida)
        self.assertIn("2 serviço(s) encontrado(s)", saida)
        self.assertIn("Opção inválida", saida)

    def test_exclusao_com_confirmacao(self):
        sis, saida = executar_menu(["4", "3", "talvez", "n", "4", "3", "s", "0"],
                                   sistema_com_exemplos())
        self.assertIn("Responda com 's' ou 'n'", saida)
        self.assertIn("Exclusão cancelada", saida)
        self.assertIsNone(sis.consultar(3))
        self.assertEqual(len(sis.lista), 7)

    def test_atualizacao_mantem_valores_com_enter(self):
        sis, _ = executar_menu(["3", "2", "Vacinação 2026", "", "", "", "", "0"],
                               sistema_com_exemplos())
        s = sis.consultar(2)
        self.assertEqual(s.titulo, "Vacinação 2026")
        self.assertEqual(s.categoria, "Saúde")

    def test_ordenar_e_analise(self):
        sis, saida = executar_menu(["6", "2", "8", "0"], sistema_com_exemplos())
        self.assertIn("Lista ordenada por titulo (Merge Sort)", saida)
        self.assertIn("Total de registros: 8", saida)
        titulos = [s.titulo for s in sis.lista]
        self.assertEqual(titulos[0], "Cadastro Único (CadÚnico)")

    def test_fim_de_entrada_nao_quebra(self):
        _, saida = executar_menu(["7", EOFError()])   # EOF na leitura seguinte
        self.assertIn("Entrada encerrada.", saida)


if __name__ == "__main__":
    unittest.main(verbosity=2)
