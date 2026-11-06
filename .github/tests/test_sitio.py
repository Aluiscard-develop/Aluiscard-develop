"""Pruebas de un sitio estático (Normas/plantillas/github/test_sitio.py, solo biblioteca estándar).

Va en .github/tests/ del repo: así no se publica (upload-pages-artifact excluye .github).
Revisa cada .html y .md del sitio: que se pueda leer, que el HTML tenga lang y title, y que todo
enlace o recurso local (href, src, ![](…), [](…)) exista. Lo externo (https:, mailto:…) no se toca.
"""
import re
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

RAIZ = Path(__file__).resolve().parents[2]
IGNORAR = {".git", ".github", "node_modules"}
MD_ENLACE = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)")


def archivos(*sufijos):
    return sorted(p for p in RAIZ.rglob("*") if p.suffix in sufijos
                  and not IGNORAR.intersection(p.relative_to(RAIZ).parts))


def es_local(ref):
    partes = urlsplit(ref)
    return bool(ref) and not partes.scheme and not partes.netloc and not ref.startswith(("#", "{"))


def destino(origen, ref):
    ruta = unquote(urlsplit(ref).path)
    base = RAIZ if ruta.startswith("/") else origen.parent
    final = (base / ruta.lstrip("/")).resolve()
    return final / "index.html" if final.is_dir() else final


class Lector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.refs, self.lang, self.titulo = [], None, False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "title":
            self.titulo = True
        for clave in ("href", "src"):
            if a.get(clave) and es_local(a[clave]):
                self.refs.append(a[clave])


class Sitio(unittest.TestCase):
    def test_hay_algo_que_revisar(self):
        self.assertTrue(archivos(".html", ".md"), "no hay .html ni .md en el repo")

    def test_html_con_lang_y_title(self):
        for html in archivos(".html"):
            with self.subTest(html=str(html.relative_to(RAIZ))):
                lector = Lector()
                lector.feed(html.read_text(encoding="utf-8"))
                self.assertTrue(lector.lang, "falta <html lang=…>")
                self.assertTrue(lector.titulo, "falta <title>")

    def test_recursos_locales_existen(self):
        rotos = []
        for f in archivos(".html", ".md"):
            texto = f.read_text(encoding="utf-8")
            if f.suffix == ".html":
                lector = Lector()
                lector.feed(texto)
                refs = lector.refs
            else:
                refs = [r for r in MD_ENLACE.findall(re.sub(r"```.*?```", "", texto, flags=re.S))
                        if es_local(r)]
            rotos += [f"{f.relative_to(RAIZ)} → {r}" for r in refs if not destino(f, r).exists()]
        self.assertEqual(rotos, [], "recursos que no existen:\n" + "\n".join(rotos))


if __name__ == "__main__":
    unittest.main()
