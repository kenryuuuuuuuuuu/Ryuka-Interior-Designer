// World centimetres; dimensioned planks, staggered ends, filtered grain.
float a = radians(Angle);
float2 p = float2(P.x*cos(a)+P.y*sin(a), -P.x*sin(a)+P.y*cos(a));
float row = floor(p.y/Width);
float shift = frac(sin(row*127.1)*43758.5453)*Length;
float column = floor((p.x+shift)/Length);
float2 local = float2(frac((p.x+shift)/Length)*Length, frac(p.y/Width)*Width);
float seed = frac(sin(dot(float2(column,row),float2(12.9898,78.233)))*43758.5453);
float edge = min(min(local.x,Length-local.x),min(local.y,Width-local.y));
float aa = max(length(fwidth(p)),0.015);
float face = smoothstep(Seam*0.5-aa,Seam*0.5+aa,edge);
float phase = p.y*2.8 + 1.4*sin(p.x*0.027+seed*12) + 0.45*sin(p.x*0.081+seed*31);
float filtered = 1-saturate(fwidth(phase)*0.35);
float grain = 1 + 0.065*sin(phase)*filtered + 0.025*sin(phase*2.3+seed*7)*filtered;
float board = lerp(0.90,1.08,seed);
return lerp(0.60,board*grain,face);
