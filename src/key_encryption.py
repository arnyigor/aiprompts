import base64
import logging
import os

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class KeyEncryption:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def generate_key(self, api_key: str) -> tuple[str, str]:
        """
        Генерирует ключ шифрования на основе API ключа
        
        Args:
            api_key: API ключ
            
        Returns:
            tuple[str, str]: (зашифрованный ключ, соль)
        """
        try:
            # Генерируем случайную соль
            salt = os.urandom(16)

            # Создаем ключ на основе API ключа и соли
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )

            # Получаем ключ шифрования
            key = base64.urlsafe_b64encode(kdf.derive(api_key.encode()))

            # Создаем шифровальщик
            f = Fernet(key)

            # Шифруем API ключ
            encrypted_key = f.encrypt(api_key.encode())

            # Возвращаем зашифрованный ключ и соль в base64
            return (
                base64.urlsafe_b64encode(encrypted_key).decode(),
                base64.urlsafe_b64encode(salt).decode()
            )

        except Exception as e:
            self.logger.error(f"Ошибка при генерации ключа: {str(e)}", exc_info=True)
            raise

    def decrypt_key(self, encrypted_key: str, salt: str, api_key: str) -> str:
        """
        Расшифровывает API ключ
        
        Args:
            encrypted_key: Зашифрованный ключ в base64
            salt: Соль в base64
            api_key: API ключ для проверки
            
        Returns:
            str: Расшифрованный API ключ
        """
        try:
            # Декодируем соль и зашифрованный ключ из base64
            salt = base64.urlsafe_b64decode(salt)
            encrypted_key = base64.urlsafe_b64decode(encrypted_key)

            # Создаем ключ на основе API ключа и соли
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )

            # Получаем ключ шифрования
            key = base64.urlsafe_b64encode(kdf.derive(api_key.encode()))

            # Создаем дешифровщик
            f = Fernet(key)

            # Расшифровываем ключ
            decrypted_key = f.decrypt(encrypted_key).decode()

            # Проверяем, что расшифрованный ключ совпадает с оригинальным
            if decrypted_key != api_key:
                raise ValueError("Неверный ключ шифрования")

            return decrypted_key

        except Exception as e:
            self.logger.error(f"Ошибка при расшифровке ключа: {str(e)}", exc_info=True)
            raise
