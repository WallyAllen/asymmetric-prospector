"""Pruebas de humo del núcleo: no necesitan navegador, red ni claves de IA."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from prospector.audit import rules  # noqa: E402
from prospector.audit.signals import ProbeResult  # noqa: E402
from prospector.compose.writer import FRASES_PROHIBIDAS, componer_por_plantilla, limpiar  # noqa: E402
from prospector.config import ComposeSettings  # noqa: E402
from prospector.models import Audit, EmailDraft, Lead, Metrics  # noqa: E402
from prospector.utils import (clean_emails, is_directory, lead_id, normalize_url,  # noqa: E402
                              registrable_domain)


class TestUtils(unittest.TestCase):
    def test_normalizacion(self):
        self.assertEqual(normalize_url("WWW.Ejemplo.com/inicio/?utm=x"), "https://ejemplo.com/inicio")
        self.assertEqual(normalize_url("ejemplo.com"), "https://ejemplo.com/")
        self.assertIsNone(normalize_url(""))

    def test_dominio_registrable(self):
        self.assertEqual(registrable_domain("https://blog.tienda.co.uk/x"), "tienda.co.uk")
        self.assertEqual(registrable_domain("https://www.clinica.es"), "clinica.es")

    def test_directorios_descartados(self):
        self.assertTrue(is_directory("https://www.cylex.es/valencia/abogado.html"))
        self.assertTrue(is_directory("https://lawzana.com/es/x"))
        self.assertFalse(is_directory("https://casesdedret.com/"))

    def test_limpieza_de_emails(self):
        crudos = ["INFO@Clinica.es", "logo@2x.png", "noreply@clinica.es", "juan@clinica.es"]
        limpios = clean_emails(crudos)
        self.assertEqual(limpios[0], "info@clinica.es")
        self.assertNotIn("logo@2x.png", limpios)
        self.assertNotIn("noreply@clinica.es", limpios)

    def test_id_estable(self):
        self.assertEqual(lead_id("https://www.clinica.es/x"), "clinica.es")
        sin_web = lead_id(None, "Clínica Sol", "a@b.com")
        self.assertTrue(sin_web.startswith("noweb-"))
        self.assertEqual(sin_web, lead_id(None, "Clínica Sol", "a@b.com"))


def _res(**metricas) -> ProbeResult:
    metricas.setdefault("https", True)
    res = ProbeResult(ok=True, metrics=Metrics(http_status=200, **metricas))
    res.desktop = {"rects": {"fold": {"x": 0, "y": 0, "width": 1440, "height": 900}}}
    return res


class TestReglas(unittest.TestCase):
    def test_web_sana_no_pasa_el_umbral(self):
        res = _res(
            tiene_viewport_meta=True, ctas_en_fold=3, tiene_formulario=True, tiene_tel=True,
            lcp_ms=1400, cls=0.02, peso_kb=900, favicon=True, og_image=True, h1=1,
            title="Clínica dental en Valencia | Sonrisa", meta_description="Implantes y ortodoncia",
            items_menu=5, palabras_en_fold=45, ano_copyright=2026,
            overflow_horizontal_mobile=False, texto_pequeno_mobile=0, tap_targets_pequenos=1,
        )
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertEqual(score, 0)  # ningún hallazgo: web sana de verdad
        self.assertEqual(veredicto, "sano")
        self.assertFalse(hallazgos)

    def test_landing_funcional_con_detalles_menores_no_es_critica(self):
        """El caso real que motivó este test: una landing con CTA, formulario y
        buen copy, pero un par de detalles de pulido (sin HTTPS, sin favicon,
        teléfono no pulsable) NO puede salir 'crítica'. Es una web que
        convierte; el score tiene que reflejar eso, no acumular puntos por
        cosas que no le cuestan un solo cliente al negocio."""
        res = _res(
            tiene_viewport_meta=True, ctas_en_fold=2, tiene_formulario=True, tiene_tel=False,
            tiene_whatsapp=False, https=False, lcp_ms=1800, cls=0.05, peso_kb=1200,
            favicon=False, og_image=True, h1=1,
            title="Abogados Cases de Dret · Mercantil Barcelona",
            meta_description="Despacho de derecho mercantil en Barcelona.",
            items_menu=4, palabras_en_fold=40, ano_copyright=2025,
            overflow_horizontal_mobile=False, texto_pequeno_mobile=0, tap_targets_pequenos=0,
        )
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertLess(score, 28, f"score {score} demasiado alto para una landing funcional")
        self.assertEqual(veredicto, "sano")
        self.assertFalse(any(h.categoria == "killer" for h in hallazgos))

    def test_web_horrible_puntua_alto(self):
        res = _res(
            tiene_viewport_meta=False, ctas_en_fold=0, tiene_formulario=False, tiene_tel=False,
            tiene_whatsapp=False, lcp_ms=6400, cls=0.42, peso_kb=5200, favicon=False,
            og_image=False, h1=0, title=None, meta_description=None, items_menu=14,
            palabras_en_fold=4, ano_copyright=2014, overflow_horizontal_mobile=True,
            ancho_scroll_mobile=1100, texto_pequeno_mobile=40, tap_targets_pequenos=20,
            popup_intrusivo=True,
        )
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertEqual(score, 100)
        self.assertEqual(veredicto, "critico")
        killers = [h for h in hallazgos if h.categoria == "killer"]
        self.assertGreaterEqual(len(killers), 2, "hacen falta al menos 2 killers para ser crítico")
        ids = {h.rule_id for h in hallazgos}
        for esperado in ("sin_viewport", "sin_cta_fold", "carga_lenta", "copyright_viejo"):
            self.assertIn(esperado, ids)

    def test_pila_de_hallazgos_cosmeticos_no_cruza_a_mejorable(self):
        """Favicon + SEO + menú largo + imágenes sin optimizar, todo junto,
        con el resto de la web sana: sigue siendo 'sano'. Ningún negocio
        recibe un correo solo por no tener favicon."""
        res = _res(
            tiene_viewport_meta=True, ctas_en_fold=2, tiene_formulario=True, tiene_tel=True,
            lcp_ms=1200, cls=0.01, peso_kb=800, favicon=False, og_image=False, h1=0,
            title="Web", meta_description=None, items_menu=12, palabras_en_fold=40,
            ano_copyright=2026, overflow_horizontal_mobile=False, texto_pequeno_mobile=0,
            tap_targets_pequenos=0,
        )
        res.desktop["imagenesSobredimensionadas"] = 5
        res.desktop["imagenes"] = 10
        res.desktop["imagenesSinAlt"] = 8
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertTrue(all(h.categoria == "cosmetico" for h in hallazgos))
        self.assertEqual(veredicto, "sano")

    def test_sitio_caido_es_inaccesible(self):
        res = ProbeResult(ok=False, error="Timeout", metrics=Metrics(error="Timeout"))
        score, veredicto, hallazgos = rules.evaluar(res)
        self.assertEqual(veredicto, "inaccesible")
        self.assertGreaterEqual(score, 90)
        self.assertTrue(any(h.rule_id == "sitio_inaccesible" for h in hallazgos))

    def test_sin_web_es_maxima_oportunidad(self):
        hallazgo = rules.finding_sin_web("Clínica Sol")
        self.assertEqual(hallazgo.peso, 100)
        self.assertEqual(hallazgo.categoria, "killer")
        self.assertIn("Clínica Sol", hallazgo.argumento)


class TestRedaccion(unittest.TestCase):
    def setUp(self):
        # Aislado de .env a propósito: los tests no pueden depender de la
        # config personal de quien los corre (p. ej. SENDER_PROOF real).
        self.cfg = ComposeSettings(sender_name="Felipe", sender_role="CRO",
                                    sender_site="", sender_proof="", max_findings_in_email=2)

    def _lead_auditado(self) -> Lead:
        res = _res(tiene_viewport_meta=False, ctas_en_fold=0, lcp_ms=5200)
        score, veredicto, hallazgos = rules.evaluar(res)
        lead = Lead(nombre="Clínica Sol", url="https://clinicasol.es", email="info@clinicasol.es",
                    nicho="clínicas dentales valencia")
        lead.audit = Audit(score=score, veredicto=veredicto, findings=hallazgos)
        return lead

    def test_plantilla_sin_marcadores_ni_slop(self):
        borrador = componer_por_plantilla(self._lead_auditado(), self.cfg)
        self.assertTrue(borrador.asunto)
        self.assertNotIn("[", borrador.cuerpo)
        self.assertNotIn("{", borrador.cuerpo)
        minuscula = borrador.cuerpo.lower()
        for frase in FRASES_PROHIBIDAS:
            self.assertNotIn(frase, minuscula)
        self.assertLess(len(borrador.cuerpo.split()), 170)

    def test_lead_sin_web_tiene_su_propio_angulo(self):
        lead = Lead(nombre="Bar Pepe", email="bar@pepe.es", nicho="bares madrid")
        lead.audit = Audit(score=100, veredicto="sin_web", findings=[rules.finding_sin_web("Bar Pepe")])
        borrador = componer_por_plantilla(lead, self.cfg)
        self.assertIn("Maps", borrador.cuerpo)

    def test_filtro_antislop(self):
        sucio = "Hola. Espero que este correo te encuentre bien. En el mundo actual, **todo** cambia."
        limpio = limpiar(sucio)
        self.assertNotIn("encuentre bien", limpio)
        self.assertNotIn("mundo actual", limpio)
        self.assertNotIn("**", limpio)


class TestModelos(unittest.TestCase):
    def test_ida_y_vuelta_json(self):
        lead = Lead(nombre="X", url="https://x.es", email="a@x.es")
        lead.audit = Audit(score=80, veredicto="critico",
                           findings=[rules.finding_sin_web("X")], metrics=Metrics(lcp_ms=3000))
        copia = Lead.from_dict(lead.to_dict())
        self.assertEqual(copia.id, lead.id)
        self.assertEqual(copia.audit.score, 80)
        self.assertEqual(copia.audit.findings[0].rule_id, "sin_web")
        self.assertEqual(copia.audit.metrics.lcp_ms, 3000)

    def test_fusion_conserva_trabajo_previo(self):
        from prospector.storage import merge_leads

        viejo = Lead(nombre="X", url="https://x.es", email="a@x.es")
        viejo.audit = Audit(score=90, veredicto="critico")
        viejo.estado = "auditado"
        nuevo = Lead(nombre="X", url="https://x.es", telefono="+34600000000")
        fusion = merge_leads([viejo], [nuevo])
        self.assertEqual(len(fusion), 1)
        self.assertEqual(fusion[0].audit.score, 90)
        self.assertEqual(fusion[0].telefono, "+34600000000")

    def test_fusion_no_pisa_auditoria_con_un_lado_vacio(self):
        """Reproduce el bug real: un archivo 'más adelante' en el embudo pero
        guardado con datos viejos no debe borrar la auditoría del otro lado,
        sea cual sea el orden en que se pasen existing/nuevos."""
        from prospector.storage import merge_leads

        compuesto_viejo = Lead(nombre="X", url="https://x.es", email="a@x.es")  # estado=crudo, sin audit
        auditado = Lead(nombre="X", url="https://x.es", email="a@x.es")
        auditado.audit = Audit(score=90, veredicto="critico")
        auditado.estado = "auditado"

        fusion = merge_leads([compuesto_viejo], [auditado])
        self.assertIsNotNone(fusion[0].audit)
        self.assertEqual(fusion[0].estado, "auditado")


if __name__ == "__main__":
    unittest.main(verbosity=2)


# ═══════════════ Redacción por fragmentos y canal WhatsApp ═══════════════
# Cada test de acá abajo corresponde a un defecto medido sobre los 563
# borradores reales, no a una hipótesis.

from prospector.compose.lexicon import busqueda_de, ciudad_de, elegir, rubro_de  # noqa: E402
from prospector.compose.whatsapp import componer_whatsapp  # noqa: E402
from prospector.compose.writer import validar  # noqa: E402
from prospector.models import EmailDraft  # noqa: E402
from prospector.storage import merge_leads  # noqa: E402


class TestLexico(unittest.TestCase):
    def test_rubro_y_ciudad_del_nicho(self):
        self.assertEqual(rubro_de("veterinarias La Plata").accion, "sacar un turno")
        self.assertEqual(rubro_de("Inmobiliarias zona norte Buenos Aires").accion,
                         "consultar por una propiedad")
        # Sin tildes, en minúsculas y con la ciudad compuesta: los tres casos
        # reales del corpus que `_termino_busqueda()` citaba crudos.
        self.assertEqual(ciudad_de("dentistas en mar del plata"), "Mar del Plata")
        self.assertEqual(ciudad_de("Odontologia estética La Plata"), "La Plata")
        self.assertIn("en Mar del Plata", busqueda_de("dentistas en mar del plata"))

    def test_nicho_desconocido_degrada_sin_romper(self):
        rubro = rubro_de("floristerías Ushuaia")
        self.assertTrue(rubro.accion)
        self.assertEqual(ciudad_de(""), "")

    def test_eleccion_estable_entre_procesos(self):
        # `hash()` de Python está aleatorizado por proceso: si se usara, el
        # mismo lead cambiaría de texto en cada corrida y no se podría
        # reproducir un mensaje ya enviado.
        opciones = ("a", "b", "c", "d")
        self.assertEqual(elegir(opciones, "lead-1", "saludo"),
                         elegir(opciones, "lead-1", "saludo"))
        distintas = {elegir(opciones, f"lead-{i}", "saludo") for i in range(40)}
        self.assertEqual(distintas, set(opciones))  # reparto sobre todas


class TestValidador(unittest.TestCase):
    def test_detecta_el_con_duplicado(self):
        # "(con 4,1 con 20 reseñas se nota…)" salía en 164 de 202 correos.
        malo = EmailDraft(asunto="algo de la web",
                          cuerpo="Hola. " + "palabra " * 50 + "con 4,1 con 20 reseñas en Maps.")
        self.assertIn("«con» duplicado", " ".join(validar(malo)))

    def test_reglas_de_asunto(self):
        largo = EmailDraft(
            asunto="Estudio jurídico EOT | Abogados Previsionales: la primera pantalla",
            cuerpo="palabra " * 60)
        problemas = " ".join(validar(largo))
        self.assertIn("asunto largo", problemas)
        self.assertIn("razón social cruda", problemas)
        self.assertIn("mayúsculas", problemas)

    def test_whatsapp_rechaza_enlace_ajeno_y_acepta_el_del_lead(self):
        con_linkedin = EmailDraft(
            cuerpo="Hola. " + "palabra " * 30 + "https://www.linkedin.com/in/x/")
        self.assertTrue(any("enlace ajeno" in p for p in
                            validar(con_linkedin, canal="whatsapp")))
        propio = EmailDraft(cuerpo="Hola. " + "palabra " * 30 + "entré a clinicasol.es.")
        self.assertEqual([], validar(propio, canal="whatsapp", dominio_propio="clinicasol.es"))

    def test_la_plantilla_tambien_se_valida(self):
        lead = Lead(nombre="Clínica Sol", url="https://clinicasol.es",
                    email="info@clinicasol.es", nicho="clínicas dentales valencia")
        res = _res(tiene_viewport_meta=False, ctas_en_fold=0, lcp_ms=5200)
        score, veredicto, hallazgos = rules.evaluar(res)
        lead.audit = Audit(score=score, veredicto=veredicto, findings=hallazgos)
        cfg = ComposeSettings(sender_name="Felipe", sender_role="CRO", sender_site="",
                              sender_proof="", max_findings_in_email=2)
        borrador = componer_por_plantilla(lead, cfg)
        self.assertEqual([], validar(borrador, canal="email", dominio_propio="clinicasol.es"))


class TestWhatsApp(unittest.TestCase):
    def setUp(self):
        self.cfg = ComposeSettings(
            sender_name="Felipe", sender_role="CRO · UNLP",
            sender_site="https://www.linkedin.com/in/felipe/",
            sender_phone="+54 9 221 314 1648", sender_proof="",
            sender_pitch="armo páginas web")

    def _lead_sin_web(self) -> Lead:
        lead = Lead(nombre="Clinica Arizu", telefono="02614764018",
                    nicho="Clínicas de fisioterapia Mendoza", rating=3.0, resenas=219)
        lead.audit = Audit(score=100, veredicto="sin_web",
                           findings=[rules.finding_sin_web("Clinica Arizu")])
        return lead

    def test_no_lleva_firma_ni_enlace_ni_asunto(self):
        """Los tres estaban en los 251 mensajes en cola. El enlace en el primer
        mensaje de un número desconocido es lo que cuesta el número."""
        borrador = componer_whatsapp(self._lead_sin_web(), self.cfg)
        self.assertEqual("", borrador.asunto)
        self.assertNotIn("linkedin", borrador.cuerpo.lower())
        self.assertNotIn("221 314 1648", borrador.cuerpo)
        self.assertNotIn("UNLP", borrador.cuerpo)

    def test_entra_en_la_pantalla_de_un_celular(self):
        borrador = componer_whatsapp(self._lead_sin_web(), self.cfg)
        self.assertLessEqual(len(borrador.cuerpo.split()), 95)
        self.assertLess(len(borrador.cuerpo), 600)   # la mediana anterior era 704
        self.assertEqual([], validar(borrador, canal="whatsapp"))

    def test_usa_el_vocabulario_del_rubro(self):
        borrador = componer_whatsapp(self._lead_sin_web(), self.cfg)
        self.assertIn("turno", borrador.cuerpo)          # fisioterapia, no "reservar"
        self.assertIn("Mendoza", borrador.cuerpo)

    def test_mismo_lead_mismo_texto(self):
        lead = self._lead_sin_web()
        self.assertEqual(componer_whatsapp(lead, self.cfg).cuerpo,
                         componer_whatsapp(lead, self.cfg).cuerpo)

    def test_dos_leads_del_mismo_rubro_no_reciben_el_mismo_texto(self):
        a, b = self._lead_sin_web(), self._lead_sin_web()
        b.id, b.nombre = "otro-negocio-distinto", "Clinica Santa Clara"
        self.assertNotEqual(componer_whatsapp(a, self.cfg).cuerpo,
                            componer_whatsapp(b, self.cfg).cuerpo)


class TestColaWhatsApp(unittest.TestCase):
    def test_listo_whatsapp_no_retrocede_al_fusionar(self):
        """El bug que sacó 86 leads de score 96 de la cola sin un solo log:
        `_PROGRESO` no tenía la clave y `.get(estado, 0)` la valoraba en 0,
        así que cada `compose` los devolvía a `auditado`."""
        listo = Lead(id="x", nombre="X", telefono="221", estado="listo_whatsapp")
        listo.email_draft = EmailDraft(cuerpo="hola")
        auditado = Lead(id="x", nombre="X", telefono="221", estado="auditado")
        fusionados = merge_leads([listo], [auditado])
        self.assertEqual("listo_whatsapp", fusionados[0].estado)


# ═══════════════ Teléfonos: a quién se le abre el chat ═══════════════

from prospector.telefono import de_enlace_whatsapp, normalizar, para_whatsapp  # noqa: E402
from prospector.deliver.whatsapp import cola_pendiente as cola_whatsapp  # noqa: E402


class TestTelefono(unittest.TestCase):
    def test_un_fijo_nunca_se_convierte_en_celular(self):
        """El bug que mandó 33 de los primeros 56 mensajes a otro número.

        `0221 421-9413` es una línea. El celular de ese negocio es otro número
        que no está en ningún dato del sistema. Ponerle un 9 adelante no lo
        deduce: inventa el celular de un tercero.
        """
        fijo = normalizar("02214219413")
        self.assertEqual("542214219413", fijo.e164)   # sin 9
        self.assertEqual("fijo", fijo.tipo)
        self.assertNotIn("5492214219413", fijo.e164)
        fijo_con_15_en_los_digitos = normalizar("02215900000")
        self.assertEqual("542215900000", fijo_con_15_en_los_digitos.e164)
        self.assertEqual("fijo", fijo_con_15_en_los_digitos.tipo)

    def test_un_movil_pierde_el_15_y_gana_el_9(self):
        for crudo in ("0221 15-421-9413", "+54 9 221 421 9413", "5492214219413"):
            with self.subTest(crudo=crudo):
                movil = normalizar(crudo)
                self.assertEqual("5492214219413", movil.e164)
                self.assertEqual("movil", movil.tipo)

    def test_un_numero_extranjero_no_se_argentiniza(self):
        # El corpus real trae un veterinario de Barcelona: +34 932 460 805.
        espanol = normalizar("+34932460805")
        self.assertEqual("34932460805", espanol.e164)
        self.assertEqual("internacional", espanol.tipo)

    def test_basura_se_descarta_en_vez_de_adivinarse(self):
        # '236790221479511' aparece 24 veces en los datos reales: dos números
        # pegados por el minado. Abrir el chat equivocado es peor que saltear.
        for basura in ("236790221479511", "123", "", None):
            self.assertFalse(normalizar(basura))

    def test_el_wame_de_su_web_gana_sobre_el_fijo_de_maps(self):
        lead = Lead(nombre="X", url="https://x.com.ar", telefono="02214219413")
        lead.audit = Audit(score=80, veredicto="critico",
                           metrics=Metrics(whatsapp_web="5492214440000"))
        elegido = para_whatsapp(lead)
        self.assertEqual("5492214440000", elegido.e164)
        self.assertTrue(elegido.verificado)
        self.assertEqual(3, elegido.confianza)      # ordena primero en la cola

    def test_whatsapp_verificado_manual_gana_y_sobrevive_fusion(self):
        lead = Lead(nombre="Ejemplo", telefono="02215900000",
                    whatsapp_verificado="https://wa.me/5492216000000",
                    whatsapp_fuente="https://ejemplo.com/contacto")
        auditado = Lead(id=lead.id, nombre="Ejemplo", estado="auditado")
        fusionado = merge_leads([lead], [auditado])[0]
        elegido = para_whatsapp(fusionado)
        self.assertEqual("5492216000000", elegido.e164)
        self.assertTrue(elegido.verificado)
        self.assertEqual("https://ejemplo.com/contacto", fusionado.whatsapp_fuente)

    def test_numero_sin_whatsapp_no_vuelve_a_la_cola_tras_fusion(self):
        fallido = Lead(nombre="Ejemplo", estado="sin_whatsapp")
        auditado = Lead(id=fallido.id, nombre="Ejemplo", estado="auditado")
        self.assertEqual("sin_whatsapp", merge_leads([fallido], [auditado])[0].estado)

    def test_web_en_revision_no_vuelve_a_la_cola_tras_fusion(self):
        pendiente = Lead(nombre="Ejemplo", estado="revisar_web")
        auditado = Lead(id=pendiente.id, nombre="Ejemplo", estado="auditado")
        self.assertEqual("revisar_web", merge_leads([pendiente], [auditado])[0].estado)

    def test_cola_whatsapp_exige_numero_publicado(self):
        comprobado = Lead(nombre="Con WhatsApp", estado="listo_whatsapp",
                          whatsapp_verificado="https://wa.me/5492216000000",
                          email_draft=EmailDraft(cuerpo="Hola"))
        supuesto = Lead(nombre="Solo celular", estado="listo_whatsapp",
                        telefono="0221 15-421-9413",
                        email_draft=EmailDraft(cuerpo="Hola"))
        self.assertEqual([comprobado], cola_whatsapp([comprobado, supuesto]))
        self.assertEqual(2, len(cola_whatsapp([comprobado, supuesto],
                                              permitir_no_verificados=True)))

    def test_sin_nada_mejor_se_usa_el_fijo_pero_marcado(self):
        lead = Lead(nombre="X", url="https://x.com.ar", telefono="02214219413")
        lead.audit = Audit(score=80, veredicto="critico", metrics=Metrics())
        elegido = para_whatsapp(lead)
        self.assertEqual("fijo", elegido.tipo)
        self.assertEqual(1, elegido.confianza)      # va al final de la cola
        self.assertIn("puede no tener WhatsApp", elegido.etiqueta)

    def test_extrae_el_numero_de_los_dos_formatos_de_enlace(self):
        self.assertEqual("5492214219413",
                         de_enlace_whatsapp("https://wa.me/5492214219413").e164)
        self.assertEqual("542214219413",
                         de_enlace_whatsapp(
                             "https://api.whatsapp.com/send?phone=542214219413&text=hola").e164)
        self.assertFalse(de_enlace_whatsapp("https://wa.me/"))


class TestRespuestas(unittest.TestCase):
    def test_un_lead_que_respondio_nunca_vuelve_a_la_cola(self):
        """La prueba que no puede fallar nunca (PLAN_OUTREACH_V3, §6).

        `respondido` tiene que ganarle a cualquier estado al fusionar: si un
        `compose` lo devuelve a 'auditado', vuelve a la cola y recibe el
        segundo toque alguien que ya te contestó.
        """
        respondio = Lead(id="x", nombre="X", email="a@x.com", estado="respondido")
        for intruso in ("crudo", "auditado", "listo", "listo_whatsapp", "enviado"):
            with self.subTest(intruso=intruso):
                fusionado = merge_leads([respondio], [Lead(id="x", nombre="X", estado=intruso)])
                self.assertEqual("respondido", fusionado[0].estado)


class TestSitioNoAccesible(unittest.TestCase):
    """Separar «tu web está caída» de «no la pude medir».

    Medido sobre la tanda real: de 36 sitios marcados «inaccesible», 17 tenían
    el dominio perfectamente vivo. A esos 17 el sistema les escribía «intenté
    entrar y no cargó», y el dueño lo desmiente abriendo su propia web.
    """

    def _caido(self, dns_ok):
        from prospector.audit.signals import ProbeResult
        res = ProbeResult(ok=False, error="Error: net::ERR_NAME_NOT_RESOLVED", dns_ok=dns_ok)
        return rules.evaluar(res)

    def test_dominio_que_no_existe_es_un_hallazgo_real(self):
        score, veredicto, hallazgos = self._caido(dns_ok=False)
        self.assertEqual("inaccesible", veredicto)
        self.assertEqual(95, score)
        self.assertIn("sitio_inaccesible", [h.rule_id for h in hallazgos])

    def test_dominio_vivo_que_no_cargo_no_se_declara_caido(self):
        score, veredicto, hallazgos = self._caido(dns_ok=True)
        self.assertEqual("no_medido", veredicto)
        self.assertEqual(0, score)          # lo descarta el umbral, no se contacta
        self.assertNotIn("sitio_inaccesible", [h.rule_id for h in hallazgos])
