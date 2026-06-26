# CODING.md

## Python version
Latest stable Alpine variant. Declare in `pyproject.toml`.

## Language
Code, docstrings and comments in **English**.
Exception: error messages returned to the client in **Spanish**.

## Naming
Follow PEP 8 plus:
- Protected: `_single_leading_underscore`
- Private: `__double_leading_underscore`
- Booleans: `is_`, `has_`, `should_` prefix

**Reverse notation** — sequence is module_action_resource_type:
`elements_active` not `active_elements` → `GameCreateUseCase`, `game_create()`, `game_dict`

**Domain simplicity / Import aliasing** — name every class simply inside its own module. Add context only when importing it elsewhere using `as`. This keeps definitions clean and makes the role of each symbol explicit at the call site.

Suffixes by type:

| Type | Defined as | Imported as |
|---|---|---|
| Domain entity | `Game` | `Game as GameEntity` |
| Domain use-case interface (ABC) | `Game` | `Game as GameUsecase` |
| Application use-case (concrete) | `Game` | `Game as GameUsecase` |
| Domain repository interface (ABC) | `Game` | `Game as GameRepository` |
| Service (FastAPI dependency) | `game` | `game as game_service` |
| DTO | `GameOutput` | `GameOutput as GameOutputDTO` |

```python
# src/domain/game/entity.py
@dataclass
class Game: ...

# src/domain/game/usecase.py
class Game(ABC): ...

# src/domain/game/repository.py
class Game(ABC): ...

# src/application/game/usecase.py
from src.domain.game.usecase import Game as GameUsecase
from src.domain.game.entity import Game as GameEntity

class Game(GameUsecase): ...

# src/infrastructure/game/memory_repository.py
from src.domain.game.repository import Game as GameRepository

class InMemoryGameRepository(GameRepository): ...

# src/application/game/service.py
from src.domain.game.repository import Game as GameRepository

@lru_cache
def repository() -> GameRepository:
    return InMemoryGameRepository()

def game() -> Game: ...

# src/presentation/api/resources/game/dtos.py
from src.domain.game.entity import Game as GameEntity  # avoids collision with DTO class

class GameOutput(BaseModel):
    @classmethod
    def from_entity(cls, entity: GameEntity) -> "GameOutput": ...

# src/presentation/api/resources/game/routes.py
from src.application.game.service import game as game_service
from src.application.game.usecase import Game as GameUsecase
from src.domain.game.repository import Game as GameRepository
from src.presentation.api.resources.game.dtos import GameOutput as GameOutputDTO

async def start_game(
    usecase: Annotated[GameUsecase, Depends(game_service)],
) -> GameOutputDTO: ...
```

The rule also resolves name collisions: when a DTO and a domain entity share a name, import the entity as `...Entity` inside the DTO module.

## Indentation
4 spaces. Never tabs.

## Imports
Three sections separated by blank line: stdlib → third-party → local.

## Type hints
Mandatory on all public signatures: `def find_user(user_id: str) -> User | None`

## Docstrings
Google style, in English. Document args, returns, raises.

## Return types
Consistent return type. If nullable, declare as `X | None`. Prefer typed objects over dicts or tuples.

## Error handling
- Specific exceptions, never bare `except` or `except Exception` (except at app boundary).
- Fail-fast: validate input early.
- Custom exceptions for domain errors.
- Never `except: pass`.

## Logging
`logger = logging.getLogger(__name__)`. Never `print`. Don't log sensitive data.

## Security
- Never `eval`/`exec` on external input.
- Never `pickle` on untrusted data, use `json`.
- Secrets via env vars, never hardcoded.
- `with` for all resources.

## Testing
- `pytest`. Descriptive names: `test_parse_raises_on_empty_input`.
- Cover: happy path + edge cases + errors.
- Test each use case independently.
- Mock external dependencies (DB, storage).

## General
`ruff` or `black`. Lines ~88-100 chars. No dead code or unresolved `TODO`s. Comment the *why*, not the *what*.
