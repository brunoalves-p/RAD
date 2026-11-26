import wx
import hashlib
import mysql.connector
from mysql.connector import Error


CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
}

BANCO = "pets_db"


def gerar_hash(senha):
    # guarda só o hash da senha, nunca a senha digitada
    return hashlib.sha256(senha.encode("utf-8")).hexdigest()


def executar(sql, parametros=(), buscar=False):
    # abre a conexão, roda o comando, salva e fecha
    conexao = mysql.connector.connect(database=BANCO, **CONFIG)
    cursor = conexao.cursor()
    cursor.execute(sql, parametros)
    resultado = cursor.fetchall() if buscar else None
    conexao.commit()
    cursor.close()
    conexao.close()
    return resultado


def preparar_banco():
    # cria o banco (se não existir)
    conexao = mysql.connector.connect(**CONFIG)
    cursor = conexao.cursor()
    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {BANCO}")
    cursor.close()
    conexao.close()

    # tabela de usuários (login e senha)
    executar(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INT AUTO_INCREMENT PRIMARY KEY,
            login VARCHAR(100) NOT NULL UNIQUE,
            senha CHAR(64) NOT NULL
        )
        """
    )

    # tabela de pets: usuario_id liga cada pet ao dono
    executar(
        """
        CREATE TABLE IF NOT EXISTS pets (
            id INT AUTO_INCREMENT PRIMARY KEY,
            usuario_id INT NOT NULL,
            nome VARCHAR(100) NOT NULL,
            idade INT NOT NULL,
            raca VARCHAR(100) NOT NULL,
            peso DECIMAL(6,2) NOT NULL,
            cor VARCHAR(50) NOT NULL,
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        )
        """
    )

    # cria o usuário padrão se a tabela estiver vazia
    total = executar("SELECT COUNT(*) FROM usuarios", buscar=True)[0][0]
    if total == 0:
        executar(
            "INSERT INTO usuarios (login, senha) VALUES (%s, %s)",
            ("Fulano", gerar_hash("1234"))
        )


def avisar(janela, texto):
    wx.MessageBox(texto, "Sistema", wx.OK | wx.ICON_WARNING, janela)


class TelaPets(wx.Dialog):
    def __init__(self, pai, usuario_id, login):
        super().__init__(pai, title=f"Pets de {login}", size=(640, 520))
        self.usuario_id = usuario_id
        self.ids = []  # id do banco de cada linha da lista

        painel = wx.Panel(self)

        # campos do formulário
        wx.StaticText(painel, label="Nome:", pos=(20, 25))
        self.nome = wx.TextCtrl(painel, pos=(100, 20), size=(200, 25))

        wx.StaticText(painel, label="Idade:", pos=(20, 60))
        self.idade = wx.TextCtrl(painel, pos=(100, 55), size=(200, 25))

        wx.StaticText(painel, label="Raça:", pos=(20, 95))
        self.raca = wx.TextCtrl(painel, pos=(100, 90), size=(200, 25))

        wx.StaticText(painel, label="Peso (kg):", pos=(20, 130))
        self.peso = wx.TextCtrl(painel, pos=(100, 125), size=(200, 25))

        wx.StaticText(painel, label="Cor:", pos=(20, 165))
        self.cor = wx.TextCtrl(painel, pos=(100, 160), size=(200, 25))

        # botões
        adicionar = wx.Button(painel, label="Adicionar", pos=(350, 20), size=(130, 35))
        excluir = wx.Button(painel, label="Excluir selecionado", pos=(350, 65), size=(130, 35))
        voltar = wx.Button(painel, label="Voltar ao login", pos=(350, 110), size=(130, 35))

        adicionar.Bind(wx.EVT_BUTTON, self.adicionar)
        excluir.Bind(wx.EVT_BUTTON, self.excluir)
        voltar.Bind(wx.EVT_BUTTON, lambda evento: self.EndModal(wx.ID_OK))

        # lista dos pets cadastrados
        self.lista = wx.ListCtrl(
            painel,
            pos=(20, 210),
            size=(590, 250),
            style=wx.LC_REPORT | wx.LC_SINGLE_SEL
        )
        self.lista.InsertColumn(0, "Nome", width=150)
        self.lista.InsertColumn(1, "Idade", width=60)
        self.lista.InsertColumn(2, "Raça", width=150)
        self.lista.InsertColumn(3, "Peso (kg)", width=100)
        self.lista.InsertColumn(4, "Cor", width=120)

        self.CentreOnParent()
        self.mostrar_pets()

    def mostrar_pets(self):
        # busca só os pets do usuário logado e preenche a lista
        self.lista.DeleteAllItems()
        self.ids = []

        try:
            pets = executar(
                "SELECT id, nome, idade, raca, peso, cor FROM pets "
                "WHERE usuario_id = %s",
                (self.usuario_id,),
                buscar=True
            )
        except Error:
            avisar(self, "Erro ao acessar o banco de dados.")
            return

        for pet in pets:
            self.ids.append(pet[0])
            linha = self.lista.InsertItem(self.lista.GetItemCount(), pet[1])
            self.lista.SetItem(linha, 1, str(pet[2]))
            self.lista.SetItem(linha, 2, pet[3])
            self.lista.SetItem(linha, 3, str(pet[4]))
            self.lista.SetItem(linha, 4, pet[5])

    def adicionar(self, evento):
        nome = self.nome.GetValue().strip()
        idade = self.idade.GetValue().strip()
        raca = self.raca.GetValue().strip()
        peso = self.peso.GetValue().strip().replace(",", ".")
        cor = self.cor.GetValue().strip()

        # validações básicas
        if not nome or not idade or not raca or not peso or not cor:
            avisar(self, "Preencha todos os campos.")
            return

        if not idade.isdigit():
            avisar(self, "A idade deve ser um número inteiro.")
            return

        try:
            peso = float(peso)
        except ValueError:
            avisar(self, "O peso deve ser um número. Ex.: 4.5")
            return

        # salva o pet ligado ao usuário logado
        try:
            executar(
                "INSERT INTO pets (usuario_id, nome, idade, raca, peso, cor) "
                "VALUES (%s, %s, %s, %s, %s, %s)",
                (self.usuario_id, nome, int(idade), raca, peso, cor)
            )
        except Error:
            avisar(self, "Não foi possível salvar o pet.")
            return

        # limpa os campos e atualiza a lista
        for campo in (self.nome, self.idade, self.raca, self.peso, self.cor):
            campo.Clear()
        self.nome.SetFocus()
        self.mostrar_pets()

    def excluir(self, evento):
        indice = self.lista.GetFirstSelected()

        if indice == -1:
            avisar(self, "Selecione um pet na lista.")
            return

        # só apaga se o pet for do usuário logado
        try:
            executar(
                "DELETE FROM pets WHERE id = %s AND usuario_id = %s",
                (self.ids[indice], self.usuario_id)
            )
        except Error:
            avisar(self, "Não foi possível excluir o pet.")
            return

        self.mostrar_pets()


class TelaLogin(wx.Frame):
    def __init__(self):
        super().__init__(None, title="Cadastro de PETs", size=(400, 350))

        painel = wx.Panel(self)

        wx.StaticText(painel, label="Cadastro de PETs", pos=(130, 30))

        wx.StaticText(painel, label="Login:", pos=(40, 90))
        self.login = wx.TextCtrl(painel, pos=(110, 85), size=(220, 28))

        wx.StaticText(painel, label="Senha:", pos=(40, 140))
        self.senha = wx.TextCtrl(
            painel,
            pos=(110, 135),
            size=(220, 28),
            style=wx.TE_PASSWORD
        )

        entrar = wx.Button(painel, label="Entrar", pos=(70, 200), size=(115, 40))
        sair = wx.Button(painel, label="Sair", pos=(205, 200), size=(115, 40))

        entrar.Bind(wx.EVT_BUTTON, self.entrar)
        sair.Bind(wx.EVT_BUTTON, lambda evento: self.Close())

        entrar.SetDefault()
        self.Centre()

    def entrar(self, evento):
        login = self.login.GetValue().strip()
        senha = self.senha.GetValue()

        if not login or not senha:
            avisar(self, "Informe o login e a senha.")
            return

        # procura um usuário com esse login e esse hash de senha
        try:
            usuario = executar(
                "SELECT id FROM usuarios WHERE login = %s AND senha = %s",
                (login, gerar_hash(senha)),
                buscar=True
            )
        except Error:
            avisar(self, "Erro ao acessar o banco de dados.")
            return

        if not usuario:
            avisar(self, "Login ou senha incorretos.")
            self.senha.Clear()
            return

        # abre a tela de pets só com os dados desse usuário
        with TelaPets(self, usuario[0][0], login) as janela:
            janela.ShowModal()

        self.senha.Clear()


if __name__ == "__main__":
    app = wx.App(False)

    try:
        preparar_banco()
    except Error as erro:
        avisar(None, f"Não foi possível conectar ao MySQL:\n{erro}")
    else:
        TelaLogin().Show()
        app.MainLoop()