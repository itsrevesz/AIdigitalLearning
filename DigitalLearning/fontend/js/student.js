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
               expected_role: 'student'
           })
       });
       const data = await response.json();
       if (response.ok) {
           token = data.token;
           localStorage.setItem('token', token);
           showStudentUI();
           loadAvailableQuizzes();
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

// Elérhető kvízek betöltése
async function loadAvailableQuizzes() {
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
                   <button class="btn btn-sm btn-success" onclick="startQuiz('${quiz.id}')">
                       Kitöltés
                   </button>
               </td>
           `;
       });
   } catch (error) {
       console.error('Hiba:', error);
   }
}

// Kvíz kitöltésének indítása
async function startQuiz(quizId) {
   try {
       const response = await fetch(`${API_URL}/quiz/${quizId}`, {
           headers: {
               'Authorization': `Bearer ${token}`
           }
       });
       const quiz = await response.json();

       // Kvíz megjelenítése
       document.getElementById('availableQuizzes').style.display = 'none';
       document.getElementById('quizForm').style.display = 'block';
       document.getElementById('quizTopic').textContent = `Kvíz: ${quiz.topic}`;

       const quizContent = document.getElementById('quizContent');
       quizContent.innerHTML = `
           <form id="submitQuiz">
               ${quiz.questions.map((question, index) => `
                   <div class="card mb-3">
                       <div class="card-body">
                           <h5 class="card-title">${index + 1}. ${question.question}</h5>
                           <div class="list-group mt-3">
                               ${question.options.map((option, optIndex) => `
                                   <div class="form-check">
                                       <input class="form-check-input" type="radio" 
                                           name="question${index}" 
                                           value="${option}"
                                           id="q${index}opt${optIndex}">
                                       <label class="form-check-label" for="q${index}opt${optIndex}">
                                           ${['A', 'B', 'C', 'D'][optIndex]}) ${option}
                                       </label>
                                   </div>
                               `).join('')}
                           </div>
                       </div>
                   </div>
               `).join('')}
               <button type="submit" class="btn btn-primary">Beküldés</button>
           </form>
       `;

       // Kvíz beküldésének kezelése
       document.getElementById('submitQuiz').addEventListener('submit', (e) => {
           e.preventDefault();
           checkAnswers(quiz.questions);
       });
   } catch (error) {
       console.error('Hiba:', error);
   }
}

// Válaszok ellenőrzése
function checkAnswers(questions) {
   let score = 0;
   const results = [];

   questions.forEach((question, index) => {
       const selectedOption = document.querySelector(`input[name="question${index}"]:checked`)?.value;
       const isCorrect = selectedOption === question.correct_answer;

       if (isCorrect) score++;

       results.push({
           question: question.question,
           selectedAnswer: selectedOption,
           correctAnswer: question.correct_answer,
           isCorrect: isCorrect
       });
   });

   // Eredmények megjelenítése
   const quizContent = document.getElementById('quizContent');
   quizContent.innerHTML = `
       <div class="alert alert-info">
           <h4>Eredmény: ${score}/${questions.length} pont</h4>
       </div>
       ${results.map((result, index) => `
           <div class="card mb-2">
               <div class="card-body">
                   <h5 class="card-title">${index + 1}. ${result.question}</h5>
                   <p>Választott válasz: ${result.selectedAnswer || 'Nem választottál'}</p>
                   <p class="${result.isCorrect ? 'text-success' : 'text-danger'}">
                       ${result.isCorrect ? '✓ Helyes válasz!' : `✗ Helytelen. A helyes válasz: ${result.correctAnswer}`}
                   </p>
               </div>
           </div>
       `).join('')}
       <button onclick="window.location.reload()" class="btn btn-secondary mt-3">Új kvíz kezdése</button>
   `;
}

// UI megjelenítése bejelentkezés után
function showStudentUI() {
   document.getElementById('loginForm').style.display = 'none';
   document.getElementById('availableQuizzes').style.display = 'block';
   document.getElementById('quizForm').style.display = 'none';
}

// Kezdeti állapot beállítása
if (token) {
   showStudentUI();
   loadAvailableQuizzes();
}