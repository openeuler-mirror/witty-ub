#!/bin/bash

set -e

BASE_IMAGE="witty-ub-base:latest"
APP_IMAGE="witty-ub:latest"
REGISTRY=""
PLATFORM="local"

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --multi        Build multi-architecture image (x86_64 + arm64)"
    echo "  --registry     Specify registry for multi-arch push (required with --multi)"
    echo "  --platform     Target platform: local, linux/amd64, linux/arm64"
    echo "  -h, --help     Show this help message"
}

while [ $# -gt 0 ]; do
    case "$1" in
        --multi)
            PLATFORM="linux/amd64,linux/arm64"
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

if [ "$PLATFORM" = "linux/amd64,linux/arm64" ] && [ -z "$REGISTRY" ]; then
    echo "Error: --registry is required when building multi-architecture images"
    show_usage
    exit 1
fi

create_builder() {
    if ! docker buildx ls | grep -q witty-ub-builder; then
        echo "Creating buildx builder..."
        docker buildx create --name witty-ub-builder --use
        docker buildx inspect --bootstrap
    else
        docker buildx use witty-ub-builder
    fi
}

if [ "$PLATFORM" != "local" ]; then
    create_builder
fi

build_base() {
    echo "============================================"
    echo "Building base image: $BASE_IMAGE"
    echo "Platform: $PLATFORM"
    echo "============================================"

    if [ "$PLATFORM" = "local" ]; then
        docker build -f Dockerfile.base -t "$BASE_IMAGE" .
    else
        target_image="$BASE_IMAGE"
        if [ -n "$REGISTRY" ]; then
            target_image="$REGISTRY/$BASE_IMAGE"
        fi

        if [ "$PLATFORM" = "linux/amd64,linux/arm64" ]; then
            docker buildx build \
                --platform "$PLATFORM" \
                --push \
                -f Dockerfile.base \
                -t "$target_image" .
        else
            docker buildx build \
                --platform "$PLATFORM" \
                --load \
                -f Dockerfile.base \
                -t "$target_image" .
        fi
    fi
}

build_app() {
    echo ""
    echo "============================================"
    echo "Building application image: $APP_IMAGE"
    echo "Platform: $PLATFORM"
    echo "============================================"

    if [ "$PLATFORM" = "local" ]; then
        docker build -f Dockerfile -t "$APP_IMAGE" .
    else
        target_image="$APP_IMAGE"
        if [ -n "$REGISTRY" ]; then
            target_image="$REGISTRY/$APP_IMAGE"
        fi

        if [ "$PLATFORM" = "linux/amd64,linux/arm64" ]; then
            docker buildx build \
                --platform "$PLATFORM" \
                --push \
                -f Dockerfile \
                -t "$target_image" .
        else
            docker buildx build \
                --platform "$PLATFORM" \
                --load \
                -f Dockerfile \
                -t "$target_image" .
        fi
    fi
}

build_base
build_app

echo ""
echo "============================================"
echo "Build completed successfully!"
echo "Base image: $BASE_IMAGE"
echo "App image: $APP_IMAGE"
echo "Platform: $PLATFORM"
echo "============================================"