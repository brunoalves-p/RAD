import wx
import json
import hashlib
import secrets
import hmac
from pathlib import Path


# O arquivo é salvo na mesma pasta deste programa.
ARQUIVO = Path(__file__).resolve().parent / "usuarios.json"


def proteger_senha(senha):
    """Cria um hash para não salvar a senha em texto puro."""
    salt = secrets.token_hex(16)

    resumo = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        bytes.fromhex(salt),
        260000
    ).hex()

    return {"salt": salt, "hash": resumo}


def salvar_usuarios(usuarios):
    temporario = ARQUIVO.with_suffix(".tmp")
    temporario.write_text(
        json.dumps(usuarios, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )
    temporario.replace(ARQUIVO)


def carregar_usuarios():
    if not ARQUIVO.exists():
        salvar_usuarios({
            "Fulano": proteger_senha("1234")
        })

    return json.loads(ARQUIVO.read_text(encoding="utf-8"))


def verificar_senha(senha, registro):
    resumo = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        bytes.fromhex(registro["salt"]),
        260000
    ).hex()

    return hmac.compare_digest(resumo, registro["hash"])


def avisar(janela, texto, erro=False):
    icone = wx.ICON_WARNING if erro else wx.ICON_INFORMATION
    wx.MessageBox(texto, "Sistema", wx.OK | icone, janela)


class TelaPrincipal(wx.Dialog):
    """Janela aberta somente depois de validar o login."""

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

        # Mostra a senha para reproduzir a imagem da atividade.
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
    """Permite salvar uma nova senha para um usuário existente."""

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
            usuarios = carregar_usuarios()

            if usuario not in usuarios:
                avisar(self, "Usuário não encontrado.", True)
                return

            usuarios[usuario] = proteger_senha(senha)
            salvar_usuarios(usuarios)

        except (OSError, ValueError, KeyError, TypeError):
            avisar(
                self,
                "Não foi possível ler ou salvar o arquivo de usuários.",
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
            usuarios = carregar_usuarios()
            registro = usuarios.get(usuario)

            autorizado = (
                registro is not None
                and verificar_senha(senha, registro)
            )

        except (OSError, ValueError, KeyError, TypeError):
            avisar(
                self,
                "Não foi possível ler o arquivo de usuários.",
                True
            )
            return

        if not autorizado:
            avisar(self, "Usuário ou senha incorretos.", True)
            self.senha.Clear()
            self.senha.SetFocus()
            return

        # Só cria a outra janela quando a senha está correta.
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
    janela = TelaLogin()
    janela.Show()
    app.MainLoop()