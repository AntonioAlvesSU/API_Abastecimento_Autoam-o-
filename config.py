from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Dict, Any

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    db_user: str = Field(..., alias="DB_USER")
    db_password: str = Field(..., alias="DB_PASSWORD")
    #db_password_caxuxa: str = Field(..., alias="DB_PASSWORD_CAXUXA")

settings = Settings()

# Dados não sensíveis (host, porta e database) ficam no código
# Usuário e senha vêm das variáveis de ambiente
servidores: Dict[str, Dict[str, Any]] = {

    "Mutuca": {
        "host": "13.0.0.60",
        "port": 5432,
        "database": "autosystem",
        "user": settings.db_user,
        "password": settings.db_password,
        "ativo": True
    }
     

}