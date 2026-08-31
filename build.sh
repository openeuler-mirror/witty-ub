#!/bin/bash

set -e

BASE_IMAGE="witty-ub-base:latest"
APP_IMAGE="witty-ub:latest"
REGISTRY=""
PLATFORM="local"
USE_RPM="false"
RPM_ROLE="all"
REPO_URL=""
VERSION="latest"

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --multi        Build multi-architecture image (x86_64 + arm64)"
    echo "  --registry     Specify registry for multi-arch push (required with --multi)"
    echo "  --platform     Target platform: local, linux/amd64, linux/arm64"
    echo "  --rpm          Build image using RPM package (instead of source code)"
    echo "  --rpm-role     Image role with --rpm: all, backend, frontend (default: all)"
    echo "  --repo-url     Specify custom RPM repository URL (used with --rpm)"
    echo "  --version      Specify image tag version (default: latest)"
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
        --rpm)
            USE_RPM="true"
            shift
            ;;
        --rpm-role)
            RPM_ROLE="$2"
            shift 2
            ;;
        --repo-url)
            REPO_URL="$2"
            shift 2
            ;;
        --version)
            VERSION="$2"
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

if [ "$USE_RPM" = "true" ] && [ -z "$REPO_URL" ]; then
    echo "Error: --repo-url is required when building with --rpm"
    echo "       Example: --repo-url http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/<子目录>"
    show_usage
    exit 1
fi

case "$RPM_ROLE" in
    all|backend|frontend) ;;
    *)
        echo "Error: invalid --rpm-role '$RPM_ROLE' (expected: all|backend|frontend)"
        exit 1
        ;;
esac

# Check buildx availability
HAS_BUILDX=false
if docker buildx version >/dev/null 2>&1; then
    HAS_BUILDX=true
fi

create_builder() {
    BUILDKIT_CONFIG="$(dirname "$0")/buildkitd.toml"
    if [ -f "$BUILDKIT_CONFIG" ]; then
        BUILDKIT_CONFIG_ARG="--config $BUILDKIT_CONFIG"
    else
        BUILDKIT_CONFIG_ARG=""
    fi

    if docker buildx ls | grep -q witty-ub-builder; then
        echo "Removing existing builder to apply new config..."
        docker buildx rm witty-ub-builder
    fi

    echo "Creating buildx builder..."
    eval docker buildx create --name witty-ub-builder $BUILDKIT_CONFIG_ARG --use
    docker buildx inspect --bootstrap
}

if [ "$PLATFORM" = "linux/amd64,linux/arm64" ]; then
    if [ "$HAS_BUILDX" = "false" ]; then
        echo "Error: Multi-architecture build requires docker buildx (Docker 19.03+)"
        echo "       Alternative: build on each architecture separately and push to the same registry tag"
        exit 1
    fi
    create_builder
else
    if [ "$HAS_BUILDX" = "true" ]; then
        echo "Using default builder for build (can access local images)"
        docker buildx use default
    else
        echo "buildx not available, using docker build directly"
        if [ "$PLATFORM" != "local" ]; then
            echo "Warning: --platform requires buildx, falling back to local build"
            PLATFORM="local"
        fi
    fi
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
            REGISTRY_HOST="${REGISTRY%/*}"
            REPO_NAME="${REGISTRY##*/}"
            target_image="${REGISTRY_HOST}/${REPO_NAME}-base:${VERSION}"
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
                -t "$target_image" \
                -t "$BASE_IMAGE" .
        fi
    fi
}

build_web() {
    echo ""
    echo "============================================"
    echo "Building web frontend locally"
    echo "============================================"

    if [ ! -d "src/web" ]; then
        echo "Error: src/web directory not found"
        exit 1
    fi

    cd src/web

    echo "Ensuring npm dependencies are installed..."
    npm install

    echo "Building frontend..."
    export HUSKY=0
    npm run build-only

    if [ ! -d "dist" ]; then
        echo "Error: Frontend build failed, dist directory not created"
        exit 1
    fi

    cd ../..
}

build_app() {
    echo ""
    echo "============================================"
    echo "Building application image: $APP_IMAGE"
    echo "Platform: $PLATFORM"
    echo "============================================"

    build_web

    if [ "$PLATFORM" = "local" ]; then
        docker build -f Dockerfile -t "$APP_IMAGE" .
    else
        target_image="$APP_IMAGE"
        build_args=""
        
        if [ -n "$REGISTRY" ]; then
            target_image="$REGISTRY:${VERSION}"
            REGISTRY_HOST="${REGISTRY%/*}"
            REPO_NAME="${REGISTRY##*/}"
            base_image_reg="${REGISTRY_HOST}/${REPO_NAME}-base:${VERSION}"
            build_args="--build-arg BASE_IMAGE=${base_image_reg}"
        fi

        if [ "$PLATFORM" = "linux/amd64,linux/arm64" ]; then
            eval docker buildx build \
                --platform "$PLATFORM" \
                --push \
                $build_args \
                -f Dockerfile \
                -t "$target_image" .
        else
            docker buildx build \
                --platform "$PLATFORM" \
                --load \
                $build_args \
                -f Dockerfile \
                -t "$target_image" .
        fi
    fi
}

build_rpm() {
    echo ""
    echo "============================================"
    echo "Building RPM-based image: $APP_IMAGE (role: $RPM_ROLE)"
    echo "Platform: $PLATFORM"
    echo "============================================"

    target_image="$APP_IMAGE"
    if [ "$RPM_ROLE" != "all" ]; then
        target_image="${APP_IMAGE%:*}:$RPM_ROLE"
    fi
    if [ -n "$REGISTRY" ]; then
        target_image="$REGISTRY:${VERSION}"
        if [ "$RPM_ROLE" != "all" ]; then
            target_image="$REGISTRY:$RPM_ROLE"
        fi
    fi

    REPO_URL_FULL="${REPO_URL%/}/everything/\$basearch/"
    build_args="--build-arg REPO_URL=\"$REPO_URL_FULL\""

    if [ "$PLATFORM" = "local" ]; then
        eval docker build $build_args --target "$RPM_ROLE" -f Dockerfile.rpm -t "$target_image" .
    elif [ "$PLATFORM" = "linux/amd64,linux/arm64" ]; then
        eval docker buildx build \
            $build_args \
            --target "$RPM_ROLE" \
            --platform "$PLATFORM" \
            --push \
            -f Dockerfile.rpm \
            -t "$target_image" .
    else
        eval docker buildx build \
            $build_args \
            --target "$RPM_ROLE" \
            --platform "$PLATFORM" \
            --load \
            -f Dockerfile.rpm \
            -t "$target_image" .
    fi
}

if [ "$USE_RPM" = "true" ]; then
    build_rpm
else
    build_base
    build_app
fi

echo ""
echo "============================================"
echo "Build completed successfully!"
echo "App image: $APP_IMAGE"
echo "Platform: $PLATFORM"
echo "Version: $VERSION"
echo "Build method: $(if [ "$USE_RPM" = "true" ]; then echo "RPM"; else echo "Source"; fi)"
if [ -n "$REGISTRY" ]; then
    echo "Registry: $REGISTRY"
fi
echo "============================================"
