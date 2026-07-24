function setPreset(val) {
  document.getElementById('inFuncao').value = val;
  document.getElementById('headerFormula').innerText = 'f(x) = ' + val;
}

document.getElementById('inFuncao').addEventListener('input', (e) => {
  document.getElementById('headerFormula').innerText = 'f(x) = ' + (e.target.value || '...');
});

async function gerarFractal() {
  const btn = document.getElementById('btnGerar');
  const btnBaixar = document.getElementById('btnBaixar');
  const placeholder = document.getElementById('placeholder');
  const canvas = document.getElementById('fractalCanvas');
  const ctx = canvas.getContext('2d');

  btn.disabled = true;
  placeholder.style.display = 'block';
  placeholder.innerText = 'Calculando convergências...';

  const payload = {
    polinomio: document.getElementById('inFuncao').value,
    largura: parseInt(document.getElementById('inLargura').value),
    altura: parseInt(document.getElementById('inAltura').value),
    qtd_chutes: parseInt(document.getElementById('inIteracoes').value),
    fator_passo: parseFloat(document.getElementById('inPasso').value),
    tolerancia: parseFloat(document.getElementById('inTolerancia').value)
  };

  try {
    const response = await fetch('/api/gerar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();

    if (data.sucesso) {
      const img = new Image();
      img.onload = () => {
        canvas.width = payload.largura;
        canvas.height = payload.altura;
        ctx.drawImage(img, 0, 0);
        placeholder.style.display = 'none';
      };
      img.src = data.imagem;

      // Atualizar estatísticas e lista de raízes
      document.getElementById('statRaizes').innerText = data.qtd_raizes;
      document.getElementById('statNaoConv').innerText = data.pixels_sem_convergencia;
      document.getElementById('statTempo').innerText = data.tempo;

      const rootsList = document.getElementById('rootsList');
      rootsList.innerHTML = data.raizes.map(r => `<div class="root-item">• ${r}</div>`).join('');

      // Habilitar download
      btnBaixar.onclick = () => {
        const a = document.createElement('a');
        a.download = 'fractal_newton.png';
        a.href = data.imagem;
        a.click();
      };
    } else {
      alert('Erro no cálculo: ' + data.erro);
      placeholder.innerText = 'Erro ao processar.';
    }
  } catch (err) {
    alert('Erro ao conectar com o servidor Python.');
    placeholder.innerText = 'Falha na conexão.';
  } finally {
    btn.disabled = false;
  }
}

document.getElementById('btnGerar').addEventListener('click', gerarFractal);
window.onload = gerarFractal;