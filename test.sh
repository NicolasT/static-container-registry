# This file is to be executed using `bash_unit`

DOCKER=${DOCKER:-$(command -v docker)}
SKOPEO=${SKOPEO:-$(command -v skopeo)}
CRICTL=${CRICTL:-$(command -v crictl)}
IMAGE=${IMAGE:-nicolast/static-container-registry:test}
IMAGES=/tmp/images
CONTAINER_NAME=static-container-registry-test
REGISTRY_HOST=127.0.0.1
REGISTRY_PORT=5000
REGISTRY="$REGISTRY_HOST:$REGISTRY_PORT"

test_docker() {
        for image in ${AVAILABLE_IMAGES[*]}; do
                assert "$DOCKER pull '$REGISTRY/$image'"
        done
}

# containerd relies on the `Docker-Content-Digest` header...
todo_containerd() {
        for image in ${AVAILABLE_IMAGES[*]}; do
                sudo ${CRICTL} --image-endpoint unix:///run/containerd/containerd.sock pull "$REGISTRY_HOST/$image"
                sudo journalctl -u containerd
                assert false
        done
}

test_skopeo() {
        for image in ${AVAILABLE_IMAGES[*]}; do
                assert "$SKOPEO --debug inspect --tls-verify=false 'docker://$REGISTRY/$image'"
        done
}

setup_suite() {
        assert build_project_image
        assert create_images_directory
}

teardown_suite() {
        remove_images_directory
        delete_project_image
}

setup() {
        $DOCKER run \
                -d \
                -p "$REGISTRY:80" \
                -v "$IMAGES:/var/lib/images:ro" \
                --name "$CONTAINER_NAME" \
                "$IMAGE" > /dev/null
}

teardown() {
        $DOCKER stop "$CONTAINER_NAME" > /dev/null
        $DOCKER rm "$CONTAINER_NAME" > /dev/null
}

build_project_image() {
        $DOCKER build -t "$IMAGE" .
}

delete_project_image() {
        $DOCKER rmi "$IMAGE" > /dev/null
}

AVAILABLE_IMAGES=(
    'alpine:3.9.3'
    'alpine:3.9'
    'alpine:3.8.4'
    'metalk8s-keepalived:latest'
)
create_images_directory() {
        mkdir "$IMAGES" "$IMAGES/alpine" "$IMAGES/metalk8s-keepalived"
        $SKOPEO copy --format v2s2 --dest-compress \
                docker://docker.io/alpine:3.9.3 \
                "dir:$IMAGES/alpine/3.9.3"
        $SKOPEO copy --format v2s2 --dest-compress \
                docker://docker.io/alpine:3.9 \
                "dir:$IMAGES/alpine/3.9"
        $DOCKER pull docker.io/alpine:3.8.4
        $SKOPEO copy --format v2s2 --dest-compress \
                docker-daemon:alpine:3.8.4 \
                "dir:$IMAGES/alpine/3.8.4"
        $DOCKER rmi docker.io/alpine:3.8.4
        $SKOPEO copy --format v2s2 --dest-compress \
                docker://docker.io/nicolast/metalk8s-keepalived:latest \
                "dir:$IMAGES/metalk8s-keepalived/latest"
}

remove_images_directory() {
        rm -rf "$IMAGES"
}
