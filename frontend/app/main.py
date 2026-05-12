from flask import Flask, render_template, request, send_file, abort
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer
)
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from io import BytesIO
import os

app = Flask(__name__)

# URL del backend desde variable de entorno
BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/generar-pdf', methods=['POST'])
def generar_pdf():
    try:
        # Obtener ID de la factura desde el formulario
        id_factura = request.form['id_factura']

        # Consumir API backend
        response = requests.get(f'{BACKEND_URL}/facturas/v1/{id_factura}')
        
        if response.status_code != 200:
            abort(404, description="Factura no encontrada")
            
        factura = response.json()
        
         # Crear buffer en memoria
        buffer = BytesIO()

        # Crear documento PDF
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm
        )

        # Estilos
        styles = getSampleStyleSheet()

        # Lista de elementos del PDF
        elements = []

        # =========================================================
        # TÍTULO
        # =========================================================

        titulo = Paragraph(
            f"<b>FACTURA #{factura['numero_factura']}</b>",
            styles['Title']
        )

        fecha = Paragraph(
            f"Fecha de emisión: {factura['fecha_emision']}",
            styles['Normal']
        )

        elements.append(titulo)
        elements.append(Spacer(1, 10))
        elements.append(fecha)
        elements.append(Spacer(1, 20))

        # =========================================================
        # INFORMACIÓN EMPRESA
        # =========================================================

        empresa = factura['empresa']

        info_empresa = f"""
        <b>Empresa</b><br/>
        {empresa['nombre']}<br/>
        {empresa['direccion']}<br/>
        Tel: {empresa['telefono']}<br/>
        Email: {empresa['email']}
        """

        elements.append(Paragraph(info_empresa, styles['BodyText']))
        elements.append(Spacer(1, 15))

        # =========================================================
        # INFORMACIÓN CLIENTE
        # =========================================================

        cliente = factura['cliente']

        info_cliente = f"""
        <b>Cliente</b><br/>
        {cliente['nombre']}<br/>
        {cliente['direccion']}<br/>
        Tel: {cliente['telefono']}
        """

        elements.append(Paragraph(info_cliente, styles['BodyText']))
        elements.append(Spacer(1, 20))

        # =========================================================
        # TABLA DE DETALLE
        # =========================================================

        data = [
            [
                "Cantidad",
                "Descripción",
                "Precio Unitario",
                "Total"
            ]
        ]

        for item in factura['detalle']:
            data.append([
                item['cantidad'],
                item['descripcion'],
                f"${item['precio_unitario']}",
                f"${item['total']}"
            ])

        tabla = Table(
            data,
            colWidths=[30 * mm, 70 * mm, 40 * mm, 30 * mm]
        )

        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4CAF50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ]))

        elements.append(tabla)
        elements.append(Spacer(1, 20))

        # =========================================================
        # TOTALES
        # =========================================================

        subtotal = Paragraph(
            f"<b>Subtotal:</b> ${factura['subtotal']}",
            styles['Normal']
        )

        impuesto = Paragraph(
            f"<b>IVA (21%):</b> ${factura['impuesto']}",
            styles['Normal']
        )

        total = Paragraph(
            f"<b>Total:</b> ${factura['total']}",
            styles['Heading2']
        )

        elements.append(subtotal)
        elements.append(Spacer(1, 5))

        elements.append(impuesto)
        elements.append(Spacer(1, 5))

        elements.append(total)

        # =========================================================
        # GENERAR PDF
        # =========================================================

        doc.build(elements)

        # Reiniciar posición del buffer
        buffer.seek(0)

        # Retornar PDF descargable
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'factura_{id_factura}.pdf',
            mimetype='application/pdf'
        )

    except requests.exceptions.ConnectionError:
        abort(503, description="Error de conexión con el servidor")

    except Exception as e:
        abort(500, description=str(e))


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=3000,
        debug=True
    )
