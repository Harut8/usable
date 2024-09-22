import secrets
import string
from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, model_validator, AmqpDsn, HttpUrl, PostgresDsn, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

env_file = ".env"
encoding = "utf-8"
case_sensitive = True


def generate_secret(byte=512):
    return secrets.token_urlsafe(byte)


def generate_aes_key(length=32):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for i in range(length))


SECRET_KEY_32 = f"{generate_secret(32)}"
SECRET_KEY_64 = f"{generate_secret(64)}"
SECRET_KEY_32_AES = f"{generate_aes_key(32)}"


class CustomSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=env_file,
        env_file_encoding=encoding,
        case_sensitive=case_sensitive,
        extra="ignore",
    )


class AppSettings(CustomSettings):
    ENV: Literal["local", "dev", "prod"] = Field(default="local", alias="ENV")
    DEBUG: bool = Field(default=False, alias="DEBUG")


class DbSettings(AppSettings):
    POSTGRES_ENGINE: str = Field(default=..., alias="POSTGRES_ENGINE")
    POSTGRES_USER: str = Field(default=..., alias="POSTGRES_USER")
    POSTGRES_PASSWORD: SecretStr = Field(default=..., alias="POSTGRES_PASSWORD")
    POSTGRES_DB: str = Field(default=..., alias="POSTGRES_DB")
    POSTGRES_HOST: str = Field(default=..., alias="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=..., alias="POSTGRES_PORT")
    SQLALCHEMY_DATABASE_URI: PostgresDsn

    @model_validator(mode="before")
    def validate_postgres_dsn(cls, data: dict):
        _built_uri = PostgresDsn.build(
            scheme=data.setdefault("POSTGRES_ENGINE", "postgresql+asyncpg"),
            username=data.setdefault("POSTGRES_USER", "postgres"),
            password=data.setdefault("POSTGRES_PASSWORD", "postgres"),
            host=data.setdefault("POSTGRES_HOST", "localhost"),
            port=int(data.setdefault("POSTGRES_PORT", 5432)),
            path=data.setdefault("POSTGRES_DB", "postgres"),
        )
        data["SQLALCHEMY_DATABASE_URI"] = _built_uri if not data.get("SQLALCHEMY_DATABASE_URI") else data[
            "SQLALCHEMY_DATABASE_URI"]
        return data


class ApiSettings(CustomSettings):
    API_V1_PREFIX: str = "/api/v1"
    API_KEY: SecretStr = Field(default=f"{SECRET_KEY_32}")
    API_SECRET: SecretStr = Field(default=f"{SECRET_KEY_32}")


class S3Settings(CustomSettings):
    AWS_ACCESS_KEY: SecretStr = Field(default="")
    AWS_SECRET_KEY: SecretStr = Field(default="")
    AWS_REGION: SecretStr = Field(default="")
    AWS_BUCKET_NAME: SecretStr = Field(default="")


class JWTSettings(CustomSettings):
    JWT_ACCESS_SECRET: SecretStr = Field(default=f"{SECRET_KEY_64}")
    JWT_ALGORITHM: str = Field(default="HS256")
    VERIFICATION_MINUTES: int = Field(default=30)


class OpenAISettings(CustomSettings):
    OPENAI_API_KEY: SecretStr = Field(default=f"{SECRET_KEY_32}")


class RabbitMQSettings(AppSettings):
    RABBITMQ_HOST: str = Field(default="rabbitmq-service", alias="RMQ_HOST")
    RABBITMQ_PORT: int = Field(default=5672, alias="RMQ_PORT")
    RABBITMQ_USER: str = Field(default="guest", alias="RMQ_USER")
    RABBITMQ_PASSWORD: SecretStr = Field(default="guest", alias="RMQ_PASSWORD")
    BROKER_URL: AmqpDsn

    @model_validator(mode="before")
    def validate_broker_url(cls, data: dict):
        data["BROKER_URL"] = AmqpDsn.build(
            scheme="amqp",
            host=data.setdefault("RABBITMQ_HOST", "localhost"),
            port=int(data.setdefault("RABBITMQ_PORT", 5672)),
            username=data.setdefault("RABBITMQ_USER", "guest"),
            password=data.setdefault("RABBITMQ_PASSWORD", "guest"),
        )
        return data


class ApiCallSettings(ApiSettings):
    ORGANIZATION: HttpUrl = Field(
        default="https://example.com/organization",
        alias="SERVICE_ORGANIZATION_HOST",
    )


class MailSettings(CustomSettings):
    MAIL_USERNAME: str = Field(
        default="no-reply@simulacrumai.com",
        alias="SMTP_USERNAME",
    )
    MAIL_PASSWORD: SecretStr = Field(
        default="Yyv0Hx6UYu",
        alias="INTEGRATION_SMTP_PASSWORD",
    )
    MAIL_FROM: str = Field(
        default="noreply@simulacrumai.com",
        alias="INTEGRATION_SMTP_FROM",
    )
    MAIL_SERVER: str = Field(
        default="smtp.simulacrumai.com",
        alias="INTEGRATION_SMTP_SERVER",
    )
    MAIL_PORT: int = Field(default=465, alias="INTEGRATION_SMTP_PORT")
    MAIL_SSL_TLS: bool = Field(default=True, alias="INTEGRATION_SMTP_SSL_TLS")
    MAIL_STARTTLS: bool = Field(default=False, alias="INTEGRATION_SMTP_STARTTLS")
    VALIDATE_CERTS: bool = Field(default=False, alias="INTEGRATION_SMTP_VALIDATE_CERTS")
    USE_CREDENTIALS: bool = Field(default=True, alias="INTEGRATION_SMTP_USE_CREDENTIALS")


class Settings(BaseModel):
    APP_SETTINGS: AppSettings = Field(default_factory=AppSettings)
    DATABASE: DbSettings = Field(default_factory=DbSettings)
    API_V1: ApiSettings = Field(default_factory=ApiSettings)
    S3: S3Settings = Field(default_factory=S3Settings)
    JWT: JWTSettings = Field(default_factory=JWTSettings)
    OPENAI: OpenAISettings = Field(default_factory=OpenAISettings)
    RABBITMQ: RabbitMQSettings = Field(default_factory=RabbitMQSettings)
    API_CALL: ApiCallSettings = Field(default_factory=ApiCallSettings)
    MAIL: MailSettings = Field(default_factory=MailSettings)


@lru_cache
def get_settings() -> Settings:
    return Settings()


SETTINGS = get_settings()

print(SETTINGS.RABBITMQ)
