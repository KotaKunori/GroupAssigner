from injector import Module, provider, singleton, Injector


class ProvideUserRepositoryModule(Module):
    @singleton
    @provider
    def provideUserRepository(self) -> UserRepositoryInterface:
        return UserRepository()
    
injector = Injector([
    ProvideUserRepositoryModule,
])