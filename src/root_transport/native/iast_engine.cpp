// Binary IAST for explicitly declared positive piecewise-linear pure curves.
// Numerical (long-double) bounds; not a formally verified interval library.
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>
#include <array>
#include <set>
#include <cstdio>
#include <cfenv>
#include <quadmath.h>
#include "baselines/ruptura_finite_pwl.hpp"

using Real = long double;

extern "C" {
struct IastStats {
    uint64_t pairs_seen, supported, support_rejected, root_solves, pi_probes;
    uint64_t iterations, threshold_tests, threshold_rejected, domain_rejected;
    uint64_t near_tie_fallbacks;
    uint64_t support_refinements, boundary_tie_candidates;
    uint64_t anchor_tests, anchor_rejected, anchor_updates, warm_brackets, warm_fallbacks;
    uint64_t continuations, legacy_refresh_items;
    uint64_t witness_updates, invalid_anchors, ruptura_attempts, ruptura_iterations, ruptura_fallbacks, ruptura_warm_starts;
    uint64_t rank_witness_candidates, canonical_refinements, precision_fallbacks, ruptura_boundary_fallbacks;
    double seconds;
    uint64_t cap_sufficient_rejected, history_needed_rejected;
    uint64_t origin_solved_tests, origin_witness_tests, origin_mixed_tests;
    uint64_t interval_samples,cap_tail_rejected;
    double cap_fraction_width_sum, final_fraction_width_sum;
};
}

namespace {
constexpr Real EPS = std::numeric_limits<Real>::epsilon();
// Outward elementary enclosures. log1p is widened by four adjacent values:
// this explicit libm assumption is not a formal transcendental certificate.
Real down(Real x){return std::nextafter(x,-std::numeric_limits<Real>::infinity());}
Real up(Real x){return std::nextafter(x,std::numeric_limits<Real>::infinity());}
double lower_double(Real x){double d=double(x);return Real(d)>x?std::nextafter(d,-std::numeric_limits<double>::infinity()):d;}
double upper_double(Real x){double d=double(x);return Real(d)<x?std::nextafter(d,std::numeric_limits<double>::infinity()):d;}
struct Bound {Real lo,hi;Bound(Real x=0):lo(x),hi(x){} Bound(Real l,Real h):lo(l),hi(h){}};
Bound add(Bound a,Bound b){return {down(a.lo+b.lo),up(a.hi+b.hi)};}
Bound sub(Bound a,Bound b){return {down(a.lo-b.hi),up(a.hi-b.lo)};}
Bound mul(Bound a,Bound b){Real v[]={a.lo*b.lo,a.lo*b.hi,a.hi*b.lo,a.hi*b.hi};return {down(*std::min_element(v,v+4)),up(*std::max_element(v,v+4))};}
Bound divb(Bound a,Bound b){if(b.lo<=0&&b.hi>=0)return {-std::numeric_limits<Real>::infinity(),std::numeric_limits<Real>::infinity()};return mul(a,{down(1/b.hi),up(1/b.lo)});}
Bound log1pb(Bound a){Real l=std::log1p(a.lo),h=std::log1p(a.hi);for(int i=0;i<4;++i){l=down(l);h=up(h);}return {l,h};}
bool finite(Bound a){return std::isfinite(a.lo)&&std::isfinite(a.hi)&&a.lo<=a.hi;}
Bound fraction_at_score(Real s,Real y){Bound v=mul(Bound(s),Bound(y));return divb(v,add(sub(Bound(1),Bound(y)),v));}
Bound score_at_fraction(Real x,Real y){if(x<=0)return Bound(0);if(x>=1)return Bound(std::numeric_limits<Real>::infinity());return mul(divb(Bound(x),sub(Bound(1),Bound(x))),divb(sub(Bound(1),Bound(y)),Bound(y)));}

struct Eval { Real pi, q; };
struct Curve {
    std::vector<Real> p, q, prefix, slopes;
    std::vector<Bound> prefix_bounds,slope_bounds;
    Real pmax() const { return p.back(); }
    Real cap() const { return prefix.back(); }
    Curve(const double* pp, const double* qq, int64_t n) {
        if (n < 1) throw std::runtime_error("A curve needs positive-pressure points");
        int64_t start = 0;
        if (pp[0] == 0.) {
            if (qq[0] != 0.) throw std::runtime_error("Origin point must be (0,0)");
            start = 1;
        }
        for (int64_t i = start; i < n; ++i) {
            if (!std::isfinite(pp[i]) || !std::isfinite(qq[i]) || pp[i] <= 0. || qq[i] <= 0.)
                throw std::runtime_error("Non-origin pressures and uptakes must be finite and strictly positive");
            if (!p.empty() && pp[i] <= p.back())
                throw std::runtime_error("Pressures must be strictly increasing");
            p.push_back(pp[i]); q.push_back(qq[i]);
        }
        if (p.empty()) throw std::runtime_error("Curve contains no positive-pressure point");
        prefix.resize(p.size());
        prefix_bounds.resize(p.size());prefix_bounds[0]=Bound(q[0]);
        prefix[0] = q[0]; // Integral of the explicitly declared line to origin.
        for (size_t i = 0; i + 1 < p.size(); ++i) {
            Real slope = (q[i+1] - q[i]) / (p[i+1] - p[i]);
            slopes.push_back(slope);
            slope_bounds.push_back(divb(sub(Bound(q[i+1]),Bound(q[i])),sub(Bound(p[i+1]),Bound(p[i]))));
            prefix[i+1] = prefix[i] + segment(i, p[i+1]);
            prefix_bounds[i+1]=add(prefix_bounds[i],segment_bound(i,Bound(p[i+1])));
        }
    }
    Bound segment_bound(size_t i,Bound z) const {
        Bound delta=sub(z,Bound(p[i])),lr=log1pb(divb(delta,Bound(p[i])));
        return add(mul(Bound(q[i]),lr),mul(slope_bounds[i],sub(delta,mul(Bound(p[i]),lr))));
    }
    Bound pi_bound(Bound z,IastStats* st=nullptr) const {
        if(st)++st->pi_probes;
        if(z.lo<0||z.hi>p.back()||!finite(z))throw std::runtime_error("Interval pure-curve query outside support");
        if(z.hi<=p[0])return mul(Bound(q[0]),divb(z,Bound(p[0])));
        auto at=[&](Real t){
            if(t<=p[0])return mul(Bound(q[0]),divb(Bound(t),Bound(p[0])));
            if(t==p.back())return prefix_bounds.back();
            size_t j=std::upper_bound(p.begin(),p.end(),t)-p.begin()-1;
            return add(prefix_bounds[j],segment_bound(j,Bound(t)));
        };
        if(z.lo==z.hi)return at(z.lo);
        if(z.lo>=p[0]&&z.hi<p.back()) {
            size_t a=std::upper_bound(p.begin(),p.end(),z.lo)-p.begin()-1;
            size_t b=std::upper_bound(p.begin(),p.end(),z.hi)-p.begin()-1;
            if(a==b)return add(prefix_bounds[a],segment_bound(a,z));
        }
        return {at(z.lo).lo,at(z.hi).hi}; // Pi monotone for positive uptake.
    }
    Bound inverse_bound(Bound target,Real nominal,uint64_t* probes=nullptr) const {
        // Nominal inverse only proposes endpoints; bounded signs validate them.
        // A failed proposal keeps the physical 0/pmax endpoint, never a midpoint.
        Real d=std::max(Real(1e-12)*std::abs(nominal),1024*EPS*p.back());
        Real l=std::max(Real(0),down(nominal-d)),u=std::min(p.back(),up(nominal+d));
        if(probes)++*probes;
        if(pi_bound(Bound(l)).hi>=target.lo)l=0;
        if(u<p.back()){if(probes)++*probes;if(pi_bound(Bound(u)).lo<=target.hi)u=p.back();}
        return {l,u};
    }
    Real segment(size_t i, Real z) const {
        Real delta = z - p[i], lr = std::log1p(delta / p[i]);
        return q[i] * lr + slopes[i] * (delta - p[i] * lr);
    }
    Eval eval(Real z, IastStats* st = nullptr) const {
        if (st) ++st->pi_probes;
        if (z <= p[0]) {
            Real v = q[0] * (z / p[0]);
            return {v, v};
        }
        if (z > p.back() * (1 + 128*EPS))
            throw std::runtime_error("Pure-curve query exceeds declared pressure support");
        if (z >= p.back()) return {prefix.back(), q.back()};
        size_t j = std::upper_bound(p.begin(), p.end(), z) - p.begin() - 1;
        return {prefix[j] + segment(j, z), q[j] + slopes[j] * (z - p[j])};
    }
    Real inverse(Real pi, uint64_t* probes = nullptr) const {
        if (pi <= prefix[0]) return p[0] * pi / q[0];
        if (pi >= prefix.back()) return p.back();
        size_t j = std::upper_bound(prefix.begin(), prefix.end(), pi) - prefix.begin() - 1;
        Real lo = p[j], hi = p[j+1];
        for (int it=0; it<100; ++it) {
            Real mid = lo + (hi-lo)/2;
            if (mid == lo || mid == hi) break;
            if (probes) ++*probes;
            if (prefix[j] + segment(j, mid) < pi) lo = mid; else hi = mid;
        }
        return lo + (hi-lo)/2;
    }
    using MP = __float128;
    MP precise_pi(const MP& z, IastStats* st=nullptr,MP* error=nullptr) const {
        if(st)++st->pi_probes;
        if(z<0 || z>MP(p.back()))
            throw std::runtime_error("Binary128 pure-curve query exceeds declared pressure support");
        if(z<=MP(p[0])){MP v=MP(q[0])*z/MP(p[0]);if(error)*error=4096*ldexpq(MP(1),-112)*fabsq(v);return v;}
        MP sum(q[0]),magnitude=fabsq(sum);
        for(size_t j=0;j+1<p.size();++j) {
            MP a(p[j]),b=std::min(z,MP(p[j+1]));
            MP slope=(MP(q[j+1])-MP(q[j]))/(MP(p[j+1])-MP(p[j]));
            MP lr=logq(b/a);
            MP delta=b-a,pl=a*lr,ql=MP(q[j])*lr;
            sum+=ql+slope*(delta-pl);
            magnitude+=fabsq(ql)+fabsq(slope)*(fabsq(delta)+fabsq(pl))
                +(fabsq(MP(q[j+1]))+fabsq(MP(q[j])))/(MP(p[j+1])-MP(p[j]))*(fabsq(delta)+fabsq(pl));
            if(z<=MP(p[j+1])){if(error)*error=4096*ldexpq(MP(1),-112)*MP(j+2)*magnitude;return sum;}
        }
        if(error)*error=4096*ldexpq(MP(1),-112)*MP(p.size()+1)*magnitude;
        return sum;
    }
};

struct Pair { int64_t left, right; Real a1, a2, cap; Bound a1_bound,a2_bound; };
struct Score { int64_t id; Real value, lower, upper, x, xl, xu; bool canonical=false; };
struct Anchor { Real P=0,y=0,l=0,u=1; bool valid=false; uint8_t origin=0; };
struct Hint { Real lo=0,hi=1,start=-1,known_lo=0; bool warm=false,continued=false,witness=false; Real witness_hi=1,cap_hi=1; };
struct Engine {
    std::vector<Curve> curves;
    std::vector<Pair> pairs;
    std::vector<std::array<Anchor,2>> anchors;
    std::vector<ruptura_finite_pwl::WarmState> ruptura_warm;
    std::vector<int64_t> cap_upper_order,cap_lower_order,cap_upper_rank,incumbents;
    std::vector<uint64_t> cap_processed,cap_support_generation;
    std::vector<uint8_t> cap_supported;
    uint64_t cap_generation=0;
    void prepare_cap_index() {
        if(cap_upper_order.size()==pairs.size())return;
        size_t n=pairs.size();cap_upper_order.resize(n);cap_lower_order.resize(n);cap_upper_rank.resize(n);
        for(size_t i=0;i<n;++i)cap_upper_order[i]=cap_lower_order[i]=i;
        std::sort(cap_upper_order.begin(),cap_upper_order.end(),[&](int64_t a,int64_t b){return pairs[a].a2_bound.lo!=pairs[b].a2_bound.lo?pairs[a].a2_bound.lo<pairs[b].a2_bound.lo:a<b;});
        std::sort(cap_lower_order.begin(),cap_lower_order.end(),[&](int64_t a,int64_t b){return pairs[a].a1_bound.lo!=pairs[b].a1_bound.lo?pairs[a].a1_bound.lo>pairs[b].a1_bound.lo:a<b;});
        for(size_t i=0;i<n;++i)cap_upper_rank[cap_upper_order[i]]=i;
        cap_processed.resize(n);cap_support_generation.resize(n);cap_supported.resize(n);
    }
    uint64_t index_bytes() const {
        return (cap_upper_order.capacity()+cap_lower_order.capacity()+cap_upper_rank.capacity()+incumbents.capacity())*sizeof(int64_t)
             +(cap_processed.capacity()+cap_support_generation.capacity())*sizeof(uint64_t)+cap_supported.capacity()*sizeof(uint8_t);
    }
    bool anchor_updates_enabled=true, diagnostics_enabled=false;
    bool lean_cap=false;
    bool fast_bounds=true;
    mutable Real cached_P=-1,cached_y=-1;
    mutable Bound query_f1,query_f2,query_ratio;
    void cache_query(Real P,Real y) const {
        if(P==cached_P&&y==cached_y)return;
        Real c_lo=down(1-y),c_hi=up(1-y);
        query_f1={down(P*y),up(P*y)};
        query_f2={down(P*c_lo),up(P*c_hi)};
        query_ratio={down(c_lo/y),up(c_hi/y)};
        cached_P=P;cached_y=y;
    }
    Bound query_score(Real x,Real P,Real y) const {
        if(!fast_bounds)return score_at_fraction(x,y);
        if(x<=0)return Bound(0);if(x>=1)return Bound(std::numeric_limits<Real>::infinity());
        cache_query(P,y);
        Real lo=down(down(x/up(1-x))*query_ratio.lo);
        Real hi=up(up(x/down(1-x))*query_ratio.hi);
        if(!std::isfinite(lo)||!std::isfinite(hi)||lo<0||lo>hi)return score_at_fraction(x,y);
        return {lo,hi};
    }
    Real cap_score_upper(int64_t id,Real P,Real y) const {
        if(!fast_bounds){Bound f2=mul(Bound(P),sub(Bound(1),Bound(y)));return score_at_fraction(sub(Bound(1),mul(f2,Bound(pairs[id].a2_bound.lo))).hi,y).hi;}
        cache_query(P,y);Real numerator=up(up(1/pairs[id].a2_bound.lo)-query_f2.lo);
        if(!(query_f1.lo>0)||!std::isfinite(numerator))return std::numeric_limits<Real>::infinity();
        if(numerator<=0)return 0;
        Real result=up(numerator/query_f1.lo);
        return std::isfinite(result)?result:std::numeric_limits<Real>::infinity();
    }
    Real cap_score_lower(int64_t id,Real P,Real y) const {
        cache_query(P,y);Real denominator=up(up(1/pairs[id].a1_bound.lo)-query_f1.lo);
        if(!(denominator>0&&query_f2.lo>0)||!std::isfinite(denominator))return 0;
        Real value=down(query_f2.lo/denominator);return std::isfinite(value)?std::max(Real(0),value):Real(0);
    }
    uint64_t build_probes = 0;
    double build_seconds = 0.;
    Engine(int64_t nc, const int64_t* offsets, const double* p, const double* q,
           int64_t np, const int64_t* pair_ids,bool lean=false):lean_cap(lean) {
        auto t0 = std::chrono::steady_clock::now();
        if(std::fegetround()!=FE_TONEAREST||!std::numeric_limits<Real>::is_iec559||std::numeric_limits<Real>::radix!=2)
            throw std::runtime_error("Fast bounds require IEEE binary Real and FE_TONEAREST");
        if (nc < 1 || np < 0) throw std::runtime_error("Invalid curve/pair count");
        for (int64_t i=0; i<nc; ++i) {
            if (offsets[i+1] <= offsets[i]) throw std::runtime_error("Empty curve");
            curves.emplace_back(p+offsets[i], q+offsets[i], offsets[i+1]-offsets[i]);
        }
        for (int64_t e=0; e<np; ++e) {
            int64_t i=pair_ids[2*e], j=pair_ids[2*e+1];
            if (i<0 || j<0 || i>=nc || j>=nc) throw std::runtime_error("Invalid pair index");
            Real cap=std::min(curves[i].cap(),curves[j].cap());
            Real r1=curves[i].inverse(cap,&build_probes), r2=curves[j].inverse(cap,&build_probes);
            Bound c1=curves[i].prefix_bounds.back(),c2=curves[j].prefix_bounds.back();
            Bound cb{std::min(c1.lo,c2.lo),std::min(c1.hi,c2.hi)};
            Bound b1=curves[i].inverse_bound(cb,r1,&build_probes),b2=curves[j].inverse_bound(cb,r2,&build_probes);
            Bound a1{down(1/b1.hi),b1.lo>0?up(1/b1.lo):std::numeric_limits<Real>::infinity()};
            Bound a2{down(1/b2.hi),b2.lo>0?up(1/b2.lo):std::numeric_limits<Real>::infinity()};
            pairs.push_back({i,j,1/r1,1/r2,cap,a1,a2});
        }
        if(!lean_cap){anchors.resize(pairs.size());ruptura_warm.resize(pairs.size());}
        else anchor_updates_enabled=false;
        build_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
    }
    bool supported(const Pair& e, Real P, Real y, IastStats* st=nullptr) const {
        Bound f1b=mul(Bound(P),Bound(y)),f2b=mul(Bound(P),sub(Bound(1),Bound(y)));
        Bound sum=add(mul(f1b,e.a1_bound),mul(f2b,e.a2_bound));
        if(sum.hi<1)return true;if(sum.lo>1)return false;
        if(st)++st->support_refinements;
        // Boundary queries are rare. Re-evaluate the support-domain endpoints
        // from original curve coordinates in IEEE binary128, avoiding the
        // approximate inverse coefficients in this decision.
        using MP=Curve::MP;
        MP f1mp=MP(P)*MP(y),f2mp=MP(P)*(MP(1)-MP(y));
        MP m1(curves[e.left].pmax()),m2(curves[e.right].pmax());
        MP d1=(m1-MP(P))+f2mp,d2=(m2-MP(P))+f1mp;
        if(d1<=0||d2<=0)return false;
        MP lo=f2mp/d1,hi=d2/f1mp;if(lo>hi)return false;
        auto g=[&](const MP& s){
            MP p1=s==lo?m1:f1mp+f2mp/s;
            MP p2=s==hi?m2:f2mp+s*f1mp;
            if(p1>m1||p2>m2)throw std::runtime_error("Unresolved binary128 support endpoint");
            return curves[e.left].precise_pi(p1)-curves[e.right].precise_pi(p2);
        };
        return g(lo)>=0 && g(hi)<=0;
    }
    static Real score(Real x, Real y) { return (x/(1-x))*((1-y)/y); }
    Bound residual_bound(const Pair& e,Real P,Real y,Real x,IastStats* st) const {
        if(!(x>0&&x<1))return {-std::numeric_limits<Real>::infinity(),std::numeric_limits<Real>::infinity()};
        Bound p1=divb(mul(Bound(P),Bound(y)),Bound(x));
        Bound p2=divb(mul(Bound(P),sub(Bound(1),Bound(y))),sub(Bound(1),Bound(x)));
        if(p1.lo<0||p2.lo<0||p1.hi>curves[e.left].pmax()||p2.hi>curves[e.right].pmax())
            return {-std::numeric_limits<Real>::infinity(),std::numeric_limits<Real>::infinity()};
        return sub(curves[e.left].pi_bound(p1,st),curves[e.right].pi_bound(p2,st));
    }
    struct Residual { Real g, derivative, scale; };
    Residual residual(const Pair& e, Real f1, Real f2, Real x, IastStats* st) const {
        Real p1=f1/x,p2=f2/(1-x);
        // The feasible endpoints denote declared pressures exactly. Recovering
        // f2/(1-x_hi) after x_hi=1-f2/M2 can amplify rounding cancellation.
        // Substitute the endpoint's known value only at that represented
        // endpoint; arbitrary out-of-domain probes still raise an error.
        if(p1>curves[e.left].pmax() && x==f1/curves[e.left].pmax())p1=curves[e.left].pmax();
        if(p2>curves[e.right].pmax() && x==1-f2/curves[e.right].pmax())p2=curves[e.right].pmax();
        Eval a=curves[e.left].eval(p1,st), b=curves[e.right].eval(p2,st);
        return {a.pi-b.pi,-a.q/x-b.q/(1-x),std::abs(a.pi)+std::abs(b.pi)};
    }
    Score solve_precise(int64_t id,Real P,Real y,Real tol,IastStats* st) const {
        // Shared rare fallback in score coordinates: no 1-x cancellation.
        // Binary128 error guards are numerical assumptions, not a proof of libm.
        using MP=Curve::MP;const Pair& e=pairs[id];
        MP ym(y),f1=MP(P)*ym,f2=MP(P)*(MP(1)-ym);
        MP m1(curves[e.left].pmax()),m2(curves[e.right].pmax());
        MP d1=(m1-MP(P))+f2,d2=(m2-MP(P))+f1;
        if(!(d1>0&&d2>0))throw std::runtime_error("Invalid binary128 score domain");
        MP domain_lo=f2/d1,domain_hi=d2/f1,lo=domain_lo,hi=domain_hi;
        if(!(lo>0&&lo<=hi))throw std::runtime_error("Invalid binary128 score interval");
        auto g=[&](MP s){
            MP p1=s==domain_lo?m1:f1+f2/s,p2=s==domain_hi?m2:f2+s*f1;
            MP er1=0,er2=0;
            MP a=curves[e.left].precise_pi(p1,st,&er1),b=curves[e.right].precise_pi(p2,st,&er2);
            return std::array<MP,2>{a-b,er1+er2+4096*ldexpq(MP(1),-112)*(fabsq(a)+fabsq(b))};
        };
        for(int it=0;it<512;++it){
            ++st->iterations;
            MP target=MP(tol)*std::max(MP(1),fabsq(lo))/4;
            if(hi-lo<=target)break;
            MP mid=hi>4*lo?sqrtq(lo)*sqrtq(hi):lo+(hi-lo)/2;
            if(mid==lo||mid==hi)break;
            auto z=g(mid);
            if(z[0]>z[1])lo=mid;
            else if(z[0]<-z[1])hi=mid;
            else {
                // A rounded zero does not establish a point root. Only retain
                // an independently opposed neighbourhood, or report unknown.
                MP radius=MP(tol)*std::max(MP(1),fabsq(mid))/16;
                MP a=std::max(lo,mid-radius),b=std::min(hi,mid+radius);
                auto ga=g(a),gb=g(b);
                if((a==domain_lo||ga[0]>ga[1])&&(b==domain_hi||gb[0]<-gb[1])){lo=a;hi=b;break;}
                throw std::runtime_error("Binary128 score residual unresolved at requested tolerance");
            }
        }
        if(hi-lo>MP(tol)*std::max(MP(1),fabsq(lo)))throw std::runtime_error("Binary128 score bracket did not converge");
        Real lower=down(Real(lo)),upper=up(Real(hi)),value=Real(lo+(hi-lo)/2);
        Bound xb=fraction_at_score(value,y),xl=fraction_at_score(lower,y),xu=fraction_at_score(upper,y);
        return {id,value,lower,upper,std::min(Real(1),std::max(Real(0),(xb.lo+xb.hi)/2)),
            std::max(Real(0),xl.lo),std::min(Real(1),xu.hi)};
    }
    Score solve(int64_t id, Real P, Real y, Real tol, IastStats* st, Hint hint=Hint{}) const {
        ++st->root_solves;
        const Pair& e=pairs[id]; Real f1=P*y, f2=P*(1-y);
        if(std::abs(f1*e.a1+f2*e.a2-1)<=Real(1e-12))
            return solve_precise(id,P,y,tol,st);
        Real lo=f1/curves[e.left].pmax(), hi=1-f2/curves[e.right].pmax();
        if (!(lo>0 && hi<1 && lo<=hi)) {++st->precision_fallbacks;return solve_precise(id,P,y,tol,st);}
        if(hint.warm) {
            Real a=std::max(lo,hint.lo),b=std::min(hi,hint.hi);
            if(a<=b && residual(e,f1,f2,a,st).g>=0 && residual(e,f1,f2,b,st).g<=0) {
                lo=a;hi=b;++st->warm_brackets;
            } else ++st->warm_fallbacks;
        }
        if(hint.continued && hint.known_lo>=lo && hint.known_lo<=hi)lo=hint.known_lo;
        Real k1=curves[e.left].q[0]/curves[e.left].p[0];
        Real k2=curves[e.right].q[0]/curves[e.right].p[0];
        Real x=hint.continued?hint.start:(f1*k1)/(f1*k1+f2*k2);
        if(!std::isfinite(x)||x<=lo||x>=hi)x=lo+(hi-lo)/2;
        for (int it=0; it<512; ++it) {
            ++st->iterations;
            Real sl=score(lo,y), su=score(hi,y);
            if (su-sl <= tol*std::max(Real(1),std::abs(sl))) break;
            Residual r=residual(e,f1,f2,x,st);
            Real correction=r.g/r.derivative;
            Real score_x=score(x,y);
            Real target_x=tol*std::max(Real(1),std::abs(score_x))*y/(1-y)*(1-x)*(1-x);
            if(std::abs(correction)<target_x/8) {
                Real dx=std::max(target_x/4,256*EPS*x*(1-x));
                Real a=std::max(lo,x-dx),b=std::min(hi,x+dx);
                Residual ra=residual(e,f1,f2,a,st),rb=residual(e,f1,f2,b,st);
                if(ra.g>=0 && rb.g<=0) {lo=a;hi=b;break;}
            }
            // Strict sign update in long double. Final intervals are a numerical
            // tolerance contract, not machine-verified outward-rounded bounds.
            if (r.g>0) lo=x; else if (r.g<0) hi=x; else {
                // An exact floating-point zero still needs a nonzero bracket.
                Real dx=std::max(128*EPS, tol/8)*x*(1-x);
                Real a=std::max(lo,x-dx), b=std::min(hi,x+dx);
                Residual ra=residual(e,f1,f2,a,st), rb=residual(e,f1,f2,b,st);
                if (ra.g>=0 && rb.g<=0) {lo=a;hi=b;break;}
                lo=std::max(lo,std::nextafter(x,Real(0)));
                hi=std::min(hi,std::nextafter(x,Real(1)));
                break;
            }
            if (lo==hi) break;
            Real next=x-r.g/r.derivative;
            // Permit Newton's usual endpoint approach. A periodic bisection
            // guarantees global progress without destroying local convergence.
            if (!std::isfinite(next) || next<=lo || next>=hi || it%8==7)
                next=lo+(hi-lo)/2;
            if (next==lo || next==hi || next==x) next=lo+(hi-lo)/2;
            if (next==lo || next==hi) break;
            x=next;
        }
        if(score(hi,y)-score(lo,y)>tol*std::max(Real(1),std::abs(score(lo,y)))*Real(1.001)) {
            ++st->precision_fallbacks;
            return solve_precise(id,P,y,tol,st);
        }
        Bound gl=residual_bound(e,P,y,lo,st),gu=residual_bound(e,P,y,hi,st);
        if(!(gl.lo>=0&&gu.hi<=0)){++st->precision_fallbacks;return solve_precise(id,P,y,tol,st);}
        x=lo+(hi-lo)/2;
        return {id,score(x,y),score_at_fraction(lo,y).lo,score_at_fraction(hi,y).hi,x,lo,hi};
    }
    // Return -1: safely below threshold, 1: above, 0: near sign boundary.
    int threshold(int64_t id, Real P, Real y, Real tau, IastStats* st, Hint* hint=nullptr) const {
        ++st->threshold_tests;
        const Pair& e=pairs[id];
        if(hint){hint->witness=false;hint->continued=false;hint->known_lo=0;hint->start=-1;}
        // At selectivity tau: p1=f1+f2/tau and p2=f2+tau*f1.
        // Positive sums avoid converting tau to rounded x and subtracting 1-x.
        Bound f1=mul(Bound(P),Bound(y)),f2=mul(Bound(P),sub(Bound(1),Bound(y)));
        Bound p1=add(f1,divb(f2,Bound(tau))),p2=add(f2,mul(Bound(tau),f1));
        Real m1=curves[e.left].pmax(),m2=curves[e.right].pmax();
        if(p2.lo>m2&&p1.hi<=m1){++st->domain_rejected;return -1;}
        if(p1.lo>m1&&p2.hi<=m2)return 1;
        if(!finite(p1)||!finite(p2)||p1.lo<0||p2.lo<0||p1.hi>m1||p2.hi>m2){++st->near_tie_fallbacks;return 0;}
        Bound g=sub(curves[e.left].pi_bound(p1,st),curves[e.right].pi_bound(p2,st));
        Bound x=fraction_at_score(tau,y);
        if(g.hi<0){if(hint&&finite(x)){hint->witness=true;hint->witness_hi=std::min(Real(1),x.hi);}return -1;}
        if(g.lo>0){
            if(hint&&finite(x)&&x.lo>0&&x.hi<1){hint->known_lo=x.lo;hint->start=x.lo+(x.hi-x.lo)/2;hint->continued=true;++st->continuations;}
            return 1;
        }
        ++st->near_tie_fallbacks;
        return 0;
    }
    Hint transport_generic(int64_t id,Real P,Real y,IastStats* st,bool first_only=false,bool cap_only=false) const {
        Hint h;const Pair& e=pairs[id];
        Bound f1=mul(Bound(P),Bound(y)),f2=mul(Bound(P),sub(Bound(1),Bound(y)));
        Bound physical_lo=divb(f1,Bound(curves[e.left].pmax()));
        Bound physical_hi=sub(Bound(1),divb(f2,Bound(curves[e.right].pmax())));
        h.lo=std::max(Real(0),physical_lo.lo);h.hi=std::min(Real(1),physical_hi.hi);
        if(!finite(physical_lo)||!finite(physical_hi)||h.lo>h.hi){++st->invalid_anchors;return Hint{};}
        Real cl=std::max(h.lo,mul(f1,Bound(e.a1_bound.lo)).lo);
        Real cu=std::min(h.hi,sub(Bound(1),mul(f2,Bound(e.a2_bound.lo))).hi);
        if(cl<=cu){h.lo=cl;h.hi=cu;h.warm=true;}else ++st->invalid_anchors;
        h.cap_hi=h.hi;const Real cap_width=h.hi-h.lo;
        auto finish=[&](){if(diagnostics_enabled&&h.warm){++st->interval_samples;
            st->cap_fraction_width_sum+=double(cap_width);st->final_fraction_width_sum+=double(h.hi-h.lo);}return h;};
        if(cap_only||anchors.empty())return finish();
        for(int j=0;j<(first_only?1:2);++j){
            const Anchor& a=anchors[id][j];if(!a.valid)continue;++st->anchor_tests;
            if(diagnostics_enabled){if(a.origin==1)++st->origin_solved_tests;else if(a.origin==2)++st->origin_witness_tests;else if(a.origin==3)++st->origin_mixed_tests;}
            // Original binary64 P,y are retained, rather than rounded products.
            Bound old1=mul(Bound(a.P),Bound(a.y)),old2=mul(Bound(a.P),sub(Bound(1),Bound(a.y)));
            Bound c1=divb(f1,old1),c2=divb(f2,old2);
            Bound l1=mul(c1,Bound(a.l)),l2=sub(Bound(1),mul(c2,sub(Bound(1),Bound(a.l))));
            Bound u1=mul(c1,Bound(a.u)),u2=sub(Bound(1),mul(c2,sub(Bound(1),Bound(a.u))));
            Real l=std::min(l1.lo,l2.lo),u=std::max(u1.hi,u2.hi);
            if(!std::isfinite(l)||!std::isfinite(u)||l>u){++st->invalid_anchors;continue;}
            Real nl=std::max(h.lo,l),nu=std::min(h.hi,u);
            if(nl>nu){++st->invalid_anchors;continue;}
            h.lo=nl;h.hi=nu;h.warm=true;
        }
        return finish();
    }
    Hint transport(int64_t id,Real P,Real y,IastStats* st,bool first_only=false,bool cap_only=false) const {
        if(!fast_bounds)return transport_generic(id,P,y,st,first_only,cap_only);
        cache_query(P,y);const Pair& e=pairs[id];
        if(!(query_f1.lo>0&&query_f2.lo>0)||!finite(query_f1)||!finite(query_f2))return transport_generic(id,P,y,st,first_only,cap_only);
        Hint h;
        h.lo=std::max(Real(0),down(query_f1.lo/curves[e.left].pmax()));
        h.hi=std::min(Real(1),up(1-down(query_f2.lo/curves[e.right].pmax())));
        h.lo=std::max(h.lo,down(query_f1.lo*e.a1_bound.lo));
        h.hi=std::min(h.hi,up(1-down(query_f2.lo*e.a2_bound.lo)));
        if(!std::isfinite(h.lo)||!std::isfinite(h.hi)||h.lo>h.hi)return transport_generic(id,P,y,st,first_only,cap_only);
        h.warm=true;h.cap_hi=h.hi;Real cap_width=h.hi-h.lo;
        for(int j=0;j<(first_only?1:2)&&!cap_only&&!anchors.empty();++j){
            const Anchor& a=anchors[id][j];if(!a.valid)continue;
            Real old1lo=down(a.P*a.y),old1hi=up(a.P*a.y);
            Real old2lo=down(a.P*down(1-a.y)),old2hi=up(a.P*up(1-a.y));
            if(!(old1lo>0&&old2lo>0)){++st->invalid_anchors;continue;}
            Real c1lo=down(query_f1.lo/old1hi),c1hi=up(query_f1.hi/old1lo);
            Real c2lo=down(query_f2.lo/old2hi),c2hi=up(query_f2.hi/old2lo);
            if(!std::isfinite(c1lo)||!std::isfinite(c1hi)||!std::isfinite(c2lo)||!std::isfinite(c2hi)
                ||c1lo<0||c2lo<0||c1lo>c1hi||c2lo>c2hi||a.l<0||a.u>1||a.l>a.u){++st->invalid_anchors;continue;}
            Real l=std::min(down(c1lo*a.l),down(1-up(c2hi*up(1-a.l))));
            Real u=std::max(up(c1hi*a.u),up(1-down(c2lo*down(1-a.u))));
            ++st->anchor_tests;
            if(diagnostics_enabled){if(a.origin==1)++st->origin_solved_tests;else if(a.origin==2)++st->origin_witness_tests;else if(a.origin==3)++st->origin_mixed_tests;}
            if(!std::isfinite(l)||!std::isfinite(u)||l>u){++st->invalid_anchors;continue;}
            Real nl=std::max(h.lo,l),nu=std::min(h.hi,u);
            if(nl>nu){++st->invalid_anchors;continue;}h.lo=nl;h.hi=nu;
        }
        if(diagnostics_enabled){++st->interval_samples;st->cap_fraction_width_sum+=double(cap_width);st->final_fraction_width_sum+=double(h.hi-h.lo);}
        return h;
    }
    void remember_interval(int64_t id,Real P,Real y,Real l,Real u,uint8_t origin){
        if(!anchor_updates_enabled||anchors.empty()||!std::isfinite(l)||!std::isfinite(u)||l<0||u>1||l>u)return;
        auto& a=anchors[id];Anchor n{P,y,l,u,true,origin};
        for(int j=0;j<2;++j)if(a[j].valid&&a[j].P==P&&a[j].y==y){
            Real lo=std::max(a[j].l,l),hi=std::min(a[j].u,u);
            if(lo<=hi){a[j].l=lo;a[j].u=hi;a[j].origin|=origin;}return;
        }
        if(!a[0].valid)a[0]=n;else a[1]=n;
    }
    void remember(const Score& s,Real P,Real y,IastStats* st){
        if(anchor_updates_enabled&&!anchors.empty()){remember_interval(s.id,P,y,s.xl,s.xu,1);++st->anchor_updates;}
    }
    void remember_witness(int64_t id,Real P,Real y,const Hint& hint,IastStats* st){
        if(!hint.witness||!anchor_updates_enabled||anchors.empty())return;
        Bound f1=mul(Bound(P),Bound(y));
        Real l=std::max(Real(0),divb(f1,Bound(curves[pairs[id].left].pmax())).lo);
        Real u=std::min(Real(1),hint.witness_hi);
        if(l<=u){remember_interval(id,P,y,l,u,2);++st->witness_updates;}
    }
    Score solve_ruptura(int64_t id,Real P,Real y,Real tol,IastStats* st) {
        namespace R=ruptura_finite_pwl;
        const Pair& e=pairs[id];Real f1=P*y,f2=P*(1-y);
        // Preserve the same original-P/y binary128 boundary policy as native
        // solving. Rounded long-double partial pressures are not safe inputs
        // to the adapter's strict binary128 endpoint validation.
        if(std::abs(f1*e.a1+f2*e.a2-1)<=Real(1e-12)) {
            ++st->ruptura_boundary_fallbacks;++st->ruptura_fallbacks;
            return solve(id,P,y,tol,st);
        }
        const Curve* c[2]={&curves[e.left],&curves[e.right]};
        R::Input in{{f1,f2},{c[0]->pmax(),c[1]->pmax()},{c[0]->cap(),c[1]->cap()},tol,uint64_t(id)};
        R::Stats rs;
        auto ev=[&](unsigned i,Real p){return c[i]->eval(p,st);};
        auto inv=[&](unsigned i,Real pi){uint64_t probes=0;Real p=c[i]->inverse(pi,&probes);st->pi_probes+=probes;return R::InverseResult{p,probes};};
        auto residual_cb=[&](Real x)->Real {return residual(e,f1,f2,x,st).g;};
        auto fallback=[&](){Score z=solve(id,P,y,tol,st);return R::Result{z.value,z.lower,z.upper,z.x};};
        auto r=R::solve_binary(in,&ruptura_warm[id],rs,ev,inv,residual_cb,fallback);
        if(!r.used_fallback)++st->root_solves;
        st->ruptura_attempts+=rs.attempts;st->ruptura_iterations+=rs.iterations;
        st->ruptura_fallbacks+=rs.fallback_count;st->ruptura_warm_starts+=rs.warm_starts;
        st->iterations+=rs.iterations;
        Real l=R::x_from_score(r.lower,y),u=R::x_from_score(r.upper,y);
        return {id,r.score,r.lower,r.upper,r.x,l,u};
    }

};

void set_error(char* error, int64_t n, const std::exception& ex) {
    if (error && n>0) { std::strncpy(error,ex.what(),n-1); error[n-1]=0; }
}
bool better(const Score& a, const Score& b) {
    if (a.value != b.value) return a.value>b.value;
    return a.id<b.id;
}
void check_query(double P,double y,double tol) {
    if (!(std::isfinite(P)&&P>0&&std::isfinite(y)&&y>0&&y<1&&std::isfinite(tol)&&tol>0))
        throw std::runtime_error("Require P>0, 0<y<1 and positive tolerance");
}
}

extern "C" {
void* iast_create(int64_t nc,const int64_t* offsets,const double* p,const double* q,
                  int64_t np,const int64_t* pairs,char* error,int64_t error_n) {
    try {return new Engine(nc,offsets,p,q,np,pairs);} catch(const std::exception& e){set_error(error,error_n,e);return nullptr;}
}
void* iast_create_lean_cap(int64_t nc,const int64_t* offsets,const double* p,const double* q,
                  int64_t np,const int64_t* pairs,char* error,int64_t error_n) {
    try{return new Engine(nc,offsets,p,q,np,pairs,true);}catch(const std::exception& e){set_error(error,error_n,e);return nullptr;}
}
void iast_destroy(void* handle) {delete static_cast<Engine*>(handle);}
void iast_set_bounds_mode(void* handle,int fast) {static_cast<Engine*>(handle)->fast_bounds=fast!=0;}
void iast_set_anchor_updates(void* handle,int enabled) {Engine& e=*static_cast<Engine*>(handle);e.anchor_updates_enabled=enabled!=0&&!e.lean_cap;}
void iast_prepare_cap_index(void* handle) {static_cast<Engine*>(handle)->prepare_cap_index();}
uint64_t iast_index_bytes(void* handle) {return static_cast<Engine*>(handle)->index_bytes();}
void iast_set_incumbents(void* handle,const int64_t* ids,int64_t n) {
    Engine& e=*static_cast<Engine*>(handle);e.incumbents.assign(ids,ids+n);
}
void iast_set_diagnostics(void* handle,int enabled) {static_cast<Engine*>(handle)->diagnostics_enabled=enabled!=0;}
void iast_anchor_inventory(void* handle,uint64_t* counts) {
    Engine& e=*static_cast<Engine*>(handle);std::fill(counts,counts+4,uint64_t(0));
    for(const auto& pair:e.anchors)for(const auto& a:pair)if(a.valid){++counts[0];++counts[a.origin];}
}
void iast_reset_anchors(void* handle) {
    Engine& e=*static_cast<Engine*>(handle);
    std::fill(e.anchors.begin(),e.anchors.end(),std::array<Anchor,2>{});
    std::fill(e.ruptura_warm.begin(),e.ruptura_warm.end(),ruptura_finite_pwl::WarmState{});
}
uint64_t iast_anchor_bytes(void* handle) {
    return static_cast<Engine*>(handle)->anchors.capacity()*sizeof(std::array<Anchor,2>);
}
void iast_owned_bytes(void* handle,uint64_t* values) {
    Engine& e=*static_cast<Engine*>(handle);uint64_t curve_payload=0;
    for(const auto& c:e.curves)curve_payload+=(c.p.capacity()+c.q.capacity()+c.prefix.capacity()+c.slopes.capacity())*sizeof(Real)
        +(c.prefix_bounds.capacity()+c.slope_bounds.capacity())*sizeof(Bound);
    values[0]=curve_payload;values[1]=e.curves.capacity()*sizeof(Curve);values[2]=e.pairs.capacity()*sizeof(Pair);
    values[3]=e.anchors.capacity()*sizeof(std::array<Anchor,2>);values[4]=e.ruptura_warm.capacity()*sizeof(ruptura_finite_pwl::WarmState);
    values[5]=e.index_bytes();values[6]=sizeof(Engine);
}
int64_t iast_audit_intervals(void* handle,double P,double y,char* out,int64_t size,char* error,int64_t error_n) {
    try{
        Engine& e=*static_cast<Engine*>(handle);check_query(P,y,1e-12);std::string result="[";
        if(std::fegetround()!=FE_TONEAREST)throw std::runtime_error("Rounding mode changed from FE_TONEAREST");
        auto hx=[](Real x){char b[128];std::snprintf(b,sizeof(b),"%La",x);return std::string("\"")+b+"\"";};
        for(size_t i=0;i<e.pairs.size();++i){
            if(i)result+=",";result+="{\"pair_id\":"+std::to_string(i)+",\"anchors\":[";
            if(!e.anchors.empty())for(int j=0;j<2;++j){const Anchor& a=e.anchors[i][j];if(j)result+=",";
                result+="{\"slot\":"+std::to_string(j)+",\"valid\":"+(a.valid?"true":"false")+",\"P_hex\":"+hx(a.P)+",\"y_hex\":"+hx(a.y)
                    +",\"lo_hex\":"+hx(a.l)+",\"hi_hex\":"+hx(a.u)+",\"origin\":"+std::to_string(a.origin)+"}";}
            IastStats unused{};Hint h=e.transport(i,P,y,&unused,false,e.lean_cap);
            result+="],\"transport\":{\"warm\":"+std::string(h.warm?"true":"false")+",\"lo_hex\":"+hx(h.lo)+",\"hi_hex\":"+hx(h.hi)+"}}";
        }
        result+="]";if(size<=int64_t(result.size()))throw std::runtime_error("Audit interval buffer too small");
        std::memcpy(out,result.c_str(),result.size()+1);return result.size();
    }catch(const std::exception& e){set_error(error,error_n,e);return -1;}
}
int iast_metadata(void* handle,double* metadata,double* build_seconds,uint64_t* build_probes) {
    Engine* e=static_cast<Engine*>(handle);
    for(size_t i=0;i<e->pairs.size();++i) {
        const Pair& p=e->pairs[i];
        metadata[3*i]=p.a1;metadata[3*i+1]=p.a2;metadata[3*i+2]=p.cap;
    }
    *build_seconds=e->build_seconds;*build_probes=e->build_probes;return 0;
}
int64_t iast_query(void* handle,double P,double y,int64_t k,int method,
                   const int64_t* order,double tol,int64_t* ids,double* scores,
                   double* lower,double* upper,IastStats* stats,char* error,int64_t error_n) {
    std::memset(stats,0,sizeof(*stats));
    auto t0=std::chrono::steady_clock::now();
    try {
        check_query(P,y,tol);
        if(k<0 || method<0 || method>24) throw std::runtime_error("Invalid k/method");
        Engine& e=*static_cast<Engine*>(handle);
        if(std::fegetround()!=FE_TONEAREST)throw std::runtime_error("Rounding mode changed from FE_TONEAREST");
        if(e.lean_cap&&method!=0&&method!=20)throw std::runtime_error("Lean cap allocation supports only full/reference or indexed_cap queries");
        const bool selective=method!=0 && method!=4 && method!=11 && method!=13;
        const bool warm=(method>=4&&method<=10)||method>=13;
        const bool ranked=method>=15&&method<=19;
        const bool indexed_cap=method>=20;
        const bool arithmetic=method==6||method==7||method==8||method==9||method==14||method>=16;
        const bool witness=(method>=8&&method<=10)||method==15||method==16||method==18||method==21||method==23;
        const bool continuation=method==3||(method>=5&&method<=10)||method>=14;
        const bool ruptura=method==11||method==12;
        std::multiset<std::pair<Real,int64_t>> lower_set;
        std::vector<Score> heap;heap.reserve(std::min<int64_t>(k,e.pairs.size()));
        std::vector<Score> solved;solved.reserve(std::min<size_t>(e.pairs.size(),4096));
        Real tau=0,initial_tau=0;
        struct Work {int64_t id,pos;Hint hint;Real upper;};
        std::vector<Work> work;
        auto work_less=[](const Work&a,const Work&b){return a.upper!=b.upper?a.upper<b.upper:a.pos>b.pos;};
        uint64_t generation=0;
        auto checked_support=[&](int64_t id) {
            if(e.cap_support_generation[id]==generation)return e.cap_supported[id]!=0;
            e.cap_support_generation[id]=generation;++stats->pairs_seen;
            bool ok=e.supported(e.pairs[id],Real(P),Real(y),stats);e.cap_supported[id]=ok;
            if(ok)++stats->supported;else ++stats->support_rejected;
            return ok;
        };
        if(indexed_cap) {
            e.prepare_cap_index();generation=++e.cap_generation;
            size_t valid=0;Real lower=std::numeric_limits<Real>::infinity();
            if(k>0)for(int64_t id:e.cap_lower_order)if(checked_support(id)) {
                Hint h=e.transport(id,P,y,stats,method==23,method==20||method==24);
                Real candidate_lower=h.warm?e.query_score(h.lo,P,y).lo:Real(0);
                if(e.fast_bounds&&(method==20||method==24))candidate_lower=e.cap_score_lower(id,P,y);
                lower=std::min(lower,candidate_lower);
                if(++valid==size_t(k))break;
            }
            if(valid==size_t(k)&&k>0)initial_tau=std::max(Real(0),lower*(1-1024*EPS));
            stats->rank_witness_candidates=valid;tau=initial_tau;
        }
        if(ranked) {
            std::vector<Real> lows;work.reserve(e.pairs.size());lows.reserve(e.pairs.size());
            for(size_t pos=0;pos<e.pairs.size();++pos) {
                int64_t id=order?order[pos]:int64_t(pos);
                if(id<0||id>=int64_t(e.pairs.size()))throw std::runtime_error("Invalid query order index");
                ++stats->pairs_seen;
                if(!e.supported(e.pairs[id],Real(P),Real(y),stats)){++stats->support_rejected;continue;}
                ++stats->supported;
                Hint h=e.transport(id,P,y,stats,method==18,method==17);
                Real l=h.warm?e.query_score(h.lo,P,y).lo:Real(0);
                Real u=h.warm?e.query_score(h.hi,P,y).hi:std::numeric_limits<Real>::infinity();
                work.push_back({id,int64_t(pos),h,u});lows.push_back(l);
            }
            if(k>0 && size_t(k)<=lows.size()) {
                auto nth=lows.begin()+(lows.size()-size_t(k));
                std::nth_element(lows.begin(),nth,lows.end());
                initial_tau=std::max(Real(0),*nth*(1-1024*EPS));
                stats->rank_witness_candidates=lows.size();
            }
            std::make_heap(work.begin(),work.end(),work_less);
            tau=initial_tau;
        }
        size_t scanpos=0,incpos=0;
        while(indexed_cap?(incpos<e.incumbents.size()||scanpos<e.pairs.size()):(ranked?!work.empty():scanpos<e.pairs.size())) {
            size_t pos=indexed_cap?scanpos:scanpos++;
            int64_t index_id=-1;bool from_static=false;
            if(indexed_cap) {
                if(incpos<e.incumbents.size())index_id=e.incumbents[incpos++];
                else {index_id=e.cap_upper_order[scanpos++];from_static=true;}
                if(e.cap_processed[index_id]==generation)continue;
                if(from_static&&k>0&&tau>0) {
                    Real cutoff=tau-Real(1.001)*std::max(Real(1e-10),Real(1e-8)*std::abs(tau));
                    // Same directed cap coefficient as the sorted static index.
                    Real upper=e.cap_score_upper(index_id,P,y);
                    if(upper<cutoff) {
                        size_t remaining=e.pairs.size()-scanpos+1;
                        for(int64_t prior:e.incumbents)if(e.cap_upper_rank[prior]>=int64_t(scanpos-1))--remaining;
                        stats->anchor_rejected+=remaining;stats->cap_tail_rejected+=remaining;
                        if(e.diagnostics_enabled)stats->cap_sufficient_rejected+=remaining;
                        break;
                    }
                }
                e.cap_processed[index_id]=generation;
            }
            Work current{};
            if(ranked){std::pop_heap(work.begin(),work.end(),work_less);current=work.back();work.pop_back();}
            int64_t id=indexed_cap?index_id:(ranked?current.id:(order?order[pos]:int64_t(pos)));
            if(id<0 || id>=int64_t(e.pairs.size()))throw std::runtime_error("Invalid query order index");
            if(indexed_cap) {if(!checked_support(id))continue;}
            else if(!ranked) {
                ++stats->pairs_seen;
                if(!e.supported(e.pairs[id],Real(P),Real(y),stats)) {++stats->support_rejected;continue;}
                ++stats->supported;
            }
            if(k==0)continue;
            Hint hint;
            if(ranked)hint=current.hint;
            else if(warm)hint=e.transport(id,P,y,stats,method==7||method==9||method==23,method==13||method==14||method==20);
            if(selective && (heap.size()==size_t(k)||initial_tau>0)) {
                Real tie_margin=std::max(Real(1e-10),Real(1e-8)*std::abs(tau));
                Real prune_at=tau-Real(1.001)*tie_margin;
                if(arithmetic && hint.warm && (ranked?current.upper:((e.fast_bounds&&(method==20||method==24))?e.cap_score_upper(id,P,y):e.query_score(method==24?hint.cap_hi:hint.hi,P,y).hi))<prune_at) {
                    if(ranked){
                        stats->anchor_rejected+=1+work.size();
                        if(e.diagnostics_enabled) {
                            auto classify=[&](const Work& w){
                                if(w.hint.warm&&(e.fast_bounds?e.cap_score_upper(w.id,P,y):e.query_score(w.hint.cap_hi,P,y).hi)<prune_at)++stats->cap_sufficient_rejected;
                                else ++stats->history_needed_rejected;
                            };
                            if(method==17)stats->cap_sufficient_rejected+=1+work.size();
                            else {classify(current);for(const Work& w:work)classify(w);}
                        }
                        break;
                    }
                    ++stats->anchor_rejected;
                    if(indexed_cap&&e.diagnostics_enabled) {
                        if((e.fast_bounds?e.cap_score_upper(id,P,y):e.query_score(hint.cap_hi,P,y).hi)<prune_at)++stats->cap_sufficient_rejected;
                        else ++stats->history_needed_rejected;
                    }
                    continue;
                }
                int test=prune_at>0?e.threshold(id,P,y,prune_at,stats,continuation?&hint:nullptr):0;
                if(test<0) {if(witness)e.remember_witness(id,P,y,hint,stats);++stats->threshold_rejected;continue;}
            }
            Score item=ruptura?e.solve_ruptura(id,P,y,tol,stats):e.solve(id,P,y,tol,stats,hint);
            item.canonical=!ruptura&&!hint.warm&&!hint.continued;
            if(warm && method!=13 && method!=14 && method!=17 && method!=20)e.remember(item,P,y,stats);
            solved.push_back(item);
            bool changed=false;
            if(heap.size()<size_t(k)) {heap.push_back(item);std::push_heap(heap.begin(),heap.end(),better);changed=true;
                if(selective && method!=1)lower_set.emplace(item.lower,item.id);
            }
            else if(better(item,heap.front())) {
                if(selective && method!=1) {
                    auto it=lower_set.find({heap.front().lower,heap.front().id});
                    if(it==lower_set.end())throw std::runtime_error("Lower-bound index lost a retained member");
                    lower_set.erase(it);lower_set.emplace(item.lower,item.id);
                }
                std::pop_heap(heap.begin(),heap.end(),better);heap.back()=item;
                std::push_heap(heap.begin(),heap.end(),better);changed=true;
            }
            if(selective && changed && heap.size()==size_t(k)) {
                if(method==1) {
                    tau=heap[0].lower;
                    for(const Score& h:heap) {tau=std::min(tau,h.lower);++stats->legacy_refresh_items;}
                } else tau=lower_set.begin()->first;
                // The threshold is below all retained numerical lower brackets.
                tau=std::max(initial_tau,std::max(Real(0),tau*(1-1024*EPS)));
            }
        }
        // A fixed shell around the raw kth score avoids a non-transitive
        // tolerance comparator. The identical rule is applied to both methods.
        std::vector<Score> selected,tied;
        if(!heap.empty()) {
            Real boundary=heap.front().value;
            Real margin=std::max(Real(1e-10),Real(1e-8)*std::abs(boundary));
            for(const Score& s:solved) {
                if(s.value>boundary+margin)selected.push_back(s);
                else if(s.value>=boundary-margin)tied.push_back(s);
            }
            stats->boundary_tie_candidates=tied.size();
            std::sort(selected.begin(),selected.end(),better);
            // Strict winners can contain numerically indistinguishable scores
            // far above the kth shell. Mark all adjacent ambiguous endpoints
            // before changing any score, then use the same cold native solve
            // for every plan. This stabilizes ordering, not shell membership.
            std::vector<bool> canonical(selected.size(),false);
            for(size_t j=1;j<selected.size();++j) {
                const Score& a=selected[j-1];const Score& b=selected[j];
                Real guard=32*Real(tol)*std::max({Real(1),std::abs(a.value),std::abs(b.value)});
                if(std::abs(a.value-b.value)<=guard || a.lower<=b.upper) {
                    canonical[j-1]=true;canonical[j]=true;
                }
            }
            for(size_t j=0;j<selected.size();++j)if(canonical[j]&&!selected[j].canonical) {
                selected[j]=e.solve(selected[j].id,P,y,tol,stats,Hint{});
                selected[j].canonical=true;++stats->canonical_refinements;
            }
            std::sort(selected.begin(),selected.end(),better);
            size_t needed=heap.size()-selected.size();
            auto id_less=[](const Score&a,const Score&b){return a.id<b.id;};
            if(tied.size()>needed) {
                std::nth_element(tied.begin(),tied.begin()+needed,tied.end(),id_less);
                tied.resize(needed);
            }
            std::sort(tied.begin(),tied.end(),id_less);
            selected.insert(selected.end(),tied.begin(),tied.end());
        }
        for(size_t i=0;i<selected.size();++i) {
            ids[i]=selected[i].id;scores[i]=selected[i].value;lower[i]=lower_double(selected[i].lower);upper[i]=upper_double(selected[i].upper);
        }
        stats->seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-t0).count();
        return selected.size();
    } catch(const std::exception& e){set_error(error,error_n,e);return -1;}
}
int iast_solve_pair(void* handle,int64_t id,double P,double y,double tol,
                    double* result,IastStats* stats,char* error,int64_t error_n) {
    std::memset(stats,0,sizeof(*stats));
    try {
        check_query(P,y,tol);const Engine& e=*static_cast<Engine*>(handle);
        if(std::fegetround()!=FE_TONEAREST)throw std::runtime_error("Rounding mode changed from FE_TONEAREST");
        if(id<0||id>=int64_t(e.pairs.size()))throw std::runtime_error("Invalid pair id");
        if(!e.supported(e.pairs[id],Real(P),Real(y),stats))return 0;
        Score s=e.solve(id,P,y,tol,stats);
        result[0]=s.value;result[1]=lower_double(s.lower);result[2]=upper_double(s.upper);result[3]=s.x;return 1;
    }catch(const std::exception& e){set_error(error,error_n,e);return -1;}
}
int iast_threshold(void* handle,int64_t id,double P,double y,double tau,
                    IastStats* stats,char* error,int64_t error_n) {
    std::memset(stats,0,sizeof(*stats));
    try {
        check_query(P,y,1e-10);const Engine& e=*static_cast<Engine*>(handle);
        if(std::fegetround()!=FE_TONEAREST)throw std::runtime_error("Rounding mode changed from FE_TONEAREST");
        if(id<0||id>=int64_t(e.pairs.size())||tau<=0||!std::isfinite(tau))throw std::runtime_error("Invalid pair/threshold");
        if(!e.supported(e.pairs[id],Real(P),Real(y),stats))return 2;
        return e.threshold(id,P,y,tau,stats);
    }catch(const std::exception& e){set_error(error,error_n,e);return -2;}
}
}
