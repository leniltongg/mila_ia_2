// Script para configuração de interações específicas

// Configuração do Flatpickr para datas
document.addEventListener("DOMContentLoaded", function () {
    if (document.querySelector("#data_nascimento")) {
        flatpickr("#data_nascimento", {
            locale: "pt",
            dateFormat: "d/m/Y",
            maxDate: "today",
            allowInput: true,
            onReady: function (selectedDates, dateStr, instance) {
                instance.calendarContainer.classList.add("custom-calendar");
            },
            onChange: function (selectedDates) {
                console.log("Data selecionada:", selectedDates[0]);
            },
        });
    }
});

// Atualização dinâmica de tipos de ensino e séries
document.addEventListener("DOMContentLoaded", function () {
    const escolaSelect = document.getElementById("escola");
    const tipoEnsinoSelect = document.getElementById("tipo_ensino");
    const Ano_escolar_idSelect = document.getElementById("Ano_escolar_id");
    

    if (escolaSelect) {
        escolaSelect.addEventListener("change", function () {
            tipoEnsinoSelect.innerHTML = '<option value="">Selecione o tipo de ensino</option>';
            Ano_escolar_idSelect.innerHTML = '<option value="">Selecione o tipo de ensino primeiro</option>';
            tipoEnsinoSelect.disabled = true;
            Ano_escolar_idSelect.disabled = true;

            const selectedOption = this.options[this.selectedIndex];
            const tiposEnsino = selectedOption.getAttribute("data-tipo-ensino");

            if (tiposEnsino) {
                tiposEnsino.split(", ").forEach(tipo => {
                    const option = document.createElement("option");
                    option.value = tipo;
                    option.textContent = tipo;
                    tipoEnsinoSelect.appendChild(option);
                });
                tipoEnsinoSelect.disabled = false;
            }
        });
    }

    if (tipoEnsinoSelect) {
        tipoEnsinoSelect.addEventListener("change", function () {
            Ano_escolar_idSelect.innerHTML = '<option value="">Selecione a série</option>';
            Ano_escolar_idSelect.disabled = true;

            const Ano_escolar_idsMap = {
                "Ensino Infantil": ["Fase 1", "Fase 2"],
                "Fundamental I": ["1º Ano", "2º Ano", "3º Ano", "4º Ano", "5º Ano"],
                "Fundamental II": ["6º Ano", "7º Ano", "8º Ano", "9º Ano"],
                "Ensino Médio": ["1º Ano", "2º Ano", "3º Ano"]
            };

            const tipoEnsinoSelecionado = this.value;
            if (Ano_escolar_idsMap[tipoEnsinoSelecionado]) {
                Ano_escolar_idsMap[tipoEnsinoSelecionado].forEach(Ano_escolar_id => {
                    const option = document.createElement("option");
                    option.value = Ano_escolar_id;
                    option.textContent = Ano_escolar_id;
                    Ano_escolar_idSelect.appendChild(option);
                });
                Ano_escolar_idSelect.disabled = false;
            }
        });
    }
});

// Exibir mensagens de feedback com timeout
function showMessage(message, type) {
    const messageBox = document.createElement("div");
    messageBox.className = `message-box ${type}`;
    messageBox.textContent = message;

    document.body.appendChild(messageBox);

    setTimeout(() => {
        messageBox.remove();
    }, 3000);
}
