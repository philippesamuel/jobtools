from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_GDRIVE = (
    "~/Library/CloudStorage/GoogleDrive-philippe.sa.costa@gmail.com/My Drive"
)
_ZEUGNISSE = f"{_GDRIVE}/03_Work/01_Zeugnisse"

_DEFAULT_ATTACHMENTS: dict[str, str] = {
    "BASF_Praktikantenzeugnis_2020.pdf": (
        f"{_ZEUGNISSE}/03_Arbeitszeugnisse/2020_BASF_Praktikumszeignis.pdf"
    ),
    "BASF_Zeugnis_2022-2024.pdf": (
        f"{_ZEUGNISSE}/03_Arbeitszeugnisse/2022-2024_BASF_Arbeitszeugnis.pdf"
    ),
    "TUBerlin_Zeugnis_MSc.pdf": (
        f"{_ZEUGNISSE}/02_TUB Zeugnisse/2021_TUB_Zeugnis_Msc.pdf"
    ),
    "UFMG_Zeugnis_DE_PT.pdf": (
        f"{_ZEUGNISSE}/10_Translated and Signed Documents/Abschluss_original+Deutsch.pdf"
    ),
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="JT_",
    )

    base_path: Path = Path(f"{_GDRIVE}/03_Work/03_Bewerbungen")
    manifest_filename: str = "manifest.yaml"
    llm_model: str = "ollama:devstral-small-2:24b-cloud"
    git_init: bool = True
    review: bool = True
    cookiecutter_template: Path = Path("~/.config/jobtools/cookiecutter-jobapp")

    awesome_cv_dir: Path = Path("~/Developer/philippe-awesome-cv")
    # link_name → absolute target path (expanduser applied at runtime)
    attachments: dict[str, str] = _DEFAULT_ATTACHMENTS

    @field_validator("base_path", "cookiecutter_template", "awesome_cv_dir", mode="before")
    @classmethod
    def expand_path(cls, v: str | Path) -> Path:
        return Path(v).expanduser().resolve()

    @property
    def manifest_path(self) -> Path:
        return self.base_path / self.manifest_filename

    @property
    def assets_path(self) -> Path:
        return self.awesome_cv_dir / "assets"

    @property
    def awesome_cv_cls_path(self) -> Path:
        return self.awesome_cv_dir / "awesome-cv.cls"


settings = Settings()