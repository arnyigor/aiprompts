# Сравнение Android-копий

Основной: aipromptmaster. Источник сравнения: AIPromptMasterCompose.
Каждое отличие требует оценки; изменённый файл не означает полезную новую функцию.

| Файл | Состояние | Решение |
|---|---|---|
| app/build.gradle.kts | Различается | Проверить diff |
| app/schemas/com.arny.aipromptmaster.data.db.AppDatabase/4.json | Различается | Проверить diff |
| app/schemas/com.arny.aipromptmaster.data.db.AppDatabase/5.json | Различается | Проверить diff |
| app/schemas/com.arny.aipromptmaster.data.db.AppDatabase/6.json | Различается | Проверить diff |
| app/schemas/com.arny.aipromptmaster.data.db.AppDatabase/7.json | Только основной Android | Сохранить |
| app/schemas/com.arny.aipromptmaster.data.db.AppDatabase/8.json | Только основной Android | Сохранить |
| app/src/main/java/com/arny/aipromptmaster/AiPromptMasterApp.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/db/AppDatabase.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/db/daos/ChatDao.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/db/daos/ModelDao.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/db/daos/PromptDao.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/db/entities/MessageEntity.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/db/entities/ModelEntity.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/mappers/ModelMapper.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/models/LLMDTOResponse.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/repositories/ChatHistoryRepositoryImpl.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/repositories/FeedbackRepositoryImpl.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/repositories/ModelRepositoryImpl.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/repositories/OpenRouterRepositoryImpl.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/sync/PromptSynchronizerImpl.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/data/utils/FlowUtils.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/di/DataModule.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/di/ViewModelsModule.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/interactors/ILLMInteractor.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/interactors/LLMInteractor.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/models/errors/DomainError.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/models/LLMModels.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/models/ModelsFilter.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/repositories/IChatHistoryRepository.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/repositories/IOpenRouterRepository.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/domain/repositories/ModelRepository.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/models/ModelsEvent.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/models/ModelsScreen.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/models/ModelsUiState.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/models/ModelsViewModel.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/models/TypingIndicator.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/screens/chat/ChatScreen.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/screens/chat/ChatViewModel.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/screens/edit/PromptEditViewModel.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/theme/Color.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/theme/Theme.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/theme/Type.kt | Различается | Проверить diff |
| app/src/main/java/com/arny/aipromptmaster/ui/utils/AndroidExtentions.kt | Различается | Проверить diff |
| app/src/main/res/drawable-hdpi/ic_launcher.webp | Только основной Android | Сохранить |
| app/src/main/res/drawable-mdpi/ic_launcher.webp | Только основной Android | Сохранить |
| app/src/main/res/drawable-xhdpi/ic_launcher.webp | Только основной Android | Сохранить |
| app/src/main/res/drawable-xxhdpi/ic_launcher.webp | Только основной Android | Сохранить |
| app/src/main/res/drawable-xxxhdpi/ic_launcher.webp | Только основной Android | Сохранить |
| app/src/main/res/drawable/ic_launcher_background.xml | Различается | Проверить diff |
| app/src/main/res/drawable/ic_launcher_foreground.xml | Различается | Проверить diff |
| app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml | Различается | Проверить diff |
| app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml | Различается | Проверить diff |
| app/src/main/res/mipmap-hdpi/ic_launcher_round.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-hdpi/ic_launcher.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-mdpi/ic_launcher_round.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-mdpi/ic_launcher.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-xhdpi/ic_launcher_round.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-xhdpi/ic_launcher.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-xxhdpi/ic_launcher_round.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-xxhdpi/ic_launcher.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-xxxhdpi/ic_launcher_round.webp | Только Compose | Проверить |
| app/src/main/res/mipmap-xxxhdpi/ic_launcher.webp | Только Compose | Проверить |
| app/src/main/res/values/colors.xml | Различается | Проверить diff |
| app/src/main/res/values/strings.xml | Различается | Проверить diff |
| app/src/main/res/values/themes.xml | Различается | Проверить diff |
| build.gradle.kts | Различается | Проверить diff |
| gradle.properties | Различается | Проверить diff |
| gradle/libs.versions.toml | Различается | Проверить diff |
| gradlew | Различается | Проверить diff |
| settings.gradle.kts | Различается | Проверить diff |
| version.properties | Различается | Проверить diff |
