document.addEventListener("DOMContentLoaded", function () {
    console.log("Script Loaded");

    document.querySelectorAll(".card").forEach(card => {
        card.addEventListener("mousemove", (e) => {
            let xAxis = (window.innerWidth / 2 - e.pageX) / 25;
            let yAxis = (window.innerHeight / 2 - e.pageY) / 25;
            card.style.transform = `rotateY(${xAxis}deg) rotateX(${yAxis}deg)`;
        });

        card.addEventListener("mouseenter", () => {
            card.style.transition = "none";
        });

        card.addEventListener("mouseleave", () => {
            card.style.transition = "transform 0.5s ease";
            card.style.transform = "rotateY(0deg) rotateX(0deg)";
        });
    });
});