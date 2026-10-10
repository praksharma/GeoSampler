// Ricardo Costa, July, 2022
// parameters
N=1.0;
cx=0.0;
cy=0.0;
r1=0.5;
r2=1.0;
lc=0.1/N;
lc1=lc*r1;
lc2=lc*r2;
// points
Point(1)={cx-r1,cy,0.0,lc1};
Point(2)={cx,cy+r1,0.0,lc1};
Point(3)={cx+r1,cy,0.0,lc1};
Point(4)={cx,cy-r1,0.0,lc1};
Point(5)={cx,cy,0.0,lc1};
Point(6)={cx-r2,cy,0.0,lc2};
Point(7)={cx,cy+r2,0.0,lc2};
Point(8)={cx+r2,cy,0.0,lc2};
Point(9)={cx,cy-r2,0.0,lc2};
Point(10)={cx,cy,0.0,lc2};
// lines
Circle(1)={1,5,2};
Circle(2)={2,5,3};
Circle(3)={3,5,4};
Circle(4)={4,5,1};
Circle(5)={6,10,7};
Circle(6)={7,10,8};
Circle(7)={8,10,9};
Circle(8)={9,10,6};
// line loops
Line Loop(1)={1,2,3,4};
Line Loop(2)={5,6,7,8};
// surfaces
Plane Surface(1)={1,2};
// physicals
Physical Point(1)={1:5};
Physical Point(2)={6:10};
Physical Line(1)={1:4};
Physical Line(2)={5:8};
Physical Surface(100)={1};
// mesh options
Mesh.Algorithm=5;
Mesh.Algorithm3D=1;
Mesh.OptimizeNetgen=1;
Mesh.Format=1;
Mesh.MshFileVersion=2.0;
// end of file
