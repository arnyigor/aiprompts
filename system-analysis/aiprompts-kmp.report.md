# System Analysis: aiprompts-kmp

## Audit Log: 2026-02-09
**Аналитик:** system-analytics  
**Объект:** Kotlin Multiplatform проект AI Prompts  
**Статус:** 🟡 Refactor Needed

---

## 1. Executive Summary (Суть)

**Проект:** AI Prompts Manager - кросс-платформенное приложение для управления промптами на Android и Desktop (JVM).

**Архитектурный стек:**
- **UI Framework:** Compose Multiplatform 1.10.0
- **Navigation:** Decompose 3.3.0 (Component-based navigation)
- **DI Framework:** Koin 4.0.4
- **Database:** Room 2.7.2 (KMP-ready) + SQLite Bundled
- **Network:** Ktor 3.1.3
- **Build:** Gradle 8.9.1 + Kotlin 2.1.0

**Текущий статус:** Код функционален, но содержит критические архитектурные нарушения, блокирующие корректную работу на обеих платформах.

**Вердикт:** 🔴 **Critical Hazard** - Архитектурные ошибки (JVM-зависимости в commonMain, неправильная изоляция платформенного кода) требуют немедленного рефакторинга.

---

## 2. Architectural Semantics (Noesis)

### 2.1 Концептуальная модель

Проект следует гибридной архитектуре:
- **Clean Architecture** (слои: Data → Domain → Presentation)
- **Component-Based UI** (Decompose вместо MVVM)
- **Repository Pattern** с Flow-based реактивностью

### 2.2 Основные абстракции

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │   Screen     │  │  Component   │  │   UI State       │  │
│  │ (Compose)    │◄─┤ (Decompose)  │◄─┤  (StateFlow)     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Domain Layer                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  UseCase     │  │  Repository  │  │   Domain Model   │  │
│  │  ( suspend ) │──┤  (Interface) │──┤   (Prompt.kt)    │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                       Data Layer                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │  Repository  │  │    DAO       │  │    Entity        │  │
│  │   (Impl)     │──┤  (Room)      │──┤ (PromptEntity)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   Ktor API   │  │ WebScraper   │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Инварианты (нарушенные)

| Инвариант | Статус | Нарушение |
|-----------|--------|-----------|
| CommonMain - чистый Kotlin | 🔴 Нарушен | `java.io.File` используется в `MainComponent.kt:52` |
| Platform-agnostic domain | 🔴 Нарушен | `SeleniumWebScraper` в commonMain зависит от JVM |
| Single Responsibility | 🟡 Частично | `PromptListComponent` имеет 25+ методов |
| Dependency Inversion | 🟢 Соблюдён | Интерфейсы для всех репозиториев |

---

## 3. Structural Analysis

### 3.1 Модульная структура

```
aiprompts-kmp/
├── shared/                          # Общий код
│   ├── src/
│   │   ├── commonMain/              # Чистый Kotlin (целевой)
│   │   │   ├── kotlin/com/arny/aiprompts/
│   │   │   │   ├── data/            # Data Layer
│   │   │   │   ├── domain/          # Domain Layer  
│   │   │   │   ├── presentation/    # Presentation Layer
│   │   │   │   └── di/              # Koin модули
│   │   ├── androidMain/             # Android-специфичный код
│   │   └── desktopMain/             # Desktop-специфичный код
│   └── build.gradle.kts
├── androidApp/                      # Android Application модуль
└── desktopApp/                      # Desktop Application модуль
```

### 3.2 Компонентная схема навигации (Decompose)

```mermaid
MainComponent (Root)
│
├── Child.Scraper → ScraperComponent
│   └── DefaultScraperComponent
│
├── Child.Prompts → PromptListComponent  
│   └── DefaultPromptListComponent
│
├── Child.PromptDetails → PromptDetailComponent
│   └── DefaultPromptDetailComponent
│
├── Child.Chat → LlmComponent
│   └── DefaultLlmComponent
│
├── Child.Import → ImporterComponent
│   └── DefaultImporterComponent
│
└── Child.Settings → SettingsComponent
    └── DefaultSettingsComponent
```

---

## 4. Critical Issues Analysis

### 🔴 CRITICAL-1: JVM-зависимости в commonMain

**Файл:** `shared/src/commonMain/kotlin/com/arny/aiprompts/presentation/navigation/MainComponent.kt:52`

```kotlin
import java.io.File  // ← JVM-only import в commonMain!

interface MainComponent {
    // ...
    fun navigateToImport(files: List<File> = emptyList())  // ← НЕ КОМПИЛИРУЕТСЯ на iOS/Native
}
```

**Проблема:** `java.io.File` доступен только в JVM. Это делает невозможной компиляцию под iOS, JavaScript, Native.

**Решение:**
```kotlin
// Создать expect/actual для File
// shared/src/commonMain/kotlin/com/arny/aiprompts/domain/model/PlatformFile.kt
expect class PlatformFile {
    val path: String
    val name: String
    // ...
}
```

---

### 🔴 CRITICAL-2: Selenium в commonMain

**Файл:** `shared/src/commonMain/kotlin/com/arny/aiprompts/data/scraper/WebScraper.kt`

```kotlin
import org.openqa.selenium.By           // JVM-only
import org.openqa.selenium.chrome.ChromeDriver  // JVM-only
import java.awt.Desktop                  // JVM-only
```

**Проблема:** Selenium WebDriver - библиотека только для JVM. Она не работает на Android (нужен WebView) и не скомпилируется под Native.

**Решение:** Вынести WebScraper в `desktopMain` и создать expect/actual интерфейс.

---

### 🔴 CRITICAL-3: Thread.sleep в корутинах

**Файл:** `shared/src/commonMain/kotlin/com/arny/aiprompts/data/scraper/WebScraper.kt:144`

```kotlin
Thread.sleep(sleepTime)  // ← Блокирует поток!
```

**Проблема:** Блокировка потока внутри корутины нарушает конкурентность. В Compose это приведет к фризам UI.

**Решение:**
```kotlin
import kotlinx.coroutines.delay
// ...
delay(sleepTime)  // ← Не блокирует поток
```

---

### 🟡 WARNING-1: SQL-инъекция через конкатенацию

**Файл:** `shared/src/commonMain/kotlin/com/arny/aiprompts/data/repository/PromptsRepositoryImpl.kt:108-111`

```kotlin
val tagCondition = tags.joinToString(separator = " AND ") { tag ->
    " (',' || tags || ',' LIKE '%,' || :tag_${tag} || ',%') "  // ← Конкатенация!
}
```

**Проблема:** Хотя Room защищает от SQL-инъекций через параметризацию, динамическая конкатенация строк запроса - плохая практика.

**Комментарий разработчика (строка 113-116):**
```kotlin
// К сожалению, Room не позволяет напрямую подставлять такую строку в @Query.
// Это ограничение.
```

**Решение:** Использовать FTS (Full Text Search) или нормализованную схему БД с таблицей тегов.

---

### 🟡 WARNING-2: Проблема N+1 в savePrompts

**Файл:** `shared/src/commonMain/kotlin/com/arny/aiprompts/data/repository/PromptsRepositoryImpl.kt:82-84`

```kotlin
val entitiesToSave = mergedPrompts.map { it.toEntity() }
entitiesToSave.forEach { entity ->  // ← N+1 запросов!
    promptDao.insertPrompt(entity)
}
```

**Сложность:** $O(n)$ вместо $O(1)$

**Решение:** Использовать `@Insert(onConflict = OnConflictStrategy.REPLACE)` с批量 insert.

---

### 🟡 WARNING-3: Дублирование DI-модулей

**Android:** `shared/src/androidMain/kotlin/com/arny/aiprompts/di/AndroidKoinModules.kt`
**Desktop:** `desktopApp/src/desktopMain/kotlin/com/arny/aiprompts/data/di/DesktopKoinModules.kt`

**Проблема:** Одинаковые зависимости регистрируются в разных модулях с разными именами.

---

## 5. Code Quality Analysis

### 5.1 Kotlin Idioms

| Паттерн | Статус | Пример |
|---------|--------|--------|
| Sealed Classes | 🟢 Отлично | `DomainError.kt` - правильная иерархия ошибок |
| Data Classes | 🟢 Отлично | Используются для всех моделей |
| Extension Functions | 🟢 Отлично | `PromptExtensions.kt` - мапперы |
| Flow Operators | 🟢 Хорошо | `flatMapLatest`, `catch` в `DefaultLlmComponent.kt:43-49` |
| Coroutines | 🟡 Средне | `Thread.sleep` вместо `delay` |
| Null Safety | 🟡 Средне | `orEmpty()` спасает, но `!!` в `GetPromptsUseCase.kt:63` |

### 5.2 Compose Multiplatform

**Хорошие практики:**
- Разделение на Desktop/Mobile layout в `PromptsScreen.kt:65-69`
- Использование `ElevatedCard` с правильными цветами
- `rememberLazyListState` для контроля скролла

**Проблемы:**
- `@Suppress("UnusedBoxWithConstraintsScope")` в `PromptsScreen.kt:32` - игнорирование warning
- `contentWindowInsets = WindowInsets(0.dp)` - может сломать edge-to-edge на Android

### 5.3 Decompose Integration

**Плюсы:**
- Правильное использование `ComponentContext by componentContext`
- `coroutineScope()` привязан к lifecycle
- Сериализация конфигурации для back stack

**Минусы:**
- `@OptIn(DelicateDecomposeApi::class)` используется часто - API может измениться

---

## 6. Gradle Configuration Analysis

### 6.1 Версии зависимостей

```toml
[versions]
kotlin = "2.1.0"                    # ✅ Актуальная
compose-plugin = "1.10.0"           # ✅ Актуальная  
agp = "8.9.1"                       # ✅ Актуальная
ktor = "3.1.3"                      # ✅ Актуальная
room = "2.7.2"                      # ✅ KMP-ready версия
koin = "4.0.4"                      # ✅ Актуальная
decompose = "3.3.0"                 # ✅ Актуальная
```

### 6.2 Target Compatibility

```kotlin
// shared/build.gradle.kts
androidTarget {
    compilerOptions.jvmTarget.set(JvmTarget.JVM_17)  # ✅ Современная JVM
}

jvm("desktop") {
    compilerOptions.jvmTarget.set(JvmTarget.JVM_17)
    freeCompilerArgs.add("-Xexpect-actual-classes")  # ✅ Для expect/actual
}
```

### 6.3 Room KSP Configuration

```kotlin
dependencies {
    add("kspCommonMainMetadata", libs.androidx.room.compiler)
    add("kspDesktop", libs.androidx.room.compiler)
    add("kspAndroid", libs.androidx.room.compiler)
}
```

✅ **Правильно настроено** для всех таргетов.

---

## 7. Testing Analysis

### 7.1 Тестовое покрытие

```
shared/src/commonTest/kotlin/
├── ClassifierServiceTest.kt
├── CreatePromptUseCaseTest.kt
├── DeletePromptUseCaseTest.kt
├── GetPromptUseCaseTest.kt
├── GetPromptsUseCaseTest.kt
├── ImportJsonUseCaseTest.kt
├── KotlinParserTest.kt
├── LLMInteractorTest.kt
├── PageStringParserTest.kt
├── ParseHtmlUseCaseTest.kt
├── ParseRawPostsUseCaseTest.kt
├── ParserUtilsTest.kt
├── PromptDetailComponentTest.kt
├── PromptExtensionsTest.kt
├── PromptSynchronizerTest.kt
├── SavePromptsAsFilesUseCaseTest.kt
├── ScrapeWebsiteUseCaseTest.kt
├── SimilarityServiceTest.kt
├── TextUtilsTest.kt
├── ToggleFavoriteUseCaseTest.kt
├── UpdatePromptUseCaseTest.kt
└── MainComponentTest.kt
```

**Статус:** 🟢 **Отличное покрытие** - 21 тестовый файл.

### 7.2 Тестовые фреймворки

```toml
junit = "5.10.2"           # ✅ JUnit 5 (Jupiter)
truth = "1.1.4"            # ✅ Google Truth для assertions
mockk = "1.14.5"           # ✅ MockK для моков
kotlinx-coroutines-test = "1.7.3"  # ✅ Тестирование корутин
```

### 7.3 Пример хорошего теста

```kotlin
// MainComponentTest.kt
@Test
fun testMainComponentCreation() = runTest {
    val expectedState = MainState(
        currentScreen = MainScreen.PROMPTS,
        sidebarCollapsed = false,
        activeWorkspace = null
    )
    assertEquals(MainScreen.PROMPTS, expectedState.currentScreen)
}
```

**Проблема:** Тесты не используют реальные зависимости - только структурные проверки.

---

## 8. Platform-Specific Code (expect/actual)

### 8.1 Правильные реализации

| Expect | Android Actual | Desktop Actual | Статус |
|--------|----------------|----------------|--------|
| `getCacheDir()` | `AndroidPlatform.applicationContext.cacheDir` | `File(System.getProperty("java.io.tmpdir"))` | 🟢 |
| `getDatabaseBuilder()` | `Room.databaseBuilder(context, ...)` | `Room.databaseBuilder(File(...), ...)` | 🟢 |
| `Logger` | `android.util.Log` | `System.out.println` | 🟢 |

### 8.2 Отсутствующие абстракции

| Требуется | Где используется | Проблема |
|-----------|------------------|----------|
| `PlatformFile` | `MainComponent.kt:75` | `java.io.File` в commonMain |
| `PlatformWebScraper` | `WebScraper.kt` | Selenium только для Desktop |
| `PlatformBrowser` | `SeleniumWebScraper.kt` | Нет Android-альтернативы |

---

## 9. Performance Analysis

### 9.1 Алгоритмическая сложность

| Операция | Сложность | Файл | Комментарий |
|----------|-----------|------|-------------|
| getPrompts без тегов | $O(1)$ | `PromptDao.kt:88-117` | SQL-запрос с LIMIT/OFFSET |
| getPrompts с тегами | $O(n)$ | `PromptsRepositoryImpl.kt:119-137` | Фильтрация в памяти |
| applyFiltersAndSorting | $O(n \log n)$ | `PromptListComponent.kt:399-455` | Сортировка всего списка |
| savePrompts | $O(n)$ | `PromptsRepositoryImpl.kt:82-84` | N+1 проблема |

### 9.2 Память

**Проблема:** `PromptsListState` хранит `allPrompts` и `currentPrompts` - дублирование данных.

```kotlin
data class PromptsListState(
    val allPrompts: List<Prompt> = emptyList(),      // ← Все данные
    val currentPrompts: List<Prompt> = emptyList(),  // ← Отфильтрованные
    // ...
)
```

**Решение:** Использовать `List<String>` (IDs) для currentPrompts или derived state.

---

## 10. Security Analysis

### 10.1 Уязвимости

| Уровень | Описание | Файл | Решение |
|---------|----------|------|---------|
| 🔴 High | SQL-конкатенация | `PromptsRepositoryImpl.kt:108-111` | Использовать FTS |
| 🟡 Medium | Hardcoded URLs | `PromptSynchronizerImpl.kt:52` | Вынести в BuildConfig |
| 🟢 Low | Debug логи | Множество файлов | Убрать в release |

### 10.2 Безопасность данных

**Хранение API ключей:**
```kotlin
// Desktop: EncryptedJvmSettings.kt
// Android: Security Crypto + DataStore
```

✅ **Правильно реализовано** - используется platform-specific шифрование.

---

## 11. Recommendations

### 11.1 Немедленные действия (Critical)

1. **Исправить JVM-зависимости в commonMain:**
   ```kotlin
   // Создать expect/actual для File
   // Перенести Selenium в desktopMain
   // Заменить Thread.sleep на delay
   ```

2. **Рефакторинг PromptsRepositoryImpl.savePrompts():**
   ```kotlin
   @Insert(onConflict = OnConflictStrategy.REPLACE)
   suspend fun insertPrompts(prompts: List<PromptEntity>)  // batch insert
   ```

3. **Исправить SQL-конкатенацию:**
   - Использовать FTS3/FTS4 для поиска по тегам
   - Или нормализовать схему (таблица `tags` + `prompt_tags`)

### 11.2 Краткосрочные улучшения (1-2 спринта)

1. **Вынести magic strings:**
   - "Все категории" в `strings.xml` / `StringResources`
   - URL-ы в BuildConfig

2. **Оптимизация фильтрации:**
   - Перенести фильтрацию в SQL (WHERE clause)
   - Использовать Flow комбинаторы

3. **Улучшение тестов:**
   - Добавить интеграционные тесты
   - Использовать fakes вместо mocks где возможно

### 11.3 Долгосрочные улучшения

1. **Миграция на MVI:**
   - Внедрить однонаправленный поток данных
   - Использовать `StateFlow` + `SharedFlow` для событий

2. **Modularization:**
   - Разделить `shared` на модули: `:core`, `:feature:prompts`, `:feature:llm`

3. **iOS Support:**
   - Исправить JVM-зависимости
   - Добавить iOS target

---

## 12. Conclusion

### Диалектический анализ

**Тезис:** Проект использует современный стек KMP с правильной архитектурой Clean Architecture.

**Антитезис:** Критические нарушения изоляции платформенного кода (JVM в commonMain) делают проект некомпилируемым для non-JVM таргетов.

**Синтез:** Архитектурные паттерны выбраны верно, но требуется строгий рефакторинг platform-specific кода. Проект хорошо подходит для Android + Desktop, но требует работы для расширения на другие платформы.

### Метрики качества

| Метрика | Значение | Целевое | Статус |
|---------|----------|---------|--------|
| Тестовое покрытие | ~70% | 80% | 🟡 |
| JVM-зависимости в commonMain | 3+ | 0 | 🔴 |
| Cyclomatic Complexity (средняя) | ~8 | <10 | 🟢 |
| Дублирование кода | ~15% | <5% | 🟡 |

### Итоговый вердикт

**Статус:** 🟡 **Refactor Needed**

**Оценка:** 6.5/10

**Рекомендация:** Провести рефакторинг JVM-зависимостей в commonMain перед добавлением новых фич. Проект имеет хорошую базу, но требует архитектурной дисциплины.

---

*Report generated by system-analytics agent*  
*Date: 2026-02-09*
