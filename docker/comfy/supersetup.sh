# Adicionar verificações de erro
if ! docker-compose -f docker-compose.yml build; then
    print_error "Falha na construção dos containers"
    exit 1
fi

if ! docker-compose -f docker-compose.yml up -d; then
    print_error "Falha ao iniciar os containers"
    # Rollback parcial
    docker-compose -f docker-compose.yml down
    exit 1
fi 