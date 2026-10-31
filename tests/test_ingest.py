"""Ingesta: lectura (md/txt/pdf), chunking con metadatos, upsert por lotes, idempotencia y errores."""
import shutil

import pytest

import config
import ingest
from errores import DimensionNoCoincideError, IndiceError, IngestaError
from tests.fakes import (
    EmbeddingsConFallas,
    EmbeddingsQueSeRompe,
    EmbeddingsSimulados,
    FakePinecone,
    contar_palabras,
    crear_pdf,
)

CFG = config.Configuracion(pinecone_api_key="x", index_name="idx", namespace="ns-test", google_api_key="y")

DOC_A = "# Politica A\n\n**Código:** GD-POL-001\n\n## 1. Objetivo\n\n" + " ".join(f"alfa{i}" for i in range(400)) + \
    "\n\n## 2. Alcance\n\n" + " ".join(f"beta{i}" for i in range(400))
DOC_B = "# Procedimiento B\n\n**Código:** GD-PRO-003\n\n## 1. Pasos\n\n" + " ".join(f"gamma{i}" for i in range(150))


@pytest.fixture
def datos(tmp_path):
    carpeta = tmp_path / "data"
    carpeta.mkdir()
    (carpeta / "01-politica-a.md").write_text(DOC_A, encoding="utf-8")
    (carpeta / "02-procedimiento-b.md").write_text(DOC_B, encoding="utf-8")
    return carpeta


def _ingestar(datos, pc, embeddings=None, **opciones):
    return ingest.ingestar(
        CFG, data_dir=datos, pc=pc, embeddings=embeddings or EmbeddingsSimulados(),
        contador=contar_palabras, dormir=lambda s: None, **opciones,
    )


@pytest.fixture
def pc():
    nube = FakePinecone()
    nube.agregar_indice("idx")
    return nube


# --------------------------------------------------------------------------- lectura
def test_codigo_y_categoria_salen_del_codigo_del_documento():
    assert ingest.derivar_codigo_y_categoria("Código: GD-POL-001") == ("GD-POL-001", "politica")
    assert ingest.derivar_codigo_y_categoria("GD-ROL-001") == ("GD-ROL-001", "roles")
    assert ingest.derivar_codigo_y_categoria("GD-PRO-003") == ("GD-PRO-003", "procedimiento")
    assert ingest.derivar_codigo_y_categoria("GD-GLO-001") == ("GD-GLO-001", "glosario")
    assert ingest.derivar_codigo_y_categoria("GD-XXX-001") == ("GD-XXX-001", "general")   # tipo desconocido
    assert ingest.derivar_codigo_y_categoria("sin codigo") == (config.CODIGO_SIN_DEFINIR, "general")


def test_markdown_se_trata_como_una_sola_pagina(datos):
    docs = ingest.cargar_documentos(datos)
    assert [d.documento_id for d in docs] == ["01-politica-a", "02-procedimiento-b"]   # nombre sin extension
    assert all(len(d.paginas) == 1 and d.paginas[0].numero == 1 for d in docs)
    assert docs[0].categoria == "politica" and docs[1].categoria == "procedimiento"


def test_un_pdf_conserva_el_numero_de_pagina_real(tmp_path):
    crear_pdf(tmp_path / "manual.pdf", ["Pagina uno GD-POL-009", "Pagina dos", "Pagina tres"])
    (doc,) = ingest.cargar_documentos(tmp_path)
    assert [p.numero for p in doc.paginas] == [1, 2, 3]
    assert "Pagina dos" in doc.paginas[1].texto
    assert (doc.codigo, doc.categoria) == ("GD-POL-009", "politica")


def test_las_paginas_en_blanco_de_un_pdf_se_omiten_sin_perder_la_numeracion(tmp_path):
    crear_pdf(tmp_path / "manual.pdf", ["Uno", "", "Tres"])
    (doc,) = ingest.cargar_documentos(tmp_path)
    assert [p.numero for p in doc.paginas] == [1, 3]


def test_un_pdf_sin_texto_da_un_error_claro(tmp_path):
    crear_pdf(tmp_path / "escaneado.pdf", ["", ""])
    with pytest.raises(IngestaError, match="texto extraible"):
        ingest.cargar_documentos(tmp_path)


def test_un_pdf_corrupto_da_un_error_claro(tmp_path):
    (tmp_path / "roto.pdf").write_bytes(b"esto no es un pdf")
    with pytest.raises(IngestaError, match="roto.pdf"):
        ingest.cargar_documentos(tmp_path)


def test_errores_de_carpeta_y_de_archivos(tmp_path):
    with pytest.raises(IngestaError, match="No existe"):
        ingest.cargar_documentos(tmp_path / "nada")
    with pytest.raises(IngestaError, match="No hay archivos"):
        ingest.cargar_documentos(tmp_path)
    (tmp_path / "vacio.md").write_text("   \n\n", encoding="utf-8")
    with pytest.raises(IngestaError, match="vacios"):
        ingest.cargar_documentos(tmp_path)
    (tmp_path / "latin.txt").write_bytes("canción".encode("latin-1"))
    with pytest.raises(IngestaError, match="UTF-8"):
        ingest.cargar_documentos(tmp_path)


def test_ignora_las_extensiones_que_no_son_documentos(datos):
    (datos / "notas.docx").write_bytes(b"x")
    (datos / "imagen.png").write_bytes(b"x")
    assert len(ingest.cargar_documentos(datos)) == 2


# --------------------------------------------------------------------------- chunking y metadatos
def test_cada_fragmento_respeta_el_tamano_maximo_en_tokens(datos):
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras, chunk_size=200, chunk_overlap=20)
    assert len(fragmentos) > 2
    assert all(f.metadata["tokens"] <= 200 for f in fragmentos)
    assert all(f.metadata["tokens"] == contar_palabras(f.page_content) for f in fragmentos)


def test_el_overlap_repite_el_final_de_un_fragmento_al_inicio_del_siguiente(tmp_path):
    (tmp_path / "largo.txt").write_text(" ".join(f"p{i}" for i in range(500)), encoding="utf-8")
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(tmp_path), contar_palabras, chunk_size=100, chunk_overlap=20)
    primero, segundo = fragmentos[0].page_content.split(), fragmentos[1].page_content.split()
    assert set(primero[-20:]) & set(segundo[:25])


def test_todos_los_fragmentos_tienen_el_mismo_esquema_de_metadatos(datos):
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras, chunk_size=200, chunk_overlap=20)
    for f in fragmentos:
        assert set(f.metadata) == set(ingest.ESQUEMA_METADATA)
        ingest.validar_metadata(f.metadata)   # tipos correctos


def test_los_metadatos_describen_la_fuente_la_pagina_y_la_categoria(datos):
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras, chunk_size=200, chunk_overlap=20)
    de_a = [f for f in fragmentos if f.metadata["documento_id"] == "01-politica-a"]
    assert {f.metadata["fuente"] for f in de_a} == {"01-politica-a.md"}
    assert {f.metadata["categoria"] for f in de_a} == {"politica"}
    assert {f.metadata["codigo"] for f in de_a} == {"GD-POL-001"}
    assert {f.metadata["pagina"] for f in de_a} == {1}
    assert [f.metadata["chunk_index"] for f in de_a] == list(range(len(de_a)))
    assert any("Objetivo" in f.metadata["seccion"] for f in de_a)   # cita la seccion del documento


def test_los_ids_son_unicos_deterministas_y_llevan_el_documento_como_prefijo(datos):
    docs = ingest.cargar_documentos(datos)
    primera = ingest.fragmentar(docs, contar_palabras, chunk_size=200, chunk_overlap=20)
    segunda = ingest.fragmentar(docs, contar_palabras, chunk_size=200, chunk_overlap=20)
    ids = [f.metadata["chunk_id"] for f in primera]
    assert ids == [f.metadata["chunk_id"] for f in segunda]      # mismo contenido => mismos IDs
    assert len(set(ids)) == len(ids)
    assert all(i.startswith(f.metadata["documento_id"] + "#") for i, f in zip(ids, primera))


def test_el_id_cambia_si_cambia_el_texto_el_documento_o_la_pagina():
    base = ingest.id_de_fragmento("doc", 1, "texto")
    assert base == ingest.id_de_fragmento("doc", 1, "texto")
    assert base != ingest.id_de_fragmento("doc", 1, "texto distinto")
    assert base != ingest.id_de_fragmento("otro", 1, "texto")
    assert base != ingest.id_de_fragmento("doc", 2, "texto")


def test_en_un_pdf_cada_fragmento_conoce_su_pagina(tmp_path):
    crear_pdf(tmp_path / "manual.pdf", ["Texto de la pagina uno", "Texto de la pagina dos"])
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(tmp_path), contar_palabras)
    assert [f.metadata["pagina"] for f in fragmentos] == [1, 2]
    assert all(f.metadata["seccion"] == "" for f in fragmentos)   # un PDF no tiene titulos Markdown


@pytest.mark.parametrize(
    "cambio",
    [{"extra": "x"}, {"pagina": "1"}, {"tokens": 1.5}, {"pagina": True}],
)
def test_validar_metadata_rechaza_campos_de_mas_o_con_tipo_equivocado(cambio, datos):
    metadata = dict(ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras)[0].metadata)
    metadata.update(cambio)
    with pytest.raises(IngestaError):
        ingest.validar_metadata(metadata)


def test_validar_metadata_rechaza_campos_faltantes(datos):
    metadata = dict(ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras)[0].metadata)
    del metadata["categoria"]
    with pytest.raises(IngestaError, match="categoria"):
        ingest.validar_metadata(metadata)


def test_el_overlap_debe_ser_menor_que_el_tamano():
    with pytest.raises(ValueError):
        ingest.crear_splitter(contar_palabras, chunk_size=100, chunk_overlap=100)


# --------------------------------------------------------------------------- ingesta a Pinecone
def test_primera_ingesta_sube_todo_con_el_texto_original_dentro_de_la_metadata(datos, pc):
    embeddings = EmbeddingsSimulados()
    reporte = _ingestar(datos, pc, embeddings, reset=False)
    index = pc.Index("idx")

    fragmentos = ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras)
    assert reporte.fragmentos == reporte.nuevos == len(fragmentos) == index.cantidad("ns-test")
    assert reporte.sin_cambios == reporte.eliminados == 0 and reporte.visible
    for f in fragmentos:
        guardado = index.namespaces["ns-test"][f.metadata["chunk_id"]]
        assert guardado["metadata"]["text"] == f.page_content            # texto original en la metadata
        assert guardado["metadata"]["fuente"] == f.metadata["fuente"]
        assert len(guardado["values"]) == config.EMBEDDING_DIMENSION


def test_todo_se_guarda_en_el_namespace_configurado(datos, pc):
    _ingestar(datos, pc)
    index = pc.Index("idx")
    assert set(index.namespaces) == {"ns-test"}
    assert {ns for ns, _ in index.llamadas_upsert} == {"ns-test"}


def test_el_upsert_va_por_lotes_y_no_vector_por_vector(datos, pc):
    index = pc.Index("idx")
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras)
    nuevos, eliminados, lotes = ingest.sincronizar(
        index, EmbeddingsSimulados(), fragmentos, "ns-test", tamano_lote_upsert=3, tamano_lote_embeddings=2
    )
    tamanos = [n for _, n in index.llamadas_upsert]
    assert sum(tamanos) == nuevos == len(fragmentos)
    assert max(tamanos) <= 3 and lotes == len(tamanos) == -(-len(fragmentos) // 3)


def test_los_embeddings_se_piden_de_a_pocos_textos(datos, pc):
    embeddings = EmbeddingsSimulados()
    index = pc.Index("idx")
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras)
    ingest.sincronizar(index, embeddings, fragmentos, "ns-test", tamano_lote_upsert=100, tamano_lote_embeddings=2)
    assert max(embeddings.lotes) <= 2 and sum(embeddings.lotes) == len(fragmentos)


def test_reingestar_lo_mismo_no_llama_a_embeddings_ni_sube_nada(datos, pc):
    _ingestar(datos, pc)
    index = pc.Index("idx")
    subidas_antes = len(index.llamadas_upsert)

    embeddings = EmbeddingsSimulados()
    reporte = _ingestar(datos, pc, embeddings)
    assert reporte.base_al_dia and reporte.nuevos == 0 and reporte.eliminados == 0
    assert reporte.sin_cambios == reporte.fragmentos
    assert embeddings.llamadas_documentos == 0 and len(index.llamadas_upsert) == subidas_antes


def test_si_un_documento_cambia_solo_se_reemplazan_sus_fragmentos(datos, pc):
    _ingestar(datos, pc)
    index = pc.Index("idx")
    de_b_antes = {i for i in index.namespaces["ns-test"] if i.startswith("02-procedimiento-b#")}

    (datos / "01-politica-a.md").write_text(DOC_A.replace("alfa0 ", "CAMBIADO "), encoding="utf-8")
    embeddings = EmbeddingsSimulados()
    reporte = _ingestar(datos, pc, embeddings)

    assert 0 < reporte.nuevos < reporte.fragmentos and reporte.eliminados >= 1
    assert {i for i in index.namespaces["ns-test"] if i.startswith("02-procedimiento-b#")} == de_b_antes
    assert index.cantidad("ns-test") == reporte.fragmentos
    assert embeddings.llamadas_documentos == reporte.nuevos     # lo que no cambio no se volvio a embeber


def test_si_se_borra_un_documento_sus_fragmentos_salen_del_namespace(datos, pc):
    _ingestar(datos, pc)
    (datos / "02-procedimiento-b.md").unlink()
    reporte = _ingestar(datos, pc)
    index = pc.Index("idx")
    assert reporte.eliminados >= 1 and reporte.nuevos == 0
    assert not any(i.startswith("02-procedimiento-b#") for i in index.namespaces["ns-test"])
    assert index.cantidad("ns-test") == reporte.fragmentos


def test_reset_vacia_el_namespace_y_lo_reconstruye(datos, pc):
    _ingestar(datos, pc)
    index = pc.Index("idx")
    embeddings = EmbeddingsSimulados()
    reporte = _ingestar(datos, pc, embeddings, reset=True)
    assert {"ids": [], "delete_all": True, "namespace": "ns-test"} in index.llamadas_delete
    assert reporte.nuevos == reporte.fragmentos == index.cantidad("ns-test")
    assert embeddings.llamadas_documentos == reporte.fragmentos


def test_reset_sobre_un_namespace_nuevo_no_falla(datos, pc):
    assert _ingestar(datos, pc, reset=True).nuevos > 0


def test_otros_namespaces_no_se_tocan(datos, pc):
    index = pc.Index("idx")
    index.upsert([{"id": "ajeno#1", "values": [1.0], "metadata": {"text": "x"}}], namespace="otro-cliente")
    _ingestar(datos, pc, reset=True)
    assert index.cantidad("otro-cliente") == 1


# --------------------------------------------------------------------------- errores y robustez
def test_dimension_equivocada_se_detecta_antes_de_subir_nada(datos, pc):
    with pytest.raises(DimensionNoCoincideError, match="768"):
        _ingestar(datos, pc, EmbeddingsSimulados(dimension=768))
    assert pc.Index("idx").cantidad("ns-test") == 0


def test_un_indice_con_otra_dimension_se_detecta_antes_de_llamar_a_embeddings(datos):
    nube = FakePinecone()
    nube.agregar_indice("idx", dimension=768)
    embeddings = EmbeddingsSimulados()
    with pytest.raises(DimensionNoCoincideError):
        _ingestar(datos, nube, embeddings)
    assert embeddings.llamadas_documentos == 0     # no se gasto cuota de embeddings


def test_si_el_indice_no_existe_indica_como_crearlo(datos):
    with pytest.raises(IndiceError, match="setup_index.py"):
        _ingestar(datos, FakePinecone())


def test_la_cuota_agotada_se_reintenta_y_la_ingesta_termina(datos, pc):
    embeddings = EmbeddingsConFallas(fallas=2)
    reporte = _ingestar(datos, pc, embeddings)
    assert reporte.nuevos == reporte.fragmentos > 0


def test_si_falla_a_mitad_lo_ya_subido_se_conserva_y_al_reintentar_se_continua(datos, pc, monkeypatch):
    index = pc.Index("idx")
    fragmentos = ingest.fragmentar(ingest.cargar_documentos(datos), contar_palabras)
    with pytest.raises(ValueError):
        ingest.sincronizar(
            index, EmbeddingsQueSeRompe(despues_de=2), fragmentos, "ns-test",
            tamano_lote_upsert=2, tamano_lote_embeddings=2, dormir=lambda s: None,
        )
    assert index.cantidad("ns-test") == 2        # el primer lote ya estaba guardado

    reporte = _ingestar(datos, pc)               # la siguiente corrida solo completa lo que falta
    assert reporte.sin_cambios == 2 and reporte.nuevos == reporte.fragmentos - 2
    assert index.cantidad("ns-test") == reporte.fragmentos


def test_el_reporte_marca_visible_false_si_pinecone_tarda_en_reflejar_los_cambios(datos, pc):
    pc.Index("idx").retraso_visibilidad = 10**6
    reporte = _ingestar(datos, pc, max_espera_visibilidad_s=0)
    assert reporte.visible is False


def test_el_reporte_resume_tokens_y_categorias(datos, pc):
    reporte = _ingestar(datos, pc)
    assert reporte.archivos == 2
    assert reporte.tokens_min <= reporte.tokens_promedio <= reporte.tokens_max
    assert reporte.por_categoria == {"politica": reporte.por_categoria["politica"], "procedimiento": reporte.por_categoria["procedimiento"]}
    assert sum(reporte.por_categoria.values()) == reporte.fragmentos
    assert (reporte.indice, reporte.namespace) == ("idx", "ns-test")


def test_un_fragmento_que_excede_el_limite_de_metadata_de_pinecone_se_rechaza():
    from tests.fakes import documento

    enorme = documento("palabra " * 20_000)
    with pytest.raises(IngestaError, match="limite de metadata"):
        ingest._registro(enorme, [0.0])


def test_el_contador_cae_a_una_aproximacion_si_tiktoken_no_carga(monkeypatch):
    import builtins

    real = builtins.__import__

    def sin_tiktoken(nombre, *a, **k):
        if nombre == "tiktoken":
            raise ImportError("sin red")
        return real(nombre, *a, **k)

    monkeypatch.setattr(builtins, "__import__", sin_tiktoken)
    contar, descripcion = ingest.crear_contador_de_tokens()
    assert "aproximado" in descripcion and contar("a" * 35) == 10


# --------------------------------------------------------------------------- CLI
def test_main_dry_run_no_necesita_claves_ni_red(datos, monkeypatch, capsys):
    for nombre in ("PINECONE_API_KEY", "INDEX_NAME", "GOOGLE_API_KEY"):
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr(ingest, "crear_contador_de_tokens", lambda: (contar_palabras, "palabras (test)"))

    assert ingest.main(["--dry-run", "--data", str(datos)]) == 0
    salida = capsys.readouterr().out
    assert "DRY RUN" in salida and "01-politica-a.md" in salida and "categoria 'politica'" in salida
    assert "chunk_id" in salida and "documento_id" in salida


def test_main_sin_variables_explica_que_falta(datos, monkeypatch, capsys):
    for nombre in ("PINECONE_API_KEY", "INDEX_NAME", "GOOGLE_API_KEY"):
        monkeypatch.delenv(nombre, raising=False)
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    assert ingest.main(["--data", str(datos)]) == 1
    assert "PINECONE_API_KEY" in capsys.readouterr().err


def test_main_ingesta_completa(datos, pc, monkeypatch, capsys):
    monkeypatch.setenv("PINECONE_API_KEY", "x")
    monkeypatch.setenv("INDEX_NAME", "idx")
    monkeypatch.setenv("GOOGLE_API_KEY", "y")
    monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr(ingest, "crear_cliente", lambda cfg: pc)
    monkeypatch.setattr(ingest, "crear_embeddings", lambda cfg: EmbeddingsSimulados())
    monkeypatch.setattr(ingest, "crear_contador_de_tokens", lambda: (contar_palabras, "palabras (test)"))

    assert ingest.main(["--data", str(datos)]) == 0
    primera = capsys.readouterr().out
    assert "namespace actualizado" in primera and "mercado-austral" in primera

    assert ingest.main(["--data", str(datos)]) == 0
    assert "ya estaba al dia" in capsys.readouterr().out


def test_el_dataset_real_se_fragmenta_en_el_rango_de_la_consigna():
    """Con los documentos reales del repo: ningun fragmento supera el tamano configurado."""
    docs = ingest.cargar_documentos(config.DATA_DIR)
    fragmentos = ingest.fragmentar(docs, contar_palabras, chunk_size=300, chunk_overlap=30)
    assert len(docs) >= 4 and len(fragmentos) > len(docs)
    assert all(f.metadata["tokens"] <= 300 for f in fragmentos)
