from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JT_",
    )

    base_path: Path = Path(
        "~/Library/CloudStorage/GoogleDrive-philippe.sa.costa@gmail.com"
        "/My Drive/03_Work/03_Bewerbungen"
    )
    manifest_filename: str = "manifest.yaml"
    llm_model: str = "ollama:devstral-small-2:24b-cloud"
    git_init: bool = True
    cookiecutter_template: Path = Path("~/.config/jobtools/cookiecutter-jobapp")

    @field_validator("base_path", "cookiecutter_template", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    @property
    def manifest_path(self) -> Path:
        return self.base_path / self.manifest_filename


settings = Settings()