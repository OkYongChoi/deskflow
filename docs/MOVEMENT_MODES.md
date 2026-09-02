# DeskFlow Movement Modes

This document describes the equations used by the movement generators in
`deskflow/core.py`.

## Shared notation

- $n$: movement update index
- $\mathbf p_n=(x_n,y_n)$: current cursor position
- $\mathbf c=(c_x,c_y)$: cursor position captured when the task starts
- $R$: `Movement radius (px)` value
- $U(a,b)$: continuous uniform distribution from $a$ to $b$
- $U_{\mathrm{integer}}(a,b)$: discrete uniform distribution over integers
- $\mathcal N(\mu,\sigma^2)$: normal distribution

Every generated coordinate is rounded to an integer and clamped to the current
screen bounds before it is sent to Windows.

## Mode summary

| UI name | Internal mode | Model |
| --- | --- | --- |
| Random Walk | `random_walk` | Independent random displacement |
| Lissajous Figure Eight | `lissajous` | 1:2 Lissajous curve |
| Inertial Drift | `inertial_drift` | Correlated random motion with damping and a center spring |
| Levy Walk | `levy_walk` | Pareto-distributed step lengths |
| Breathing | `breathing` | Sinusoidally expanding and contracting orbit |
| Lorenz Butterfly | `lorenz` | Lorenz chaotic attractor projected onto the $x$-$z$ plane |
| Rose Curve | `rose_curve` | Five-petal polar rose |
| Spirograph | `spirograph` | Hypotrochoid |
| Golden Spiral | `golden_spiral` | Screen-scaled logarithmic spiral |
| Damped Pendulum | `damped_pendulum` | Parametric damped-pendulum approximation |
| Mean Reversion | `mean_reversion` | Discrete Ornstein-Uhlenbeck-like process |

## Random Walk

Each axis receives an independent integer displacement:

$$
\Delta x_n,\Delta y_n\sim U_{\mathrm{integer}}(-R,R)
$$

$$
\mathbf p_{n+1}=\mathbf p_n+(\Delta x_n,\Delta y_n)
$$

The displacement is sampled from a square rather than a circle.

## Lissajous Figure Eight

The phase advances by `0.32` radians per update:

$$
t_{n+1}=t_n+0.32
$$

$$
x_n=c_x+R\sin(t_n),\qquad
y_n=c_y+R\sin(2t_n)
$$

The $1:2$ frequency ratio produces the figure-eight path.

## Inertial Drift

Random acceleration, velocity damping, and a weak restoring force are combined:

$$
\mathbf a_n\sim U(-0.08R,0.08R)^2
$$

$$
\mathbf v_{n+1}
=0.86\mathbf v_n+\mathbf a_n+0.025(\mathbf c-\mathbf p_n)
$$

$$
\mathbf p_{n+1}=\mathbf p_n+\mathbf v_{n+1}
$$

Velocity is capped at:

$$
\lVert\mathbf v\rVert\le\max(1,0.28R)
$$

## Levy Walk

The direction is uniform and the step-length multiplier follows a Pareto
distribution with shape $\alpha=1.5$:

$$
\theta_n\sim U(0,2\pi),\qquad q_n\sim\operatorname{Pareto}(1.5)
$$

$$
s_n=\min(4R,\max(1,0.12Rq_n))
$$

$$
\mathbf p_{n+1}
=\mathbf p_n+s_n(\cos\theta_n,\sin\theta_n)
$$

This produces many short moves and occasional long jumps.

## Breathing

The phase advances by `0.28` radians. The radius oscillates between $0.1R$ and
$R$ while the point rotates:

$$
t_{n+1}=t_n+0.28
$$

$$
r_n=R\left(0.1+0.9\frac{\sin t_n+1}{2}\right)
=R(0.55+0.45\sin t_n)
$$

$$
\theta_n=0.72t_n
$$

$$
\mathbf p_n=\mathbf c+r_n(\cos\theta_n,\sin\theta_n)
$$

## Lorenz Butterfly

DeskFlow uses the standard Lorenz system:

$$
\frac{dx}{dt}=10(y-x)
$$

$$
\frac{dy}{dt}=x(28-z)-y
$$

$$
\frac{dz}{dt}=xy-\frac{8}{3}z
$$

The initial state is $(x,y,z)=(0.1,0,0)$. Each cursor update performs 24 Euler
steps with $\Delta t=0.01$. The $x$-$z$ projection is mapped to the screen:

$$
X=c_x+R\frac{x}{22},\qquad
Y=c_y+R\frac{z-25}{25}
$$

## Rose Curve

The phase advances by `0.22` radians and uses a five-petal polar rose:

$$
t_{n+1}=t_n+0.22
$$

$$
r_n=R\cos(5t_n)
$$

$$
x_n=c_x+r_n\cos t_n,\qquad
y_n=c_y+r_n\sin t_n
$$

## Spirograph

This mode uses a hypotrochoid with:

$$
A=5,\qquad B=3,\qquad d=4,\qquad
S=\frac{R}{A-B+d}=\frac{R}{6}
$$

The phase advances by `0.4` radians. This changes only the sampling interval;
the hypotrochoid and its screen-space radius are unchanged:

$$
x_n=c_x+S\left[(A-B)\cos t_n+d\cos\left(\frac{A-B}{B}t_n\right)\right]
$$

$$
y_n=c_y+S\left[(A-B)\sin t_n-d\sin\left(\frac{A-B}{B}t_n\right)\right]
$$

## Golden Spiral

The implementation samples an outward two-turn spiral in 24 updates while
expanding from $0.1R$ to $R$. It then follows the same samples in reverse so a
new cycle does not jump directly from $R$ back to $0.1R$:

$$
q=(n-1)\bmod46
$$

$$
k=\begin{cases}
q,&q<24\\
46-q,&q\ge24
\end{cases}
$$

$$
\theta_k=\frac{4\pi k}{23},\qquad
b=\frac{\ln10}{4\pi}
$$

$$
r_k=0.1R\,e^{b\theta_k}
$$

$$
\mathbf p_k=\mathbf c+r_k(\cos\theta_k,\sin\theta_k)
$$

Despite the UI name, this is currently a screen-scaled logarithmic spiral. A
strict golden spiral would increase its radius by the golden ratio $\varphi$
after every quarter turn.

## Damped Pendulum

The implementation is a parametric visual approximation. It samples two time
units per cursor update and restarts after 60 updates, covering the same
120-unit damping window as the earlier one-unit sampling:

$$
m=n\bmod60,\qquad t_m=2m
$$

$$
D_m=e^{-0.018t_m}
$$

$$
\theta_m=0.95D_m\cos(0.3t_m)
$$

$$
x_m=c_x+R\sin\theta_m
$$

$$
y_m=c_y+0.55R(1-\cos\theta_m)
$$

This mode does not numerically integrate the physical pendulum differential
equation; it reproduces the appearance of damped oscillation.

## Mean Reversion

This mode is similar to a discrete Ornstein-Uhlenbeck process:

$$
\boldsymbol\epsilon_n
\sim\mathcal N\left(\mathbf0,(0.16R)^2I\right)
$$

$$
\mathbf p_{n+1}
=\mathbf p_n+0.16(\mathbf c-\mathbf p_n)+\boldsymbol\epsilon_n
$$

The restoring force grows with distance from the starting center, while the
normal noise keeps the path irregular.

## Smooth cursor interpolation

After a mode produces a target point, Windows movement uses Smoothstep
interpolation between the current point $\mathbf a$ and target $\mathbf b$:

$$
h(s)=3s^2-2s^3,\qquad 0\le s\le1
$$

$$
\mathbf p(s)=(1-h(s))\mathbf a+h(s)\mathbf b
$$

The movement uses up to 24 interpolation steps over approximately 0.18 seconds.
This gives zero slope at the beginning and end of each movement.

## Radius behavior

- `Random Walk` and `Levy Walk` use $R$ primarily as a per-step scale and can
  roam across the screen over time.
- Parametric modes such as `Lissajous Figure Eight`, `Rose Curve`, and
  `Spirograph` use the captured start position as their center.
- Stochastic centered modes use a restoring force but can temporarily exceed
  $R$.
- All modes are ultimately clamped to the available screen bounds.
