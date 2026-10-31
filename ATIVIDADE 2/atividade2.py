import wx
import hashlib
import secrets
import hmac
import mysql.connector
from mysql.connector import Error


CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "",
}

BANCO = "sistema_cadastro"


def proteger_senha(senha):
    salt = secrets.token_hex(16)

    resumo = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        bytes.fromhex(salt),
        260000
    ).hex()

    return {"salt": salt, "hash": resumo}


def verificar_senha(senha, registro):
    resumo = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        bytes.fromhex(registro["salt"]),
        260000
    ).hex()

    return hmac.compare_digest(resumo, registro["hash"])


def conectar():
    return mysql.connector.connect(database=BANCO, **CONFIG)


def preparar_banco():
    conexao = mysql.connector.connect(**CONFIG)
    try:
        cursor = conexao.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS {BANCO} "
            "CHARACTER SET utf8mb4"
        )
        cursor.close()
    finally:
        conexao.close()

    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INT AUTO_INCREMENT PRIMARY KEY,
                usuario VARCHAR(100) NOT NULL UNIQUE,
                salt CHAR(32) NOT NULL,
                hash CHAR(64) NOT NULL
            )
            """
        )

        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total = cursor.fetchone()[0]

        if total == 0:
            registro = proteger_senha("1234")
            cursor.execute(
                "INSERT INTO usuarios (usuario, salt, hash) "
                "VALUES (%s, %s, %s)",
                ("Fulano", registro["salt"], registro["hash"])
            )

        conexao.commit()
        cursor.close()
    finally:
        conexao.close()


def buscar_usuario(usuario):
    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT salt, hash FROM usuarios WHERE usuario = %s",
            (usuario,)
        )
        linha = cursor.fetchone()
        cursor.close()
    finally:
        conexao.close()

    if linha is None:
        return None

    return {"salt": linha[0], "hash": linha[1]}


def atualizar_senha(usuario, registro):
    conexao = conectar()
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "UPDATE usuarios SET salt = %s, hash = %s WHERE usuario = %s",
            (registro["salt"], registro["hash"], usuario)
        )
        conexao.commit()
        cursor.close()
    finally:
        conexao.close()


def avisar(janela, texto, erro=False):
    icone = wx.ICON_WARNING if erro else wx.ICON_INFORMATION
    wx.MessageBox(texto, "Sistema", wx.OK | icone, janela)


class TelaPrincipal(wx.Dialog):
    def __init__(self, pai, usuario, senha):
        super().__init__(
            pai,
            title="Acesso autorizado",
            size=(380, 430)
        )

        painel = wx.Panel(self)
        painel.SetBackgroundColour("#D9D9D9")

        wx.StaticText(
            painel,
            label=f"Login: {usuario}",
            pos=(30, 40)
        )

        wx.StaticText(
            painel,
            label=f"Senha: {senha}",
            pos=(30, 75)
        )

        voltar = wx.Button(
            painel,
            label="Voltar ao login",
            pos=(110, 300),
            size=(150, 35)
        )

        voltar.Bind(
            wx.EVT_BUTTON,
            lambda evento: self.EndModal(wx.ID_OK)
        )

        self.CentreOnParent()


class TelaRecuperacao(wx.Dialog):
    def __init__(self, pai):
        super().__init__(
            pai,
            title="Redefinir senha",
            size=(400, 430)
        )

        painel = wx.Panel(self)
        painel.SetBackgroundColour("#D9D9D9")

        wx.StaticText(
            painel,
            label="Redefinir senha",
            pos=(135, 35)
        )

        wx.StaticText(painel, label="Usuário:", pos=(30, 105))
        self.usuario = wx.TextCtrl(
            painel,
            pos=(130, 100),
            size=(220, 28)
        )

        wx.StaticText(painel, label="Senha:", pos=(30, 155))
        self.senha = wx.TextCtrl(
            painel,
            pos=(130, 150),
            size=(220, 28),
            style=wx.TE_PASSWORD
        )

        wx.StaticText(
            painel,
            label="Confirme a\nsenha:",
            pos=(30, 205)
        )

        self.confirmacao = wx.TextCtrl(
            painel,
            pos=(130, 200),
            size=(220, 28),
            style=wx.TE_PASSWORD
        )

        salvar = wx.Button(
            painel,
            label="Salvar",
            pos=(65, 280),
            size=(115, 35)
        )

        cancelar = wx.Button(
            painel,
            label="Cancelar",
            pos=(200, 280),
            size=(115, 35)
        )

        salvar.Bind(wx.EVT_BUTTON, self.redefinir)

        cancelar.Bind(
            wx.EVT_BUTTON,
            lambda evento: self.EndModal(wx.ID_CANCEL)
        )

        salvar.SetDefault()
        self.CentreOnParent()

    def redefinir(self, evento):
        usuario = self.usuario.GetValue().strip()
        senha = self.senha.GetValue()
        confirmacao = self.confirmacao.GetValue()

        if not usuario or not senha.strip() or not confirmacao:
            avisar(self, "Preencha todos os campos.", True)
            return

        if senha != confirmacao:
            avisar(self, "As senhas não coincidem.", True)
            return

        try:
            if buscar_usuario(usuario) is None:
                avisar(self, "Usuário não encontrado.", True)
                return

            atualizar_senha(usuario, proteger_senha(senha))

        except Error:
            avisar(
                self,
                "Não foi possível acessar o banco de dados.",
                True
            )
            return

        avisar(self, "Senha redefinida com sucesso!")
        self.EndModal(wx.ID_OK)


class TelaLogin(wx.Frame):
    def __init__(self):
        super().__init__(
            None,
            title="Sistema de Cadastro",
            size=(400, 430)
        )

        painel = wx.Panel(self)
        painel.SetBackgroundColour("#D9D9D9")

        titulo = wx.StaticText(
            painel,
            label="Sistema de Cadastro",
            pos=(65, 40)
        )

        titulo.SetFont(
            wx.Font(
                18,
                wx.FONTFAMILY_SWISS,
                wx.FONTSTYLE_NORMAL,
                wx.FONTWEIGHT_NORMAL
            )
        )

        wx.StaticText(painel, label="Usuário:", pos=(40, 145))
        self.usuario = wx.TextCtrl(
            painel,
            pos=(125, 140),
            size=(220, 28)
        )

        wx.StaticText(painel, label="Senha:", pos=(40, 195))
        self.senha = wx.TextCtrl(
            painel,
            pos=(125, 190),
            size=(220, 28),
            style=wx.TE_PASSWORD
        )

        entrar = wx.Button(
            painel,
            label="Entrar",
            pos=(65, 250),
            size=(115, 40)
        )

        sair = wx.Button(
            painel,
            label="Sair",
            pos=(200, 250),
            size=(115, 40)
        )

        recuperar = wx.Button(
            painel,
            label="Redefinir senha",
            pos=(120, 305),
            size=(150, 30)
        )

        entrar.Bind(wx.EVT_BUTTON, self.entrar)
        sair.Bind(wx.EVT_BUTTON, lambda evento: self.Close())
        recuperar.Bind(wx.EVT_BUTTON, self.recuperar)

        entrar.SetDefault()
        self.usuario.SetFocus()
        self.Centre()

    def entrar(self, evento):
        usuario = self.usuario.GetValue().strip()
        senha = self.senha.GetValue()

        if not usuario or not senha:
            avisar(self, "Informe o usuário e a senha.", True)
            return

        try:
            registro = buscar_usuario(usuario)

            autorizado = (
                registro is not None
                and verificar_senha(senha, registro)
            )

        except Error:
            avisar(
                self,
                "Não foi possível acessar o banco de dados.",
                True
            )
            return

        if not autorizado:
            avisar(self, "Usuário ou senha incorretos.", True)
            self.senha.Clear()
            self.senha.SetFocus()
            return

        with TelaPrincipal(self, usuario, senha) as janela:
            janela.ShowModal()

        self.senha.Clear()
        self.senha.SetFocus()

    def recuperar(self, evento):
        with TelaRecuperacao(self) as janela:
            janela.usuario.SetValue(self.usuario.GetValue())

            if janela.ShowModal() == wx.ID_OK:
                self.senha.Clear()
                self.senha.SetFocus()


if __name__ == "__main__":
    app = wx.App(False)

    try:
        preparar_banco()
    except Error as erro:
        avisar(
            None,
            f"Não foi possível conectar ao MySQL:\n{erro}",
            True
        )
    else:
        janela = TelaLogin()
        janela.Show()
        app.MainLoop()