// static/theme.js
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('theme-form');
    const toast = document.getElementById('toast');
    let tempTimer = null;

    // Показываем тост, если в URL есть параметр theme_applied
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('theme_applied') === '1') {
        toast.style.display = 'flex';
        // Удаляем параметр из URL без перезагрузки
        const newUrl = window.location.pathname;
        window.history.replaceState({}, document.title, newUrl);
    }

    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            const formData = new FormData(form);
            formData.append('action', 'temporary');

            try {
                const response = await fetch(window.location.href, {
                    method: 'POST',
                    body: formData
                });
                if (response.ok) {
                    // После сохранения переходим на ту же страницу с параметром, чтобы показать тост
                    window.location.href = window.location.pathname + '?theme_applied=1';
                } else {
                    alert('Ошибка сохранения');
                }
            } catch (err) {
                alert('Ошибка сети');
            }
        });
    }

    // Обработчики кнопок тоста
    const btnPermanent = document.getElementById('toast-permanent');
    const btnRollback = document.getElementById('toast-rollback');
    const btnTemp = document.getElementById('toast-temp');

    if (btnPermanent) {
        btnPermanent.onclick = async () => {
            const formData = new FormData(form);
            formData.append('action', 'permanent');
            await fetch(window.location.href, { method: 'POST', body: formData });
            window.location.href = window.location.pathname; // перезагружаем без параметра
        };
    }

    if (btnRollback) {
        btnRollback.onclick = async () => {
            await fetch('/reset_temp_theme', { method: 'POST' });
            window.location.href = window.location.pathname;
        };
    }

    if (btnTemp) {
        btnTemp.onclick = () => {
            if (tempTimer) clearTimeout(tempTimer);
            tempTimer = setTimeout(async () => {
                await fetch('/reset_temp_theme', { method: 'POST' });
                window.location.href = window.location.pathname;
            }, 120000);
            document.getElementById('toast-timer').innerText = 'Тема будет откатана через 2 минуты';
            toast.style.display = 'none';
        };
    }
});
