const API_URL = 'http://localhost:5000';
let token = localStorage.getItem('token');

// Regisztráció kezelése
document.getElementById('registerForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: document.getElementById('regUsername').value,
                password: document.getElementById('regPassword').value,
                role: document.getElementById('regRole').value
            })
        });

        const data = await response.json();
        if (response.ok) {
            alert('Sikeres regisztráció! Most már bejelentkezhet.');
            document.getElementById('regUsername').value = '';
            document.getElementById('regPassword').value = '';
        } else {
            alert('Hiba a regisztráció során: ' + data.message);
        }
    } catch (error) {
        console.error('Hiba:', error);
    }
});

// Bejelentkezés kezelése
document.getElementById('login').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const response = await fetch(`${API_URL}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: document.getElementById('username').value,
                password: document.getElementById('password').value,
                expected_role: 'teacher'
            })
        });
        const data = await response.json();
        if (response.ok) {
            token = data.token;
            localStorage.setItem('token', token);
            showTeacherUI();
            loadQuizzes();
        } else {
            alert('Hibás bejelentkezési adatok!');
        }
    } catch (error) {
        console.error('Hiba:', error);
    }
});

// Kijelentkezés
document.getElementById('logoutBtn').addEventListener('click', () => {
    localStorage.removeItem('token');
    window.location.reload();
});

// Kvíz generálás
document.getElementById('generateQuiz').addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const response = await fetch(`${API_URL}/generate-quiz`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({
                topic: document.getElementById('topic').value
            })
        });
        const data = await response.json();
        if (response.ok) {
            alert('Kvíz sikeresen létrehozva!');
            loadQuizzes();
            document.getElementById('topic').value = '';
        } else {
            alert('Hiba történt a generálás során: ' + data.message);
        }
    } catch (error) {
        console.error('Hiba:', error);
    }
});

// Kvízek betöltése
async function loadQuizzes() {
    try {
        const response = await fetch(`${API_URL}/quizzes`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const quizzes = await response.json();
        const tbody = document.getElementById('quizTableBody');
        tbody.innerHTML = '';

        quizzes.forEach(quiz => {
            const row = tbody.insertRow();
            row.innerHTML = `
                <td>${quiz.topic}</td>
                <td>${quiz.created_at}</td>
                <td>
                    <button class="btn btn-sm btn-primary" onclick="viewQuiz('${quiz.id}')">
                        Megtekintés
                    </button>
                    <button class="btn btn-sm btn-danger" onclick="deleteQuiz('${quiz.id}')">
                        Törlés
                    </button>
                </td>
            `;
        });
    } catch (error) {
        console.error('Hiba:', error);
    }
}

// UI megjelenítése bejelentkezés után
function showTeacherUI() {
    document.getElementById('loginForm').style.display = 'none';
    document.getElementById('quizPanel').style.display = 'block';
    document.getElementById('quizList').style.display = 'block';
}

// Kvíz törlése
// Kvíz törlése
async function deleteQuiz(quizId) {
    if (confirm('Biztosan törölni szeretné ezt a kvízt?')) {
        try {
            const response = await fetch(`${API_URL}/delete-quiz/${quizId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            if (response.ok) {
                alert('Kvíz sikeresen törölve!');
                await loadQuizzes();
            } else {
                alert('Hiba történt a törlés során!');
            }
        } catch (error) {
            console.error('Hiba:', error);
        }
    }
}

// Kvíz megtekintése
async function viewQuiz(quizId) {
    try {
        const response = await fetch(`${API_URL}/quiz/${quizId}`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        const quiz = await response.json();
        
        const modalHtml = `
            <div class="modal fade" id="quizModal" tabindex="-1">
                <div class="modal-dialog modal-lg">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">Kvíz: ${quiz.topic}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${quiz.questions.map((q, i) => `
                                <div class="card mb-3">
                                    <div class="card-body">
                                        <h6 class="card-title">${i + 1}. ${q.question}</h6>
                                        <div class="list-group mt-2">
                                            ${q.options.map(option => `
                                                <div class="list-group-item ${option === q.correct_answer ? 'list-group-item-success' : ''}">
                                                    ${option} ${option === q.correct_answer ? '✓' : ''}
                                                </div>
                                            `).join('')}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Modal létrehozása és megjelenítése
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        const modal = new bootstrap.Modal(document.getElementById('quizModal'));
        modal.show();

        // Modal törlése bezárás után
        document.getElementById('quizModal').addEventListener('hidden.bs.modal', function () {
            this.remove();
        });
    } catch (error) {
        console.error('Hiba:', error);
        alert('Hiba történt a kvíz betöltésekor!');
    }
}

// Kezdeti állapot beállítása
if (token) {
    showTeacherUI();
    loadQuizzes();
}