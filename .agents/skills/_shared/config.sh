#!/bin/bash

# 配置加载脚本
# 加载和管理项目配置文件

# 加载部署配置
load_deploy_config() {
    local project_root=$(get_project_root)
    local config_file="$project_root/scripts/deploy.env"

    if [ -f "$config_file" ]; then
        source "$config_file"
        log_debug "已加载部署配置: $config_file"
        return 0
    else
        log_warning "配置文件不存在: $config_file"
        log_info "使用默认配置或环境变量"
        return 1
    fi
}

# 获取数据库配置
get_db_config() {
    # 从环境变量或 alembic.ini 读取
    # 优先使用环境变量
    if [ -n "$DATABASE_URL" ]; then
        echo "$DATABASE_URL"
    else
        # 默认配置
        echo "postgresql://hospital:password@localhost:5432/hospital"
    fi
}

# 获取 Redis 配置
get_redis_config() {
    if [ -n "$REDIS_URL" ]; then
        echo "$REDIS_URL"
    else
        echo "redis://localhost:6379/0"
    fi
}

# 获取后端 API 配置
get_api_config() {
    local env=${1:-local}

    case "$env" in
        production)
            echo "https://api.hospital.example.com"
            ;;
        staging)
            echo "https://api-staging.hospital.example.com"
            ;;
        *)
            echo "http://localhost:8000"
            ;;
    esac
}

# 获取应用端口配置
get_app_port() {
    local app=$1

    case "$app" in
        admin)
            echo "8005"
            ;;
        patient-h5)
            echo "8002"
            ;;
        doctor)
            echo "8003"
            ;;
        server)
            echo "8000"
            ;;
        *)
            echo ""
            ;;
    esac
}

# 检查环境配置
check_env_config() {
    local env=${1:-local}

    case "$env" in
        production|staging)
            if [ ! -f "scripts/deploy.env" ]; then
                log_error "生产/测试环境需要配置 scripts/deploy.env"
                return 1
            fi
            ;;
    esac
    return 0
}

# 获取 Docker 配置
get_docker_compose_file() {
    local project_root=$(get_project_root)
    local env=${1:-local}

    if [ "$env" = "production" ]; then
        echo "$project_root/docker-compose.prod.yml"
    else
        echo "$project_root/docker-compose.yml"
    fi
}

# 导出函数
export -f load_deploy_config get_db_config get_redis_config
export -f get_api_config get_app_port check_env_config
export -f get_docker_compose_file
