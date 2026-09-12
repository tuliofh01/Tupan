// Tupan, Máquina de Chuva — carcaça paramétrica (OpenSCAD)
// Rode: openscad -o tupan.stl tupan.scad
wall = 0.4;  // espessura da parede (cm)
W = 34.0; D = 24.0; H = 32.0;

module carcaca() {
    difference() {
        cube([W, D, H]);
        translate([wall, wall, wall]) cube([W-2*wall, D-2*wall, H]);
    }
}

module pecas() {
    // ventoinhas
    translate([1.0, 4.0, 16.0]) cube([3.0, 14.0, 10.0]);
    // leito_CaCl2
    translate([5.0, 3.0, 8.0]) cube([16.0, 16.0, 12.0]);
    // vidraria
    translate([10.0, 6.0, 20.0]) cube([10.0, 10.0, 12.0]);
    // solenoide
    translate([8.0, 9.0, 6.0]) cube([16.0, 4.0, 2.0]);
    // filtro_mineral
    translate([22.0, 8.0, 8.0]) cube([5.0, 5.0, 9.0]);
    // bacia
    translate([27.0, 6.0, 4.0]) cube([12.0, 10.0, 8.0]);
    // arduino_e_sensores
    translate([5.0, 0.5, 26.0]) cube([12.0, 6.0, 3.0]);
}

carcaca();
pecas();
