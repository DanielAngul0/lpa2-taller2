from flask import Flask, render_template, request, send_file, abort, jsonify, session
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_RIGHT, TA_CENTER
from io import BytesIO
import os
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'factura-secret-key-2025-xK9mP')

BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')


# ──────────────────────────────────────────────────────────────
# PDF BUILDER (función reutilizable)
# ──────────────────────────────────────────────────────────────

def build_pdf(factura: dict) -> BytesIO:
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm
    )

    styles = getSampleStyleSheet()

    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=22,
        textColor=colors.HexColor('#1e3a5f'),
        spaceAfter=4,
    )
    style_subtitle = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6b7280'),
        spaceAfter=2,
    )
    style_section = ParagraphStyle(
        'Section',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#374151'),
        leading=14,
    )
    style_total = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=13,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor('#1e3a5f'),
    )
    style_right = ParagraphStyle(
        'Right',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT,
        textColor=colors.HexColor('#374151'),
    )

    elements = []

    # ── HEADER ────────────────────────────────────────────────
    header_data = [[
        Paragraph(f"<b>FACTURA</b>", style_title),
        Paragraph(
            f"<b>#{factura['numero_factura']}</b><br/>"
            f"<font color='#6b7280' size='9'>Fecha: {factura['fecha_emision']}</font>",
            style_right
        )
    ]]
    header_table = Table(header_data, colWidths=[85 * mm, 85 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, 0), 1.5, colors.HexColor('#2563eb')),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 16))

    # ── EMPRESA / CLIENTE ─────────────────────────────────────
    empresa = factura['empresa']
    cliente = factura['cliente']

    empresa_text = (
        f"<b><font color='#2563eb'>EMISOR</font></b><br/>"
        f"<b>{empresa['nombre']}</b><br/>"
        f"{empresa['direccion'].replace(chr(10), '<br/>')}<br/>"
        f"Tel: {empresa['telefono']}<br/>"
        f"Email: {empresa['email']}"
    )
    cliente_text = (
        f"<b><font color='#2563eb'>FACTURADO A</font></b><br/>"
        f"<b>{cliente['nombre']}</b><br/>"
        f"{cliente['direccion'].replace(chr(10), '<br/>')}<br/>"
        f"Tel: {cliente['telefono']}"
    )

    parties_data = [[
        Paragraph(empresa_text, style_section),
        Paragraph(cliente_text, style_section),
    ]]
    parties_table = Table(parties_data, colWidths=[85 * mm, 85 * mm])
    parties_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#f0f7ff')),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#f8fafc')),
        ('BOX', (0, 0), (0, 0), 0.5, colors.HexColor('#bfdbfe')),
        ('BOX', (1, 0), (1, 0), 0.5, colors.HexColor('#dbe3ef')),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ]))
    elements.append(parties_table)
    elements.append(Spacer(1, 20))

    # ── TABLA DETALLE ─────────────────────────────────────────
    header_row = [
        Paragraph('<b>Cant.</b>', ParagraphStyle('H', parent=styles['Normal'], fontSize=9, textColor=colors.white, fontName='Helvetica-Bold')),
        Paragraph('<b>Descripción</b>', ParagraphStyle('H', parent=styles['Normal'], fontSize=9, textColor=colors.white, fontName='Helvetica-Bold')),
        Paragraph('<b>Precio Unit.</b>', ParagraphStyle('H', parent=styles['Normal'], fontSize=9, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
        Paragraph('<b>Total</b>', ParagraphStyle('H', parent=styles['Normal'], fontSize=9, textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_RIGHT)),
    ]
    data = [header_row]

    style_cell = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#374151'))
    style_cell_right = ParagraphStyle('CellR', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#374151'), alignment=TA_RIGHT)

    for i, item in enumerate(factura['detalle']):
        row_bg = colors.HexColor('#f8fafc') if i % 2 == 0 else colors.white
        data.append([
            Paragraph(str(item['cantidad']), style_cell),
            Paragraph(item['descripcion'], style_cell),
            Paragraph(f"${item['precio_unitario']:,.2f}", style_cell_right),
            Paragraph(f"${item['total']:,.2f}", style_cell_right),
        ])

    tabla = Table(data, colWidths=[20 * mm, 80 * mm, 35 * mm, 35 * mm])

    row_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a5f')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#e5e7eb')),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    for i in range(1, len(data)):
        bg = colors.HexColor('#f0f4f8') if i % 2 == 1 else colors.white
        row_styles.append(('BACKGROUND', (0, i), (-1, i), bg))

    tabla.setStyle(TableStyle(row_styles))
    elements.append(tabla)
    elements.append(Spacer(1, 16))

    # ── TOTALES ───────────────────────────────────────────────
    totals_data = [
        ['', 'Subtotal:', f"${factura['subtotal']:,.2f}"],
        ['', 'IVA (21%):', f"${factura['impuesto']:,.2f}"],
        ['', 'TOTAL:', f"${factura['total']:,.2f}"],
    ]
    totals_table = Table(totals_data, colWidths=[100 * mm, 40 * mm, 30 * mm])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (1, 0), (-1, 1), 'Helvetica'),
        ('FONTNAME', (1, 2), (-1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 1), 9),
        ('FONTSIZE', (1, 2), (-1, 2), 12),
        ('TEXTCOLOR', (0, 0), (-1, 1), colors.HexColor('#6b7280')),
        ('TEXTCOLOR', (1, 2), (-1, 2), colors.HexColor('#1e3a5f')),
        ('LINEABOVE', (1, 2), (-1, 2), 1.5, colors.HexColor('#2563eb')),
        ('TOPPADDING', (0, 2), (-1, 2), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(totals_table)

    # ── FOOTER ────────────────────────────────────────────────
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor('#e5e7eb')))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "<font color='#9aa4b2' size='8'>Documento generado automáticamente · Sistema de Facturas Sintéticas</font>",
        ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer


# ──────────────────────────────────────────────────────────────
# HELPERS DE HISTORIAL EN SESIÓN
# ──────────────────────────────────────────────────────────────

def get_historial():
    return session.get('historial', [])


def save_to_historial(factura: dict) -> str:
    historial = get_historial()
    entry_id = str(uuid.uuid4())
    historial.insert(0, {
        'id': entry_id,
        'numero_factura': factura['numero_factura'],
        'fecha_emision': factura['fecha_emision'],
        'fecha_generacion': datetime.now().strftime('%d/%m/%Y %H:%M'),
        'total': factura['total'],
        'datos': factura,
    })
    # Mantener máximo 50 facturas en historial
    session['historial'] = historial[:50]
    session.modified = True
    return entry_id


def find_entry(entry_id: str):
    for entry in get_historial():
        if entry['id'] == entry_id:
            return entry
    return None


def delete_entry(entry_id: str) -> bool:
    historial = get_historial()
    new_historial = [e for e in historial if e['id'] != entry_id]
    if len(new_historial) == len(historial):
        return False
    session['historial'] = new_historial
    session.modified = True
    return True


# ──────────────────────────────────────────────────────────────
# RUTAS
# ──────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    try:
        id_factura = request.form['id_factura']
        response = requests.get(f'{BACKEND_URL}/facturas/v1/{id_factura}')

        if response.status_code != 200:
            abort(404, description="Factura no encontrada")

        factura = response.json()

        # Guardar en historial de sesión
        save_to_historial(factura)

        buffer = build_pdf(factura)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'factura_{id_factura}.pdf',
            mimetype='application/pdf'
        )

    except requests.exceptions.ConnectionError:
        abort(503, description="Error de conexión con el servidor backend")
    except Exception as e:
        abort(500, description=str(e))


# ── HISTORIAL API ─────────────────────────────────────────────

@app.route('/historial', methods=['GET'])
def historial_list():
    items = [
        {
            'id': e['id'],
            'numero_factura': e['numero_factura'],
            'fecha_emision': e['fecha_emision'],
            'fecha_generacion': e['fecha_generacion'],
            'total': e['total'],
        }
        for e in get_historial()
    ]
    return jsonify(items)


@app.route('/historial/<entry_id>', methods=['GET'])
def historial_detail(entry_id):
    entry = find_entry(entry_id)
    if not entry:
        return jsonify({'error': 'No encontrada'}), 404
    return jsonify(entry['datos'])


@app.route('/historial/<entry_id>/pdf', methods=['GET'])
def historial_pdf(entry_id):
    entry = find_entry(entry_id)
    if not entry:
        abort(404, description="Factura no encontrada en el historial")
    buffer = build_pdf(entry['datos'])
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"factura_{entry['numero_factura']}.pdf",
        mimetype='application/pdf'
    )


@app.route('/historial/<entry_id>', methods=['DELETE'])
def historial_delete(entry_id):
    if delete_entry(entry_id):
        return jsonify({'ok': True})
    return jsonify({'error': 'No encontrada'}), 404


@app.route('/historial/limpiar', methods=['POST'])
def historial_limpiar():
    session['historial'] = []
    session.modified = True
    return jsonify({'ok': True})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)