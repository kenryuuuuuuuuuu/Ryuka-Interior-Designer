// UVs encode metres along the surface; one UV unit is one metre.
float a = radians(Angle);
float2 p = 100 * float2(UV.x*cos(a)+UV.y*sin(a),-UV.x*sin(a)+UV.y*cos(a));
float2 cell = floor(p/float2(Length,Width));
float2 q = frac(p/float2(Length,Width))*float2(Length,Width);
float edge = min(min(q.x,Length-q.x),min(q.y,Width-q.y));
float aa = max(length(fwidth(p)),0.01);
float face = smoothstep(Seam*0.5-aa,Seam*0.5+aa,edge);
float seed = frac(sin(dot(cell,float2(12.9898,78.233)))*43758.5453);
float phase = p.y*2.2+0.8*sin(p.x*.035+seed*13);
float filtered = 1-saturate(fwidth(phase)*.4);
float grain = 1+.035*sin(phase)*filtered;
float stone = 1+.012*sin(p.x*.3)*sin(p.y*.25);
float variation = lerp(.97,1.03,seed);
return lerp(Mode>0.5 ? .62 : .84,variation*(Mode>0.5 ? grain : stone),face);
