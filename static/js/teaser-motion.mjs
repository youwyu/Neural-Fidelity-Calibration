// Geometry and prescribed motion shared by all interactive domain samples.
export const SIDE = 12.8;
export function snowHeight(x, y) {
  return .075*Math.sin(1.8*x+.4)*Math.cos(1.7*y)+.032*Math.sin(4*x+2.3*y)
    +.16*Math.exp(-((x+.9)**2+(y-.75)**2)/.5)
    +.11*Math.exp(-((x-.85)**2+(y+.70)**2)/.4)
    -.07*Math.exp(-((x-.65)**2+(y-.50)**2)/.30)
    +.22*Math.exp(-((x+1.10)**2+(y-1.05)**2)/.20)
    +.18*Math.exp(-((x-1.05)**2+(y+1.08)**2)/.20);
}
export function groundHeight(x, y, index, depth) {
  const phase=index*.83, px=x*2.8/SIDE, py=y*2.8/SIDE;
  const hollow=Math.exp(-((px-.48*Math.cos(phase))**2+(py-.45*Math.sin(phase))**2)/.55);
  const compression=depth*(.42+.58*hollow)+(.018+.012*(index%3))*(1+Math.sin(2.5*px+phase)*Math.cos(2.1*py-phase));
  return snowHeight(x,y)-compression;
}
export function routeState(t, route) {
  const omega=route.direction*2*Math.PI*route.laps/32;
  const wave=omega*t+route.phase, q=wave+route.speed_modulation*Math.sin(wave);
  const dq=omega*(1+route.speed_modulation*Math.cos(wave));
  const ddq=-omega*omega*route.speed_modulation*Math.sin(wave);
  const [ax,ay]=route.amplitudes, c=Math.cos(route.rotation), s=Math.sin(route.rotation);
  const lx=ax*Math.sin(q), ly=ay*Math.sin(2*q);
  const vx=ax*Math.cos(q)*dq, vy=2*ay*Math.cos(2*q)*dq;
  const acx=ax*(-Math.sin(q)*dq*dq+Math.cos(q)*ddq);
  const acy=ay*(-4*Math.sin(2*q)*dq*dq+2*Math.cos(2*q)*ddq);
  const speed=Math.hypot(vx,vy);
  return {x:route.center[0]+c*lx-s*ly, y:route.center[1]+s*lx+c*ly,
    yaw:Math.atan2(s*vx+c*vy,c*vx-s*vy), speed, turn:(vx*acy-vy*acx)/(speed*speed)};
}
export function supportPose(state, ground) {
  const {x,y,yaw}=state, c=Math.cos(yaw), s=Math.sin(yaw);
  const corners=[[.131,.187795],[.131,-.187795],[-.131,.187795],[-.131,-.187795]];
  const heights=corners.map(([xx,yy])=>ground(x+c*xx-s*yy,y+s*xx+c*yy));
  const mean=heights.reduce((a,b)=>a+b,0)/4;
  const gx=(heights[0]+heights[1]-heights[2]-heights[3])/(4*.131);
  const gy=(heights[0]-heights[1]+heights[2]-heights[3])/(4*.187795);
  const wx=c*gx-s*gy, wy=s*gx+c*gy, norm=Math.hypot(wx,wy,1);
  const up=[-wx/norm,-wy/norm,1/norm];
  const fn=Math.hypot(c,s,gx), forward=[c/fn,s/fn,gx/fn];
  const left=[up[1]*forward[2]-up[2]*forward[1],up[2]*forward[0]-up[0]*forward[2],up[0]*forward[1]-up[1]*forward[0]];
  return {position:[x,y,mean+.095/up[2]-.0345*up[2]], forward,left,up};
}
