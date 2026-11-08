#pragma once
// RUPTURA-derived FastIAST, adapted to finite positive PWL curves.
// Upstream: iRASPA/RUPTURA 96ed683f593bf832f2871d86f67272a97e74b3ce,
// src/mixture_prediction.cpp:187-346. MIT copyright and license are retained
// in RUPTURA_LICENSE.md. This is an adaptation, not unmodified RUPTURA.
#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <utility>

namespace ruptura_finite_pwl {
using Real = long double;
enum class FallbackReason : unsigned {
    none=0, invalid_initialization, singular_jacobian, nonfinite_iteration,
    iteration_limit, score_validation, count
};
struct Input {
    std::array<Real,2> f, pmax, cap;
    Real score_tolerance;                  // REQUIRED: matched protocol tolerance.
    std::uint64_t cache_key;               // Identity of ordered curves AND model version.
};
struct WarmState {
    bool valid=false;
    std::uint64_t cache_key=0;
    std::array<Real,2> pstar{{0,0}};
};
struct InverseResult { Real pressure; std::uint64_t probes; };
struct Result {
    Real score, lower, upper, x;
    bool used_fallback=false;
    unsigned newton_iterations=0;
    FallbackReason fallback_reason=FallbackReason::none;
};
struct Stats {
    std::uint64_t attempts=0, warm_starts=0, cold_starts=0, initialization_adjustments=0;
    std::uint64_t iterations=0, eval_probes=0, inverse_calls=0, inverse_probes=0;
    std::uint64_t validation_probes=0, negative_step_halvings=0, upper_step_dampings=0;
    std::uint64_t newton_accepted=0, fallback_count=0, fallback_exceptions=0;
    std::array<std::uint64_t,static_cast<unsigned>(FallbackReason::count)> fallback_reasons{};
    double total_seconds=0, fallback_seconds=0;
    // eval+inverse+validation exclude fallback probes, which the shared backend
    // must count. Never add these diagnostic counts to the backend probe count.
};
inline const char* reason_name(FallbackReason r) {
    switch(r) {
    case FallbackReason::none:return "none";
    case FallbackReason::invalid_initialization:return "invalid_initialization";
    case FallbackReason::singular_jacobian:return "singular_jacobian";
    case FallbackReason::nonfinite_iteration:return "nonfinite_iteration";
    case FallbackReason::iteration_limit:return "iteration_limit";
    case FallbackReason::score_validation:return "score_validation";
    default:return "invalid_reason";
    }
}
struct SecondsScope {
    double& out;
    std::chrono::steady_clock::time_point begin=std::chrono::steady_clock::now();
    ~SecondsScope() { out+=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count(); }
};
inline Real score_from_x(Real x,Real y) { return x/(1-x)*(1-y)/y; }
inline Real x_from_score(Real s,Real y) { return (s*y)/((1-y)+s*y); }

// Preconditions: BOTH positive components; positive PWL+origin backend; caller
// already establishes a supported root by the common finite-domain support test.
// eval(i,p) -> object with .pi and .q; MUST reject p outside [0,pmax[i]].
// inverse(i,psi) -> InverseResult; psi is in (0,min(cap)]. Count its actual probes.
// residual(x) -> sign-preserving Real value of Pi_0(f0/x)-Pi_1(f1/(1-x));
// use the shared precision policy (ordinary long double; binary128 near support),
// count both Pi calls, and never extrapolate. Do not impose more expensive
// validation here than the matched scalar solver uses for that candidate.
// fallback() -> Result with the shared solver's same score bracket/tolerance;
// it must count ALL its own probes, iterations, and exceptions in caller stats.
// All callbacks execute synchronously inside total_seconds. Exceptions are not
// converted into successful results. Selection/k-shell stays in the caller.
template<class EvalFn,class InverseFn,class ResidualFn,class FallbackFn>
Result solve_binary(const Input& in, WarmState* warm, Stats& stats,
                    EvalFn&& eval, InverseFn&& inverse,
                    ResidualFn&& residual, FallbackFn&& fallback) {
    SecondsScope timer{stats.total_seconds};
    ++stats.attempts;
    if (!(in.score_tolerance>0) || !std::isfinite(in.score_tolerance))
        throw std::invalid_argument("RUPTURA adapter requires a positive score tolerance");
    for(unsigned i=0;i<2;++i)
        if (!(in.f[i]>0 && in.pmax[i]>0 && in.cap[i]>0) ||
            !std::isfinite(in.f[i]+in.pmax[i]+in.cap[i]))
            throw std::invalid_argument("RUPTURA adapter requires finite positive inputs");
    const Real P=in.f[0]+in.f[1], y=in.f[0]/P;
    unsigned iterations=0;
    auto update_cache=[&](const Result& r) {
        if (!warm) return;
        const std::array<Real,2> pc{{in.f[0]/r.x,in.f[1]/(1-r.x)}};
        warm->valid=std::isfinite(pc[0]+pc[1]) && pc[0]>0 && pc[1]>0 &&
                    pc[0]<=in.pmax[0] && pc[1]<=in.pmax[1];
        warm->cache_key=in.cache_key;
        warm->pstar=pc;
    };
    auto use_fallback=[&](FallbackReason reason)->Result {
        ++stats.fallback_count;
        ++stats.fallback_reasons[static_cast<unsigned>(reason)];
        if(warm)warm->valid=false;
        SecondsScope fallback_timer{stats.fallback_seconds};
        try {
            Result r=fallback();
            if (!(r.x>0 && r.x<1 && r.lower<=r.score && r.score<=r.upper) ||
                !std::isfinite(r.score+r.lower+r.upper) ||
                r.upper-r.lower>in.score_tolerance*std::max(Real(1),std::fabs(r.lower))*Real(1.001L))
                throw std::runtime_error("Shared fallback violated the matched score contract");
            r.used_fallback=true; r.newton_iterations=iterations; r.fallback_reason=reason;
            update_cache(r);
            return r;
        } catch (...) { ++stats.fallback_exceptions; throw; }
    };
    auto probe=[&](unsigned i,Real p) {
        if (!(p>0 && p<=in.pmax[i]) || !std::isfinite(p))
            throw std::runtime_error("Adapter attempted an out-of-domain pure-curve probe");
        ++stats.eval_probes;
        return eval(i,p);
    };
    std::array<Real,2> p{};
    bool valid_warm=warm && warm->valid && warm->cache_key==in.cache_key;
    if(valid_warm)
        for(unsigned i=0;i<2;++i)
            valid_warm=valid_warm && std::isfinite(warm->pstar[i]) &&
                       warm->pstar[i]>0 && warm->pstar[i]<=in.pmax[i];
    if(valid_warm) {
        ++stats.warm_starts;
        p=warm->pstar; // Original cached fictitious pure pressures.
    } else {
        ++stats.cold_starts;
        // Original: psi0=sum_i y_i Pi_i(P). Domain-safe substitutions only
        // activate where that original expression or its inverse is unsupported.
        bool adjusted=P>in.pmax[0] || P>in.pmax[1];
        Real psi=y*probe(0,std::min(P,in.pmax[0])).pi+
                 (1-y)*probe(1,std::min(P,in.pmax[1])).pi;
        const Real common_cap=std::min(in.cap[0],in.cap[1]);
        adjusted=adjusted || psi>common_cap;
        psi=std::min(psi,common_cap);
        if(adjusted)++stats.initialization_adjustments;
        if(!(psi>0) || !std::isfinite(psi))
            return use_fallback(FallbackReason::invalid_initialization);
        for(unsigned i=0;i<2;++i) {
            ++stats.inverse_calls;
            const InverseResult inv=inverse(i,psi);
            stats.inverse_probes+=inv.probes;
            p[i]=inv.pressure;
            if(!(p[i]>0 && p[i]<=in.pmax[i]) || !std::isfinite(p[i]))
                return use_fallback(FallbackReason::invalid_initialization);
        }
    }
    bool converged=false;
    // The 2-component specialization of upstream lines 224-306. No scalar
    // root iteration replaces the upstream pressure-space Newton algorithm.
    for(unsigned it=0;it<50;++it) {
        const auto a=probe(0,p[0]), b=probe(1,p[1]);
        Real G0=a.pi-b.pi, G1=in.f[0]/p[0]+in.f[1]/p[1]-1;
        const Real A=a.q/p[0], B=-b.q/p[1], C=-in.f[0]/(p[0]*p[0]);
        Real D=-in.f[1]/(p[1]*p[1]);
        if(!(A>0) || !std::isfinite(A+B+C+D+G0+G1))
            return use_fallback(FallbackReason::singular_jacobian);
        D-=C*B/A; G1-=C*G0/A;   // Original sparse elimination, lines 257-263.
        if(D==0 || !std::isfinite(D+G1))
            return use_fallback(FallbackReason::singular_jacobian);
        const Real d1=G1/D, d0=(G0-d1*B)/A;
        const std::array<Real,2> delta{{d0,d1}};
        for(unsigned i=0;i<2;++i) {
            Real proposal=p[i]-delta[i];
            if(!std::isfinite(proposal))
                return use_fallback(FallbackReason::nonfinite_iteration);
            if(proposal<=0) { proposal=p[i]/2; ++stats.negative_step_halvings; }
            // Added finite-support safeguard; upstream has no upper bound.
            if(proposal>in.pmax[i]) {
                proposal=p[i]+(in.pmax[i]-p[i])/2;
                ++stats.upper_step_dampings;
            }
            if(!(proposal>0 && proposal<=in.pmax[i]))
                return use_fallback(FallbackReason::nonfinite_iteration);
            p[i]=proposal;
        }
        const auto ap=probe(0,p[0]), bp=probe(1,p[1]);
        // Original N=2 sample standard deviation of spreading pressures.
        const Real error=std::fabs(ap.pi-bp.pi)/std::sqrt(Real(2));
        const Real sum_xi=in.f[0]/std::max(p[0],Real(1e-15L))+
                          in.f[1]/std::max(p[1],Real(1e-15L));
        ++iterations; ++stats.iterations;
        if(error<Real(1e-13L) && std::fabs(sum_xi-1)<Real(1e-10L)) {
            converged=true; break;
        }
    }
    if(!converged)return use_fallback(FallbackReason::iteration_limit);
    const Real z0=in.f[0]/std::max(p[0],Real(1e-15L));
    const Real z1=in.f[1]/std::max(p[1],Real(1e-15L));
    const Real x=z0/(z0+z1), s=score_from_x(x,y);
    if(!(x>0 && x<1 && s>0) || !std::isfinite(s))
        return use_fallback(FallbackReason::score_validation);
    // Original residual tolerances do NOT imply the requested score accuracy.
    // Two shared-precision sign probes validate a narrow local bracket.
    // This is validation only: no additional root search/Newton repair here.
    const Real radius=Real(.24L)*in.score_tolerance*std::max(Real(1),std::fabs(s));
    const Real lo_domain=in.f[0]/in.pmax[0], hi_domain=1-in.f[1]/in.pmax[1];
    Real xl=std::max(x_from_score(std::max(Real(0),s-radius),y),
                     std::nextafter(lo_domain,Real(1)));
    Real xh=std::min(x_from_score(s+radius,y),std::nextafter(hi_domain,Real(0)));
    if(!(xl>0 && xl<=x && x<=xh && xh<1 && xl<xh))
        return use_fallback(FallbackReason::score_validation);
    stats.validation_probes+=2;
    const Real gl=residual(xl);
    stats.validation_probes+=2;
    const Real gh=residual(xh);
    if(!std::isfinite(gl+gh) || !(gl>0 && gh<0))
        return use_fallback(FallbackReason::score_validation);
    const Real lower=std::nextafter(score_from_x(xl,y),-std::numeric_limits<Real>::infinity());
    const Real upper=std::nextafter(score_from_x(xh,y),std::numeric_limits<Real>::infinity());
    if(!(lower<=s && s<=upper) ||
       upper-lower>in.score_tolerance*std::max(Real(1),std::fabs(lower))*Real(1.001L))
        return use_fallback(FallbackReason::score_validation);
    Result result{s,lower,upper,x,false,iterations,FallbackReason::none};
    ++stats.newton_accepted;
    // Preserve upstream's actual Newton pstar warm start (not normalized x).
    if(warm) { warm->valid=true; warm->cache_key=in.cache_key; warm->pstar=p; }
    return result;
}
} // namespace ruptura_finite_pwl
