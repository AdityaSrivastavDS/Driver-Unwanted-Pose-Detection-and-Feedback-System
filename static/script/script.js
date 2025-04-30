document.addEventListener("DOMContentLoaded", function () {
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({ canvas: document.getElementById("bgCanvas"), alpha: true });

    renderer.setSize(window.innerWidth, window.innerHeight);
    document.body.appendChild(renderer.domElement);

    const geometry = new THREE.TorusGeometry(6, 1, 16, 100);
    const material = new THREE.MeshBasicMaterial({ color: 0xff007f, wireframe: true });
    const torus = new THREE.Mesh(geometry, material);
    
    scene.add(torus);
    camera.position.z = 20;

    function animate() {
        requestAnimationFrame(animate);
        torus.rotation.x += 0.005;
        torus.rotation.y += 0.005;
        renderer.render(scene, camera);
    }

    animate();
});
