"""
Redux Browser — Assistente de Primeiro Uso (Onboarding Wizard)

Wizard de 5 páginas apresentado na primeira execução:
  1. Boas-vindas
  2. Tema & Aparência
  3. Motor de Busca
  4. Privacidade & Segurança
  5. Tudo pronto!

Design premium: frameless, animações de slide, dot-indicator,
paleta adaptativa Redux (accent #FF3B3B).
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QWidget, QStackedWidget, QGraphicsDropShadowEffect,
    QGridLayout, QSizePolicy, QButtonGroup, QRadioButton,
    QGraphicsOpacityEffect, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup,
    QPoint, QSize, pyqtSignal, QTimer
)
from PyQt6.QtGui import QColor, QFont, QPixmap, QIcon

from browser.ui.theme import Theme
from browser.ui.icons import Icons
from browser.config.settings_manager import get_settings
from browser.config.search_engines import (
    PRIVATE_ENGINES, POPULAR_ENGINES, set_current_engine
)
from browser.security.brave_farbling import FarblingLevel
from browser.security.adblock_engine import AdBlockLevel


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_W, _H = 720, 540
_ANIM_DURATION = 350

_PAGE_WELCOME = 0
_PAGE_THEME = 1
_PAGE_SEARCH = 2
_PAGE_PRIVACY = 3
_PAGE_DONE = 4
_TOTAL_PAGES = 5


# ---------------------------------------------------------------------------
# Helpers SVG
# ---------------------------------------------------------------------------
def _colored_svg(svg: str, color: str) -> str:
    return svg.replace("currentColor", color)


def _svg_icon(svg_str: str, color: str, size: int = 18) -> QIcon:
    colored = _colored_svg(svg_str, color)
    pm = QPixmap()
    pm.loadFromData(colored.encode("utf-8"), "SVG")
    return QIcon(pm)


def _svg_pixmap(svg_str: str, color: str, size: int = 48) -> QPixmap:
    # Resize the viewBox for larger rendering
    import re as _re
    colored = _colored_svg(svg_str, color)
    colored = _re.sub(r'width="\d+"', f'width="{size}"', colored)
    colored = _re.sub(r'height="\d+"', f'height="{size}"', colored)
    pm = QPixmap()
    pm.loadFromData(colored.encode("utf-8"), "SVG")
    return pm


# ---------------------------------------------------------------------------
# Dot Indicator Widget
# ---------------------------------------------------------------------------
class _DotIndicator(QWidget):
    """Bolinhas de progresso horizontais."""

    def __init__(self, total: int, accent: str, inactive: str, parent=None):
        super().__init__(parent)
        self._total = total
        self._current = 0
        self._accent = accent
        self._inactive = inactive
        self._dots: list[QLabel] = []

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for i in range(total):
            dot = QLabel()
            dot.setFixedSize(10, 10)
            self._dots.append(dot)
            lay.addWidget(dot)

        self._update()

    def set_current(self, index: int):
        self._current = index
        self._update()

    def _update(self):
        for i, dot in enumerate(self._dots):
            if i == self._current:
                dot.setStyleSheet(
                    f"background: {self._accent}; border-radius: 5px;"
                )
            else:
                dot.setStyleSheet(
                    f"background: {self._inactive}; border-radius: 5px;"
                )


# ---------------------------------------------------------------------------
# Selection Card — reusable
# ---------------------------------------------------------------------------
class _SelectionCard(QWidget):
    """Card clicável com borda de destaque ao selecionar."""

    clicked = pyqtSignal()

    def __init__(
        self,
        title: str,
        subtitle: str = "",
        icon_label: str = "",
        palette: dict | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self._selected = False
        self._p = palette or Theme.DARK
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 12, 14, 12)
        lay.setSpacing(4)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        if icon_label:
            ico = QLabel(icon_label)
            ico.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ico.setStyleSheet("font-size: 26px; background: transparent; border: none;")
            lay.addWidget(ico)

        t = QLabel(title)
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        t.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {self._p['text_primary']};"
            " background: transparent; border: none;"
        )
        t.setWordWrap(True)
        lay.addWidget(t)

        if subtitle:
            s = QLabel(subtitle)
            s.setAlignment(Qt.AlignmentFlag.AlignCenter)
            s.setStyleSheet(
                f"font-size: 11px; color: {self._p['text_secondary']};"
                " background: transparent; border: none;"
            )
            s.setWordWrap(True)
            lay.addWidget(s)

        self._apply_style()

    def set_selected(self, val: bool):
        self._selected = val
        self._apply_style()

    def is_selected(self) -> bool:
        return self._selected

    def _apply_style(self):
        p = self._p
        if self._selected:
            self.setStyleSheet(
                f"_SelectionCard {{ background: {p['accent_subtle']};"
                f" border: 2px solid {p['accent']};"
                f" border-radius: {p['radius_lg']}; }}"
            )
        else:
            self.setStyleSheet(
                f"_SelectionCard {{ background: {p['bg_tertiary']};"
                f" border: 1px solid {p['border']};"
                f" border-radius: {p['radius_lg']}; }}"
            )

    def mousePressEvent(self, ev):
        self.clicked.emit()
        super().mousePressEvent(ev)


# ---------------------------------------------------------------------------
# Onboarding Wizard
# ---------------------------------------------------------------------------
class OnboardingWizard(QDialog):
    """
    Assistente de primeiro uso do Redux Browser.
    Apresenta 5 páginas para personalização inicial.
    """

    # Emitido ao finalizar com dict de configurações escolhidas
    finished_setup = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._settings = get_settings()
        self._theme_name = self._settings.get("theme", "dark")
        self._p = Theme.DARK if self._theme_name == "dark" else Theme.LIGHT
        self._animating = False

        # Escolhas do usuário (defaults)
        self._choices: dict = {
            "theme": "dark",
            "search_engine": "DuckDuckGo",
            "farbling_level": "balanced",
            "adblock_level": "standard",
        }

        self._setup_window()
        self._build_ui()

    # ── window setup ──────────────────────────────────────────────────
    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(_W + 40, _H + 40)  # margin for shadow
        self.setModal(True)

    # ── main layout ───────────────────────────────────────────────────
    def _build_ui(self):
        p = self._p

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(20, 20, 20, 20)

        # Container with shadow
        self._container = QWidget()
        self._container.setObjectName("onboardingContainer")
        self._container.setFixedSize(_W, _H)
        self._apply_container_style()

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(48)
        shadow.setColor(QColor(0, 0, 0, int(255 * (0.7 if self._theme_name == "dark" else 0.25))))
        shadow.setOffset(0, 16)
        self._container.setGraphicsEffect(shadow)
        root_layout.addWidget(self._container, alignment=Qt.AlignmentFlag.AlignCenter)

        # Inner layout
        inner = QVBoxLayout(self._container)
        inner.setContentsMargins(0, 0, 0, 0)
        inner.setSpacing(0)

        # Stacked widget for pages
        self._stack = QStackedWidget()
        inner.addWidget(self._stack, 1)

        # Bottom bar (dots + buttons)
        bottom = QWidget()
        bottom.setStyleSheet("background: transparent;")
        bottom_lay = QHBoxLayout(bottom)
        bottom_lay.setContentsMargins(28, 0, 28, 20)

        self._btn_back = QPushButton("Voltar")
        self._btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_back.clicked.connect(self._go_back)
        self._btn_back.setVisible(False)
        bottom_lay.addWidget(self._btn_back)

        bottom_lay.addStretch()

        self._dots = _DotIndicator(
            _TOTAL_PAGES, p["accent"], p["border_hover"]
        )
        bottom_lay.addWidget(self._dots)

        bottom_lay.addStretch()

        self._btn_next = QPushButton("Continuar")
        self._btn_next.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_next.clicked.connect(self._go_next)
        bottom_lay.addWidget(self._btn_next)

        inner.addWidget(bottom)

        self._apply_button_styles()

        # Build pages
        self._stack.addWidget(self._build_welcome_page())
        self._stack.addWidget(self._build_theme_page())
        self._stack.addWidget(self._build_search_page())
        self._stack.addWidget(self._build_privacy_page())
        self._stack.addWidget(self._build_done_page())

        self._stack.setCurrentIndex(0)
        self._dots.set_current(0)

    # ── navigation ────────────────────────────────────────────────────
    def _current_index(self) -> int:
        return self._stack.currentIndex()

    def _go_next(self):
        if self._animating:
            return
        idx = self._current_index()
        if idx == _PAGE_DONE:
            self._finish()
            return
        self._slide_to(idx + 1)

    def _go_back(self):
        if self._animating:
            return
        idx = self._current_index()
        if idx > 0:
            self._slide_to(idx - 1, forward=False)

    def _slide_to(self, new_idx: int, forward: bool = True):
        """Animated slide transition between pages."""
        old_widget = self._stack.currentWidget()
        new_widget = self._stack.widget(new_idx)

        if old_widget is new_widget:
            return

        self._animating = True
        w = self._stack.width()

        # Position new widget off-screen
        new_widget.setGeometry(
            w if forward else -w, 0, w, self._stack.height()
        )
        new_widget.show()

        # Animate old widget out
        anim_old = QPropertyAnimation(old_widget, b"pos")
        anim_old.setDuration(_ANIM_DURATION)
        anim_old.setStartValue(QPoint(0, 0))
        anim_old.setEndValue(QPoint(-w if forward else w, 0))
        anim_old.setEasingCurve(QEasingCurve.Type.InOutCubic)

        # Animate new widget in
        anim_new = QPropertyAnimation(new_widget, b"pos")
        anim_new.setDuration(_ANIM_DURATION)
        anim_new.setStartValue(QPoint(w if forward else -w, 0))
        anim_new.setEndValue(QPoint(0, 0))
        anim_new.setEasingCurve(QEasingCurve.Type.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_old)
        group.addAnimation(anim_new)

        def on_finished():
            self._stack.setCurrentIndex(new_idx)
            self._animating = False
            self._update_nav(new_idx)

        group.finished.connect(on_finished)
        group.start()

        self._dots.set_current(new_idx)

    def _update_nav(self, idx: int):
        """Update button text/visibility based on page index."""
        self._btn_back.setVisible(idx > 0)

        if idx == _PAGE_DONE:
            self._btn_next.setText("Começar a Navegar 🚀")
        elif idx == _PAGE_WELCOME:
            self._btn_next.setText("Vamos lá!")
        else:
            self._btn_next.setText("Continuar")

        self._apply_button_styles()

    def _finish(self):
        """Save all choices and close."""
        s = self._settings

        s.set("theme", self._choices["theme"])
        s.set("search_engine", self._choices["search_engine"])
        s.set("farbling_level", self._choices["farbling_level"])
        s.set("adblock_level", self._choices["adblock_level"])
        s.set("onboarding_completed", True)

        # Set search engine via module helper
        from browser.config.search_engines import ALL_ENGINES
        for eng in ALL_ENGINES:
            if eng.name == self._choices["search_engine"]:
                set_current_engine(eng)
                break

        self.finished_setup.emit(dict(self._choices))
        self.accept()

    # ==================================================================
    #  PAGE 1 — Boas-vindas
    # ==================================================================
    def _build_welcome_page(self) -> QWidget:
        p = self._p
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(48, 40, 48, 20)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Shield icon
        shield_pm = _svg_pixmap(Icons.SHIELD, p["accent"], 72)
        icon_lbl = QLabel()
        icon_lbl.setPixmap(shield_pm)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(icon_lbl)

        lay.addSpacing(20)

        # Title
        title = QLabel("Bem-vindo ao Redux Browser")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 28px; font-weight: 700; color: {p['text_primary']};"
            " background: transparent;"
        )
        lay.addWidget(title)

        lay.addSpacing(12)

        # Subtitle
        subtitle = QLabel(
            "Um navegador feito para quem valoriza\n"
            "privacidade, velocidade e personalização."
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 15px; color: {p['text_secondary']}; line-height: 1.6;"
            " background: transparent;"
        )
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        lay.addSpacing(32)

        # Feature chips
        features = [
            ("🛡️", "Proteção anti-fingerprint"),
            ("🚫", "Bloqueador de anúncios"),
            ("🔒", "Busca privada por padrão"),
        ]
        chip_row = QHBoxLayout()
        chip_row.setSpacing(12)
        chip_row.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for emoji, text in features:
            chip = QLabel(f"  {emoji}  {text}  ")
            chip.setStyleSheet(
                f"background: {p['bg_tertiary']}; color: {p['text_primary']};"
                f" border: 1px solid {p['border']}; border-radius: 20px;"
                " padding: 8px 14px; font-size: 12px;"
            )
            chip_row.addWidget(chip)

        lay.addLayout(chip_row)

        lay.addStretch()
        return page

    # ==================================================================
    #  PAGE 2 — Tema & Aparência
    # ==================================================================
    def _build_theme_page(self) -> QWidget:
        p = self._p
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(48, 36, 48, 20)
        lay.setSpacing(0)

        # Title
        title = QLabel("Escolha seu tema")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {p['text_primary']};"
            " background: transparent;"
        )
        lay.addWidget(title)

        lay.addSpacing(6)

        subtitle = QLabel("Você pode alterar depois nas configurações.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {p['text_secondary']}; background: transparent;"
        )
        lay.addWidget(subtitle)

        lay.addSpacing(28)

        # Theme cards
        cards_lay = QHBoxLayout()
        cards_lay.setSpacing(20)
        cards_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._theme_cards: dict[str, _ThemePreviewCard] = {}

        dark_card = _ThemePreviewCard("dark", p)
        light_card = _ThemePreviewCard("light", p)

        dark_card.clicked.connect(lambda: self._select_theme("dark"))
        light_card.clicked.connect(lambda: self._select_theme("light"))

        self._theme_cards["dark"] = dark_card
        self._theme_cards["light"] = light_card

        cards_lay.addWidget(dark_card)
        cards_lay.addWidget(light_card)

        lay.addLayout(cards_lay)
        lay.addStretch()

        # Default selection
        self._select_theme("dark")

        return page

    def _select_theme(self, theme_name: str):
        self._choices["theme"] = theme_name
        for name, card in self._theme_cards.items():
            card.set_selected(name == theme_name)

        # Live preview: re-theme the wizard itself
        self._theme_name = theme_name
        self._p = Theme.DARK if theme_name == "dark" else Theme.LIGHT
        self._apply_container_style()
        self._apply_button_styles()
        self._dots._accent = self._p["accent"]
        self._dots._inactive = self._p["border_hover"]
        self._dots._update()

    # ==================================================================
    #  PAGE 3 — Motor de Busca
    # ==================================================================
    def _build_search_page(self) -> QWidget:
        p = self._p
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(48, 36, 48, 20)
        lay.setSpacing(0)

        title = QLabel("Escolha seu motor de busca")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {p['text_primary']};"
            " background: transparent;"
        )
        lay.addWidget(title)

        lay.addSpacing(6)

        subtitle = QLabel("Motores com 🔒 não rastreiam suas buscas.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {p['text_secondary']}; background: transparent;"
        )
        lay.addWidget(subtitle)

        lay.addSpacing(20)

        # Scroll area for engine cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_inner = QWidget()
        scroll_inner.setStyleSheet("background: transparent;")
        grid = QGridLayout(scroll_inner)
        grid.setSpacing(10)

        self._engine_cards: dict[str, _SelectionCard] = {}

        # Private engines (top rows)
        priv_label = QLabel("🔒 Privados")
        priv_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {p['text_secondary']};"
            " background: transparent; border: none;"
        )
        grid.addWidget(priv_label, 0, 0, 1, 4)

        row, col = 1, 0
        for eng in PRIVATE_ENGINES:
            card = _SelectionCard(
                title=eng.name,
                icon_label=eng.icon,
                palette=p,
            )
            card.clicked.connect(lambda n=eng.name: self._select_engine(n))
            grid.addWidget(card, row, col)
            self._engine_cards[eng.name] = card
            col += 1
            if col >= 4:
                col = 0
                row += 1

        row += 1
        pop_label = QLabel("🌐 Populares")
        pop_label.setStyleSheet(
            f"font-size: 11px; font-weight: 600; color: {p['text_secondary']};"
            " background: transparent; border: none;"
        )
        grid.addWidget(pop_label, row, 0, 1, 4)
        row += 1
        col = 0

        for eng in POPULAR_ENGINES:
            card = _SelectionCard(
                title=eng.name,
                icon_label=eng.icon,
                palette=p,
            )
            card.clicked.connect(lambda n=eng.name: self._select_engine(n))
            grid.addWidget(card, row, col)
            self._engine_cards[eng.name] = card
            col += 1
            if col >= 4:
                col = 0
                row += 1

        scroll.setWidget(scroll_inner)
        lay.addWidget(scroll, 1)

        # Default
        self._select_engine("DuckDuckGo")

        return page

    def _select_engine(self, name: str):
        self._choices["search_engine"] = name
        for n, card in self._engine_cards.items():
            card.set_selected(n == name)

    # ==================================================================
    #  PAGE 4 — Privacidade & Segurança
    # ==================================================================
    def _build_privacy_page(self) -> QWidget:
        p = self._p
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(48, 36, 48, 20)
        lay.setSpacing(0)

        title = QLabel("Privacidade & Segurança")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {p['text_primary']};"
            " background: transparent;"
        )
        lay.addWidget(title)

        lay.addSpacing(6)

        subtitle = QLabel("Configure o nível de proteção do Redux Browser.")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 13px; color: {p['text_secondary']}; background: transparent;"
        )
        lay.addWidget(subtitle)

        lay.addSpacing(20)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { background: transparent; border: none; }"
        )
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_inner = QWidget()
        scroll_inner.setStyleSheet("background: transparent;")
        sections_lay = QVBoxLayout(scroll_inner)
        sections_lay.setSpacing(16)

        # ── Farbling section ──
        farb_title = QLabel("🛡️ Anti-Fingerprint (Farbling)")
        farb_title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {p['text_primary']};"
            " background: transparent; border: none;"
        )
        sections_lay.addWidget(farb_title)

        farb_desc = QLabel(
            "Altera sutilmente dados de fingerprint para proteger sua identidade."
        )
        farb_desc.setStyleSheet(
            f"font-size: 11px; color: {p['text_secondary']};"
            " background: transparent; border: none;"
        )
        farb_desc.setWordWrap(True)
        sections_lay.addWidget(farb_desc)

        farb_row = QHBoxLayout()
        farb_row.setSpacing(10)

        self._farbling_cards: dict[str, _SelectionCard] = {}
        farbling_opts = [
            ("off", "Desativado", "Sem proteção"),
            ("balanced", "Balanceado", "Recomendado"),
            ("maximum", "Máximo", "Pode quebrar sites"),
        ]
        for val, name, desc in farbling_opts:
            card = _SelectionCard(title=name, subtitle=desc, palette=p)
            card.clicked.connect(lambda v=val: self._select_farbling(v))
            farb_row.addWidget(card)
            self._farbling_cards[val] = card

        sections_lay.addLayout(farb_row)

        sections_lay.addSpacing(8)

        # ── AdBlock section ──
        ad_title = QLabel("🚫 Bloqueador de Anúncios")
        ad_title.setStyleSheet(
            f"font-size: 13px; font-weight: 600; color: {p['text_primary']};"
            " background: transparent; border: none;"
        )
        sections_lay.addWidget(ad_title)

        ad_desc = QLabel(
            "Bloqueia anúncios e rastreadores para uma navegação mais rápida e limpa."
        )
        ad_desc.setStyleSheet(
            f"font-size: 11px; color: {p['text_secondary']};"
            " background: transparent; border: none;"
        )
        ad_desc.setWordWrap(True)
        sections_lay.addWidget(ad_desc)

        ad_row = QHBoxLayout()
        ad_row.setSpacing(10)

        self._adblock_cards: dict[str, _SelectionCard] = {}
        adblock_opts = [
            ("off", "Desativado", "Sem bloqueio"),
            ("standard", "Padrão", "Recomendado"),
            ("aggressive", "Agressivo", "Máximo bloqueio"),
        ]
        for val, name, desc in adblock_opts:
            card = _SelectionCard(title=name, subtitle=desc, palette=p)
            card.clicked.connect(lambda v=val: self._select_adblock(v))
            ad_row.addWidget(card)
            self._adblock_cards[val] = card

        sections_lay.addLayout(ad_row)

        scroll.setWidget(scroll_inner)
        lay.addWidget(scroll, 1)

        # Defaults
        self._select_farbling("balanced")
        self._select_adblock("standard")

        return page

    def _select_farbling(self, level: str):
        self._choices["farbling_level"] = level
        for v, card in self._farbling_cards.items():
            card.set_selected(v == level)

    def _select_adblock(self, level: str):
        self._choices["adblock_level"] = level
        for v, card in self._adblock_cards.items():
            card.set_selected(v == level)

    # ==================================================================
    #  PAGE 5 — Tudo Pronto!
    # ==================================================================
    def _build_done_page(self) -> QWidget:
        p = self._p
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(48, 40, 48, 20)
        lay.setSpacing(0)
        lay.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Checkmark emoji
        check = QLabel("✅")
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check.setStyleSheet("font-size: 56px; background: transparent;")
        lay.addWidget(check)

        lay.addSpacing(16)

        title = QLabel("Tudo pronto!")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size: 26px; font-weight: 700; color: {p['text_primary']};"
            " background: transparent;"
        )
        lay.addWidget(title)

        lay.addSpacing(12)

        subtitle = QLabel(
            "Seu Redux Browser está configurado.\n"
            "Navegue com privacidade e velocidade."
        )
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(
            f"font-size: 14px; color: {p['text_secondary']};"
            " background: transparent; line-height: 1.5;"
        )
        subtitle.setWordWrap(True)
        lay.addWidget(subtitle)

        lay.addSpacing(28)

        # Summary cards
        self._summary_lay = QVBoxLayout()
        self._summary_lay.setSpacing(8)
        self._summary_lay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addLayout(self._summary_lay)

        lay.addStretch()
        return page

    def _refresh_summary(self):
        """Update summary labels based on current choices."""
        # Clear old widgets
        while self._summary_lay.count():
            item = self._summary_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        p = self._p
        items = [
            ("🎨", "Tema", "Escuro" if self._choices["theme"] == "dark" else "Claro"),
            ("🔍", "Busca", self._choices["search_engine"]),
            ("🛡️", "Farbling", {
                "off": "Desativado", "balanced": "Balanceado", "maximum": "Máximo"
            }.get(self._choices["farbling_level"], "Balanceado")),
            ("🚫", "AdBlock", {
                "off": "Desativado", "standard": "Padrão", "aggressive": "Agressivo"
            }.get(self._choices["adblock_level"], "Padrão")),
        ]

        for emoji, label, value in items:
            row = QLabel(f"  {emoji}  {label}: {value}")
            row.setStyleSheet(
                f"background: {p['bg_tertiary']}; color: {p['text_primary']};"
                f" border: 1px solid {p['border']}; border-radius: 10px;"
                " padding: 10px 18px; font-size: 13px;"
            )
            row.setAlignment(Qt.AlignmentFlag.AlignCenter)
            row.setMinimumWidth(340)
            self._summary_lay.addWidget(row, alignment=Qt.AlignmentFlag.AlignCenter)

    # ── styling helpers ───────────────────────────────────────────────
    def _apply_container_style(self):
        p = self._p
        self._container.setStyleSheet(
            f"QWidget#onboardingContainer {{"
            f"  background-color: {p['bg_primary']};"
            f"  border: 1px solid {p['border']};"
            f"  border-radius: {p['radius_xl']};"
            f"}}"
        )

    def _apply_button_styles(self):
        p = self._p
        # "Continuar" / primary button
        self._btn_next.setStyleSheet(
            f"QPushButton {{"
            f"  background: {p['accent']}; color: #FFFFFF;"
            f"  border: none; border-radius: {p['radius_md']};"
            f"  padding: 10px 28px; font-size: 13px; font-weight: 600;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {p['accent_hover']};"
            f"}}"
        )
        # "Voltar" / ghost button
        self._btn_back.setStyleSheet(
            f"QPushButton {{"
            f"  background: transparent; color: {p['text_secondary']};"
            f"  border: 1px solid {p['border']}; border-radius: {p['radius_md']};"
            f"  padding: 10px 22px; font-size: 13px;"
            f"}}"
            f"QPushButton:hover {{"
            f"  background: {p['bg_tertiary']}; color: {p['text_primary']};"
            f"}}"
        )

    # Override slide_to to also update summary when reaching done page
    def _slide_to(self, new_idx: int, forward: bool = True):
        """Animated slide transition between pages."""
        old_widget = self._stack.currentWidget()
        new_widget = self._stack.widget(new_idx)

        if old_widget is new_widget:
            return

        self._animating = True
        w = self._stack.width()

        new_widget.setGeometry(
            w if forward else -w, 0, w, self._stack.height()
        )
        new_widget.show()

        anim_old = QPropertyAnimation(old_widget, b"pos")
        anim_old.setDuration(_ANIM_DURATION)
        anim_old.setStartValue(QPoint(0, 0))
        anim_old.setEndValue(QPoint(-w if forward else w, 0))
        anim_old.setEasingCurve(QEasingCurve.Type.InOutCubic)

        anim_new = QPropertyAnimation(new_widget, b"pos")
        anim_new.setDuration(_ANIM_DURATION)
        anim_new.setStartValue(QPoint(w if forward else -w, 0))
        anim_new.setEndValue(QPoint(0, 0))
        anim_new.setEasingCurve(QEasingCurve.Type.InOutCubic)

        group = QParallelAnimationGroup(self)
        group.addAnimation(anim_old)
        group.addAnimation(anim_new)

        def on_finished():
            self._stack.setCurrentIndex(new_idx)
            self._animating = False
            self._update_nav(new_idx)
            # Refresh summary when arriving at done page
            if new_idx == _PAGE_DONE:
                self._refresh_summary()

        group.finished.connect(on_finished)
        group.start()

        self._dots.set_current(new_idx)

    # ── Close on Esc ──────────────────────────────────────────────────
    def keyPressEvent(self, event):
        # Disable Esc close during onboarding — must finish wizard
        if event.key() == Qt.Key.Key_Escape:
            return
        super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Theme Preview Card (for page 2)
# ---------------------------------------------------------------------------
class _ThemePreviewCard(QWidget):
    """
    A mini preview card that shows a fake browser UI in dark or light theme,
    so users can see what each theme looks like.
    """

    clicked = pyqtSignal()

    def __init__(self, theme_name: str, wizard_palette: dict, parent=None):
        super().__init__(parent)
        self._theme_name = theme_name
        self._selected = False
        self._wp = wizard_palette  # wizard's current palette for borders
        self._tp = Theme.DARK if theme_name == "dark" else Theme.LIGHT  # preview palette
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(280, 200)

        self._build()

    def _build(self):
        tp = self._tp
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Mini browser preview
        preview = QWidget()
        preview.setFixedSize(260, 140)
        preview.setStyleSheet(
            f"background: {tp['bg_primary']}; border-radius: 10px;"
            f" border: 1px solid {tp['border']};"
        )

        pv_lay = QVBoxLayout(preview)
        pv_lay.setContentsMargins(10, 8, 10, 8)
        pv_lay.setSpacing(5)

        # Fake toolbar
        toolbar = QWidget()
        toolbar.setFixedHeight(22)
        toolbar.setStyleSheet(
            f"background: {tp['bg_secondary']}; border-radius: 5px;"
        )
        tb_lay = QHBoxLayout(toolbar)
        tb_lay.setContentsMargins(6, 0, 6, 0)

        # Traffic lights
        for c in ["#FF5F57", "#FFBD2E", "#28C840"]:
            dot = QLabel()
            dot.setFixedSize(8, 8)
            dot.setStyleSheet(f"background: {c}; border-radius: 4px;")
            tb_lay.addWidget(dot)

        # Fake URL bar
        url = QLabel()
        url.setFixedHeight(14)
        url.setStyleSheet(
            f"background: {tp['bg_tertiary']}; border-radius: 4px;"
            " margin-left: 8px;"
        )
        tb_lay.addWidget(url, 1)

        pv_lay.addWidget(toolbar)

        # Fake content lines
        for w_pct in [80, 60, 90, 45]:
            line = QLabel()
            line.setFixedHeight(8)
            line.setFixedWidth(int(240 * w_pct / 100))
            line.setStyleSheet(
                f"background: {tp['bg_tertiary']}; border-radius: 3px;"
            )
            pv_lay.addWidget(line)

        pv_lay.addStretch()
        lay.addWidget(preview, alignment=Qt.AlignmentFlag.AlignCenter)

        lay.addSpacing(10)

        # Label
        name_text = "🌙 Escuro" if self._theme_name == "dark" else "☀️ Claro"
        lbl = QLabel(name_text)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(
            f"font-size: 14px; font-weight: 600; color: {self._tp['text_primary']};"
            " background: transparent;"
        )
        lay.addWidget(lbl)

        self._apply_style()

    def set_selected(self, val: bool):
        self._selected = val
        self._apply_style()

    def _apply_style(self):
        wp = self._wp
        if self._selected:
            self.setStyleSheet(
                f"_ThemePreviewCard {{ background: {wp['accent_subtle']};"
                f" border: 2px solid {wp['accent']};"
                f" border-radius: {wp['radius_xl']}; }}"
            )
        else:
            self.setStyleSheet(
                f"_ThemePreviewCard {{ background: transparent;"
                f" border: 1px solid {wp['border']};"
                f" border-radius: {wp['radius_xl']}; }}"
            )

    def mousePressEvent(self, ev):
        self.clicked.emit()
        super().mousePressEvent(ev)
