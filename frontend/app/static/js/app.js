document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("invoice-form");
    const input = document.getElementById("id_factura");
    const button = document.getElementById("submit-btn");
    const status = document.getElementById("status-message");

    const originalButtonText = button.textContent;

    const showStatus = (message, type = "") => {
        status.textContent = message;
        status.className = "status";
        if (type) {
            status.classList.add(type);
        }
    };

    const resetButton = () => {
        button.disabled = false;
        button.textContent = originalButtonText;
    };

    input.addEventListener("input", () => {
        input.value = input.value.toUpperCase().trimStart();
        status.textContent = "";
        status.className = "status";
    });

    form.addEventListener("submit", async (event) => {
        event.preventDefault();

        const value = input.value.trim();

        if (!value) {
            showStatus("Debes ingresar un número de factura.", "is-error");
            input.focus();
            return;
        }

        if (value.length < 3) {
            showStatus("El identificador debe tener al menos 3 caracteres.", "is-error");
            input.focus();
            return;
        }

        button.disabled = true;
        button.textContent = "Generando PDF...";
        showStatus("Consultando el backend y generando el documento...", "is-success");

        try {
            const formData = new FormData(form);

            const response = await fetch("/generar-pdf", {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                let errorMessage = "Ocurrió un error al generar la factura.";

                try {
                    const errorText = await response.text();
                    if (errorText) {
                        errorMessage = errorText;
                    }
                } catch (error) {
                    // Se mantiene el mensaje por defecto
                }

                throw new Error(errorMessage);
            }

            const blob = await response.blob();
            const pdfUrl = window.URL.createObjectURL(blob);
            const link = document.createElement("a");

            link.href = pdfUrl;
            link.download = `factura_${value}.pdf`;
            document.body.appendChild(link);
            link.click();
            link.remove();

            window.URL.revokeObjectURL(pdfUrl);

            showStatus("PDF generado correctamente.", "is-success");
        } catch (error) {
            console.error(error);
            showStatus(error.message || "No se pudo generar el PDF.", "is-error");
        } finally {
            resetButton();
        }
    });
});