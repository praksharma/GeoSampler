// Ricardo Costa, July, 2022
// parameters
N=1.0;
lc=0.2/(1.5^(N-1));
cx=0.0;
cy=0.0;
cz=0.0;
r=1.0;
// points
Point(1)={cx,cy,0.0,lc};
Point(2)={cx-r,cy,cz,lc};
Point(3)={cx,cy+r,cz,lc};
Point(4)={cx+r,cy,cz,lc};
Point(5)={cx,cy-r,cz,lc};
Point(6)={cx,cy,cz+r,lc};
Point(7)={cx,cy,cz-r,lc};
// lines
Circle(1)={2,1,3};
Circle(2)={3,1,4};
Circle(3)={4,1,5};
Circle(4)={2,1,5};
Circle(5)={5,1,6};
Circle(6)={3,1,6};
Circle(7)={3,1,7};
Circle(8)={5,1,7};
Circle(9)={2,1,6};
Circle(10)={4,1,6};
Circle(11)={4,1,7};
Circle(12)={2,1,7};
// line loops
Line Loop(1)={1,7,-12};
Line Loop(2)={12,-8,-4};
Line Loop(3)={4,5,-9};
Line Loop(4)={9,-6,-1};
Line Loop(5)={2,11,-7};
Line Loop(6)={-11,3,8};
Line Loop(7)={-3,10,-5};
Line Loop(8)={-10,-2,6};
// surfaces
Surface(1)={1};
Surface(2)={2};
Surface(3)={3};
Surface(4)={4};
Surface(5)={5};
Surface(6)={6};
Surface(7)={7};
Surface(8)={8};
// surface loops
Surface Loop(1)={1,2,3,4,5,6,7,8};
// volumes
Volume(1)={1};
// physicals
Physical Point(1)={2:7};
Physical Line(1)={1:12};
Physical Surface(1)={1:8};
Physical Volume(100)={1};
// mesh options
Mesh.Algorithm=5;
Mesh.Algorithm3D=1;
Mesh.OptimizeNetgen=1;
Mesh.Format=1;
Mesh.MshFileVersion=2.0;
// end of file
