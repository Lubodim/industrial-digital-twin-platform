import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

const DEFAULT_OPTIONS = Object.freeze({
    backgroundColor: 0x1f262e,
    modelColor: 0x8fa6b8,
    autoRotate: false,
    autoRotateSpeed: 1.0,
    rotationDirection: 1,
    enableDamping: true,
    dampingFactor: 0.08,
    showGrid: true,
    showAxes: false,
});

export class LocalStlViewer {
    constructor(container, options = {}) {
        if (!(container instanceof HTMLElement)) {
            throw new TypeError("LocalStlViewer requires a valid HTML container.");
        }

        this.container = container;
        this.options = { ...DEFAULT_OPTIONS, ...options };
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.controls = null;
        this.model = null;
        this.grid = null;
        this.axes = null;
        this.animationFrameId = null;
        this.resizeObserver = null;
        this.isDisposed = false;
        this.isLoaded = false;
        this.isAutoRotating = Boolean(this.options.autoRotate);
        this.rotationDirection = this.options.rotationDirection >= 0 ? 1 : -1;
        this.initialCameraPosition = new THREE.Vector3(3, 2, 3);
        this.initialTarget = new THREE.Vector3(0, 0, 0);
        this.changeCallbacks = new Set();
        this.loadCallbacks = new Set();
        this.errorCallbacks = new Set();

        this.initialize();
    }

    initialize() {
        this.createScene();
        this.createCamera();
        this.createRenderer();
        this.createLights();
        this.createHelpers();
        this.createControls();
        this.observeSize();
        this.animate();
    }

    createScene() {
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(this.options.backgroundColor);
    }

    createCamera() {
        const { width, height } = this.getContainerSize();

        this.camera = new THREE.PerspectiveCamera(
            45,
            width / height,
            0.01,
            100000,
        );

        this.camera.position.copy(this.initialCameraPosition);
    }

    createRenderer() {
        this.renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: false,
            powerPreference: "high-performance",
        });

        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
        this.renderer.outputColorSpace = THREE.SRGBColorSpace;
        this.renderer.setSize(
            this.getContainerSize().width,
            this.getContainerSize().height,
            false,
        );

        this.renderer.domElement.classList.add("stl-viewer-canvas");
        this.renderer.domElement.setAttribute("aria-label", "Интерактивен 3D модел");
        this.container.replaceChildren(this.renderer.domElement);
    }

    createLights() {
        const ambientLight = new THREE.HemisphereLight(0xffffff, 0x334455, 1.8);
        this.scene.add(ambientLight);

        const keyLight = new THREE.DirectionalLight(0xffffff, 2.4);
        keyLight.position.set(4, 6, 5);
        this.scene.add(keyLight);

        const fillLight = new THREE.DirectionalLight(0x9fc5ff, 1.2);
        fillLight.position.set(-4, 2, -3);
        this.scene.add(fillLight);

        const bottomLight = new THREE.DirectionalLight(0xffffff, 0.7);
        bottomLight.position.set(0, -5, 2);
        this.scene.add(bottomLight);
    }

    createHelpers() {
        if (this.options.showGrid) {
            this.grid = new THREE.GridHelper(10, 10, 0x557080, 0x33414c);
            this.grid.material.transparent = true;
            this.grid.material.opacity = 0.35;
            this.scene.add(this.grid);
        }

        if (this.options.showAxes) {
            this.axes = new THREE.AxesHelper(2);
            this.scene.add(this.axes);
        }
    }

    createControls() {
        this.controls = new OrbitControls(this.camera, this.renderer.domElement);
        this.controls.enableDamping = this.options.enableDamping;
        this.controls.dampingFactor = this.options.dampingFactor;
        this.controls.enablePan = true;
        this.controls.enableZoom = true;
        this.controls.enableRotate = true;
        this.controls.screenSpacePanning = true;
        this.controls.minDistance = 0.01;
        this.controls.maxDistance = 100000;
        this.controls.target.copy(this.initialTarget);
        this.controls.update();

        this.controls.addEventListener("change", () => {
            const state = this.getViewState();
            this.changeCallbacks.forEach((callback) => callback(state, this));
        });
    }

    async load(url) {
        if (!url) {
            throw new Error("Липсва адрес на STL файла.");
        }

        this.setLoadingState(true);

        try {
            const geometry = await new STLLoader().loadAsync(url);

            geometry.computeVertexNormals();
            geometry.computeBoundingBox();
            geometry.computeBoundingSphere();

            this.removeCurrentModel();
            this.centerGeometry(geometry);

            const material = new THREE.MeshStandardMaterial({
                color: this.options.modelColor,
                metalness: 0.28,
                roughness: 0.62,
                side: THREE.DoubleSide,
            });

            this.model = new THREE.Mesh(geometry, material);
            this.model.castShadow = false;
            this.model.receiveShadow = false;
            this.scene.add(this.model);

            this.fitCameraToModel();
            this.isLoaded = true;
            this.setLoadingState(false);
            this.loadCallbacks.forEach((callback) => callback(this));
        } catch (error) {
            this.isLoaded = false;
            this.setLoadingState(false);
            this.showError("3D моделът не може да бъде зареден.");
            this.errorCallbacks.forEach((callback) => callback(error, this));
            throw error;
        }

        return this;
    }

    centerGeometry(geometry) {
        geometry.computeBoundingBox();

        if (!geometry.boundingBox) {
            return;
        }

        const center = geometry.boundingBox.getCenter(new THREE.Vector3());
        geometry.translate(-center.x, -center.y, -center.z);
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();
    }

    fitCameraToModel() {
        if (!this.model) {
            return;
        }

        const boundingBox = new THREE.Box3().setFromObject(this.model);
        const size = boundingBox.getSize(new THREE.Vector3());
        const center = boundingBox.getCenter(new THREE.Vector3());
        const maximumDimension = Math.max(size.x, size.y, size.z) || 1;
        const verticalFieldOfView = THREE.MathUtils.degToRad(this.camera.fov);
        const distance = (maximumDimension / (2 * Math.tan(verticalFieldOfView / 2))) * 1.55;

        this.initialTarget.copy(center);
        this.initialCameraPosition.set(
            center.x + distance,
            center.y + distance * 0.65,
            center.z + distance,
        );

        this.camera.near = Math.max(maximumDimension / 1000, 0.001);
        this.camera.far = Math.max(maximumDimension * 1000, 1000);
        this.camera.position.copy(this.initialCameraPosition);
        this.camera.updateProjectionMatrix();

        this.controls.target.copy(this.initialTarget);
        this.controls.minDistance = Math.max(maximumDimension * 0.05, 0.001);
        this.controls.maxDistance = Math.max(maximumDimension * 50, 100);
        this.controls.update();

        if (this.grid) {
            const gridScale = Math.max(maximumDimension / 10, 0.1);
            this.grid.scale.setScalar(gridScale);
            this.grid.position.y = boundingBox.min.y;
        }
    }

    resetView() {
        this.camera.position.copy(this.initialCameraPosition);
        this.controls.target.copy(this.initialTarget);
        this.camera.up.set(0, 1, 0);
        this.controls.update();
        return this;
    }

    setPresetView(viewName) {
        if (!this.model) {
            return this;
        }

        const boundingBox = new THREE.Box3().setFromObject(this.model);
        const size = boundingBox.getSize(new THREE.Vector3());
        const center = boundingBox.getCenter(new THREE.Vector3());
        const distance = Math.max(size.x, size.y, size.z, 1) * 2.2;

        const positions = {
            front: new THREE.Vector3(center.x, center.y, center.z + distance),
            back: new THREE.Vector3(center.x, center.y, center.z - distance),
            left: new THREE.Vector3(center.x - distance, center.y, center.z),
            right: new THREE.Vector3(center.x + distance, center.y, center.z),
            top: new THREE.Vector3(center.x, center.y + distance, center.z),
            bottom: new THREE.Vector3(center.x, center.y - distance, center.z),
            isometric: new THREE.Vector3(
                center.x + distance,
                center.y + distance * 0.75,
                center.z + distance,
            ),
        };

        const selectedPosition = positions[viewName] || positions.isometric;

        this.camera.position.copy(selectedPosition);
        this.camera.up.set(0, 1, 0);
        this.controls.target.copy(center);
        this.controls.update();

        return this;
    }

    startAutoRotate() {
        this.isAutoRotating = true;
        return this;
    }

    stopAutoRotate() {
        this.isAutoRotating = false;
        return this;
    }

    toggleAutoRotate() {
        this.isAutoRotating = !this.isAutoRotating;
        return this.isAutoRotating;
    }

    reverseRotation() {
        this.rotationDirection *= -1;
        return this.rotationDirection;
    }

    setRotationDirection(direction) {
        this.rotationDirection = direction >= 0 ? 1 : -1;
        return this;
    }

    getViewState() {
        return {
            cameraPosition: this.camera.position.clone(),
            cameraQuaternion: this.camera.quaternion.clone(),
            cameraUp: this.camera.up.clone(),
            target: this.controls.target.clone(),
        };
    }

    applyViewState(state, emitChange = false) {
        if (!state) {
            return this;
        }

        this.camera.position.copy(state.cameraPosition);
        this.camera.quaternion.copy(state.cameraQuaternion);
        this.camera.up.copy(state.cameraUp);
        this.controls.target.copy(state.target);

        if (emitChange) {
            this.controls.update();
        } else {
            this.controls.enabled = false;
            this.controls.update();
            this.controls.enabled = true;
        }

        return this;
    }

    onViewChange(callback) {
        if (typeof callback === "function") {
            this.changeCallbacks.add(callback);
        }

        return () => this.changeCallbacks.delete(callback);
    }

    onLoad(callback) {
        if (typeof callback === "function") {
            this.loadCallbacks.add(callback);
        }

        return () => this.loadCallbacks.delete(callback);
    }

    onError(callback) {
        if (typeof callback === "function") {
            this.errorCallbacks.add(callback);
        }

        return () => this.errorCallbacks.delete(callback);
    }

    setLoadingState(isLoading) {
        this.container.classList.toggle("is-loading", Boolean(isLoading));
    }

    showError(message) {
        const errorElement = document.createElement("div");
        errorElement.className = "stl-viewer-error";
        errorElement.textContent = message;
        this.container.appendChild(errorElement);
    }

    removeCurrentModel() {
        if (!this.model) {
            return;
        }

        this.scene.remove(this.model);
        this.model.geometry?.dispose();

        if (Array.isArray(this.model.material)) {
            this.model.material.forEach((material) => material.dispose());
        } else {
            this.model.material?.dispose();
        }

        this.model = null;
    }

    observeSize() {
        this.resizeObserver = new ResizeObserver(() => this.resize());
        this.resizeObserver.observe(this.container);
    }

    resize() {
        if (!this.renderer || !this.camera || this.isDisposed) {
            return;
        }

        const { width, height } = this.getContainerSize();

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();
        this.renderer.setSize(width, height, false);
    }

    getContainerSize() {
        return {
            width: Math.max(this.container.clientWidth, 320),
            height: Math.max(this.container.clientHeight, 320),
        };
    }

    animate() {
        if (this.isDisposed) {
            return;
        }

        this.animationFrameId = window.requestAnimationFrame(() => this.animate());

        if (this.model && this.isAutoRotating) {
            const speed = Number(this.options.autoRotateSpeed) || 1;
            this.model.rotation.y += 0.005 * speed * this.rotationDirection;
        }

        this.controls?.update();
        this.renderer?.render(this.scene, this.camera);
    }

    dispose() {
        this.isDisposed = true;

        if (this.animationFrameId) {
            window.cancelAnimationFrame(this.animationFrameId);
        }

        this.resizeObserver?.disconnect();
        this.controls?.dispose();
        this.removeCurrentModel();

        this.renderer?.dispose();
        this.renderer?.domElement.remove();

        this.changeCallbacks.clear();
        this.loadCallbacks.clear();
        this.errorCallbacks.clear();
    }
}

export function synchronizeViewers(firstViewer, secondViewer) {
    if (!(firstViewer instanceof LocalStlViewer) || !(secondViewer instanceof LocalStlViewer)) {
        throw new TypeError("synchronizeViewers requires two LocalStlViewer instances.");
    }

    let synchronizing = false;

    const synchronize = (source, target) => {
        if (synchronizing) {
            return;
        }

        synchronizing = true;
        target.applyViewState(source.getViewState());
        synchronizing = false;
    };

    const removeFirstListener = firstViewer.onViewChange(() => {
        synchronize(firstViewer, secondViewer);
    });

    const removeSecondListener = secondViewer.onViewChange(() => {
        synchronize(secondViewer, firstViewer);
    });

    return () => {
        removeFirstListener();
        removeSecondListener();
    };
}
