const filaBody = document.getElementById("fila-body");
const formCliente = document.getElementById("form-cliente");
const btnChamar = document.getElementById("btn-chamar");

const totalAguardando = document.getElementById("total-aguardando");
const totalAtendimento = document.getElementById("total-atendimento");
const totalConcluidos = document.getElementById("total-concluidos");
const totalCancelados = document.getElementById("total-cancelados");

const clienteAtual = document.getElementById("cliente-atual");
const toast = document.getElementById("toast");
const statusAtualizacao = document.getElementById("status-atualizacao");


function mostrarToast(mensagem) {

    if (!toast) {
        return;
    }

    toast.textContent = mensagem;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
    }, 3000);
}


async function carregarFila() {

    if (!filaBody) {
        return;
    }

    try {

        const response = await fetch("/api/fila");

        if (!response.ok) {
            throw new Error("Erro ao carregar fila.");
        }

        const fila = await response.json();

        renderizarFila(fila);

        if (statusAtualizacao) {
            statusAtualizacao.textContent = "● Atualizado agora";
            statusAtualizacao.className = "online";
        }

    } catch (error) {

        if (statusAtualizacao) {
            statusAtualizacao.textContent = "● Erro de conexão";
            statusAtualizacao.className = "offline";
        }

    }
}


function renderizarFila(fila) {

    filaBody.innerHTML = "";

    const aguardando = fila.filter(
        cliente => cliente.status === "Aguardando"
    );

    const emAtendimento = fila.filter(
        cliente => cliente.status === "Em atendimento"
    );

    const atual = emAtendimento.length > 0
        ? emAtendimento[0]
        : null;

    renderizarClienteAtual(atual);

    const clientesAguardando = fila.filter(
        cliente => cliente.status === "Aguardando"
    );

    if (clientesAguardando.length === 0) {

        const row = document.createElement("tr");

        row.innerHTML = `
            <td colspan="7" class="empty-table">
                Não existem clientes aguardando.
            </td>
        `;

        filaBody.appendChild(row);

        return;
    }

    clientesAguardando.forEach((cliente, index) => {

        const row = document.createElement("tr");

        const prioridadeClass =
            cliente.prioridade === "Preferencial"
                ? "badge badge-priority"
                : "badge";

        row.innerHTML = `
            <td>
                <span class="position">
                    ${index + 1}
                </span>
            </td>

            <td>
                <strong>${escapeHtml(cliente.nome)}</strong>
            </td>

            <td>
                ${escapeHtml(cliente.telefone || "-")}
            </td>

            <td>
                <span class="${prioridadeClass}">
                    ${escapeHtml(cliente.prioridade)}
                </span>
            </td>

            <td>
                ${escapeHtml(cliente.chegada_formatado || "-")}
            </td>

            <td>
                <span class="badge">
                    Aguardando
                </span>
            </td>

            <td>
                <div class="actions">

                    <button
                        type="button"
                        class="btn btn-success"
                        onclick="alterarStatus(${cliente.id}, 'Em atendimento')"
                    >
                        Atender
                    </button>

                    <button
                        type="button"
                        class="btn btn-danger"
                        onclick="cancelarCliente(${cliente.id})"
                    >
                        Cancelar
                    </button>

                </div>
            </td>
        `;

        filaBody.appendChild(row);
    });
}


function renderizarClienteAtual(cliente) {

    if (!clienteAtual) {
        return;
    }

    if (!cliente) {

        clienteAtual.innerHTML = `
            <span class="empty">
                Nenhum cliente em atendimento.
            </span>
        `;

        return;
    }

    clienteAtual.innerHTML = `
        <div>
            <strong>
                ${escapeHtml(cliente.nome)}
            </strong>

            <div style="margin-top: 5px; color: #64748b;">
                Em atendimento desde
                ${escapeHtml(cliente.inicio_atendimento_formatado || "-")}
            </div>

            <div class="actions" style="margin-top: 12px;">

                <button
                    type="button"
                    class="btn btn-success"
                    onclick="alterarStatus(${cliente.id}, 'Concluído')"
                >
                    Concluir
                </button>

                <button
                    type="button"
                    class="btn btn-danger"
                    onclick="cancelarCliente(${cliente.id})"
                >
                    Cancelar
                </button>

            </div>
        </div>
    `;
}


async function carregarDashboard() {

    if (!totalAguardando) {
        return;
    }

    try {

        const response = await fetch("/api/dashboard");

        if (!response.ok) {
            throw new Error("Erro ao carregar dashboard.");
        }

        const dados = await response.json();

        totalAguardando.textContent = dados.aguardando;
        totalAtendimento.textContent = dados.atendimento;
        totalConcluidos.textContent = dados.concluidos;
        totalCancelados.textContent = dados.cancelados;

    } catch (error) {

        console.error(error);

    }
}


if (formCliente) {

    formCliente.addEventListener("submit", async function (event) {

        event.preventDefault();

        const formData = new FormData(formCliente);

        const dados = {
            nome: formData.get("nome"),
            telefone: formData.get("telefone"),
            prioridade: formData.get("prioridade")
        };

        try {

            const response = await fetch(
                "/api/cadastrar",
                {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify(dados)
                }
            );

            const resultado = await response.json();

            if (!response.ok) {
                throw new Error(resultado.mensagem);
            }

            mostrarToast(resultado.mensagem);

            formCliente.reset();

            document.getElementById("prioridade").value = "Normal";

            await atualizarTudo();

            document.getElementById("nome").focus();

        } catch (error) {

            mostrarToast(
                error.message || "Não foi possível cadastrar."
            );

        }

    });

}


if (btnChamar) {

    btnChamar.addEventListener("click", async function () {

        btnChamar.disabled = true;

        try {

            const response = await fetch(
                "/api/chamar-proximo",
                {
                    method: "POST"
                }
            );

            const resultado = await response.json();

            if (!response.ok) {
                throw new Error(resultado.mensagem);
            }

            mostrarToast(resultado.mensagem);

            await atualizarTudo();

        } catch (error) {

            mostrarToast(
                error.message || "Não foi possível chamar o próximo."
            );

        } finally {

            btnChamar.disabled = false;

        }

    });

}


async function alterarStatus(id, status) {

    try {

        const response = await fetch(
            `/api/status/${id}`,
            {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    status: status
                })
            }
        );

        const resultado = await response.json();

        if (!response.ok) {
            throw new Error(resultado.mensagem);
        }

        mostrarToast(resultado.mensagem);

        await atualizarTudo();

    } catch (error) {

        mostrarToast(
            error.message || "Não foi possível alterar o status."
        );

    }

}


async function cancelarCliente(id) {

    const confirmar = confirm(
        "Deseja realmente cancelar este atendimento?"
    );

    if (!confirmar) {
        return;
    }

    try {

        const response = await fetch(
            `/api/cancelar/${id}`,
            {
                method: "POST"
            }
        );

        const resultado = await response.json();

        if (!response.ok) {
            throw new Error(resultado.mensagem);
        }

        mostrarToast(resultado.mensagem);

        await atualizarTudo();

    } catch (error) {

        mostrarToast(
            error.message || "Não foi possível cancelar."
        );

    }

}


async function atualizarTudo() {

    await Promise.all([
        carregarFila(),
        carregarDashboard()
    ]);

}


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }

    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


if (filaBody) {

    atualizarTudo();

    setInterval(
        atualizarTudo,
        3000
    );

}
