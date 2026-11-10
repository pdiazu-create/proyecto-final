"""Exportación local de borradores a Office Open XML."""
from io import BytesIO
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
PML = 'http://schemas.openxmlformats.org/presentationml/2006/main'
DML = 'http://schemas.openxmlformats.org/drawingml/2006/main'
WML = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
TIPO = 'application/vnd.openxmlformats-officedocument.'


def texto_xml(texto):
    valido = (c for c in texto if c in '\t\n\r' or
              32 <= ord(c) <= 0xD7FF or 0xE000 <= ord(c) <= 0xFFFD or ord(c) >= 0x10000)
    return escape(''.join(valido))


def relaciones(*entradas):
    items = ''.join(f'<Relationship Id="rId{i}" Type="{REL}/{tipo}" Target="{ruta}"/>'
                    for i, (tipo, ruta) in enumerate(entradas, 1))
    return f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{items}</Relationships>'


def empaquetar(archivos, principal, tipos):
    tipos_xml = ''.join(f'<Override PartName="/{ruta}" ContentType="{TIPO}{tipo}+xml"/>'
                        for ruta, tipo in tipos.items())
    archivos['[Content_Types].xml'] = (
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>' + tipos_xml + '</Types>')
    archivos['_rels/.rels'] = relaciones(('officeDocument', principal))
    salida = BytesIO()
    with ZipFile(salida, 'w', ZIP_DEFLATED) as paquete:
        for ruta, xml in archivos.items():
            paquete.writestr(ruta, '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>' + xml)
    return salida.getvalue()


def documento(titulo, secciones):
    def parrafo(texto, estilo):
        return (f'<w:p><w:pPr><w:pStyle w:val="{estilo}"/></w:pPr><w:r>'
                f'<w:t xml:space="preserve">{texto_xml(texto)}</w:t></w:r></w:p>')

    cuerpo = parrafo('GRACE  /  MATERIAL ACADÉMICO', 'Marca') + parrafo(titulo, 'Title')
    for indice, seccion in enumerate(secciones, 1):
        cuerpo += parrafo(f'{indice:02d}   {seccion["titulo"]}', 'Heading1')
        cuerpo += ''.join(parrafo(linea, 'Contenido') for linea in seccion['puntos'])
    ruta = 'word/document.xml'
    fuente = '<w:rFonts w:ascii="Arial" w:hAnsi="Arial"/><w:lang w:val="es-NI"/>'
    estilos = (f'<w:styles xmlns:w="{WML}"><w:docDefaults><w:rPrDefault>'
               f'<w:rPr>{fuente}</w:rPr></w:rPrDefault></w:docDefaults>')
    for estilo, nombre, tamano, color, espacios, negrita in (
        ('Marca', 'Marca Grace', 20, '08676A', '<w:keepNext/><w:spacing w:after="160"/>', True),
        ('Title', 'Title', 52, '102C49', '<w:keepNext/><w:spacing w:after="360"/>', True),
        ('Heading1', 'heading 1', 30, '08676A',
         '<w:keepNext/><w:spacing w:before="300" w:after="130"/><w:outlineLvl w:val="0"/>', True),
        ('Contenido', 'Contenido', 24, '213D55', '<w:spacing w:after="130" w:line="300" w:lineRule="auto"/>', False),
    ):
        peso = '<w:b/>' if negrita else ''
        estilos += (f'<w:style w:type="paragraph" w:styleId="{estilo}"><w:name w:val="{nombre}"/>'
                    f'<w:pPr>{espacios}</w:pPr><w:rPr>{peso}<w:color w:val="{color}"/>'
                    f'<w:sz w:val="{tamano}"/></w:rPr></w:style>')
    estilos += '</w:styles>'
    pagina = ('<w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
              '<w:pgMar w:top="1100" w:right="1260" w:bottom="1100" w:left="1260"'
              ' w:header="500" w:footer="500" w:gutter="0"/></w:sectPr>')
    archivos = {ruta: f'<w:document xmlns:w="{WML}"><w:body>{cuerpo}{pagina}</w:body></w:document>',
                'word/styles.xml': estilos,
                'word/_rels/document.xml.rels': relaciones(('styles', 'styles.xml'))}
    return empaquetar(archivos, ruta, {ruta: 'wordprocessingml.document.main',
                                      'word/styles.xml': 'wordprocessingml.styles'})


def _caja(numero, texto, x, y, ancho, alto, tamano, color, fondo=None, negrita=False):
    relleno = f'<a:solidFill><a:srgbClr val="{fondo}"/></a:solidFill>' if fondo else '<a:noFill/>'
    margen = 155000 if fondo else 0
    peso = int(negrita)
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{numero}" name="Bloque {numero}"/><p:cNvSpPr txBox="1"/>'
            '<p:nvPr/></p:nvSpPr><p:spPr><a:xfrm>'
            f'<a:off x="{x}" y="{y}"/><a:ext cx="{ancho}" cy="{alto}"/>'
            f'</a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{relleno}'
            '<a:ln><a:noFill/></a:ln></p:spPr>'
            f'<p:txBody><a:bodyPr wrap="square" anchor="ctr" lIns="{margen}" rIns="{margen}">'
            '<a:normAutofit/></a:bodyPr><a:lstStyle/><a:p><a:r>'
            f'<a:rPr lang="es-NI" sz="{tamano}" b="{peso}"><a:solidFill><a:srgbClr val="{color}"/>'
            f'</a:solidFill></a:rPr><a:t>{texto_xml(texto)}</a:t></a:r></a:p></p:txBody></p:sp>')


def _componer_diapositiva(indice, seccion, total):
    portada = indice == 1
    fondo = '102C49' if portada else 'F3F8FD'
    cajas = _caja(2, 'GRACE  /  MATERIAL DE CLASE', 750000, 430000, 10300000, 420000,
                  1500, '8FE3D8' if portada else '08676A', negrita=True)
    if portada:
        cajas += _caja(3, seccion['titulo'], 750000, 1500000, 10500000, 2750000, 4500, 'FFFFFF', negrita=True)
        cajas += _caja(4, f'{total - 1} secciones de estudio', 750000, 4570000, 10500000, 650000, 2100, 'ACD6F0')
    else:
        cajas += _caja(3, seccion['titulo'], 750000, 950000, 10500000, 950000, 3300, '102C49', negrita=True)
        puntos = seccion['puntos']
        alto = min(1240000, 4050000 // max(1, len(puntos)))
        if seccion['titulo'].casefold().startswith('diagrama:') and 2 <= len(puntos) <= 4:
            separacion = 450000
            ancho = (10500000 - separacion * (len(puntos) - 1)) // len(puntos)
            for orden, punto in enumerate(puntos):
                x = 750000 + orden * (ancho + separacion)
                cajas += _caja(10 + orden * 2, punto, x, 2750000, ancho, 1500000,
                               1900, '102C49', 'D9F0EE', True)
                if orden + 1 < len(puntos):
                    cajas += _caja(11 + orden * 2, '→', x + ancho, 2750000, separacion, 1500000,
                                   2400, '08676A', negrita=True)
        else:
            for orden, punto in enumerate(puntos, 1):
                y = 2070000 + (orden - 1) * alto
                cajas += _caja(4 + orden * 2, f'{orden:02d}', 750000, y, 750000, alto - 100000,
                               1800, '08676A', 'D9F0EE', True)
                cajas += _caja(5 + orden * 2, punto, 1610000, y, 9680000, alto - 100000,
                               2200, '213D55', 'FFFFFF')
    cajas += _caja(4 if not portada else 5, f'{indice:02d} / {total:02d}', 750000, 6380000, 10500000,
                   310000, 1300, 'ACD6F0' if portada else '405F79')
    fondo_xml = (f'<p:bg><p:bgPr><a:solidFill><a:srgbClr val="{fondo}"/>'
                 '</a:solidFill><a:effectLst/></p:bgPr></p:bg>')
    return fondo_xml, cajas


def presentacion(titulo, secciones):
    ns = f'xmlns:p="{PML}" xmlns:a="{DML}" xmlns:r="{REL}"'
    base = ('<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr/>')
    ruta = 'ppt/presentation.xml'
    maestro = 'ppt/slideMasters/slideMaster1.xml'
    plano = 'ppt/slideLayouts/slideLayout1.xml'
    tema = 'ppt/theme/theme1.xml'
    tipos = {ruta: 'presentationml.presentation.main', maestro: 'presentationml.slideMaster',
             plano: 'presentationml.slideLayout', tema: 'theme'}
    mapa = ('<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2"'
            ' accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>')
    archivos = {
        maestro: f'<p:sldMaster {ns}><p:cSld><p:spTree>{base}</p:spTree></p:cSld>{mapa}'
                 '<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst></p:sldMaster>',
        plano: f'<p:sldLayout {ns} type="blank"><p:cSld><p:spTree>{base}</p:spTree></p:cSld>'
               '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sldLayout>',
        'ppt/slideMasters/_rels/slideMaster1.xml.rels': relaciones(
            ('slideLayout', '../slideLayouts/slideLayout1.xml'), ('theme', '../theme/theme1.xml')),
        'ppt/slideLayouts/_rels/slideLayout1.xml.rels': relaciones(('slideMaster', '../slideMasters/slideMaster1.xml')),
        tema: _tema(),
    }
    diapositivas = [{'titulo': titulo, 'puntos': ['Material de clase']}, *secciones]
    entradas = [('slideMaster', 'slideMasters/slideMaster1.xml')]
    ids = []
    for i, seccion in enumerate(diapositivas, 1):
        archivo = f'ppt/slides/slide{i}.xml'
        tipos[archivo] = 'presentationml.slide'
        entradas.append(('slide', f'slides/slide{i}.xml'))
        ids.append(f'<p:sldId id="{255+i}" r:id="rId{i+1}"/>')
        fondo, cajas = _componer_diapositiva(i, seccion, len(diapositivas))
        archivos[archivo] = (f'<p:sld {ns}><p:cSld>{fondo}<p:spTree>{base}{cajas}</p:spTree></p:cSld>'
                             '<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>')
        archivos[f'ppt/slides/_rels/slide{i}.xml.rels'] = relaciones(('slideLayout', '../slideLayouts/slideLayout1.xml'))
    archivos[ruta] = (f'<p:presentation {ns}><p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/>'
                      '</p:sldMasterIdLst><p:sldIdLst>' + ''.join(ids) + '</p:sldIdLst>'
                      '<p:sldSz cx="12192000" cy="6858000"/><p:notesSz cx="6858000" cy="9144000"/></p:presentation>')
    archivos['ppt/_rels/presentation.xml.rels'] = relaciones(*entradas)
    return empaquetar(archivos, ruta, tipos)


def _tema():
    colores = dict(zip(('dk1', 'lt1', 'dk2', 'lt2', 'accent1', 'accent2', 'accent3', 'accent4',
                        'accent5', 'accent6', 'hlink', 'folHlink'),
                       ('123455', 'FFFFFF', '234569', 'EAF6FD', '12656B', '0B5FD3', 'D67662',
                        '307584', '42658C', '487264', '0B5FD3', '544887')))
    paleta = ''.join(f'<a:{k}><a:srgbClr val="{v}"/></a:{k}>' for k, v in colores.items())
    familia = '<a:latin typeface="Arial"/><a:ea typeface=""/><a:cs typeface=""/>'
    relleno = '<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>'
    linea = '<a:ln w="9525">' + relleno + '<a:prstDash val="solid"/></a:ln>'
    return (f'<a:theme xmlns:a="{DML}" name="Grace"><a:themeElements><a:clrScheme name="Celeste">'
            f'{paleta}</a:clrScheme><a:fontScheme name="Arial"><a:majorFont>{familia}</a:majorFont>'
            f'<a:minorFont>{familia}</a:minorFont></a:fontScheme><a:fmtScheme name="Grace">'
            f'<a:fillStyleLst>{relleno*3}</a:fillStyleLst><a:lnStyleLst>{linea*3}</a:lnStyleLst>'
            f'<a:effectStyleLst>{"<a:effectStyle><a:effectLst/></a:effectStyle>"*3}</a:effectStyleLst>'
            f'<a:bgFillStyleLst>{relleno*3}</a:bgFillStyleLst></a:fmtScheme></a:themeElements></a:theme>')
